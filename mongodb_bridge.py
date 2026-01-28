#!/usr/bin/env python3
"""
Secure MongoDB HTTP Bridge
==========================
A secure REST API that provides full MongoDB access over HTTP.
Run this on your server to allow Claude to query your database.

Requirements:
    pip install flask pymongo

Usage:
    1. Set environment variables:
       export MONGO_URI="mongodb://localhost:27017"
       export API_KEY="your-secret-key-here"
    
    2. Run the server:
       python3 mongodb_bridge.py
    
    3. For production with HTTPS (recommended):
       Use nginx as reverse proxy with SSL, or:
       pip install pyopenssl
       python3 mongodb_bridge.py --ssl

Security:
    - All requests require X-API-Key header
    - Generates a random API key if not set
    - Supports HTTPS for encrypted connections
"""

import os
import sys
import json
import secrets
import argparse
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId, json_util
from bson.errors import InvalidId

app = Flask(__name__)

# Configuration
MONGO_URI = os.environ.get("MONGO_URI", None)
API_KEY = os.environ.get("API_KEY", None)

# Interactive configuration if MONGO_URI not set
if not MONGO_URI:
    print("\n" + "="*60)
    print("MongoDB Connection Setup")
    print("="*60)
    
    mongo_host = input("MongoDB host [localhost]: ").strip() or "localhost"
    mongo_port = input("MongoDB port [27017]: ").strip() or "27017"
    mongo_user = input("MongoDB username (leave empty if none): ").strip()
    mongo_pass = ""
    if mongo_user:
        mongo_pass = input("MongoDB password: ").strip()
    mongo_db = input("Authentication database (leave empty for default): ").strip()
    
    if mongo_user and mongo_pass:
        if mongo_db:
            MONGO_URI = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/{mongo_db}"
        else:
            MONGO_URI = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}"
    else:
        MONGO_URI = f"mongodb://{mongo_host}:{mongo_port}"
    
    print(f"\nUsing MongoDB URI: {MONGO_URI.replace(mongo_pass, '****') if mongo_pass else MONGO_URI}")
    print("="*60 + "\n")

# Generate a random API key if not provided
if not API_KEY:
    API_KEY = secrets.token_urlsafe(32)
    print(f"\n{'='*60}")
    print("WARNING: No API_KEY environment variable set!")
    print(f"Generated temporary API key:\n")
    print(f"   {API_KEY}")
    print(f"\nSet this in your environment for persistence:")
    print(f"   export API_KEY=\"{API_KEY}\"")
    print(f"{'='*60}\n")

# MongoDB client (lazy connection)
_client = None

def get_client():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client


def parse_json_extended(data):
    """Parse JSON with MongoDB extended JSON support."""
    return json_util.loads(json.dumps(data))


def serialize_response(data):
    """Serialize MongoDB response to JSON-safe format."""
    return json.loads(json_util.dumps(data))


def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        provided_key = request.headers.get("X-API-Key")
        if not provided_key or provided_key != API_KEY:
            return jsonify({"error": "Unauthorized - Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/", methods=["GET"])
def index():
    """Health check endpoint."""
    return jsonify({
        "service": "MongoDB HTTP Bridge",
        "status": "running",
        "auth_required": True,
        "endpoints": [
            "GET  /databases",
            "GET  /databases/<db>/collections",
            "POST /query",
            "POST /aggregate",
            "POST /insert",
            "POST /update",
            "POST /delete",
            "POST /command",
            "GET  /collection/<db>/<collection>/count",
            "GET  /collection/<db>/<collection>/indexes"
        ]
    })


@app.route("/databases", methods=["GET"])
@require_api_key
def list_databases():
    """List all databases."""
    try:
        client = get_client()
        databases = []
        for db_info in client.list_databases():
            databases.append({
                "name": db_info["name"],
                "sizeOnDisk": db_info.get("sizeOnDisk"),
                "empty": db_info.get("empty", False)
            })
        return jsonify({"databases": databases})
    except PyMongoError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/databases/<db>/collections", methods=["GET"])
@require_api_key
def list_collections(db):
    """List all collections in a database."""
    try:
        client = get_client()
        database = client[db]
        collections = database.list_collection_names()
        
        # Get collection stats
        collection_info = []
        for coll_name in collections:
            try:
                stats = database.command("collStats", coll_name)
                collection_info.append({
                    "name": coll_name,
                    "count": stats.get("count", 0),
                    "size": stats.get("size", 0),
                    "avgObjSize": stats.get("avgObjSize", 0)
                })
            except:
                collection_info.append({"name": coll_name})
        
        return jsonify({"database": db, "collections": collection_info})
    except PyMongoError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/query", methods=["POST"])
@require_api_key
def query():
    """
    Execute a find query.
    
    Request body:
    {
        "database": "mydb",
        "collection": "mycollection",
        "filter": {"field": "value"},      // optional, default {}
        "projection": {"field": 1},         // optional
        "sort": [["field", 1]],            // optional, 1=asc, -1=desc
        "limit": 100,                       // optional, default 100
        "skip": 0                           // optional
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        db_name = data.get("database")
        coll_name = data.get("collection")
        
        if not db_name or not coll_name:
            return jsonify({"error": "database and collection are required"}), 400
        
        client = get_client()
        collection = client[db_name][coll_name]
        
        # Parse query parameters
        filter_query = parse_json_extended(data.get("filter", {}))
        projection = data.get("projection")
        sort = data.get("sort")
        limit = data.get("limit", 100)
        skip = data.get("skip", 0)
        
        # Build cursor
        cursor = collection.find(filter_query, projection)
        
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        
        # Execute and serialize
        documents = list(cursor)
        
        return jsonify({
            "database": db_name,
            "collection": coll_name,
            "count": len(documents),
            "documents": serialize_response(documents)
        })
    except PyMongoError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Query error: {str(e)}"}), 400


@app.route("/aggregate", methods=["POST"])
@require_api_key
def aggregate():
    """
    Execute an aggregation pipeline.
    
    Request body:
    {
        "database": "mydb",
        "collection": "mycollection",
        "pipeline": [
            {"$match": {"status": "active"}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        db_name = data.get("database")
        coll_name = data.get("collection")
        pipeline = data.get("pipeline", [])
        
        if not db_name or not coll_name:
            return jsonify({"error": "database and collection are required"}), 400
        
        client = get_client()
        collection = client[db_name][coll_name]
        
        # Parse pipeline with extended JSON
        pipeline = parse_json_extended(pipeline)
        
        # Execute aggregation
        results = list(collection.aggregate(pipeline))
        
        return jsonify({
            "database": db_name,
            "collection": coll_name,
            "count": len(results),
            "results": serialize_response(results)
        })
    except PyMongoError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Aggregation error: {str(e)}"}), 400


@app.route("/insert", methods=["POST"])
@require_api_key
def insert():
    """
    Insert documents.
    
    Request body:
    {
        "database": "mydb",
        "collection": "mycollection",
        "documents": [{"field": "value"}, ...],  // or single document
        "ordered": true  // optional
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        db_name = data.get("database")
        coll_name = data.get("collection")
        documents = data.get("documents")
        ordered = data.get("ordered", True)
        
        if not db_name or not coll_name or not documents:
            return jsonify({"error": "database, collection, and documents are required"}), 400
        
        client = get_client()
        collection = client[db_name][coll_name]
        
        # Handle single document or list
        if isinstance(documents, dict):
            documents = [documents]
        
        documents = parse_json_extended(documents)
        
        result = collection.insert_many(documents, ordered=ordered)
        
        return jsonify({
            "database": db_name,
            "collection": coll_name,
            "inserted_count": len(result.inserted_ids),
            "inserted_ids": serialize_response(result.inserted_ids)
        })
    except PyMongoError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Insert error: {str(e)}"}), 400


@app.route("/update", methods=["POST"])
@require_api_key
def update():
    """
    Update documents.
    
    Request body:
    {
        "database": "mydb",
        "collection": "mycollection",
        "filter": {"field": "value"},
        "update": {"$set": {"field": "new_value"}},
        "many": false,  // optional, default false (update one)
        "upsert": false // optional
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        db_name = data.get("database")
        coll_name = data.get("collection")
        filter_query = data.get("filter", {})
        update_doc = data.get("update")
        many = data.get("many", False)
        upsert = data.get("upsert", False)
        
        if not db_name or not coll_name or not update_doc:
            return jsonify({"error": "database, collection, and update are required"}), 400
        
        client = get_client()
        collection = client[db_name][coll_name]
        
        filter_query = parse_json_extended(filter_query)
        update_doc = parse_json_extended(update_doc)
        
        if many:
            result = collection.update_many(filter_query, update_doc, upsert=upsert)
        else:
            result = collection.update_one(filter_query, update_doc, upsert=upsert)
        
        return jsonify({
            "database": db_name,
            "collection": coll_name,
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": serialize_response(result.upserted_id) if result.upserted_id else None
        })
    except PyMongoError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Update error: {str(e)}"}), 400


@app.route("/delete", methods=["POST"])
@require_api_key
def delete():
    """
    Delete documents.
    
    Request body:
    {
        "database": "mydb",
        "collection": "mycollection",
        "filter": {"field": "value"},
        "many": false  // optional, default false (delete one)
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        db_name = data.get("database")
        coll_name = data.get("collection")
        filter_query = data.get("filter", {})
        many = data.get("many", False)
        
        if not db_name or not coll_name:
            return jsonify({"error": "database and collection are required"}), 400
        
        client = get_client()
        collection = client[db_name][coll_name]
        
        filter_query = parse_json_extended(filter_query)
        
        if many:
            result = collection.delete_many(filter_query)
        else:
            result = collection.delete_one(filter_query)
        
        return jsonify({
            "database": db_name,
            "collection": coll_name,
            "deleted_count": result.deleted_count
        })
    except PyMongoError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Delete error: {str(e)}"}), 400


@app.route("/command", methods=["POST"])
@require_api_key
def run_command():
    """
    Run a raw MongoDB command.
    
    Request body:
    {
        "database": "mydb",
        "command": {"ping": 1}
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        db_name = data.get("database", "admin")
        command = data.get("command")
        
        if not command:
            return jsonify({"error": "command is required"}), 400
        
        client = get_client()
        database = client[db_name]
        
        command = parse_json_extended(command)
        result = database.command(command)
        
        return jsonify({
            "database": db_name,
            "result": serialize_response(result)
        })
    except PyMongoError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Command error: {str(e)}"}), 400


@app.route("/collection/<db>/<collection>/count", methods=["GET"])
@require_api_key
def count_documents(db, collection):
    """Get document count for a collection."""
    try:
        client = get_client()
        coll = client[db][collection]
        count = coll.estimated_document_count()
        return jsonify({
            "database": db,
            "collection": collection,
            "count": count
        })
    except PyMongoError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/collection/<db>/<collection>/indexes", methods=["GET"])
@require_api_key
def list_indexes(db, collection):
    """List indexes for a collection."""
    try:
        client = get_client()
        coll = client[db][collection]
        indexes = list(coll.list_indexes())
        return jsonify({
            "database": db,
            "collection": collection,
            "indexes": serialize_response(indexes)
        })
    except PyMongoError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sample", methods=["POST"])
@require_api_key  
def sample():
    """
    Get a random sample of documents (useful for exploring data).
    
    Request body:
    {
        "database": "mydb",
        "collection": "mycollection",
        "size": 5  // optional, default 5
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        db_name = data.get("database")
        coll_name = data.get("collection")
        size = data.get("size", 5)
        
        if not db_name or not coll_name:
            return jsonify({"error": "database and collection are required"}), 400
        
        client = get_client()
        collection = client[db_name][coll_name]
        
        # Use $sample aggregation
        pipeline = [{"$sample": {"size": size}}]
        results = list(collection.aggregate(pipeline))
        
        return jsonify({
            "database": db_name,
            "collection": coll_name,
            "count": len(results),
            "documents": serialize_response(results)
        })
    except PyMongoError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Sample error: {str(e)}"}), 400


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MongoDB HTTP Bridge")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=80, help="Port to listen on")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS (requires pyopenssl)")
    parser.add_argument("--cert", default="cert.pem", help="SSL certificate file")
    parser.add_argument("--key", default="key.pem", help="SSL key file")
    args = parser.parse_args()
    
    print(f"\nMongoDB URI: {MONGO_URI}")
    print(f"Starting server on {args.host}:{args.port}")
    print(f"SSL: {'Enabled' if args.ssl else 'Disabled'}")
    print(f"\nTest connection:")
    print(f"   curl -H 'X-API-Key: {API_KEY}' http://{'localhost' if args.host == '0.0.0.0' else args.host}:{args.port}/databases\n")
    
    ssl_context = None
    if args.ssl:
        try:
            ssl_context = (args.cert, args.key)
            print(f"   Using SSL cert: {args.cert}, key: {args.key}")
        except Exception as e:
            print(f"WARNING: SSL setup failed: {e}")
            print("   Generate self-signed cert: openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes")
            sys.exit(1)
    
    app.run(host=args.host, port=args.port, ssl_context=ssl_context, threaded=True)
