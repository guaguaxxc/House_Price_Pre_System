import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # 数据库
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root:root@192.168.224.128/house_data')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 缓存
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300

    # 日志
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/app.log'

    # 模型路径
    RF_MODEL_PATH = './pred/house_price_prediction_model_rf.pkl'
    LGBM_MODEL_PATH = './pred/house_price_prediction_model_lgbm.pkl'
    ENCODING_MAPS_PATH = './pred/target_encoding_maps.pkl'
