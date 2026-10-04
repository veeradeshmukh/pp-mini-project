"""
app.py - the Flask web server.

Run it:   python app.py      then open  http://127.0.0.1:5000

Flow of the whole project:
  browser (HTML/JS)  --fetch()-->  Flask routes below  -->  database.py  -->  mandals.db
"""
import os
import uuid

from flask import Flask, jsonify, render_template, request

import database as db

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # reject uploads over 5 MB

UPLOAD_DIR = os.path.join(app.static_folder, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# The map is limited to South Mumbai. The SAME box is used to (a) lock the
# map in the browser and (b) reject pins placed outside it on the server.
BOUNDS = {"south": 18.89, "west": 72.79, "north": 19.02, "east": 72.88}

AREAS = ["Colaba", "Fort", "Girgaon", "Khetwadi", "Dongri", "Mazgaon",
         "Kalachowki", "Chinchpokli", "Lalbaug", "Parel", "Worli", "Other"]


# ---------------------------------------------------------------- helpers
def clean(text, max_len):
    """Trim whitespace and cap length. (HTML is escaped again in the browser.)"""
    return (text or "").strip()[:max_len]


def rating(value):
    """Return an int 1-5, or None if the value is not valid."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 5 else None


def image_extension(data):
    """Check the first bytes of the file ('magic numbers') instead of trusting
    the file name. Returns 'jpg' / 'png' / 'webp' or None."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def error(message, status=400):
    return jsonify({"error": message}), status


# ------------------------------------------------------------------ pages
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/contribute")
def contribute():
    return render_template("contribute.html")


# -------------------------------------------------------------------- API
@app.route("/api/config")
def config():
    return jsonify({"bounds": BOUNDS, "areas": AREAS})


@app.route("/api/mandals", methods=["GET"])
def list_mandals():
    return jsonify(db.get_all_mandals())


@app.route("/api/mandals/<int:mandal_id>", methods=["GET"])
def mandal_detail(mandal_id):
    mandal = db.get_mandal(mandal_id)
    if mandal is None:
        return error("Mandal not found", 404)
    return jsonify(mandal)


@app.route("/api/mandals", methods=["POST"])
def create_mandal():
    data = request.get_json(silent=True) or {}
    name = clean(data.get("name"), 80)
    area = clean(data.get("area"), 40)
    if len(name) < 3:
        return error("Please enter the mandal's name (at least 3 characters).")
    if not area:
        return error("Please choose an area.")

    try:
        lat, lng = float(data.get("lat")), float(data.get("lng"))
    except (TypeError, ValueError):
        return error("Please click the map to place the pin.")
    if not (BOUNDS["south"] <= lat <= BOUNDS["north"] and BOUNDS["west"] <= lng <= BOUNDS["east"]):
        return error("That pin is outside the South Mumbai map area.")

    year = data.get("established_year")
    if year in ("", None):
        year = None
    else:
        try:
            year = int(year)
        except ValueError:
            return error("Established year must be a number.")
        if not 1892 <= year <= 2026:  # first public Ganeshotsav was 1893
            return error("Established year should be between 1892 and 2026.")

    new_id = db.add_mandal(
        name, area, lat, lng,
        description=clean(data.get("description"), 400),
        station=clean(data.get("nearest_station"), 60),
        year=year,
    )
    if new_id is None:
        return error("A mandal with this name already exists.", 409)
    return jsonify({"id": new_id}), 201


@app.route("/api/mandals/<int:mandal_id>/reviews", methods=["POST"])
def create_review(mandal_id):
    if not db.mandal_exists(mandal_id):
        return error("Mandal not found", 404)
    data = request.get_json(silent=True) or {}
    overall, crowd, parking = (rating(data.get(k)) for k in ("overall", "crowd", "parking"))
    if None in (overall, crowd, parking):
        return error("Overall, crowd and parking ratings must each be 1 to 5.")
    db.add_review(
        mandal_id,
        clean(data.get("reviewer"), 40) or "Anonymous",
        overall, crowd, parking,
        clean(data.get("comment"), 500),
    )
    return jsonify({"ok": True}), 201


@app.route("/api/mandals/<int:mandal_id>/photos", methods=["POST"])
def upload_photo(mandal_id):
    if not db.mandal_exists(mandal_id):
        return error("Mandal not found", 404)
    file = request.files.get("photo")
    if file is None or file.filename == "":
        return error("Please choose a photo.")
    data = file.read()
    ext = image_extension(data)
    if ext is None:
        return error("Only JPG, PNG or WEBP images are allowed.")
    # Random file name: avoids clashes and never uses the user's file name.
    filename = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        f.write(data)
    db.add_photo(mandal_id, filename, clean(request.form.get("uploader"), 40) or "Anonymous")
    return jsonify({"ok": True, "filename": filename}), 201


@app.errorhandler(413)
def too_large(_):
    return error("That file is too large (max 5 MB).", 413)


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)
