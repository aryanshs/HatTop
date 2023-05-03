from contextlib import redirect_stderr
from distutils.log import error
from http import client
from urllib import request
from flask import Flask, render_template, url_for, request, session, redirect
from pymongo import MongoClient
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError
import re

app = Flask(__name__)
app.secret_key = 'cse312'

client = MongoClient('localhost', 27017)

db = client.flask_db  # creating a flask databse
hatTop = db.hatTop  # creating a collection in the flask_db database


# default Page
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == "POST":
        data = request.form.to_dict()

        print(data["schoolOption"])
        return render_template('loginPhase2.html', schoolSelected=data['schoolOption'])

    return render_template('loginPage.html')


# Signup Page
@app.route('/signup', methods=['GET', 'POST'])
def signUp():
    if request.method == "POST":
        data = request.form.to_dict()

        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'

        # checking if password is strong enough
        if len(data['password']) < 8 or not re.match(pattern, data['password']):
            errorMessage = 'Password must contain at least 8 characters, at least one uppercase letter, one lowercase letter, one number, and one special character.'
            return render_template('signup.html', name=data['name'], username=data['username'], email=data['email'], error=errorMessage)
        elif data['password'] != data['confirmPassword']:
            errorMessage = 'Passwords must be the same'
            return render_template('signup.html', name=data['name'], username=data['username'], email=data['email'], error=errorMessage)
        else:
            data['noContent'] = True
            hatTop.insert_one(data)
            # this can be called from anywhere
            session['username'] = data['username']

            return redirect(url_for('profStudent'))

    return render_template('signup.html')


# Professor Or Student Page
@app.route('/professororstudent', methods=['GET', 'POST'])
def profStudent():
    if request.method == "POST":
        data = request.form.to_dict()
        print(data)
        print(session.get('username'))

        # setting professor and student to true or false for the user to identify if they they are a professor or a student
        if 'professor' in data:
            userData = hatTop.find_one({'username': session.get('username')})
            userData['professor'] = True
            # update it in database
            hatTop.update_one({'_id': userData['_id']}, {'$set': userData})

            return redirect(url_for('homePage'))
        if 'student' in data:
            userData = hatTop.find_one({'username': session.get('username')})
            userData['student'] = True
            # update it in database
            hatTop.update_one({'_id': userData['_id']}, {'$set': userData})

            return redirect(url_for('homePage'))

    return render_template('professorOrStudent.html')


# Login page
@app.route('/login', methods=['GET', 'POST'])
def loginPhase2():
    if request.method == "POST":
        data = request.form.to_dict()  # converting the post data into a dictionary
        schoolData = ""
        if data['schoolData']:
            schoolData = data['schoolData']
        print(data)
        userData = hatTop.find_one({'username': data['username']})
        # this can be called from anywhere
        session['username'] = data['username']

        # checking if user has an account

        # if they don't we send them a link to sign up page
        if userData == None:
            error_message = "We don't have an account with that username, please create an account."
            return render_template('loginPhase2.html', AcctError=error_message)

        # if they do have an account, we check if their password, username, and school are correctly entered
        else:
            if userData['password'] != data['password']:
                error_message = "Please Check Your Password"
                return render_template('loginPhase2.html', schoolSelected=userData['schoolData'], username=data['username'], PasswordError=error_message)
            elif userData['schoolData'] != schoolData:
                error_message = "Please ensure you select the right School"
                return render_template('loginPhase2.html', schoolSelected=userData['schoolData'], username=data['username'], SchoolError=error_message)
            else:

                # if everything was correctly entered, we render the homepage
                return redirect(url_for('homePage'))

        print(userData)
    return render_template('loginPhase2.html')


# Home Page
@app.route('/home')
def homePage():
    # checking if user is a professor or a student, and checking if they are enrolled or have signed up for any classes
    userData = hatTop.find_one({'username': session.get('username')})
    if 'professor' in userData:
        if 'noContent' in userData:
            return render_template('homePage.html', professor=True, noContent=True)

    if 'student' in userData:
        if 'noContent' in userData:
            return render_template('homePage.html', student=True, noContent=True)


# Adding Courses Page
@app.route('/addcourses',methods = ["GET","POST"])
def addCourses():

    # looking into the database to check if the user is a professor or a student
    userData = hatTop.find_one({'username': session.get('username')})

    if 'professor' in userData:
        return render_template('addCourses.html', professor=True)
    if 'student' in userData:
        course = ''
        courseCode = None
        data = request.form.to_dict()  # converting the post data into a dictionary
        print(data)
        if("query" in data):
            query = data["query"]
            course = load_courses_from_db(query,"prefix")
            print(course)
        if("courseCode" in data):
            query = data["courseCode"]
            enroll_course = load_courses_from_db(query,"code")

            print(enroll_course[0]['coursePrefix'])
            print(data['coursePrefix'])
            if(enroll_course[0]['coursePrefix'] == data['coursePrefix']):
                hatTop.update_one({'courseCode': query}, { '$push' : { 'students': session.get('username')}})
                hatTop.update_one({'username': session.get('username')},{ '$push' : { 'courses': data['courseCode']}})
            else:
                print("error")


        return render_template('addCourses.html', student=True, courses = course)

def load_courses_from_db(query,method):
    if method == "prefix":
        courses = hatTop.find({'coursePrefix': {'$regex': query, '$options': 'i'}})
        return list(courses)
    elif method == "code":
        courses = hatTop.find({'courseCode': query})
        return list(courses)
    

def userLoggedIn():
    username = session.get('username', None)

    if username is not None:
        return True
    else:
        return False


if __name__ == "__main__":
    app.run()
