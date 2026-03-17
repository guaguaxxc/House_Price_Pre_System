"""
用户信息模型
================================================
对应数据库中的 user 表，存储系统用户的登录信息。
包含用户名、密码以及与预测历史的一对多关系。
"""

from extensions import db


class User(db.Model):
    """
    用户模型类，映射数据库表 user。
    用于用户认证及关联预测历史记录。
    """
    __tablename__ = 'user'  # 数据库表名

    user_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
        comment="自增主键，唯一标识每个用户"
    )
    user_name = db.Column(
        db.String(255),
        nullable=True,
        unique=True,  # 用户名唯一，不可重复
        comment="用户名，用于登录，需唯一"
    )
    user_password = db.Column(
        db.String(255),
        nullable=True,
        comment="用户密码（建议存储哈希值，此处为简化使用明文，实际生产应加密）"
    )

    # 一对多关系：一个用户可以有多次预测历史
    # backref='user' 允许从 History 对象直接访问其所属用户，如 history.user
    # lazy=True 表示当访问 User.histories 时，返回一个可用的查询对象（默认未加载）
    histories = db.relationship(
        'History',
        backref='user',
        lazy=True
        # 注意：relationship 不支持 comment 参数，已移除
    )
