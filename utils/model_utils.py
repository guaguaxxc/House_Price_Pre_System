"""
模型训练工具函数模块
================================================
提供模型训练过程中常用的数据处理函数，包括：
    - 从字符串中提取数值
    - 目标编码（带平滑）
    - 添加非线性特征（房龄平方、容积率对数、物业费平方根）
"""
import re
import numpy as np
import pandas as pd
from datetime import datetime

CURRENT_YEAR = datetime.now().year  # 用于房龄计算的当前年份


def extract_numeric_value(val, unit_list=None):
    """
    从字符串中提取第一个数值（整数或小数），并移除可能包含的单位。
    例如：
        "65000元/㎡" → 65000.0
        "30%" → 30.0
        "暂无" → NaN
    :param val: 原始输入值（可能是字符串、数字或NaN）
    :param unit_list: list - 需要从字符串中移除的单位列表，如 ["元/㎡", "年", "%"]
                      若为None，使用默认单位列表。
    :return: float 或 np.nan - 提取到的数值，若无法提取则返回NaN
    """
    # 处理无效值
    if pd.isna(val) or str(val).strip() in ["暂无", "无", "未知", ""]:
        return np.nan

    # 默认单位列表，涵盖常见的单位
    unit_list = unit_list or ["年", "%", "元/m²", "元/㎡", "元/㎡·月", "元/㎡月"]

    val_str = str(val).strip()
    # 移除所有单位
    for unit in unit_list:
        val_str = val_str.replace(unit, "")

    # 使用正则提取第一个数字（支持整数和小数）
    match = re.search(r'(\d+\.?\d*)', val_str)
    return float(match.group()) if match else np.nan


def target_encoding(df, group_col, target_col, alpha=5):
    """
    对类别特征进行目标编码（Target Encoding），并加入平滑处理以避免过拟合。
    编码值计算公式：
        encoded = (count * mean + alpha * global_mean) / (count + alpha)
    :param df: pandas DataFrame - 包含原始数据的DataFrame
    :param group_col: str - 需要进行编码的类别列名
    :param target_col: str - 目标变量列名（用于计算均值）
    :param alpha: int - 平滑参数，alpha越大，编码值越向全局均值收缩
    :return: (encoded_series, encoding_map)
             encoded_series: pd.Series - 编码后的数值序列
             encoding_map: dict - 类别到编码值的映射，包含一个 "UNKNOWN" 键用于处理未见过的类别
    """
    # 按类别分组，计算均值和计数
    cat_stats = df.groupby(group_col).agg(
        mean=(target_col, 'mean'),
        count=(target_col, 'count')
    ).reset_index()
    # 全局目标均值
    global_mean = df[target_col].mean()
    # 计算平滑后的编码值
    cat_stats["encoded"] = (cat_stats["count"] * cat_stats["mean"] + alpha * global_mean) / (cat_stats["count"] + alpha)
    # 构建编码映射
    encoding_map = dict(zip(cat_stats[group_col], cat_stats["encoded"]))
    encoding_map["UNKNOWN"] = global_mean  # 添加未知类别的默认值
    # 对原始列进行编码，未匹配到的用全局均值填充
    encoded_series = df[group_col].map(encoding_map).fillna(global_mean)
    return encoded_series, encoding_map


def add_nonlinear_features(df):
    """
    在DataFrame中添加非线性特征，以增强模型对复杂关系的拟合能力。
    添加的特征包括：
        - house_age_sq: 房龄的平方
        - plot_ratio_log: 容积率的对数（使用 log1p 避免负值）
        - property_fee_sqrt: 物业费的平方根
    :param df: pandas DataFrame - 必须包含 'house_age', 'plot_ratio', 'property_fee' 列
    :return: pandas DataFrame - 包含新增特征的新DataFrame（原DataFrame不变）
    """
    df_new = df.copy()
    df_new["house_age_sq"] = df_new["house_age"] ** 2
    df_new["plot_ratio_log"] = np.log1p(df_new["plot_ratio"])  # log(1+x)
    df_new["property_fee_sqrt"] = np.sqrt(df_new["property_fee"])
    return df_new
