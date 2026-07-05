function addNotification(type, message) {
            state.notifications.unshift({
                message,
                timestamp: new Date().toLocaleTimeString(),
                type,
            });

            state.notifications = state.notifications.slice(0, 25);
            updateNotificationsPanel();
            updateSidebarHeaderCounts(state.lastPlanes);
        }

function checkFavoriteAlerts(planes) {
            const activeFavoriteHexes = new Set(
                planes
                    .filter((plane) => state.favoriteAircraft.has(plane.icao_hex))
                    .map((plane) => plane.icao_hex),
            );

            planes.forEach((plane) => {
                if (state.favoriteAircraft.has(plane.icao_hex) && !state.alertedFavorites.has(plane.icao_hex)) {
                    state.alertedFavorites.add(plane.icao_hex);
                    addNotification(
                        "⭐ Favorite",
                        `${plane.callsign || plane.icao_hex} entered range | ${plane.distance_miles} mi`,
                    );
                }
            });

            state.alertedFavorites.forEach((hex) => {
                if (!activeFavoriteHexes.has(hex)) {
                    state.alertedFavorites.delete(hex);
                }
            });
        }

function checkMilitaryAlerts(planes) {
            planes.forEach((plane) => {
                if (plane.category === "Military" && !state.alertedMilitary.has(plane.icao_hex)) {
                    state.alertedMilitary.add(plane.icao_hex);
                    addNotification(
                        "🚨 Military",
                        `${plane.callsign || plane.icao_hex} | ${plane.aircraft_type || "Unknown"} | ${plane.distance_miles} mi`,
                    );
                }
            });

            const activeMilitary = new Set(
                planes
                    .filter((plane) => plane.category === "Military")
                    .map((plane) => plane.icao_hex),
            );

            state.alertedMilitary.forEach((hex) => {
                if (!activeMilitary.has(hex)) {
                    state.alertedMilitary.delete(hex);
                }
            });
        }

function updateNotificationsPanel() {
            const panel = $("notifications-panel");

            if (state.notifications.length === 0) {
                panel.innerHTML = `<div style="padding:10px;color:#aaa;">No notifications yet.</div>`;
                return;
            }

            panel.innerHTML = state.notifications.map((note) => `
                <div style="padding:8px 10px;border-bottom:1px solid #333;">
                    <strong>${note.type}</strong><br>
                    <span style="color:#aaa;">${note.timestamp}</span><br>
                    ${note.message}
                </div>
            `).join("");
        }
