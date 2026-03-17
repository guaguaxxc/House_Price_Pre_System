"""
用户预测历史模型
================================================
对应数据库中的 history 表，存储每个用户进行的房价预测记录。
包含预测的城市、预测结果价格以及关联的用户ID。
"""

from extensions import db


class History(db.Model):
    """
    预测历史记录模型，映射数据库表 history。
    每条记录对应一次房价预测操作。
    """
    __tablename__ = 'history'  # 数据库表名

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
        comment="自增主键，唯一标识每条预测历史记录"
    )
    city = db.Column(
        db.String(255),
        nullable=True,
        comment="预测时选择的城市名称，如'北京'"
    )
    price = db.Column(
        db.String(255),
        nullable=True,
        comment="预测结果价格（字符串形式，包含单位'元/㎡'），如'65000 元/㎡'"
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.user_id'),  # 外键关联 user 表的 user_id
        nullable=True,
        comment="关联的用户ID，标识是哪位用户的预测记录"
    )

    # 注意：user 关系在 User 模型中通过 backref 定义，此处无需重复声明
