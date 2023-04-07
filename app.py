from contextlib import redirect_stderr
from crypt import methods
from distutils.log import error
from http import client
from urllib import request
from flask import Flask, render_template, url_for, request
from pymongo import MongoClient
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError
import re

app = Flask(__name__)

client = MongoClient('localhost', 27017)

db = client.flask_db  # creating a flask databse
hatTop = db.hatTop  # creating a collection in the flask_db database


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == "POST":
        data = request.form.to_dict()

        print(data["schoolOption"])
        return render_template('loginPhase2.html', schoolSelected=data['schoolOption'])

    return render_template('loginPage.html')


@app.route('/signup', methods=['GET', 'POST'])
def signUp():
    if request.method == "POST":
        data = request.form.to_dict()

        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        # if not re.match(pattern, data['password']):
        if len(data['password']) < 8 or not re.match(pattern, data['password']):
            errorMessage = 'Password must contain at least 8 characters, at least one uppercase letter, one lowercase letter, one number, and one special character.'
            return render_template('signup.html', name=data['name'], username=data['username'], email=data['email'], error=errorMessage)
        elif data['password'] != data['confirmPassword']:
            errorMessage = 'Passwords must be the same'
            return render_template('signup.html', name=data['name'], username=data['username'], email=data['email'], error=errorMessage)
        else:
            hatTop.insert_one(data)
            return render_template('homePage.html')

    return render_template('signup.html')


@app.route('/home')
def homePage():
    return render_template('homePage.html')


@app.route('/login', methods=['GET', 'POST'])
def loginPhase2():
    if request.method == "POST":
        data = request.form.to_dict()
        schoolData = ""
        if data['schoolData']:
            schoolData = data['schoolData']
        print(data)
        userData = hatTop.find_one({'username': data['username']})
        if userData == None:
            error_message = "We don't have an account with that username, please create an account."
            return render_template('loginPhase2.html', AcctError=error_message)
        else:
            if userData['password'] != data['password']:
                error_message = "Please Check Your Password"
                return render_template('loginPhase2.html', schoolSelected=userData['schoolData'], username=data['username'], PasswordError=error_message)
            elif userData['schoolData'] != schoolData:
                error_message = "Please ensure you select the right School"
                return render_template('loginPhase2.html', schoolSelected=userData['schoolData'], username=data['username'], SchoolError=error_message)
            else:
                return render_template('homePage.html')

        print(userData)
    return render_template('loginPhase2.html')


if __name__ == "__main__":
    app.run()
