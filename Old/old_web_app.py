"""SkyLog Radar web server.

This rewritten version keeps the app in one readable file for now, but it is
organized into clear sections so it can be split into modules later.
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
from __future__ import annotations

import math
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request


# -----------------------------------------------------------------------------
# Flask app object
# -----------------------------------------------------------------------------
app = Flask(__name__)


# -----------------------------------------------------------------------------
# Application constants and runtime state
# -----------------------------------------------------------------------------
CACHE_SECONDS = 10
DB_NAME = "skylog.db"
FETCH_SECONDS = 10
PHOTO_CACHE_SECONDS = 86_400

MY_LAT = 36.31344
MY_LON = -82.35347
RADIUS_MILES = 100.0

cached_results: List[Dict[str, Any]] = []
fetch_error: Optional[str] = None
last_fetch = 0.0
last_fetch_time: Optional[str] = None
latest_aircraft: List[Dict[str, Any]] = []
photo_cache: Dict[str, Dict[str, Any]] = {}


# -----------------------------------------------------------------------------
# Aircraft classification helper
# -----------------------------------------------------------------------------
def classify_aircraft(aircraft: Dict[str, Any]) -> str:
    """Return Commercial, Civilian, Military, or Unknown for one API aircraft."""
    callsign = (aircraft.get("flight") or "").strip().upper()
    tail = (aircraft.get("r") or "").strip().upper()
    aircraft_type = (aircraft.get("t") or "").strip().upper()
    icao_hex = (aircraft.get("hex") or "").strip().upper()

    commercial_prefixes = [
        "AAL", "ASA", "DAL", "EDV", "ENY", "FDX", "FFT", "JBU", "NKS",
        "RPA", "SKW", "SWA", "UAL", "UPS",
    ]

    military_callsigns = [
        "ARMY", "GOLD", "HOIST", "JEDI", "KING", "MARINE", "NAVY", "PAT",
        "RCH", "REACH", "SAM", "SPAR",
    ]

    if icao_hex.startswith("AE"):
        return "Military"

    if any(callsign.startswith(prefix) for prefix in military_callsigns):
        return "Military"

    if any(callsign.startswith(prefix) for prefix in commercial_prefixes):
        return "Commercial"

    if tail.startswith("N"):
        return "Civilian"

    if aircraft_type.startswith(("A3", "B7", "B38", "B39", "CRJ", "E17", "E19")):
        return "Commercial"

    return "Unknown"


# -----------------------------------------------------------------------------
# Distance calculation helper
# -----------------------------------------------------------------------------
def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in miles between two lat/lon points."""
    earth_radius_miles = 3958.8

    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_miles * c


# -----------------------------------------------------------------------------
# Airplanes.live API URL builder
# -----------------------------------------------------------------------------
def get_api_url() -> str:
    """Build the Airplanes.live point API URL from current location/radius."""
    radius_nm = float(RADIUS_MILES) * 0.868976
    return f"https://api.airplanes.live/v2/point/{MY_LAT}/{MY_LON}/{radius_nm:.2f}"


# -----------------------------------------------------------------------------
# ZIP code lookup helper
# -----------------------------------------------------------------------------
def get_coordinates_from_zip(zip_code: str) -> Dict[str, Any]:
    """Return coordinates and place info for a United States ZIP code."""
    response = requests.get(
        f"https://api.zippopotam.us/us/{zip_code}",
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    place = data["places"][0]

    return {
        "city": place["place name"],
        "lat": float(place["latitude"]),
        "lon": float(place["longitude"]),
        "state": place["state abbreviation"],
    }


# -----------------------------------------------------------------------------
# Database initialization helper
# -----------------------------------------------------------------------------
def init_database() -> None:
    """Create SkyLog tables if they do not already exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS aircraft_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            icao_hex TEXT,
            callsign TEXT,
            tail_number TEXT,
            latitude REAL,
            longitude REAL,
            altitude_feet TEXT,
            speed_knots REAL,
            heading_degrees REAL,
            distance_miles REAL,
            seen_at TEXT,
            category TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS aircraft_passes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            icao_hex TEXT,
            callsign TEXT,
            tail_number TEXT,
            aircraft_type TEXT,
            first_seen TEXT,
            last_seen TEXT,
            closest_distance_miles REAL,
            closest_latitude REAL,
            closest_longitude REAL,
            altitude_feet TEXT,
            speed_knots REAL,
            heading_degrees REAL,
            direction TEXT,
            category TEXT
        )
        """
    )

    conn.commit()
    conn.close()


# -----------------------------------------------------------------------------
# Aircraft position logging helper
# -----------------------------------------------------------------------------
def log_web_aircraft_position(record: Dict[str, Any]) -> None:
    """Save one aircraft position point to SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO aircraft_positions (
            icao_hex,
            callsign,
            tail_number,
            latitude,
            longitude,
            altitude_feet,
            speed_knots,
            heading_degrees,
            distance_miles,
            seen_at,
            category
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.get("icao_hex"),
            record.get("callsign"),
            record.get("tail_number"),
            record.get("lat"),
            record.get("lon"),
            record.get("altitude"),
            record.get("speed"),
            record.get("heading"),
            record.get("distance_miles"),
            time.strftime("%Y-%m-%d %H:%M:%S"),
            record.get("category"),
        ),
    )

    conn.commit()
    conn.close()


# -----------------------------------------------------------------------------
# API aircraft normalizer
# -----------------------------------------------------------------------------
def normalize_aircraft_record(plane: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert one raw API aircraft object into SkyLog's frontend format."""
    lat = plane.get("lat")
    lon = plane.get("lon")

    if lat is None or lon is None:
        return None

    distance = haversine_miles(MY_LAT, MY_LON, float(lat), float(lon))

    return {
        "aircraft_type": plane.get("t", ""),
        "altitude": plane.get("alt_baro", ""),
        "callsign": (plane.get("flight") or "").strip(),
        "category": classify_aircraft(plane),
        "description": plane.get("desc", ""),
        "distance_miles": round(distance, 2),
        "heading": plane.get("track", 0),
        "icao_hex": (plane.get("hex") or "").upper(),
        "lat": lat,
        "lon": lon,
        "owner_operator": plane.get("ownOp", ""),
        "speed": plane.get("gs", ""),
        "tail_number": plane.get("r", ""),
        "year": plane.get("year", ""),
    }


# -----------------------------------------------------------------------------
# One-time aircraft fetch helper
# -----------------------------------------------------------------------------
def fetch_aircraft_once() -> List[Dict[str, Any]]:
    """Fetch current aircraft once from Airplanes.live."""
    response = requests.get(get_api_url(), timeout=20)
    response.raise_for_status()

    data = response.json()
    planes = data.get("ac", data.get("aircraft", []))

    results: List[Dict[str, Any]] = []

    for plane in planes:
        record = normalize_aircraft_record(plane)

        if record is None:
            continue

        results.append(record)
        log_web_aircraft_position(record)

    return results


# -----------------------------------------------------------------------------
# Background aircraft fetch loop
# -----------------------------------------------------------------------------
def fetch_aircraft_loop() -> None:
    """Continuously refresh current aircraft in the background."""
    global fetch_error, last_fetch_time, latest_aircraft

    while True:
        try:
            latest_aircraft = fetch_aircraft_once()
            last_fetch_time = time.strftime("%Y-%m-%d %H:%M:%S")
            fetch_error = None
            print(f"Fetched {len(latest_aircraft)} aircraft")

        except requests.RequestException as exc:
            fetch_error = "Airplanes.live timeout or connection issue"
            print(f"API warning: {exc}")

        time.sleep(FETCH_SECONDS)


# -----------------------------------------------------------------------------
# Route: home page
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    """Render the SkyLog radar page."""
    return render_template(
        "index.html",
        my_lat=MY_LAT,
        my_lon=MY_LON,
        radius=RADIUS_MILES,
    )


# -----------------------------------------------------------------------------
# Route: current aircraft JSON
# -----------------------------------------------------------------------------
@app.route("/aircraft")
def aircraft():
    """Return latest aircraft snapshot."""
    return jsonify(latest_aircraft)


# -----------------------------------------------------------------------------
# Route: aircraft local history JSON
# -----------------------------------------------------------------------------
@app.route("/aircraft/<icao_hex>/history")
def aircraft_history(icao_hex: str):
    """Return local SQLite history summary for one aircraft."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            MIN(seen_at),
            MAX(seen_at),
            COUNT(*),
            MAX(speed_knots),
            MAX(CASE
                WHEN altitude_feet IN ('ground', 'GROUND', 'GND') THEN 0
                ELSE CAST(altitude_feet AS INTEGER)
            END),
            MIN(distance_miles)
        FROM aircraft_positions
        WHERE UPPER(icao_hex) = UPPER(?)
        """,
        (icao_hex,),
    )

    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        return jsonify({"found": False})

    first_seen, last_seen, track_points, max_speed, max_altitude, closest = row

    return jsonify(
        {
            "closest_distance": closest,
            "first_seen": first_seen,
            "found": True,
            "last_seen": last_seen,
            "max_altitude": max_altitude,
            "max_speed": max_speed,
            "time_in_area": "Tracked locally",
            "track_points": track_points,
        }
    )


# -----------------------------------------------------------------------------
# Route: aircraft photo lookup JSON
# -----------------------------------------------------------------------------
@app.route("/aircraft_photo")
def aircraft_photo():
    """Return one real aircraft photo URL when possible."""
    tail = request.args.get("tail", "").strip().upper()

    if not tail:
        return jsonify({"found": False})

    now = time.time()

    if tail in photo_cache:
        cached = photo_cache[tail]

        if now - cached["time"] < PHOTO_CACHE_SECONDS:
            return jsonify(cached["data"])

    search_url = f"https://www.planespotters.net/search?q={tail}"

    try:
        response = requests.get(
            search_url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        if response.status_code != 200:
            return jsonify({"found": False})

        soup = BeautifulSoup(response.text, "html.parser")
        image = soup.find("img", class_="photo_card__photo")

        if not image:
            image = soup.select_one("img[src*='photos'], img[data-src*='photos']")

        if not image:
            return jsonify({"found": False})

        src = image.get("data-src") or image.get("src")

        if not src:
            return jsonify({"found": False})

        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = "https://www.planespotters.net" + src

        data = {
            "found": True,
            "image": src,
            "source": search_url,
        }

        photo_cache[tail] = {"data": data, "time": now}
        return jsonify(data)

    except Exception as exc:
        print(f"Photo scrape error: {exc}")
        return jsonify({"found": False})


# -----------------------------------------------------------------------------
# Route: historical heatmap JSON
# -----------------------------------------------------------------------------
@app.route("/heatmap_history")
def heatmap_history():
    """Return historical heatmap points from SQLite."""
    range_value = request.args.get("range", "24h")
    category = request.args.get("category", "All")

    range_sql = {
        "1h": "datetime('now', '-1 hour')",
        "24h": "datetime('now', '-24 hours')",
        "7d": "datetime('now', '-7 days')",
        "30d": "datetime('now', '-30 days')",
    }.get(range_value, "datetime('now', '-24 hours')")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query = f"""
        SELECT latitude, longitude
        FROM aircraft_positions
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
          AND seen_at >= {range_sql}
    """
    params: List[Any] = []

    if category != "All":
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY seen_at DESC LIMIT 3000"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return jsonify([[lat, lon, 0.6] for lat, lon in rows])


# -----------------------------------------------------------------------------
# Route: set location by ZIP code
# -----------------------------------------------------------------------------
@app.route("/set_location", methods=["POST"])
def set_location():
    """Update radar center point from a ZIP code."""
    global MY_LAT, MY_LON

    data = request.get_json() or {}
    zip_code = str(data.get("zip", "")).strip()

    if not zip_code:
        return jsonify({"error": "ZIP code is required", "success": False}), 400

    try:
        location = get_coordinates_from_zip(zip_code)
        MY_LAT = location["lat"]
        MY_LON = location["lon"]

        return jsonify(
            {
                "city": location["city"],
                "lat": MY_LAT,
                "lon": MY_LON,
                "state": location["state"],
                "success": True,
            }
        )

    except Exception as exc:
        return jsonify({"error": str(exc), "success": False}), 400


# -----------------------------------------------------------------------------
# Route: set radius
# -----------------------------------------------------------------------------
@app.route("/set_radius", methods=["POST"])
def set_radius():
    """Update radar radius and immediately return a fresh aircraft list."""
    global fetch_error, last_fetch_time, latest_aircraft, RADIUS_MILES

    data = request.get_json() or {}
    RADIUS_MILES = float(data.get("radius", RADIUS_MILES))

    try:
        latest_aircraft = fetch_aircraft_once()
        last_fetch_time = time.strftime("%Y-%m-%d %H:%M:%S")
        fetch_error = None

    except requests.RequestException as exc:
        fetch_error = "Airplanes.live timeout or connection issue"
        print(f"Radius update warning: {exc}")

    return jsonify(
        {
            "aircraft": latest_aircraft,
            "radius": RADIUS_MILES,
            "success": True,
        }
    )


# -----------------------------------------------------------------------------
# Route: status JSON
# -----------------------------------------------------------------------------
@app.route("/status")
def status():
    """Return backend fetch status."""
    return jsonify(
        {
            "aircraft_count": len(latest_aircraft),
            "fetch_error": fetch_error,
            "last_fetch_time": last_fetch_time,
        }
    )


# -----------------------------------------------------------------------------
# Application startup
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    init_database()

    fetch_thread = threading.Thread(
        target=fetch_aircraft_loop,
        daemon=True,
    )
    fetch_thread.start()

    app.run(debug=True, use_reloader=False)
