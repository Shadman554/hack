# Location Collector Phishing Project

This project enables stealthy collection of precise or approximate location data from targets via social-engineered phishing links optimized for mobile devices.

## Features

- Mobile-optimized phishing page that captures GPS coordinates or fallback device/network info.
- Python Flask backend server with two HTTPS endpoints for data collection.
- Reverse geocoding using OpenStreetMap Nominatim API with rate limiting.
- IP geolocation enrichment using ipinfo.io.
- Logs all data with timestamps for analysis.

## Requirements

- Python 3.8+
- Flask
- Requests

## Running Locally with HTTPS

1. Provide your SSL certificate and key as `cert.pem` and `key.pem` in the project directory.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the server:

```bash
python server.py
```

4. Deploy the `phishing.html` page on a web server.

## Deploying on Railway

Railway provides automatic HTTPS termination and dynamic port assignment.

### Steps:

1. Set environment variable `RAILWAY=true` in Railway project settings.
2. The server will automatically use the port Railway assigns via the `PORT` environment variable.
3. Do NOT provide SSL certificates; Railway handles HTTPS.
4. Run the server with:

```bash
python server.py
```

### Notes:

- The server disables HTTPS and listens on the Railway-assigned port when `RAILWAY=true`.
- The phishing page endpoints are relative URLs and should work without modification.

## Logging

All collected data is logged to `location_logs.txt` with timestamps.

## Disclaimer

This project is for authorized security testing only. Unauthorized use is illegal.

## PostgreSQL Setup

1. Create a PostgreSQL database on Railway or your preferred provider.
2. Set the `DATABASE_URL` environment variable in Railway to your database connection string (e.g., `postgresql://user:password@host:port/dbname`).
3. The server will automatically create the required table `location_logs` on startup.

## Railway Deployment Notes

- Set environment variables `RAILWAY=true` and `DATABASE_URL` in Railway project settings.
- Do NOT provide SSL certificates; Railway handles HTTPS termination.
- The server uses the dynamic port Railway assigns via the `PORT` environment variable.
- Run the server with:

```bash
python server.py
```

- The phishing page endpoints use relative URLs and require no modification.