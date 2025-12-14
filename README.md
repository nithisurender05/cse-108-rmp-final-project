# cse-108-rmp-final-project
Rate My Professor DUPE!

😈😺  𝐓ᕼ𝒾ＮĞＳ Ⓣㄖ 𝐖Ỗ𝐫ᵏ Ⓞℕ  🎁♝

Professor Registration and Log In (to add yourself to list)

Sorting by Keyword

Reply to Reviews

Anonymous Option for Reviewers?

Admin Login to delete inappropriate reviews

Database note:
- Email column is required (NOT NULL). Do NOT remove it. The app expects `users.email` to exist and be NOT NULL. If you need to migrate the DB, use a controlled migration tool like Alembic and avoid ad-hoc scripts.

- Professors:

- Professors can sign up with a dedicated form at `/professor/signup`. When a professor signs up, they're assigned the `professor` role and a linked profile is created.
- After signup professors can access their dashboard at `/professor/dashboard` where they can view their averaged rating, all reviews, and a short AI-style summary of criticism.

Troubleshooting registration:
- Fix your HTML form: make sure the input contains a name attribute exactly `name="email"`.
- Template snippet to use in `templates/register.html`:
	```html
	<input type="email" name="email" id="email" required>
	```
- Ensure the Flask route reads `request.form.get('email')` and validates presence before commit.
- The app by default uses `sqlite:///site.db`. If your SQLite is stored in `instance/site.db`, update `SQLALCHEMY_DATABASE_URI` to `sqlite:///instance/site.db`.
