"""
请求会话模块
================================================
创建并配置一个带有重试机制、随机请求头和Cookie的requests Session对象，
用于所有HTTP请求，以提高爬虫的稳定性和反爬能力。
"""

import requests
from requests.adapters import HTTPAdapter
from config import RETRY_STRATEGY, get_random_headers, get_cookies


def create_session():
    """
    创建并返回一个配置好的requests Session对象。
    该会话包含以下特性：
        - 挂载HTTPAdapter，支持重试策略（指数退避）
        - 设置随机生成的请求头
        - 添加基础Cookie
        - 配置超时时间和最大重定向次数
    :return: requests.Session - 配置好的会话对象
    """
    session = requests.Session()

    # 挂载重试适配器到HTTP和HTTPS协议
    adapter = HTTPAdapter(max_retries=RETRY_STRATEGY)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # 设置动态请求头和Cookie
    session.headers.update(get_random_headers())
    session.cookies.update(get_cookies())

    # 全局超时时间（连接和读取均适用）
    session.timeout = 15

    # 最大重定向次数，防止无限重定向（如遇到验证页）
    session.max_redirects = 5

    return session
