from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import requests
from dotenv import load_dotenv
import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pins.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



app.secret_key = "i love horses"


# ---------------- Models ---------------- #

class Pin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    label = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Pin {self.label}>"

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    to_name = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    # song = db.Column(db.String(200), nullable=False)   
    photo = db.Column(db.String(200), nullable=True)   
    video = db.Column(db.String(200), nullable=True)   
    from_name = db.Column(db.String(50), nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)



# ---------------- Routes ---------------- #
@app.route("/")
def index():
    cards = Card.query.order_by(Card.created.desc()).all()
    return render_template("index.html", cards=cards)

@app.route('/api/pins', methods=['GET'])
def get_pins():
    pins = Pin.query.all()
    return jsonify([{"id": p.id, "lat": p.lat, "lng": p.lng, "label": p.label} for p in pins])

@app.route('/api/pins', methods=['POST'])
def add_pin():
    data = request.get_json()
    new_pin = Pin(lat=data['lat'], lng=data['lng'], label=data['label'])
    db.session.add(new_pin)
    db.session.commit()
    return jsonify({"message": "Pin added successfully!"}), 201


UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/create", methods=["POST", "GET"])
def create():
    if request.method == "POST":
        try:
            to_name = request.form.get("to_name")
            location = request.form.get("location")
            message = request.form.get("message")
            # song = request.form.get("song")
            from_name = request.form.get("from_name") or "Anonymous"

            
            photo_file = request.files.get("photo_file")
            video_file = request.files.get("video_file")

            photo_path, video_path = None, None
            if photo_file and photo_file.filename:
                filename = secure_filename(photo_file.filename)
                photo_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                photo_file.save(photo_path)

            if video_file and video_file.filename:
                filename = secure_filename(video_file.filename)
                video_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                video_file.save(video_path)

    
            new_card = Card(
                to_name=to_name,
                location=location,
                message=message,
                # song=song,
                photo=photo_path,
                video=video_path,
                from_name=from_name
            )
            db.session.add(new_card)
            db.session.commit()

            flash("Story submitted successfully!", "success")
            return redirect(url_for("index"))

        except Exception as e:
            return f"Error: {e}"

    return render_template("create.html")



@app.route("/contacts")
def contacts():
    return render_template("contacts.html")


# ---------------- Run ---------------- #
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)