from app import app, db, Professor, User, Review, bcrypt

def seed_data():
    with app.app_context():
        # 1. Drop everything to start fresh (Optional - remove if you want to keep old data)
        db.drop_all()
        db.create_all()

        # 2. Create Dummy Professors
        profs = [
            Professor(name="Dr. Alan Turing", department="Computer Science", university="Cambridge"),
            Professor(name="Dr. Marie Curie", department="Physics", university="Sorbonne"),
            Professor(name="Dr. Ada Lovelace", department="Mathematics", university="University of London"),
            Professor(name="Dr. Richard Feynman", department="Physics", university="Caltech"),
            Professor(name="Dr. Grace Hopper", department="Computer Science", university="Yale")
        ]
        
        db.session.add_all(profs)
        
        # 3. Create a Dummy User (so you can log in immediately)
        # Password will be "password123"
        hashed_pw = bcrypt.generate_password_hash("password123").decode('utf-8')
        test_user = User(username="test_student", email="student@example.com", password_hash=hashed_pw)
        db.session.add(test_user)
        
        # Commit so the IDs are generated
        db.session.commit()

        # 3b. Create a test user WITHOUT an email to verify optional-email flow
        anon_user = User(username="test_noemail", email=None, password_hash=hashed_pw)
        db.session.add(anon_user)
        db.session.commit()

        # 3c. Seed some canonical Course entries so they appear in the navbar selector
        from app import Course
        courses = [
            Course(code='CS 101'),
            Course(code='CS 201'),
            Course(code='MATH 201'),
            Course(code='PHYS 150'),
        ]
        for c in courses:
            exists = Course.query.filter_by(code=c.code).first()
            if not exists:
                db.session.add(c)
        db.session.commit()

        # 4. Create a Dummy Review (Must happen after user & profs are saved)
        # Let's review Dr. Turing (who is index 0 in our list)
        review1 = Review(
            user_id=test_user.id, 
            professor_id=profs[0].id, 
            course_code="CS 101", 
            rating=5, 
            comment="Incredible lecturer, invented computers basically.",
            grade='A',
            semester='Fall',
            year=2023
        )
        db.session.add(review1)
        
        # Additional reviews so more courses and professors appear in selectors
        review2 = Review(user_id=test_user.id, professor_id=profs[4].id, course_code="CS 101", rating=4, comment="Practical and engaging.", grade='A-', semester='Fall', year=2023)
        review3 = Review(user_id=test_user.id, professor_id=profs[2].id, course_code="MATH 201", rating=5, comment="Brilliant explanations of proofs.", grade='A', semester='Spring', year=2024)
        review4 = Review(user_id=test_user.id, professor_id=profs[1].id, course_code="PHYS 150", rating=4, comment="Loved the lab sessions.", grade='B+', semester='Fall', year=2022)
        review5 = Review(user_id=test_user.id, professor_id=profs[3].id, course_code="PHYS 150", rating=5, comment="Makes complex topics simple.", grade='A', semester='Spring', year=2023)
        review6 = Review(user_id=anon_user.id, professor_id=profs[0].id, course_code="CS 201", rating=4, comment="Challenging but fair.", grade='B', semester='Spring', year=2024)
        db.session.add_all([review2, review3, review4, review5, review6])

        db.session.commit()
        # 5. Create a professor user for testing
        hashed_pw2 = bcrypt.generate_password_hash("professor123").decode('utf-8')
        prof_user = User(username="prof_jones", email="jones@example.com", password_hash=hashed_pw2, role='professor')
        db.session.add(prof_user)
        db.session.commit()

        # Create professor profile linking to the prof user
        prof_profile = Professor(name="Dr. Jones", department="History", university="State U", user_id=prof_user.id)
        db.session.add(prof_profile)
        db.session.commit()
        # 6. Create an admin user for testing
        hashed_admin_pw = bcrypt.generate_password_hash("adminpass").decode('utf-8')
        admin_user = User(username="admin", email="admin@example.com", password_hash=hashed_admin_pw, role='admin')
        db.session.add(admin_user)
        db.session.commit()

        # Add a few reviews for Dr. Jones
        r1 = Review(user_id=test_user.id, professor_id=prof_profile.id, course_code="HIST 200", rating=2, comment="Hard grading and unclear expectations.", grade='B-', semester='Spring', year=2023)
        r2 = Review(user_id=test_user.id, professor_id=prof_profile.id, course_code="HIST 201", rating=4, comment="Great lectures but heavy workload.", grade='A-', semester='Fall', year=2022)
        db.session.add_all([r1, r2])
        db.session.commit()
        print("Database seeded! Created 5 professors, test users (with and without email), admin user, and several reviews.")

if __name__ == "__main__":
    seed_data()