from flask import Flask, render_template, redirect, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Regexp
import os
import random
import datetime

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'test'
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)


class LinkForm(FlaskForm):
    link = StringField('Shorten your link:', validators=[DataRequired(),
                Regexp("^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.%]*$"
                       , 0, 'Unable to shorten that link. It is not a valid url.')])
    expiration = SelectField('Expiration Time:', choices=[('5m', '5 Minutes'), ('10m', '10 Minutes'), ('15m', '15 Minutes'),
    ('30m', '30 Minutes'), ('1h', '1 Hour'), ('2h', '2 Hours'), ('4h', '4 Hours'), ('8h', '8 Hours'), ('12h', '12 Hours'),
                             ('1d', '1 Day'), ('7d', '7 Days')])
    submit = SubmitField('Shorten')


class Link(db.Model):
    __tablename__ = 'links'
    id = db.Column(db.Integer, primary_key=True)
    original_link = db.Column(db.Text)
    short_link = db.Column(db.Text, unique=True)
    clicks = db.Column(db.Integer, nullable=False, default=0)
    creation_date = db.Column(db.DATETIME())
    expiration_date = db.Column(db.DATETIME())

    def __repr__(self):
        return '<Link> %r' % self.original_link


@app.errorhandler(404)
def page_not_found(error):
   return render_template('404.html', title='404'), 404


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
        db.session.add(Link(original_link=original_link, short_link=short_link, creation_date=creation_date,
                            expiration_date=expiration_date))
        db.session.commit()
        db.session.close()

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


def short_url_creator():
    return 'http://127.0.0.1:5000/'+''.join([random.choice(list('123456789qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM')) for x in range(7)])


def clicks(url):
    url.clicks += 1
    db.session.commit()
    db.session.close()


if __name__ == '__main__':
    app.run()

