"""
爬虫主程序（毕设-安居客爬虫）
=================
核心功能：断点续爬、紧急保存、进度管理、数据写入
"""
import csv
import os
import sys
import signal
from spider_city import crawl_and_save_city_csv
from spider_communities import crawl_city
from config import (
    CITY_CSV_PATH, FINAL_CSV_PATH, PROGRESS_CSV_PATH,
    PROGRESS_HEADERS, DEFAULT_START_INDEX, CSV_ENCODING, CSV_HEADERS
)
from utils import logger, ensure_dir_exists, clean_csv_data

# 全局变量：临时未保存数据
TEMP_UNSAVED_DATA = []


def signal_handler(signum, frame):
    """捕获Ctrl+C，紧急保存临时数据"""
    logger.warning("\n检测到手动中断（Ctrl+C），开始紧急保存...")
    global TEMP_UNSAVED_DATA

    if TEMP_UNSAVED_DATA:
        success = write_community_csv(TEMP_UNSAVED_DATA, emergency=True)
        if success:
            logger.info(f"✅ 紧急保存完成：{len(TEMP_UNSAVED_DATA)} 条数据")
        else:
            logger.error(f"❌ 紧急保存失败：{len(TEMP_UNSAVED_DATA)} 条数据丢失")
        TEMP_UNSAVED_DATA = []
    else:
        logger.info("暂无未保存的临时数据")

    sys.exit(0)


# 注册中断信号处理
signal.signal(signal.SIGINT, signal_handler)


def save_progress(last_index, crawled_list, failed_dict):
    """保存爬取进度到CSV"""
    # 确保目录存在
    if not ensure_dir_exists(os.path.dirname(PROGRESS_CSV_PATH)):
        return False

    # 数据格式化
    try:
        crawled_str = ",".join(map(str, crawled_list)) if crawled_list else ""
        failed_items = []
        for idx, name in failed_dict.items():
            clean_name = name.replace(",", "，").replace(":", "：")
            failed_items.append(f"{idx}:{clean_name}")
        failed_str = ",".join(failed_items) if failed_items else ""
    except Exception as e:
        logger.error(f"进度数据格式化失败：{str(e)}")
        return False

    # 写入进度
    try:
        with open(PROGRESS_CSV_PATH, "w", newline="", encoding=CSV_ENCODING) as f:
            writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(PROGRESS_HEADERS)
            writer.writerow([last_index, crawled_str, failed_str])
        logger.info(f"进度已保存：最后爬取索引 {last_index}")
        return True
    except Exception as e:
        logger.error(f"保存进度失败：{str(e)}")
        return False


def load_progress():
    """加载爬取进度"""
    init_progress = {
        "last_crawled_index": DEFAULT_START_INDEX,
        "crawled_cities": [],
        "failed_cities": {}
    }

    if not os.path.exists(PROGRESS_CSV_PATH):
        logger.info("进度文件不存在，使用默认起始索引")
        return init_progress

    try:
        with open(PROGRESS_CSV_PATH, "r", encoding=CSV_ENCODING) as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != PROGRESS_HEADERS:
                raise ValueError("进度CSV表头不匹配")
            rows = list(reader)
            if not rows:
                raise ValueError("进度CSV无数据")

            row = rows[0]
            # 解析数据
            last_index = int(row["last_crawled_index"].strip()) if row[
                "last_crawled_index"].strip() else DEFAULT_START_INDEX
            crawled_list = [int(i) for i in row["crawled_cities"].strip().split(",") if i.strip().isdigit()]
            failed_dict = {}
            for item in row["failed_cities"].strip().split(","):
                if ":" in item:
                    idx_str, name = item.split(":", 1)
                    if idx_str.strip().isdigit():
                        failed_dict[int(idx_str.strip())] = name.strip()

            logger.info(f"加载进度成功：最后索引 {last_index}，已爬 {len(crawled_list)} 城，失败 {len(failed_dict)} 城")
            return {
                "last_crawled_index": last_index,
                "crawled_cities": crawled_list,
                "failed_cities": failed_dict
            }
    except Exception as e:
        logger.error(f"加载进度失败，使用默认配置：{str(e)}")
        return init_progress


def write_community_csv(data, emergency=False):
    """写入小区数据到CSV"""
    if not data:
        logger.info("无数据需要写入")
        return True

    # 确保目录存在
    if not ensure_dir_exists(os.path.dirname(FINAL_CSV_PATH)):
        return False

    # 数据清洗
    clean_data = []
    for row in data:
        clean_row = clean_csv_data(row)
        if len(clean_row) == len(CSV_HEADERS):
            clean_data.append(clean_row)
        else:
            logger.warning(f"数据行长度异常，跳过：{clean_row[:3]}...")

    # 写入CSV
    try:
        file_exists = os.path.isfile(FINAL_CSV_PATH)
        with open(FINAL_CSV_PATH, "a", newline="", encoding=CSV_ENCODING) as f:
            writer = csv.writer(
                f,
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_ALL,
                escapechar='\\'
            )
            # 首次写入表头
            if not file_exists:
                writer.writerow(clean_csv_data(CSV_HEADERS))
                logger.info("首次创建CSV文件，写入表头")
            # 写入数据
            writer.writerows(clean_data)

        log_prefix = "紧急保存" if emergency else "常规写入"
        logger.info(f"{log_prefix}完成：{len(clean_data)} 条数据 → {FINAL_CSV_PATH}")
        return True
    except PermissionError:
        logger.error(f"权限错误：无法写入 {FINAL_CSV_PATH}（文件可能被Excel打开）")
        return False
    except Exception as e:
        logger.error(f"写入CSV失败：{str(e)}")
        return False


def main(force_reload_city=False):
    """主函数"""
    global TEMP_UNSAVED_DATA
    TEMP_UNSAVED_DATA = []

    # 1. 爬取城市列表
    try:
        cities = crawl_and_save_city_csv(force_reload=force_reload_city)
        if not cities:
            logger.error("城市列表为空，终止程序")
            return
    except RuntimeError as e:
        logger.error(f"城市列表爬取失败：{str(e)}")
        return

    # 2. 读取城市列表
    try:
        with open(CITY_CSV_PATH, "r", encoding=CSV_ENCODING) as f:
            cities = list(csv.DictReader(f))
        total_cities = len(cities)
        logger.info(f"读取城市列表成功：共 {total_cities} 个城市")
    except Exception as e:
        logger.error(f"读取城市列表失败：{str(e)}")
        return

    # 3. 加载进度
    progress = load_progress()
    last_idx = progress["last_crawled_index"]
    crawled_cities = progress["crawled_cities"]
    failed_cities = progress["failed_cities"]

    # 检查是否已爬完
    if last_idx >= total_cities:
        logger.info(f"所有城市已爬取完成（最后索引 {last_idx}，总城市 {total_cities}）")
        return

    # 4. 开始爬取
    target_cities = cities[last_idx:]
    logger.info(f"本次爬取计划：从第 {last_idx + 1} 个城市开始，共 {len(target_cities)} 个城市")

    current_idx = last_idx
    for city in target_cities:
        city_name = city["city_name"]
        city_pinyin = city["city_pinyin"]

        logger.info(f"\n========== 开始爬取：第 {current_idx + 1}/{total_cities} 城 → {city_name} ==========")

        try:
            # 爬取当前城市
            city_data = crawl_city(city_name, city_pinyin)

            if city_data:
                # 临时存储（用于紧急保存）
                TEMP_UNSAVED_DATA.extend(city_data)
                # 写入CSV
                write_success = write_community_csv(city_data)

                if write_success:
                    TEMP_UNSAVED_DATA = []  # 清空已保存数据
                    crawled_cities.append(current_idx)
                    progress["last_crawled_index"] = current_idx
                    progress["crawled_cities"] = crawled_cities
                else:
                    failed_cities[current_idx] = city_name
                    progress["failed_cities"] = failed_cities
            else:
                logger.warning(f"{city_name} 未爬取到任何数据")
        except Exception as e:
            logger.error(f"{city_name} 爬取异常：{str(e)}")
            failed_cities[current_idx] = city_name
            progress["failed_cities"] = failed_cities

        # 保存进度（每次爬完一个城市都保存）
        save_progress(progress["last_crawled_index"], crawled_cities, failed_cities)
        current_idx += 1

    # 5. 兜底保存剩余数据
    if TEMP_UNSAVED_DATA:
        logger.info(f"爬取完成，兜底保存 {len(TEMP_UNSAVED_DATA)} 条临时数据")
        write_community_csv(TEMP_UNSAVED_DATA)

    # 6. 汇总统计
    logger.info("\n========== 爬取汇总 ==========")
    logger.info(f"总城市数：{total_cities}")
    logger.info(f"已爬城市数：{len(crawled_cities)}")
    logger.info(f"失败城市数：{len(failed_cities)}")

    # 统计CSV数据量
    if os.path.exists(FINAL_CSV_PATH):
        try:
            with open(FINAL_CSV_PATH, "r", encoding=CSV_ENCODING) as f:
                total_rows = len(list(csv.reader(f))) - 1  # 减表头
            logger.info(f"CSV总数据量：{total_rows} 条")
            logger.info(f"CSV文件路径：{os.path.abspath(FINAL_CSV_PATH)}")
        except Exception as e:
            logger.error(f"统计CSV数据量失败：{str(e)}")


if __name__ == "__main__":
    # force_reload_city（是否重新爬取城市列表）
    main(force_reload_city=False)
