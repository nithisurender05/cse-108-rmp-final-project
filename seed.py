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

        # 4. Create a Dummy Review (Must happen after user & profs are saved)
        # Let's review Dr. Turing (who is index 0 in our list)
        review1 = Review(
            user_id=test_user.id, 
            professor_id=profs[0].id, 
            course_code="CS 101", 
            rating=5, 
            comment="Incredible lecturer, invented computers basically."
        )
        db.session.add(review1)
        
        db.session.commit()
        print("Database seeded! Created 5 professors, 1 user, and 1 review.")

if __name__ == "__main__":
    seed_data()