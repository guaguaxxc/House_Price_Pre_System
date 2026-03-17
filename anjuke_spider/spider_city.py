"""
城市列表爬取模块
================================================
负责从安居客城市列表页抓取所有城市的名称和拼音，并保存为CSV文件。
支持强制重新爬取或读取已有文件，避免重复请求。
"""

import csv
import os
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from config import CITY_LIST_URL, CITY_CSV_PATH, CSV_ENCODING
from session import create_session
from utils import logger, ensure_dir_exists


def crawl_and_save_city_csv(force_reload=False):
    """
    爬取全国城市列表，并保存为CSV文件。
    如果 force_reload=False 且 CSV 文件已存在，则直接读取并返回内容；
    否则发送请求解析城市列表页，提取城市名称和拼音，写入CSV。
    :param force_reload: bool - 是否强制重新爬取并覆盖现有文件
    :return: list[dict] - 城市列表，每个元素包含 'city_name' 和 'city_pinyin'
    :raises RuntimeError: 当请求失败或解析出错时抛出
    """
    # 若文件已存在且不强制重爬，则直接读取
    if not force_reload and os.path.exists(CITY_CSV_PATH):
        logger.info(f"城市列表文件已存在，跳过爬取：{CITY_CSV_PATH}")
        with open(CITY_CSV_PATH, 'r', encoding=CSV_ENCODING) as f:
            return list(csv.DictReader(f))

    # 确保数据目录存在
    ensure_dir_exists(os.path.dirname(CITY_CSV_PATH))

    # 创建会话并请求城市列表页
    session = create_session()
    try:
        logger.info(f"开始爬取城市列表：{CITY_LIST_URL}")
        resp = session.get(CITY_LIST_URL)
        resp.raise_for_status()  # 检查HTTP错误
    except Exception as e:
        logger.error(f"爬取城市列表失败：{str(e)}")
        raise RuntimeError(f"城市列表爬取失败：{str(e)}") from e

    # 使用lxml解析器解析HTML
    soup = BeautifulSoup(resp.text, "lxml")
    cities = []

    # 查找所有城市区块（每个字母开头的区域）
    blocks = soup.find_all("div", class_="ajk-city-cell is-letter")
    for block in blocks:
        ul = block.find("ul", class_="ajk-city-cell-content")
        if not ul:
            continue

        for li in ul.find_all("li"):
            a_tag = li.find("a")
            if not a_tag:
                continue

            city_name = a_tag.get_text(strip=True)  # 城市中文名
            city_url = a_tag.get("href", "").strip()  # 城市链接，如 https://bj.anjuke.com
            if not city_url or not city_name:
                continue

            # 从链接中提取城市拼音（子域名）
            try:
                parsed_url = urlparse(city_url)
                city_pinyin = parsed_url.netloc.split(".")[0]  # 取子域名部分
            except Exception:
                continue

            city_info = {
                "city_name": city_name,
                "city_pinyin": city_pinyin
            }
            cities.append(city_info)
            logger.debug(f"提取城市：{city_name} ({city_pinyin})")

    # 将结果写入CSV
    if cities:
        with open(CITY_CSV_PATH, "w", newline="", encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=["city_name", "city_pinyin"])
            writer.writeheader()
            writer.writerows(cities)
        logger.info(f"城市列表保存完成：{len(cities)} 条数据 → {CITY_CSV_PATH}")
    else:
        logger.warning("未提取到任何城市数据！")

    return cities


# 运行入口：单独运行此模块时强制重新爬取城市列表
if __name__ == "__main__":
    crawl_and_save_city_csv(force_reload=True)
