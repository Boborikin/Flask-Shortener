import flask
from flask import Flask, render_template, redirect, abort, request, url_for, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Regexp, Email, Length, EqualTo
import os
import random
import datetime
from dateutil.relativedelta import relativedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user, AnonymousUserMixin
from flask_migrate import Migrate

basedir = os.path.abspath(os.path.dirname(__file__))
login_manager = LoginManager()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'test'
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
login_manager.init_app(app)
migrate = Migrate(app, db)


class LinkForm(FlaskForm):
    link = StringField('Shorten your link:', validators=[DataRequired(),
                Regexp("^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.%]*$"
                       , 0, 'Unable to shorten that link. It is not a valid url.')])
    expiration = SelectField('Expiration Time:', choices=[('5m', '5 Minutes'), ('10m', '10 Minutes'), ('15m', '15 Minutes'),
    ('30m', '30 Minutes'), ('1h', '1 Hour'), ('2h', '2 Hours'), ('4h', '4 Hours'), ('8h', '8 Hours'), ('12h', '12 Hours'),
                             ('1d', '1 Day'), ('7d', '7 Days'), ('1M', '1 Month'), ('6M', '6 Months'), ('1y', '1 Year')])

    submit = SubmitField('Shorten')


class LoginForm(FlaskForm):
    email = StringField('Email:', validators=[Length(1, 64), Email()], render_kw={"placeholder": "email"})
    password = PasswordField('Password:', validators=[DataRequired()],  render_kw={"placeholder": "password"})
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')


class SignupForm(FlaskForm):
    email = StringField('Email:', validators=[DataRequired(), Length(1, 64), Email()], render_kw={"placeholder": "email"})
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)], render_kw={"placeholder": 'username'})
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('password_confirm',
            message=("Passwords must match"))], render_kw={"placeholder": 'password'})
    password_confirm = PasswordField('Confirm password', validators=[DataRequired()],
                                     render_kw={"placeholder": 'confirm password'})
    submit = SubmitField('Register')


class Link(db.Model):
    __tablename__ = 'links'
    id = db.Column(db.Integer, primary_key=True)
    original_link = db.Column(db.Text)
    short_link = db.Column(db.Text, unique=True)
    clicks = db.Column(db.Integer, nullable=False, default=0)
    creation_date = db.Column(db.DATETIME())
    expiration_date = db.Column(db.DATETIME())
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<Link %r>' % self.original_link


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    link = db.relationship('Link', backref='users')

    @property
    def password(self):
        raise AttributeError('password is not readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.usernane


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/secret')
@login_required
def secret():
    return 'Only authenticated users are allowed!'

@app.route('/stats')
@login_required
def stats():
    return 'Only authenticated users are allowed!'

@app.errorhandler(404)
def page_not_found(error):
   return render_template('404.html', title='Page not found'), 404


@app.route('/', methods=['GET', 'POST'])
def index():
    expiration_date = ''
    form = LinkForm()
    short_link = ''
    if form.validate_on_submit():
        original_link = form.link.data
        expiration_time = form.expiration.data
        if 'http://' not in original_link and 'https://' not in original_link:
            original_link = 'http://' + form.link.data
        short_link = short_url_creator()
        creation_date = datetime.datetime.now()
        if 'm' in expiration_time:
            expiration_time = int(expiration_time.rstrip('m'))
            expiration_date = creation_date + datetime.timedelta(minutes=expiration_time)
        elif 'h' in expiration_time:
            expiration_time = int(expiration_time.rstrip('h'))
            expiration_date = creation_date + datetime.timedelta(hours=expiration_time)
        elif 'd' in expiration_time:
            expiration_time = int(expiration_time.rstrip('d'))
            expiration_date = creation_date + datetime.timedelta(days=expiration_time)
        elif 'M' in expiration_time:
            expiration_time = int(expiration_time.rstrip('M'))
            expiration_date = creation_date + relativedelta(months=expiration_time)
        elif 'y' in expiration_time:
            expiration_time = int(expiration_time.rstrip('y'))
            expiration_date = creation_date + relativedelta(years=expiration_time)

        if current_user.is_authenticated:
            db.session.add(Link(original_link=original_link, short_link=short_link, creation_date=creation_date,
                                expiration_date=expiration_date, user_id=current_user.id))

        db.session.add(Link(original_link=original_link, short_link=short_link, creation_date=creation_date,
                                expiration_date=expiration_date, user_id=None))
        db.session.flush()
        db.session.commit()

    return render_template('index.html', form=form, link=short_link)


@app.route('/<code>')
def redirector(code):
    url = Link.query.filter(Link.short_link.endswith(code)).first()
    if url is None or url.expiration_date < datetime.datetime.now():
        abort(404)
    else:
        original_link = url.original_link
        clicks(url)
        return redirect(original_link, 302)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            next = request.args.get('next')
            if next is None or not next.startswith('/'):
                next = url_for('index')
            return redirect(next)
        flash('Invalid username or password')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = SignupForm()
    if form.validate_on_submit():
        db.session.add(User(email=form.email.data, username=form.username.data, password=form.password.data))
        db.session.commit()
        db.session.close()
        flash('You can now login.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


def short_url_creator():
    return 'http://127.0.0.1:5000/'+''.join([random.choice(list('123456789qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM')) for x in range(7)])


def clicks(url):
    url.clicks += 1
    db.session.commit()
    db.session.close()


if __name__ == '__main__':
    app.run()
