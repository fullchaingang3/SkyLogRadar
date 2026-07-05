function addNotification(type, message, severity="INFO") {
            state.notifications.unshift({
                title:title,
                message:message,
                severity:severity,
                time:new Date()
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

        /* ------------------------------------------------------------------
           Function: updateNotificationsPanel
           Builds the notification list with alert severity.
        ------------------------------------------------------------------ */
        function updateNotificationsPanel() {
            const panel = $("notifications-panel");

            if (state.notifications.length === 0) {
                panel.innerHTML = `
                    <div style="
                        padding:10px;
                        color:#aaa;
                    ">
                        No notifications yet.
                    </div>
                `;
                return;
            }

            panel.innerHTML = state.notifications.map((note) => {
                let severityIcon = "🟢";
                if (note.severity === "WATCH") {
                    severityIcon = "🟡";
                }
                if (note.severity === "CRITICAL") {
                    severityIcon = "🔴";
                }
                return `
                    <div style="
                        padding:8px 10px;
                        border-bottom:1px solid #333;
                    ">
        
                        <div style="
                            font-size:11px;
                            font-weight:bold;
                            margin-bottom:4px;
                        ">
                            ${severityIcon} ${note.severity || "INFO"}
                        </div>
        
                        <strong>
                            ${note.type}
                        </strong>
        
                        <br>
        
                        <span style="
                            color:#aaa;
                            font-size:11px;
                        ">
                            ${note.timestamp}
                        </span>
        
                        <br>        
        
                        <span>
                            ${note.message}
                        </span>        
        
                    </div>
                `;

            }).join("");
        }
