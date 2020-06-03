from flask import *
from flask_login import LoginManager, login_required, logout_user, login_user, current_user, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import Email, InputRequired, Length, ValidationError

from broadway.db import sql_db, db

bp = Blueprint('auth', __name__)

class User(UserMixin, sql_db.Model):
    id = sql_db.Column(sql_db.Integer, primary_key=True)
    username = sql_db.Column(sql_db.String(30), unique=True)
    email = sql_db.Column(sql_db.String(50), unique=True)
    password = sql_db.Column(sql_db.String(80))

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4)])

class RegisterForm(FlaskForm):
    name = StringField('name', validators=[InputRequired(), Length(max=60)])
    email = StringField('email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=30)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=4, max=80)])
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Username already exists!")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Email already exists!")

@bp.route('/register', methods=['GET', 'POST'])
def register():

    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        sql_db.session.add(new_user)
        sql_db.session.commit()

        db.collection(u'users').document(form.username.data).set({
            u'name': form.name.data,
            u'username': form.username.data,
            u'email': form.email.data,
            u'num_of_correct_answers': 0,
        })
        return redirect(url_for('auth.login'))

    return render_template('register.html', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Incorrect password')
        else:
            flash('No user found')

    return render_template('login.html', form=form)
    
@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for('index'))

login_manager = LoginManager()
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))