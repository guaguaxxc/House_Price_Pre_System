"""
房价预测模型训练脚本
================================================
该脚本从数据库加载小区数据，进行特征工程预处理，
分别训练随机森林和 LightGBM 回归模型，并评估模型性能。
训练好的模型和编码映射将被保存到指定路径，供后续预测使用。
"""
import pandas as pd
import numpy as np
import joblib
import sys
import os

# 将项目根目录添加到系统路径，以便导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model.Community_info import Community_info
from utils.model_utils import extract_numeric_value, target_encoding, add_nonlinear_features
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from lightgbm import LGBMRegressor
from datetime import datetime
from app import create_app

# ================= 全局配置 =================
CURRENT_YEAR = datetime.now().year  # 用于计算房龄的当前年份
RF_MODEL_SAVE_PATH = './pred/house_price_prediction_model_rf.pkl'  # 随机森林模型保存路径
LGBM_MODEL_SAVE_PATH = './pred/house_price_prediction_model_lgbm.pkl'  # LightGBM模型保存路径
ENCODING_MAP_SAVE_PATH = './pred/target_encoding_maps.pkl'  # 目标编码映射保存路径

# 确保保存目录存在
os.makedirs(os.path.dirname(RF_MODEL_SAVE_PATH), exist_ok=True)


def load_data_from_db():
    """
    从数据库加载小区数据，并转换为 pandas DataFrame。
    仅保留价格非空的小区记录，提取模型训练所需的特征字段和价格字段。
    :return: pandas DataFrame，包含原始特征和价格列
    """
    # 查询所有价格不为空的小区记录
    communities = Community_info.query.filter(
        Community_info.price.isnot(None),
        Community_info.price != ''
    ).all()

    data = []
    for c in communities:
        data.append({
            'city': c.city,
            'property_type': c.property_type,
            'completion_time': c.completion_time,
            'property_right_years': c.property_right_years,
            'property_fee': c.property_fee,
            'plot_ratio': c.plot_ratio,
            'greening_rate': c.greening_rate,
            'building_type': c.building_type,
            'unified_heating': c.unified_heating,
            'water_supply_power': c.water_supply_power,
            'price': c.price
        })

    df = pd.DataFrame(data)
    print(f"【数据库】加载数据 {len(df)} 条")
    return df


def preprocess_training_data(df):
    """
    对原始数据进行特征工程处理，生成训练用的特征矩阵 X 和目标向量 y，
    同时返回用于目标编码的映射字典。
    处理步骤包括：
        1. 提取价格数值并过滤异常值（基于分位数）。
        2. 对建筑类型进行独热编码（提取核心类型：低层、多层等）。
        3. 计算房龄，并限制在合理范围（0-50年）。
        4. 处理数值特征（产权年限、物业费、容积率、绿化率）：提取数值、截断、填充缺失。
        5. 添加非线性特征（房龄平方、容积率对数、物业费平方根）。
        6. 对城市进行目标编码（Target Encoding），生成 city_encoded 列。
        7. 规范化类别字段（物业类型、集中供暖、水电类型）。
        8. 筛选最终的特征列。
    :param df: 原始数据 DataFrame
    :return: X (特征矩阵), y (目标价格序列), encoding_maps (城市编码映射字典)
    """
    # ---------- 1. 目标变量提取与清洗 ----------
    # 从价格字符串中提取数值（如 "65000元/㎡" → 65000.0）
    df['price'] = df['price'].apply(extract_numeric_value, unit_list=["元/m²", "元/㎡"])

    # 根据价格分位数去除极端值（保留 8% - 92% 分位数之间的数据）
    q_low, q_high = df['price'].quantile(0.08), df['price'].quantile(0.92)
    df = df[(df['price'] >= q_low) & (df['price'] <= q_high)]

    # ---------- 2. 建筑类型独热编码 ----------
    # 定义核心建筑类型，只有包含这些类型的记录才保留（避免杂项数据）
    core_building_types = ["低层", "多层", "小高层", "高层", "超高层"]
    df = df[df["building_type"].apply(
        lambda x: any(bt in str(x) for bt in core_building_types) if pd.notna(x) else False
    )]

    # 为每种核心类型创建独热编码列
    for bt in core_building_types:
        df[f"building_type_{bt}"] = df["building_type"].apply(lambda x: 1 if bt in str(x) else 0)

    # 删除原始 building_type 列
    df.drop("building_type", axis=1, inplace=True)

    # ---------- 3. 房龄计算 ----------
    # 从竣工时间字符串中提取年份（如 "2010年" → 2010.0）
    df["completion_year"] = df["completion_time"].apply(
        lambda x: extract_numeric_value(x, unit_list=["年"]) if pd.notna(x) else np.nan
    )

    # 计算房龄 = 当前年份 - 竣工年份，限制在合理范围，无效值设为 NaN
    df["house_age"] = df["completion_year"].apply(
        lambda x: CURRENT_YEAR - x if (pd.notna(x) and 1900 <= x <= CURRENT_YEAR) else np.nan
    )

    # 房龄大于50年的按50处理
    df["house_age"] = df["house_age"].apply(lambda x: 50 if x > 50 else x)

    # 用中位数填充缺失的房龄
    df["house_age"].fillna(df["house_age"].median(), inplace=True)

    # 删除中间列
    df.drop(["completion_time", "completion_year"], axis=1, inplace=True)

    # ---------- 4. 数值特征处理 ----------
    # 定义各数值字段的处理配置：单位、最大值、最小值（用于截断）
    numeric_config = {
        "property_right_years": {"unit": ["年"], "max": 70, "min": 40},
        "property_fee": {"unit": ["元/㎡·月"], "max": 10, "min": 0.5},
        "plot_ratio": {"unit": [], "max": 4, "min": 0.5},
        "greening_rate": {"unit": ["%"], "max": 50, "min": 10}
    }

    for field, cfg in numeric_config.items():
        # 提取数值
        df[field] = df[field].apply(extract_numeric_value, unit_list=cfg["unit"])
        # 截断到合理范围
        df[field] = df[field].apply(lambda x: cfg["max"] if x > cfg["max"] else (cfg["min"] if x < cfg["min"] else x))
        # 用中位数填充缺失值
        df[field].fillna(df[field].median(), inplace=True)

    # ---------- 5. 添加非线性特征 ----------
    df = add_nonlinear_features(df)  # 该函数会添加 house_age_sq, plot_ratio_log, property_fee_sqrt

    # ---------- 6. 城市目标编码 ----------
    # 对城市进行目标编码，用价格的均值作为编码值，并返回编码映射字典
    df["city_encoded"], encoding_maps = target_encoding(df, "city", "price", alpha=5)

    # 删除原始城市列
    df.drop("city", axis=1, inplace=True)

    # ---------- 7. 类别字段规范化 ----------
    # 物业类型：若不在预设列表中，归类为"其他"
    df["property_type"] = df["property_type"].apply(
        lambda x: x if x in ["住宅", "公寓", "商铺", "写字楼", "别墅"] else "其他"
    )
    # 集中供暖：不在["是","否"]的标记为"未知"
    df["unified_heating"] = df["unified_heating"].apply(lambda x: x if x in ["是", "否"] else "未知")
    # 水电类型：不在["民用","商用"]的标记为"未知"
    df["water_supply_power"] = df["water_supply_power"].apply(lambda x: x if x in ["民用", "商用"] else "未知")

    # ---------- 8. 最终特征选择 ----------
    # 定义模型需要的特征列（需与训练时的顺序一致）
    feature_cols = [
        "city_encoded",
        "property_type", "unified_heating", "water_supply_power",
        "property_right_years", "property_fee", "plot_ratio", "greening_rate", "house_age",
        "house_age_sq", "plot_ratio_log", "property_fee_sqrt",
        "building_type_低层", "building_type_多层", "building_type_小高层", "building_type_高层", "building_type_超高层"
    ]

    # 仅保留存在的列（避免因数据缺失导致错误）
    X = df[[col for col in feature_cols if col in df.columns]]
    y = df['price']

    return X, y, encoding_maps


def train_models():
    """
    主训练流程：
        1. 从数据库加载数据。
        2. 数据预处理，得到特征和目标。
        3. 划分训练集和测试集。
        4. 构建包含数值标准化和类别独热编码的预处理管道。
        5. 训练随机森林和 LightGBM 模型。
        6. 在测试集上评估模型性能（MAE, MSE, R2）。
        7. 保存训练好的模型和编码映射。
    """
    # 加载数据
    df = load_data_from_db()
    if len(df) < 200:
        print(f"数据不足，当前{len(df)}条，需要≥200")
        return

    # 数据预处理
    X, y, encoding_maps = preprocess_training_data(df)
    if len(X) < 200:
        print(f"预处理后数据不足{len(X)}条")
        return

    # ---------- 划分训练集/测试集 ----------
    # 如果物业类型类别数足够，按物业类型分层抽样
    stratify = X["property_type"] if X["property_type"].nunique() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=stratify
    )

    # ---------- 定义特征处理器 ----------
    # 数值特征列表（需要标准化）
    numeric_features = [
        "city_encoded", "property_right_years", "property_fee", "plot_ratio",
        "greening_rate", "house_age", "house_age_sq", "plot_ratio_log",
        "property_fee_sqrt", "building_type_低层", "building_type_多层",
        "building_type_小高层", "building_type_高层", "building_type_超高层"
    ]
    # 类别特征列表（需要独热编码）
    categorical_features = ["property_type", "unified_heating", "water_supply_power"]

    # 仅保留实际存在的特征
    numeric_features = [f for f in numeric_features if f in X.columns]
    categorical_features = [f for f in categorical_features if f in X.columns]

    # 创建列转换器：分别处理数值列和类别列
    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), numeric_features),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
    ])

    # ---------- 定义模型管道 ----------
    # 随机森林管道
    rf_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(
            n_estimators=150, max_depth=8, min_samples_split=20,
            min_samples_leaf=5, max_features="sqrt", random_state=42, n_jobs=-1
        ))
    ])

    # LightGBM 管道
    lgbm_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", LGBMRegressor(
            n_estimators=150, max_depth=8, learning_rate=0.1,
            num_leaves=31, min_child_samples=5, subsample=0.8,
            colsample_bytree=0.8, random_state=42, n_jobs=-1, verbose=-1
        ))
    ])

    # ---------- 训练模型 ----------
    print("训练随机森林...")
    rf_pipeline.fit(X_train, y_train)
    print("训练LightGBM...")
    lgbm_pipeline.fit(X_train, y_train)

    # ---------- 评估函数 ----------
    def evaluate(pipeline, X_tr, y_tr, X_te, y_te):
        """计算模型在训练集和测试集上的 MAE、MSE 和 R2 分数"""
        pred_tr = pipeline.predict(X_tr)
        pred_te = pipeline.predict(X_te)
        return {
            "train_mae": mean_absolute_error(y_tr, pred_tr),
            "train_mse": mean_squared_error(y_tr, pred_tr),
            "train_r2": r2_score(y_tr, pred_tr),
            "test_mae": mean_absolute_error(y_te, pred_te),
            "test_mse": mean_squared_error(y_te, pred_te),
            "test_r2": r2_score(y_te, pred_te),
        }

    # 评估两个模型
    rf_metrics = evaluate(rf_pipeline, X_train, y_train, X_test, y_test)
    lgbm_metrics = evaluate(lgbm_pipeline, X_train, y_train, X_test, y_test)

    # 输出评估对比
    print("\n" + "=" * 50)
    print("模型评估对比")
    print("=" * 50)
    print(f"{'指标':15} {'随机森林':>10} {'LightGBM':>10}")
    for key in ["train_mae", "train_mse", "train_r2", "test_mae", "test_mse", "test_r2"]:
        rf_val = rf_metrics[key]
        lgbm_val = lgbm_metrics[key]
        print(f"{key:15} {rf_val:10.2f} {lgbm_val:10.2f}")

    # ---------- 保存模型和编码映射 ----------
    joblib.dump(rf_pipeline, RF_MODEL_SAVE_PATH)
    joblib.dump(lgbm_pipeline, LGBM_MODEL_SAVE_PATH)
    joblib.dump(encoding_maps, ENCODING_MAP_SAVE_PATH)
    print(f"\n模型已保存至：{RF_MODEL_SAVE_PATH} 和 {LGBM_MODEL_SAVE_PATH}")
    print(f"编码映射保存至：{ENCODING_MAP_SAVE_PATH}")


if __name__ == "__main__":
    # 创建 Flask 应用上下文，以便使用数据库连接
    app = create_app()
    with app.app_context():
        train_models()
