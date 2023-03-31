from http import client
from flask import Flask, render_template, url_for
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient('localhost', 27017)

db = client.flask_db  # creating a flask databse
hatTop = db.hatTop  # creating a collection in the flask_db database


@app.route('/')
def home():
    return render_template('loginPage.html')


if __name__ == "__main__":
    app.run()
