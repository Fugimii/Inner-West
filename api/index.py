from flask import Flask, jsonify, request
import sqlite3
import random
import json
import os
import shutil

app = Flask(__name__, static_folder='../public')

suburbs = []
suburb_names = []

class Suburb:
    def __init__(self, name, center, shape):
        self.name = name
        self.center = center
        self.shape = shape
    
    def to_dict(self):
        return {
            "name": self.name,
            "center": self.center,
            "shape_url": f"/api/get_shape/{self.name}"
        }

def get_connection():
    db_path = "/tmp/database.db"
    # Copy the pre-built database if it doesn't exist in /tmp
    if not os.path.exists(db_path):
        source_db = os.path.join(os.path.dirname(__file__), '..', 'database.db')
        if os.path.exists(source_db):
            shutil.copy(source_db, db_path)
    
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    return con, cur


@app.route("/")
@app.route("/api")
@app.route("/api/")
def api_root():
    return jsonify({"status": "ok", "message": "Inner West API"})

@app.route("/get_suburb_pair")
@app.route("/api/get_suburb_pair")
def get_suburb_pair():
    pair = random.sample(suburbs, 2)
    pair = [suburb.to_dict() for suburb in pair]
    return jsonify(pair)

@app.route("/vote", methods=["POST"])
@app.route("/api/vote", methods=["POST"])
def vote():
    data = request.get_json()
    winner = data.get("winner")
    loser = data.get("loser")
    
    if not winner or not loser:
        return jsonify({"error": "Both winner and loser are required"}), 400
    
    if winner not in suburb_names or loser not in suburb_names:
        return jsonify({"error": "Invalid suburb"}), 400
    
    con, cur = get_connection()
    cur.execute("INSERT INTO votes (winner, loser) VALUES (?, ?)", (winner, loser))
    con.commit()
    con.close()
    return jsonify({"success": True, "winner": winner, "loser": loser})

@app.route("/get_shape/<suburb_name>")
@app.route("/api/get_shape/<suburb_name>")
def get_shape(suburb_name):
    suburb_name = suburb_name.replace("%20", " ")
    con, cur = get_connection()
    cur.execute("SELECT shape FROM suburbs WHERE suburb = ?", (suburb_name,))
    row = cur.fetchone()
    con.close()
    
    if row:
        # Parse the string to a Python dict, then jsonify
        try:
            geojson = json.loads(row[0])
            return geojson
        except Exception as e:
            return jsonify({"error": "Invalid GeoJSON", "details": str(e)}), 500
    else:
        return jsonify({"error": "Suburb not found"}), 404

def setup_database():
    con, cur = get_connection()
    cur.execute("CREATE TABLE IF NOT EXISTS votes (winner TEXT, loser TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    con.commit()
    con.close()

def get_suburbs():
    con, cur = get_connection()
    cur.execute("SELECT suburb, center, shape FROM suburbs")
    rows = cur.fetchall()
    con.close()
    return [Suburb(row[0], json.loads(row[1]), json.loads(row[2])) for row in rows]

def ensure_initialized():
    global suburbs, suburb_names
    if not suburbs:
        setup_database()
        suburbs = get_suburbs()
        suburb_names = [suburb.name for suburb in suburbs]

# Initialize on module load
ensure_initialized()

@app.before_request
def before_request():
    ensure_initialized()

# Export for Vercel
app = app
