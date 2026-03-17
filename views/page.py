from flask import session, render_template, redirect, Blueprint, request, flash, url_for
from utils.visualization import (
    process_price_chart_data, process_summary_data, process_radar_sale_data,
    process_wordcloud_data, get_city_price_xy, get_city_price_greening_scatter,
    get_city_completion_price_line, get_property_type_dict, get_greening_area_chart_data,
    get_province_house_data, get_region_house_data, get_wordcloud_data,
    get_history_by_username, get_history_max_price, get_history_most_frequent_city,
    get_history_city_pie_data, get_city_list,
    get_all_db_data, fuzzy_match_data, get_data_by_id, insert_history_record
)
from utils.config import RF_MODEL_PATH, LGBM_MODEL_PATH, ENCODING_MAPS_PATH
from extensions import db
from utils.visualization import clear_chart_cache
from model.Community_info import Community_info
from model.History import History
import joblib
import pandas as pd
import re
import numpy as np
from datetime import datetime

pb = Blueprint('page', __name__, url_prefix='/page')


@pb.route('/home')
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


@pb.route('/tableData', methods=['GET', 'POST'])
def tableData():
    template_params = {
        "username": session.get('username', '未登录'),
        "community_data": [],
        "error_msg": ""
    }

    try:
        community_data = get_all_db_data()
        if not community_data:
            template_params["error_msg"] = "暂无小区数据可展示"
            return render_template('tableData.html', **template_params)

        search_word = ""
        if request.method == "POST":
            search_word = request.form.get('searchWord', '').strip()
        elif request.method == "GET":
            search_word = request.args.get('searchWord', '').strip()

        if search_word:
            filtered_data = fuzzy_match_data(search_word, community_data)
            template_params["community_data"] = filtered_data
            if not filtered_data:
                template_params["error_msg"] = f"未找到包含「{search_word}」的小区数据"
        else:
            template_params["community_data"] = community_data[:1000]

    except Exception as e:
        template_params["error_msg"] = f"数据加载失败：{str(e)}"
        print(f"tableData路由异常：{str(e)}")

    return render_template('tableData.html', **template_params)


@pb.route('/detail')
def detail():
    username = session.get('username')
    id = request.args.get('id')
    community_info = get_data_by_id(id)
    return render_template('detail.html',
                           username=username,
                           community_info=community_info)


@pb.route('/addHouse', methods=['GET', 'POST'])
def addHouse():
    username = session.get('username')

    if request.method == 'GET':
        return render_template('addHouse.html', username=username)

    if request.method == 'POST':
        # 收集表单数据
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

        # 必填字段校验
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
            clear_chart_cache()
            flash('小区信息添加成功！', 'success')
            return redirect(url_for('page.tableData', searchWord=community.community_name))
        except Exception as e:
            db.session.rollback()
            flash(f'添加失败：{str(e)}', 'error')
            return render_template('addHouse.html', username=username)


@pb.route('/editHouse', methods=['GET', 'POST'])
def editHouse():
    username = session.get('username')

    if request.method == 'GET':
        id = request.args.get('id')
        community_info = get_data_by_id(id)  # 获取小区信息

        if not id or not community_info:
            flash("未找到对应的小区信息，请检查ID！", 'error')
            return render_template('editHouse.html', username=username, community_info=None)

        # 重要：传递变量名必须为 community_info
        return render_template('editHouse.html',
                               username=username,
                               community_info=community_info)

    if request.method == 'POST':
        id = request.args.get('id')
        if not id:
            flash("修改失败：未获取到小区ID！", 'error')
            return render_template('editHouse.html', username=username, community=None)

        community = get_data_by_id(id)
        if not community:
            flash("未找到对应的小区信息！", 'error')
            return render_template('editHouse.html', username=username, community=None)

        # 更新字段
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
            clear_chart_cache()
            flash('小区信息更新成功！', 'success')
            return redirect(url_for('page.tableData', searchWord=community.community_name))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
            return render_template('editHouse.html', username=username, community=community)


@pb.route('/deleteHouse', methods=['GET'])
def deleteHouse():
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


@pb.route('/priceChart', methods=['GET'])
def priceChart():
    username = session.get('username')
    cities_list = get_city_list()
    defaultCity = request.args.get('defaultCity') if request.args.get('defaultCity') else cities_list[0]
    X_price, Y_price = get_city_price_xy(defaultCity)
    scatter_result = get_city_price_greening_scatter(defaultCity, return_type="labeled")
    X_price_and_completion, Y_price_and_completion = get_city_price_xy(defaultCity)
    line_data = get_city_completion_price_line(defaultCity)
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


@pb.route('/detailChart', methods=['GET'])
def detailChart():
    username = session.get('username')
    map_data = get_property_type_dict()
    X_green, Y_green = get_greening_area_chart_data()
    return render_template('detailChart.html',
                           username=username,
                           map_data=map_data,
                           X_green=X_green,
                           Y_green=Y_green)


@pb.route('/mapChart', methods=['GET'])
def mapChart():
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


@pb.route('/cloudChart', methods=['GET'])
def cloudChart():
    username = session.get('username')
    comm_wordcloud, property_wordcloud = get_wordcloud_data()
    return render_template('cloudChart.html',
                           comm_wordcloud=comm_wordcloud,
                           property_wordcloud=property_wordcloud,
                           username=username)


# ===================== 模型路径 =====================
RF_MODEL_PATH = "./pred/house_price_prediction_model_rf.pkl"
LGBM_MODEL_PATH = "./pred/house_price_prediction_model_lgbm.pkl"
ENCODING_MAPS_PATH = "./pred/target_encoding_maps.pkl"


# ===================== 预加载双模型 + 编码映射 =====================
def load_models_and_maps():
    try:
        rf_model = joblib.load(RF_MODEL_PATH)
        lgbm_model = joblib.load(LGBM_MODEL_PATH)
        encoding_maps = joblib.load(ENCODING_MAPS_PATH)
        return rf_model, lgbm_model, encoding_maps
    except Exception as e:
        print(f"模型加载失败：{str(e)}")
        return None, None, None


RF_MODEL, LGBM_MODEL, ENCODING_MAPS = load_models_and_maps()


# ===================== 预处理函数 =====================
def preprocess_data(input_df):
    df = input_df.copy(deep=True)
    CURRENT_YEAR = datetime.now().year

    def extract_numeric_value(val, unit_list=None):
        if pd.isna(val) or str(val).strip() in ["暂无", "无", "未知", ""]:
            return np.nan
        unit_list = unit_list or ["年", "%", "元/m²", "元/㎡", "元/㎡·月", "元/㎡月"]
        val_str = str(val).strip()
        for unit in unit_list:
            val_str = val_str.replace(unit, "")
        match = re.search(r'(\d+\.?\d*)', val_str)
        return float(match.group()) if match else np.nan

    target_cols = ["property_type", "unified_heating", "water_supply_power"]
    df.columns = [col.strip() for col in df.columns]
    for col in target_cols:
        if col not in df.columns:
            df[col] = "未知"
        df[col] = df[col].astype(str).str.strip().replace(["nan", "", " "], "未知")

    pt_values = ["住宅", "公寓", "商铺", "写字楼", "别墅", "其他"]
    for val in pt_values:
        df[f"property_type_{val}"] = 1 if df["property_type"].iloc[0] == val else 0

    uh_values = ["是", "否", "未知"]
    for val in uh_values:
        df[f"unified_heating_{val}"] = 1 if df["unified_heating"].iloc[0] == val else 0

    wsp_values = ["民用", "商用", "未知"]
    for val in wsp_values:
        df[f"water_supply_power_{val}"] = 1 if df["water_supply_power"].iloc[0] == val else 0

    core_building_types = ["低层", "多层", "小高层", "高层", "超高层"]
    building_type_val = df["building_type"].iloc[0] if not pd.isna(df["building_type"].iloc[0]) else ""
    for bt in core_building_types:
        df[f"building_type_{bt}"] = 1 if bt in building_type_val else 0
    df.drop("building_type", axis=1, inplace=True)

    df["completion_year"] = df["completion_time"].apply(
        lambda x: extract_numeric_value(x, unit_list=["年"]) if pd.notna(x) else np.nan)
    df["house_age"] = df["completion_year"].apply(
        lambda x: CURRENT_YEAR - x if (pd.notna(x) and 1900 <= x <= CURRENT_YEAR) else np.nan)
    df["house_age"] = df["house_age"].apply(lambda x: 50 if x > 50 else x)
    df["house_age"].fillna(df["house_age"].median() if not df["house_age"].isna().all() else 0, inplace=True)
    df.drop(["completion_time", "completion_year"], axis=1, inplace=True)

    numeric_config = {
        "property_right_years": {"unit": ["年"], "max": 70, "min": 40},
        "property_fee": {"unit": [], "max": 10, "min": 0.5},
        "plot_ratio": {"unit": [], "max": 4, "min": 0.5},
        "greening_rate": {"unit": [], "max": 50, "min": 10}
    }
    for field, cfg in numeric_config.items():
        df[field] = df[field].apply(extract_numeric_value, unit_list=cfg["unit"])
        df[field].fillna(df[field].median() if not df[field].isna().all() else cfg["min"], inplace=True)
        df[field] = df[field].apply(lambda x: cfg["max"] if x > cfg["max"] else (cfg["min"] if x < cfg["min"] else x))

    df["house_age_sq"] = df["house_age"] ** 2
    df["plot_ratio_log"] = np.log1p(df["plot_ratio"])
    df["property_fee_sqrt"] = np.sqrt(df["property_fee"])

    if "city" in df.columns and "city" in ENCODING_MAPS:
        df["city_encoded"] = df["city"].map(ENCODING_MAPS["city"]).fillna(ENCODING_MAPS["city"].get("UNKNOWN", 0))
    else:
        df["city_encoded"] = 0
    df.drop("city", axis=1, inplace=True)

    df["property_type"] = "未知"
    df["unified_heating"] = "未知"
    df["water_supply_power"] = "未知"

    required_cols = [
        "city_encoded", "property_right_years", "property_fee", "plot_ratio", "greening_rate", "house_age",
        "house_age_sq", "plot_ratio_log", "property_fee_sqrt",
        "building_type_低层", "building_type_多层", "building_type_小高层", "building_type_高层",
        "building_type_超高层",
        "property_type_住宅", "property_type_公寓", "property_type_商铺", "property_type_写字楼", "property_type_别墅",
        "property_type_其他",
        "unified_heating_是", "unified_heating_否", "unified_heating_未知",
        "water_supply_power_民用", "water_supply_power_商用", "water_supply_power_未知",
        "property_type", "unified_heating", "water_supply_power"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0 if any(prefix in col for prefix in ["building_type_", "property_type_", "unified_heating_",
                                                            "water_supply_power_"]) else "未知"

    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].fillna("未知")
        else:
            df[col] = df[col].fillna(0)

    return df[required_cols]


# ===================== 核心接口 =====================
@pb.route('/pricePre', methods=['GET', 'POST'])
def pricePre():
    cities_list = get_city_list()
    rf_price_result = 0
    lgbm_price_result = 0
    priceResult = 0
    errorMsg = ""
    username = session.get('username')
    user_id = session.get('user_id')

    if request.method == "GET":
        return render_template('pricePre.html',
                               username=username,
                               cities_list=cities_list,
                               rf_price_result=rf_price_result,
                               lgbm_price_result=lgbm_price_result,
                               priceResult=priceResult,
                               errorMsg=errorMsg)
    else:
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

        required_fields = ["city", "property_type", "building_type", "completion_time",
                           "property_right_years", "property_fee", "plot_ratio", "greening_rate",
                           "unified_heating", "water_supply_power"]
        empty_fields = [f for f in required_fields if
                        not input_data[f].iloc[0] or str(input_data[f].iloc[0]).strip() == ""]
        if empty_fields:
            errorMsg = f"请填写必填字段：{','.join(empty_fields)}"
            return render_template('pricePre.html', **locals())

        if not RF_MODEL or not LGBM_MODEL or not ENCODING_MAPS:
            errorMsg = "模型加载失败，暂时无法预测，请联系管理员"
            return render_template('pricePre.html', **locals())

        try:
            processed_data = preprocess_data(input_data)
        except Exception as e:
            errorMsg = f"数据处理失败：{str(e)}"
            return render_template('pricePre.html', **locals())

        try:
            rf_pred = RF_MODEL.predict(processed_data)[0]
            rf_price_result = round(rf_pred, 2)
            lgbm_pred = LGBM_MODEL.predict(processed_data)[0]
            lgbm_price_result = round(lgbm_pred, 2)
            priceResult = lgbm_price_result

            if user_id:
                insert_history_record(city=city, price=f"{lgbm_price_result} 元/㎡", user_id=user_id)
        except Exception as e:
            errorMsg = f"预测失败：{str(e)}"

        return render_template('pricePre.html', **locals())
