from asyncio import constants
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
gradeBook = db.gradeBook  #collection to store gradebook for each course
questions = db.questions #collection to store all questions
professorAndStudents = db.professorAndStudents #collection for classes


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
            data['courses'] = []
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
        if userData['noContent'] == True:
            return render_template('homePage.html', professor=True, noContent=True)
        else:
            classData = professorAndStudents.find(
                {'professorUsername': session.get('username')})
            classData2 = []
            index = 0
            for i in userData["courses"]:
                # classData2.append(professorAndStudents.find(
                #     {'courseCode': i}))
                for j in professorAndStudents.find(
                        {'courseCode': i}):
                    classData2.append(j)
                index += 1
            return render_template('homePage.html', professor=True, noContent=False, classesData=classData2)

    if 'student' in userData:
        if userData['noContent'] == True:
            return render_template('homePage.html', student=True, noContent=True)


# Adding Courses Page
@ app.route('/addcourses', methods=['GET', 'POST'])
def addCourses():

    if (request.method == "POST"):
        data = request.form.to_dict()  # convertint data from post into a dictionary
        # finding user data based on current user's username
        userData = hatTop.find_one({'username': session.get('username')})
        newUserData = {}
        if 'professor' in userData:
            # creating a students key in the data for professor to later add students,
            # the value for key 'students' is also a dictionary, which will contain username of the
            # student who is enrolled in the professor's class and the values could contain their grades
            # and any other stuff that we need
            data["students"] = [{}]

            # here we created newUserData dict, which will contain professor's username and their class as a list in professorsAndStudents
            # newUserData["username"] = session.get('username')
            data["professorUsername"] = session.get("username")

            # inserting the professor and student data to our collection (professorAndStudents)
            professorAndStudents.insert_one(data)

            # setting noContent to false for userData (hatTop collection) , signifying the user has enrolled or
            # signed up for atleast one class
            userData["noContent"] = False
            # adding classes for the professor
            if (len(userData["courses"]) == 0):
                userData["courses"] = [data["courseCode"]]
            else:
                userData["courses"].append(data["courseCode"])
            print(userData["courses"])
            print(data["courseCode"])
            hatTop.update_one({'_id': userData['_id']}, {'$set': userData})

            return render_template('addCourses.html', professor=True, classAdded=True)

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
    
#Create a question form
@app.route('/createquestion', methods=['GET'])
def createquestion():
    professor = True
    student = False
    course='course 42069'
    #This should check if it's a student, if so then redirect to safe page
    #Students do not have authority to create questions
    if student:
        return render_template('homePage.html', student=True, noContent=True)
    
    if professor:
        return render_template('createQuestion.html',courseName=course)

#receives completed createquestion forms
#uses that data to
@app.route('/activequestion', methods=['GET', 'POST'])
def activequestion():
    #the following variables are hardcoded for testing purposes
    #once the dependent features are implemented then it will be removed
    professor = True #this will be derived from userData
    student = False #this will be derived from userData
    studentName = 'Zack' #this will be derived from session
    course = 'CSE 42069' #this will be derived from request data

    if request.method == "POST":

        question = request.form.to_dict()

        #put all the answers options into list
        answers = []
        for key in question:
            if key[:6] == 'answer' and not (question[key] == ""):
                answers.append(question[key])

        #add question to questions collection
        q = questions.insert_one({'course':course, 'question':html.escape(question['question']), 'answers':answers, 'correctAnswer':html.escape(question['correctAnswer']), 'isActive':1})

        #if it's a professor then don't render as form, just as text
        if professor:
            return render_template('activeQuestion.html',courseName=course, questionID=q.inserted_id,professor=True,question=html.escape(question['question']) , answer1=html.escape(question['answer1']), answer2=html.escape(question['answer2']), answer3=html.escape(question['answer3']), answer4=html.escape(question['answer4']), answer5=html.escape(question['answer5']))
        
    #if it's a get then use question id to get information from db
    question = request.form.to_dict()
    qid = question['id']
    q = questions.find_one({'_id': qid})
    
    #get the answers
    ans1 = q['answers'][0]
    ans2 = q['answers'][1]
    ans3 = ""
    ans4 = ""
    ans5 = ""
    if(len(q['answers']) >= 3):
        ans3 = q['answers'][2]
    if(len(q['answers']) >= 4):
        ans4 = q['answers'][3]
    if(len(q['answers']) >= 5):
        ans5 = q['answers'][4]

    return render_template('activeQuestion.html',courseName=q['course'], student=True,question=q['question'] , answer1=ans1, answer2=ans2, answer3=ans3, answer4=ans4, answer5=ans5)
    
#Don't really have to do anything when question starts
#This is just a sanity check to confirm socket connection has correctly happened
#And that questionID was correctly passed
@socket.on('startQuestion')
def postQuestion(questionID):
    print('Question: ', questionID , ' Started')

#When a student submits an answer:
#1. Check that question is active
#   1a. If it is inactive display appropriate message and do nothing else
#   1b. If it is active then continue
#2. check if answer is correct
#3. Upsert the submission
#4 Send the updated number of submissions to client
@socket.on('Submission')
def handleSubmission(questionID, answer):
    #get question by id
    question = questions.find_one({'_ID':questionID})

    #If question is inactive then tell client
    #This should never actually trigger, as the moment a question closes
    #The client should be alerted and redirected
    if(question['isActive'] == 0):
        socket.emit('questionClosed')
    
    #check if answer is correct
    if(answer == question['correctAnswer']):
        score = 1
    else:
        score = 0

    #perform a upsert
    data = {'course':question['course'], 'answer':answer, 'score':score, 'question':question['question']}
    gradeBook.update_one({'qid':questionID, 'student':session.get('username')}, data, upsert=True)
    
    #get the number of subissions for question
    count = gradeBook.count_documents({'qid':questionID})
    socket.emit('newSubmission', count)
    print('Question: ', questionID , ' Started')

#upon ending a question:
#1. Set the question to inactive in DB
#2. Display the final results
@socket.on('endQuestion')
def stopQuestion():
    print('Question ended')

if __name__ == "__main__":
    socket.run(app)
