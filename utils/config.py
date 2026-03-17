"""
配置文件
================================================
包含数据库连接配置、连接池设置以及训练好的模型文件路径。
所有配置均以字典形式提供，便于其他模块导入使用。
"""

# 数据库连接配置
DB_CONFIG = {
    "host": "192.168.224.128",  # 数据库主机地址
    "port": 3306,  # 数据库端口，MySQL默认3306
    "user": "root",  # 数据库用户名
    "password": "root",  # 数据库密码
    "database": "house_data",  # 要连接的数据库名称
    "charset": "utf8mb4",  # 字符集，支持emoji等
}

# 数据库连接池配置
POOL_CONFIG = {
    "maxconnections": 10,  # 连接池允许的最大连接数
    "mincached": 2,  # 初始化时至少创建的空闲连接数
    "maxcached": 5,  # 连接池中最多允许的空闲连接数
}

# 训练好的模型文件路径（用于房价预测）
RF_MODEL_PATH = "./pred/house_price_prediction_model_rf.pkl"  # 随机森林模型
LGBM_MODEL_PATH = "./pred/house_price_prediction_model_lgbm.pkl"  # LightGBM模型
ENCODING_MAPS_PATH = "./pred/target_encoding_maps.pkl"  # 目标编码映射字典
