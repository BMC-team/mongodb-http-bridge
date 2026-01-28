# MongoDB HTTP Bridge

A secure REST API bridge for accessing MongoDB over HTTP. Designed to enable remote database access when direct MongoDB connections are not possible (firewalls, proxies, etc.).

Supports MongoDB sharded clusters with automatic handling of unavailable shards.

## Features

- API Key Authentication - All requests require authentication
- HTTPS Support - Optional SSL/TLS encryption
- Full MongoDB Access - Query, aggregate, insert, update, delete
- Shard-Aware - Query online shards even when others are unavailable
- Direct Shard Access - Bypass mongos and query specific shards directly
- Interactive Setup - Prompts for MongoDB connection settings
- Zero Configuration - Auto-generates API key if not set
- Single File - No complex setup required

## Quick Install

### One-Line Install
```bash
curl -fsSL https://raw.githubusercontent.com/BMC-team/mongodb-http-bridge/main/mongodb_bridge.py -o mongodb_bridge.py && pip install flask pymongo && sudo python3 mongodb_bridge.py
```

### Step by Step
```bash
# 1. Download
curl -O https://raw.githubusercontent.com/BMC-team/mongodb-http-bridge/main/mongodb_bridge.py

# 2. Install dependencies
pip install flask pymongo

# 3. Run (will prompt for MongoDB settings and auto-generate API key)
sudo python3 mongodb_bridge.py --port 80
```

### With Virtual Environment (Recommended for newer Python)
```bash
# Create and activate virtual environment
python3 -m venv mongodb-bridge-env
source mongodb-bridge-env/bin/activate

# Install dependencies
pip install flask pymongo

# Run
sudo mongodb-bridge-env/bin/python mongodb_bridge.py --port 443
```

## Interactive Setup

When you run the script without environment variables, it will ask for your MongoDB connection settings:

```
============================================================
MongoDB Connection Setup
============================================================
MongoDB host [localhost]: localhost
MongoDB port [27017]: 27020
MongoDB username (leave empty if none): admin
MongoDB password: ****
Authentication database (leave empty for default): admin

Using MongoDB URI: mongodb://admin:****@localhost:27020/admin
============================================================
```

## Configuration

### Environment Variables (Skip Interactive Prompts)
```bash
export MONGO_URI="mongodb://admin:password@localhost:27020/?authSource=admin"
export API_KEY="your-strong-api-key-here"
```

### Command Line Options
```bash
python3 mongodb_bridge.py --help

Options:
  --host    Host to bind to (default: 0.0.0.0)
  --port    Port to listen on (default: 80)
  --ssl     Enable HTTPS
  --cert    SSL certificate file (default: cert.pem)
  --key     SSL key file (default: key.pem)
```

### Run with HTTPS
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Run with SSL
sudo python3 mongodb_bridge.py --port 443 --ssl
```

### Run in Background
```bash
export MONGO_URI="mongodb://admin:password@localhost:27020/?authSource=admin"
export API_KEY="your-strong-api-key"
nohup sudo -E python3 mongodb_bridge.py --port 443 > bridge.log 2>&1 &
```

## API Endpoints

### General Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Health check (no auth required) |
| GET | /databases | List all databases |
| GET | /databases/<db>/collections | List collections in database |
| POST | /query | Find documents |
| POST | /aggregate | Run aggregation pipeline |
| POST | /insert | Insert documents |
| POST | /update | Update documents |
| POST | /delete | Delete documents |
| POST | /command | Run raw MongoDB command |
| POST | /sample | Get random documents |
| GET | /collection/<db>/<coll>/count | Document count |
| GET | /collection/<db>/<coll>/indexes | List indexes |

### Shard-Aware Endpoints (for sharded clusters)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /shards | List all shards with online/offline status |
| GET | /databases/available | List databases from online shards only |
| GET | /databases/<db>/collections/available | List collections from online shards only |

### Direct Shard Endpoints (bypass mongos)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /shard/<shard_id>/databases | List databases on specific shard |
| GET | /shard/<shard_id>/databases/<db>/collections | List collections on specific shard |
| POST | /shard/<shard_id>/query | Query directly on specific shard |

## Usage Examples

### Authentication

All endpoints (except `/`) require the `X-API-Key` header:
```bash
curl -H "X-API-Key: YOUR_API_KEY" http://localhost/databases
```

### List Databases
```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost/databases
```

### Query Documents
```bash
curl -X POST http://localhost/query \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "mydb",
    "collection": "users",
    "filter": {"status": "active"},
    "projection": {"name": 1, "email": 1},
    "sort": [["created", -1]],
    "limit": 10,
    "skip": 0
  }'
```

### Aggregation Pipeline
```bash
curl -X POST http://localhost/aggregate \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "mydb",
    "collection": "orders",
    "pipeline": [
      {"$match": {"status": "completed"}},
      {"$group": {"_id": "$product", "total": {"$sum": "$amount"}}}
    ]
  }'
```

### Insert Documents
```bash
curl -X POST http://localhost/insert \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "mydb",
    "collection": "logs",
    "documents": [
      {"event": "login", "user": "john"},
      {"event": "logout", "user": "jane"}
    ]
  }'
```

### Update Documents
```bash
curl -X POST http://localhost/update \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "mydb",
    "collection": "users",
    "filter": {"email": "john@example.com"},
    "update": {"$set": {"status": "inactive"}},
    "many": false,
    "upsert": false
  }'
```

### Delete Documents
```bash
curl -X POST http://localhost/delete \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "mydb",
    "collection": "sessions",
    "filter": {"expired": true},
    "many": true
  }'
```

### Check Shard Status
```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost/shards
```

Response:
```json
{
  "total_shards": 2,
  "online_shards": 1,
  "offline_shards": 1,
  "shards": [
    {"id": "rs_usa01", "host": "rs_usa01/10.5.5.2:27017", "online": true, "state": 1},
    {"id": "rs_china01", "host": "rs_china01/10.5.5.3:27017", "online": false, "error": "..."}
  ]
}
```

### List Databases from Online Shards Only
```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost/databases/available
```

### Query Specific Shard Directly
```bash
curl -X POST http://localhost/shard/rs_usa01/query \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "Fermenter",
    "collection": "Fermenters List",
    "filter": {},
    "limit": 10
  }'
```

## Run as Service (systemd)

```bash
sudo tee /etc/systemd/system/mongodb-bridge.service << 'EOF'
[Unit]
Description=MongoDB HTTP Bridge
After=network.target mongod.service

[Service]
Type=simple
User=root
Environment="API_KEY=your-strong-api-key-here"
Environment="MONGO_URI=mongodb://admin:password@localhost:27020/?authSource=admin"
ExecStart=/usr/bin/python3 /opt/mongodb_bridge.py --port 443
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mongodb-bridge
sudo systemctl start mongodb-bridge
```

## Security Recommendations

1. Use a strong API key (64+ characters recommended)
2. Use HTTPS in production
3. Use firewall rules to restrict access
4. Run behind nginx for additional security features
5. Do not expose to public internet without proper security
6. Set up port forwarding on your router if needed

## Generating a Strong API Key

```bash
# Using Python
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# Using OpenSSL
openssl rand -base64 48
```

## Troubleshooting

### Port already in use
```bash
sudo lsof -i :80
sudo pkill -f mongodb_bridge.py
```

### MongoDB authentication failed
Verify your credentials work with mongosh:
```bash
mongosh "mongodb://admin:password@localhost:27020/?authSource=admin"
```

### Shard unavailable errors
Use shard-aware endpoints:
- `/databases/available` instead of `/databases`
- `/shard/<shard_id>/query` for direct shard queries

### Virtual environment required (Python 3.12+)
```bash
python3 -m venv mongodb-bridge-env
source mongodb-bridge-env/bin/activate
pip install flask pymongo
```

## License

MIT License - Use freely!
