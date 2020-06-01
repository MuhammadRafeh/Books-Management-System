import os

from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template('index.html')

@app.route("/registration", methods=['POST'])
def register():
	"""Handing Username Section"""
	inputusername = request.form.get('inputusername')
	user_exist = db.execute('SELECT * FROM users WHERE username = :inputusername',{'inputusername':inputusername}).fetchone()
	if not(user_exist is None):
		return render_template('index.html', issue="Username Already Exists!", result="unsuccess")
	"""Handling Email Section"""
	inputemail = request.form.get('inputemail')
	email_exist = db.execute('SELECT * FROM users WHERE email = :inputemail',{'inputemail':inputemail}).fetchone()
	if not(email_exist is None):
		return render_template('index.html', issue="Email Already Exists!", result="unsuccess")
	else:
		req = requests.get(f'https://app.verify-email.org/api/v1/UpNGc6mUVeKLPL8d2wR66dRI60Xz27Q0eJlchtqzKAO1ffil8g/verify/{inputemail}')
		result = req.json()
		if result['status']!=1: #If equal to 1 it's mean that Email is ok/exists
			return render_template("index.html", issue='Invalid Email Address!', result="unsuccess")


	return render_template('index.html', issue="Registered Successfully!", result='success')
