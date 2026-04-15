from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_required, current_user
import os
from dotenv import load_dotenv

from models import db, User
from auth import auth
from recommender import get_recommendations

# Load environment variables
load_dotenv()

app = Flask(__name__)

# -----------------------
# App Configuration
# -----------------------
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tourism.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mysecret')

# -----------------------
# Initialize Extensions
# -----------------------
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'   # Points to the Blueprint's login route

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# -----------------------
# Register Blueprints
# -----------------------
app.register_blueprint(auth)

# -----------------------
# Initialize DB Tables
# -----------------------
with app.app_context():
    db.create_all()

# -----------------------
# Application Routes
# -----------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/review', methods=['GET', 'POST'])
@login_required
def review():
    from models import Review
    if request.method == 'POST':
        place_name  = request.form['place_name']
        rating      = int(request.form['rating'])
        review_text = request.form['review_text']
        new_review  = Review(
            place_name=place_name,
            rating=rating,
            review_text=review_text,
            user_id=current_user.id
        )
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
    from models import Complaint
    if request.method == 'POST':
        complaint_text = request.form['complaint_text']
        new_complaint  = Complaint(complaint_text=complaint_text, user_id=current_user.id)
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
        city        = request.form['city'].strip().title()
        country     = request.form['country'].strip().title()
        if not destination or not city or not country:
            recommendations = ["Please provide a valid destination, city, and country."]
            return render_template('recommend.html', recommendations=recommendations)
        recommendations = get_recommendations(destination, city, country)
    return render_template('recommend.html', recommendations=recommendations)

@app.route('/helplines')
def helplines():
    return render_template('helplines.html')

# -----------------------
# Run
# -----------------------
if __name__ == '__main__':
    app.run(debug=True)
