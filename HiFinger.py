import json,sys,argparse,time
import requests,urllib3,csv
import fake_useragent
import multiprocessing
import datetime
import mmh3
from protocol_evaluate import *
from lxml import etree
from multiprocessing import Pool,Manager
from chardet.universaldetector import UniversalDetector
from TideFinger import *
import traceback
urllib3.disable_warnings()

def color_red(text):
    return "\033[31m" + text + "\033[0m"
def color_green(text):
    return "\033[32m" + text + "\033[0m"
def color_yellow(text):
    return "\033[33m" + text + "\033[0m"
def color_blue(text):
    return "\033[34m" + text + "\033[0m"
def color_purple(text):
    return "\033[35m" + text + "\033[0m"
def color_cyan(text):
    return "\033[36m" + text + "\033[0m"
def color_gray(text):
    return "\033[37m" + text + "\033[0m"
def color_default(text):
    return "\033[38m" + text + "\033[0m"

def str_style(text):
    return color_default('[')+text+color_default(']')
def result_print(info):
    '''
        输出结果
    '''
    resStr = ""
    if info['status'] == "Time out" or info['status'] == "Unknown error occurred" or info['status'] == "Unable to connect to the server":
        resStr = str_style(color_red("-"))+str_style(color_red(info['url']))+str_style(color_red(str(info['status'])))
    elif info['status'] == 200:
        resStr = str_style(color_green("+"))+str_style(color_green(info['url']))+str_style(color_green(str(info['status'])))
    else:
        resStr = str_style(color_blue("*"))+str_style(color_blue(info['url']))+str_style(color_blue(str(info['status'])))
    
    if info['title'] != "":
        resStr += str_style(color_purple(info['title']))

    if info['server'] != "":
        resStr += str_style(color_cyan(info['server']))

    if info['cms'] != []:
        temp = ""
        for i in info['cms']:
            temp += i+"|"
        temp = temp[:-1]
        resStr += str_style(color_yellow(temp))
    if info['banner'] != []:
        temp = ""
        for i in info['banner']:
            temp += i+"|"
        temp = temp[:-1]
        resStr += str_style(color_yellow(temp))
    print(resStr)
    #print(info)


def write_to_csv(data, filename):
    '''
        将结果写入csv文件
    '''
    # 判断文件夹是否存在
    if not os.path.exists('./results'):
        # 如果文件夹不存在，创建文件夹
        os.makedirs('./results')
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = data[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()  # 写入表头
        for item in data:
            # 将列表类型的值转换为逗号分隔的字符串
            for key in ('cms', 'banner'):
                if isinstance(item.get(key), list):
                    item[key] = ', '.join(item[key])
            writer.writerow(item)  # 写入数据行
        if ":" in filename:
            print(f"扫描结果已成功保存到：",filename)
        else:
            filename = os.getcwd().replace('\\', '/') + filename.replace('./','/')
            filename = filename.replace(' ', '')
            print(f"扫描结果已成功保存到：", filename)
def timed_function(func):
    """
    装饰器，用于计算函数执行时间
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()  # 记录开始时间
        result = func(*args, **kwargs)  # 调用原函数并获取结果
        end_time = time.time()  # 记录结束时间
        elapsed_time = end_time - start_time  # 计算耗时
        print(f"扫描结束，耗时：{elapsed_time:.6f}秒")
        return result
    return wrapper
def read_urls(file_path):
    with open(file_path, "r") as file:
        res = file.readlines()
        return res

def ico_hash(url):
    '''
    获取ico的hash值
    '''
    try:
        ico_url = url + ''
        response = requests.get(ico_url, timeout=5, verify=False)
        if response.status_code == 200:
            ico_data = response.content
            hash_value = mmh3.hash(ico_data)
            return str(hash_value)
        else:
            return ''
    except Exception as e:
        return ''

def hash_match(hash_value, keyword):
    '''
    判断hash值是否匹配
    '''
    if keyword == hash_value:
        return True
    else:
        return False

def extract_url(url):
    '''
    提取url中的域名
    '''
    pattern = r"(?:(?:https?|ftp):\/\/)?(?:[\w.-]+|\[[\d:.]+\])(?::\d+)?(?=/.*|$)"
    match = re.search(pattern, url)
    if not '.' in url:
        return ''
    if match:
        return match.group(0)
    else:
        return ''
def contains_all_substrings(main_string, substring_list):
    '''
    判断主字符串是否包含所有子字符串
    '''
    for substring in substring_list:
        if substring not in main_string:
            return False
    return True
def my_cms_match(text, patterns):
    '''
    判断字符串是否包含所有子字符串
    '''
    return any(re.search(p, text) for p in patterns)

def match_cms(finger_regular, url, header, title, body):
    '''
    根据finger_regular检测cms
    '''
    #print(f"url: {url}\ntitle: {title}\nheader: {header}\nbody: {body}\n")
    header = str(header)
    match_result = {'url':'','cms':[]}
    fingers = []
    try:
        ico_hash_value = ico_hash(url)
        for re in finger_regular:
            cms = re['cms']
            if cms in match_result['cms']:
                continue
            method = re['method']
            location = re['location']
            keyword = re['keyword']
            if method == "keyword":
                if location == "title":
                    if contains_all_substrings(title,keyword):
                        fingers.append(cms)
                elif location == "body":
                    if contains_all_substrings(body,keyword):
                        fingers.append(cms)
                elif location == "header":
                    if contains_all_substrings(header,keyword):
                        fingers.append(cms)
            elif method == "regular":
                if location == "title":
                    if my_cms_match(title, keyword):
                        fingers.append(cms)
                elif location == "body":
                    if my_cms_match(body, keyword):
                        fingers.append(cms)
                elif location == "header":
                    if my_cms_match(header, keyword):
                        fingers.append(cms)
            elif method == "faviconhash":
                if hash_match(ico_hash_value, keyword):
                    fingers.append(cms)

        match_result['url'] = url
        match_result['cms'] = list(set(fingers))
        return match_result
    except Exception as e:
        print(traceback.print_exc())
        return {}

def work(target_url,finger_regular,res_list):
    try:
        ua = fake_useragent.FakeUserAgent()
        info = {'url':target_url, 'status':'','server':'','title':'', 'cms':[], 'banner':[]}
        header = {"User-Agent":ua.getRandom['useragent'],'Accept-Encoding':'gzip, deflate'}
        if "https" in target_url:
            response = requests.get(url=target_url,headers=header,timeout=(3.05,20),verify=False)
        else:
            response = requests.get(url=target_url,headers=header,timeout=(3.05,20))
        info['status'] = response.status_code

        if 'Server' in response.headers:
            info['server'] = response.headers['Server']
        
        # # 检查并强制指定编码
        # if 'charset' in response.headers.get('Content-Type'):
        #     encoding = response.headers['Content-Type'].split('charset=')[-1]
        # elif response.apparent_encoding == "GB2312" or response.apparent_encoding == "GBK":
        #     content = response.content.decode("GB18030")
        # else:
        #     encoding = 'utf-8'
        # content = response.content.decode(encoding)
        
        # 使用chardet检测编码
        detector = UniversalDetector()
        detector.feed(response.content)
        detector.close()
        detected_encoding = detector.result['encoding']

        # 根据检测结果解码
        if detected_encoding:
            content = response.content.decode(detected_encoding, errors='replace')
        else:
            # 如果无法自动检测，则尝试使用UTF-8或其他常见编码
            content = response.content.decode('utf-8', errors='replace')

        if response.status_code == 200:
            page = etree.HTML(content)
            title = page.xpath("//title/text()")
            if title:
                info['title'] = title[0]
            if "isSearchEngine" in content:
                match = re.search(r'document\.title\s*=\s*"([^"]*)"', content)
                if match:
                    info['title'] = match.group(1)
            info.update(match_cms(finger_regular,target_url, response.headers, title, response.text))
        elif "<html>" in content:
            page = etree.HTML(content)
            title = page.xpath("//title/text()")
            if title:
                info['title'] = title[0]
            info.update(match_cms(finger_regular,target_url, response.headers, title, response.text))

        
        banner = []
        fofa_cms = Cmsscanner(target_url)
        fofa_finger = fofa_cms.run()
        for x in fofa_finger:
            banner.append(x)

        Wappalyzer = useWappalyzer(target_url)
        for x in Wappalyzer:
            x = str(x).replace('\\;confidence:50','')
            banner.append(x)
        
        update = False
        webanalyzer_banner = webanalyzer.check(target_url,update)
        for webanalyzer_banner_ in webanalyzer_banner:
            banner.append(webanalyzer_banner_)
        
        banner_tmp = []
        banner.sort()
        banner_ = set(list(banner))

        for x in banner_:
            if x:
                flag = 0
                for y in info['cms']:
                    if str(x).lower() == str(y).lower() or str(y).lower() == str(x):
                        flag = 1
                        continue
                if flag == 0:
                    banner_tmp.append(x)

        banner = banner_tmp
        info['banner'] = banner
    except requests.exceptions.Timeout:
        info['status'] = "Time out"
    except requests.exceptions.ConnectionError:
        info['status'] = "Unable to connect to the server"
    except requests.exceptions.RequestException as e:
        info['status'] = "Unknown error occurred"
    except Exception as error:
        pass
        #print(f"[Error]{error}")
    finally:
        result_print(info)
        res_list.append(info)

@timed_function
def process_pool(finger_regular,file_path,res_list,pool_num=4):
    '''
    多进程处理
    '''
    urls = read_urls(file_path)
    urls = list(set(urls))
    if urls == []:
        print("[x]No URLs found in the file")
        res_list = []
        os._exit(0)
    with multiprocessing.Pool(processes=pool_num) as pool:
        for url in urls:
            try:
                url = extract_url(url)
                if url.strip() == '':
                    continue
                if not 'http' in url:
                    # url = url.split('//')[-1]
                    url = detect_optimal_protocol(url) + url
                url = url.strip()
                pool.apply_async(work, args=(url,finger_regular,res_list,))
            except Exception as e:
                print(e)
        pool.close()
        pool.join()

@timed_function
def one_work(target_url,finger_regular,res_list):
    target_url = args.url
    target_url = extract_url(target_url)
    if target_url == '':
        print("[x]Invild URL")
        os._exit(0)

    if not 'http' in target_url:
        # target_url = target_url.split('//')[-1]
        target_url = detect_optimal_protocol(target_url) + target_url
    target_url = target_url.strip()
    if target_url[-1] == '/':
        target_url = target_url[:-1]
    work(target_url,finger_regular,res_list)

def print_slogan():
    print('''
██╗  ██╗██╗███████╗██╗███╗   ██╗ ██████╗ ███████╗██████╗ 
██║  ██║██║██╔════╝██║████╗  ██║██╔════╝ ██╔════╝██╔══██╗
███████║██║█████╗  ██║██╔██╗ ██║██║  ███╗█████╗  ██████╔╝
██╔══██║██║██╔══╝  ██║██║╚██╗██║██║   ██║██╔══╝  ██╔══██╗
██║  ██║██║██║     ██║██║ ╚████║╚██████╔╝███████╗██║  ██║
╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
                                                         
''',end="")
    print("-"*60,'\n')

if __name__ == '__main__':
    try:
        print_slogan()
        manager = Manager()
        result_list = manager.list()
        finger_regular = {}

        current_time = datetime.datetime.now()
        custom_format = "%Y_%m_%d_%H_%M_%S"
        formatted_time = current_time.strftime(custom_format)

        #导入文本cms指纹信息
        with open("./cms_finger.json","r",encoding="utf-8") as file:
            finger_regular = json.load(file)['fingerprint']
        parser = argparse.ArgumentParser()
        parser.add_argument("-u", "--url", help="Target URL", dest="url", type=str)
        parser.add_argument("-f", "--file", help="Target URLs file", dest="file", type=str)
        parser.add_argument("-o", "--output", help="File path for saving results", dest="output", type=str,default='./results/'+formatted_time+'.csv')
        parser.add_argument("-p", "--pool", help="Number of processes", dest="pool", type=int, default=4)
        args = parser.parse_args()

        #如果用户没有输入任何参数，则输出帮助信息
        if len(sys.argv) == 1:
            parser.print_help()
        elif args.url is not None:
            one_work(args.url, finger_regular,result_list)
            #print(result_list)
            if result_list != []:
                write_to_csv(result_list,args.output)
        elif args.file is not None:
            process_pool(finger_regular,args.file,result_list,args.pool)
            #print(result_list)
            if result_list != []:
                write_to_csv(result_list,args.output)        

        
    except AttributeError as e:
        parser.print_help()
    except:
        print('\n','>>>' * 20)
        print(traceback.print_exc())
    #main()
        