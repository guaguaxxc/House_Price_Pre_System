"""
全局配置文件
================================================
该文件包含爬虫运行所需的所有配置参数，包括请求头、Cookie、重试策略、
文件路径、爬取限制、CSV格式以及断点续爬相关配置。
"""

from urllib3.util import Retry
import random

# ================= 请求配置 =================
# 随机User-Agent池
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'
]


def get_random_headers():
    """
    生成随机的请求头，每次请求使用不同的User-Agent，并添加Referer、Accept等常用头字段，模拟真实浏览器访问。
    :return: dict - 包含随机User-Agent的完整请求头
    """
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Referer': 'https://www.anjuke.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',  # 支持压缩编码
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive',  # 保持长连接
        'Upgrade-Insecure-Requests': '1'  # 强制使用HTTPS
    }


def get_cookies():
    """
    返回基础Cookie字典，用于维持会话状态。
    :return: dict - Cookie键值对
    """
    base_cookies = {
        'ctid': '11',
        'ajkAuthTicket': 'TT=d5470263ab293ad63f3f4c498f506489&TS=1773734739698&PBODY=cncDI4p7Y2qAlWllnipY98jIxJaVlyaIdDQuf-ib-MKLGtthg-wtZT49QFUbgvR37HbftDq3RlLf0uEmdOG7UUhDTn_VC6iuU_oxyVvvXDOSPPNUnlddtUeeN5jBBX2ma1jUmRT5MB44INU0TQcKudyWEBx1vd6VjlEZqSDZ_58&VER=2&CUID=uXrr9JiwZTqHgkwywSR0TuJpTd-Z8guI',
    }
    return base_cookies


# 重试策略：当请求失败时自动重试，使用指数退避算法
RETRY_STRATEGY = Retry(
    total=5,  # 最大重试次数
    backoff_factor=2,  # 退避因子，重试间隔为 2^n 秒
    status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的HTTP状态码
    allowed_methods=frozenset(['GET']),  # 仅对GET请求进行重试
    raise_on_status=False  # 重试耗尽后不抛出异常，返回最后一次响应
)

# ================= 路径配置 =================
# 城市列表页的URL，用于获取所有城市的拼音和名称
CITY_LIST_URL = "https://www.anjuke.com/sy-city.html"
# 小区列表页URL模板，通过城市拼音和页码进行格式化
BASE_URL_TEMPLATE = "https://{city}.anjuke_spider.com/community/p{page}/"

DATA_DIR = "./data"  # 数据存储目录及文件路径，统一放在data文件夹下
CITY_CSV_PATH = f"{DATA_DIR}/anjuke_city.csv"  # 城市列表CSV
FINAL_CSV_PATH = f"{DATA_DIR}/communities_data.csv"  # 最终小区数据CSV
PROGRESS_CSV_PATH = f"{DATA_DIR}/crawl_progress.csv"  # 爬取进度CSV

# ================= 爬虫控制配置 =================
# 每个城市最多爬取的小区数量
PER_CITY_LIMIT = 50

# 列表页请求失败时的重试次数及基础延迟
LIST_PAGE_RETRY_TIMES = 3
# 基础延迟秒数，重试时会指数增长
LIST_PAGE_RETRY_DELAY = 2


def get_random_delay():
    """
    生成一个随机的短延迟时间，用于详情页请求之间的间隔，降低请求频率。
    :return: float - 0.1到0.5之间的随机浮点数
    """
    return random.uniform(0.1, 0.5)


# CSV文件列定义，按照数据写入顺序排列
CSV_HEADERS = [
    '城市', '小区名称', '价格', '地址', '小区链接',
    '物业类型', '权属类别', '竣工时间', '产权年限', '总户数', '总建筑面积', '容积率',
    '绿化率', '建筑类型', '所属商圈', '统一供暖', '供水供电', '停车位', '物业费',
    '停车费', '车位管理费', '物业公司', '小区地址', '开发商', '在售房源', '在租房源'
]
CSV_ENCODING = "utf-8-sig"  # 使用带BOM的UTF-8，便于Excel直接打开
# 断点续爬默认起始索引（0表示从第一个城市开始）
DEFAULT_START_INDEX = 0
# 进度CSV的表头定义
PROGRESS_HEADERS = ["last_crawled_index", "crawled_cities", "failed_cities"]
