from flask import Flask, jsonify, render_template, request
import requests
import math
import time
import threading
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup

app = Flask(__name__)

MY_LAT = 36.31344
MY_LON = -82.35347
RADIUS_MILES = 100
RADIUS_NM = RADIUS_MILES * 0.868976

def get_coordinates_from_zip(zip_code):
    url = f"https://api.zippopotam.us/us/{zip_code}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    data = response.json()

    place = data["places"][0]

    return {
        "lat": float(place["latitude"]),
        "lon": float(place["longitude"]),
        "city": place["place name"],
        "state": place["state abbreviation"]
    }

def get_api_url():
    radius_nm = RADIUS_MILES * 0.868976
    return f"https://api.airplanes.live/v2/point/{MY_LAT}/{MY_LON}/{radius_nm:.2f}"

FETCH_SECONDS = 10

DB_NAME = "skylog.db"

latest_aircraft = []
last_fetch_time = None
fetch_error = None
photo_cache = {}
PHOTO_CACHE_SECONDS = 86400

CACHE_SECONDS = 10

cached_results = []
last_fetch = 0


def classify_aircraft(aircraft):
    callsign = (aircraft.get("flight") or "").strip().upper()
    tail = (aircraft.get("r") or "").upper()
    aircraft_type = (aircraft.get("t") or "").upper()
    icao_hex = (aircraft.get("hex") or "").upper()

    commercial_prefixes = [
        "DAL", "AAL", "UAL", "SWA", "FFT", "JBU", "ASA", "NKS",
        "SKW", "ENY", "EDV", "RPA", "UPS", "FDX"
    ]

    military_callsigns = [
        "RCH", "REACH", "PAT", "SAM", "SPAR", "NAVY", "ARMY",
        "MARINE", "KING", "GOLD", "HOIST", "JEDI"
    ]

    if icao_hex.startswith("AE"):
        return "Military"

    if any(callsign.startswith(prefix) for prefix in military_callsigns):
        return "Military"

    if any(callsign.startswith(prefix) for prefix in commercial_prefixes):
        return "Commercial"

    if tail.startswith("N"):
        return "Civilian"

    return "Unknown"

def haversine_miles(lat1, lon1, lat2, lon2):
    earth_radius_miles = 3958.8

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius_miles * c

def log_web_aircraft_position(record):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
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
    """, (
        record["icao_hex"],
        record["callsign"],
        record["tail_number"],
        record["lat"],
        record["lon"],
        record["altitude"],
        record["speed"],
        record["heading"],
        record["distance_miles"],
        time.strftime("%Y-%m-%d %H:%M:%S"),
        record["category"]
    ))

    conn.commit()
    conn.close()

def fetch_aircraft_loop():
    global latest_aircraft
    global last_fetch_time
    global fetch_error

    while True:
        try:
            response = requests.get(get_api_url(), timeout=20)

            if response.status_code == 429:
                fetch_error = "Rate limited by Airplanes.live"
                print(fetch_error)
                time.sleep(FETCH_SECONDS)
                continue

            response.raise_for_status()
            data = response.json()

            planes = data.get("ac", data.get("aircraft", []))

            results = []

            for plane in planes:
                lat = plane.get("lat")
                lon = plane.get("lon")

                if lat is None or lon is None:
                    continue

                distance = haversine_miles(
                    MY_LAT,
                    MY_LON,
                    lat,
                    lon
                )

                record = {
                    "icao_hex": plane.get("hex"),
                    "callsign": (plane.get("flight") or "").strip(),
                    "tail_number": plane.get("r", ""),
                    "aircraft_type": plane.get("t", ""),
                    "description": plane.get("desc", ""),
                    "owner_operator": plane.get("ownOp", ""),
                    "year": plane.get("year", ""),
                    "altitude": plane.get("alt_baro", ""),
                    "speed": plane.get("gs", ""),
                    "heading": plane.get("track", 0),
                    "lat": lat,
                    "lon": lon,
                    "distance_miles": round(distance, 2),
                    "category": classify_aircraft(plane)
                }

                results.append(record)
                log_web_aircraft_position(record)

            latest_aircraft = results
            last_fetch_time = time.strftime("%Y-%m-%d %H:%M:%S")
            fetch_error = None

            print(f"Fetched {len(results)} aircraft")

        except requests.RequestException as e:
            fetch_error = "Airplanes.live timeout or connection issue"
            print(f"API warning: {e}")

        time.sleep(FETCH_SECONDS)


@app.route("/")
def index():
    return render_template(
        "index.html",
        my_lat=MY_LAT,
        my_lon=MY_LON,
        radius=RADIUS_MILES
    )

@app.route("/set_location", methods=["POST"])
def set_location():
    global MY_LAT
    global MY_LON

    data = request.get_json()
    zip_code = str(data.get("zip", "")).strip()

    if not zip_code:
        return jsonify({
            "success": False,
            "error": "ZIP code is required"
        }), 400

    try:
        location = get_coordinates_from_zip(zip_code)

        MY_LAT = location["lat"]
        MY_LON = location["lon"]

        return jsonify({
            "success": True,
            "lat": MY_LAT,
            "lon": MY_LON,
            "city": location["city"],
            "state": location["state"]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route("/set_radius", methods=["POST"])
def set_radius():
    global RADIUS_MILES
    global latest_aircraft
    global last_fetch_time
    global fetch_error

    data = request.get_json()
    radius = float(data.get("radius", RADIUS_MILES))

    RADIUS_MILES = radius

    try:
        latest_aircraft = fetch_aircraft_once()
        last_fetch_time = time.strftime("%Y-%m-%d %H:%M:%S")
        fetch_error = None
    except requests.RequestException as e:
        fetch_error = "Airplanes.live timeout or connection issue"
        print(f"Radius update warning: {e}")

    return jsonify({
        "success": True,
        "radius": RADIUS_MILES,
        "aircraft": latest_aircraft
    })

def fetch_aircraft_once():
    response = requests.get(get_api_url(), timeout=20)
    response.raise_for_status()
    data = response.json()

    planes = data.get("ac", data.get("aircraft", []))
    results = []

    for plane in planes:
        lat = plane.get("lat")
        lon = plane.get("lon")

        if lat is None or lon is None:
            continue

        distance = haversine_miles(MY_LAT, MY_LON, lat, lon)

        record = {
            "icao_hex": plane.get("hex"),
            "callsign": (plane.get("flight") or "").strip(),
            "tail_number": plane.get("r", ""),
            "aircraft_type": plane.get("t", ""),
            "description": plane.get("desc", ""),
            "owner_operator": plane.get("ownOp", ""),
            "year": plane.get("year", ""),
            "altitude": plane.get("alt_baro", ""),
            "speed": plane.get("gs", ""),
            "heading": plane.get("track", 0),
            "lat": lat,
            "lon": lon,
            "distance_miles": round(distance, 2),
            "category": classify_aircraft(plane)
        }

        results.append(record)
        log_web_aircraft_position(record)

    return results

@app.route("/aircraft")
def aircraft():
    return jsonify(latest_aircraft)


@app.route("/status")
def status():
    return jsonify({
        "last_fetch_time": last_fetch_time,
        "aircraft_count": len(latest_aircraft),
        "fetch_error": fetch_error
    })

@app.route("/aircraft_photo")
def aircraft_photo():
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
            headers={
                "User-Agent": "Mozilla/5.0"
            }
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
            "source": search_url
        }

        photo_cache[tail] = {
            "time": now,
            "data": data
        }

        return jsonify(data)

    except Exception as e:
        print(f"Photo scrape error: {e}")
        return jsonify({"found": False})

@app.route("/heatmap_history")
def heatmap_history():
    range_value = request.args.get("range", "24h")
    category = request.args.get("category", "All")

    range_map = {
        "1h": "-1 hour",
        "24h": "-1 day",
        "7d": "-7 days",
        "30d": "-30 days"
    }

    since = range_map.get(range_value, "-1 day")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if category == "All":
        cursor.execute("""
            SELECT latitude, longitude, category
            FROM aircraft_positions
            WHERE seen_at >= datetime('now', ?)
              AND latitude IS NOT NULL
              AND longitude IS NOT NULL
        """, (since,))
    else:
        cursor.execute("""
            SELECT latitude, longitude, category
            FROM aircraft_positions
            WHERE seen_at >= datetime('now', ?)
              AND category = ?
              AND latitude IS NOT NULL
              AND longitude IS NOT NULL
        """, (since, category))

    rows = cursor.fetchall()
    conn.close()

    points = []

    for lat, lon, cat in rows:
        intensity = 0.5

        if cat == "Military":
            intensity = 1.0
        elif cat == "Commercial":
            intensity = 0.7
        elif cat == "Civilian":
            intensity = 0.6

        points.append([lat, lon, intensity])

    return jsonify(points)

@app.route("/aircraft/<icao_hex>/history")
def aircraft_history(icao_hex):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            MIN(seen_at),
            MAX(seen_at),
            COUNT(*),
            MAX(speed_knots),
            MAX(CAST(altitude_feet AS INTEGER))
        FROM aircraft_positions
        WHERE icao_hex = ?
    """, (icao_hex,))

    first_seen, last_seen, points, max_speed, max_altitude = cursor.fetchone()

    conn.close()

    if not first_seen:
        return jsonify({
            "found": False
        })

    first_dt = datetime.strptime(first_seen, "%Y-%m-%d %H:%M:%S")
    last_dt = datetime.strptime(last_seen, "%Y-%m-%d %H:%M:%S")

    duration_seconds = int((last_dt - first_dt).total_seconds())
    minutes = duration_seconds // 60
    seconds = duration_seconds % 60

    return jsonify({
        "found": True,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "time_in_area": f"{minutes}m {seconds}s",
        "track_points": points,
        "max_speed": round(max_speed, 1) if max_speed else "N/A",
        "max_altitude": max_altitude if max_altitude else "N/A"
    })

if __name__ == "__main__":
    fetch_thread = threading.Thread(
        target=fetch_aircraft_loop,
        daemon=True
    )

    fetch_thread.start()
    app.run(debug=True, use_reloader=False)