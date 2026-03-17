"""
用户认证蓝图模块
================================================
该模块提供用户登录、注册、注销功能。
但为了简洁，直接在文件内定义表单类。
"""

from flask import Blueprint, render_template, redirect, session, url_for, flash
from forms.user import LoginForm, RegisterForm
from model.User import User
from extensions import db
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo

# 创建用户蓝图，所有路由前缀为 /user
user_bp = Blueprint('user', __name__, url_prefix='/user')


# ==================== 登录表单 ====================
class LoginForm(FlaskForm):
    """用户登录表单"""
    username = StringField('用户名', validators=[DataRequired(), Length(1, 20)])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')


# ==================== 注册表单 ====================
class RegisterForm(FlaskForm):
    """用户注册表单，包含密码确认"""
    username = StringField('用户名', validators=[DataRequired(), Length(1, 20)])
    password = PasswordField('密码', validators=[DataRequired(), Length(6, 20)])
    checkPassword = PasswordField('确认密码',
                                  validators=[DataRequired(), EqualTo('password', message='两次密码不一致')])
    submit = SubmitField('注册')


# ==================== 登录路由 ====================
@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    用户登录页面。
    GET 请求：显示登录表单。
    POST 请求：验证用户名和密码，若成功则写入 session，并重定向至首页。
    """
    form = LoginForm()
    if form.validate_on_submit():
        # 查询用户（此处使用明文密码，生产环境应使用哈希比较）
        user = User.query.filter_by(
            user_name=form.username.data,
            user_password=form.password.data
        ).first()
        if user:
            # 登录成功，保存用户信息到 session
            session['username'] = user.user_name
            session['user_id'] = user.user_id
            flash('登录成功', 'success')
            return redirect(url_for('page.home'))  # 重定向到首页
        else:
            flash('账号或密码错误', 'error')
    return render_template('login.html', form=form)


# ==================== 注册路由 ====================
@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    用户注册页面。
    GET 请求：显示注册表单。
    POST 请求：验证表单，检查用户名是否已存在，若不存在则创建新用户并重定向至登录页。
    """
    form = RegisterForm()
    if form.validate_on_submit():
        # 检查用户名是否已存在
        existing = User.query.filter_by(user_name=form.username.data).first()
        if existing:
            flash('该用户已存在', 'error')
        else:
            # 创建新用户（明文密码存储，生产环境应加密）
            new_user = User(user_name=form.username.data, user_password=form.password.data)
            db.session.add(new_user)
            db.session.commit()
            flash('注册成功，请登录', 'success')
            return redirect(url_for('user.login'))
    return render_template('register.html', form=form)


# ==================== 注销路由 ====================
@user_bp.route('/logout')
def logout():
    """
    用户注销：清空 session 中的所有数据，并重定向到登录页。
    """
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('user.login'))
