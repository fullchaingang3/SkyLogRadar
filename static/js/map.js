function animateRadarSweep() {
            if (!sweepEnabled()) {
                if (state.sweepLine) {
                    map.removeLayer(state.sweepLine);
                    state.sweepLine = null;
                }

                requestAnimationFrame(animateRadarSweep);
                return;
            }

            state.sweepAngle = (state.sweepAngle + 0.75) % 360;
            const endPoint = destinationPoint(
                config.homeLat,
                config.homeLon,
                state.sweepAngle,
                config.radiusMiles,
            );

            if (state.sweepLine) {
                map.removeLayer(state.sweepLine);
            }

            state.sweepLine = L.polyline(
                [[config.homeLat, config.homeLon], endPoint],
                { color: "lime", opacity: 0.8, weight: 3 },
            ).addTo(map);

            requestAnimationFrame(animateRadarSweep);
        }

function createPlaneIcon(category, heading, isFocused) {
            const color = getColor(category);
            const iconSize = isFocused ? 42 : 30;
            const anchor = isFocused ? 21 : 15;

            return L.divIcon({
                className: "",
                html: `
                    <div style="transform: rotate(${heading - 45}deg); width:${iconSize}px; height:${iconSize}px;">
                        <svg viewBox="0 0 512 512" width="${iconSize}" height="${iconSize}" fill="${color}">
                            <path d="M476 3L12 223l180 73 73 180L476 3z"/>
                        </svg>
                    </div>
                `,
                iconAnchor: [anchor, anchor],
                iconSize: [iconSize, iconSize],
            });
        }

function createAircraftLabel(plane) {
            const labelText = `
                <div style="
                    color:white;
                    background:rgba(0,0,0,0.65);
                    padding:3px 5px;
                    border-radius:4px;
                    font-size:11px;
                    white-space:nowrap;
                    border:1px solid ${getColor(plane.category)};
                ">
                    ${plane.callsign || plane.icao_hex}<br>
                    ${getAltitudeDisplay(plane)} | ${Math.round(plane.speed || 0)} kt
                </div>
            `;

            return L.divIcon({
                className: "",
                html: labelText,
                iconAnchor: [-15, 15],
                iconSize: [110, 35],
            });
        }

/* ------------------------------------------------------------------
   Function: updateAircraftMarker
   Updates or creates the aircraft marker on the map.
   Clicking the marker opens the left details panel only.
------------------------------------------------------------------ */
function updateAircraftMarker(plane) {
    const icon = createPlaneIcon(
        plane.category,
        plane.heading || 0,
        plane.icao_hex === state.focusedAircraft
    );

    if (state.aircraftMarkers[plane.icao_hex]) {
        state.aircraftMarkers[plane.icao_hex]
            .setLatLng([plane.lat, plane.lon])
            .setIcon(icon);

        state.aircraftMarkers[plane.icao_hex].off("click");
        state.aircraftMarkers[plane.icao_hex].on("click", () => {
            focusAircraft(plane);
        });
    } else {
        state.aircraftMarkers[plane.icao_hex] = L.marker(
            [plane.lat, plane.lon],
            { icon }
        ).addTo(map);

        state.aircraftMarkers[plane.icao_hex].on("click", () => {
            focusAircraft(plane);
        });
    }
}

function updateAircraftTrail(plane) {
            const trailColor = getColor(plane.category);

            if (trailsEnabled()) {
                if (state.aircraftTrailLines[plane.icao_hex]) {
                    const trailPoints = state.aircraftTrails[plane.icao_hex].slice(0, -1);
                    state.aircraftTrailLines[plane.icao_hex].setLatLngs(trailPoints);
                } else {
                    state.aircraftTrailLines[plane.icao_hex] = L.polyline(
                        state.aircraftTrails[plane.icao_hex],
                        { color: trailColor, opacity: 0.75, weight: 3 },
                    ).addTo(map);
                }
            } else if (state.aircraftTrailLines[plane.icao_hex]) {
                map.removeLayer(state.aircraftTrailLines[plane.icao_hex]);
                delete state.aircraftTrailLines[plane.icao_hex];
            }
        }

function updateAircraftMapLabel(plane) {
            if (labelsEnabled()) {
                const labelIcon = createAircraftLabel(plane);

                if (state.aircraftLabels[plane.icao_hex]) {
                    state.aircraftLabels[plane.icao_hex]
                        .setLatLng([plane.lat, plane.lon])
                        .setIcon(labelIcon);
                } else {
                    state.aircraftLabels[plane.icao_hex] = L.marker(
                        [plane.lat, plane.lon],
                        { icon: labelIcon, interactive: false },
                    ).addTo(map);
                }
            } else if (state.aircraftLabels[plane.icao_hex]) {
                map.removeLayer(state.aircraftLabels[plane.icao_hex]);
                delete state.aircraftLabels[plane.icao_hex];
            }
        }

function updateHeatmap(planes) {
            if (!heatmapEnabled()) {
                if (state.heatLayer) {
                    map.removeLayer(state.heatLayer);
                    state.heatLayer = null;
                }
                return;
            }

            const mode = $("heatmap-mode").value;
            const heatPoints = planes
                .filter((plane) => {
                    if (mode === "All") return true;
                    if (mode === "Favorites") return state.favoriteAircraft.has(plane.icao_hex);
                    return plane.category === mode;
                })
                .map((plane) => {
                    let intensity = 0.5;

                    if (plane.category === "Military") intensity = 1.0;
                    else if (plane.category === "Commercial") intensity = 0.7;
                    else if (plane.category === "Civilian") intensity = 0.6;

                    return [plane.lat, plane.lon, intensity];
                });

            if (state.heatLayer) {
                state.heatLayer.setLatLngs(heatPoints);
            } else {
                state.heatLayer = L.heatLayer(heatPoints, {
                    blur: 25,
                    maxZoom: 12,
                    radius: 35,
                }).addTo(map);
            }
        }

async function updateHistoricalHeatmap() {
            if (!heatmapEnabled()) {
                if (state.heatLayer) {
                    map.removeLayer(state.heatLayer);
                    state.heatLayer = null;
                }
                return;
            }

            const range = $("heatmap-time-range").value;
            const mode = $("heatmap-mode").value;

            if (range === "live") {
                updateHeatmap(state.lastPlanes);
                return;
            }

            const category = mode === "Favorites" ? "All" : mode;
            const response = await fetch(`/heatmap_history?range=${range}&category=${category}`);
            const heatPoints = await response.json();

            if (state.heatLayer) {
                state.heatLayer.setLatLngs(heatPoints);
            } else {
                state.heatLayer = L.heatLayer(heatPoints, {
                    blur: 22,
                    maxZoom: 12,
                    radius: 30,
                }).addTo(map);
            }
        }

function removeOldAircraftLayers(seen) {
            Object.keys(state.aircraftMarkers).forEach((hex) => {
                if (seen.has(hex)) {
                    return;
                }

                map.removeLayer(state.aircraftMarkers[hex]);
                delete state.aircraftMarkers[hex];

                if (state.aircraftTrailLines[hex]) {
                    map.removeLayer(state.aircraftTrailLines[hex]);
                    delete state.aircraftTrailLines[hex];
                }

                if (state.aircraftLabels[hex]) {
                    map.removeLayer(state.aircraftLabels[hex]);
                    delete state.aircraftLabels[hex];
                }

                delete state.aircraftTrails[hex];

                if (state.focusedAircraft === hex) {
                    state.focusedAircraft = null;
                }
            });
        }

/* ------------------------------------------------------------------
   Function: refreshFocusedPopup
   No-op. Map popups were removed because details now live in the left panel.
------------------------------------------------------------------ */
function refreshFocusedPopup() {
    return;
}
