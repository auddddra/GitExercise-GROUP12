from flask import Flask, render_template, request, redirect, url_for, jsonify
import uuid
import requests
from dotenv import load_dotenv
import os

# Setup
app = Flask(__name__)
hearts = {}

# Load .env
load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# ---------------- Spotify Helpers ---------------- #
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

# ---------------- Routes ---------------- #
@app.route("/")
def index():
    return render_template("index.html", hearts=hearts)

@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        heart_id = str(uuid.uuid4())
        hearts[heart_id] = {
            "title": request.form["title"],
            "message": request.form["message"],
            "song": request.form["song"],
            "from_name": request.form.get("from"),
            "photo": request.files.get("photo"),
            "video": request.files.get("video"),
        }
        return redirect(url_for("view", heart_id=heart_id))
    return render_template("create.html")

@app.route("/view/<heart_id>")
def view(heart_id):
    heart = hearts.get(heart_id)
    if not heart:
        return "Heart not found", 404
    return render_template("view.html", **heart)

@app.route("/contacts")
def contacts():
    return render_template("contacts.html")

@app.route("/token")
def token():
    return jsonify({"token": get_token()})

@app.route("/search")
def search():
    query = request.args.get("q")  # ?q=songname
    token = get_token()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    search_url = "https://api.spotify.com/v1/search"
    response = requests.get(
        search_url,
        headers=headers,
        params={
            "q": query,
            "type": "track",
            "limit": 5
        }
    )

    return jsonify(response.json())

# ---------------- Run App ---------------- #
if __name__ == "__main__":
    app.run(debug=True)

