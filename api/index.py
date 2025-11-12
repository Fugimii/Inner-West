from flask import Flask, jsonify, request
import json
import os
import polars as pl
from redis import Redis

app = Flask(__name__, static_folder='../public')

suburbs = None
suburb_names = []
client = None

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

def setup_database():
    global client
    client = Redis.from_url(os.environ.get('REDIS_URL'))

def get_suburbs():
    # Use absolute path relative to this file's location
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "./api/suburbs.csv")
    suburbs = pl.read_csv(csv_path)
    suburbs = suburbs.with_columns(
        pl.col("center").map_elements(json.loads, return_dtype=pl.Object).alias("center")
    )
    return suburbs

def ensure_initialized():
    global suburbs, suburb_names
    if suburbs is None or suburbs.height == 0:
        setup_database()
        suburbs = get_suburbs()
        suburb_names = suburbs['suburb'].to_list()

@app.route("/api/votes")
def get_votes():
    if client is None:
        return jsonify({"error": "Redis client not initialized"}), 500
    
    try:
        # Get all vote data from the hash
        votes_data = client.hgetall("votes")
        
        votes = {k.decode('utf-8'): int(v) for k, v in votes_data.items()}
        
        # Aggregate votes by suburb (count wins for each suburb)
        suburb_wins = {}
        for key, count in votes.items():
            # Parse the key format: "winner:SuburbName:loser:OtherSuburb"
            parts = key.split(":")
            if len(parts) >= 2:
                winner = parts[1]
                suburb_wins[winner] = suburb_wins.get(winner, 0) + count
        
        # Sort suburbs by number of wins
        sorted_suburbs = sorted(suburb_wins.items(), key=lambda x: x[1], reverse=True)[:50]
        top_suburbs = [{"suburb": suburb, "wins": wins} for suburb, wins in sorted_suburbs]
        
        total_votes = sum(votes.values())
        
        return jsonify({
            "total_votes": total_votes,
            "total_matchups": len(votes),
            "top_50_suburbs": top_suburbs
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Initialize on module load
ensure_initialized()

@app.before_request
def before_request():
    ensure_initialized()

# Export for Vercel
app = app
