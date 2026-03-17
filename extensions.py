import logging
import os
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
cache = Cache()
csrf = CSRFProtect()


def setup_logging(app):
    """配置日志，确保日志目录存在"""
    if not app.debug:
        log_file = app.config['LOG_FILE']
        # 确保日志文件所在目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
