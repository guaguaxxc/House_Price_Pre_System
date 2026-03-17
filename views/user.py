from flask import Blueprint, render_template, redirect, session, url_for, flash
from forms.user import LoginForm, RegisterForm
from model.User import User
from model.History import History
from extensions import db
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo

user_bp = Blueprint('user', __name__, url_prefix='/user')


class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 20)])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')


class RegisterForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 20)])
    password = PasswordField('密码', validators=[DataRequired(), Length(6, 20)])
    checkPassword = PasswordField('确认密码',
                                  validators=[DataRequired(), EqualTo('password', message='两次密码不一致')])
    submit = SubmitField('注册')


@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(
            user_name=form.username.data,
            user_password=form.password.data
        ).first()
        if user:
            session['username'] = user.user_name
            session['user_id'] = user.user_id
            flash('登录成功', 'success')
            return redirect(url_for('page.home'))  # 修正为 page.home
        else:
            flash('账号或密码错误', 'error')
    return render_template('login.html', form=form)


@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(user_name=form.username.data).first()
        if existing:
            flash('该用户已存在', 'error')
        else:
            new_user = User(user_name=form.username.data, user_password=form.password.data)
            db.session.add(new_user)
            db.session.commit()
            flash('注册成功，请登录', 'success')
            return redirect(url_for('user.login'))
    return render_template('register.html', form=form)


@user_bp.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('user.login'))
