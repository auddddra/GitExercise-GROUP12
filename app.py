from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from difflib import SequenceMatcher
import os
import requests
from dotenv import load_dotenv

# ---------- Config ----------
UPLOAD_FOLDER = "static/uploads"
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_VIDEO_EXT = {"mp4", "webm", "ogg", "mov"}

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pins.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = "i love horses"

db = SQLAlchemy(app)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
    from_name = db.Column(db.String(50), nullable=True)
    song = db.Column(db.Text, nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected, archived

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("card.id"), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)

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


@app.route("/create", methods=["GET", "POST"])
def create():
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
                from_name=from_name,
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
    pending = Card.query.filter_by(status="pending").all()
    approved = Card.query.filter_by(status="approved").all()
    rejected = Card.query.filter_by(status="rejected").all()
    archived = Card.query.filter_by(status="archived").all()

    return render_template(
        "admin.html",
        pending=[serialize_card(c) for c in pending],
        approved=[serialize_card(c) for c in approved],
        rejected=[serialize_card(c) for c in rejected],
        archived=[serialize_card(c) for c in archived]
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
        flash("Card updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("edit.html", card=card)

# ---------- Run ----------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)





