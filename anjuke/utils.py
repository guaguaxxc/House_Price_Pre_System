"""
通用工具函数模块
=================
提供安全文本提取、路径创建、日志输出等通用功能
"""
import os
import logging

# 配置日志
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
    安全提取HTML元素文本（避免None异常）
    :param element: bs4.Tag对象
    :param selector: CSS选择器
    :param default: 默认值
    :return: 清洗后的文本
    """
    if not element:
        return default
    target = element.select_one(selector)
    if not target:
        return default
    # 清洗文本（移除特殊字符、空白符）
    text = target.get_text(strip=True).replace('\n', '').replace('\t', '').replace('\r', '')
    return text if text else default


def ensure_dir_exists(dir_path):
    """
    确保目录存在，不存在则创建（含权限检查）
    :param dir_path: 目录路径
    :return: bool - 是否创建/存在
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
        # 验证可写性
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
    清洗CSV数据（避免列错乱、特殊字符问题）
    :param data: 原始数据列表
    :return: 清洗后的数据
    """
    if not isinstance(data, list):
        return []
    cleaned = []
    for item in data:
        if not item:
            continue
        # 转换为字符串+替换CSV分隔符
        str_item = str(item).replace(',', '，').replace('"', '""')
        cleaned.append(str_item)
    return cleaned
