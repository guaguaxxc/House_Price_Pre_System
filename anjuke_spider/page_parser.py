"""
页面解析模块
================================================
提供从小区列表页和详情页中提取结构化数据的函数。
使用BeautifulSoup进行HTML解析。
"""

from utils import safe_get_text, clean_csv_data


def parse_list_page(soup):
    """
    解析小区列表页，提取所有小区链接的<a>标签。
    :param soup: BeautifulSoup对象，已解析的列表页HTML
    :return: list[bs4.Tag] - 包含所有小区标签的列表，若未找到则返回空列表
    """
    # 尝试通过多个class名称查找小区链接
    community_tags = soup.find_all('a', class_=['li-row', 'community-item'])
    if not community_tags:
        # 如果上述类名未匹配，使用CSS选择器进行更宽泛的查找
        community_tags = soup.select('div.community-list > a')
    return community_tags


def parse_detail_page(soup):
    """
    解析小区详情页，提取核心字段、额外信息以及房源数量。
    :param soup: BeautifulSoup对象，已解析的详情页HTML
    :return: tuple - (核心字段列表, 额外信息字典, 在售房源字符串, 在租房源字符串)
             其中核心字段列表长度为14，额外信息字典包含停车费、物业公司等5个字段，
    """
    # 1. 提取14个核心字段，使用多个选择器增强容错
    details = []
    for i in range(14):
        # 尝试通过类名 'value value_{i}' 提取
        value = safe_get_text(soup, f'div.value.value_{i}')
        if value == 'N/A':
            # 若未找到，尝试通过 'div.info-item:nth-child({i+1}) > div.value' 选择
            value = safe_get_text(soup, f'div.info-item:nth-child({i + 1}) > div.value')
        details.append(value)

    # 2. 提取额外信息，包括停车费、物业公司等5个字段
    extra_info = {
        '停车费': 'N/A',
        '车位管理费': 'N/A',
        '物业公司': 'N/A',
        '小区地址': 'N/A',
        '开发商': 'N/A'
    }

    # 查找页面中的信息列
    info_columns = soup.find_all('div', class_=['column-1', 'info-column'])
    for column in info_columns:
        label = safe_get_text(column, 'div.label')  # 获取标签文本
        value = safe_get_text(column, 'div.value')  # 获取对应值
        for key in extra_info:
            if key in label or label in key:  # 模糊匹配，适应标签变化
                extra_info[key] = value

    # 3. 提取在售和租房源数量
    sale_tag = soup.find('div', class_='sale') or soup.find('span', class_='sale-count')
    rent_tag = soup.find('div', class_='rent') or soup.find('span', class_='rent-count')

    sale_info = 'N/A'

    if sale_tag:
        # 尝试从多种元素中提取数字和单位
        num = safe_get_text(sale_tag, 'i.source-number') or safe_get_text(sale_tag, 'span.number')
        unit = safe_get_text(sale_tag, 'i.source-unit') or '套'
        sale_info = f"{num} {unit}" if num else 'N/A'

    rent_info = 'N/A'
    if rent_tag:
        num = safe_get_text(rent_tag, 'i.source-number') or safe_get_text(rent_tag, 'span.number')
        unit = safe_get_text(rent_tag, 'i.source-unit') or '套'
        rent_info = f"{num} {unit}" if num else 'N/A'

    # 清洗数据，去除可能引起CSV错乱的字符
    details = clean_csv_data(details)
    extra_info = {k: clean_csv_data([v])[0] for k, v in extra_info.items()}
    sale_info = clean_csv_data([sale_info])[0]
    rent_info = clean_csv_data([rent_info])[0]

    return details, extra_info, sale_info, rent_info
