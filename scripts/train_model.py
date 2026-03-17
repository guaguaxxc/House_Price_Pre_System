"""
房价预测模型训练脚本（带随机搜索调参）
================================================
该脚本从数据库加载小区数据，进行特征工程预处理，
使用 RandomizedSearchCV 对随机森林和 LightGBM 进行参数调优，
训练最佳模型并评估性能。
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
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from lightgbm import LGBMRegressor
from datetime import datetime
from app import create_app
from scipy.stats import randint, uniform  # 用于参数分布

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
    df = df.copy()
    # 1. 提取价格数值
    df['price'] = df['price'].apply(extract_numeric_value, unit_list=["元/m²", "元/㎡"])

    # 放宽异常值过滤：保留 1% - 99% 分位数
    q_low, q_high = df['price'].quantile(0.01), df['price'].quantile(0.99)
    df = df[(df['price'] >= q_low) & (df['price'] <= q_high)]

    # 2. 建筑类型独热编码（保留所有记录，将不在核心类型中的归为“其他”）
    core_building_types = ["低层", "多层", "小高层", "高层", "超高层"]

    # 提取主要类型（取第一个出现的核心类型）
    def extract_main_building_type(btype):
        if pd.isna(btype):
            return "未知"
        for bt in core_building_types:
            if bt in str(btype):
                return bt
        return "其他"

    df['building_type_main'] = df['building_type'].apply(extract_main_building_type)
    # 对主要类型进行独热编码
    df = pd.get_dummies(df, columns=['building_type_main'], prefix='building_type')
    # 确保所有核心类型列都存在
    for bt in core_building_types:
        col = f'building_type_{bt}'
        if col not in df.columns:
            df[col] = 0

    # 删除原始 building_type 列
    df.drop('building_type', axis=1, inplace=True)

    # 3. 房龄计算
    df["completion_year"] = df["completion_time"].apply(
        lambda x: extract_numeric_value(x, unit_list=["年"]) if pd.notna(x) else np.nan
    )
    df["house_age"] = df["completion_year"].apply(
        lambda x: CURRENT_YEAR - x if (pd.notna(x) and 1900 <= x <= CURRENT_YEAR) else np.nan
    )
    df["house_age"] = df["house_age"].apply(lambda x: 50 if x > 50 else x)
    df["house_age"].fillna(df["house_age"].median(), inplace=True)
    df.drop(["completion_time", "completion_year"], axis=1, inplace=True)

    # 4. 数值特征处理（动态范围）
    numeric_config = {
        "property_right_years": {"unit": ["年"]},
        "property_fee": {"unit": ["元/㎡·月"]},
        "plot_ratio": {"unit": []},
        "greening_rate": {"unit": ["%"]}
    }
    for field, cfg in numeric_config.items():
        df[field] = df[field].apply(extract_numeric_value, unit_list=cfg["unit"])
        # 用 1% 和 99% 分位数截断
        q_low_field, q_high_field = df[field].quantile(0.01), df[field].quantile(0.99)
        df[field] = df[field].clip(lower=q_low_field, upper=q_high_field)
        df[field].fillna(df[field].median(), inplace=True)

    # 5. 添加非线性特征
    df = add_nonlinear_features(df)

    # 6. 城市目标编码（alpha=2）
    df["city_encoded"], encoding_maps = target_encoding(df, "city", "price", alpha=2)
    df.drop("city", axis=1, inplace=True)

    # 7. 类别字段规范化
    df["property_type"] = df["property_type"].apply(
        lambda x: x if x in ["住宅", "公寓", "商铺", "写字楼", "别墅"] else "其他"
    )
    df["unified_heating"] = df["unified_heating"].apply(lambda x: x if x in ["是", "否"] else "未知")
    df["water_supply_power"] = df["water_supply_power"].apply(lambda x: x if x in ["民用", "商用"] else "未知")

    # 8. 最终特征选择
    feature_cols = [
                       "city_encoded",
                       "property_type", "unified_heating", "water_supply_power",
                       "property_right_years", "property_fee", "plot_ratio", "greening_rate", "house_age",
                       "house_age_sq", "plot_ratio_log", "property_fee_sqrt"
                   ] + [col for col in df.columns if col.startswith('building_type_')]

    X = df[[col for col in feature_cols if col in df.columns]]
    y = df['price']
    return X, y, encoding_maps


def train_models_with_search():
    """
    主训练流程：加载数据、预处理、随机搜索调参、评估、保存模型。
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
    stratify = X["property_type"] if X["property_type"].nunique() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=stratify
    )

    # ---------- 定义特征处理器 ----------
    numeric_features = [
        "city_encoded", "property_right_years", "property_fee", "plot_ratio",
        "greening_rate", "house_age", "house_age_sq", "plot_ratio_log",
        "property_fee_sqrt", "building_type_低层", "building_type_多层",
        "building_type_小高层", "building_type_高层", "building_type_超高层"
    ]
    categorical_features = ["property_type", "unified_heating", "water_supply_power"]

    numeric_features = [f for f in numeric_features if f in X.columns]
    categorical_features = [f for f in categorical_features if f in X.columns]

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), numeric_features),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
    ])

    # ========== 随机森林参数搜索 ==========
    print("\n开始随机森林参数搜索...")
    # 定义基础 pipeline
    rf_base = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(random_state=42, n_jobs=-1))
    ])

    # 参数分布
    rf_param_dist = {
        'regressor__n_estimators': randint(100, 500),
        'regressor__max_depth': randint(5, 20),
        'regressor__min_samples_split': randint(2, 20),
        'regressor__min_samples_leaf': randint(1, 10),
        'regressor__max_features': ['sqrt', 'log2', None],
    }

    # 随机搜索对象
    rf_search = RandomizedSearchCV(
        rf_base,
        rf_param_dist,
        n_iter=15,  # 随机采样15个参数组合
        cv=2,  # 3折交叉验证
        scoring='r2',
        random_state=42,
        n_jobs=-1,
        verbose=1,
        return_train_score=False  # 只保留测试分数，减少计算量
    )

    rf_search.fit(X_train, y_train)

    print("\n随机森林最佳参数:")
    for param, value in rf_search.best_params_.items():
        print(f"  {param}: {value}")
    print(f"最佳交叉验证 R²: {rf_search.best_score_:.4f}")

    # ========== LightGBM 参数搜索 ==========
    print("\n开始 LightGBM 参数搜索...")
    lgb_base = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", LGBMRegressor(random_state=42, n_jobs=-1, verbose=-1))
    ])

    lgb_param_dist = {
        'regressor__n_estimators': randint(100, 500),
        'regressor__max_depth': randint(3, 15),
        'regressor__learning_rate': uniform(0.01, 0.2),  # 0.01 ~ 0.21
        'regressor__num_leaves': randint(20, 100),
        'regressor__subsample': uniform(0.6, 0.4),  # 0.6 ~ 1.0
        'regressor__colsample_bytree': uniform(0.6, 0.4),
        'regressor__reg_alpha': uniform(0, 0.5),
        'regressor__reg_lambda': uniform(0, 0.5),
    }

    lgb_search = RandomizedSearchCV(
        lgb_base,
        lgb_param_dist,
        n_iter=15,
        cv=2,
        scoring='r2',
        random_state=42,
        n_jobs=-1,
        verbose=1,
        return_train_score=False
    )

    lgb_search.fit(X_train, y_train)

    print("\nLightGBM 最佳参数:")
    for param, value in lgb_search.best_params_.items():
        print(f"  {param}: {value}")
    print(f"最佳交叉验证 R²: {lgb_search.best_score_:.4f}")

    # ========== 在测试集上评估最佳模型 ==========
    def evaluate(pipeline, X_tr, y_tr, X_te, y_te):
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

    rf_best = rf_search.best_estimator_
    lgb_best = lgb_search.best_estimator_

    rf_metrics = evaluate(rf_best, X_train, y_train, X_test, y_test)
    lgb_metrics = evaluate(lgb_best, X_train, y_train, X_test, y_test)

    print("\n" + "=" * 50)
    print("模型评估对比（最佳参数）")
    print("=" * 50)
    print(f"{'指标':15} {'随机森林':>10} {'LightGBM':>10}")
    for key in ["train_mae", "train_mse", "train_r2", "test_mae", "test_mse", "test_r2"]:
        rf_val = rf_metrics[key]
        lgb_val = lgb_metrics[key]
        print(f"{key:15} {rf_val:10.2f} {lgb_val:10.2f}")

    # ---------- 保存最佳模型和编码映射 ----------
    joblib.dump(rf_best, RF_MODEL_SAVE_PATH)
    joblib.dump(lgb_best, LGBM_MODEL_SAVE_PATH)
    joblib.dump(encoding_maps, ENCODING_MAP_SAVE_PATH)
    print(f"\n模型已保存至：{RF_MODEL_SAVE_PATH} 和 {LGBM_MODEL_SAVE_PATH}")
    print(f"编码映射保存至：{ENCODING_MAP_SAVE_PATH}")


if __name__ == "__main__":
    # 创建 Flask 应用上下文，以便使用数据库连接
    app = create_app()
    with app.app_context():
        train_models_with_search()
