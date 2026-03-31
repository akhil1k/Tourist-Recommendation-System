from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
import os
from dotenv import load_dotenv
from groq import Groq

# Load env vars from .env
load_dotenv()

# Environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Groq API key not found. Set GROQ_API_KEY in your .env file.")

# Configure Groq client
client = Groq(api_key=GROQ_API_KEY)


app = Flask(__name__)

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tourism.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SECRET_KEY'] = 'mysecret'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# -----------------------
# Database models
# -----------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    reviews = db.relationship('Review', backref='author', lazy='dynamic')
    complaints = db.relationship('Complaint', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='Pending')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -----------------------
# Groq recommendation helper
# -----------------------
def get_recommendations(destination, city, country):
    """
    Use Groq (Llama 3) to generate tourist recommendations.
    Returns a list of bullet-point strings.
    """
    prompt = f"""You are a knowledgeable local travel guide. List the top 5 must-visit tourist attractions strictly located within a 10 to 15 kilometer radius of "{destination}" in {city}, {country}. Do NOT include places that are far away from this specific location.

For each attraction, provide:
• The name of the attraction
• A 2-3 line engaging summary describing why it is worth visiting, briefly mentioning approximately how far it is from {destination}.

Format your response as a simple bullet-point list. Each item should start with the attraction name 
followed by a colon, then the summary. Do not use numbering, use bullet points (•) only.
Do not include any introduction or closing text, just the bullet points."""

    try:
        print(f"\n🔍 Searching recommendations for: {destination}, {city}, {country}")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024
        )

        result_text = response.choices[0].message.content
        if result_text:
            lines = result_text.strip().split("\n")
            recommendations = [line.strip() for line in lines if line.strip()]
            print(f"✅ Successfully got {len(recommendations)} recommendations")
            return recommendations
        else:
            print("⚠️ Groq returned an empty response")
            return ["No recommendations could be generated. Please try again."]

    except Exception as e:
        print(f"\n❌ ERROR in get_recommendations:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        return [f"Error getting recommendations: {str(e)}"]


# -----------------------
# Flask routes
# -----------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect('/login')
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists.', 'danger')
    return render_template('register.html')

# filepath comment kept from your original
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check your username or password.', 'danger')
    return render_template('login.html')

@app.route('/review', methods=['GET', 'POST'])
@login_required
def review():
    if request.method == 'POST':
        place_name = request.form['place_name']
        rating = int(request.form['rating'])
        review_text = request.form['review_text']
        new_review = Review(place_name=place_name, rating=rating, review_text=review_text, user_id=current_user.id)
        db.session.add(new_review)
        try:
            db.session.commit()
            flash('Review submitted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting review: {str(e)}', 'danger')
        return redirect(url_for('index'))
    return render_template('review.html')

@app.route('/complaint', methods=['GET', 'POST'])
@login_required
def complaint():
    if request.method == 'POST':
        complaint_text = request.form['complaint_text']
        new_complaint = Complaint(complaint_text=complaint_text, user_id=current_user.id)
        db.session.add(new_complaint)
        try:
            db.session.commit()
            flash('Complaint submitted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting complaint: {str(e)}', 'danger')
        return redirect(url_for('index'))
    return render_template('complaint.html')

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    recommendations = []
    if request.method == 'POST':
        destination = request.form['destination'].strip().title()
        city = request.form['city'].strip().title()
        country = request.form['country'].strip().title()
        if not destination or not city or not country:
            recommendations = ["Please provide a valid destination, city, and country."]
            return render_template('recommend.html', recommendations=recommendations)

        recommendations = get_recommendations(destination, city, country)
    return render_template('recommend.html', recommendations=recommendations)

@app.route('/helplines')
def helplines():
    return render_template('helplines.html')

# -----------------------
# Initialize DB & run
# -----------------------
def init_db():
    with app.app_context():
        db.create_all()

init_db()

if __name__ == '__main__':
    app.run(debug=True)
