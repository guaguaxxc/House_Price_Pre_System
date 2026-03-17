from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
import logging

db = SQLAlchemy()
cache = Cache()
csrf = CSRFProtect()

# 日志配置
def setup_logging(app):
    if not app.debug:
        handler = logging.FileHandler(app.config['LOG_FILE'])
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)