import logging
from app import app
from db import db
from model.User import User
from model.History import History
from model.Community_info import Community_info

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_tables():
    """创建数据库表（带异常处理）"""
    try:
        # 推送应用上下文
        with app.app_context():
            # 创建所有表
            db.create_all()
            logger.info("数据库表创建成功！")
    except Exception as e:
        logger.error(f"创建表失败：{str(e)}")
        raise  # 抛出异常便于调试


if __name__ == '__main__':
    create_tables()
