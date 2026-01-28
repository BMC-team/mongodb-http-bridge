# MongoDB HTTP Bridge

A secure REST API bridge for accessing MongoDB over HTTP. Designed to enable remote database access when direct MongoDB connections are not possible (firewalls, proxies, etc.).

## Features

- API Key Authentication - All requests require authentication
- HTTPS Support - Optional SSL/TLS encryption
- Full MongoDB Access - Query, aggregate, insert, update, delete
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

# 3. Run (will auto-generate API key)
sudo python3 mongodb_bridge.py --port 80
```

## Configuration

### Environment Variables
```bash
export API_KEY="your-secret-key"              # Optional: auto-generated if not set
export MONGO_URI="mongodb://localhost:27017"  # Optional: default is localhost
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

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Health check (no auth required) |
| GET | /databases | List all databases |
| GET | /databases/<db>/collections | List collections |
| POST | /query | Find documents |
| POST | /aggregate | Run aggregation pipeline |
| POST | /insert | Insert documents |
| POST | /update | Update documents |
| POST | /delete | Delete documents |
| POST | /command | Run raw MongoDB command |
| POST | /sample | Get random documents |
| GET | /collection/<db>/<coll>/count | Document count |
| GET | /collection/<db>/<coll>/indexes | List indexes |

## Usage Examples

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
    "limit": 10
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
    "many": false
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

## Run as Service (systemd)

```bash
sudo tee /etc/systemd/system/mongodb-bridge.service << 'EOF'
[Unit]
Description=MongoDB HTTP Bridge
After=network.target mongod.service

[Service]
Type=simple
User=root
Environment="API_KEY=your-secret-key"
Environment="MONGO_URI=mongodb://localhost:27017"
ExecStart=/usr/bin/python3 /opt/mongodb_bridge.py --port 80
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mongodb-bridge
sudo systemctl start mongodb-bridge
```

## Security Recommendations

1. Use HTTPS in production
2. Set a strong API key via environment variable
3. Use firewall rules to restrict access
4. Run behind nginx for additional security features
5. Do not expose to public internet without proper security

## License

MIT License - Use freely!
