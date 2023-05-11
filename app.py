from bson.objectid import ObjectId
from asyncio import constants
from contextlib import redirect_stderr
from distutils.log import error
from http import client
from urllib import request
from flask import Flask, render_template, url_for, request, session, redirect, escape
from flask_socketio import SocketIO, send
import bcrypt
from pymongo import MongoClient
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError
import json
import html
import re

app = Flask(__name__)
app.secret_key = 'cse312'
socket = SocketIO(app, async_mode="gevent")  # creating socket
client = MongoClient('localhost', 27017)

db = client.flask_db  # creating a flask databse
hatTop = db.hatTop  # collection to store user information
gradeBook = db.gradeBook  # collection to store gradebook for each course
questions = db.questions  # collection to store all questions
professorAndStudents = db.professorAndStudents  # collection for classes


# default Page
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == "POST":
        data = request.form.to_dict()

        return render_template('loginPhase2.html', schoolSelected=data['schoolOption'])

    return render_template('loginPage.html')


# Signup Page
@app.route('/signup', methods=['GET', 'POST'])
def signUp():
    if request.method == "POST":
        data = request.form.to_dict()

        # escaping user inputs
        for key, value in data.items():
            data[key] = escape(value)

        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'

        # checking if password is strong enough
        if len(data['password']) < 8 or not re.match(pattern, data['password']):
            errorMessage = 'Password must contain at least 8 characters, at least one uppercase letter, one lowercase letter, one number, and one special character.'
            return render_template('signup.html', name=data['name'], username=data['username'], email=data['email'], error=errorMessage)
        elif data['password'] != data['confirmPassword']:
            errorMessage = 'Passwords must be the same'
            return render_template('signup.html', name=data['name'], username=data['username'], email=data['email'], error=errorMessage)
        elif hatTop.find_one({'username': data['username']}):
            errorMessage = "Account already exists, please Login"
            return render_template('signup.html', ExistingUserError=errorMessage)
        else:
            data['noContent'] = True
            data['courses'] = []

            # Hashing password
            salt = bcrypt.gensalt()
            hashedPassword = bcrypt.hashpw(
                data['password'].encode('utf-8'), salt)
            data['password'] = hashedPassword
            data['confirmPassword'] = hashedPassword
            data['salt'] = salt

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

        for key, value in data.items():
            data[key] = escape(value)

        if data['schoolData']:
            schoolData = data['schoolData']

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
            if bcrypt.checkpw(data['password'].encode('utf-8'), userData['password']) == False:
                error_message = "Please Check Your Password"
                return render_template('loginPhase2.html', schoolSelected=userData['schoolData'], username=data['username'], PasswordError=error_message)
            elif userData['schoolData'] != schoolData:
                error_message = "Please ensure you select the right School"
                return render_template('loginPhase2.html', schoolSelected=userData['schoolData'], username=data['username'], SchoolError=error_message)
            else:

                # if everything was correctly entered, we render the homepage
                return redirect(url_for('homePage'))

    return render_template('loginPhase2.html')


# Home Page
@ app.route('/home')
def homePage():
    if userLoggedIn():
        # checking if user is a professor or a student, and checking if they are enrolled or have signed up for any classes
        userData = hatTop.find_one({'username': session.get('username')})
        if 'professor' in userData:
            if userData['noContent'] == True:
                return render_template('homePage.html', professor=True, noContent=True)
            else:
                # classData = professorAndStudents.find(
                #     {'professorUsername': session.get('username')})
                classData2 = []
                index = 0
                for i in userData["courses"]:

                    for j in professorAndStudents.find(
                            {'courseCode': i}):
                        classData2.append(j)
                    index += 1
                    print("classData2: ", classData2)
                return render_template('homePage.html', professor=True, noContent=False, classesData=classData2)

        if 'student' in userData:
            if userData['noContent'] == True:
                return render_template('homePage.html', student=True, noContent=True)
            else:
                all_courses = []
                courses = userData['courses']
                for course in courses:
                    all_courses.append(
                        professorAndStudents.find_one({'courseCode': course}))
                print(all_courses)
                return render_template('homePage.html', student=True, noContent=False, classesData=all_courses)
    else:
        return redirect(url_for('home'))


# Adding Courses Page
@ app.route('/addcourses', methods=['GET', 'POST'])
def addCourses():
    if userLoggedIn():
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
        userData = hatTop.find_one({'username': session.get('username')})
        if 'professor' in userData:
            return render_template('addCourses.html', professor=True)
        if 'student' in userData:
            course = ''
            courseCode = None
            data = request.form.to_dict()  # converting the post data into a dictionary
            print(data)
            if ("query" in data):
                query = data["query"]
                course = load_courses_from_db(query, "prefix")
            if ("courseCode" in data):
                query = data["courseCode"]
                enroll_course = load_courses_from_db(query, "code")

                print(enroll_course[0]['coursePrefix'])
                print(data['coursePrefix'])
                if (enroll_course[0]['coursePrefix'] == data['coursePrefix']):
                    hatTop.update_one({'_id': userData['_id']}, {
                        '$set': {'noContent': False}})
                    professorAndStudents.update_one(
                        {'courseCode': query}, {'$push': {'students': session.get('username')}})
                    hatTop.update_one({'username': session.get('username')}, {
                        '$push': {'courses': data['courseCode']}})
                    return redirect(url_for('homePage'))

                else:
                    print("error")

            return render_template('addCourses.html', student=True, courses=course)
    else:
        return redirect(url_for('home'))


def load_courses_from_db(query, method):
    if method == "prefix":
        courses = professorAndStudents.find(
            {'coursePrefix': {'$regex': query, '$options': 'i'}})
        return list(courses)
    elif method == "code":
        courses = professorAndStudents.find({'courseCode': query})
        return list(courses)


def userLoggedIn():
    username = session.get('username', None)

    if username is not None:
        return True
    else:
        return False

# logging out user


@app.route('/logout', methods=['POST'])
def logout():
    if request.method == "POST":
        username = session.get('username')
        del session['username']
        return redirect(url_for('home'))

# Create a question form


@ app.route('/createquestion', methods=['GET'])
def createquestion():
    if (userLoggedIn()):
        cid = request.args.get('courseID')
        userData = hatTop.find_one({'username': session.get('username')})

        # get courseData
        obj = ObjectId(cid)
        course = professorAndStudents.find_one({'_id': obj})

        # This should check if it's a student, if so then redirect to safe page
        # Students do not have authority to create questions
        if 'student' in userData:
            return render_template('loginPage.html')

        if 'professor' in userData:
            return render_template('createQuestion.html', professor=True, courseName=course['coursePrefix'], courseID=cid)
    else:
        return redirect(url_for('home'))

# This receives the course id from homepage


@ app.route('/coursePage', methods=['GET'])
def coursePage():
    if userLoggedIn():
        cid = request.args.get('courseID')
        userData = hatTop.find_one({'username': session.get('username')})

        # get courseData
        obj = ObjectId(cid)
        course = professorAndStudents.find_one({'_id': obj})
        print('course: ', course)

        if 'professor' in userData:
            return render_template('coursePage.html', professor=True, courseName=course['coursePrefix'], courseID=cid)

        # get all active questions for this course
        activeQuestions = []
        for question in questions.find({'cid': cid}):
            if question['isActive'] == 1:
                activeQuestions.append(question)

        if 'student' in userData:
            return render_template('coursePage.html', cid=cid, qid=question['_id'], student=True, courseName=course['coursePrefix'], courseID=cid, activeQuestions=activeQuestions)
    else:
        return redirect(url_for('home'))


# receives completed createquestion forms
# uses that data to


@ app.route('/activequestion', methods=['GET', 'POST'])
def activequestion():
    if userLoggedIn():
        if request.method == "POST":
            userData = hatTop.find_one({'username': session.get('username')})
            question = request.form.to_dict()

            cid = question['courseID']
            # get courseData
            obj = ObjectId(cid)
            course = professorAndStudents.find_one({'_id': obj})

            # put all the answers options into list
            answers = []
            for key in question:
                if key[:6] == 'answer' and not (question[key] == ""):
                    answers.append(question[key])

            # add question to questions collection
            q = questions.insert_one({'cid': cid, 'question': html.escape(
                question['question']), 'answers': answers, 'correctAnswer': int(question['correctAnswer'][6:]), 'isActive': 1})

            # if it's a professor then don't render as form, just as text
            if 'professor' in userData:
                return render_template('activeQuestion.html', courseID=cid, courseName=course['coursePrefix'], questionID=q.inserted_id, professor=True, question=html.escape(question['question']), answer1=html.escape(question['answer1']), answer2=html.escape(question['answer2']), answer3=html.escape(question['answer3']), answer4=html.escape(question['answer4']), answer5=html.escape(question['answer5']))
            if 'student' in userData:
                return render_template('loginPage.html')

        # if it's a get then use question id to get information from db
        qid = request.args.get('qid')
        cid = request.args.get('cid')
        obj = ObjectId(qid)
        q = questions.find_one({'_id': obj})

        # get courseData
        obj = ObjectId(cid)
        course = professorAndStudents.find_one({'_id': obj})

        # get the answers
        ans1 = q['answers'][0]
        ans2 = q['answers'][1]
        ans3 = ""
        ans4 = ""
        ans5 = ""
        if (len(q['answers']) >= 3):
            ans3 = q['answers'][2]
        if (len(q['answers']) >= 4):
            ans4 = q['answers'][3]
        if (len(q['answers']) >= 5):
            ans5 = q['answers'][4]

        return render_template('activeQuestion.html', questionID=qid, courseID=cid, courseName=course['coursePrefix'], student=True, question=q['question'], answer1=ans1, answer2=ans2, answer3=ans3, answer4=ans4, answer5=ans5)
    else:
        return redirect(url_for('home'))

# upon ending a question:
# 1. Set the question to inactive in DB
# 2. Send message to all sockets that question has ended
# 3. Go to prof homepage


@ app.route('/endQuestion', methods=['POST'])
def stopQuestion():
    if userLoggedIn():
        data = request.form.to_dict()
        cid = data['courseID']
        qid = data['questionID']
        qobj = ObjectId(qid)

        # get courseData
        print('cid: ', cid)
        print('qid: ', qid)
        obj = ObjectId(cid)
        course = professorAndStudents.find_one({'_id': obj})

        questions.update_one({'_id': qobj}, {'$set': {'isActive': 0}})

        socket.emit('questionClosed', {'qid': qid})
        return render_template('coursePage.html', professor=True, courseName=course['coursePrefix'], courseID=cid)
    else:
        return redirect(url_for('home'))

# Don't really have to do anything when question starts
# This is just a sanity check to confirm socket connection has correctly happened
# And that questionID was correctly passed


@socket.on('startQuestion')
def postQuestion(questionID):
    print('Question: ', questionID, ' Started')

# When a student submits an answer:
# 1. Check that question is active
#   1a. If it is inactive display appropriate message and do nothing else
#   1b. If it is active then continue
# 2. check if answer is correct
# 3. Upsert the submission
# 4 Send the updated number of submissions to client


@socket.on('submission')
def handleSubmission(answerInfo):
    # get question by id
    answer = answerInfo['answer']
    questionID = answerInfo['questionID']
    print('submission received')
    print('qid: ', questionID)
    question = questions.find_one({'_id': ObjectId(questionID)})

    # If question is inactive then tell client
    # This should never actually trigger, as the moment a question closes
    # The client should be alerted and redirected
    if (question['isActive'] == 0):
        socket.emit('questionClosed')

    # check if answer is correct
    if (answer == "answer" + str(question['correctAnswer'])):
        score = 1
    else:
        score = 0

    # perform a upsert
    data = {'cid': question['cid'], 'answer': answer,
            'score': score, 'question': question['question']}
    gradeBook.update_one({'qid': questionID, 'student': session.get('username')}, {
                         "$set": data}, upsert=True)

    # get the number of subissions for question
    count = gradeBook.count_documents({'qid': questionID})
    socket.emit('newSubmission', {'qid': questionID, 'count': count})
    print('count: ', count)
    print('Student: ', session.get('username'), ' submitted the answer: ',
          answer, ' for question: ', question['question'])


@ app.route('/gradebook', methods=["GET"])
def gradebook():
    if userLoggedIn():
        cid = request.args.get('courseID')
        userData = hatTop.find_one({'username': session.get('username')})
        obj = ObjectId(cid)
        course = professorAndStudents.find_one({'_id': obj})
        final = []

        if 'professor' in userData:
            for g in gradeBook.find():
                if g['cid'] == cid:
                    final.append()
            return render_template('profGradeboook.html', courseName=course['coursePrefix'], gradeBookData=final)

        if 'student' in userData:
            for g in gradeBook.find():
                if g['student'] == session.get('username'):
                    if g['cid'] == cid:
                        final.append()
            return render_template('studGradebook.html', courseName=course['coursePrefix'], gradeBookData=final)
    else:
        return redirect(url_for('home'))


if __name__ == "__main__":
    socket.run(app)
