from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

# ---------- Config ----------
UPLOAD_FOLDER = "static/uploads"
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_VIDEO_EXT = {"mp4", "webm", "ogg", "mov"}

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pins.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

my_secret_key = "i love horses"

db = SQLAlchemy(app)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)




# ---------------- Models ---------------- #

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    to_name = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    photos = db.relationship("Photo", backref="card", lazy=True)
    video = db.Column(db.String(200), nullable=True)  # stores "uploads/filename.ext"
    from_name = db.Column(db.String(50), nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("card.id"), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)  # stores "uploads/filename.ext"



# ---------------- Routes ---------------- #
@app.route("/")
def index():
    cards = Card.query.order_by(Card.created.desc()).all()
    return render_template("index.html", cards=cards)


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

            new_card = Card(
                to_name=to_name,
                location=location,
                message=message,
                from_name=from_name,
                lat=float(lat) if lat else None,
                lng=float(lng) if lng else None
            )
            db.session.add(new_card)
            db.session.flush() 

            photos = request.files.getlist("photos")
            if photos and len(photos) > 6:
                flash("You can only upload up to 6 photos.", "warning")
                db.session.rollback()
                return redirect(request.url)

            for photo in photos:
                if photo and photo.filename:
                    if not allowed_file(photo.filename, kind="image"):
                        continue
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

            video_file = request.files.get("video")
            if video_file and video_file.filename:
                if allowed_file(video_file.filename, kind="video"):
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


@app.route("/api/cards", methods=["GET"])
def api_cards():
    cards = Card.query.filter(Card.lat.isnot(None), Card.lng.isnot(None)).all()
    out = []
    for c in cards:
        first_photo = c.photos[0].file_path if c.photos else None
        attachments = len(c.photos) + (1 if c.video else 0)
        out.append({
            "id": c.id,
            "to_name": c.to_name,
            "location": c.location,
            "message": c.message,
            "lat": c.lat,
            "lng": c.lng,
            "first_photo": first_photo,
            "attachments": attachments
        })
    return jsonify(out)

@app.route("/api/card/<int:card_id>")
def api_card(card_id):
    c = Card.query.get_or_404(card_id)
    photos = [p.file_path for p in c.photos]
    return jsonify({
        "id": c.id,
        "to_name": c.to_name,
        "location": c.location,
        "message": c.message,
        "photos": photos,
        "video": c.video,
        "from_name": c.from_name
    })


# ---------- Run ----------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)