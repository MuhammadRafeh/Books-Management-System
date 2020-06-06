import os

from flask import Flask, session, render_template, request, redirect, url_for, abort, jsonify
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
	if "user" in session:
		return redirect(url_for('login'))
	return render_template('index.html')

@app.route("/registration", methods=['POST'])
def register():
	"""Fetching all the Inputs"""
	inputusername = request.form.get('inputusername')
	inputemail = request.form.get('inputemail')
	inputpassword = request.form.get('inputpassword')

	"""Handing Username Section"""
	user_exist = db.execute('SELECT * FROM users WHERE username = :inputusername',{'inputusername':inputusername}).fetchone()
	if not(user_exist is None):
		return render_template('index.html', issue="Username Already Exists!", result="unsuccess")

	"""Handling Email Section"""
	email_exist = db.execute('SELECT * FROM users WHERE email = :inputemail',{'inputemail':inputemail}).fetchone()
	if not(email_exist is None):
		return render_template('index.html', issue="Email Already Exists! Just Login Below", result="unsuccess")
	else:
		req = requests.get('https://app.verify-email.org/api/v1/UpNGc6mUVeKLPL8d2wR66dRI60Xz27Q0eJlchtqzKAO1ffil8g/verify/{}'.format(inputemail))
		result = req.json()
		if result['status']!=1: #If equal to 1 it's mean that Email is ok/exists
			return render_template("index.html", issue='Invalid Email Address!', result="unsuccess")

	"""Inserting data into the Database"""
	db.execute("INSERT INTO users (username, email, password) VALUES (:inputusername, :inputemail, :inputpassword)",{
		'inputusername':inputusername, 'inputemail': inputemail, 'inputpassword':inputpassword
		})
	db.commit()
	return render_template('index.html', issue="Registered Successfully!", result='success')

@app.route("/login", methods=['POST', 'GET'])
def login():
	if request.method=='POST':
		"""Fetching all the Inputs"""
		loginusername = request.form.get('loginusername')
		loginpassword = request.form.get('loginpassword')

		"""Checking User Exists or Not"""
		record_exist = db.execute('SELECT * FROM users WHERE username = :loginusername AND password = :loginpassword', {'loginusername':loginusername, 'loginpassword': loginpassword}).fetchone()
		if record_exist is None:
			#return "Invalid Username/Password!"
			return render_template('index.html', issue='Invalid Username/Password!', result='unsuccess')

		"""Storing current logged in user into the session"""
		session["user"] = []
		session["user"].append(record_exist.id)
		session["user"].append(record_exist.username)
		return render_template('search.html', user=session['user'])

	else:
		if 'user' in session:
			return render_template('search.html', user=session['user'])
		return redirect(url_for('index'))

@app.route('/logout')
def logout():
	session.pop('user')
	return redirect(url_for('index'))

@app.route('/search', methods=['POST','GET'])
def search():
	if request.method=='POST':
		"""Fetching all the Inputs"""
		isbn = request.form.get('isbn')
		title = request.form.get('title')
		author = request.form.get('author')
		#info = db.execute("SELECT * FROM books WHERE author = :author",{'author':author}).fetchall()

		if request.args.get("f") == 'f1':
			data = db.execute("SELECT * FROM books WHERE isbn = :isbn",{'isbn':isbn}).fetchall()

		elif request.args.get("f") == 'f2':
			data = db.execute("SELECT * FROM books WHERE title = :title",{'title':title}).fetchall()

		elif request.args.get("f") == 'f3':
			data = db.execute("SELECT * FROM books WHERE author = :author",{'author':author}).fetchall()

		elif request.args.get("f") == 'f4':
			if (author is not None and title is not None and author is not None):
				data = db.execute("SELECT * FROM books WHERE (title = :title AND isbn = :isbn) AND (author = :author)",{'title':title, 'isbn':isbn,'author':author}).fetchall()
			else:
				data = 'incomplete'

		return render_template('searched.html', data=data)

	else:
		return redirect(url_for('login'))

@app.route('/book/<int:no>', methods=['GET', 'POST'])
def book(no):
	if 'user' not in session:
			return redirect(url_for('login'))

	if request.method=='GET':

		"""Collecting only 1 book data whose id is no"""
		book = db.execute("SELECT * FROM books WHERE id = :id",{'id':no}).fetchone()

		"""Checking if enter book is valid or not"""
		if book is None:
			return render_template('error.html', error = 'Entered Id is Incorrect!')

		"""Checking if user has already reviewed it or not"""
		reviewed = db.execute("SELECT * FROM reviews WHERE users_id = :users_id AND books_id = :books_id",{'users_id': session['user'][0], 'books_id': no}).fetchone()
		if reviewed is None:
			flag = True
		else:
			flag = False

		"""Taking another people reviews to display on page"""
		reviews = db.execute("SELECT username, rating, review FROM reviews JOIN users ON users.id = reviews.users_id WHERE books_id = :books_id", {'books_id': no}).fetchall()

		"""Using API to get Goodreads Reviews"""
		res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "am79tEwwV9gqV6uXm5SA", "isbns": book.isbn})
		dic = res.json()

		"""0 index showing average_rating, 1 shows reviews count"""
		goodratings = [dic['books'][0]['average_rating'], dic['books'][0]['ratings_count']]

		return render_template('book.html', book=book, flag=flag, reviews=reviews, goodratings=goodratings)
		

	else:
		rating = request.form.get('rating')
		if rating is None:
			rating = 1
		review = request.form.get('review')
		db.execute("INSERT INTO reviews (users_id, books_id, rating, review) VALUES (:users_id, :books_id, :rating, :review)", {'users_id': session['user'][0], 'books_id': no, 'rating' : int(rating), 'review': review})
		db.commit()
		return redirect(url_for('book', no=no))


@app.route('/api/<string:isbn>')
def api(isbn):

	"""Fetching Book"""
	book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {'isbn':isbn}).fetchone()

	"""Checking if book is Available or Not"""
	if book is None:
		return abort(404)

	"""Calculating review counts and average score"""
	cal = db.execute("SELECT COUNT(*), AVG(rating) FROM reviews WHERE books_id = :books_id", {'books_id': book.id}).fetchall()

	try:
		return jsonify({
			"title": book.title,
	    	"author": book.author,
	    	"year": book.year,
	    	"isbn": book.isbn,
	    	"review_count": cal[0].count,
	    	"average_score": float(cal[0].avg)
			})
	except Exception:
		return jsonify({
			"title": book.title,
	    	"author": book.author,
	    	"year": book.year,
	    	"isbn": book.isbn,
	    	"review_count": cal[0].count,
	    	"average_score": 0
			})



