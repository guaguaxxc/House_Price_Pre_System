"""
图表展示蓝图模块
================================================
提供多个图表页面：价格图表、详细图表、地图图表、词云图表。
每个路由从 visualization 工具模块获取处理后的数据，并传递给相应模板。
"""

from flask import Blueprint, render_template, session, request
from utils.visualization import (
    get_city_price_xy, get_city_price_greening_scatter, get_city_completion_price_line,
    get_property_type_dict, get_greening_area_chart_data, get_province_house_data,
    get_region_house_data, get_wordcloud_data, get_city_list
)

# 创建图表蓝图，URL前缀为 /chart
chart_bp = Blueprint('chart', __name__, url_prefix='/chart')


@chart_bp.route('/price')
def price():
    """
    价格图表页面：展示指定城市的房价分布散点图、价格-绿化率散点图、竣工时间-价格折线图。
    支持通过 URL 参数 ?city=城市名 切换城市，默认显示城市列表中的第一个城市。
    """
    username = session.get('username')
    # 获取所有城市列表，用于下拉框选择
    cities = get_city_list()
    # 获取默认城市：优先使用请求参数，否则取城市列表第一个
    default_city = request.args.get('city') or (cities[0] if cities else '北京')

    # 获取价格分布的 x 轴（价格）和 y 轴（数量）数据
    x_price, y_price = get_city_price_xy(default_city)

    # 获取价格-绿化率散点图数据，包含轴范围
    scatter = get_city_price_greening_scatter(default_city, return_type="labeled")

    # 获取竣工时间-价格折线图数据
    line = get_city_completion_price_line(default_city)

    return render_template('priceChart.html',
                           username=username,
                           cities=cities,
                           default_city=default_city,
                           x_price=x_price,
                           y_price=y_price,
                           scatter_data=scatter["scatter_data"],
                           axis_x_min=scatter["axis_range"]["x_range"][0],
                           axis_x_max=scatter["axis_range"]["x_range"][1],
                           axis_y_min=scatter["axis_range"]["y_range"][0],
                           axis_y_max=scatter["axis_range"]["y_range"][1],
                           line_x=line["x_axis"],
                           line_y=line["y_axis"])


@chart_bp.route('/detail')
def detail():
    """
    详细图表页面：展示物业类型分布图（饼图/柱状图）和绿化率-建筑面积分布图。
    """
    username = session.get('username')
    # 获取物业类型分布数据（用于地图或饼图）
    map_data = get_property_type_dict()
    # 获取绿化率-建筑面积散点图数据
    x_green, y_green = get_greening_area_chart_data()

    return render_template('detailChart.html',
                           username=username,
                           map_data=map_data,
                           x_green=x_green,
                           y_green=y_green)


@chart_bp.route('/map')
def map():
    """
    地图图表页面：展示各省份房价和在售房源数量的地图数据，
    以及各区域（如华北、华东）的在售/在租房源柱状图。
    """
    username = session.get('username')
    # 获取各省份平均价格和在售房源数量（用于地图）
    province_price, province_sale = get_province_house_data()
    # 获取各区域（如华北、华东）的在售/在租房源数据
    regions, sale_data, rent_data = get_region_house_data()

    return render_template('mapChart.html',
                           username=username,
                           province_price_data=province_price,
                           province_sale_data=province_sale,
                           regions=regions,
                           sale_data=sale_data,
                           rent_data=rent_data)


@chart_bp.route('/cloud')
def cloud():
    """
    词云图表页面：展示小区名称词云和物业类型词云。
    """
    username = session.get('username')
    # 获取小区名称词云和物业类型词云的数据（通常是词频字典）
    comm_cloud, prop_cloud = get_wordcloud_data()

    return render_template('cloudChart.html',
                           username=username,
                           comm_wordcloud=comm_cloud,
                           property_wordcloud=prop_cloud)
