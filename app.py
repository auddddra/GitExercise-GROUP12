from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# -----------------------
# Flask setup
# -----------------------
app = Flask(__name__)
app.secret_key = "super_secret_091725"

# -----------------------
# Database setup
# -----------------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db = SQLAlchemy(app)

# -----------------------
# User model
# -----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

with app.app_context():
    db.create_all()

# -----------------------
# Helper functions (console use)
# -----------------------


def register_user(username, email, password):
    """Register a new user with a hashed password (console)."""
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print("⚠️ Username already exists!")
            return

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        print(f"✅ User '{username}' registered!")

        return 

def check_login(username, password):
    """Check login credentials (console)."""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            print("✅ Login success!")
            return True
        else:
            print("❌ Wrong username or password.")
            return False


def delete_user(username):
    """Delete a user (console)."""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print("⚠️ User not found!")
            return
        db.session.delete(user)
        db.session.commit()
        print(f"🗑️ User '{username}' deleted!")

# -----------------------
# Flask Routes (frontend use)
# -----------------------
@app.route("/")
def home():
    return render_template("login.html")  # your combined login/register HTML

@app.route("/register", methods=["GET", "POST"])
def register():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")

    if User.query.filter_by(username=username).first():
        flash("⚠️ Username already exists!", "danger")
        return redirect(url_for("login"))

    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    flash("✅ Registration successful! Please log in.", "success")
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        session["user_id"] = user.id
        session["username"] = user.username
        flash("✅ Login successful!", "success")
        return redirect(url_for("profile"))
    else:
        flash("❌ Invalid username or password", "danger")
        return redirect(url_for("login"))

@app.route("/profile")
def profile():
    return render_template("profile-page.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# -----------------------
# Run App
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
