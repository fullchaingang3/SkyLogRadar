import csv
import os
import requests
import sqlite3
import math
from datetime import datetime
from Old.radar_display import RadarDisplay

# Change these to match your location
MY_LAT = 36.31344
MY_LON = -82.35347

# User selects radius in miles
# RADIUS_MILES = 15
VALID_RADII = [5, 10, 25, 50, 100, 250]

CSV_FILE = "../aircraft_log.csv"

def append_to_csv(record):
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, "a", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "ICAO Hex",
                "Callsign",
                "Tail Number",
                "Aircraft Type",
                "First Seen",
                "Last Seen",
                "Closest Distance Miles",
                "Closest Latitude",
                "Closest Longitude",
                "Altitude Feet",
                "Speed Knots",
                "Heading Degrees",
                "Direction"
            ])

        writer.writerow([
            record["icao_hex"],
            record["callsign"],
            record["tail_number"],
            record["aircraft_type"],
            record["first_seen"],
            record["last_seen"],
            round(record["closest_distance_miles"], 2),
            record["closest_latitude"],
            record["closest_longitude"],
            record["altitude_feet"],
            record["speed_knots"],
            record["heading_degrees"],
            record["direction"]
        ])

def choose_radius():
    print("Choose tracking radius:")
    for radius in VALID_RADII:
        print(f"{radius} miles")

    while True:
        choice = input("Enter 5, 10, 25, 50, 100, 250: ").strip()

        try:
            radius = int(choice)

            if radius in VALID_RADII:
                return radius

            print("Please choose one of the listed options.")

        except ValueError:
            print("Please enter a number.")

# Convert to NM
# RADIUS_NM = RADIUS_MILES * 0.868976
RADIUS_NM = None

POLL_SECONDS = 10
DB_NAME = "skylog.db"

# API_URL = f"https://api.airplanes.live/v2/point/{MY_LAT}/{MY_LON}/{RADIUS_NM:.2f}"
API_URL = None

print(API_URL)
print()
active_aircraft = {}

print("Creating database.....")
def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
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
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aircraft_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            icao_hex TEXT,
            callsign TEXT,
            tail _number TEXT,
            latitude REAL,
            longitude REAL,
            altitude_feet TEXT,
            speed_knots REAL,
            heading_degrees REAL,
            distance_miles REAL,
            seen_at TEXT
        )
    """)
    conn.commit()
    conn.close()
print("Database setup complete.")
print()

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
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius_miles * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    diff_lon = math.radians(lon2 - lon1)

    x = math.sin(diff_lon) * math.cos(lat2)

    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(diff_lon)
    )

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360

def classify_aircraft(aircraft):
    callsign = (aircraft.get("flight") or "").strip().upper()
    tail_number = (aircraft.get("r") or "").strip().upper()
    aircraft_type = (aircraft.get("t") or "").strip().upper()
    icao_hex = (aircraft.get("hex") or "").strip().upper()

    commercial_prefixes = [
        "DAL", "AAL", "UAL", "SWA", "FFT", "JBU", "ASA", "NKS",
        "SKW", "ENY", "EDV", "RPA", "PDT", "AWI", "ASH", "UPS",
        "FDX", "GTI", "ABX"
    ]

    military_callsigns = [
        "RCH", "REACH", "PAT", "SAM", "SPAR", "VENUS", "KING",
        "NAVY", "MARINE", "ARMY", "AF", "GOLD", "HOIST", "JEDI",
        "ROGUE", "MOOSE", "TITAN", "LION", "DECOY", "BRAVE",
        "EVAC", "RESCUE"
    ]

    military_type_prefixes = [
        "C17", "C5", "C130", "C30J", "KC", "F15", "F16", "F18",
        "F22", "F35", "A10", "B1", "B2", "B52", "T38", "T6",
        "T1", "E3", "E4", "E6", "E8", "P8", "P3", "U2", "RQ",
        "MQ", "UH", "HH", "CH", "AH"
    ]

    military_hex_prefixes = [
        "AE"  # Many U.S. military aircraft use AE-prefixed ICAO hex codes
    ]

    if any(callsign.startswith(prefix) for prefix in military_callsigns):
        return "Military"

    if any(aircraft_type.startswith(prefix) for prefix in military_type_prefixes):
        return "Military"

    if any(icao_hex.startswith(prefix) for prefix in military_hex_prefixes):
        return "Military"

    if any(callsign.startswith(prefix) for prefix in commercial_prefixes):
        return "Commercial"

    if aircraft_type.startswith(("A3", "A2", "B7", "B38M", "B39M", "E17", "E19", "CRJ")):
        return "Commercial"

    if tail_number.startswith("N"):
        return "Civilian"

    return "Unknown"

def heading_to_direction(heading):
    if heading is None:
        return "Unknown"

    directions = [
        "North", "Northeast", "East", "Southeast",
        "South", "Southwest", "West", "Northwest"
    ]

    index = round(heading / 45) % 8
    return directions[index]


def fetch_aircraft():
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()

    data = response.json()

    aircraft = data.get("aircraft", data.get("ac", []))

    '''if aircraft:
        print("\nAircraft Fields Available:")

        for key in sorted(aircraft[0].keys()):
            print(key)'''


    return aircraft



# Log the closest that the plane passes.
def log_aircraft_pass(record):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO aircraft_passes (
            icao_hex,
            callsign,
            tail_number,
            aircraft_type,
            first_seen,
            last_seen,
            closest_distance_miles,
            closest_latitude,
            closest_longitude,
            altitude_feet,
            speed_knots,
            heading_degrees,
            direction
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record["icao_hex"],
        record["callsign"],
        record["tail_number"],
        record["aircraft_type"],
        record["first_seen"],
        record["last_seen"],
        record["closest_distance_miles"],
        record["closest_latitude"],
        record["closest_longitude"],
        record["altitude_feet"],
        record["speed_knots"],
        record["heading_degrees"],
        record["direction"]
    ))

    conn.commit()
    conn.close()

# Historical tracking
def log_aircraft_position(record):
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
        record["current_latitude"],
        record["current_longitude"],
        record["altitude_feet"],
        record["speed_knots"],
        record["heading_degrees"],
        record["distance_miles"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        record["category"]
    ))

    conn.commit()
    conn.close()

def update_tracking(aircraft_list):
    global active_aircraft

    seen_now = set()

    for aircraft in aircraft_list:
        icao_hex = aircraft.get("hex")

        lat = aircraft.get("lat")
        lon = aircraft.get("lon")

        if not icao_hex or lat is None or lon is None:
            continue

        distance = haversine_miles(MY_LAT, MY_LON, lat, lon)
        bearing = calculate_bearing(MY_LAT, MY_LON, lat, lon)

        if distance > RADIUS_MILES:
            continue

        seen_now.add(icao_hex)

        callsign = aircraft.get("flight", "").strip()
        tail_number = aircraft.get("r", "")
        description = aircraft.get("desc", "")
        owner_operator = aircraft.get("ownOp", "")
        year = aircraft.get("year", "")
        squawk = aircraft.get("squawk", "")
        aircraft_type = aircraft.get("t", "")
        origin_airport = aircraft.get("orig", aircraft.get("from", ""))
        destination_airport = aircraft.get("dest", aircraft.get("to", ""))
        altitude = aircraft.get("alt_baro", "")
        speed = aircraft.get("gs")
        heading = aircraft.get("track")
        direction = heading_to_direction(heading)
        category = classify_aircraft(aircraft)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if icao_hex not in active_aircraft:
            active_aircraft[icao_hex] = {
                "icao_hex": icao_hex,
                "callsign": callsign,
                "tail_number": tail_number,
                "aircraft_type": aircraft_type,
                "first_seen": now,
                "last_seen": now,
                "description": description,
                "owner_operator": owner_operator,
                "year": year,
                "squawk": squawk,
                "closest_distance_miles": distance,
                "closest_latitude": lat,
                "closest_longitude": lon,
                "altitude_feet": altitude,
                "speed_knots": speed,
                "heading_degrees": heading,
                "origin_airport": origin_airport,
                "destination_airport": destination_airport,
                "direction": direction,
                "category": category,
                "current_latitude": lat,
                "current_longitude": lon,
                "distance_miles": distance,
                "bearing_degrees": bearing
            }

            print(f"Started tracking {category} | {callsign or icao_hex} - {distance:.2f} miles away")

        else:
            record = active_aircraft[icao_hex]
            record["last_seen"] = now
            record["altitude_feet"] = altitude
            record["speed_knots"] = speed
            record["heading_degrees"] = heading
            record["direction"] = direction
            record["description"] = description
            record["owner_operator"] = owner_operator
            record["year"] = year
            record["squawk"] = squawk
            record["current_latitude"] = lat
            record["current_longitude"] = lon
            record["distance_miles"] = distance
            record["bearing_degrees"] = bearing
            record["category"] = category
            log_aircraft_position(record)
            record["origin_airport"] = origin_airport
            record["destination_airport"] = destination_airport

            if distance < record["closest_distance_miles"]:
                record["closest_distance_miles"] = distance
                record["closest_latitude"] = lat
                record["closest_longitude"] = lon

            print(
                f"Tracking {category} | "
                f"{callsign or icao_hex} | "
                f"{distance:.2f} mi | "
                f"Closest: {record['closest_distance_miles']:.2f} mi | "
                f"{speed} knots | {direction}"
            )

    aircraft_to_log = []

    for icao_hex in list(active_aircraft.keys()):
        if icao_hex not in seen_now:
            aircraft_to_log.append(icao_hex)

    for icao_hex in aircraft_to_log:
        record = active_aircraft.pop(icao_hex)
        log_aircraft_pass(record)
        append_to_csv(record)
        print(f"Total logged passes: {count_logged_passes()}")

        print(
            f"Logged {record['callsign'] or record['icao_hex']} | "
            f"Closest point: {record['closest_distance_miles']:.2f} miles"
        )

def count_positions():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM aircraft_positions"
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count

def count_logged_passes():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM aircraft_passes")
    count = cursor.fetchone()[0]

    conn.close()
    return count

def print_category_counts():
    counts = {
        "Commercial": 0,
        "Civilian": 0,
        "Military": 0,
        "Unknown": 0
    }

    for record in active_aircraft.values():
        category = record.get("category", "Unknown")

        if category not in counts:
            counts[category] = 0

        counts[category] += 1

    print()
    print("Aircraft Currently Within Range")
    print(f"Commercial: {counts['Commercial']}")
    print(f"Civilian:   {counts['Civilian']}")
    print(f"Military:   {counts['Military']}")
    print(f"Unknown:    {counts['Unknown']}")
    print()

def refresh_aircraft(radar):
    try:
        aircraft = fetch_aircraft()
        print(f"API returned {len(aircraft)} aircraft")

        update_tracking(aircraft)
        print(
            f"Position records: {count_positions()}"
        )
        radar.update_radar(active_aircraft)

        print(f"Currently tracking {len(active_aircraft)} aircraft")
        print_category_counts()
        print("-" * 50)

    except Exception as e:
        print(f"Error: {e}")

    radar.root.after(POLL_SECONDS * 1000, lambda: refresh_aircraft(radar))

def main():
    global RADIUS_MILES, RADIUS_NM, API_URL

    RADIUS_MILES = choose_radius()
    RADIUS_NM = RADIUS_MILES * 0.868976
    API_URL = f"https://api.airplanes.live/v2/point/{MY_LAT}/{MY_LON}/{RADIUS_NM:.2f}"

    print("Creating database...")
    setup_database()
    print("Database setup complete.")

    print("SkyLog Radar Console Started")
    print(f"Location: {MY_LAT}, {MY_LON}")
    print(f"Radius: {RADIUS_MILES} miles")
    print("Close radar window to stop.\n")

    radar = RadarDisplay(RADIUS_MILES, MY_LAT, MY_LON)

    refresh_aircraft(radar)

    radar.root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping SkyLog Radar.")