from flask import Flask, render_template, redirect
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Regexp
import os
import random
import datetime

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'ddfgfddfdfgd'
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)

class LinkForm(FlaskForm):
    link = StringField('Shorten your link:', validators=[DataRequired(),
                Regexp("^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$"
                       , 0, 'Unable to shorten that link. It is not a valid url.')])
    submit = SubmitField('Shorten')



class Link(db.Model):
    __tablename__ = 'links'
    id = db.Column(db.Integer, primary_key=True)
    original_link = db.Column(db.Text)
    short_link = db.Column(db.Text)
    creation_date = db.Column(db.DATETIME(6))
    expiration_date = db.Column(db.DATETIME(6))

    def __repr__(self):
        return '<Link %r>' % self.original_link


@app.route('/', methods=['GET', 'POST'])
def index():
    form = LinkForm()
    original_link = None
    short_link = None
    if form.validate_on_submit():
        original_link = form.link.data
        if 'http://' not in original_link and 'https://' not in original_link:
            original_link = 'http://' + form.link.data
        short_link = short_url_creator()
        creation_date = datetime.datetime.now()
        db.session.add(Link(original_link=original_link, short_link=short_link, creation_date=creation_date))
        db.session.commit()

    return render_template('index.html', form=form, link=original_link, link2=short_link)

@app.route('/<code>')
def redirector(code):
    if code:
        url = Link.query.filter(Link.short_link.endswith(code)).first()
        original_url = url.original_link
    return redirect(original_url, 302)

def short_url_creator():
    return 'http://127.0.0.1:5000/'+''.join([random.choice(list('123456789qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM')) for x in range(7)])


if __name__ == '__main__':
    app.run()

