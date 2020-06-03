import os, firebase_admin
from flask import Flask, render_template
from dotenv import load_dotenv
from firebase_admin import credentials, firestore
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flaskext.markdown import Markdown

from broadway.auth import login_manager

def create_app():
    load_dotenv()
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(base_dir, 'users.db')
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    Markdown(app)

    @app.route('/')
    def index():
        return render_template('index.html')
    app.add_url_rule('/', endpoint='index')

    from broadway.db import sql_db
    sql_db.init_app(app)
    
    with app.app_context():
        sql_db.create_all()
        sql_db.session.commit()

    from . import auth
    app.register_blueprint(auth.bp)

    from . import discuss
    app.register_blueprint(discuss.bp)

    from . import quiz
    app.register_blueprint(quiz.bp)
    
    @app.errorhandler(404)
    def page_not_found(error):  
        return render_template('404.html'), 404
    
    return app

app = create_app()