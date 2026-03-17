"""
扩展初始化模块
================================================
集中初始化 Flask 扩展实例（SQLAlchemy、Cache、CSRF），
并提供日志配置函数，避免循环导入。
"""

import logging
import os
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect

# 创建扩展实例
db = SQLAlchemy()
cache = Cache()
csrf = CSRFProtect()


def setup_logging(app):
    """
    配置应用日志，将 INFO 级别及以上的日志写入文件。
    步骤：
        1. 检查是否为调试模式（调试模式下不写文件，避免干扰）
        2. 获取日志文件路径，并确保目录存在
        3. 创建文件处理器，设置格式
        4. 将处理器添加到 app.logger
    :param app: Flask 应用实例
    """
    if not app.debug:  # 非调试模式下才写入文件
        log_file = app.config['LOG_FILE']
        # 确保日志文件所在目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 创建文件处理器
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)  # 只记录 INFO 及以上级别

        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        # 将处理器添加到应用日志器
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
