"""
页面蓝图模块
================================================
该模块定义了所有前端页面的路由，包括：
    - 首页（/home）
    - 数据表格页（/tableData）
    - 详情页（/detail）
    - 添加/编辑/删除小区（/addHouse, /editHouse, /deleteHouse）
    - 各类图表页（/priceChart, /detailChart, /mapChart, /cloudChart）
    - 房价预测页（/pricePre）
每个路由从数据库获取数据，调用可视化工具函数处理，最后渲染对应的模板。
"""

from flask import session, render_template, redirect, Blueprint, request, flash, url_for

# 从 prediction 蓝图导入已加载的模型和预处理函数
from blueprints.prediction import rf_model, lgbm_model, encoding_maps, preprocess_data

# 导入可视化工具函数
from utils.visualization import (
    process_price_chart_data, process_summary_data, process_radar_sale_data,
    process_wordcloud_data, get_city_price_xy, get_city_price_greening_scatter,
    get_city_completion_price_line, get_property_type_dict, get_greening_area_chart_data,
    get_province_house_data, get_region_house_data, get_wordcloud_data,
    get_history_by_username, get_history_max_price, get_history_most_frequent_city,
    get_history_city_pie_data, get_city_list,
    get_all_db_data, fuzzy_match_data, get_data_by_id, insert_history_record
)

# 导入数据库扩展和模型
from extensions import db
from utils.visualization import clear_chart_cache
from model.Community_info import Community_info
import pandas as pd

# 创建页面蓝图，所有路由前缀为 /page
pb = Blueprint('page', __name__, url_prefix='/page')


# ==================== 首页 ====================
@pb.route('/home')
def home():
    """
    系统首页，展示各类统计图表和用户历史信息。
    从 session 获取当前用户名，调用多个可视化函数获取图表数据，
    并传递给模板 index.html 进行渲染。
    :return: 渲染后的首页 HTML 页面
    """
    username = session.get('username')

    # 获取首页所需的各种图表数据
    price_chart_data = process_price_chart_data()  # 价格排行前10
    summary_data = process_summary_data()  # 统计数据（总数、最高价等）
    radar_sale_data = process_radar_sale_data()  # 在售房源雷达图
    wordcloud_data = process_wordcloud_data()  # 地址词云

    # 获取当前用户的预测历史
    predict_count, history_data = get_history_by_username(username)

    # 获取全局历史统计
    max_price = get_history_max_price()  # 最高预测价格
    most_frequent_city = get_history_most_frequent_city()  # 最常预测城市
    city_pie_data = get_history_city_pie_data()  # 城市预测数量饼图

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


# ==================== 数据表格页 ====================
@pb.route('/tableData', methods=['GET', 'POST'])
def tableData():
    """
    小区数据表格页面，支持按城市、小区名称、地址模糊搜索。
    GET 请求：从 URL 参数获取 searchWord 进行搜索。
    POST 请求：从表单获取 searchWord 进行搜索。
    默认显示前1000条记录，避免一次性加载过多数据。

    :return: 渲染后的表格页面 tableData.html
    """
    # 初始化模板参数
    template_params = {
        "username": session.get('username', '未登录'),
        "community_data": [],
        "error_msg": ""
    }

    try:
        # 获取所有小区数据（ORM 对象列表）
        community_data = get_all_db_data()
        if not community_data:
            template_params["error_msg"] = "暂无小区数据可展示"
            return render_template('tableData.html', **template_params)

        # 获取搜索关键词（优先 POST，其次 GET）
        search_word = ""
        if request.method == "POST":
            search_word = request.form.get('searchWord', '').strip()
        elif request.method == "GET":
            search_word = request.args.get('searchWord', '').strip()

        # 若有关键词，进行模糊匹配；否则显示前1000条
        if search_word:
            filtered_data = fuzzy_match_data(search_word, community_data)
            template_params["community_data"] = filtered_data
            if not filtered_data:
                template_params["error_msg"] = f"未找到包含「{search_word}」的小区数据"
        else:
            template_params["community_data"] = community_data[:1000]

    except Exception as e:
        template_params["error_msg"] = f"数据加载失败：{str(e)}"
        # 在控制台打印异常便于调试
        print(f"tableData路由异常：{str(e)}")

    return render_template('tableData.html', **template_params)


# ==================== 详情页 ====================
@pb.route('/detail')
def detail():
    """
    查看单个小区的详细信息。
    从 URL 参数获取小区 ID，调用 get_data_by_id 获取对应记录，
    并渲染详情页面 detail.html。

    :return: 渲染后的详情页面
    """
    username = session.get('username')
    id = request.args.get('id')
    community_info = get_data_by_id(id)
    return render_template('detail.html',
                           username=username,
                           community_info=community_info)


# ==================== 添加小区 ====================
@pb.route('/addHouse', methods=['GET', 'POST'])
def addHouse():
    """
    添加新小区信息。
    GET 请求：显示空表单。
    POST 请求：接收表单数据，创建新小区记录并保存到数据库。
              保存成功后清空图表缓存，并重定向到表格页面，自动搜索新小区名称。
    """
    username = session.get('username')

    if request.method == 'GET':
        return render_template('addHouse.html', username=username)

    if request.method == 'POST':
        # 收集表单数据（所有字段均为字符串）
        form_data = {
            'city': request.form.get('city', ''),
            'community_name': request.form.get('community_name', ''),
            'price': request.form.get('price', ''),
            'address': request.form.get('address', ''),
            'community_link': request.form.get('community_link', ''),
            'property_type': request.form.get('property_type', ''),
            'ownership_type': request.form.get('ownership_type', ''),
            'completion_time': request.form.get('completion_time', ''),
            'property_right_years': request.form.get('property_right_years', ''),
            'total_households': request.form.get('total_households', ''),
            'total_building_area': request.form.get('total_building_area', ''),
            'plot_ratio': request.form.get('plot_ratio', ''),
            'greening_rate': request.form.get('greening_rate', ''),
            'building_type': request.form.get('building_type', ''),
            'business_district': request.form.get('business_district', ''),
            'unified_heating': request.form.get('unified_heating', ''),
            'water_supply_power': request.form.get('water_supply_power', ''),
            'parking_spaces': request.form.get('parking_spaces', ''),
            'property_fee': request.form.get('property_fee', ''),
            'parking_fee': request.form.get('parking_fee', ''),
            'parking_management_fee': request.form.get('parking_management_fee', ''),
            'property_company': request.form.get('property_company', ''),
            'community_address': request.form.get('community_address', ''),
            'developer': request.form.get('developer', ''),
            'sale_houses': request.form.get('sale_houses', ''),
            'rent_houses': request.form.get('rent_houses', '')
        }

        # 必填字段校验（城市和小区名称）
        required_fields = ['city', 'community_name']
        empty_fields = [field for field in required_fields if not form_data.get(field, '').strip()]
        if empty_fields:
            flash(f"以下必填字段不能为空：{','.join(empty_fields)}", 'error')
            return render_template('addHouse.html', username=username)

        # 创建 ORM 实例
        community = Community_info(**form_data)

        try:
            db.session.add(community)
            db.session.commit()
            # 数据变更后清除图表缓存
            clear_chart_cache()
            flash('小区信息添加成功！', 'success')
            return redirect(url_for('page.tableData', searchWord=community.community_name))
        except Exception as e:
            db.session.rollback()
            flash(f'添加失败：{str(e)}', 'error')
            return render_template('addHouse.html', username=username)


# ==================== 编辑小区 ====================
@pb.route('/editHouse', methods=['GET', 'POST'])
def editHouse():
    """
    编辑现有小区信息。
    GET 请求：根据 URL 参数 id 加载对应记录，填充到表单。
    POST 请求：接收表单数据，更新对应记录并提交到数据库。
              更新成功后清空图表缓存。
    """
    username = session.get('username')

    # ---------- GET 请求：显示编辑表单 ----------
    if request.method == 'GET':
        id = request.args.get('id')
        community_info = get_data_by_id(id)

        if not id or not community_info:
            flash("未找到对应的小区信息，请检查ID！", 'error')
            return render_template('editHouse.html', username=username, community_info=None)

        # 渲染编辑页面，传入现有数据
        return render_template('editHouse.html',
                               username=username,
                               community_info=community_info)

    # ---------- POST 请求：更新数据 ----------
    if request.method == 'POST':
        id = request.args.get('id')
        if not id:
            flash("修改失败：未获取到小区ID！", 'error')
            return render_template('editHouse.html', username=username, community=None)

        community = get_data_by_id(id)
        if not community:
            flash("未找到对应的小区信息！", 'error')
            return render_template('editHouse.html', username=username, community=None)

        # 更新所有字段（从表单获取）
        community.city = request.form.get('city', '')
        community.community_name = request.form.get('community_name', '')
        community.price = request.form.get('price', '')
        community.address = request.form.get('address', '')
        community.community_link = request.form.get('community_link', '')
        community.property_type = request.form.get('property_type', '')
        community.ownership_type = request.form.get('ownership_type', '')
        community.completion_time = request.form.get('completion_time', '')
        community.property_right_years = request.form.get('property_right_years', '')
        community.total_households = request.form.get('total_households', '')
        community.total_building_area = request.form.get('total_building_area', '')
        community.plot_ratio = request.form.get('plot_ratio', '')
        community.greening_rate = request.form.get('greening_rate', '')
        community.building_type = request.form.get('building_type', '')
        community.business_district = request.form.get('business_district', '')
        community.unified_heating = request.form.get('unified_heating', '')
        community.water_supply_power = request.form.get('water_supply_power', '')
        community.parking_spaces = request.form.get('parking_spaces', '')
        community.property_fee = request.form.get('property_fee', '')
        community.parking_fee = request.form.get('parking_fee', '')
        community.parking_management_fee = request.form.get('parking_management_fee', '')
        community.property_company = request.form.get('property_company', '')
        community.community_address = request.form.get('community_address', '')
        community.developer = request.form.get('developer', '')
        community.sale_houses = request.form.get('sale_houses', '')
        community.rent_houses = request.form.get('rent_houses', '')

        # 必填字段校验
        if not community.city or not community.community_name:
            flash("城市和小区名不能为空！", 'error')
            return render_template('editHouse.html', username=username, community=community)

        try:
            db.session.commit()
            clear_chart_cache()  # 数据变更，清除缓存
            flash('小区信息更新成功！', 'success')
            return redirect(url_for('page.tableData', searchWord=community.community_name))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return render_template('editHouse.html', username=username, community=community)


# ==================== 删除小区 ====================
@pb.route('/deleteHouse', methods=['GET'])
def deleteHouse():
    """
    删除指定小区记录。
    从 URL 参数获取小区 ID，若存在则删除，并清空图表缓存。
    """
    id = request.args.get('id')
    if not id:
        flash("删除失败：未获取到小区ID！", 'error')
        return redirect(url_for('page.tableData'))

    community = get_data_by_id(id)
    if not community:
        flash("删除失败：未找到对应的小区信息！", 'error')
        return redirect(url_for('page.tableData'))

    community_name = community.community_name or ''
    try:
        db.session.delete(community)
        db.session.commit()
        clear_chart_cache()
        flash(f'小区“{community_name}”删除成功！', 'success')
        return redirect(url_for('page.tableData', searchWord=community_name))
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
        return redirect(url_for('page.tableData'))


# ==================== 价格图表页 ====================
@pb.route('/priceChart', methods=['GET'])
def priceChart():
    """
    价格图表页面，展示指定城市的：
        - 价格区间分布柱状图
        - 价格-绿化率散点图
        - 竣工年份-平均价格折线图
    支持通过 URL 参数 ?defaultCity=城市名 切换城市，默认显示城市列表的第一个。
    """
    username = session.get('username')
    cities_list = get_city_list()

    # 确定默认城市
    defaultCity = request.args.get('defaultCity') if request.args.get('defaultCity') else cities_list[0]

    # 获取价格区间分布
    X_price, Y_price = get_city_price_xy(defaultCity)

    # 获取价格-绿化率散点图数据及坐标轴范围
    scatter_result = get_city_price_greening_scatter(defaultCity, return_type="labeled")

    # 获取竣工年份-价格折线图数据
    line_data = get_city_completion_price_line(defaultCity)

    # 注意：X_price_and_completion 和 Y_price_and_completion 实际与 X_price, Y_price 相同，可能是模板需要
    X_price_and_completion, Y_price_and_completion = X_price, Y_price

    return render_template('priceChart.html',
                           username=username,
                           cities_list=cities_list,
                           defaultCity=defaultCity,
                           X_price=X_price,
                           Y_price=Y_price,
                           scatter_data=scatter_result["scatter_data"],
                           axis_x_min=scatter_result["axis_range"]["x_range"][0],
                           axis_x_max=scatter_result["axis_range"]["x_range"][1],
                           axis_y_min=scatter_result["axis_range"]["y_range"][0],
                           axis_y_max=scatter_result["axis_range"]["y_range"][1],
                           X_price_and_completion=X_price_and_completion,
                           Y_price_and_completion=Y_price_and_completion,
                           line_x=line_data["x_axis"],
                           line_y=line_data["y_axis"])


# ==================== 详细图表页 ====================
@pb.route('/detailChart', methods=['GET'])
def detailChart():
    """
    详细图表页面，展示：
        - 物业类型分布树图
        - 绿化率分布面积图
    """
    username = session.get('username')
    map_data = get_property_type_dict()  # 树图数据
    X_green, Y_green = get_greening_area_chart_data()  # 绿化率分布
    return render_template('detailChart.html',
                           username=username,
                           map_data=map_data,
                           X_green=X_green,
                           Y_green=Y_green)


# ==================== 地图图表页 ====================
@pb.route('/mapChart', methods=['GET'])
def mapChart():
    """
    地图图表页面，展示：
        - 各省份平均房价地图
        - 各省份在售房源数量地图
        - 各大区在售/在租房源柱状图
    """
    username = session.get('username')
    province_price_data, province_sale_data = get_province_house_data()
    regions, sale_data, rent_data = get_region_house_data()
    return render_template('mapChart.html',
                           username=username,
                           province_price_data=province_price_data,
                           province_sale_data=province_sale_data,
                           regions=regions,
                           sale_data=sale_data,
                           rent_data=rent_data)


# ==================== 词云图表页 ====================
@pb.route('/cloudChart', methods=['GET'])
def cloudChart():
    """
    词云图表页面，展示：
        - 小区名称分词词云
        - 物业公司名称分词词云
    """
    username = session.get('username')
    comm_wordcloud, property_wordcloud = get_wordcloud_data()
    return render_template('cloudChart.html',
                           comm_wordcloud=comm_wordcloud,
                           property_wordcloud=property_wordcloud,
                           username=username)


# ==================== 房价预测页 ====================
# 注意：模型路径已在配置文件中定义，此处重复定义可能是冗余，但保留以确保可运行
RF_MODEL_PATH = "./pred/house_price_prediction_model_rf.pkl"
LGBM_MODEL_PATH = "./pred/house_price_prediction_model_lgbm.pkl"
ENCODING_MAPS_PATH = "./pred/target_encoding_maps.pkl"


@pb.route('/pricePre', methods=['GET', 'POST'])
def pricePre():
    """
    房价预测页面。
    GET 请求：显示空表单。
    POST 请求：接收表单数据，调用预训练的随机森林和 LightGBM 模型进行预测，
              并将结果展示给用户。若用户已登录，预测结果自动保存到历史记录。
    """
    # 获取城市列表用于下拉框
    cities_list = get_city_list()

    # 初始化结果变量
    rf_price_result = 0
    lgbm_price_result = 0
    priceResult = 0
    errorMsg = ""

    username = session.get('username')
    user_id = session.get('user_id')

    if request.method == "GET":
        # 显示空表单
        return render_template('pricePre.html',
                               username=username,
                               cities_list=cities_list,
                               rf_price_result=rf_price_result,
                               lgbm_price_result=lgbm_price_result,
                               priceResult=priceResult,
                               errorMsg=errorMsg)
    else:  # POST
        # 获取表单数据
        form_data = request.form
        city = form_data.get("city", "")
        property_type = form_data.get("property_type", "")
        building_type = form_data.get("building_type", "")
        completion_time = form_data.get("completion_time", "")
        property_right_years = form_data.get("property_right_years", "")
        property_fee = form_data.get("property_fee", "")
        plot_ratio = form_data.get("plot_ratio", "")
        greening_rate = form_data.get("greening_rate", "")
        unified_heating = form_data.get("unified_heating", "")
        water_supply_power = form_data.get("water_supply_power", "")

        # 构建输入 DataFrame
        input_data = pd.DataFrame({
            "city": [city],
            "property_type": [property_type],
            "building_type": [building_type],
            "completion_time": [completion_time],
            "property_right_years": [property_right_years],
            "property_fee": [property_fee],
            "plot_ratio": [plot_ratio],
            "greening_rate": [greening_rate],
            "unified_heating": [unified_heating],
            "water_supply_power": [water_supply_power]
        })

        # 必填字段检查
        required_fields = ["city", "property_type", "building_type", "completion_time",
                           "property_right_years", "property_fee", "plot_ratio", "greening_rate",
                           "unified_heating", "water_supply_power"]
        empty_fields = [f for f in required_fields if
                        not input_data[f].iloc[0] or str(input_data[f].iloc[0]).strip() == ""]
        if empty_fields:
            errorMsg = f"请填写必填字段：{','.join(empty_fields)}"
            return render_template('pricePre.html', **locals())

        # 检查模型是否加载成功
        if not rf_model or not lgbm_model or not encoding_maps:
            errorMsg = "模型加载失败，暂时无法预测，请联系管理员"
            return render_template('pricePre.html', **locals())

        # 数据预处理
        try:
            processed_data = preprocess_data(input_data)
        except Exception as e:
            errorMsg = f"数据处理失败：{str(e)}"
            return render_template('pricePre.html', **locals())

        # 进行预测
        try:
            rf_pred = rf_model.predict(processed_data)[0]
            rf_price_result = round(rf_pred, 2)

            lgbm_pred = lgbm_model.predict(processed_data)[0]
            lgbm_price_result = round(lgbm_pred, 2)

            # 默认使用 LightGBM 结果作为最终展示价格
            priceResult = lgbm_price_result

            # 若用户已登录，保存预测历史
            if user_id:
                insert_history_record(city=city, price=f"{lgbm_price_result} 元/㎡", user_id=user_id)

        except Exception as e:
            errorMsg = f"预测失败：{str(e)}"

        # 渲染结果页面
        return render_template('pricePre.html', **locals())
