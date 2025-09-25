from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_dance.contrib.google import make_google_blueprint, google

app = Flask(__name__)
app.secret_key = "super_secret_091725"

# database setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db = SQLAlchemy(app)

# GOOGLE API
google_bp = make_google_blueprint(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    redirect_to="google_login"
)
app.register_blueprint(google_bp, url_prefix="/login")

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=True, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=True)  # nullable so Google login works

with app.app_context():
    db.create_all()

# Google Login Route
@app.route("/google_login")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return "Google login failed", 400

    user_info = resp.json()
    email = user_info["email"]

    # check if user already exists
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(username=email.split("@")[0], email=email, password=None)
        db.session.add(user)
        db.session.commit()

    # save login session
    session["user_id"] = user.id
    session["username"] = user.username
    flash("✅ Logged in with Google!", "success")
    return redirect(url_for("profile"))

# normal auth routes
@app.route("/")
def home():
    return render_template("login.html")  # combined login/register HTML

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")

    if User.query.filter_by(username=username).first():
        flash("⚠️ Username already exists!", "danger")
        return redirect(url_for("home"))

    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    flash("✅ Registration successful! Please log in.", "success")
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    user = User.query.filter_by(username=username).first()

    if user and user.password and check_password_hash(user.password, password):
        session["user_id"] = user.id
        session["username"] = user.username
        flash("✅ Login successful!", "success")
        return redirect(url_for("profile"))
    else:
        flash("❌ Invalid username or password", "danger")
        return redirect(url_for("home"))

@app.route("/profile")
def profile():
    if "user_id" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("home"))
    user = User.query.get(session["user_id"])
    return render_template("profile-page.html", user=user)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

# Run App
if __name__ == "__main__":
    app.run(debug=True)
