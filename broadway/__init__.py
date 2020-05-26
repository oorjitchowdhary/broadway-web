import os, firebase_admin, flask_login, time
from flask import *
from dotenv import load_dotenv
from firebase_admin import auth, credentials, firestore
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, PasswordField
from wtforms.validators import Email, Length, InputRequired, ValidationError
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_required, logout_user, login_user, current_user, UserMixin

def create_app():
    load_dotenv()
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(base_dir, 'users.db')
    sql_db = SQLAlchemy(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    class User(UserMixin, sql_db.Model):
        id = sql_db.Column(sql_db.Integer, primary_key=True)
        username = sql_db.Column(sql_db.String(30), unique=True)
        email = sql_db.Column(sql_db.String(50), unique=True)
        password = sql_db.Column(sql_db.String(80))

    sql_db.create_all()
    sql_db.session.commit()

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

    class NewDiscussionForm(FlaskForm):
        title = StringField('title', validators=[InputRequired(), Length(max=60)])
        content = StringField('content', validators=[InputRequired()])
    
    class CommentForm(FlaskForm):
        comment = StringField('comment', validators=[InputRequired()])

    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type": os.environ.get('TYPE'),
            "project_id": os.environ.get('PROJECT_ID'),
            "private_key_id": os.environ.get('PRIVATE_KEY_ID'),
            "private_key": os.environ.get('PRIVATE_KEY').replace('\\n', '\n'),
            "client_email": os.environ.get('CLIENT_EMAIL'),
            "client_id": os.environ.get('CLIENT_ID'),
            "auth_uri": os.environ.get('AUTH_URI'),
            "token_uri": os.environ.get('TOKEN_URI'),
            "auth_provider_x509_cert_url": os.environ.get('AUTH_PROVIDER_CERT_URL'),
            "client_x509_cert_url": os.environ.get('CLIENT_CERT_URL')
        })
        default_app = firebase_admin.initialize_app(cred)
    db = firestore.client()

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/')
    def hello():
        return render_template('index.html')
    app.add_url_rule('/', endpoint='index')

    @app.route('/register', methods=['GET', 'POST'])
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
            })

            return redirect(url_for('login'))

        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user:
                if check_password_hash(user.password, form.password.data):
                    login_user(user)
                    return redirect(url_for('home'))
                else:
                    flash('Incorrect password')
            else:
                flash('No user found')

        return render_template('login.html', form=form)
    
    @app.route('/logout', methods=['GET', 'POST'])
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/home')
    @login_required
    def home():
        # show user profile
        # about the play
        # fandom sections
        return render_template('home.html')

    @app.route('/discuss', methods=['GET', 'POST'])
    @app.route('/discuss/', methods=['GET', 'POST'])
    @login_required
    def discuss():
        # show all discussions
        discussions = db.collection(u'discussions').stream()
        # create new discussion buton for logged in user
        return render_template('discuss.html', discussions=discussions)

    @app.route('/discuss/<post_id>', methods=['GET', 'POST'])
    @login_required
    def discuss_post(post_id):
        discussions = db.collection(u'discussions')
        post = discussions.document(post_id).get().to_dict()
        title = post['title']
        content = post['content']
        posted_by_user = post['posted_by_user']

        comments_on_post = db.collection(u'comments').where(u'on_post_id', u'==', post_id).stream()

        form = CommentForm()
        if form.validate_on_submit():
            db.collection(u'comments').add({
                u'on_post_id': post_id,
                u'comment_author': current_user.username,
                u'comment': form.comment.data,
            })
            return redirect(url_for('discuss')+post_id)

        return render_template('post.html', title=title, content=content, posted_by_user=posted_by_user, comments_on_post=comments_on_post, form=form)

    @app.route('/discuss/new', methods=['GET', 'POST'])
    def create_discussion():
        form = NewDiscussionForm()
        if form.validate_on_submit():
            db.collection(u'discussions').add({
                u'title': form.title.data,
                u'content': form.content.data,
                u'posted_by_user': current_user.username,
            })
            return redirect(url_for('discuss'))

        return render_template('create_discussion.html', form=form)

    @app.route('/quiz', methods=['GET', 'POST'])
    def quiz():
        # create quiz button for logged in user
        # display all available quizzes
        return render_template('quiz.html')
    
    @app.route('/quiz/new')
    def create_quiz():
        return render_template('create_quiz.html')

    @app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
    def play_quiz(quiz_id):
        # play a selected quiz
        # optimize firestore usage; save points in session
        # display answer after 5 incorrect attempts
        # update points after completing quiz
        return render_template('play_quiz.html')
    
    @app.errorhandler(404)
    def page_not_found(error):  
        return render_template('404.html'), 404
    
    return app