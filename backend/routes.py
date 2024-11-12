from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"

print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# REST API Endpoints
######################################################################

# 1. Health Check
@app.route("/health", methods=["GET"])
def healthz():
    return jsonify(dict(status="OK")), 200

# 2. Count of Songs
@app.route("/count", methods=["GET"])
def count():
    """Return the count of songs in the database."""
    count = db.songs.count_documents({})
    return {"count": count}, 200

# 3. List All Songs
@app.route("/song", methods=["GET"])
def songs():
    """List all songs from the database."""
    results = list(db.songs.find({}))
    return {"songs": parse_json(results)}, 200

# 4. Read a Single Song by ID
@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """Get a song by its ID."""
    song = db.songs.find_one({"id": id})
    if not song:
        return {"message": f"song with id {id} not found"}, 404
    return parse_json(song), 200

# 5. Create a New Song
@app.route("/song", methods=["POST"])
def create_song():
    """Create a new song."""
    song_in = request.json
    song = db.songs.find_one({"id": song_in["id"]})
    if song:
        return {"Message": f"song with id {song_in['id']} already present"}, 302
    insert_id: InsertOneResult = db.songs.insert_one(song_in)
    return {"inserted id": str(insert_id.inserted_id)}, 201

# 6. Update an Existing Song
@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """Update an existing song."""
    song_in = request.json
    song = db.songs.find_one({"id": id})
    if song == None:
        return {"message": "song not found"}, 404
    updated_data = {"$set": song_in}
    result = db.songs.update_one({"id": id}, updated_data)
    if result.modified_count == 0:
        return {"message": "song found, but nothing updated"}, 200
    return parse_json(db.songs.find_one({"id": id})), 201

# 7. Delete a Song
@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """Delete a song."""
    result = db.songs.delete_one({"id": id})
    if result.deleted_count == 0:
        return {"message": "song not found"}, 404
    return "", 204
