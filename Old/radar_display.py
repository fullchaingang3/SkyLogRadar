import tkinter as tk
import math
import sqlite3
from datetime import datetime

class RadarDisplay:
    def __init__(self, radius_miles, home_lat, home_lon):
        self.radius_miles = radius_miles
        self.home_lat = home_lat
        self.home_lon = home_lon

        self.sweep_angle = 0
        self.last_active_aircraft = {}
        self.sweep_line = None

        self.trails = {}
        self.max_trail_points = 5

        self.aircraft_click_zones = {}

        # MILITARY ALERTS
        self.alerted_military = set()
        self.military_alert_windows = {}

        # CREATE WINDOW FIRST
        self.root = tk.Tk()
        self.root.title("SkyLog Radar")

        # Recenter radar in window
        self.root.bind(
            "<Configure>",
            self.on_window_resize
        )

        # FRAME
        self.top_frame = tk.Frame(
            self.root,
            bg="black"
        )

        self.top_frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        # Create a three panel top bar
        self.left_panel = tk.Frame(self.top_frame, bg="black")
        self.left_panel.pack(side="left", expand=True, fill="both", anchor="n")

        self.middle_panel = tk.Frame(self.top_frame, bg="black")
        self.middle_panel.pack(side="left", expand=True, fill="both", anchor="n")

        self.right_panel = tk.Frame(self.top_frame, bg="black")
        self.right_panel.pack(side="right", expand=True, fill="both",anchor="n")


        # NOW create filter variables
        self.show_commercial = tk.BooleanVar(value=True)
        self.show_civilian = tk.BooleanVar(value=True)
        self.show_military = tk.BooleanVar(value=True)
        self.show_unknown = tk.BooleanVar(value=True)

        # NOW search variables
        self.search_text = tk.StringVar()
        self.highlight_aircraft = None
        self.focused_aircraft = None

        # Heat map
        self.show_heatmap = tk.BooleanVar(value=False)

        # NOW create filter frame
        # Search Box
        search_frame = tk.Frame(self.right_panel, bg="black")
        search_frame.pack(anchor="n", pady=(5, 8))

        tk.Label(
            search_frame,
            text="Search:",
            fg="white",
            bg="black"
        ).pack(side="left")

        tk.Entry(
            search_frame,
            textvariable=self.search_text,
            width=20
        ).pack(side="left")

        tk.Button(
            search_frame,
            text="Find",
            command=self.search_aircraft
        ).pack(side="left")

        tk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search
        ).pack(side="left")

        filter_frame = tk.Frame(self.right_panel, bg="black")
        filter_frame.pack(anchor="n", pady=(0, 8))

        tk.Checkbutton(
            filter_frame,
            text="Commercial",
            variable=self.show_commercial,
            fg="cyan",
            bg="black",
            selectcolor="black",
            command = self.refresh_display
        ).pack(side="left")

        tk.Checkbutton(
            filter_frame,
            text="Civilian",
            variable=self.show_civilian,
            fg="lime",
            bg="black",
            selectcolor="black",
            command = self.refresh_display
        ).pack(side="left")

        tk.Checkbutton(
            filter_frame,
            text="Military",
            variable=self.show_military,
            fg="red",
            bg="black",
            selectcolor="black",
            command = self.refresh_display
        ).pack(side="left")

        tk.Checkbutton(
            filter_frame,
            text="Unknown",
            variable=self.show_unknown,
            fg="yellow",
            bg="black",
            selectcolor="black",
            command = self.refresh_display
        ).pack(side="left")

        # Heat map checkboxes
        tk.Checkbutton(
            filter_frame,
            text="Heat Map",
            variable=self.show_heatmap,
            fg="orange",
            bg="black",
            selectcolor="black",
            command=self.refresh_display
        ).pack(side="left")

        # Zoom button frame
        button_frame = tk.Frame(self.right_panel, bg = "black")
        button_frame.pack(anchor="n", pady = (0, 5))

        # Zoom
        tk.Button(
            button_frame,
            text="Zoom In",
            command=self.zoom_in
        ).pack(side="left", padx=3)

        tk.Button(
            button_frame,
            text="Zoom Out",
            command=self.zoom_out
        ).pack(side="left", padx=3)

        tk.Button(
            button_frame,
            text="Reset View",
            command=self.reset_view
        ).pack(side="left", padx=3)

        # Stats
        self.stats_label = tk.Label(
            self.left_panel,
            text="Loading stats...",
            fg="white",
            bg="black",
            font=("Consolas", 10),
            justify="left",
            anchor="w"
        )

        self.stats_label.pack(anchor="n")

        # Military Alerts Panel
        self.military_alerts_label = tk.Label(
            self.middle_panel,
            text="MILITARY ALERTS\n====================\nNone active",
            fg="red",
            bg="black",
            font=("Consolas", 10),
            justify="left",
            anchor="w"
        )

        self.military_alerts_label.pack(anchor="n")

        # Radar canvas
        if self.radius_miles <= 10:
            self.canvas_size = 800
        elif self.radius_miles <= 25:
            self.canvas_size = 950
        elif self.radius_miles <= 50:
            self.canvas_size = 1100
        else:
            self.canvas_size = 1300

        self.center = self.canvas_size // 2
        self.max_radius_pixels = (self.canvas_size // 2) - 60

        # Zoom
        self.default_max_radius_pixels = self.max_radius_pixels
        self.zoom_level = 1.0

        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill="both", expand=True)

        v_scroll = tk.Scrollbar(
            canvas_frame,
            orient="vertical"
        )

        v_scroll.pack(
            side="right",
            fill="y"
        )

        h_scroll = tk.Scrollbar(
            canvas_frame,
            orient="horizontal"
        )

        h_scroll.pack(
            side="bottom",
            fill="x"
        )

        self.canvas = tk.Canvas(
            canvas_frame,
            width=1000,
            height=800,
            bg="black",
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )

        self.canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        v_scroll.config(
            command=self.canvas.yview
        )

        h_scroll.config(
            command=self.canvas.xview
        )

        self.virtual_size = 3000

        self.canvas.configure(
            scrollregion=(
                0,
                0,
                self.virtual_size,
                self.virtual_size
            )
        )

        self.center = self.virtual_size // 2

        self.root.after(
            100,
            self.center_radar
        )

        self.canvas.bind("<Button-1>", self.handle_click)

        self.root.after(50, self.animate_sweep)

    # Will be moving to own file eventually
    def haversine_miles(self, lat1, lon1, lat2, lon2):
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

    # Will be moving to own file eventually
    def calculate_bearing(self, lat1, lon1, lat2, lon2):
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

    # Recenter radar
    def on_window_resize(self, event):

        if event.widget == self.root:
            self.root.after(
                50,
                self.center_radar
            )

    # Military Alerts Panel
    def update_military_alert_panel(self):
        military_aircraft = [
            aircraft
            for aircraft in self.last_active_aircraft.values()
            if aircraft.get("category") == "Military"
        ]

        if not military_aircraft:
            self.military_alerts_label.config(
                text="MILITARY ALERTS\n====================\nNone active"
            )
            return

        lines = [
            "MILITARY ALERTS",
            "===================="
        ]

        military_aircraft.sort(
            key=lambda aircraft: aircraft.get(
                "distance_miles",
                999
            )
        )

        for aircraft in military_aircraft[:8]:
            callsign = aircraft.get("callsign") or aircraft.get("icao_hex")
            aircraft_type = aircraft.get("aircraft_type", "Unknown")
            distance = aircraft.get("distance_miles", 0)
            speed = aircraft.get("speed_knots", "Unknown")

            window_width = self.root.winfo_width()
            use_long_format = window_width >= 1400

            if use_long_format:
                lines.append(
                    f"{callsign} | {aircraft_type} | {distance:.1f} mi | {speed} kt"
                )
            else:
                lines.append(
                    f"{callsign[:8]:<8} {distance:>5.1f} mi"
                )

        self.military_alerts_label.config(
            text="\n".join(lines)
        )

    # Search feature
    def search_aircraft(self):

        query = self.search_text.get().upper().strip()

        if not query:
            self.clear_search()
            return

        self.highlight_aircraft = None

        for aircraft in self.last_active_aircraft.values():

            callsign = (
                    aircraft.get("callsign") or ""
            ).upper()

            tail = (
                    aircraft.get("tail_number") or ""
            ).upper()

            aircraft_type = (
                    aircraft.get("aircraft_type") or ""
            ).upper()

            owner = (
                    aircraft.get("owner_operator") or ""
            ).upper()

            if (
                    query in callsign
                    or query in tail
                    or query in aircraft_type
                    or query in owner
            ):
                self.highlight_aircraft = aircraft.get("icao_hex")

                break

        self.refresh_display()

    # Zoom
    def zoom_in(self):
        self.zoom_level *= 1.2
        self.max_radius_pixels = int(
            self.default_max_radius_pixels * self.zoom_level
        )
        self.refresh_display()

    def zoom_out(self):
        self.zoom_level *= 0.8

        if self.zoom_level < 0.25:
            self.zoom_level = 0.25

        self.max_radius_pixels = int(
            self.default_max_radius_pixels * self.zoom_level
        )

        self.refresh_display()

    def reset_view(self):

        self.zoom_level = 1.0

        self.max_radius_pixels = (
            self.default_max_radius_pixels
        )

        self.refresh_display()

        self.center_radar()

    # Stats
    def update_statistics(self):
        conn = sqlite3.connect("../skylog.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(DISTINCT icao_hex)
            FROM aircraft_positions
            WHERE seen_at >= date('now', 'localtime')
        """)
        aircraft_today = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT icao_hex)
            FROM aircraft_positions
            WHERE category = 'Military'
              AND seen_at >= date('now', 'localtime')
        """)
        military_today = cursor.fetchone()[0]

        cursor.execute("""
            SELECT MIN(closest_distance_miles)
            FROM aircraft_passes
            WHERE date(last_seen) = date('now', "localtime")
        """)
        closest_pass = cursor.fetchone()[0]

        cursor.execute("""
            SELECT MAX(speed_knots)
            FROM aircraft_positions
            WHERE date(seen_at) = date('now', "localtime")
        """)
        fastest = cursor.fetchone()[0]

        cursor.execute("""
            SELECT MAX(CAST(altitude_feet AS INTEGER))
            FROM aircraft_positions
            WHERE date(seen_at) = date('now', "localtime")
              AND altitude_feet != 'ground'
        """)
        highest = cursor.fetchone()[0]

        conn.close()

        military_active = sum(
            1
            for aircraft in self.last_active_aircraft.values()
            if aircraft.get("category") == "Military"
        )

        self.stats_label.config(
            text=(
                "SKYLOG STATISTICS\n"
                "====================\n"
                f"Aircraft Today : {aircraft_today}\n"
                f"Military Today : {military_today}\n"
                f"Military Active: {military_active}\n"
                f"Closest Pass   : {round(closest_pass, 2) if closest_pass else 'N/A'} mi\n"
                f"Fastest        : {round(fastest, 1) if fastest else 'N/A'} kt\n"
                f"Highest        : {highest if highest else 'N/A'} ft\n"
                f"Zoom Level     : {self.zoom_level:.2f}x"
            )
        )

    # Heat map
    def draw_heatmap(self):
        if not self.show_heatmap.get():
            return

        conn = sqlite3.connect("../skylog.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT latitude, longitude
            FROM aircraft_positions
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL
            ORDER BY seen_at DESC
            LIMIT 1500
        """)

        rows = cursor.fetchall()
        conn.close()

        heat_points = {}

        for lat, lon in rows:
            distance = self.haversine_miles(
                self.home_lat,
                self.home_lon,
                lat,
                lon
            )

            if distance > self.radius_miles:
                continue

            bearing = self.calculate_bearing(
                self.home_lat,
                self.home_lon,
                lat,
                lon
            )

            x, y = self.latlon_to_radar_xy(distance, bearing)

            grid_size = 18 if self.radius_miles <= 25 else 12

            grid_x = round(x / grid_size) * grid_size
            grid_y = round(y / grid_size) * grid_size

            key = (grid_x, grid_y)

            heat_points[key] = heat_points.get(key, 0) + 1

        for (x, y), count in heat_points.items():
            radius = min(18, 3 + count * 0.6)

            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill="orange",
                outline=""
            )

    # Refresh Page on click
    def refresh_display(self):
        self.update_radar(self.last_active_aircraft)

    def should_show_aircraft(self, category):
        if category == "Commercial":
            return self.show_commercial.get()

        if category == "Civilian":
            return self.show_civilian.get()

        if category == "Military":
            return self.show_military.get()

        return self.show_unknown.get()

    def update_radar(self, active_aircraft):
        self.canvas.delete("all")
        self.aircraft_click_zones = {}
        self.last_active_aircraft = active_aircraft
        self.draw_radar_background()
        # Heat map
        self.draw_heatmap()
        for aircraft in active_aircraft.values():
            lat = aircraft.get("current_latitude")
            lon = aircraft.get("current_longitude")

            if lat is None or lon is None:
                continue

            x, y = self.latlon_to_radar_xy(
                aircraft["distance_miles"],
                aircraft["bearing_degrees"]
            )

            icao_hex = aircraft.get("icao_hex")

            if icao_hex:

                if icao_hex not in self.trails:
                    self.trails[icao_hex] = []

                self.trails[icao_hex].append((lat, lon))

                if len(self.trails[icao_hex]) > self.max_trail_points:
                    self.trails[icao_hex].pop(0)

            category = aircraft.get("category", "Unknown")
            callsign = aircraft.get("callsign") or aircraft.get("icao_hex")

            if not self.should_show_aircraft(category):
                continue

            if category == "Military":
                icao_hex = aircraft.get("icao_hex")

                if icao_hex and icao_hex not in self.alerted_military:
                    self.alerted_military.add(icao_hex)
                    self.show_military_alert(callsign, aircraft)

            color = self.get_color(category)

            if icao_hex in self.trails and len(self.trails[icao_hex]) >= 2:

                points = []

                for trail_lat, trail_lon in self.trails[icao_hex]:
                    trail_distance = self.haversine_miles(
                        self.home_lat,
                        self.home_lon,
                        trail_lat,
                        trail_lon
                    )

                    trail_bearing = self.calculate_bearing(
                        self.home_lat,
                        self.home_lon,
                        trail_lat,
                        trail_lon
                    )

                    trail_x, trail_y = self.latlon_to_radar_xy(
                        trail_distance,
                        trail_bearing
                    )

                    points.extend([trail_x, trail_y])

                trail_width = 2

                if icao_hex == self.focused_aircraft:
                    trail_width = 5

                self.canvas.create_line(
                    points,
                    fill=color,
                    width=trail_width,
                    smooth=True
                )

            if icao_hex == self.highlight_aircraft:
                self.canvas.create_oval(
                    x - 15,
                    y - 15,
                    x + 15,
                    y + 15,
                    outline="white",
                    width=3
                )

            heading = aircraft.get("heading_degrees", 0) or 0

            if icao_hex == self.focused_aircraft:
                self.canvas.create_oval(
                    x - 18,
                    y - 18,
                    x + 18,
                    y + 18,
                    outline="white",
                    width=3
                )

            self.draw_airplane_icon(
                x,
                y,
                heading,
                color
            )

            self.aircraft_click_zones[icao_hex] = {
                "x": x,
                "y": y,
                "aircraft": aircraft
            }

            altitude = aircraft.get("altitude_feet", "Unknown")
            speed = aircraft.get("speed_knots", "Unknown")
            distance = aircraft.get("distance_miles", 0)
            direction = aircraft.get("direction", "Unknown")
            aircraft_type = aircraft.get("aircraft_type", "")

            origin = aircraft.get("origin_airport", "")
            destination = aircraft.get("destination_airport", "")
            route = ""

            if origin or destination:
                route = f"{origin}→{destination}"

            label = (
                f"{callsign}\n"
                f"{category} | {aircraft_type}\n"
                f"{distance:.1f} mi | {speed} kt\n"
                f"{route}"
            )

            self.canvas.create_text(
                x + 10,
                y,
                text=label,
                fill=color,
                anchor="w",
                font=("Arial", 8)
            )

        self.update_statistics()
        self.close_inactive_military_alerts(active_aircraft)
        self.update_military_alert_panel()

    def center_radar(self):

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        self.canvas.xview_moveto(
            (self.center - canvas_width / 2)
            / self.virtual_size
        )

        self.canvas.yview_moveto(
            (self.center - canvas_height / 2)
            / self.virtual_size
        )

    # Airplane icon
    def draw_airplane_icon(self, x, y, heading, color):
        size = 10

        angle = math.radians(heading)

        nose = (
            x + size * math.sin(angle),
            y - size * math.cos(angle)
        )

        left_wing = (
            x + size * 0.7 * math.sin(angle - 2.3),
            y - size * 0.7 * math.cos(angle - 2.3)
        )

        right_wing = (
            x + size * 0.7 * math.sin(angle + 2.3),
            y - size * 0.7 * math.cos(angle + 2.3)
        )

        tail = (
            x - size * 0.8 * math.sin(angle),
            y + size * 0.8 * math.cos(angle)
        )

        self.canvas.create_polygon(
            nose[0], nose[1],
            left_wing[0], left_wing[1],
            tail[0], tail[1],
            right_wing[0], right_wing[1],
            fill=color,
            outline=color
        )

    # Flight history over our location
    def get_aircraft_history(self, tail_number, callsign):
        conn = sqlite3.connect("../skylog.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                COUNT(*),
                MIN(closest_distance_miles),
                MAX(last_seen),
                AVG(speed_knots)
            FROM aircraft_passes
            WHERE tail_number = ?
               OR callsign = ?
        """, (tail_number, callsign))

        result = cursor.fetchone()
        conn.close()

        return result

    def show_military_alert(self, callsign, aircraft):
        alert = tk.Toplevel(self.root)
        icao_hex = aircraft.get("icao_hex")
        alert.title("Military Aircraft Alert")
        alert.geometry("450x250")
        alert.configure(bg="black")

        aircraft_type = aircraft.get("aircraft_type", "Unknown")
        tail = aircraft.get("tail_number", "Unknown")
        distance = aircraft.get("distance_miles", 0)
        altitude = aircraft.get("altitude_feet", "Unknown")
        speed = aircraft.get("speed_knots", "Unknown")
        direction = aircraft.get("direction", "Unknown")
        timestamp = datetime.now().strftime(
            "%Y-%m-%d %I:%M:%S %p"
        )

        message = (
            f"MILITARY AIRCRAFT DETECTED\n"
            f"{timestamp}\n\n"
            f"Callsign: {callsign}\n"
            f"Tail: {tail}\n"
            f"Type: {aircraft_type}\n"
            f"Distance: {distance:.1f} mi\n"
            f"Altitude: {altitude}\n"
            f"Speed: {speed} kt\n"
            f"Direction: {direction}\n\n"
        )

        label = tk.Label(
            alert,
            text=message,
            fg="red",
            bg="black",
            font=("Consolas", 11, "bold"),
            justify="left"
        )

        label.pack(padx=15, pady=15)

        with open(
                "../military_alerts.log",
                "a",
                encoding="utf-8"
        ) as logfile:
            logfile.write(
                f"{timestamp} | "
                f"{callsign} | "
                f"{aircraft_type} | "
                f"{distance:.1f} mi | "
                f"{altitude} ft | "
                f"{speed} kt\n"
            )

        if icao_hex:
            self.military_alert_windows[icao_hex] = alert

        self.root.bell()

    def close_inactive_military_alerts(self, active_aircraft):
        active_military_hexes = set()

        for aircraft in active_aircraft.values():
            if aircraft.get("category") == "Military":
                active_military_hexes.add(aircraft.get("icao_hex"))

        for icao_hex in list(self.military_alert_windows.keys()):
            if icao_hex not in active_military_hexes:
                alert_window = self.military_alert_windows.pop(icao_hex)

                if alert_window.winfo_exists():
                    alert_window.destroy()

    def clear_focused_aircraft(self):
        self.focused_aircraft = None
        self.refresh_display()

    def handle_click(self, event):
        click_x = self.canvas.canvasx(event.x)
        click_y = self.canvas.canvasy(event.y)

        clicked_aircraft = False

        for icao_hex, data in self.aircraft_click_zones.items():
            x = data["x"]
            y = data["y"]

            distance_from_click = math.sqrt(
                (click_x - x) ** 2 + (click_y - y) ** 2
            )

            if distance_from_click <= 25:
                clicked_aircraft = True

                self.focused_aircraft = icao_hex

                self.refresh_display()

                self.show_aircraft_details(
                    data["aircraft"]
                )

                break

        if not clicked_aircraft:
            self.clear_focused_aircraft()

    def show_aircraft_details(self, aircraft):
        details = tk.Toplevel(self.root)
        details.protocol(
            "WM_DELETE_WINDOW",
            lambda: (
                self.clear_focused_aircraft(),
                details.destroy()
            )
        )
        details.title("Aircraft Details")
        details.geometry("800x800")
        details.resizable(True, True)
        details.configure(bg="black")

        callsign = aircraft.get("callsign") or aircraft.get("icao_hex", "Unknown")
        category = aircraft.get("category", "Unknown")
        aircraft_type = aircraft.get("aircraft_type", "Unknown")
        tail_number = aircraft.get("tail_number", "Unknown")
        distance = aircraft.get("distance_miles", 0)
        altitude = aircraft.get("altitude_feet", "Unknown")
        speed = aircraft.get("speed_knots", "Unknown")
        direction = aircraft.get("direction", "Unknown")
        heading = aircraft.get("heading_degrees", "Unknown")
        closest = aircraft.get("closest_distance_miles", 0)
        history = self.get_aircraft_history(tail_number, callsign)

        pass_count = history[0] or 0
        best_distance = history[1]
        last_seen = history[2]
        avg_speed = history[3]
        origin = aircraft.get("origin_airport", "Unknown")
        destination = aircraft.get("destination_airport", "Unknown")
        description = aircraft.get("description", "Unknown")
        owner_operator = aircraft.get("owner_operator", "Unknown")
        year = aircraft.get("year", "Unknown")
        squawk = aircraft.get("squawk", "Unknown")

        message = (
            f"{callsign}\n\n"
            f"Category: {category}\n"
            f"Tail Number: {tail_number}\n"
            f"Aircraft Type: {aircraft_type}\n"
            f"Description: {description}\n"
            f"Owner/Operator: {owner_operator}\n"
            f"Year: {year}\n"
            f"Squawk: {squawk}\n\n"
            "Current Data:\n"
            f"Current Distance: {distance:.1f} mi\n"
            f"Closest So Far: {closest:.1f} mi\n"
            f"Altitude: {altitude} ft\n"
            f"Speed: {speed} kt\n"
            f"Heading: {heading}°\n"
            f"Direction: {direction}\n"
            f"Logged Passes: {pass_count}\n\n"
            "Historical Data:\n"
            f"Best Closest Pass: {round(best_distance,2) if best_distance else 'N/A'} mi\n"
            f"Last Logged: {last_seen if last_seen else 'N/A'}\n"
            f"Average Speed: {round(avg_speed, 1) if avg_speed else 'N/A'} kt\n\n"
        )

        label = tk.Label(
            details,
            text=message,
            fg="white",
            bg="black",
            font=("Consolas", 11),
            justify="left"
        )
        details.geometry("800x800")
        label.pack(padx=20, pady=20, anchor="w")

        # Flight Replay
        tk.Button(
            details,
            text="Replay Flight",
            command=lambda:
            self.replay_flight(
                aircraft["icao_hex"]
            )
        ).pack(
            pady=10
        )

    # Clear search
    def clear_search(self):
        self.search_text.set("")
        self.highlight_aircraft = None
        self.focused_aircraft = None
        self.refresh_display()

    # Flight Replay History
    def get_flight_positions(self, icao_hex):

        conn = sqlite3.connect("../skylog.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                latitude,
                longitude,
                heading_degrees
            FROM aircraft_positions
            WHERE icao_hex = ?
            ORDER BY seen_at
        """, (icao_hex,))

        results = cursor.fetchall()

        conn.close()

        return results

    # Flight replay engine
    def replay_flight(self, icao_hex):

        positions = self.get_flight_positions(
            icao_hex
        )

        if not positions:
            return

        self.replay_positions = positions
        self.replay_index = 0

        self.animate_replay()

    # Create animation
    def animate_replay(self):

        if self.replay_index >= len(
                self.replay_positions
        ):
            return

        lat, lon, heading = (
            self.replay_positions[
                self.replay_index
            ]
        )

        distance = self.haversine_miles(
            self.home_lat,
            self.home_lon,
            lat,
            lon
        )

        bearing = self.calculate_bearing(
            self.home_lat,
            self.home_lon,
            lat,
            lon
        )

        x, y = self.latlon_to_radar_xy(
            distance,
            bearing
        )

        self.canvas.create_oval(
            x - 8,
            y - 8,
            x + 8,
            y + 8,
            outline="white",
            width=3
        )

        self.replay_index += 1

        self.root.after(
            100,
            self.animate_replay
        )

    def animate_sweep(self):
        self.sweep_angle = (self.sweep_angle + 3) % 360

        if self.sweep_line is not None:
            self.canvas.delete(self.sweep_line)

        sweep_length = self.max_radius_pixels
        angle = math.radians(self.sweep_angle)

        x = self.center + sweep_length * math.sin(angle)
        y = self.center - sweep_length * math.cos(angle)

        self.sweep_line = self.canvas.create_line(
            self.center,
            self.center,
            x,
            y,
            fill="#00ff00",
            width=2
        )

        self.root.after(50, self.animate_sweep)

    def draw_radar_background(self):
        # Radar range rings
        ring_percents = [0.25, 0.5, 0.75, 1.0]

        for percent in ring_percents:
            r = self.max_radius_pixels * percent
            miles = self.radius_miles * percent

            self.canvas.create_oval(
                self.center - r,
                self.center - r,
                self.center + r,
                self.center + r,
                outline="#1f3b1f"
            )

            # Ring distance label
            label_angle = math.radians(45)

            label_x = self.center + (r * math.cos(label_angle))
            label_y = self.center - (r * math.sin(label_angle))

            self.canvas.create_text(
                label_x + 12,
                label_y - 12,
                text=f"{miles:.0f} mi",
                fill="#888888",
                font=("Arial", 9, "bold")
            )

        # Cross lines
        self.canvas.create_line(
            self.center,
            self.center - self.max_radius_pixels,
            self.center,
            self.center + self.max_radius_pixels,
            fill="light green"
        )

        self.canvas.create_line(
            self.center - self.max_radius_pixels,
            self.center,
            self.center + self.max_radius_pixels,
            self.center,
            fill="light green"
        )

        # Direction labels
        label_offset = self.max_radius_pixels + 35

        self.canvas.create_text(
            self.center,
            self.center - label_offset,
            text="N",
            fill="green",
            font=("Arial", 16, "bold")
        )

        self.canvas.create_text(
            self.center,
            self.center + label_offset,
            text="S",
            fill="green",
            font=("Arial", 16, "bold")
        )

        self.canvas.create_text(
            self.center - label_offset,
            self.center,
            text="W",
            fill="green",
            font=("Arial", 16, "bold")
        )

        self.canvas.create_text(
            self.center + label_offset,
            self.center,
            text="E",
            fill="green",
            font=("Arial", 16, "bold")
        )

        # You
        self.canvas.create_oval(
            self.center - 6,
            self.center - 6,
            self.center + 6,
            self.center + 6,
            fill="white",
            outline="white"
        )

        self.canvas.create_text(
            self.center,
            self.center + 20,
            text="YOU",
            fill="white",
            font=("Arial", 10, "bold")
        )

        # Legend
        self.canvas.create_text(
            15,
            15,
            text="Commercial = Cyan | Civilian = Lime | Military = Red | Unknown = Yellow",
            fill="white",
            anchor="nw",
            font=("Arial", 9)
        )

    def latlon_to_radar_xy(self, distance_miles, bearing_degrees):
        distance_ratio = distance_miles / self.radius_miles
        pixel_distance = distance_ratio * self.max_radius_pixels

        angle = math.radians(bearing_degrees)

        x = self.center + pixel_distance * math.sin(angle)
        y = self.center - pixel_distance * math.cos(angle)

        return x, y

    def get_color(self, category):
        if category == "Commercial":
            return "cyan"
        if category == "Civilian":
            return "lime"
        if category == "Military":
            return "red"
        return "yellow"

