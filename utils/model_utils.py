# utils/model_utils.py
import re
import numpy as np
import pandas as pd
from datetime import datetime

CURRENT_YEAR = datetime.now().year


def extract_numeric_value(val, unit_list=None):
    """从字符串中提取数字，支持单位去除"""
    if pd.isna(val) or str(val).strip() in ["暂无", "无", "未知", ""]:
        return np.nan
    unit_list = unit_list or ["年", "%", "元/m²", "元/㎡", "元/㎡·月", "元/㎡月"]
    val_str = str(val).strip()
    for unit in unit_list:
        val_str = val_str.replace(unit, "")
    match = re.search(r'(\d+\.?\d*)', val_str)
    return float(match.group()) if match else np.nan


def target_encoding(df, group_col, target_col, alpha=5):
    """目标编码（带平滑）"""
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
    """添加房龄平方、容积率对数、物业费平方根"""
    df_new = df.copy()
    df_new["house_age_sq"] = df_new["house_age"] ** 2
    df_new["plot_ratio_log"] = np.log1p(df_new["plot_ratio"])
    df_new["property_fee_sqrt"] = np.sqrt(df_new["property_fee"])
    return df_new
