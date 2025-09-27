from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_dance.contrib.google import make_google_blueprint, google
from difflib import SequenceMatcher
import os
import requests
from dotenv import load_dotenv
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import sqlite3
from locations import get_faculty_name

load_dotenv()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # http for local dev

# ---------- Config ----------
UPLOAD_FOLDER = "static/uploads"
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_VIDEO_EXT = {"mp4", "webm", "ogg", "mov"}

app = Flask(__name__)
app.secret_key = "super_secret_091725"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


db = SQLAlchemy(app)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Email Config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
mail = Mail(app)

# Token Serializer
s = URLSafeTimedSerializer(app.secret_key)

# GOOGLE API
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

google_bp = make_google_blueprint(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
        scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email"
    ],
    redirect_url="/google_authorized"
)

app.register_blueprint(google_bp, url_prefix="/login")

@app.route("/google_authorized")
def google_authorized():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return "Google login failed", 400

    user_info = resp.json()
    email = user_info["email"]

    # Check if user exists
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(username=email.split("@")[0], email=email, password=None)
        db.session.add(user)
        db.session.commit()

    # Save login session
    session["user_id"] = user.id
    session["username"] = user.username
    flash("✅ Logged in with Google!", "success")
    return redirect(url_for("profile"))

with app.app_context():
    db.create_all()

# Load .env for Spotify
load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# ---------------- Helpers ---------------- #
def allowed_file(filename, kind="image"):
    ext = filename.rsplit(".", 1)[-1].lower()
    if kind == "image":
        return ext in ALLOWED_IMAGE_EXT
    elif kind == "video":
        return ext in ALLOWED_VIDEO_EXT
    return False

def get_token():
    """Request access token from Spotify"""
    auth_url = "https://accounts.spotify.com/api/token"
    auth_response = requests.post(
        auth_url,
        {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    auth_response_data = auth_response.json()
    return auth_response_data["access_token"]

# ---------------- Models ---------------- #
class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    to_name = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    photos = db.relationship("Photo", backref="card", lazy=True)
    video = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True) 
    song = db.Column(db.Text, nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected, archived

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("card.id"), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=True, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=True)  # nullable so Google login works
    is_admin = db.Column(db.Boolean, default=False)  

# ---------------- Routes ---------------- #

# ---------- Message Route ----------
@app.route("/message", methods=["GET", "POST"])
def message():
    if request.method == "POST":
        place_name = request.form.get("place_name")
        message = request.form.get("message")
        lat = request.form.get("lat")
        lng = request.form.get("lng")
        # Here you can also save the message to the DB if needed
        return f"Message for {place_name} at ({lat}, {lng}): {message}"
    else:
        lat = request.args.get("lat")
        lng = request.args.get("lng")
        return render_template("message.html", lat=lat, lng=lng)


# ---------- Index Route ----------
@app.route("/", methods=["GET"])

def index():
    search_query = request.args.get("q", "").strip()

    # Get approved cards
    cards = Card.query.filter_by(status="approved").all()

    # Check login/admin status
    user = None
    is_admin = False
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        is_admin = user.is_admin if user else False
    

    # Filter by search query if present
    if search_query:
        filtered_cards = [
            card for card in cards
            if search_query.lower() in card.to_name.lower() or
            (card.from_name and search_query.lower() in card.from_name.lower())
        ]
        def similarity(card):
            to_similarity = SequenceMatcher(None, search_query.lower(), card.to_name.lower()).ratio()
            from_similarity = SequenceMatcher(None, search_query.lower(), (card.from_name or "").lower()).ratio()
            return max(to_similarity, from_similarity)
        cards = sorted(filtered_cards, key=similarity, reverse=True)
    else:
        cards = sorted(cards, key=lambda c: c.created, reverse=True)

    # Only include cards with valid coordinates for the map
    map_cards = [
        {"id": c.id, "to_name": c.to_name, "location": c.location,
        "message": c.message, "lat": float(c.lat), "lng": float(c.lng)}
        for c in cards if c.lat is not None and c.lng is not None
    ]

    return render_template("index.html", cards=cards, search_query=search_query, map_cards=map_cards)

@app.route("/location", methods=["POST"])
def save_location():
    lat = float(request.form["lat"])
    lng = float(request.form["lng"])
    faculty_name = get_faculty_name(lat, lng)
    return f"Saved: {faculty_name}"

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":

        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if User.query.filter_by(username=username).first():
            flash("⚠️ Username already exists!", "danger")
            return redirect(url_for("register"))

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash("✅ Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    
    return render_template("login.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        admin_check = request.form.get("admin_check")
        passcode = request.form.get("passcode")

        user = User.query.filter_by(username=username).first()

        if user and user.password and check_password_hash(user.password, password):

            # admin access
            if user and user.password and check_password_hash(user.password, password):
                session["user_id"] = user.id
                session["username"] = user.username

            # temporary admin access ONLY if checkbox ticked and passcode correct
            if admin_check == "yes" and passcode == "1234":
                session["is_admin_temp"] = True
                flash("✅ Admin access granted for this session!", "success")
            else:
                session["is_admin_temp"] = False

            # login session
            session["user_id"] = user.id
            session["username"] = user.username
            flash("✅ Login successful!", "success")
            return redirect(url_for("profile"))
        else:
            flash("❌ Invalid username or password", "danger")
            return redirect(url_for("login"))
        
    return render_template("login.html")

@app.route("/forgot", methods=["POST"])
def forgot():
    email = request.form.get("email")
    user = User.query.filter_by(email=email).first()

    if not user:
        flash("❌ No account with that email.", "danger")
        return redirect(url_for("login"))

    token = s.dumps(email, salt="reset-token")
    reset_url = url_for("reset_token", token=token, _external=True)

    # Send email
    msg = Message("Password Reset Request",
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[email])
    msg.body = f"Click the link to reset your password: {reset_url}\nThis link expires in 1 hour."
    mail.send(msg)

    flash("📧 A password reset link has been sent to your email!", "info")
    return redirect(url_for("login"))

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_token(token):
    try:
        email = s.loads(token, salt="reset-token", max_age=3600)  # expires in 1 hour
    except (SignatureExpired, BadSignature):
        flash("❌ Reset link is invalid or expired.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        new_password = request.form.get("password")
        hashed_pw = generate_password_hash(new_password)

        user = User.query.filter_by(email=email).first()
        if user:
            user.password = hashed_pw
            db.session.commit()
            flash("✅ Your password has been reset! Please log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("❌ User not found.", "danger")
            return redirect(url_for("login"))

    return render_template("reset.html", token=token)
        
@app.route("/profile")
def profile():
    if "user_id" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("login"))
    
    user = User.query.get(session["user_id"])
    return render_template("profile-page.html", username=session.get("username"), user=user)

@app.route("/update_username", methods=["POST"])
def update_username():
    new_username = request.form.get("nickname")
    if not new_username or not new_username.strip():
        flash("❌ Username cannot be empty.", "danger")
        return redirect(url_for("profile"))

    user = User.query.get(session["user_id"])
    user.username = new_username
    db.session.commit()

    session["username"] = new_username
    flash("✅ Username updated!", "success")
    return redirect(url_for("profile"))

@app.route("/delete_profile", methods=["POST"])
def delete_profile():
    user = User.query.get(session["user_id"])
    if user:
        
        Card.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        session.clear()  
        flash("🗑️ Your profile and all your cards have been deleted.", "success")
        return redirect(url_for("index"))
    else:
        flash("❌ User not found.", "danger")
        return redirect(url_for("profile"))



@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/create", methods=["GET", "POST"])
def create():

    if "user_id" not in session:  
        flash("⚠️ You must be logged in to create a card!", "warning")
        return redirect(url_for("login"))

    pre_lat = request.args.get("lat")
    pre_lng = request.args.get("lng")

    if request.method == "POST":
        try:
            to_name = request.form.get("to_name")
            location = request.form.get("location")
            message = request.form.get("message")
            from_name = request.form.get("from_name") or "Anonymous"
            lat = request.form.get("lat")
            lng = request.form.get("lng")
            song = request.form.get("song")

            new_card = Card(
                to_name=to_name,
                location=location,
                message=message,
                user_id=session["user_id"],  
                song=song,
                lat=float(lat) if lat else None,
                lng=float(lng) if lng else None,
                status="pending"
            )

            db.session.add(new_card)
            db.session.flush()

            # Photos
            photos = request.files.getlist("photos")
            if photos and len(photos) > 6:
                flash("You can only upload up to 6 photos.", "warning")
                db.session.rollback()
                return redirect(request.url)
            for photo in photos:
                if photo and photo.filename and allowed_file(photo.filename, "image"):
                    filename = secure_filename(photo.filename)
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(save_path):
                        filename = f"{base}_{counter}{ext}"
                        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                        counter += 1
                    photo.save(save_path)
                    db_photo = Photo(card_id=new_card.id, file_path=f"uploads/{filename}")
                    db.session.add(db_photo)

            # Video
            video_file = request.files.get("video")
            if video_file and video_file.filename and allowed_file(video_file.filename, "video"):
                filename = secure_filename(video_file.filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(save_path):
                    filename = f"{base}_{counter}{ext}"
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    counter += 1
                video_file.save(save_path)
                new_card.video = f"uploads/{filename}"

            db.session.commit()
            flash("Story submitted successfully!", "success")
            return redirect(url_for("index"))

        except Exception as e:
            db.session.rollback()
            return f"Error: {e}"

    return render_template("create.html", pre_lat=pre_lat, pre_lng=pre_lng)

@app.route("/card/<int:card_id>")
def view_card(card_id):
    card = Card.query.get_or_404(card_id)
    return render_template("card_detail.html", card=card)

# Spotify search
@app.route("/search")
def search():
    query = request.args.get("q")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        "https://api.spotify.com/v1/search",
        headers=headers,
        params={"q": query, "type": "track", "limit": 5}
    )
    return jsonify(response.json())

@app.route("/contacts")
def contacts():
    return render_template("contacts.html")

# ---------------- Admin Routes ---------------- #
def serialize_card(card):
    return {
        "id": card.id,
        "to_name": card.to_name,
        "message": card.message,
        "lat": card.lat,
        "lng": card.lng,
        "location": card.location
    }

@app.route("/admin")
def admin_dashboard():
    
    user = User.query.get(session["user_id"])

    pending = Card.query.filter_by(status="pending").all()
    approved = Card.query.filter_by(status="approved").all()
    rejected = Card.query.filter_by(status="rejected").all()
    archived = Card.query.filter_by(status="archived").all()

    
    users = User.query.all()
    user_data = []
    for u in users:
        total_cards = Card.query.filter_by(user_id=u.id).count()  # safer than from_name
        user_data.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "total_cards": total_cards
        })


    return render_template("admin.html",
        pending=[serialize_card(c) for c in pending],
        approved=[serialize_card(c) for c in approved],
        rejected=[serialize_card(c) for c in rejected],
        archived=[serialize_card(c) for c in archived],
        user_data=user_data 
    )


@app.route("/admin/card/<int:card_id>/approve", methods=["POST"])
def approve_card(card_id):
    card = Card.query.get_or_404(card_id)
    card.status = "approved"
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/card/<int:card_id>/reject", methods=["POST"])
def reject_card(card_id):
    card = Card.query.get_or_404(card_id)
    card.status = "rejected"
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/card/<int:card_id>/archive", methods=["POST"])
def archive_card(card_id):
    card = Card.query.get_or_404(card_id)
    card.status = "archived"
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/delete/<int:card_id>", methods=["POST"])
def delete_card(card_id):
    card = Card.query.get_or_404(card_id)
    card.status = "archived"
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/edit/<int:card_id>", methods=["GET", "POST"])
def edit_card(card_id):
    card = Card.query.get_or_404(card_id)
    if request.method == "POST":
        card.to_name = request.form["to_name"]
        card.location = request.form["location"]
        card.message = request.form["message"]
        card.video = request.form["video"]
        card.from_name = request.form["from_name"]
        card.lat = request.form["lat"]
        card.lng = request.form["lng"]
        card.status = "approved"
        db.session.commit()
        return redirect(url_for("admin_dashboard"))
    return render_template("edit.html", card=card)

@app.route("/user/<int:user_id>")
def view_user_profile(user_id):
    current_user = User.query.get(session.get("user_id"))
    user = User.query.get_or_404(user_id)
    return render_template("profile-page.html", user=user, username=user.username)


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def admin_delete_user(user_id):

    user = User.query.get(user_id)
    if user:
       
        Card.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        flash(f"🗑️ User {user.username} and all their cards have been deleted.")
    else:
        flash("❌ User not found.", "danger")

    return redirect(url_for("admin_dashboard"))




@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    if user_id:
        user = User.query.get(user_id)
        return dict(current_user=user)
    return dict(current_user=None)

# ---------- Run ----------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
