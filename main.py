from flask import Flask, jsonify, request
import sqlite3
import random
import json
from create_suburbs_database import create_suburbs_database

app = Flask(__name__)

class Suburb:
    def __init__(self, name, center, shape):
        self.name = name
        self.center = center
        self.shape = shape
    
    def to_dict(self):
        print(self.center)
        return {
            "name": self.name,
            "center": self.center,
            "shape_url": f"/get_shape/{self.name}"
        }

def get_connection():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    return con, cur

suburbs = []

@app.route("/")
def index():
    return app.send_static_file('index.html')

@app.route("/get_suburb_pair")
def get_suburb_pair():
    pair = random.sample(suburbs, 2)
    pair = [suburb.to_dict() for suburb in pair]
    return jsonify(pair)

@app.route("/vote", methods=["POST"])
def vote():
    data = request.get_json()
    winner = data.get("winner")
    loser = data.get("loser")
    
    if not winner or not loser:
        return jsonify({"error": "Both winner and loser are required"}), 400
    
    if winner not in suburbs or loser not in suburbs:
        return jsonify({"error": "Invalid suburb"}), 400
    
    con, cur = get_connection()
    cur.execute("INSERT INTO votes (winner, loser) VALUES (?, ?)", (winner, loser))
    con.commit()
    con.close()
    return jsonify({"success": True, "winner": winner, "loser": loser})

@app.route("/get_shape/<suburb_name>")
def get_shape(suburb_name):
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
            print(row[0])
            print(e)
            return jsonify({"error": "Invalid GeoJSON", "details": str(e)}), 500
    else:
        return jsonify({"error": "Suburb not found"}), 404

def setup_database():
    con, cur = get_connection()
    cur.execute("CREATE TABLE IF NOT EXISTS votes (winner TEXT, loser TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    con.commit()
    
    # if subrubs table doesn't exist, create it
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='suburbs'")
    if not cur.fetchone():
        create_suburbs_database()
    
    con.close()

def get_suburbs():
    con, cur = get_connection()

    cur.execute("SELECT suburb, center, shape FROM suburbs")
    rows = cur.fetchall()
    con.close()
    return [Suburb(row[0], json.loads(row[1]), json.loads(row[2])) for row in rows]

if __name__ == "__main__":
    setup_database()
    suburbs = get_suburbs()
    app.run(debug=True, port=8000)