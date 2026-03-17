from flask import Flask, session, redirect, url_for
from config import Config
from extensions import db, cache, csrf, setup_logging
from views.page import pb
from views.user import user_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    cache.init_app(app)
    csrf.init_app(app)
    setup_logging(app)

    app.register_blueprint(pb)
    app.register_blueprint(user_bp)

    @app.route('/')
    def index():
        if session.get('username'):
            return redirect(url_for('page.home'))
        else:
            return redirect(url_for('user.login'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
