async function buildPopupContent(plane) {
            let historyHtml = "";

            try {
                const response = await fetch(`/aircraft/${plane.icao_hex}/history`);
                const history = await response.json();

                if (history.found) {
                    historyHtml = `
                        <hr>
                        <strong>Local History</strong><br>
                        First Seen: ${history.first_seen}<br>
                        Last Seen: ${history.last_seen}<br>
                        Time in Area: ${history.time_in_area}<br>
                        Track Points: ${history.track_points}<br>
                        Max Speed: ${history.max_speed || "Unknown"} kt<br>
                        Max Altitude: ${history.max_altitude || "Unknown"} ft<br>
                        Closest: ${history.closest_distance || "Unknown"} mi<br>
                        <br>
                        <button disabled>Replay Flight</button>
                    `;
                } else {
                    historyHtml = `
                        <hr>
                        <strong>Local History</strong><br>
                        No local history found yet.<br>
                        Keep tracking this aircraft and try again shortly.
                    `;
                }
            } catch (error) {
                historyHtml = `
                    <hr>
                    <strong>Local History</strong><br>
                    History unavailable.
                `;
            }

            return `
                <strong>${plane.callsign || plane.icao_hex}</strong><br>
                Category: ${plane.category || "Unknown"}<br>
                Tail: ${plane.tail_number || "Unknown"}<br>
                Type: ${plane.aircraft_type || "Unknown"}<br>
                Description: ${plane.description || "Unknown"}<br>
                Operator: ${plane.owner_operator || "Unknown"}<br>
                Year: ${plane.year || "Unknown"}<br>
                Altitude: ${getAltitudeDisplay(plane)}<br>
                Distance: ${plane.distance_miles || "Unknown"} mi<br>
                Speed: ${plane.speed || "Unknown"} kt
                ${historyHtml}
            `;
        }

function openAircraftDetailsSection() {
            $("details-side-panel").classList.remove("collapsed");
        }

function closeDetailsPanel(resetView = true) {
            state.focusedAircraft = null;
            $("details-side-panel").classList.add("collapsed");

            Object.values(state.aircraftMarkers).forEach((marker) => marker.closePopup());

            if (resetView) {
                map.setView([config.homeLat, config.homeLon], 9);
            }

            updateAircraftList(state.lastPlanes);
        }

async function getAircraftPhotoHtml(plane) {
            if (!plane.tail_number) {
                return `<div style="padding:8px;color:#aaa;border:1px solid #333;margin-bottom:10px;">No tail number available for photo lookup.</div>`;
            }

            try {
                const response = await fetch(`/aircraft_photo?tail=${encodeURIComponent(plane.tail_number)}`);
                const photo = await response.json();

                if (!photo.found) {
                    return `<div style="padding:8px;color:#aaa;border:1px solid #333;margin-bottom:10px;">No aircraft photo found.</div>`;
                }

                return `
                    <a href="${photo.source}" target="_blank">
                        <img src="${photo.image}" style="width:100%;max-height:180px;object-fit:cover;border:1px solid #333;margin-bottom:10px;">
                    </a>
                `;
            } catch (error) {
                return `<div style="padding:8px;color:#aaa;border:1px solid #333;margin-bottom:10px;">Unable to load aircraft photo.</div>`;
            }
        }

/* ------------------------------------------------------------------
   Function: focusAircraft
   Focuses the map and opens the left aircraft details panel.
------------------------------------------------------------------ */
function focusAircraft(plane) {
    if (!plane.analysis) {
        plane.analysis = analyzeAircraft(plane);
    }

    state.focusedAircraft = plane.icao_hex;
    map.setView([plane.lat, plane.lon], 12);

    updateAircraftDetailsPanel(plane);
    updateAircraftList(state.lastPlanes);
}

function focusAircraftByHex(hex) {
            const plane = state.lastPlanes.find((item) => item.icao_hex === hex);

            if (plane) {
                focusAircraft(plane);
            }
        }

async function updateAircraftDetailsPanel(plane) {
            openAircraftDetailsSection();

            const panel = $("details-side-content");
            panel.innerHTML = `<div style="padding:10px;color:#aaa;">Loading aircraft details...</div>`;

            const photoHtml = await getAircraftPhotoHtml(plane);
            const photoUrl = getAircraftPhotoUrl(plane);
            const score = (plane.analysis || analyzeAircraft(plane)).score;

            panel.innerHTML = `
                <div style="padding:10px;">
                    ${photoHtml}

                    <div style="text-align:center;border-bottom:1px solid #333;padding-bottom:10px;margin-bottom:10px;">
                        <div style="font-size:18px;font-weight:bold;">${plane.callsign || plane.icao_hex}</div>
                        <div style="color:#aaa;">${plane.tail_number || "No Tail"} | ${plane.aircraft_type || "Unknown Type"}</div>
                        <div style="margin-top:6px;">${getAircraftBadges(plane)}</div>
                        <div style="margin-top:6px;color:#ffb300;">${getScoreStars(score)}</div>
                        <div style="font-size:12px;color:#aaa;">Intelligence Score: ${plane.analysis?.score || score}</div>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px;">
                        <div><strong>Altitude</strong><br>${getAltitudeDisplay(plane)}</div>
                        <div><strong>Category</strong><br>${plane.category || "Unknown"}</div>
                        <div><strong>Distance</strong><br>${plane.distance_miles || "Unknown"} mi</div>
                        <div><strong>Heading</strong><br>${plane.heading || "Unknown"}°</div>
                        <div><strong>Speed</strong><br>${Math.round(plane.speed || 0)} kt</div>
                        <div><strong>Year</strong><br>${plane.year || "Unknown"}</div>
                        <div style="grid-column:1 / span 2;"><strong>Description</strong><br>${plane.description || "Unknown"}</div>
                        <div style="grid-column:1 / span 2;"><strong>Operator</strong><br>${plane.owner_operator || "Unknown"}</div>
                    </div>

                    ${buildIntelligenceHtml(plane)}

                    <br>

                    ${photoUrl ? `<button onclick="window.open('${photoUrl}', '_blank')">View Real Aircraft Photos</button><br><br>` : ""}

                    <button onclick="toggleFavorite('${plane.icao_hex}')">
                        ${state.favoriteAircraft.has(plane.icao_hex) ? "Remove Favorite" : "Add Favorite"}
                    </button>
                </div>
            `;
        }
