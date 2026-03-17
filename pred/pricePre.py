import pandas as pd
import numpy as np
import pymysql
import re
import warnings
from datetime import datetime
from dbutils.pooled_db import PooledDB
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
# 新增LightGBM导入
from lightgbm import LGBMRegressor

# 基础配置
warnings.filterwarnings('ignore')
# 新增LightGBM模型保存路径
RF_MODEL_SAVE_PATH = './house_price_prediction_model_rf.pkl'
LGBM_MODEL_SAVE_PATH = './house_price_prediction_model_lgbm.pkl'
ENCODING_MAP_SAVE_PATH = './target_encoding_maps.pkl'
CURRENT_YEAR = datetime.now().year

# -------------------------- 1. 数据库配置（不变） --------------------------
DB_CONFIG = {
    'host': '192.168.224.128',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'house_data',
    'charset': 'utf8mb4',
    'maxconnections': 10,
    'mincached': 2,
    'maxcached': 5,
}
TABLE_NAME = "community_info"
FEATURE_FIELDS = [
    "city", "property_type", "completion_time", "property_right_years",
    "property_fee", "plot_ratio", "greening_rate", "building_type",
    "unified_heating", "water_supply_power"
]
TARGET_FIELD = "price"

# 创建数据库连接池
try:
    POOL = PooledDB(creator=pymysql, **DB_CONFIG)
    print("【数据库】连接池创建成功")
except Exception as e:
    print(f"【数据库】连接池创建失败：{str(e)}")
    exit()

# -------------------------- 2. 核心工具函数（不变） --------------------------
def extract_numeric_value(val, unit_list=None):
    if pd.isna(val) or str(val).strip() in ["暂无", "无", "未知", ""]:
        return np.nan
    unit_list = unit_list or ["年", "%", "元/m²", "元/㎡", "元/㎡·月", "元/㎡月"]
    val_str = str(val).strip()
    for unit in unit_list:
        val_str = val_str.replace(unit, "")
    match = re.search(r'(\d+\.?\d*)', val_str)
    return float(match.group()) if match else np.nan

def target_encoding(df, group_col, target_col, alpha=5):
    """修复后的目标编码（用字段名分组）"""
    cat_stats = df.groupby(group_col).agg(
        mean=(target_col, 'mean'),
        count=(target_col, 'count')
    ).reset_index()
    global_mean = df[target_col].mean()
    cat_stats["encoded"] = (cat_stats["count"] * cat_stats["mean"] + alpha * global_mean) / (cat_stats["count"] + alpha)
    encoding_map = dict(zip(cat_stats[group_col], cat_stats["encoded"]))
    encoding_map["UNKNOWN"] = global_mean
    encoded_series = df[group_col].map(encoding_map).fillna(global_mean)
    return encoded_series, encoding_map

def add_nonlinear_features(df):
    """新增非线性特征"""
    df_new = df.copy()
    df_new["house_age_sq"] = df_new["house_age"] ** 2
    df_new["plot_ratio_log"] = np.log1p(df_new["plot_ratio"])
    df_new["property_fee_sqrt"] = np.sqrt(df_new["property_fee"])
    return df_new

# -------------------------- 3. 数据库数据读取（不变） --------------------------
def load_data_from_db():
    conn, cursor = None, None
    try:
        conn = POOL.connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        query_fields = FEATURE_FIELDS + [TARGET_FIELD]
        sql = f"""
            SELECT {','.join(query_fields)} 
            FROM {TABLE_NAME} 
            WHERE {TARGET_FIELD} IS NOT NULL 
              AND {TARGET_FIELD} != ''
        """
        cursor.execute(sql)
        df = pd.DataFrame(cursor.fetchall())
        print(f"【数据库】查询到有效数据：{len(df)} 条")
        return df
    except Exception as e:
        print(f"【数据库】查询失败：{str(e)}")
        return pd.DataFrame()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# -------------------------- 4. 数据预处理（不变） --------------------------
def preprocess_data(raw_df, is_train=True, encoding_maps=None):
    df = raw_df.copy(deep=True)
    print(f"【预处理】原始数据量：{len(df)} 条")
    encoding_maps = encoding_maps or {}

    # 1. 目标字段处理
    if TARGET_FIELD in df.columns and is_train:
        df[TARGET_FIELD] = df[TARGET_FIELD].apply(extract_numeric_value, unit_list=["元/m²", "元/㎡"])
        price_q8 = df[TARGET_FIELD].quantile(0.08)
        price_q92 = df[TARGET_FIELD].quantile(0.92)
        df = df[(df[TARGET_FIELD] >= price_q8) & (df[TARGET_FIELD] <= price_q92)]
        print(f"【预处理】房价异常值过滤后：{len(df)} 条")

    # 2. 建筑类型独热编码
    core_building_types = ["低层", "多层", "小高层", "高层", "超高层"]
    df = df[df["building_type"].apply(
        lambda x: any(bt in str(x) for bt in core_building_types) if pd.notna(x) else False
    )]
    for bt in core_building_types:
        df[f"building_type_{bt}"] = df["building_type"].apply(lambda x: 1 if bt in str(x) else 0)
    df.drop("building_type", axis=1, inplace=True)
    print(f"【预处理】建筑类型独热编码后：{len(df)} 条")

    # 3. 竣工时间转房龄
    df["completion_year"] = df["completion_time"].apply(
        lambda x: extract_numeric_value(x, unit_list=["年"]) if pd.notna(x) else np.nan
    )
    df["house_age"] = df["completion_year"].apply(
        lambda x: CURRENT_YEAR - x if (pd.notna(x) and 1900 <= x <= CURRENT_YEAR) else np.nan
    )
    df["house_age"] = df["house_age"].apply(lambda x: 50 if x > 50 else x)
    df["house_age"].fillna(df["house_age"].median(), inplace=True)
    df.drop(["completion_time", "completion_year"], axis=1, inplace=True)
    print(f"【预处理】房龄计算后：{len(df)} 条")

    # 4. 数值特征处理
    numeric_config = {
        "property_right_years": {"unit": ["年"], "max":70, "min":40},
        "property_fee": {"unit": ["元/㎡·月"], "max":10, "min":0.5},
        "plot_ratio": {"unit": [], "max":4, "min":0.5},
        "greening_rate": {"unit": ["%"], "max":50, "min":10}
    }
    for field, cfg in numeric_config.items():
        df[field] = df[field].apply(extract_numeric_value, unit_list=cfg["unit"])
        df[field] = df[field].apply(lambda x: cfg["max"] if x > cfg["max"] else (cfg["min"] if x < cfg["min"] else x))
        df[field].fillna(df[field].median(), inplace=True)
    print(f"【预处理】数值特征范围限制后：{len(df)} 条")

    # 5. 新增非线性特征
    df = add_nonlinear_features(df)
    print(f"【预处理】新增非线性特征后：{len(df.columns)} 个字段")

    # 6. 城市字段目标编码
    target_encode_fields = ["city"]
    if is_train and TARGET_FIELD in df.columns:
        for field in target_encode_fields:
            df[f"{field}_encoded"], encoding_maps[field] = target_encoding(
                df=df, group_col=field, target_col=TARGET_FIELD, alpha=5
            )
        joblib.dump(encoding_maps, ENCODING_MAP_SAVE_PATH)
        print(f"【预处理】目标编码映射已保存至：{ENCODING_MAP_SAVE_PATH}")
    elif not is_train and encoding_maps:
        for field in target_encode_fields:
            if field in encoding_maps:
                df[f"{field}_encoded"] = df[field].map(encoding_maps[field]).fillna(encoding_maps[field]["UNKNOWN"])
            else:
                print(f"【警告】预测阶段缺少 {field} 的编码映射")
                df[f"{field}_encoded"] = 0
    df.drop(target_encode_fields, axis=1, inplace=True)
    print(f"【预处理】目标编码后：{len(df.columns)} 个字段")

    # 7. 其他类别字段规范（仍为字符串类型，后续需编码）
    df["property_type"] = df["property_type"].apply(
        lambda x: x if x in ["住宅", "公寓", "商铺", "写字楼", "别墅"] else "其他"
    )
    df["unified_heating"] = df["unified_heating"].apply(lambda x: x if x in ["是", "否"] else "未知")
    df["water_supply_power"] = df["water_supply_power"].apply(lambda x: x if x in ["民用", "商用"] else "未知")

    # 8. 最终特征筛选
    final_feature_cols = [
        "city_encoded",
        "property_type", "unified_heating", "water_supply_power",  # 字符串类别特征
        "property_right_years", "property_fee", "plot_ratio", "greening_rate", "house_age",
        "house_age_sq", "plot_ratio_log", "property_fee_sqrt",
        "building_type_低层", "building_type_多层", "building_type_小高层", "building_type_高层", "building_type_超高层"
    ]
    final_feature_cols = [col for col in final_feature_cols if col in df.columns]
    X = df[final_feature_cols]
    y = df[TARGET_FIELD] if (TARGET_FIELD in df.columns and is_train) else None

    print(f"【预处理】最终特征：{len(final_feature_cols)} 个，有效样本：{len(X)} 条")
    return (X, y, encoding_maps) if is_train else X

# -------------------------- 5. 模型训练（新增LightGBM对比） --------------------------
def train_contrast_models():
    raw_df = load_data_from_db()
    if len(raw_df) < 200:
        print(f"【训练】有效数据不足（{len(raw_df)}条），需≥200条")
        return None, None

    X, y, encoding_maps = preprocess_data(raw_df, is_train=True)
    if len(X) < 200:
        print(f"【训练】预处理后数据不足（{len(X)}条），终止训练")
        return None, None

    # 分层抽样（不变）
    stratify_col = X["property_type"] if len(X["property_type"].unique()) >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=stratify_col
    )
    print(f"【训练】分层抽样：训练集{len(X_train)}条，测试集{len(X_test)}条")

    # 特征处理器（通用，两个模型共用）
    numeric_features = [
        "city_encoded", "property_right_years", "property_fee", "plot_ratio",
        "greening_rate", "house_age", "house_age_sq", "plot_ratio_log",
        "property_fee_sqrt", "building_type_低层", "building_type_多层",
        "building_type_小高层", "building_type_高层", "building_type_超高层"
    ]
    categorical_features = ["property_type", "unified_heating", "water_supply_power"]
    # 筛选实际存在的特征
    numeric_features = [col for col in numeric_features if col in X.columns]
    categorical_features = [col for col in categorical_features if col in X.columns]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        ],
        remainder="drop"
    )

    # 1. 随机森林模型Pipeline
    rf_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(
            n_estimators=150,
            max_depth=8,
            min_samples_split=20,
            min_samples_leaf=5,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1
        ))
    ])

    # 2. LightGBM模型Pipeline
    lgbm_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", LGBMRegressor(
            n_estimators=150,
            max_depth=8,
            learning_rate=0.1,
            num_leaves=31,
            min_child_samples=5,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbose=-1  # 关闭LightGBM日志输出
        ))
    ])

    # 训练两个模型
    print("\n【训练】开始训练随机森林模型...")
    rf_pipeline.fit(X_train, y_train)
    print("\n【训练】开始训练LightGBM模型...")
    lgbm_pipeline.fit(X_train, y_train)

    # 评估两个模型
    def evaluate_model(pipeline, X_train, y_train, X_test, y_test, model_name):
        y_pred_train = pipeline.predict(X_train)
        y_pred_test = pipeline.predict(X_test)
        metrics = {
            "训练集MAE": mean_absolute_error(y_train, y_pred_train),
            "训练集MSE": mean_squared_error(y_train, y_pred_train),
            "训练集R²": r2_score(y_train, y_pred_train),
            "测试集MAE": mean_absolute_error(y_test, y_pred_test),
            "测试集MSE": mean_squared_error(y_test, y_pred_test),
            "测试集R²": r2_score(y_test, y_pred_test)
        }
        r2_gap = metrics["训练集R²"] - metrics["测试集R²"]
        metrics["R²差距"] = r2_gap
        return metrics, r2_gap

    # 评估随机森林
    rf_metrics, rf_r2_gap = evaluate_model(rf_pipeline, X_train, y_train, X_test, y_test, "随机森林")
    # 评估LightGBM
    lgbm_metrics, lgbm_r2_gap = evaluate_model(lgbm_pipeline, X_train, y_train, X_test, y_test, "LightGBM")

    # 输出对比结果
    print("\n" + "="*80)
    print("【训练】模型对比评估结果")
    print("="*80)
    # 构建对比表格
    metrics_keys = ["训练集MAE", "训练集MSE", "训练集R²", "测试集MAE", "测试集MSE", "测试集R²", "R²差距"]
    print(f"{'指标':12s} | {'随机森林':12s} | {'LightGBM':12s} | {'更优模型':12s}")
    print("-"*80)
    for key in metrics_keys:
        rf_val = rf_metrics[key]
        lgbm_val = lgbm_metrics[key]
        # 判断更优模型：MAE/MSE/R²差距越小越好，R²越大越好
        if "R²" in key and key != "R²差距":
            best_model = "LightGBM" if lgbm_val > rf_val else "随机森林"
        else:
            best_model = "LightGBM" if lgbm_val < rf_val else "随机森林"
        print(f"{key:12s} | {rf_val:12.2f} | {lgbm_val:12.2f} | {best_model:12s}")

    # 过拟合判断
    print("\n【训练】过拟合分析")
    for model_name, r2_gap in [("随机森林", rf_r2_gap), ("LightGBM", lgbm_r2_gap)]:
        if r2_gap <= 0.15:
            print(f"{model_name}：过拟合缓解（R²差距={r2_gap:.2f} ≤ 0.15）")
        else:
            print(f"{model_name}：仍存在过拟合（R²差距={r2_gap:.2f} > 0.15）")

    # 保存两个模型
    try:
        joblib.dump(rf_pipeline, RF_MODEL_SAVE_PATH)
        joblib.dump(lgbm_pipeline, LGBM_MODEL_SAVE_PATH)
        print(f"\n【训练】模型保存完成：")
        print(f"- 随机森林模型：{RF_MODEL_SAVE_PATH}")
        print(f"- LightGBM模型：{LGBM_MODEL_SAVE_PATH}")
    except Exception as e:
        print(f"【训练】模型保存失败：{str(e)}")
        return None, None

    return rf_pipeline, lgbm_pipeline

# -------------------------- 6. 预测函数（支持指定模型类型） --------------------------
def predict_new_price(new_data_df, model_type="rf"):
    """
    预测房价
    :param new_data_df: 新数据DataFrame
    :param model_type: 模型类型，可选 'rf'（随机森林）或 'lgbm'（LightGBM）
    :return: 预测结果列表
    """
    # 选择模型路径
    if model_type == "rf":
        model_path = RF_MODEL_SAVE_PATH
    elif model_type == "lgbm":
        model_path = LGBM_MODEL_SAVE_PATH
    else:
        print(f"【预测】不支持的模型类型：{model_type}，默认使用随机森林")
        model_path = RF_MODEL_SAVE_PATH

    try:
        model = joblib.load(model_path)
        encoding_maps = joblib.load(ENCODING_MAP_SAVE_PATH)
        print(f"【预测】{model_type.upper()}模型和编码映射加载成功")
    except Exception as e:
        print(f"【预测】加载资源失败：{str(e)}")
        return None

    X_new = preprocess_data(new_data_df, is_train=False, encoding_maps=encoding_maps)
    if X_new.empty:
        print("【预测】预处理后无有效特征")
        return None

    try:
        predictions = model.predict(X_new)
        return [round(p, 2) for p in predictions]
    except Exception as e:
        print(f"【预测】计算失败：{str(e)}")
        return None

# -------------------------- 7. 执行入口（新增模型对比预测） --------------------------
if __name__ == "__main__":
    print("="*80)
    print("【主流程】开始训练房价预测模型（随机森林 + LightGBM 对比）")
    print("="*80)
    rf_model, lgbm_model = train_contrast_models()
    if not rf_model or not lgbm_model:
        print("【主流程】模型训练失败")
        exit()

    print("\n" + "="*80)
    print("【主流程】模型示例预测对比")
    print("="*80)
    new_house_data = pd.DataFrame({
        "city": ["鞍山市", "大连市", "沈阳市"],
        "property_type": ["住宅", "公寓", "商铺"],
        "completion_time": ["2015年", "2020年", "2008年"],
        "property_right_years": ["70年", "40年", "50年"],
        "property_fee": ["1.5元/㎡·月", "2.8元/㎡·月", "3.2元/㎡·月"],
        "plot_ratio": ["2.2", "3.5", "1.8"],
        "greening_rate": ["35%", "28%", "42%"],
        "building_type": ["多层|小高层", "高层", "低层"],
        "unified_heating": ["是", "否", "是"],
        "water_supply_power": ["民用", "商用", "民用"]
    })

    # 分别用两个模型预测
    rf_predictions = predict_new_price(new_house_data, model_type="rf")
    lgbm_predictions = predict_new_price(new_house_data, model_type="lgbm")

    # 合并预测结果
    if rf_predictions and lgbm_predictions:
        new_house_data["随机森林预测（元/m²）"] = rf_predictions
        new_house_data["LightGBM预测（元/m²）"] = lgbm_predictions
        new_house_data["预测差值（元/m²）"] = abs(new_house_data["LightGBM预测（元/m²）"] - new_house_data["随机森林预测（元/m²）"])
        print("新数据预测结果对比：")
        print(new_house_data[["city", "property_type", "building_type", "随机森林预测（元/m²）", "LightGBM预测（元/m²）", "预测差值（元/m²）"]].to_string(index=False))
    else:
        print("【主流程】示例预测失败")