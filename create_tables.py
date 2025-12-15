from app import db, app

with app.app_context():
    db.create_all()
    print("✅ Database tables created successfully!")
    print("You can now run your app normally.")