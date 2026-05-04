FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# tzdata is needed for zoneinfo lookups used in city-based naming endpoint.
# build-essential provides gcc/g++/make needed to compile pyswisseph.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 5050

ENV HOST=0.0.0.0 \
    PORT=5050 \
    DEBUG=false

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5050"]
