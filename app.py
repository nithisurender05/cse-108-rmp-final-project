from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime

app = Flask(__name__)

# CONFIGURATION
# Replace 'root', 'password' with your actual MySQL credentials
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SECRET_KEY'] = 'key' # Needed for session management
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- DATABASE MODELS (Mapping Python Classes to SQL Tables) ---

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Professor(db.Model):
    __tablename__ = 'professors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    university = db.Column(db.String(100))
    reviews = db.relationship('Review', backref='professor', lazy=True)

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('professors.id'), nullable=False)
    course_code = db.Column(db.String(20), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    votes = db.relationship('ReviewVote', backref='review', lazy=True)

class ReviewVote(db.Model):
    __tablename__ = 'review_votes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'), nullable=False)
    vote_type = db.Column(db.Integer, nullable=False) # 1 = Like, -1 = Dislike

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

@app.route('/')
def home():
    # Show list of all professors
    professors = Professor.query.all()
    return render_template('index.html', professors=professors)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Hash the password
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Create user
        new_user = User(username=username, email=request.form.get('email'), password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and bcrypt.check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Login Failed. Check username and password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/professor/<int:id>', methods=['GET', 'POST'])
def professor_detail(id):
    professor = Professor.query.get_or_404(id)
    
    # Filter Logic
    course_filter = request.args.get('course')
    if course_filter:
        reviews = Review.query.filter_by(professor_id=id, course_code=course_filter).all()
    else:
        reviews = professor.reviews

    # Calculate Average Rating
    avg_rating = 0
    if reviews:
        avg_rating = sum([r.rating for r in reviews]) / len(reviews)

    return render_template('professor_detail.html', professor=professor, reviews=reviews, avg_rating=round(avg_rating, 1))

@app.route('/professor/<int:id>/add_review', methods=['POST'])
@login_required
def add_review(id):
    rating = int(request.form.get('rating'))
    course = request.form.get('course')
    comment = request.form.get('comment')
    
    new_review = Review(user_id=current_user.id, professor_id=id, course_code=course, rating=rating, comment=comment)
    db.session.add(new_review)
    db.session.commit()
    return redirect(url_for('professor_detail', id=id))

@app.route('/vote/<int:review_id>/<int:vote_type>', methods=['POST'])
@login_required
def vote_review(review_id, vote_type):
    # Check if user already voted
    existing_vote = ReviewVote.query.filter_by(user_id=current_user.id, review_id=review_id).first()
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Toggle off if clicking same button (remove vote)
            db.session.delete(existing_vote)
        else:
            # Change vote
            existing_vote.vote_type = vote_type
    else:
        # New vote
        new_vote = ReviewVote(user_id=current_user.id, review_id=review_id, vote_type=vote_type)
        db.session.add(new_vote)
    
    db.session.commit()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)