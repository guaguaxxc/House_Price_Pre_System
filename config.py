"""
应用配置文件
================================================
使用环境变量或默认值定义应用的所有配置项，包括密钥、数据库连接、缓存、日志和模型路径。
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量（如果有）
load_dotenv()


class Config:
    """应用配置类，所有配置项均为类属性"""
    # Flask 密钥，用于会话安全
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # ================= 数据库配置 =================
    # 数据库连接 URI，格式：mysql+pymysql://用户名:密码@主机/数据库名
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root:root@192.168.224.128/house_data')
    # 关闭 SQLAlchemy 的修改跟踪，节省内存
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ================= 缓存配置 =================
    CACHE_TYPE = 'SimpleCache'           # 使用简单内存缓存（适合开发）
    CACHE_DEFAULT_TIMEOUT = 300          # 默认缓存超时时间（秒）

    # ================= 日志配置 =================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')   # 日志级别
    LOG_FILE = 'logs/app.log'                     # 日志文件路径（相对项目根目录）

    # ================= 模型文件路径 =================
    # 训练好的随机森林模型
    RF_MODEL_PATH = './pred/house_price_prediction_model_rf.pkl'
    # 训练好的 LightGBM 模型
    LGBM_MODEL_PATH = './pred/house_price_prediction_model_lgbm.pkl'
    # 目标编码映射字典
    ENCODING_MAPS_PATH = './pred/target_encoding_maps.pkl'