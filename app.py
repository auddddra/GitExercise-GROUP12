from flask import Flask, render_template, request, redirect, url_for
from flask_scss import Scss

pins = []

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", pins=pins)

@app.route("/contacts")
def contacts():
    return render_template("contacts.html")

@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/message", methods=["GET", "POST"])
def message():
    if request.method == "POST":
        place_name = request.form.get("place_name")
        message = request.form.get("message")
        lat = request.form.get("lat")
        lng = request.form.get("lng")
        return f"Message for {place_name} at ({lat}, {lng}): {message}"
    else:
        lat = request.args.get("lat")
        lng = request.args.get("lng")
        return render_template("message.html", lat=lat, lng=lng)

@app.route("/save_message", methods=["POST"])
def save_message():
    place_name = request.form.get("place_name")
    message = request.form.get("message")
    lat = request.form.get("lat")
    lng = request.form.get("lng")
    pins.append({
        "place_name": place_name,
        "message": message,
        "lat": lat,
        "lng": lng
    })
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)