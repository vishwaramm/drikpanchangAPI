import os
from flask import Flask, jsonify, request

import panchangApi

app = Flask(__name__)


def _payload_from_request():
    data = {}

    # Query params for GET
    for key, value in request.args.items():
        data[key] = value

    # JSON body for POST can override query params
    if request.is_json:
        body = request.get_json(silent=True) or {}
        if isinstance(body, dict):
            data.update(body)

    return data


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/v1/panchang", methods=["GET"])
def get_panchang():
    try:
        payload = _payload_from_request()
        date = panchangApi.parse_date(str(payload.get("date", "")))
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
        timezone = float(payload["timezone"])

        panchang_data = panchangApi.calculate_panchang(date, latitude, longitude, timezone)
        return jsonify(panchang_data)
    except KeyError as exc:
        return jsonify({"error": f"missing required field: {exc.args[0]}"}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"internal error: {str(exc)}"}), 500


@app.route("/api/v1/drik/functions", methods=["GET"])
def get_available_functions():
    return jsonify({"functions": panchangApi.list_drik_functions()})


@app.route("/api/v1/cities", methods=["GET"])
def get_cities():
    try:
        payload = _payload_from_request()
        result = panchangApi.get_cities(str(payload.get("country", "")).strip())
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"internal error: {str(exc)}"}), 500


@app.route("/api/v1/drik/<function_name>", methods=["GET", "POST"])
def call_drik_function(function_name):
    try:
        payload = _payload_from_request()
        result = panchangApi.call_drik_function(function_name, payload)
        return jsonify({"function": function_name, "result": result})
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except TypeError as exc:
        return jsonify({"error": f"invalid payload: {str(exc)}"}), 400
    except Exception as exc:
        return jsonify({"error": f"internal error: {str(exc)}"}), 500


@app.route("/api/v1/naming/letters", methods=["GET", "POST"])
def get_name_letters():
    try:
        payload = _payload_from_request()
        result = panchangApi.get_name_letters(payload)
        return jsonify(result)
    except KeyError as exc:
        return jsonify({"error": f"missing required field: {exc.args[0]}"}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"internal error: {str(exc)}"}), 500


@app.route("/api/v1/naming/letters/by-city", methods=["GET", "POST"])
def get_name_letters_by_city():
    try:
        payload = _payload_from_request()
        result = panchangApi.get_name_letters_by_city(payload)
        return jsonify(result)
    except ValueError as exc:
        error_value = exc.args[0] if exc.args else str(exc)
        if isinstance(error_value, dict):
            return jsonify({"error": error_value.get("message"), "matches": error_value.get("matches", [])}), 400
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"internal error: {str(exc)}"}), 500


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("DEBUG", "false").strip().lower() == "true"
    app.run(host=host, port=port, debug=debug)
