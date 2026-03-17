"""
全局配置文件（毕设-安居客爬虫）
=================
包含请求配置、路径配置、爬虫控制参数等
"""
from urllib3.util import Retry
import random
import time

# ================= 请求配置 =================
# 随机UA池（扩充真实UA）
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'
]


# 动态生成请求头（增强反爬）
def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Referer': 'https://www.anjuke.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',  # 新增编码头
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive',  # 长连接
        'Upgrade-Insecure-Requests': '1'  # 强制HTTPS
    }


# Cookies（建议定期更新，毕设可从浏览器抓包获取）
def get_dynamic_cookies():
    base_cookies = {
        'ctid': '11',
        'ajkAuthTicket': 'TT=d5470263ab293ad63f3f4c498f506489&TS=1773734739698&PBODY=cncDI4p7Y2qAlWllnipY98jIxJaVlyaIdDQuf-ib-MKLGtthg-wtZT49QFUbgvR37HbftDq3RlLf0uEmdOG7UUhDTn_VC6iuU_oxyVvvXDOSPPNUnlddtUeeN5jBBX2ma1jUmRT5MB44INU0TQcKudyWEBx1vd6VjlEZqSDZ_58&VER=2&CUID=uXrr9JiwZTqHgkwywSR0TuJpTd-Z8guI',
    }
    return base_cookies


# 重试策略（增强版）
RETRY_STRATEGY = Retry(
    total=5,  # 增加重试次数
    backoff_factor=2,  # 指数退避（2^n秒）
    status_forcelist=[429, 500, 502, 503, 504],  # 新增429（请求频繁）
    allowed_methods=frozenset(['GET']),
    raise_on_status=False  # 不抛出异常，返回响应
)

# ================= 路径配置 =================
# 城市列表页URL
CITY_LIST_URL = "https://www.anjuke.com/sy-city.html"
# 小区列表页URL模板
BASE_URL_TEMPLATE = "https://{city}.anjuke.com/community/p{page}/"
# 文件路径（统一放到data目录，便于管理）
DATA_DIR = "./data"
CITY_CSV_PATH = f"{DATA_DIR}/anjuke_city.csv"
FINAL_CSV_PATH = f"{DATA_DIR}/communities_data.csv"
PROGRESS_CSV_PATH = f"{DATA_DIR}/crawl_progress.csv"

# ================= 爬虫控制配置 =================
# 每个城市爬取的小区数量上限
PER_CITY_LIMIT = 10

# 列表页无结果重试次数
LIST_PAGE_RETRY_TIMES = 3
LIST_PAGE_RETRY_DELAY = 2  # 基础延迟秒数


# 随机延迟（反爬核心：增加随机范围）
def get_random_delay():
    return random.uniform(0.1, 0.5)


# CSV配置
CSV_HEADERS = [
    '城市', '小区名称', '价格', '地址', '小区链接',
    '物业类型', '权属类别', '竣工时间', '产权年限', '总户数', '总建筑面积', '容积率',
    '绿化率', '建筑类型', '所属商圈', '统一供暖', '供水供电', '停车位', '物业费',
    '停车费', '车位管理费', '物业公司', '小区地址', '开发商', '在售房源', '在租房源'
]
CSV_ENCODING = "utf-8-sig"  # 兼容Excel打开

# 断点续爬默认配置
DEFAULT_START_INDEX = 0
PROGRESS_HEADERS = ["last_crawled_index", "crawled_cities", "failed_cities"]
