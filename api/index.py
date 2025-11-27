from flask import Flask, jsonify, request
import json
import os
import polars as pl
from redis import Redis
from .bradley_terry import BradleyTerryModel

app = Flask(__name__, static_folder='../public')

suburbs = None
suburb_names = []
client = None

def _setup_database():
    global client
    client = Redis.from_url(os.environ.get('REDIS_URL'))

def _get_suburbs():
    # Use absolute path relative to this file's location
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "./api/suburbs.csv")
    suburbs = pl.read_csv(csv_path)
    suburbs = suburbs.with_columns(
        pl.col("center").map_elements(json.loads, return_dtype=pl.Object).alias("center")
    )
    return suburbs

def _ensure_initialized():
    global suburbs, suburb_names
    if suburbs is None or suburbs.height == 0:
        _setup_database()
        suburbs = _get_suburbs()
        suburb_names = suburbs['suburb'].to_list()

@app.route("/api")
def api_root():
    return jsonify({"status": "ok"})

@app.route("/get_suburb_pair")
@app.route("/api/get_suburb_pair")
def get_suburb_pair():
    pair = suburbs.sample(2)
    pair = pair.drop("shape").to_dicts()

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
    
    client.hincrby("votes", f"winner:{winner}:loser:{loser}", 1)
    return jsonify({"success": True, "winner": winner, "loser": loser})

@app.route("/get_shape/<suburb_name>")
@app.route("/api/get_shape/<suburb_name>")
def get_shape(suburb_name):
    suburb_name = suburb_name.replace("%20", " ")
    shape = suburbs.filter(pl.col("suburb") == suburb_name)["shape"]
    
    if shape is not None:
        try:
            geojson = json.loads(shape[0])
            geojson = geojson
            return geojson
        except Exception as e:
            return jsonify({"error": "Invalid GeoJSON", "details": str(e)}), 500
    else:
        return jsonify({"error": "Suburb not found"}), 404

@app.route("/api/votes")
def get_votes():
    if client is None:
        return jsonify({"error": "Redis client not initialized"}), 500
    
    # Check if cached strengths exist
    cached_strengths = client.get("cached_strengths")
    if cached_strengths:
        return jsonify(json.loads(cached_strengths))
    
    votes_data = client.hgetall("votes")
    votes = {k.decode('utf-8'): int(v) for k, v in votes_data.items()}
    match_records = []
    for key, count in votes.items():
        parts = key.split(":")
        winner = parts[1]
        loser = parts[3]
        for _ in range(count):
            match_records.append({"winner": winner, "loser": loser})
    matches_df = pl.DataFrame(match_records)
    model = BradleyTerryModel(matches_df)
    model.fit()
    strengths_df = model.get_strengths()
    strengths = strengths_df.to_dicts()
    
    # Cache the computed strengths
    client.set("cached_strengths", json.dumps(strengths), ex=3600)  # Cache for 1 hour
    
    return jsonify(strengths)

# Initialize on module load
_ensure_initialized()

@app.before_request
def before_request():
    _ensure_initialized()

# Export for Vercel
app = app
