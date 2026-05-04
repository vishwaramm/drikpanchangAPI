# drikpanchangAPI

FastAPI service built on top of the `drik-panchanga` library and a clean-room astrology engine.

## Features

- Panchang summary endpoint
- Dynamic endpoint for individual drik-panchanga functions
- Birth naming syllable endpoint (Nakshatra/Pada based)
- Function discovery endpoint
- Basic health check endpoint
- Modular astrology engine for birth charts, dashas, divisional charts, transits, panchang, muhurta, compatibility, and interpretations
- Ashta-Kuta compatibility scoring for matchmaking
- Typed request and response models for the new API surface
- Schema examples and API capability discovery for client introspection
- In-memory result caching for repeated calculations

## Project Structure

- `main.py` - primary FastAPI app
- `legacy_panchanga.py` - input parsing and drik function dispatcher for legacy panchang/naming routes
- `astrology/` - clean-room astrology engine package with injectable engines, rule catalogs, schemas, and registry
- `astrology/api/` - FastAPI router namespace
- `astrology/api/v1.py` - mounted `/api/v1` astrology router
- `astrology/core/` - stable namespace for core astrology logic imports
- `astrology/services/` - stable namespace for service and registry imports
- `astrology/engines/` - engine namespace for swap-friendly imports
- `astrology/responses.py` - typed response models for the API contract
- `astrology/rulepacks.py` - named rule-pack registry for policy swaps
- `astrology/muhurta.py` - muhurta scoring and date filtering engine
- `astrology/panchang.py` - the new panchang engine layer
- `drik-panchanga/` - upstream drik panchanga source code
- `requirements.txt` - Python dependencies

## Requirements

- Python 3.11+ recommended
- `pyswisseph` system-compatible environment

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

### FastAPI service

```bash
uvicorn main:app --host 0.0.0.0 --port 5050
```

Server starts on:

- `http://127.0.0.1:5050`

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
docker run --rm -p 5050:5050 --name drikpanchang-api drikpanchang-api:latest
```

API will be available at:

- `http://127.0.0.1:5050`

### 6. Run with Docker Compose (optional)

```bash
docker compose down
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
curl "http://127.0.0.1:5050/health"
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
curl "http://127.0.0.1:5050/api/v1/panchang?date=2025-01-23&latitude=12.972&longitude=77.594&timezone=5.5"
```

### 3. List Supported Drik Functions

- `GET /api/v1/drik/functions`

Example:

```bash
curl "http://127.0.0.1:5050/api/v1/drik/functions"
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
curl "http://127.0.0.1:5050/api/v1/drik/vaara?date=2025-01-23"
```

```bash
curl "http://127.0.0.1:5050/api/v1/drik/tithi?date=2025-01-23&latitude=12.972&longitude=77.594&timezone=5.5"
```

POST example:

```bash
curl -X POST "http://127.0.0.1:5050/api/v1/drik/day_duration" \
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
curl "http://127.0.0.1:5050/api/v1/naming/letters?birth_datetime=2025-01-23T14:35:00&timezone=5.5&latitude=12.972&longitude=77.594"
```

Example (POST):

```bash
curl -X POST "http://127.0.0.1:5050/api/v1/naming/letters" \
  -H "Content-Type: application/json" \
  -d '{"birth_datetime":"2025-01-23T14:35:00","timezone":5.5,"latitude":12.972,"longitude":77.594}'
```

Response includes:

- `nakshatra_name`
- `pada`
- `recommended_syllable`
- `syllables_for_nakshatra`

## New Astrology API

All new endpoints live under `/api/v1/astrology`.

### 1. Birth Chart

- `GET /api/v1/astrology/birth-chart`
- `POST /api/v1/astrology/birth-chart`

Inputs:

- `birth_datetime` or `birth_date` + `birth_time`
- `timezone` or `timezone_name`
- `latitude` and `longitude`, or `city` with optional `state` and `country`
- `ayanamsa` and optional `ayanamsa_value`
- `house_system` with `whole_sign` as the default

### 2. Vimshottari Dashas

- `GET /api/v1/astrology/dashas`
- `POST /api/v1/astrology/dashas`

Returns:

- mahadasha, antardasha, and pratyantardasha timing
- optional `sookshma` and `prana` levels when `max_depth` is increased
- dasha balance at birth
- structured nesting for the full timeline

### 3. Divisional Charts

- `GET /api/v1/astrology/divisional-charts`
- `POST /api/v1/astrology/divisional-charts`

Returns:

- D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D30, D60 placements

### 4. Transits

- `GET /api/v1/astrology/transits`
- `POST /api/v1/astrology/transits`

Returns:

- transit chart
- natal-to-transit aspect hits
- summary overlays

### 5. Interpretation

- `GET /api/v1/astrology/interpretation`
- `POST /api/v1/astrology/interpretation`

Returns:

- structured rule matches
- category scores
- theme summaries for career, marriage, finance, health, education, relocation, and general interpretation
- optional per-request `rule_pack` selection

Available rule packs:

- `default_traditional`
- `classical_core`
- `life_themes`

Rule sources are mixed:

- Drik Panchang is used wherever it publishes an explicit definition
- Common classical Vedic astrology practice is used for rules not fully specified there
- Any remaining thresholds are labeled `best_judgment` in the response metadata

### 6. Panchang

- `GET /api/v1/astrology/panchang`
- `POST /api/v1/astrology/panchang`

Inputs:

- `date`
- `latitude` and `longitude`, or `city` with optional `state` and `country`
- `timezone` or `timezone_name`

Returns:

- the legacy panchang summary through the new service layer

The astrology package now also includes:

- `astrology/cache.py` for in-memory result caching
- `astrology/cache.py` also includes a file-backed persistent cache backend
- `astrology/schemas.py` for request validation
- `astrology/responses.py` for typed response models
- `astrology/registry.py` for versioned service selection
- `astrology/rulepacks.py` for named rule bundles
- `astrology/muhurta.py` for muhurta scoring
- `astrology/panchang.py` for the new panchang engine layer
- `astrology/core/` for stable core imports
- `astrology/services/` for stable service imports
- `tests/fixtures/` for snapshot payloads and known output fixtures

Response contracts are now explicitly modeled for:

- birth chart
- dashas
- divisional charts
- transits
- interpretation
- compatibility
- muhurta
- panchang

Capability discovery is available at:

- `GET /api/v1/astrology/meta`
- `POST /api/v1/astrology/meta`

It reports:

- selected service version
- available rule packs
- supported endpoints
- supported dasha levels
- supported divisional charts
- supported ayanamsa values
- cache backend name

Available rule packs now include:

- `default_traditional`
- `classical_core`
- `strict_classical`
- `extended_interpretive`
- `life_themes`

Version selection:

- pass `version=v1` in the query string, or
- send `X-Astrology-Version: v1`

If no version is supplied, the default `v1` service is used.

### 7. Compatibility

- `GET /api/v1/astrology/compatibility`
- `POST /api/v1/astrology/compatibility`

Returns an Ashta-Kuta compatibility report.

Inputs:

- `boy_chart` and `girl_chart`, or
- nested `boy` and `girl` birth payloads that can be converted into charts

The response includes:

- total gunas
- per-kuta scores for Varna, Vashya, Tara, Yoni, Graha Maitri, Gana, Bhakoot, and Nadi
- a simple grade summary

### 8. Muhurta

- `GET /api/v1/astrology/muhurta`
- `POST /api/v1/astrology/muhurta`

Inputs:

- `date` for a single day, or
- `start_date` and `end_date` for a date range
- `latitude` and `longitude`, or `city` with optional `state` and `country`
- `timezone` or `timezone_name`
- `activity_type` such as `general`, `career`, `marriage`, `travel`, `education`, or `finance`
- `minimum_score` to filter out weak days

Returns:

- scored dates
- panchang component breakdown
- Rahu Kalam, Yamaganda, Gulika, and Abhijit windows
- best_dates summary

### 9. Name Letters by City (No Lat/Long Needed)

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
curl "http://127.0.0.1:5050/api/v1/naming/letters/by-city?birth_datetime=2000-06-05T06:35:00&city=San%20Fernando&country=Trinidad"
```

Example (POST):

```bash
curl -X POST "http://127.0.0.1:5050/api/v1/naming/letters/by-city" \
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
