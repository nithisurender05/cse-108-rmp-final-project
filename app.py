from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
from sqlalchemy import func, or_
import re

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
    email = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, server_default='student')

class Professor(db.Model):
    __tablename__ = 'professors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    university = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviews = db.relationship('Review', backref='professor', lazy=True)
    user = db.relationship('User', backref='professor_profile', uselist=False)

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('professors.id'), nullable=False)
    course_code = db.Column(db.String(20), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    grade = db.Column(db.String(5), nullable=True)
    semester = db.Column(db.String(10), nullable=True)
    year = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    votes = db.relationship('ReviewVote', backref='review', lazy=True)
    user = db.relationship('User', backref='reviews', uselist=False)
    replies = db.relationship('ReviewReply', backref='review', lazy=True)
    
    

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=True)


class ReviewVote(db.Model):
    __tablename__ = 'review_votes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'), nullable=False)
    vote_type = db.Column(db.Integer, nullable=False) # 1 = Like, -1 = Dislike


class ReviewReply(db.Model):
    __tablename__ = 'review_replies'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='replies', uselist=False)


## Reply model removed — no direct replies to reviews

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

@app.route('/')
def home():
    # Show list of all professors
    professors = Professor.query.all()
    # If the logged-in user is a professor, show their dashboard as home
    # unless they specifically request to view other professors using '?view=others'
    if current_user.is_authenticated and getattr(current_user, 'role', None) == 'professor' and request.args.get('view') != 'others':
        return redirect(url_for('professor_dashboard'))
    return render_template('index.html', professors=professors)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        role = request.form.get('role') or 'student'
        prof_name = request.form.get('prof_name')
        department = request.form.get('department') or ''
        other_dept = request.form.get('other_department') or ''
        # If "Other" was selected, use the provided other_department value
        # Accept other_department either when 'Other' is selected or when department left blank
        if (not department or department == 'Other') and other_dept:
            department = other_dept
        university = request.form.get('university')

        # Debugging: show captured values (do NOT print password in production)
        app.logger.debug(f"Register form data — username={username}, email={email}, password_provided={bool(password)}")

        # Basic validation
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return redirect(url_for('register'))

        # If professor, require professor name
        if role == 'professor' and not prof_name:
            flash('Professor name is required for professor signups.', 'danger')
            return redirect(url_for('register'))

        # Prevent duplicate usernames
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose another.', 'danger')
            return redirect(url_for('register'))

        # If email provided, check duplicates
        if email and User.query.filter_by(email=email).first():
            flash('Email already registered. Please use another or log in.', 'danger')
            return redirect(url_for('register'))

        # Hash the password
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        # Create user with selected role
        new_user = User(username=username, email=email or None, password_hash=hashed_pw, role=role)
        db.session.add(new_user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.exception('Failed to create user')
            flash('Failed to create account. Please try again.', 'danger')
            return redirect(url_for('register'))

        # If professor, create profile, auto-login, and redirect to dashboard
        if role == 'professor':
            try:
                new_prof = Professor(name=prof_name, department=department, university=university, user_id=new_user.id)
                db.session.add(new_prof)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                app.logger.exception('Failed to create professor profile')
                flash('Failed to create professor profile. Please try again.', 'danger')
                return redirect(url_for('register'))
            login_user(new_user)
            flash('Professor account created! Welcome to your dashboard.', 'success')
            return redirect(url_for('professor_dashboard'))

        # Otherwise, treat as student: auto-login and redirect to home
        login_user(new_user)
        flash('Account created! You are now logged in.', 'success')
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and bcrypt.check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            # If professor, go to dashboard; otherwise go to home
            if getattr(user, 'role', None) == 'professor':
                return redirect(url_for('professor_dashboard'))
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

    # Add vote counts and user_vote to each review for the template
    for r in reviews:
        r.likes_count = ReviewVote.query.filter_by(review_id=r.id, vote_type=1).count()
        r.dislikes_count = ReviewVote.query.filter_by(review_id=r.id, vote_type=-1).count()
        if current_user.is_authenticated:
            v = ReviewVote.query.filter_by(review_id=r.id, user_id=current_user.id).first()
            r.user_vote = v.vote_type if v else 0
        else:
            r.user_vote = 0
        # Load replies for each review
        r.replies_list = ReviewReply.query.filter_by(review_id=r.id).order_by(ReviewReply.created_at.asc()).all()
        # (No reply list) Keep existing review info

    return render_template('professor_detail.html', professor=professor, reviews=reviews, avg_rating=round(avg_rating, 1))


@app.route('/search')
def search():
    q = request.args.get('q', '')
    q_stripped = (q or '').strip()
    if not q_stripped:
        return redirect(url_for('home'))

    # Professors matching name, department, or university
    profs_by_name = Professor.query.filter(Professor.name.ilike(f"%{q_stripped}%")).all()
    profs_by_dept = Professor.query.filter(or_(Professor.department.ilike(f"%{q_stripped}%"), Professor.university.ilike(f"%{q_stripped}%"))).all()

    # Normalize query for course matching (remove non-alphanumeric)
    q_norm = re.sub(r"\W+", "", q_stripped).lower()

    # Build a SQL expression that removes common separators from course_code and lowercases it
    cleaned_course = func.lower(func.replace(func.replace(func.replace(Review.course_code, ' ', ''), '-', ''), '.', ''))

    # Find reviews where cleaned course_code contains the normalized query
    reviews_by_course = []
    if q_norm:
        reviews_by_course = Review.query.filter(cleaned_course.ilike(f"%{q_norm}%")).all()

    # Also search review comments for the query (helps match subjects mentioned in reviews)
    reviews_by_comment = Review.query.filter(Review.comment.ilike(f"%{q_stripped}%")).all()

    # Combine review results
    reviews = {r.id: r for r in (reviews_by_course + reviews_by_comment)}

    # Map course_code -> set of professors
    courses_map = {}
    profs_by_course = {}
    for r in reviews.values():
        if not r.course_code:
            continue
        code_display = r.course_code
        prof = r.professor
        if code_display not in courses_map:
            courses_map[code_display] = set()
        if prof:
            courses_map[code_display].add((prof.id, prof.name))
            profs_by_course[prof.id] = prof

    # Combine professors from name, department/university, and course/comment matches (unique)
    profs_dict = {p.id: p for p in profs_by_name}
    for p in profs_by_dept:
        profs_dict[p.id] = p
    for pid, p in profs_by_course.items():
        profs_dict[pid] = p

    combined_profs = list(profs_dict.values())

    # Convert course map to list for template
    course_list = []
    for code, profs in courses_map.items():
        course_list.append({'course_code': code, 'professors': [{'id': pid, 'name': pname} for pid, pname in sorted(list(profs))]})

    return render_template('search_results.html', query=q_stripped, professors=combined_profs, courses=course_list)


@app.route('/api/professors_for_course')
def professors_for_course():
    # Return JSON list of professors who have reviews for the given course code
    q = request.args.get('q', '')
    q_stripped = (q or '').strip()
    if not q_stripped:
        return jsonify([])

    # Normalize course code for matching
    q_norm = re.sub(r"\W+", "", q_stripped).lower()
    cleaned_course = func.lower(func.replace(func.replace(func.replace(Review.course_code, ' ', ''), '-', ''), '.', ''))

    profs = {}
    # First try exact normalized matches
    matched = Review.query.filter(cleaned_course == q_norm).all()
    for r in matched:
        if r.professor:
            profs[r.professor.id] = r.professor.name

    # Fallback: case-insensitive contains match
    if not profs:
        matched2 = Review.query.filter(Review.course_code.ilike(f"%{q_stripped}%")).all()
        for r in matched2:
            if r.professor:
                profs[r.professor.id] = r.professor.name

    out = [{'id': pid, 'name': name} for pid, name in profs.items()]
    return jsonify(out)


@app.route('/rate_class', methods=['GET', 'POST'])
def rate_class():
    if request.method == 'POST':
        course = (request.form.get('course') or '').strip()
        # If the form used the 'Other' course field, it will post 'course'=='__other__' and the
        # real value will be in 'course_other'. Prefer that when present.
        if course == '__other__':
            course_other = (request.form.get('course_other') or '').strip()
            course = course_other
        rating_val = request.form.get('rating')
        professor_choice = request.form.get('professor_id')
        comment = request.form.get('comment') or None

        if not course or not rating_val:
            flash('Course and rating are required.', 'danger')
            return redirect(url_for('rate_class'))

        try:
            rating = int(rating_val)
        except ValueError:
            flash('Invalid rating.', 'danger')
            return redirect(url_for('rate_class'))

        professor_id = None
        # Existing professor selected
        if professor_choice and professor_choice != 'new':
            try:
                professor_id = int(professor_choice)
                if not Professor.query.get(professor_id):
                    flash('Selected professor not found.', 'danger')
                    return redirect(url_for('rate_class'))
            except ValueError:
                professor_id = None

        # Add new professor
        if professor_choice == 'new':
            prof_name = request.form.get('prof_name')
            department = request.form.get('department') or ''
            other_dept = request.form.get('other_department') or ''
            if (not department or department == 'Other') and other_dept:
                department = other_dept
            university = request.form.get('university')

            if not prof_name:
                flash('Professor name is required when adding a new professor.', 'danger')
                return redirect(url_for('rate_class'))

            try:
                new_prof = Professor(name=prof_name, department=department, university=university)
                db.session.add(new_prof)
                db.session.commit()
                professor_id = new_prof.id
            except Exception:
                db.session.rollback()
                app.logger.exception('Failed to create new professor')
                flash('Failed to create professor. Try again.', 'danger')
                return redirect(url_for('rate_class'))

        if not professor_id:
            flash('Please select or add a professor to associate with this class.', 'danger')
            return redirect(url_for('rate_class'))

        user_id = current_user.id if current_user.is_authenticated else None
        # Ensure the Course exists in Course table for future quick-selection
        try:
            existing_course = Course.query.filter(func.lower(Course.code) == course.lower()).first()
        except Exception:
            existing_course = None
        if not existing_course:
            try:
                new_course = Course(code=course)
                db.session.add(new_course)
                db.session.commit()
            except Exception:
                db.session.rollback()
        new_review = Review(user_id=user_id, professor_id=professor_id, course_code=course, rating=rating, comment=comment)
        db.session.add(new_review)
        db.session.commit()
        flash('Class rating submitted.', 'success')
        return redirect(url_for('professor_detail', id=professor_id))

    # GET: build a list of distinct course codes from reviews
    codes = [rc[0] for rc in db.session.query(Review.course_code).distinct().all() if rc[0]]
    codes = sorted({c.strip() for c in codes})
    selected = request.args.get('course', '')
    return render_template('rate_class.html', course_codes=codes, selected_course=selected)


@app.route('/api/course_codes')
def api_course_codes():
    # Prefer explicit Course table if populated
    try:
        course_rows = Course.query.order_by(Course.code.asc()).all()
    except Exception:
        course_rows = []

    if course_rows:
        codes = [c.code for c in course_rows]
        return jsonify(codes)

    codes = [rc[0] for rc in db.session.query(Review.course_code).distinct().all() if rc[0]]
    codes = sorted({c.strip() for c in codes})
    return jsonify(codes)





@app.route('/review/<int:review_id>/reply', methods=['POST'])
@login_required
def add_reply(review_id):
    review = Review.query.get_or_404(review_id)
    comment = request.form.get('reply_comment')
    if not comment or comment.strip() == '':
        flash('Reply cannot be empty.', 'danger')
        return redirect(url_for('professor_detail', id=review.professor_id))
    user_id = current_user.id if current_user.is_authenticated else None
    new_reply = ReviewReply(user_id=user_id, review_id=review_id, comment=comment.strip())
    db.session.add(new_reply)
    db.session.commit()
    flash('Reply added.', 'success')
    return redirect(url_for('professor_detail', id=review.professor_id))


@app.route('/professor/dashboard')
@login_required
def professor_dashboard():
    # Only professors can access their dashboard
    if current_user.role != 'professor':
        flash('Only professors can access this dashboard.', 'danger')
        return redirect(url_for('home'))

    # Find the professor profile for this user
    professor = Professor.query.filter_by(user_id=current_user.id).first()
    if not professor:
        flash('No professor profile found for your account. Please add your profile.', 'warning')
        return redirect(url_for('professor_signup'))

    reviews = professor.reviews
    avg_rating = 0
    if reviews:
        avg_rating = sum([r.rating for r in reviews])/len(reviews)

    ai_summary = generate_reviews_summary(reviews)

    return render_template('professor_dashboard.html', professor=professor, reviews=reviews, avg_rating=round(avg_rating, 1), ai_summary=ai_summary)


@app.route('/admin/reviews')
@login_required
def admin_reviews():
    # Only admins can access the admin review management page
    if getattr(current_user, 'role', None) != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('home'))

    # Show all reviews with related professor and user info
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    # For display convenience, annotate author_name and professor_name
    for r in reviews:
        r.professor_name = r.professor.name if r.professor else 'Unknown'
        r.author_name = r.user.username if (r.user and r.user.username) else 'Anonymous'
        r.replies_list = ReviewReply.query.filter_by(review_id=r.id).order_by(ReviewReply.created_at.asc()).all()
    return render_template('admin_reviews.html', reviews=reviews)


@app.route('/admin/review/<int:review_id>/delete', methods=['POST'])
@login_required
def admin_delete_review(review_id):
    # Only admins can delete reviews
    if getattr(current_user, 'role', None) != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('home'))

    review = Review.query.get(review_id)
    if not review:
        flash('Review not found.', 'warning')
        return redirect(url_for('admin_reviews'))

    # Delete associated votes first
    ReviewVote.query.filter_by(review_id=review.id).delete()
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted successfully.', 'success')
    return redirect(url_for('admin_reviews'))


@app.route('/admin/reply/<int:reply_id>/delete', methods=['POST'])
@login_required
def admin_delete_reply(reply_id):
    if getattr(current_user, 'role', None) != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('home'))
    reply = ReviewReply.query.get(reply_id)
    if not reply:
        flash('Reply not found.', 'warning')
        return redirect(url_for('admin_reviews'))
    db.session.delete(reply)
    db.session.commit()
    flash('Reply deleted.', 'success')
    return redirect(url_for('admin_reviews'))


def generate_reviews_summary(reviews):
    # Simple heuristic summarizer: collect comments for negative/neutral reviews (rating <= 3)
    if not reviews:
        return None
    negative_comments = [r.comment for r in reviews if r.comment and r.rating <= 3]
    if not negative_comments:
        return 'No significant criticism found (most reviews are positive).'

    # Tokenize simple words, exclude stopwords, and find most common keywords
    stopwords = set(["the", "and", "or", "to", "a", "an", "is", "was", "in", "of", "for", "on", "with", "that", "this", "it"])
    from collections import Counter
    word_counts = Counter()
    for c in negative_comments:
        words = [w.strip('.,!?:;()\"\'\'').lower() for w in c.split()]
        for w in words:
            if w and w not in stopwords and len(w) > 2:
                word_counts[w] += 1

    common = [w for w, cnt in word_counts.most_common(5)]
    if not common:
        return 'Criticisms noted but unable to extract common themes.'
    return 'Common criticisms: ' + ', '.join(common)

@app.route('/professor/<int:id>/add_review', methods=['POST'])
def add_review(id):
    rating = int(request.form.get('rating'))
    course = request.form.get('course')
    comment = request.form.get('comment')
    # Allow anonymous reviews if user is not logged in
    user_id = current_user.id if current_user.is_authenticated else None
    # New fields: grade, semester, year
    grade = (request.form.get('grade') or '').strip() or None
    semester = request.form.get('semester') or None
    year_val = request.form.get('year')
    try:
        year = int(year_val) if year_val else None
    except ValueError:
        year = None
    new_review = Review(user_id=user_id, professor_id=id, course_code=course, rating=rating, comment=comment)
    new_review.grade = grade
    new_review.semester = semester
    new_review.year = year
    db.session.add(new_review)
    db.session.commit()
    return redirect(url_for('professor_detail', id=id))


## Reply endpoint removed — replies are no longer supported


@app.route('/professor/add', methods=['GET', 'POST'])
def add_professor():
    if request.method == 'POST':
        name = request.form.get('name')
        department = request.form.get('department') or ''
        other_dept = request.form.get('other_department') or ''
        if (not department or department == 'Other') and other_dept:
            department = other_dept
        university = request.form.get('university')

        # Basic validation
        if not name:
            flash('Professor name is required.', 'danger')
            return redirect(url_for('add_professor'))

        # Avoid duplicate professor with same name & university
        exists = Professor.query.filter_by(name=name, university=university).first()
        if exists:
            flash('This professor already exists.', 'warning')
            return redirect(url_for('professor_detail', id=exists.id))

        new_prof = Professor(name=name, department=department, university=university)
        db.session.add(new_prof)
        db.session.commit()
        flash('Professor added successfully!', 'success')
        return redirect(url_for('professor_detail', id=new_prof.id))

    return render_template('add_professor.html')


@app.route('/professor/signup', methods=['GET', 'POST'])
def professor_signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        prof_name = request.form.get('prof_name')
        department = request.form.get('department') or ''
        other_dept = request.form.get('other_department') or ''
        if (not department or department == 'Other') and other_dept:
            department = other_dept
        university = request.form.get('university')

        if not username or not password or not prof_name:
            flash('Username, password, and professor name are required for professor signup.', 'danger')
            return redirect(url_for('professor_signup'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose another.', 'danger')
            return redirect(url_for('professor_signup'))

        if email and User.query.filter_by(email=email).first():
            flash('Email already registered. Please login instead.', 'danger')
            return redirect(url_for('login'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email or None, password_hash=hashed_pw, role='professor')
        db.session.add(user)
        db.session.commit()

        # Create professor profile linking to the user
        new_prof = Professor(name=prof_name, department=department, university=university, user_id=user.id)
        db.session.add(new_prof)
        db.session.commit()

        # Log in the user
        login_user(user)
        flash('Professor account created and profile registered.', 'success')
        return redirect(url_for('professor_dashboard'))
    return render_template('professor_signup.html')

@app.route('/vote/<int:review_id>/<vote_type>', methods=['POST'])
def vote_review(review_id, vote_type):
    # Ensure the user is authenticated; return JSON 401 if not (AJAX-friendly)
    if not current_user.is_authenticated:
        return jsonify({'status': 'error', 'message': 'Login required'}), 401
    # Parse vote_type flexibly: accept '1', '-1', 'like', 'dislike'
    try:
        vt = int(vote_type)
    except ValueError:
        vt_lower = vote_type.lower()
        if vt_lower in ('like', 'up'):
            vt = 1
        elif vt_lower in ('dislike', 'down'):
            vt = -1
        else:
            return jsonify({'status': 'error', 'message': 'Invalid vote type'}), 400

    # Check if user already voted
    vote_type = vt
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

    # Recompute counts and return them to the client
    likes_count = ReviewVote.query.filter_by(review_id=review_id, vote_type=1).count()
    dislikes_count = ReviewVote.query.filter_by(review_id=review_id, vote_type=-1).count()
    # Determine current user's vote after the change
    user_vote_obj = ReviewVote.query.filter_by(review_id=review_id, user_id=current_user.id).first()
    user_vote = user_vote_obj.vote_type if user_vote_obj else 0

    return jsonify({'status': 'success', 'likes': likes_count, 'dislikes': dislikes_count, 'user_vote': user_vote})

if __name__ == '__main__':
    app.run(debug=True)