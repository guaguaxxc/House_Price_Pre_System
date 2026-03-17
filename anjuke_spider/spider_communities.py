"""
小区数据爬取模块
================================================
针对单个城市，爬取其所有小区列表页和详情页，提取结构化数据。
包含列表页重试机制、详情页解析、翻页控制及数据收集。
"""

import time
import random
from bs4 import BeautifulSoup
from config import (BASE_URL_TEMPLATE, PER_CITY_LIMIT, get_random_delay,
                    LIST_PAGE_RETRY_TIMES, LIST_PAGE_RETRY_DELAY, CSV_HEADERS)
from session import create_session
from page_parser import parse_list_page, parse_detail_page
from utils import logger, safe_get_text


def crawl_city(city_name, city_pinyin, limit=PER_CITY_LIMIT):
    """
    爬取指定城市的小区数据。
    该函数会依次请求该城市的列表页（从第1页开始），
    对每一页中的每个小区，请求详情页并解析所需字段。
    当达到 limit 数量或列表页无数据时停止。
    :param city_name: str - 城市中文名
    :param city_pinyin: str - 城市拼音（用于构造URL）
    :param limit: int - 最多爬取的小区数量
    :return: list[list] - 符合CSV_HEADERS顺序的数据行列表
    """
    session = create_session()
    city_data = []  # 存储当前城市所有小区数据
    collected = 0  # 已收集数量
    page = 1  # 当前页码
    logger.info(f"开始爬取城市：{city_name}（拼音：{city_pinyin}），上限：{limit}条")
    while collected < limit:
        list_url = BASE_URL_TEMPLATE.format(city=city_pinyin, page=page)
        communities = None
        retry_count = 0
        # 列表页请求重试循环
        while retry_count < LIST_PAGE_RETRY_TIMES:
            try:
                logger.debug(
                    f"[{city_name}] 爬取列表页：第{page}页 (尝试 {retry_count + 1}/{LIST_PAGE_RETRY_TIMES}) → {list_url}")
                list_resp = session.get(list_url)
                if list_resp.status_code == 429:
                    logger.warning(f"[{city_name}] 429请求频繁，等待10秒...")
                    time.sleep(10)
                    continue
                list_resp.raise_for_status()
                list_soup = BeautifulSoup(list_resp.text, "lxml")
                communities = parse_list_page(list_soup)
                if communities:  # 成功解析到小区链接
                    break
                else:
                    logger.warning(f"[{city_name}] 第{page}页解析无结果，可能页面结构变化或暂时无数据，准备重试...")
            except Exception as e:
                logger.error(f"[{city_name}] 第{page}页列表爬取失败：{str(e)}")
            # 重试前等待，采用指数退避 + 随机抖动
            retry_count += 1
            if retry_count < LIST_PAGE_RETRY_TIMES:
                delay = LIST_PAGE_RETRY_DELAY * (2 ** (retry_count - 1)) + random.uniform(0, 1)
                logger.info(f"[{city_name}] 等待 {delay:.2f} 秒后重试...")
                time.sleep(delay)
        # 如果重试后仍无结果，认为该页无数据，终止当前城市爬取
        if not communities:
            logger.info(f"[{city_name}] 第{page}页多次重试后仍无小区，终止爬取")
            break
        # 遍历当前页的每个小区链接，提取详情数据
        for community in communities:
            if collected >= limit:
                break
            # 从列表页提取基本信息
            comm_name = safe_get_text(community, "div.li-title")
            comm_price = safe_get_text(community, "div.community-price")
            comm_address = safe_get_text(community, "div.props")
            comm_link = community.get("href", "")
            if not comm_link or not comm_name:
                logger.debug(f"[{city_name}] 小区信息不完整，跳过")
                continue
            # 随机延迟，避免请求过快
            time.sleep(get_random_delay())
            # 请求详情页
            try:
                detail_resp = session.get(comm_link)
                detail_resp.raise_for_status()
            except Exception as e:
                logger.warning(f"[{city_name}] 小区「{comm_name}」详情爬取失败：{str(e)}")
                continue
            # 解析详情页
            detail_soup = BeautifulSoup(detail_resp.text, "lxml")
            details, extra_info, sale_info, rent_info = parse_detail_page(detail_soup)
            # 组装一行数据，顺序必须与 CSV_HEADERS 一致
            row = [
                city_name, comm_name, comm_price, comm_address, comm_link,
                *details,
                extra_info['停车费'], extra_info['车位管理费'],
                extra_info['物业公司'], extra_info['小区地址'],
                extra_info['开发商'], sale_info, rent_info
            ]
            # 验证数据长度是否正确
            if len(row) == len(CSV_HEADERS):
                city_data.append(row)
                collected += 1
                logger.info(f"[{city_name}] 已爬取 {collected}/{limit} 个小区：{comm_name}")
            else:
                logger.warning(f"[{city_name}] 小区「{comm_name}」数据长度异常，跳过")

            time.sleep(get_random_delay())  # 再次延迟，避免连续请求
        page += 1
        time.sleep(random.uniform(2, 5))  # 翻页后等待较长时间
    logger.info(f"[{city_name}] 爬取完成，共获取 {len(city_data)} 条有效数据")

    return city_data
