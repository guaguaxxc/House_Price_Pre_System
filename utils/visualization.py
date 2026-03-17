"""
数据可视化工具模块
================================================
提供各种图表所需的数据处理函数，包括：
    - 基础数据获取（小区、历史记录）
    - 首页图表（价格排行、统计数据、雷达图、词云）
    - 图表页面数据（价格分布、散点图、折线图、物业类型树图、绿化率分布、省份/区域统计、详细词云）
    - 历史记录统计（用户历史、最贵预测、最常预测城市、城市饼图）
大部分函数使用缓存装饰器，以减少数据库查询次数，提高响应速度。
"""

from model.Community_info import Community_info
from model.History import History
from model.User import User
from sqlalchemy import distinct, and_, or_
from collections import defaultdict, Counter
import re
from extensions import cache, db
from .map_transform import CITY_TO_PROVINCE, PROVINCE_TO_REGION, standardize_province_name
import jieba


# ================= 基础数据获取函数 =================
def get_all_db_data():
    """
    从数据库获取所有小区记录的 ORM 对象列表。
    :return: list[Community_info] - 所有小区对象
    """
    return Community_info.query.all()


def fuzzy_match_data(search_word, data_list):
    """
    对已加载的数据列表进行模糊匹配（基于城市、小区名称、地址）。
    :param search_word: str - 搜索关键词
    :param data_list: list - 待过滤的数据对象列表
    :return: list - 过滤后的数据列表
    """
    if not search_word:
        return data_list
    search_word = search_word.lower()
    return [c for c in data_list if
            (c.city and search_word in c.city.lower()) or
            (c.community_name and search_word in c.community_name.lower()) or
            (c.community_address and search_word in c.community_address.lower())]


def get_data_by_id(id):
    """
    根据主键ID获取单个小区记录。
    :param id: int - 小区ID
    :return: Community_info - 对应的小区对象，若不存在返回None
    """
    return Community_info.query.get(id)


def insert_history_record(city, price, user_id):
    """
    向历史记录表中插入一条预测记录。
    :param city: str - 预测的城市
    :param price: str - 预测结果价格（带单位）
    :param user_id: int - 执行预测的用户ID
    :return: bool - 插入成功返回True，否则返回False
    """
    history = History(city=city, price=price, user_id=user_id)
    try:
        db.session.add(history)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] 插入历史记录失败：{e}")
        return False


# ================= 辅助函数 =================
def extract_numeric(value):
    """
    从字符串中提取第一个数值（浮点数），用于图表数据计算。
    :param value: 输入值（字符串或None）
    :return: float 或 None - 提取到的数值，若无效则返回None
    """
    if not value or not isinstance(value, str):
        return None
    match = re.search(r'(\d+\.?\d*)', value)
    return float(match.group(1)) if match else None


# ================= 清除缓存函数 =================
def clear_chart_cache():
    """
    清除所有图表相关的缓存。在数据被修改（如添加、编辑、删除小区）后调用，
    以确保下次访问图表时能获取最新数据。
    """
    cache.delete_memoized(process_price_chart_data)
    cache.delete_memoized(process_summary_data)
    cache.delete_memoized(process_radar_sale_data)
    cache.delete_memoized(process_wordcloud_data)
    cache.delete_memoized(get_city_list)
    cache.delete_memoized(get_city_price_xy)
    cache.delete_memoized(get_city_price_greening_scatter)
    cache.delete_memoized(get_city_completion_price_line)
    cache.delete_memoized(get_property_type_dict)
    cache.delete_memoized(get_greening_area_chart_data)
    cache.delete_memoized(get_province_house_data)
    cache.delete_memoized(get_region_house_data)
    cache.delete_memoized(get_wordcloud_data)


# ================= 缓存装饰器 =================
def cached(timeout=31536000, key_prefix=None):
    """
    自定义缓存装饰器，简化 cache.cached 的调用。
    默认超时时间为一年（31536000秒），适用于不经常变化的数据。
    :param timeout: int - 缓存超时时间（秒）
    :param key_prefix: str - 缓存键前缀，若不指定则自动生成
    :return: 装饰后的函数
    """
    if key_prefix is not None:
        return cache.cached(timeout=timeout, key_prefix=key_prefix)
    else:
        return cache.cached(timeout=timeout)


# ================= 首页图表 =================
@cached(timeout=31536000, key_prefix='price_chart')
def process_price_chart_data():
    """
    处理价格排行榜前10的小区数据，用于首页柱状图。
    筛选出价格非空且包含数字的小区，提取数值后按价格降序排列，取前10名。
    :return: dict - 包含 xAxis（小区名称列表）和 series（价格列表）的字典
    """
    # 查询价格不为空且包含数字的小区
    communities = Community_info.query.filter(
        Community_info.price.isnot(None),
        Community_info.price != '暂无',
        Community_info.price.op('regexp')('[0-9]+')
    ).all()

    data = []
    for c in communities:
        price = extract_numeric(c.price)
        if price:
            city = c.city or ''
            comm_name = c.community_name or ''
            # 去除名称中可能包含的广告字样
            comm_name_clean = comm_name.replace('数据由万科物业提供', '')
            data.append({
                'name': f"{city}-{comm_name_clean}",
                'price': price
            })

    # 按价格降序排序
    data.sort(key=lambda x: x['price'], reverse=True)
    top10 = data[:10]

    return {
        'xAxis': [d['name'] for d in top10],
        'series': [d['price'] for d in top10],
        'status': 'success' if top10 else 'warning',
        'msg': ''
    }


@cached(timeout=31536000, key_prefix='summary')
def process_summary_data():
    """
    处理首页的统计摘要数据，包括：
        - 小区总数
        - 最高单价
        - 物业类型数量（去重）
        - 平均在售房源数

    :return: dict - 包含上述四个指标的字典
    """
    # 小区总数（小区名称不为空）
    total_count = Community_info.query.filter(Community_info.community_name.isnot(None)).count()

    # 最高单价
    max_price = 0
    for c in Community_info.query.filter(Community_info.price.isnot(None)):
        p = extract_numeric(c.price)
        if p and p > max_price:
            max_price = p

    # 物业类型数量（去重，考虑可能用“|”分隔的多个类型）
    property_types = set()
    for c in Community_info.query.filter(
            and_(Community_info.property_type.isnot(None),
                 Community_info.property_type != '暂无')
    ):
        types = c.property_type.split('|')
        property_types.update(t.strip() for t in types if t.strip())

    # 平均在售房源数
    sale_values = []
    for c in Community_info.query.filter(Community_info.sale_houses.isnot(None)):
        s = extract_numeric(c.sale_houses)
        if s:
            sale_values.append(s)
    avg_sale = round(sum(sale_values) / len(sale_values)) if sale_values else 0

    return {
        'total_count': total_count,
        'max_price': max_price,
        'property_type_count': len(property_types),
        'avg_sale_houses': avg_sale
    }


@cached(timeout=31536000, key_prefix='radar_sale')
def process_radar_sale_data():
    """
    处理在售房源城市排名前10的雷达图数据。
    :return: dict - 包含雷达图指标（indicator）和对应数据（data）的字典
    """
    # 按城市汇总在售房源总数
    city_sale = defaultdict(int)
    for c in Community_info.query.filter(
            Community_info.sale_houses.isnot(None),
            Community_info.sale_houses != '暂无'
    ):
        s = extract_numeric(c.sale_houses)
        if s:
            city_sale[c.city] += s

    # 取前10个城市
    sorted_items = sorted(city_sale.items(), key=lambda x: x[1], reverse=True)[:10]

    # 若无数据，返回默认示例
    if not sorted_items:
        return {
            'indicator': [{'name': '北京', 'max': 1000}, {'name': '上海', 'max': 1000}],
            'data': [850, 780],
            'max_value': 1000
        }

    cities, sales = zip(*sorted_items)
    max_sale = max(sales)
    indicator = [{'name': c, 'max': max_sale} for c in cities]

    return {
        'indicator': indicator,
        'data': list(sales),
        'max_value': max_sale
    }


@cached(timeout=31536000, key_prefix='wordcloud')
def process_wordcloud_data():
    """
    处理首页地址词云数据（基于小区地址的出现频次）。
    :return: dict - 包含 words 列表的字典，每个元素为 {'name': 地址, 'value': 频次}
    """
    address_counter = Counter()
    for c in Community_info.query.filter(
            or_(Community_info.community_address.isnot(None),
                Community_info.address.isnot(None))
    ):
        addr = c.community_address or c.address
        if addr and addr.strip() not in ('', '暂无', '未知'):
            addr_clean = addr.strip().lower().replace('　', ' ')
            if addr_clean not in ('', '暂无', '未知', 'n/a'):
                address_counter[addr] += 1

    words = [{'name': addr, 'value': cnt} for addr, cnt in address_counter.most_common(50)]
    if not words:
        words = [{'name': '测试小区', 'value': 10}]

    return {'words': words}


# ================= 图表页面数据 =================
@cached(timeout=31536000, key_prefix='city_list')
def get_city_list():
    """
    获取所有出现过的城市名称（去重），用于下拉框选择。
    :return: list[str] - 城市名称列表
    """
    cities = db.session.query(distinct(Community_info.city)).filter(Community_info.city.isnot(None)).all()
    return [c[0] for c in cities] if cities else []


def get_city_price_xy(city):
    """
    获取指定城市的价格区间分布数据（柱状图）。
    :param city: str - 城市名称
    :return: (labels, counts) - 区间标签列表和对应的小区数量列表
    """
    # 定义价格区间（单位：元/㎡）
    intervals = [(0, 1000), (1000, 2000), (2000, 3000), (3000, 4000), (4000, 5000),
                 (5000, 6000), (6000, 7000), (7000, 8000), (8000, 9000), (9000, None)]

    counts = [0] * len(intervals)
    for c in Community_info.query.filter_by(city=city).filter(Community_info.price.isnot(None)):
        p = extract_numeric(c.price)
        if p:
            for i, (low, high) in enumerate(intervals):
                if high is None:
                    if p >= low:
                        counts[i] += 1
                        break
                elif low <= p < high:
                    counts[i] += 1
                    break

    labels = [f"{low}-{high}元/m²" if high else f"{low}元以上" for low, high in intervals]
    return labels, counts


def get_city_price_greening_scatter(city, return_type='labeled'):
    """
    获取指定城市的单价-绿化率散点图数据。
    :param city: str - 城市名称
    :param return_type: str - 返回数据格式，'simple'返回[[价格,绿化率],...]，
                       'labeled'返回[{'name':小区名,'value':[价格,绿化率]},...]
    :return: dict - 包含散点数据(scatter_data)和坐标轴范围(axis_range)的字典
    """
    scatter = []
    for c in Community_info.query.filter_by(city=city).filter(
            Community_info.price.isnot(None),
            Community_info.greening_rate.isnot(None),
            Community_info.greening_rate != '暂无'
    ):
        price = extract_numeric(c.price)
        greening = extract_numeric(c.greening_rate)
        if price and greening:
            name = c.community_name or f'小区{len(scatter)}'
            if return_type == 'simple':
                scatter.append([price, greening])
            else:
                scatter.append({
                    'name': name,
                    'value': [price, greening]
                })

    # 计算坐标轴范围，增加10%的边距
    if scatter:
        if return_type == 'simple':
            x_vals = [s[0] for s in scatter]
            y_vals = [s[1] for s in scatter]
        else:
            x_vals = [s['value'][0] for s in scatter]
            y_vals = [s['value'][1] for s in scatter]

        x_min, x_max = min(x_vals), max(x_vals)
        y_min, y_max = min(y_vals), max(y_vals)
        x_buffer = (x_max - x_min) * 0.1 or 1000
        y_buffer = (y_max - y_min) * 0.05 or 2
    else:
        x_min, x_max, x_buffer = 0, 50000, 1000
        y_min, y_max, y_buffer = 0, 50, 2

    return {
        'scatter_data': scatter,
        'axis_range': {
            'x_range': [int(x_min - x_buffer), int(x_max + x_buffer)],
            'y_range': [int(y_min - y_buffer), int(y_max + y_buffer)]
        }
    }


def get_city_completion_price_line(city):
    """
    获取指定城市的竣工年份-平均价格折线图数据。
    :param city: str - 城市名称
    :return: dict - 包含x轴（年份列表）和y轴（平均价格列表）的字典
    """
    year_prices = defaultdict(list)
    for c in Community_info.query.filter_by(city=city).filter(
            Community_info.completion_time.isnot(None),
            Community_info.price.isnot(None)
    ):
        year_match = re.search(r'\d{4}', str(c.completion_time))
        if year_match:
            year = int(year_match.group())
            price = extract_numeric(c.price)
            if price:
                year_prices[year].append(price)

    sorted_years = sorted(year_prices.keys())
    y_axis = [round(sum(year_prices[y]) / len(year_prices[y]), 2) for y in sorted_years]

    return {'x_axis': sorted_years, 'y_axis': y_axis}


@cached(timeout=31536000, key_prefix='property_type_dict')
def get_property_type_dict():
    """
    获取物业类型分布树图数据。
    :return: dict - 符合ECharts树图格式的字典，包含根节点名称和子节点列表
    """
    # 预定义的目标类型（用于归类）
    target = ["仓储", "住宅", "公寓", "其他", "别墅", "商业", "商住楼", "联列住宅", "自建房", "酒店"]
    counter = Counter({t: 0 for t in target})

    for c in Community_info.query.filter(Community_info.property_type.isnot(None)):
        pt = c.property_type.strip()
        matched = False
        for t in target:
            if t in pt:
                counter[t] += 1
                matched = True
                break
        if not matched:
            counter['其他'] += 1

    return {
        'name': '物业类型总览',
        'children': [{'name': t, 'value': counter[t]} for t in target]
    }


@cached(timeout=31536000, key_prefix='greening_area_chart')
def get_greening_area_chart_data():
    """
    获取绿化率分布面积图数据（按10%间隔统计小区数量）。
    :return: (intervals, counts) - 区间标签列表和对应的小区数量列表
    """
    intervals = ['0-10%', '10-20%', '20-30%', '30-40%', '40-50%',
                 '50-60%', '60-70%', '70-80%', '80-90%', '90-100%']
    counts = [0] * 10

    for c in Community_info.query.filter(Community_info.greening_rate.isnot(None)):
        g = extract_numeric(c.greening_rate)
        if g and 0 <= g <= 100:
            idx = int(g // 10)
            if idx >= 10:
                idx = 9
            counts[idx] += 1

    return intervals, counts


@cached(timeout=31536000, key_prefix='province_house_data')
def get_province_house_data():
    """
    获取各省份的平均房价和在售房源总数，用于地图展示。
    :return: (price_data, sale_data)
             price_data: list[dict] - 每个元素为 {'name':省份简称, 'value':平均价格}
             sale_data: list[dict] - 每个元素为 {'name':省份简称, 'value':在售房源总数}
    """
    province_price = defaultdict(list)
    province_sale = defaultdict(int)

    for c in Community_info.query.filter(Community_info.city.isnot(None)):
        city = c.city
        province = CITY_TO_PROVINCE.get(city)
        if not province:
            continue

        if c.price:
            p = extract_numeric(c.price)
            if p:
                province_price[province].append(p)

        if c.sale_houses:
            s = extract_numeric(c.sale_houses)
            if s:
                province_sale[province] += s

    # 处理省份名称（移除“省”、“市”等后缀）并计算平均价格
    price_data = [{'name': p.replace('省', '').replace('市', ''), 'value': round(sum(vals) / len(vals), 0)}
                  for p, vals in province_price.items() if vals]

    sale_data = [{'name': p.replace('省', '').replace('市', ''), 'value': province_sale[p]}
                 for p in province_sale]

    return price_data, sale_data


@cached(timeout=31536000, key_prefix='region_house_data')
def get_region_house_data():
    """
    获取各大区（东北、华北、华东等）的在售和在租房源总数，用于柱状图。
    :return: (regions, sale_data, rent_data)
             regions: list[str] - 大区名称列表
             sale_data: list[int] - 对应大区的在售房源总数
             rent_data: list[int] - 对应大区的在租房源总数
    """
    region_stats = defaultdict(lambda: {'sale': 0, 'rent': 0})
    regions = ["东北", "华北", "华东", "华中", "华南", "西南", "西北"]

    for c in Community_info.query.filter(Community_info.city.isnot(None)):
        city = c.city
        province_suffix = CITY_TO_PROVINCE.get(city)
        if not province_suffix:
            continue

        province = standardize_province_name(province_suffix)
        region = PROVINCE_TO_REGION.get(province)
        if not region:
            continue

        if c.sale_houses:
            s = extract_numeric(c.sale_houses)
            if s:
                region_stats[region]['sale'] += s
        if c.rent_houses:
            r = extract_numeric(c.rent_houses)
            if r:
                region_stats[region]['rent'] += r

    sale_data = [region_stats[r]['sale'] for r in regions]
    rent_data = [region_stats[r]['rent'] for r in regions]

    return regions, sale_data, rent_data


@cached(timeout=31536000, key_prefix='wordcloud_data_detail')
def get_wordcloud_data():
    """
    获取小区名称和物业公司名称的分词词云数据。
    :return: (comm_cloud, prop_cloud)
             comm_cloud: list[dict] - 小区名称词云，每个元素为 {'name':词, 'value':频次}
             prop_cloud: list[dict] - 物业公司词云
    """
    comm_counter = Counter()
    prop_counter = Counter()

    # 定义停用词，过滤掉无意义的词
    STOP_WORDS = {"暂无", "小区", "花园", "大厦", "公寓", "住宅", "别墅", "商铺", "写字楼", "的", "和", "与", "及",
                  "园", "苑", "里"}

    for c in Community_info.query.filter(
            Community_info.community_name.isnot(None),
            Community_info.property_company.isnot(None)
    ):
        # 小区名词云
        if c.community_name:
            words = jieba.lcut(c.community_name)
            for w in words:
                if w not in STOP_WORDS and len(w) >= 2:
                    comm_counter[w] += 1

        # 物业公司词云
        if c.property_company:
            words = jieba.lcut(c.property_company)
            for w in words:
                if w not in STOP_WORDS and len(w) >= 2:
                    prop_counter[w] += 1

    comm = [{'name': k, 'value': v} for k, v in comm_counter.most_common(200) if v >= 2]
    prop = [{'name': k, 'value': v} for k, v in prop_counter.most_common(200) if v >= 2]

    return comm, prop


# ================= 历史记录统计 =================
def get_history_by_username(username):
    """
    根据用户名获取该用户的预测历史记录。
    :param username: str - 用户名
    :return: (count, history_list)
             count: int - 历史记录总数
             history_list: list[dict] - 每条记录包含 id, city, price
    """
    user = User.query.filter_by(user_name=username).first()
    if not user:
        return 0, []

    histories = History.query.filter_by(user_id=user.user_id).order_by(History.id.desc()).all()
    return len(histories), [{'id': h.id, 'city': h.city, 'price': h.price} for h in histories]


def get_history_max_price():
    """
    获取所有历史预测中的最高价格及对应记录。
    :return: (max_price, max_record)
             max_price: float - 最高价格数值
             max_record: dict - 对应记录的 id, city, price
    """
    histories = History.query.filter(History.price.isnot(None)).all()
    max_price = None
    max_record = None
    for h in histories:
        p = extract_numeric(h.price)
        if p and (max_price is None or p > max_price):
            max_price = p
            max_record = {'id': h.id, 'city': h.city, 'price': h.price}
    return max_price, max_record


def get_history_most_frequent_city():
    """
    统计历史预测中出现最频繁的城市及其次数。
    :return: (most_city, most_count, city_counter)
             most_city: str - 出现次数最多的城市
             most_count: int - 该城市出现次数
             city_counter: dict - 所有城市的出现次数统计
    """
    cities = [h.city for h in History.query.filter(History.city.isnot(None)).all()]
    if not cities:
        return None, 0, {}
    counter = Counter(cities)
    most_city, most_count = counter.most_common(1)[0]
    return most_city, most_count, dict(counter)


def get_history_city_pie_data():
    """
    获取历史预测中各城市占比的饼图数据。
    :return: (pie_data, city_count)
             pie_data: list[dict] - 每个元素为 {'name':城市, 'value':预测次数}
             city_count: int - 涉及的不同城市数量
    """
    cities = [h.city for h in History.query.filter(History.city.isnot(None)).all()]
    if not cities:
        return [], 0
    counter = Counter(cities)
    pie = [{'name': c, 'value': cnt} for c, cnt in counter.items()]
    return pie, len(counter)
