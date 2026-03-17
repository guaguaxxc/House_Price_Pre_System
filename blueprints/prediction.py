"""
房价预测蓝图模块
================================================
该模块提供房价预测功能，用户通过表单输入小区特征（城市、物业类型、竣工时间等），
系统调用预训练的机器学习模型（随机森林和 LightGBM）进行价格预测，
并将预测结果保存到历史记录中。
"""

from flask import Blueprint, render_template, session
from forms.prediction import PredictionForm
from model.History import History
from extensions import db
from utils.visualization import get_city_list
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
import re
from config import Config

# 创建预测蓝图，所有路由的前缀为 /predict
prediction_bp = Blueprint('prediction', __name__, url_prefix='/predict')

# ================= 模型预加载 =================
# 在应用启动时加载训练好的模型和编码映射，避免每次请求重复加载
# 若加载失败，将相关变量置为 None，并在后续请求中提示错误
try:
    # 随机森林回归模型
    rf_model = joblib.load(Config.RF_MODEL_PATH)
    # LightGBM 回归模型
    lgbm_model = joblib.load(Config.LGBM_MODEL_PATH)
    # 类别特征编码映射字典（如城市、物业类型等与数值的对应关系）
    encoding_maps = joblib.load(Config.ENCODING_MAPS_PATH)
except Exception as e:
    rf_model = lgbm_model = encoding_maps = None
    print(f"模型加载失败: {e}")


def preprocess_data(input_df):
    """
    对用户输入的原始数据进行特征工程处理，使其符合模型输入要求。
    该函数执行以下操作：
        1. 复制数据框，避免修改原始数据。
        2. 定义辅助函数 extract_numeric_value，从字符串中提取数值。
        3. 对类别特征（物业类型、统一供暖、供水供电）进行独热编码。
        4. 从建筑类型中提取核心类型（低层、多层等）并生成独热编码。
        5. 计算房龄（当前年份 - 竣工年份），并处理异常值。
        6. 对数值特征（产权年限、物业费、容积率、绿化率）进行提取、缺失值填充和截断。
        7. 构造派生特征：房龄平方、容积率对数、物业费平方根。
        8. 对城市进行编码（使用预加载的编码映射）。
        9. 确保所有模型需要的特征列存在，缺失的列用默认值填充。
    :param input_df: pandas DataFrame，包含用户提交的单行数据
    :return: pandas DataFrame，包含模型所需的全部特征，顺序与训练时一致
    """
    # 复制数据框，避免影响原始数据
    df = input_df.copy(deep=True)
    CURRENT_YEAR = datetime.now().year

    # ---------- 辅助函数：从字符串中提取数值 ----------
    def extract_numeric_value(val, unit_list=None):
        """
        从包含单位或说明的字符串中提取第一个数值（整数或小数）。
        若值无效（空、None、'暂无'等），返回 NaN。
        :param val: 原始值（字符串或数字）
        :param unit_list: 需要移除的单位列表，如 ["年", "%"]
        :return: float 或 NaN
        """
        if pd.isna(val) or str(val).strip() in ["暂无", "无", "未知", ""]:
            return np.nan
        unit_list = unit_list or ["年", "%", "元/m²", "元/㎡", "元/㎡·月", "元/㎡月"]
        val_str = str(val).strip()
        # 移除所有单位
        for unit in unit_list:
            val_str = val_str.replace(unit, "")
        # 使用正则提取第一个数字（含小数点）
        match = re.search(r'(\d+\.?\d*)', val_str)
        return float(match.group()) if match else np.nan

    # ---------- 类别特征处理 ----------
    # 确保三个关键类别列存在，若缺失则填充为"未知"
    target_cols = ["property_type", "unified_heating", "water_supply_power"]
    # 去除列名两侧空格
    df.columns = [col.strip() for col in df.columns]
    for col in target_cols:
        if col not in df.columns:
            df[col] = "未知"
        # 将空值或空白字符统一替换为"未知"
        df[col] = df[col].astype(str).str.strip().replace(["nan", "", " "], "未知")

    # 对 property_type 进行独热编码
    pt_values = ["住宅", "公寓", "商铺", "写字楼", "别墅", "其他"]
    for val in pt_values:
        df[f"property_type_{val}"] = 1 if df["property_type"].iloc[0] == val else 0

    # 对 unified_heating 进行独热编码
    uh_values = ["是", "否", "未知"]
    for val in uh_values:
        df[f"unified_heating_{val}"] = 1 if df["unified_heating"].iloc[0] == val else 0

    # 对 water_supply_power 进行独热编码
    wsp_values = ["民用", "商用", "未知"]
    for val in wsp_values:
        df[f"water_supply_power_{val}"] = 1 if df["water_supply_power"].iloc[0] == val else 0

    # 处理 building_type（可能为多值字符串，如"高层/小高层"）
    core_building_types = ["低层", "多层", "小高层", "高层", "超高层"]
    building_type_val = df["building_type"].iloc[0] if not pd.isna(df["building_type"].iloc[0]) else ""
    for bt in core_building_types:
        # 如果建筑类型字符串中包含该核心类型，则对应列为1，否则为0
        df[f"building_type_{bt}"] = 1 if bt in building_type_val else 0
    # 原始 building_type 列不再需要
    df.drop("building_type", axis=1, inplace=True)

    # ---------- 竣工时间与房龄 ----------
    # 提取竣工年份（数值）
    df["completion_year"] = df["completion_time"].apply(
        lambda x: extract_numeric_value(x, unit_list=["年"]) if pd.notna(x) else np.nan)
    # 计算房龄 = 当前年份 - 竣工年份，并限制在合理范围
    df["house_age"] = df["completion_year"].apply(
        lambda x: CURRENT_YEAR - x if (pd.notna(x) and 1900 <= x <= CURRENT_YEAR) else np.nan)
    # 房龄大于50年的按50处理
    df["house_age"] = df["house_age"].apply(lambda x: 50 if x > 50 else x)
    # 若房龄仍为NaN，用中位数填充；若全为NaN则用0填充
    df["house_age"].fillna(df["house_age"].median() if not df["house_age"].isna().all() else 0, inplace=True)
    # 删除中间列
    df.drop(["completion_time", "completion_year"], axis=1, inplace=True)

    # ---------- 数值特征处理 ----------
    # 定义各数值字段的配置：单位、最大值、最小值（用于截断）
    numeric_config = {
        "property_right_years": {"unit": ["年"], "max": 70, "min": 40},
        "property_fee": {"unit": [], "max": 10, "min": 0.5},
        "plot_ratio": {"unit": [], "max": 4, "min": 0.5},
        "greening_rate": {"unit": [], "max": 50, "min": 10}
    }
    for field, cfg in numeric_config.items():
        # 提取数值
        df[field] = df[field].apply(extract_numeric_value, unit_list=cfg["unit"])
        # 缺失值填充：若有中位数则用中位数，否则用最小值
        df[field].fillna(df[field].median() if not df[field].isna().all() else cfg["min"], inplace=True)
        # 截断到合理范围
        df[field] = df[field].apply(lambda x: cfg["max"] if x > cfg["max"] else (cfg["min"] if x < cfg["min"] else x))

    # ---------- 构造派生特征 ----------
    df["house_age_sq"] = df["house_age"] ** 2  # 房龄平方
    df["plot_ratio_log"] = np.log1p(df["plot_ratio"])  # 容积率的对数（log1p 避免负数）
    df["property_fee_sqrt"] = np.sqrt(df["property_fee"])  # 物业费的平方根

    # ---------- 城市编码 ----------
    # 假设 rf_model 是一个字典，包含 'city' 映射（实际可能是模型对象，这里根据原代码逻辑）
    # 原代码使用 rf_model["city"]，需确保 rf_model 是字典结构，否则需调整
    if "city" in df.columns and "city" in rf_model:
        df["city_encoded"] = df["city"].map(rf_model["city"]).fillna(rf_model["city"].get("UNKNOWN", 0))
    else:
        df["city_encoded"] = 0
    df.drop("city", axis=1, inplace=True)

    # 原代码后续保留了 property_type 等原始文本列（可能用于调试），但模型不需要，这里也保留
    df["property_type"] = "未知"
    df["unified_heating"] = "未知"
    df["water_supply_power"] = "未知"

    # ---------- 确保所有模型所需列存在 ----------
    # 模型训练时使用的特征列表（需与训练时完全一致）
    required_cols = [
        "city_encoded", "property_right_years", "property_fee", "plot_ratio", "greening_rate", "house_age",
        "house_age_sq", "plot_ratio_log", "property_fee_sqrt",
        "building_type_低层", "building_type_多层", "building_type_小高层", "building_type_高层",
        "building_type_超高层",
        "property_type_住宅", "property_type_公寓", "property_type_商铺", "property_type_写字楼", "property_type_别墅",
        "property_type_其他",
        "unified_heating_是", "unified_heating_否", "unified_heating_未知",
        "water_supply_power_民用", "water_supply_power_商用", "water_supply_power_未知",
        "property_type", "unified_heating", "water_supply_power"  # 这三个文本列可能被模型忽略，但保留
    ]
    # 若缺失某列，按类型填充默认值：独热编码列填0，文本列填"未知"
    for col in required_cols:
        if col not in df.columns:
            if any(prefix in col for prefix in
                   ["building_type_", "property_type_", "unified_heating_", "water_supply_power_"]):
                df[col] = 0
            else:
                df[col] = "未知"

    # 最终填充所有NaN值：数值列填0，文本列填"未知"
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].fillna("未知")
        else:
            df[col] = df[col].fillna(0)

    # 返回按 required_cols 顺序排列的数据框
    return df[required_cols]


@prediction_bp.route('/', methods=['GET', 'POST'])
def index():
    """
    房价预测主页面。
    GET 请求：展示空表单，供用户填写。
    POST 请求：接收表单数据，进行预处理，调用两个模型进行预测，并返回结果。
               若用户已登录，将预测记录保存到历史表。
    """
    form = PredictionForm()
    # 动态填充城市下拉框选项，从数据库中获取城市列表（去重）
    form.city.choices = [(c, c) for c in get_city_list()]

    username = session.get('username')
    user_id = session.get('user_id')  # 用户ID，用于关联历史记录

    result = None  # 存储预测结果（两个模型的预测值）
    error = None  # 存储错误信息，用于前端显示

    if form.validate_on_submit():
        # 表单验证通过（CSRF、字段验证等）
        if not rf_model or not lgbm_model:
            error = "模型未加载，请联系管理员"
        else:
            try:
                # 将表单数据转换为 DataFrame，便于特征工程处理
                input_df = pd.DataFrame([{
                    'city': form.city.data,
                    'property_type': form.property_type.data,
                    'building_type': form.building_type.data,
                    'completion_time': form.completion_time.data,
                    'property_right_years': form.property_right_years.data,
                    'property_fee': form.property_fee.data,
                    'plot_ratio': form.plot_ratio.data,
                    'greening_rate': form.greening_rate.data,
                    'unified_heating': form.unified_heating.data,
                    'water_supply_power': form.water_supply_power.data
                }])

                # 执行特征工程
                processed = preprocess_data(input_df)

                # 使用随机森林模型进行预测
                rf_pred = rf_model.predict(processed)[0]
                # 使用 LightGBM 模型进行预测
                lgbm_pred = lgbm_model.predict(processed)[0]

                # 封装结果，保留两位小数
                result = {
                    'rf': round(rf_pred, 2),
                    'lgbm': round(lgbm_pred, 2)
                }

                # 如果用户已登录，将预测记录保存到历史表
                if user_id:
                    history = History(
                        city=form.city.data,
                        price=f"{result['lgbm']} 元/㎡",  # 默认使用 LightGBM 结果存入历史
                        user_id=user_id
                    )
                    db.session.add(history)
                    db.session.commit()

            except Exception as e:
                error = f"预测失败: {str(e)}"
                db.session.rollback()  # 回滚数据库会话，防止脏数据

    # 渲染模板，传递表单、结果和错误信息
    return render_template('pricePre.html',
                           form=form,
                           username=username,
                           result=result,
                           error=error)
