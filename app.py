from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Regexp
import os
import random
import sqlite3

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
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
    creation_date = db.Column(db.DateTime)
    expiration_date = db.Column(db.DateTime)

    def __repr__(self):
        return '<Link %r>' % self.original_link


@app.route('/', methods=['GET', 'POST'])
def index():
    link = None
    form = LinkForm()
    if form.validate_on_submit():
        link = form.link.data

    return render_template('index.html', form=form, link=link)


def short_url_creator():
    return ''.join([random.choice(list('123456789qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM')) for x in range(7)])


if __name__ == '__main__':
    app.run()


print(short_url_creator())