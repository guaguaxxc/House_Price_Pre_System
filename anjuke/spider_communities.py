import time
import random
from bs4 import BeautifulSoup
from config import BASE_URL_TEMPLATE, PER_CITY_LIMIT, get_random_delay, CSV_HEADERS, LIST_PAGE_RETRY_TIMES, \
    LIST_PAGE_RETRY_DELAY
from session import create_session
from page_parser import parse_list_page, parse_detail_page
from utils import logger, safe_get_text


def crawl_city(city_name, city_pinyin, limit=PER_CITY_LIMIT):
    session = create_session()
    city_data = []
    collected = 0
    page = 1

    logger.info(f"开始爬取城市：{city_name}（拼音：{city_pinyin}），上限：{limit}条")

    while collected < limit:
        list_url = BASE_URL_TEMPLATE.format(city=city_pinyin, page=page)
        communities = None
        retry_count = 0

        # 列表页重试循环
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

                if communities:  # 成功获取到小区列表
                    break
                else:
                    logger.warning(f"[{city_name}] 第{page}页解析无结果，可能页面结构变化或暂时无数据，准备重试...")
            except Exception as e:
                logger.error(f"[{city_name}] 第{page}页列表爬取失败：{str(e)}")

            # 重试前等待（指数退避）
            retry_count += 1
            if retry_count < LIST_PAGE_RETRY_TIMES:
                delay = LIST_PAGE_RETRY_DELAY * (2 ** (retry_count - 1)) + random.uniform(0, 1)
                logger.info(f"[{city_name}] 等待 {delay:.2f} 秒后重试...")
                time.sleep(delay)

        # 经过重试后仍无结果，认为该页无数据，终止该城市爬取
        if not communities:
            logger.info(f"[{city_name}] 第{page}页多次重试后仍无小区，终止爬取")
            break

        # 处理当前页的小区详情（原有逻辑不变）
        for community in communities:
            if collected >= limit:
                break

            # 提取列表页基础信息
            comm_name = safe_get_text(community, "div.li-title")
            comm_price = safe_get_text(community, "div.community-price")
            comm_address = safe_get_text(community, "div.props")
            comm_link = community.get("href", "")

            if not comm_link or not comm_name:
                logger.debug(f"[{city_name}] 小区信息不完整，跳过")
                continue

            time.sleep(get_random_delay())
            try:
                detail_resp = session.get(comm_link)
                detail_resp.raise_for_status()
            except Exception as e:
                logger.warning(f"[{city_name}] 小区「{comm_name}」详情爬取失败：{str(e)}")
                continue

            detail_soup = BeautifulSoup(detail_resp.text, "lxml")
            details, extra_info, sale_info, rent_info = parse_detail_page(detail_soup)

            row = [
                city_name, comm_name, comm_price, comm_address, comm_link,
                *details,
                extra_info['停车费'], extra_info['车位管理费'],
                extra_info['物业公司'], extra_info['小区地址'],
                extra_info['开发商'], sale_info, rent_info
            ]

            if len(row) == len(CSV_HEADERS):
                city_data.append(row)
                collected += 1
                logger.info(f"[{city_name}] 已爬取 {collected}/{limit} 个小区：{comm_name}")
            else:
                logger.warning(f"[{city_name}] 小区「{comm_name}」数据长度异常，跳过")

            time.sleep(get_random_delay())

        page += 1
        time.sleep(random.uniform(2, 5))  # 翻页延迟

    logger.info(f"[{city_name}] 爬取完成，共获取 {len(city_data)} 条有效数据")
    return city_data
