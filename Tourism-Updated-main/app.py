from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_required, current_user
import os
from dotenv import load_dotenv

from models import db, User, Wishlist, Complaint
from auth import auth
from recommender import get_recommendations
from helpers import (get_weather, get_image, get_wikipedia_summary, get_related_places,
                     get_place_images, popular_places, best_time,
                     place_coordinates, place_activities, place_how_to_reach, place_facts)

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
    from models import Review
    recent_reviews = Review.query.order_by(Review.id.desc()).limit(5).all()

    cards = []
    for place in popular_places:
        name = place["name"]
        cards.append({
            "name": name,
            "category": place["category"],
            "image": get_image(name),   # served from disk cache — fast
            "best_time": best_time.get(name, "All year")
            # weather is loaded client-side via /api/weather/<city>
        })

    return render_template('index.html', reviews=recent_reviews, popular_cards=cards)

# Lightweight JSON endpoint for async weather fetching
@app.route('/api/weather/<city>')
def api_weather(city):
    from flask import jsonify
    return jsonify({"weather": get_weather(city)})

@app.route('/place/<name>')
def place_detail(name):
    description = get_wikipedia_summary(name)
    image = get_image(name)
    images = get_place_images(name)
    weather = get_weather(name)
    recommendations = get_related_places(name)

    coords = place_coordinates.get(name, [30.3165, 78.0322])
    activities = place_activities.get(name, [])
    how_to_reach = place_how_to_reach.get(name, {})
    facts = place_facts.get(name, {})

    return render_template("place.html",
                           name=name,
                           description=description,
                           image=image,
                           images=images,
                           weather=weather,
                           best_time=best_time.get(name, "All year"),
                           recommendations=recommendations,
                           coordinates=coords,
                           activities=activities,
                           how_to_reach=how_to_reach,
                           facts=facts)

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
        destination = request.form.get('destination', '').strip().title()
        city        = request.form.get('city', '').strip().title()
        country     = request.form.get('country', '').strip().title()
        category    = request.form.get('category', 'All').strip()
        if not destination or not city or not country:
            recommendations = ["Please provide a valid destination, city, and country."]
            return render_template('recommend.html', recommendations=recommendations)
        recommendations = get_recommendations(destination, city, country, category)
        return render_template('recommend.html', recommendations=recommendations, city=city, country=country)
    return render_template('recommend.html', recommendations=[])

@app.route('/helplines')
def helplines():
    return render_template('helplines.html')


# -----------------------
# Profile Route
# -----------------------
@app.route('/profile')
@login_required
def profile():
    from models import Review, Complaint
    user_reviews   = Review.query.filter_by(user_id=current_user.id).all()
    user_wishlist  = Wishlist.query.filter_by(user_id=current_user.id).all()
    user_complaints = Complaint.query.filter_by(user_id=current_user.id).count()
    return render_template(
        'profile.html',
        reviews=user_reviews,
        wishlist=user_wishlist,
        complaint_count=user_complaints
    )


# -----------------------
# Wishlist Routes
# -----------------------
@app.route('/wishlist/add', methods=['POST'])
@login_required
def wishlist_add():
    place_name = request.form.get('place_name', '').strip()
    city       = request.form.get('city', '').strip()
    country    = request.form.get('country', '').strip()
    notes      = request.form.get('notes', '').strip()
    if not place_name:
        flash('Place name is required.', 'danger')
        return redirect(url_for('profile'))
    # Prevent duplicates
    existing = Wishlist.query.filter_by(user_id=current_user.id, place_name=place_name).first()
    if existing:
        flash(f'"{place_name}" is already in your bucket list!', 'warning')
        return redirect(url_for('profile'))
    item = Wishlist(place_name=place_name, city=city, country=country, notes=notes, user_id=current_user.id)
    db.session.add(item)
    db.session.commit()
    flash(f'"{place_name}" added to your bucket list!', 'success')
    return redirect(url_for('profile'))


@app.route('/wishlist/remove/<int:item_id>', methods=['POST'])
@login_required
def wishlist_remove(item_id):
    item = Wishlist.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('profile'))
    db.session.delete(item)
    db.session.commit()
    flash('Place removed from bucket list.', 'info')
    return redirect(url_for('profile'))

# -----------------------
# Run
# -----------------------
if __name__ == '__main__':
    app.run(debug=True)
