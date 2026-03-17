"""
Flask 应用工厂模块
================================================
该模块负责创建 Flask 应用实例，注册蓝图，并配置根路由。
"""

from flask import Flask, session, redirect, url_for
from config import Config
from extensions import db, cache, csrf, setup_logging
from views.page import pb
from views.user import user_bp


def create_app():
    """
    创建并配置 Flask 应用实例。
    步骤：
        1. 创建 Flask 对象
        2. 加载配置（从 Config 类）
        3. 初始化扩展（数据库、缓存、CSRF）
        4. 配置日志
        5. 注册蓝图
        6. 定义根路由

    :return: 配置好的 Flask 应用实例
    """
    app = Flask(__name__)
    app.config.from_object(Config)  # 从 Config 类加载配置

    # 初始化扩展
    db.init_app(app)
    cache.init_app(app)
    csrf.init_app(app)

    # 设置日志（文件输出等）
    setup_logging(app)

    # 注册蓝图
    app.register_blueprint(pb)  # 页面相关路由
    app.register_blueprint(user_bp)  # 用户认证相关路由

    # 根路由：根据登录状态跳转到首页或登录页
    @app.route('/')
    def index():
        if session.get('username'):
            return redirect(url_for('page.home'))  # 已登录，跳转首页
        else:
            return redirect(url_for('user.login'))  # 未登录，跳转登录页

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)  # 开发模式下开启调试
