"""
城市列表爬取模块
=================
爬取全国城市列表并保存为CSV
"""
import csv
import os

from config import CITY_LIST_URL, CITY_CSV_PATH, CSV_ENCODING
from session import create_session
from urllib.parse import urlparse
from utils import logger, ensure_dir_exists


def crawl_and_save_city_csv(force_reload=False):
    """
    爬取城市列表并保存为CSV
    :param force_reload: 是否强制重新爬取（覆盖现有文件）
    :return: list[dict] - 城市列表
    """
    # 检查文件是否已存在
    if not force_reload and os.path.exists(CITY_CSV_PATH):
        logger.info(f"城市列表文件已存在，跳过爬取：{CITY_CSV_PATH}")
        # 读取现有文件
        with open(CITY_CSV_PATH, 'r', encoding=CSV_ENCODING) as f:
            return list(csv.DictReader(f))

    # 确保数据目录存在
    ensure_dir_exists(os.path.dirname(CITY_CSV_PATH))

    # 创建会话并请求
    session = create_session()
    try:
        logger.info(f"开始爬取城市列表：{CITY_LIST_URL}")
        resp = session.get(CITY_LIST_URL)
        resp.raise_for_status()  # 触发HTTP错误
    except Exception as e:
        logger.error(f"爬取城市列表失败：{str(e)}")
        raise RuntimeError(f"城市列表爬取失败：{str(e)}") from e

    # 解析页面（使用lxml解析器，更快更稳定）
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "lxml")
    cities = []
    blocks = soup.find_all("div", class_="ajk-city-cell is-letter")

    for block in blocks:
        ul = block.find("ul", class_="ajk-city-cell-content")
        if not ul:
            continue

        for li in ul.find_all("li"):
            a_tag = li.find("a")
            if not a_tag:
                continue

            city_name = a_tag.get_text(strip=True)
            city_url = a_tag.get("href", "").strip()
            if not city_url or not city_name:
                continue

            # 提取城市拼音（如 https://bj.anjuke.com → bj）
            try:
                parsed_url = urlparse(city_url)
                city_pinyin = parsed_url.netloc.split(".")[0]
            except:
                continue

            city_info = {
                "city_name": city_name,
                "city_pinyin": city_pinyin
            }
            cities.append(city_info)
            logger.debug(f"提取城市：{city_name} ({city_pinyin})")

    # 保存为CSV
    if cities:
        with open(CITY_CSV_PATH, "w", newline="", encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=["city_name", "city_pinyin"])
            writer.writeheader()
            writer.writerows(cities)
        logger.info(f"✅ 城市列表保存完成：{len(cities)} 条数据 → {CITY_CSV_PATH}")
    else:
        logger.warning("未提取到任何城市数据！")

    return cities


# 调试用
if __name__ == "__main__":
    crawl_and_save_city_csv(force_reload=True)
