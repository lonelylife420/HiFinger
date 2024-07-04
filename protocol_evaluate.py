import requests
from urllib.parse import urlparse, urlunparse

def test_url(url):
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        status_code = response.status_code
        response_time = response.elapsed.total_seconds()
        content_length = len(response.content)
        ssl_error = None
    except requests.exceptions.SSLError as e:
        status_code = None
        response_time = None
        content_length = None
        ssl_error = str(e)
    except requests.exceptions.RequestException as e:
        status_code = None
        response_time = None
        content_length = None
        ssl_error = str(e)

    return {
        'status_code': status_code,
        'response_time': response_time,
        'content_length': content_length,
        'ssl_error': ssl_error,
    }
def test_both_protocols(input_url):
    url = urlparse(input_url)
    http_url = urlunparse(('http', url.netloc, url.path, url.params, url.query, url.fragment))
    https_url = urlunparse(('https', url.netloc, url.path, url.params, url.query, url.fragment))
    if '///' in http_url:
        http_url = http_url.replace('///','//')
    if '///' in https_url:
        https_url = https_url.replace('///','//')
    http_result = test_url(http_url)
    https_result = test_url(https_url)

    return http_result, https_result
def evaluate_results(http_result, https_result):
    if not http_result['status_code'] and not https_result['status_code']:
        # 如果两者都无法正常访问，返回错误信息
        evaluate_result = "Both HTTP and HTTPS failed to access the URL."
        return "http://"

    if http_result['status_code'] == https_result['status_code'] == 200:
        # 如果状态码都是200，比较响应时间和内容长度
        http_response_time = http_result['response_time']
        https_response_time = https_result['response_time']
        time_threshold = max(http_response_time, https_response_time) * 0.1

        if abs(http_response_time - https_response_time) <= time_threshold:
            # 响应时间差异不大，比较内容长度
            if http_result['content_length'] == https_result['content_length']:
                evaluate_result = "Both protocols seem equally suitable."
                return "http://"
            elif http_result['content_length'] > https_result['content_length']:
                evaluate_result = "HTTP seems to provide more complete content."
                return "http://"
            else:
                evaluate_result = "HTTPs seems to provide more complete content."
                return "https://"

        elif http_response_time < https_response_time:
            evaluate_result = "HTTP has a significantly faster response time."
            return "http://"
        else:
            evaluate_result = "HTTPS has a significantly faster response time."
            return "https://"

    elif http_result['status_code'] == 200:
        # HTTP成功，HTTPS失败或状态码非200
        evaluate_result = f"HTTP is functioning correctly ({http_result['status_code']}), but HTTPS encountered issues: {https_result['ssl_error']}. Use HTTP with caution due to potential security risks."
        return "http://"

    elif https_result['status_code'] == 200:
        # HTTPS成功，HTTP失败或状态码非200
        evaluate_result = f"HTTPS is functioning correctly ({https_result['status_code']}), but HTTP encountered issues: {http_result['ssl_error']}. Use HTTPS for secure communication."
        return "https://"

    else:
        # 两者状态码都不是200，但至少有一个成功
        evaluate_result = f"Both protocols returned non-200 status codes: HTTP ({http_result['status_code']}) and HTTPS ({https_result['status_code']}). Unable to determine which is more suitable."
        return "http://"
def detect_optimal_protocol(user_input):
    http_result, https_result = test_both_protocols(user_input)
    evaluation = evaluate_results(http_result, https_result)
    return evaluation

# 用户输入链接
if __name__ == "__main__":
    input_url = input("Enter a URL: ")
    print(detect_optimal_protocol(input_url))