"""
用户认证表单模块
================================================
该模块定义了用户登录和注册的 Flask-WTF 表单，
包含用户名、密码等字段，并配置了长度验证和密码一致性验证。
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


class LoginForm(FlaskForm):
    """
    用户登录表单。
    """
    username = StringField(
        '用户名',
        validators=[DataRequired(), Length(1, 20)]  # 必填，长度1-20
    )
    password = PasswordField(
        '密码',
        validators=[DataRequired()]  # 必填
    )
    submit = SubmitField('登录')


class RegisterForm(FlaskForm):
    """
    用户注册表单。
    包含用户名、密码和确认密码，密码需一致。
    """
    username = StringField(
        '用户名',
        validators=[DataRequired(), Length(1, 20)]  # 必填，长度1-20
    )
    password = PasswordField(
        '密码',
        validators=[DataRequired(), Length(6, 20)]  # 必填，长度6-20
    )
    confirm = PasswordField(
        '确认密码',
        validators=[DataRequired(), EqualTo('password')]  # 必填，且必须与password一致
    )
    submit = SubmitField('注册')
