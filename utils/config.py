# 数据库连接配置
DB_CONFIG = {
    "host": "192.168.224.128",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "house_data",
    "charset": "utf8mb4",
}

# 连接池配置
POOL_CONFIG = {
    "maxconnections": 10,
    "mincached": 2,
    "maxcached": 5,
}

# 模型文件路径
RF_MODEL_PATH = "./pred/house_price_prediction_model_rf.pkl"
LGBM_MODEL_PATH = "./pred/house_price_prediction_model_lgbm.pkl"
ENCODING_MAPS_PATH = "./pred/target_encoding_maps.pkl"
