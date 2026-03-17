"""
通用工具函数模块
================================================
提供日志配置、安全文本提取、目录创建、数据清洗等常用功能，
供其他模块调用，减少代码重复。
"""

import os
import logging

# 配置日志：同时输出到控制台和文件（data/crawl_log.log）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{os.path.dirname(__file__)}/data/crawl_log.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def safe_get_text(element, selector, default='N/A'):
    """
    从BeautifulSoup元素中安全地提取指定CSS选择器的文本内容。
    如果元素不存在或选择器未匹配到任何内容，返回默认值。
    提取后的文本会去除两端空白及换行符。
    :param element: bs4.Tag - 要搜索的父元素
    :param selector: str - CSS选择器
    :param default: str - 默认返回值
    :return: str - 提取并清洗后的文本，若未找到则返回默认值
    """
    if not element:
        return default
    target = element.select_one(selector)
    if not target:
        return default
    # 移除常见的空白字符
    text = target.get_text(strip=True).replace('\n', '').replace('\t', '').replace('\r', '')
    return text if text else default


def ensure_dir_exists(dir_path):
    """
    确保指定目录存在，如果不存在则创建。
    同时会测试目录是否可写，通过创建一个临时文件来验证。
    :param dir_path: str - 目录路径
    :return: bool - 目录存在且可写返回True，否则返回False
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
        # 测试写入权限
        test_file = os.path.join(dir_path, 'test_write.tmp')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('test')
        os.remove(test_file)
        logger.info(f"目录检查通过：{dir_path}")
        return True
    except Exception as e:
        logger.error(f"目录操作失败：{dir_path} | 错误：{str(e)}")
        return False


def clean_csv_data(data):
    """
    清洗数据列表，移除可能导致CSV格式错乱的特殊字符。
    具体操作：
        - 将每个元素转换为字符串
        - 将英文逗号替换为中文逗号，避免列分隔符混淆
        - 将英文双引号替换为两个双引号，符合CSV转义规则
    :param data: list - 原始数据列表
    :return: list - 清洗后的字符串列表
    """
    if not isinstance(data, list):
        return []
    cleaned = []
    for item in data:
        if not item:
            continue
        str_item = str(item).replace(',', '，').replace('"', '""')
        cleaned.append(str_item)
    return cleaned
