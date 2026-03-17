"""
数据库表创建脚本
================================================
在应用上下文中调用 db.create_all() 创建所有数据库表。
可在首次部署或模型变更后运行此脚本。
"""

import logging
from app import app
from extensions import db

# 配置日志输出格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_tables():
    """
    在应用上下文中创建所有数据库表。

    异常处理：若创建失败，记录错误日志并抛出异常。
    """
    try:
        # 推送应用上下文，以便使用数据库连接
        with app.app_context():
            # 创建所有通过 SQLAlchemy 定义的表
            db.create_all()
            logger.info("数据库表创建成功！")
    except Exception as e:
        logger.error(f"创建表失败：{str(e)}")
        raise  # 抛出异常便于调用者调试


if __name__ == '__main__':
    create_tables()
