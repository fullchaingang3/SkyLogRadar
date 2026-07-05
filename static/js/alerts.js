/*********************************************************************
 * SKYLOG ALERT RULES
 *
 * Add future smart alerts inside this array. The engine is ready, but
 * it is not replacing the current favorite/military alerts yet.
 *********************************************************************/
const alertRules = [
    {
        id: "favorite-nearby",
        enabled: true,
        condition: (plane) => state.favoriteAircraft.has(plane.icao_hex),
        title: "⭐ Favorite Aircraft",
        message: (plane) => `${plane.callsign || plane.icao_hex} is nearby.`,
    },
    {
        id: "military-nearby",
        enabled: true,
        condition: (plane) => plane.category === "Military",
        title: "🚨 Military Aircraft",
        message: (plane) => `${plane.callsign || plane.icao_hex} entered your area.`,
    },
];

/*********************************************************************
 * Function: evaluateAlertRules
 * Runs every aircraft through every enabled alert rule.
 *********************************************************************/
function evaluateAlertRules(planes) {
    planes.forEach((plane) => {
        alertRules.forEach((rule) => {
            if (!rule.enabled) return;

            const key = `${rule.id}-${plane.icao_hex}`;

            if (rule.condition(plane)) {
                if (!state.alertHistory.has(key)) {
                    state.alertHistory.add(key);
                    addNotification(rule.title, rule.message(plane));
                }
            } else {
                state.alertHistory.delete(key);
            }
        });
    });
}
