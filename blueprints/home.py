"""
首页蓝图模块
================================================
负责渲染系统首页，并加载各类统计图表数据（价格分布、摘要统计、雷达图、词云等）。
数据通过缓存优化，减少数据库查询压力。
"""

from flask import Blueprint, render_template, session
from extensions import cache
from utils.visualization import (
    process_price_chart_data, process_summary_data, process_radar_sale_data,
    process_wordcloud_data, get_history_by_username, get_history_max_price,
    get_history_most_frequent_city, get_history_city_pie_data
)

# 创建首页蓝图，URL前缀为 /home
home_bp = Blueprint('home', __name__, url_prefix='/home')


@home_bp.route('/')
@cache.cached(timeout=300, key_prefix='home_data')  # 缓存首页数据300秒，避免每次请求都重新计算
def home():
    """
    渲染系统首页，展示各类统计图表和用户历史信息。
    该路由从 session 获取当前用户名，调用多个数据处理函数获取图表所需数据，
    并将所有数据传递给模板 index.html 进行渲染。
    :return: 渲染后的首页 HTML 页面
    """
    # 获取当前登录用户名
    username = session.get('username')

    # 获取价格图表数据
    price_chart_data = process_price_chart_data()

    # 获取摘要统计数据
    summary_data = process_summary_data()

    # 获取雷达图数据
    radar_sale_data = process_radar_sale_data()

    # 获取词云数据
    wordcloud_data = process_wordcloud_data()

    # 获取当前用户的预测历史记录和预测次数
    predict_count, history_data = get_history_by_username(username)

    # 获取历史预测中的最高价格
    max_price = get_history_max_price()

    # 获取历史预测中最常出现的城市
    most_frequent_city = get_history_most_frequent_city()

    # 获取历史预测中各城市占比的饼图数据
    city_pie_data = get_history_city_pie_data()

    # 将所有数据传递给模板
    return render_template('index.html',
                           username=username,
                           price_chart_data=price_chart_data,
                           summary_data=summary_data,
                           radar_sale_data=radar_sale_data,
                           wordcloud_data=wordcloud_data,
                           predict_count=predict_count,
                           history_data=history_data,
                           max_price=max_price,
                           most_frequent_city=most_frequent_city,
                           city_pie_data=city_pie_data)
