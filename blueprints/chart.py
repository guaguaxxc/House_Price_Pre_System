from flask import Blueprint, render_template, session, request
from utils.visualization import (
    get_city_price_xy, get_city_price_greening_scatter, get_city_completion_price_line,
    get_property_type_dict, get_greening_area_chart_data, get_province_house_data,
    get_region_house_data, get_wordcloud_data, get_city_lsit
)

chart_bp = Blueprint('chart', __name__, url_prefix='/chart')


@chart_bp.route('/price')
def price():
    username = session.get('username')
    cities = get_city_lsit()
    default_city = request.args.get('city') or (cities[0] if cities else '北京')
    x_price, y_price = get_city_price_xy(default_city)
    scatter = get_city_price_greening_scatter(default_city, return_type="labeled")
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
    username = session.get('username')
    map_data = get_property_type_dict()
    x_green, y_green = get_greening_area_chart_data()
    return render_template('detailChart.html',
                           username=username,
                           map_data=map_data,
                           x_green=x_green,
                           y_green=y_green)


@chart_bp.route('/map')
def map():
    username = session.get('username')
    province_price, province_sale = get_province_house_data()
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
    username = session.get('username')
    comm_cloud, prop_cloud = get_wordcloud_data()
    return render_template('cloudChart.html',
                           username=username,
                           comm_wordcloud=comm_cloud,
                           property_wordcloud=prop_cloud)
