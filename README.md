# drikpanchangAPI

Flask API wrapper around functions from the `drik-panchanga` library.

## Features

- Panchang summary endpoint
- Dynamic endpoint for individual drik-panchanga functions
- Birth naming syllable endpoint (Nakshatra/Pada based)
- Function discovery endpoint
- Basic health check endpoint

## Project Structure

- `app.py` - Flask app and API routes
- `panchangApi.py` - input parsing and drik function dispatcher
- `drik-panchanga/` - upstream drik panchanga source code
- `requirements.txt` - Python dependencies

## Requirements

- Python 3.9+
- `pyswisseph` system-compatible environment

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Server starts on:

- `http://127.0.0.1:5000`

## Docker (Fedora, From Scratch)

### 1. Install Docker Engine

```bash
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 2. Enable and start Docker

```bash
sudo systemctl enable --now docker
sudo systemctl status docker
```

### 3. Optional: run Docker without sudo

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 4. Build image

From project root:

```bash
docker build -t drikpanchang-api:latest .
```

### 5. Run container

```bash
docker run --rm -p 5000:5000 --name drikpanchang-api drikpanchang-api:latest
```

API will be available at:

- `http://127.0.0.1:5000`

### 6. Run with Docker Compose (optional)

```bash
docker compose up --build
```

Stop:

```bash
docker compose down
```

## API Endpoints

### 1. Health

- `GET /health`

Example:

```bash
curl "http://127.0.0.1:5000/health"
```

### 2. Panchang Summary

- `GET /api/v1/panchang`

Required query params:

- `date` (`YYYY-MM-DD`, `DD-MM-YYYY`, or `DDMMYYYY`)
- `latitude`
- `longitude`
- `timezone`

Example:

```bash
curl "http://127.0.0.1:5000/api/v1/panchang?date=2025-01-23&latitude=12.972&longitude=77.594&timezone=5.5"
```

### 3. List Supported Drik Functions

- `GET /api/v1/drik/functions`

Example:

```bash
curl "http://127.0.0.1:5000/api/v1/drik/functions"
```

### 4. Call Any Drik Function

- `GET /api/v1/drik/<function_name>`
- `POST /api/v1/drik/<function_name>`

You can pass either:

- `jd` directly, or
- `date` (which will be converted to Julian day)

Functions that need location also require:

- `latitude`, `longitude`, `timezone`

Examples:

```bash
curl "http://127.0.0.1:5000/api/v1/drik/vaara?date=2025-01-23"
```

```bash
curl "http://127.0.0.1:5000/api/v1/drik/tithi?date=2025-01-23&latitude=12.972&longitude=77.594&timezone=5.5"
```

POST example:

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/drik/day_duration" \
  -H "Content-Type: application/json" \
  -d '{"date":"2025-01-23","latitude":12.972,"longitude":77.594,"timezone":5.5}'
```

### 5. Name Letters / Syllables from Birth Data

- `GET /api/v1/naming/letters`
- `POST /api/v1/naming/letters`

Inputs:

- `birth_datetime` (ISO-8601 preferred, e.g. `2025-01-23T14:35:00`)
- `timezone` (required if `birth_datetime` has no UTC offset, e.g. `5.5`)
- `latitude` and `longitude` (optional, but recommended for location-aware/topocentric result)

Example (GET):

```bash
curl "http://127.0.0.1:5000/api/v1/naming/letters?birth_datetime=2025-01-23T14:35:00&timezone=5.5&latitude=12.972&longitude=77.594"
```

Example (POST):

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/naming/letters" \
  -H "Content-Type: application/json" \
  -d '{"birth_datetime":"2025-01-23T14:35:00","timezone":5.5,"latitude":12.972,"longitude":77.594}'
```

Response includes:

- `nakshatra_name`
- `pada`
- `recommended_syllable`
- `syllables_for_nakshatra`

### 6. Name Letters by City (No Lat/Long Needed)

- `GET /api/v1/naming/letters/by-city`
- `POST /api/v1/naming/letters/by-city`

Inputs:

- `birth_datetime` (required)
- `city` (required)
- `state` (optional, used for disambiguation)
- `country` (optional, used for disambiguation)

You can also pass city in one field:

- `city=San Fernando, Trinidad and Tobago`

Example (GET):

```bash
curl "http://127.0.0.1:5000/api/v1/naming/letters/by-city?birth_datetime=2000-06-05T06:35:00&city=San%20Fernando&country=Trinidad"
```

Example (POST):

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/naming/letters/by-city" \
  -H "Content-Type: application/json" \
  -d '{"birth_datetime":"2000-06-05T06:35:00","city":"San Fernando","country":"Trinidad"}'
```

## Error Handling

- `400` for invalid or missing input
- `404` for unsupported function names
- `500` for unexpected internal errors

## Notes

- This project depends on the bundled `drik-panchanga` source as a submodule-like folder.
- Swiss Ephemeris API compatibility fixes were applied in `drik-panchanga/panchanga.py` for current `pyswisseph`.
