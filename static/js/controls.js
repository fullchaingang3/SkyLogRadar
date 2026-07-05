function clearFocus() {
            state.focusedAircraft = null;
            $("aircraft-search").value = "";

            Object.values(state.aircraftMarkers).forEach((marker) => marker.closePopup());
            map.setView([config.homeLat, config.homeLon], 9);

            closeDetailsPanel(false);
            updateAircraftList(state.lastPlanes);
            updateAircraft();
        }

function exportVisibleAircraftCsv() {
            const rows = [["Callsign", "Tail", "Type", "Category", "Distance", "Altitude", "Speed"]];

            state.lastPlanes.forEach((plane) => {
                if (!shouldShowPlane(plane)) {
                    return;
                }

                rows.push([
                    plane.callsign || plane.icao_hex,
                    plane.tail_number || "",
                    plane.aircraft_type || "",
                    plane.category || "",
                    plane.distance_miles || "",
                    plane.altitude || "",
                    plane.speed || "",
                ]);
            });

            const csv = rows.map((row) => row.join(",")).join("\n");
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");

            link.href = url;
            link.download = "skylog_visible_aircraft.csv";
            link.click();
            URL.revokeObjectURL(url);
        }

function showScoreInfo() {
            alert(
                "Aircraft Intelligence Score\n\n"
                + "Military aircraft: +50\n"
                + "Favorite aircraft: +40\n"
                + "Within 5 miles: +25\n"
                + "Within 15 miles: +15\n"
                + "Below 5,000 ft: +15\n"
                + "Speed over 450 kt: +10\n"
                + "Unknown category: +8\n\n"
                + "Higher score = more interesting aircraft.",
            );
        }

function toggleSidebar() {
            const sidebar = $("sidebar");
            const button = $("sidebar-toggle-btn");
            const isClosing = !sidebar.classList.contains("collapsed");

            sidebar.classList.toggle("collapsed");

            if (isClosing) {
                button.innerHTML = "❮";
                document.documentElement.style.setProperty("--sidebar-width", "0px");
            } else {
                button.innerHTML = "❯";
                document.documentElement.style.setProperty("--sidebar-width", "450px");
            }

            setTimeout(() => map.invalidateSize(), 300);
        }

function toggleSidebarSection(sectionId) {
            const section = $(sectionId);
            const accordionSections = [
                "favorites-panel",
                "hot-aircraft-panel",
                "leaders-panel",
                "military-alerts-panel",
                "notifications-panel",
            ];

            if (accordionSections.includes(sectionId)) {
                accordionSections.forEach((id) => {
                    if (id !== sectionId) {
                        $(id).classList.add("collapsed");
                    }
                });
            }

            section.classList.toggle("collapsed");
        }

function toggleTopControls() {
            const controls = $("top-controls");
            const header = document.querySelector(".controls-header");

            controls.classList.toggle("collapsed");
            header.innerHTML = controls.classList.contains("collapsed")
                ? "▶ Radar Controls"
                : "▼ Radar Controls";

            setTimeout(() => map.invalidateSize(), 100);
        }

function toggleUpdates() {
            state.updatesPaused = !state.updatesPaused;
            $("pause-updates-btn").innerText = state.updatesPaused ? "Resume Updates" : "Pause Updates";

            if (!state.updatesPaused) {
                updateAircraft();
            }
        }

async function updateLocationFromZip() {
            const zip = $("zip-input").value.trim();

            if (!zip) {
                alert("Enter a ZIP code first.");
                return;
            }

            const response = await fetch("/set_location", {
                body: JSON.stringify({ zip }),
                headers: { "Content-Type": "application/json" },
                method: "POST",
            });

            const result = await response.json();

            if (!result.success) {
                alert(`Could not update location: ${result.error}`);
                return;
            }

            location.reload();
        }

/* ------------------------------------------------------------------
   Function: updateRadius
   Updates tracking radius and refreshes visible aircraft.
------------------------------------------------------------------ */
async function updateRadius() {
    config.radiusMiles = parseFloat($("radius-select").value);

    if (rangeCircle) {
        rangeCircle.setRadius(config.radiusMiles * 1609.34);
    }

    const response = await fetch("/set_radius", {
        body: JSON.stringify({ radius: config.radiusMiles }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
    });

    const result = await response.json();

    if (result.aircraft) {
        state.lastPlanes = result.aircraft;

        state.lastPlanes.forEach((plane) => {
            plane.analysis = analyzeAircraft(plane);
        });

        updateAircraftList(state.lastPlanes);
        updateMilitaryAlerts(state.lastPlanes);
        updateFavoritesPanel(state.lastPlanes);
        updateCategoryCounts(state.lastPlanes);
        updateHistoricalHeatmap();
    }

    updateStatus();
}

async function updateStatus() {
            const response = await fetch("/status");
            const status = await response.json();

            $("last-update").innerText = `Last Update: ${status.last_fetch_time || "--"}`;
            $("api-status").innerText = status.fetch_error ? `API: ${status.fetch_error}` : "API: OK";
        }

function wireEventListeners() {
            $("aircraft-search").addEventListener("input", () => updateAircraftList(state.lastPlanes));
            $("clear-focus-btn").addEventListener("click", clearFocus);
            $("export-csv-btn").addEventListener("click", exportVisibleAircraftCsv);
            $("pause-updates-btn").addEventListener("click", toggleUpdates);
            $("radius-select").addEventListener("change", updateRadius);
            $("update-location-btn").addEventListener("click", updateLocationFromZip);

            ["heatmap-mode", "heatmap-time-range", "toggle-heatmap"].forEach((id) => {
                $(id).addEventListener("change", updateHistoricalHeatmap);
            });

            ["filter-civilian", "filter-commercial", "filter-military", "filter-unknown", "toggle-labels", "toggle-sweep", "toggle-trails"].forEach((id) => {
                $(id).addEventListener("change", updateAircraft);
            });
        }

/* ------------------------------------------------------------------
   Function: toggleMissionMode
   Enables or disables SkyLog Mission Mode.
------------------------------------------------------------------ */
function toggleMissionMode() {
    state.missionMode = !state.missionMode;

    const button = $("mission-mode-btn");

    button.innerText = state.missionMode
        ? "🎯 Mission Mode: ON"
        : "🎯 Mission Mode: OFF";

    button.classList.toggle("mission-active", state.missionMode);

    updateAircraft();
}
