/* ------------------------------------------------------------------
   Object: DOM element lookup helper
------------------------------------------------------------------ */
const $ = (id) => document.getElementById(id);

/* ------------------------------------------------------------------
   Object: App runtime state
------------------------------------------------------------------ */
const state = {
            aircraftLabels: {},
            aircraftMarkers: {},
            aircraftTrailLines: {},
            aircraftTrails: {},
            alertedFavorites: new Set(),
            alertedMilitary: new Set(),
            alertHistory: new Set(),
            currentSort: "distance",
            favoriteAircraft: new Set(),
            focusedAircraft: null,
            heatLayer: null,
            lastPlanes: [],
            maxTrailPoints: 20,
            missionMode: false,
            notifications: [],
            sortAscending: true,
            sweepAngle: 0,
            sweepLine: null,
            updatesPaused: false,
        };

/* ------------------------------------------------------------------
   Object: Leaflet map
------------------------------------------------------------------ */
const map = L.map("map").setView([config.homeLat, config.homeLon], 9);

/* ------------------------------------------------------------------
   Object: OpenStreetMap tile layer
------------------------------------------------------------------ */
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "© OpenStreetMap contributors",
}).addTo(map);

/* ------------------------------------------------------------------
   Object: Home marker
------------------------------------------------------------------ */
L.marker([config.homeLat, config.homeLon])
    .addTo(map)
    .bindPopup("Your Location");

/* ------------------------------------------------------------------
   Object: Radius circle
------------------------------------------------------------------ */
let rangeCircle = L.circle([config.homeLat, config.homeLon], {
    radius: config.radiusMiles * 1609.34,
    color: "lime",
    fill: false,
}).addTo(map);
