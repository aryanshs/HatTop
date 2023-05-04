from contextlib import redirect_stderr
from distutils.log import error
from http import client
from urllib import request
from flask import Flask, render_template, url_for, request, session, redirect
from flask_socketio import SocketIO, send
from pymongo import MongoClient
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError
import html
import re

app = Flask(__name__)
app.secret_key = 'cse312'
socket = SocketIO(app, async_mode="gevent") #creating socket
client = MongoClient('localhost', 27017)

db = client.flask_db  # creating a flask databse
hatTop = db.hatTop  # collection to store user information
gradeBook = db.gradeBook  # collection to store gradebook for each course


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
@app.route('/addcourses')
def addCourses():

    # looking into the database to check if the user is a professor or a student
    userData = hatTop.find_one({'username': session.get('username')})

    if 'professor' in userData:
        return render_template('addCourses.html', professor=True)
    if 'student' in userData:
        return render_template('addCourses.html', student=True)

# checking if user is logged in
def userLoggedIn():
    username = session.get('username', None)

    if username is not None:
        return True
    else:
        return False
    
# Create a question
#Send the completed form data to socket so it can start the question
@app.route('/createquestion', methods=['GET', 'POST'])
def createquestion():
    #the following variables are hardcoded for testing purposes
    #once the dependent features are implemented then it will be removed
    professor = True #this will be derived from userData
    student = False #this will be derived from userData
    studentName = 'Zack' #this will be derived from session
    course = 'CSE 42069' #this will be derived from request data
    if request.method == "POST":

        question = request.form.to_dict()

        #add question to gradebook
        q = gradeBook.insert_one({'course':course, 'question':html.escape(question['question']), 'student':'', 'score':0, 'correctAnswer':html.escape(question['correctAnswer']), 'isActive':1})

        #if it's a professor then don't render as form, just as text
        if professor:
            return render_template('activeQuestion.html',courseName=course, questionID=q.inserted_id,professor=True,question=html.escape(question['question']) , answer1=html.escape(question['answer1']), answer2=html.escape(question['answer2']), answer3=html.escape(question['answer3']), answer4=html.escape(question['answer4']), answer5=html.escape(question['answer5']))
        
        #if it's a student then render as form
        if student:
            return render_template('activeQuestion.html',courseName=course, student=True,question=html.escape(question['question']) , answer1=html.escape(question['answer1']), answer2=html.escape(question['answer2']), answer3=html.escape(question['answer3']), answer4=html.escape(question['answer4']), answer5=html.escape(question['answer5']))
    
    #This should check if it's a student, if so then redirect to safe page
    #Students do not have authority to create questions
    if student:
        return render_template('homePage.html', student=True, noContent=True)
    
    if professor:
        return render_template('createQuestion.html',courseName=course)

@socket.on('startQuestion')
def postQuestion(questionID):
    print('Question: ', questionID , ' Started')

#When a student submits an answer:
#1. Check that question is active
#   1a. If it is inactive display appropriate message and do nothing else
#   1b. If it is active then continue
#2. Check if student as already submitted a question
#   2a. If no submission exists create one
#   2b. If submission exists just update it
#3 Update the number of submissions for professors page
@socket.on('Submission')
def handleSubmission(questionID):
    print('Question: ', questionID , ' Started')

#upon ending a question:
#1. Set the question to inactive in DB
#2. Display the final results
@socket.on('endQuestion')
def stopQuestion():
    print('Question ended')

if __name__ == "__main__":
    socket.run(app)
