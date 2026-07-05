/* ------------------------------------------------------------------
   Function: updateAircraft
   Fetches aircraft, analyzes them, updates panels, and redraws map layers.
------------------------------------------------------------------ */
async function updateAircraft() {
    const response = await fetch("/aircraft");
    const planes = await response.json();
    const seen = new Set();

    state.lastPlanes = planes;

    planes.forEach((plane) => {
        plane.analysis = analyzeAircraft(plane);
    });

    evaluateAlertRules(planes);
    updateMilitaryAlerts(planes);
    updateFavoritesPanel(planes);
    updateAircraftList(planes);
    updateHotAircraftPanel(planes);
    updateLeadersPanel(planes);
    updateSidebarHeaderCounts(planes);
    updateHistoricalHeatmap();
    updateCategoryCounts(planes);

    $("aircraft-count").innerText = `Aircraft: ${planes.length}`;

    planes.forEach((plane) => {
        if (!shouldShowPlane(plane)) {
            return;
        }

        seen.add(plane.icao_hex);

        if (!state.aircraftTrails[plane.icao_hex]) {
            state.aircraftTrails[plane.icao_hex] = [];
        }

        state.aircraftTrails[plane.icao_hex].push([plane.lat, plane.lon]);

        if (state.aircraftTrails[plane.icao_hex].length > state.maxTrailPoints) {
            state.aircraftTrails[plane.icao_hex].shift();
        }

        updateAircraftTrail(plane);
        updateAircraftMarker(plane);
        updateAircraftMapLabel(plane);
    });

    refreshFocusedPopup();
    removeOldAircraftLayers(seen);
}

function startApp() {
            $("radius-select").value = String(config.radiusMiles);
            wireEventListeners();
            animateRadarSweep();
            updateAircraftList(state.lastPlanes);
            updateFavoritesPanel(state.lastPlanes);
            updateMilitaryAlerts(state.lastPlanes);
            updateAircraft();
            updateStatus();

            setTimeout(() => {
                updateAircraft();
                updateStatus();
            }, 2500);

            setInterval(() => {
                if (!state.updatesPaused) {
                    updateAircraft();
                }
            }, 5000);

            setInterval(updateStatus, 5000);
        }

/* ------------------------------------------------------------------
   Object: App startup call
------------------------------------------------------------------ */
startApp();
