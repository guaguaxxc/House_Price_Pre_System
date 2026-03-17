"""
页面解析模块
=================
解析小区列表页/详情页，提取结构化数据
"""
from utils import safe_get_text, clean_csv_data


def parse_list_page(soup):
    """
    解析小区列表页，提取所有小区<a>标签
    :param soup: BeautifulSoup对象
    :return: list[bs4.Tag] - 小区标签列表
    """
    # 增强选择器（适配页面结构变化）
    community_tags = soup.find_all('a', class_=['li-row', 'community-item'])
    if not community_tags:
        community_tags = soup.select('div.community-list > a')
    return community_tags


def parse_detail_page(soup):
    """
    解析小区详情页，提取结构化数据
    :param soup: BeautifulSoup对象
    :return: tuple - (核心字段列表, 额外信息字典, 在售房源, 在租房源)
    """
    # 1. 提取14个核心字段（适配不同页面结构）
    details = []
    for i in range(14):
        # 多选择器容错
        value = safe_get_text(soup, f'div.value.value_{i}')
        if value == 'N/A':
            value = safe_get_text(soup, f'div.info-item:nth-child({i + 1}) > div.value')
        details.append(value)

    # 2. 提取额外信息（停车费、物业公司等）
    extra_info = {
        '停车费': 'N/A',
        '车位管理费': 'N/A',
        '物业公司': 'N/A',
        '小区地址': 'N/A',
        '开发商': 'N/A'
    }

    # 多维度解析（适配不同页面布局）
    info_columns = soup.find_all('div', class_=['column-1', 'info-column'])
    for column in info_columns:
        label = safe_get_text(column, 'div.label')
        value = safe_get_text(column, 'div.value')
        for key in extra_info:
            if key in label or label in key:
                extra_info[key] = value

    # 3. 提取在售/在租房源
    sale_tag = soup.find('div', class_='sale') or soup.find('span', class_='sale-count')
    rent_tag = soup.find('div', class_='rent') or soup.find('span', class_='rent-count')

    sale_info = 'N/A'
    if sale_tag:
        num = safe_get_text(sale_tag, 'i.source-number') or safe_get_text(sale_tag, 'span.number')
        unit = safe_get_text(sale_tag, 'i.source-unit') or '套'
        sale_info = f"{num} {unit}" if num else 'N/A'

    rent_info = 'N/A'
    if rent_tag:
        num = safe_get_text(rent_tag, 'i.source-number') or safe_get_text(rent_tag, 'span.number')
        unit = safe_get_text(rent_tag, 'i.source-unit') or '套'
        rent_info = f"{num} {unit}" if num else 'N/A'

    # 清洗数据
    details = clean_csv_data(details)
    extra_info = {k: clean_csv_data([v])[0] for k, v in extra_info.items()}
    sale_info = clean_csv_data([sale_info])[0]
    rent_info = clean_csv_data([rent_info])[0]

    return details, extra_info, sale_info, rent_info
