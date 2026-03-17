"""
请求会话模块（毕设-安居客爬虫）
=================
创建带重试/反爬配置的requests会话
"""
import requests
from requests.adapters import HTTPAdapter
from config import RETRY_STRATEGY, get_random_headers, get_dynamic_cookies


def create_session():
    """
    创建配置好的请求会话
    :return: requests.Session对象
    """
    session = requests.Session()

    # 挂载重试适配器
    adapter = HTTPAdapter(max_retries=RETRY_STRATEGY)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # 设置请求头和Cookie
    session.headers.update(get_random_headers())
    session.cookies.update(get_dynamic_cookies())

    # 超时配置
    session.timeout = 15

    # 禁用重定向限制（部分页面会重定向到验证页）
    session.max_redirects = 5

    return session