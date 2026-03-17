# scripts/train_model.py
import pandas as pd
import numpy as np
import joblib
import sys
import os

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

CURRENT_YEAR = datetime.now().year
RF_MODEL_SAVE_PATH = './pred/house_price_prediction_model_rf.pkl'
LGBM_MODEL_SAVE_PATH = './pred/house_price_prediction_model_lgbm.pkl'
ENCODING_MAP_SAVE_PATH = './pred/target_encoding_maps.pkl'
import os

os.makedirs(os.path.dirname(RF_MODEL_SAVE_PATH), exist_ok=True)
os.makedirs(os.path.dirname(LGBM_MODEL_SAVE_PATH), exist_ok=True)


def load_data_from_db():
    """使用 SQLAlchemy 加载数据，返回 DataFrame"""
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
    """训练专用的预处理，返回 X, y, encoding_maps"""
    # 提取目标变量
    df['price'] = df['price'].apply(extract_numeric_value, unit_list=["元/m²", "元/㎡"])
    # 异常值过滤
    q_low, q_high = df['price'].quantile(0.08), df['price'].quantile(0.92)
    df = df[(df['price'] >= q_low) & (df['price'] <= q_high)]

    # 建筑类型独热编码
    core_building_types = ["低层", "多层", "小高层", "高层", "超高层"]
    df = df[df["building_type"].apply(
        lambda x: any(bt in str(x) for bt in core_building_types) if pd.notna(x) else False
    )]
    for bt in core_building_types:
        df[f"building_type_{bt}"] = df["building_type"].apply(lambda x: 1 if bt in str(x) else 0)
    df.drop("building_type", axis=1, inplace=True)

    # 房龄
    df["completion_year"] = df["completion_time"].apply(
        lambda x: extract_numeric_value(x, unit_list=["年"]) if pd.notna(x) else np.nan
    )
    df["house_age"] = df["completion_year"].apply(
        lambda x: CURRENT_YEAR - x if (pd.notna(x) and 1900 <= x <= CURRENT_YEAR) else np.nan
    )
    df["house_age"] = df["house_age"].apply(lambda x: 50 if x > 50 else x)
    df["house_age"].fillna(df["house_age"].median(), inplace=True)
    df.drop(["completion_time", "completion_year"], axis=1, inplace=True)

    # 数值特征
    numeric_config = {
        "property_right_years": {"unit": ["年"], "max": 70, "min": 40},
        "property_fee": {"unit": ["元/㎡·月"], "max": 10, "min": 0.5},
        "plot_ratio": {"unit": [], "max": 4, "min": 0.5},
        "greening_rate": {"unit": ["%"], "max": 50, "min": 10}
    }
    for field, cfg in numeric_config.items():
        df[field] = df[field].apply(extract_numeric_value, unit_list=cfg["unit"])
        df[field] = df[field].apply(lambda x: cfg["max"] if x > cfg["max"] else (cfg["min"] if x < cfg["min"] else x))
        df[field].fillna(df[field].median(), inplace=True)

    # 非线性特征
    df = add_nonlinear_features(df)

    # 目标编码城市
    df["city_encoded"], encoding_maps = target_encoding(df, "city", "price", alpha=5)
    df.drop("city", axis=1, inplace=True)

    # 类别字段规范
    df["property_type"] = df["property_type"].apply(
        lambda x: x if x in ["住宅", "公寓", "商铺", "写字楼", "别墅"] else "其他"
    )
    df["unified_heating"] = df["unified_heating"].apply(lambda x: x if x in ["是", "否"] else "未知")
    df["water_supply_power"] = df["water_supply_power"].apply(lambda x: x if x in ["民用", "商用"] else "未知")

    # 最终特征列
    feature_cols = [
        "city_encoded",
        "property_type", "unified_heating", "water_supply_power",
        "property_right_years", "property_fee", "plot_ratio", "greening_rate", "house_age",
        "house_age_sq", "plot_ratio_log", "property_fee_sqrt",
        "building_type_低层", "building_type_多层", "building_type_小高层", "building_type_高层", "building_type_超高层"
    ]
    X = df[[col for col in feature_cols if col in df.columns]]
    y = df['price']
    return X, y, encoding_maps


def train_models():
    df = load_data_from_db()
    if len(df) < 200:
        print(f"数据不足，当前{len(df)}条，需要≥200")
        return

    X, y, encoding_maps = preprocess_training_data(df)
    if len(X) < 200:
        print(f"预处理后数据不足{len(X)}条")
        return

    # 分层抽样
    stratify = X["property_type"] if X["property_type"].nunique() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=stratify
    )

    # 特征处理器
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

    # 随机森林
    rf_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(
            n_estimators=150, max_depth=8, min_samples_split=20,
            min_samples_leaf=5, max_features="sqrt", random_state=42, n_jobs=-1
        ))
    ])
    # LightGBM
    lgbm_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", LGBMRegressor(
            n_estimators=150, max_depth=8, learning_rate=0.1,
            num_leaves=31, min_child_samples=5, subsample=0.8,
            colsample_bytree=0.8, random_state=42, n_jobs=-1, verbose=-1
        ))
    ])

    print("训练随机森林...")
    rf_pipeline.fit(X_train, y_train)
    print("训练LightGBM...")
    lgbm_pipeline.fit(X_train, y_train)

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

    rf_metrics = evaluate(rf_pipeline, X_train, y_train, X_test, y_test)
    lgbm_metrics = evaluate(lgbm_pipeline, X_train, y_train, X_test, y_test)

    # 输出对比
    print("\n" + "=" * 50)
    print("模型评估对比")
    print("=" * 50)
    print(f"{'指标':15} {'随机森林':>10} {'LightGBM':>10}")
    for key in ["train_mae", "train_mse", "train_r2", "test_mae", "test_mse", "test_r2"]:
        rf_val = rf_metrics[key]
        lgbm_val = lgbm_metrics[key]
        print(f"{key:15} {rf_val:10.2f} {lgbm_val:10.2f}")

    # 保存模型和编码映射
    joblib.dump(rf_pipeline, RF_MODEL_SAVE_PATH)
    joblib.dump(lgbm_pipeline, LGBM_MODEL_SAVE_PATH)
    joblib.dump(encoding_maps, ENCODING_MAP_SAVE_PATH)
    print(f"\n模型已保存至：{RF_MODEL_SAVE_PATH} 和 {LGBM_MODEL_SAVE_PATH}")
    print(f"编码映射保存至：{ENCODING_MAP_SAVE_PATH}")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        train_models()
