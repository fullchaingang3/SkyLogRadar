/* ------------------------------------------------------------------
   Object: alertRules
   Smart alert rules evaluated against every aircraft.
------------------------------------------------------------------ */
const alertRules = [
    {
        id: "favorite-nearby",
        enabled: true,

        severity: "INFO",

        condition: (plane) => isFavorite(plane.icao_hex),
        title: "⭐ Favorite Aircraft",
        message: (plane) => `${plane.callsign || plane.icao_hex} is nearby.`
    },

    {
        id: "military-nearby",
        enabled: true,

        severity: "INFO",

        condition: (plane) => plane.category === "Military",
        title: "🚨 Military Aircraft",
        message: (plane) => `${plane.callsign || plane.icao_hex} entered your area.`
    },

    {
        id: "hot-aircraft",
        enabled: true,

        severity: "INFO",

        condition: (plane) => (plane.analysis?.score || 0) >= 70,
        title: "🔥 High Interest Aircraft",
        message: (plane) => `${plane.callsign || plane.icao_hex} scored ${plane.analysis.score}.`
    },

    {
        id: "low-helicopter",
        enabled: true,

        severity: "INFO",

        condition: (plane) =>
            (plane.aircraft_type || "").startsWith("H") &&
            getAltitudeValue(plane) > 0 &&
            getAltitudeValue(plane) < 1000,
        title: "🚁 Low Helicopter",
        message: (plane) => `${plane.callsign || plane.icao_hex} is below 1,000 ft.`
    },

        {
        id: "emergency-squawk",
        enabled: true,

        severity: "INFO",

        condition: (plane) =>
            ["7500", "7600", "7700"].includes(String(plane.squawk)),

        title: "🆘 Emergency Squawk",

        message: (plane) =>
            `${plane.callsign || plane.icao_hex} is broadcasting emergency code ${plane.squawk}.`
    },

        {
        id: "low-aircraft",
        enabled: true,

        severity: "INFO",

        condition: (plane) =>
            getAltitudeValue(plane) > 0 &&
            getAltitudeValue(plane) < 1500,

        title: "⬇️ Low Aircraft",

        message: (plane) =>
            `${plane.callsign || plane.icao_hex} is flying below 1,500 ft.`
    },

        {
        id: "high-speed",
        enabled: true,

        severity: "INFO",

        condition: (plane) =>
            (plane.speed || 0) > 500,

        title: "⚡ High Speed Aircraft",

        message: (plane) =>
            `${plane.callsign || plane.icao_hex} is traveling ${Math.round(plane.speed)} knots.`
    },

        {
        id: "close-pass",
        enabled: true,

        severity: "INFO",
        condition: (plane) =>
            plane.distance_miles <= 5,

        title: "📍 Close Aircraft",

        message: (plane) =>
            `${plane.callsign || plane.icao_hex} is within 5 miles.`
    },

        {
        id: "unknown-aircraft",
        enabled: true,

        severity: "INFO",

        condition: (plane) =>
            plane.category === "Unknown",

        title: "❓ Unknown Aircraft",

        message: (plane) =>
            `${plane.callsign || plane.icao_hex} has limited identification data.`
    }
];

/* ------------------------------------------------------------------
   Function: evaluateAlertRules
   Runs enabled alert rules against current aircraft.
------------------------------------------------------------------ */
function evaluateAlertRules(planes) {
    planes.forEach((plane) => {
        alertRules.forEach((rule) => {
            if (!rule.enabled) return;

            const key = `${rule.id}-${plane.icao_hex}`;

            if (rule.condition(plane)) {
                if (!state.alertHistory.has(key)) {
                    state.alertHistory.add(key);
                    addNotification(rule.title,rule.message(plane),rule.severity);
                }
            } else {
                state.alertHistory.delete(key);
            }
        });
    });
}