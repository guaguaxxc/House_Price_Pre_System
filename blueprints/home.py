from flask import Blueprint, render_template, session
from extensions import cache
from utils.visualization import (
    process_price_chart_data, process_summary_data, process_radar_sale_data,
    process_wordcloud_data, get_history_by_username, get_history_max_price,
    get_history_most_frequent_city, get_history_city_pie_data
)

home_bp = Blueprint('home', __name__, url_prefix='/home')


@home_bp.route('/')
@cache.cached(timeout=300, key_prefix='home_data')  # 缓存首页数据
def home():
    username = session.get('username')
    price_chart_data = process_price_chart_data()
    summary_data = process_summary_data()
    radar_sale_data = process_radar_sale_data()
    wordcloud_data = process_wordcloud_data()
    predict_count, history_data = get_history_by_username(username)
    max_price = get_history_max_price()
    most_frequent_city = get_history_most_frequent_city()
    city_pie_data = get_history_city_pie_data()
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
