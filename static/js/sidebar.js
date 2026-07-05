function getAircraftBadges(plane) {
            const badges = [];

            if (state.favoriteAircraft.has(plane.icao_hex)) {
                badges.push(`<span class="aircraft-badge badge-favorite">FAV</span>`);
            }

            if (plane.category === "Military") {
                badges.push(`<span class="aircraft-badge badge-military">MIL</span>`);
            }

            if ((plane.analysis || analyzeAircraft(plane)).score >= 70) {
                badges.push(`<span class="aircraft-badge badge-hot">HOT</span>`);
            }

            if (getAltitudeValue(plane) > 0 && getAltitudeValue(plane) < 3000) {
                badges.push(`<span class="aircraft-badge badge-low">LOW</span>`);
            }

            if ((Number(plane.speed) || 0) > 500) {
                badges.push(`<span class="aircraft-badge badge-fast">FAST</span>`);
            }

            if ((plane.aircraft_type || "").startsWith("H")) {
                badges.push(`<span class="aircraft-badge badge-heli">HELI</span>`);
            }

            return badges.join("");
        }

function sortAircraft(column) {
            if (state.currentSort === column) {
                state.sortAscending = !state.sortAscending;
            } else {
                state.currentSort = column;
                state.sortAscending = true;
            }

            updateAircraftList(state.lastPlanes);
        }

function toggleFavorite(hex) {
            if (state.favoriteAircraft.has(hex)) {
                state.favoriteAircraft.delete(hex);
            } else {
                state.favoriteAircraft.add(hex);
            }

            updateAircraftList(state.lastPlanes);
            updateFavoritesPanel(state.lastPlanes);
            checkFavoriteAlerts(state.lastPlanes);
            updateSidebarHeaderCounts(state.lastPlanes);
        }

function updateAircraftList(planes) {
            const list = $("aircraft-list");
            const searchText = $("aircraft-search").value.toUpperCase().trim();
            let filteredPlanes = [...planes];

            list.innerHTML = "";

            if (searchText) {
                filteredPlanes = filteredPlanes.filter((plane) => (
                    (plane.aircraft_type || "").toUpperCase().includes(searchText)
                    || (plane.callsign || "").toUpperCase().includes(searchText)
                    || (plane.icao_hex || "").toUpperCase().includes(searchText)
                    || (plane.owner_operator || "").toUpperCase().includes(searchText)
                    || (plane.tail_number || "").toUpperCase().includes(searchText)
                ));
            }

            filteredPlanes.sort((a, b) => {
                if (state.favoriteAircraft.has(a.icao_hex) && !state.favoriteAircraft.has(b.icao_hex)) return -1;
                if (!state.favoriteAircraft.has(a.icao_hex) && state.favoriteAircraft.has(b.icao_hex)) return 1;

                let result = 0;

                switch (state.currentSort) {
                    case "altitude":
                        result = getAltitudeValue(a) - getAltitudeValue(b);
                        break;
                    case "callsign":
                        result = (a.callsign || a.icao_hex || "").localeCompare(b.callsign || b.icao_hex || "");
                        break;
                    case "distance":
                        result = (a.distance_miles || 999) - (b.distance_miles || 999);
                        break;
                    case "speed":
                        result = (Number(a.speed) || 0) - (Number(b.speed) || 0);
                        break;
                    case "type":
                        result = (a.aircraft_type || "").localeCompare(b.aircraft_type || "");
                        break;
                    default:
                        result = 0;
                }

                return state.sortAscending ? result : -result;
            });

            filteredPlanes.forEach((plane) => {
                if (!shouldShowPlane(plane)) {
                    return;
                }

                const row = document.createElement("tr");
                row.style.borderLeft = `5px solid ${getColor(plane.category)}`;

                if (plane.icao_hex === state.focusedAircraft) {
                    row.style.background = "#222";
                }

                row.innerHTML = `
                    <td class="star-col">
                        <span
                            class="aircraft-star ${state.favoriteAircraft.has(plane.icao_hex) ? "favorite" : ""}"
                            onclick="event.stopPropagation(); toggleFavorite('${plane.icao_hex}')"
                        >★</span>
                    </td>

                    <td class="callsign-col">
                        <div class="aircraft-callsign">${plane.callsign || plane.icao_hex}</div>
                        <div class="aircraft-badge-row">${getAircraftBadges(plane)}</div>
                    </td>

                    <td class="dist-col">${Number(plane.distance_miles || 0).toFixed(1)}</td>
                    <td class="alt-col">${getAltitudeDisplay(plane)}</td>
                    <td class="speed-col">${Math.round(plane.speed || 0)}</td>
                    <td class="type-col">${plane.aircraft_type || ""}</td>
                `;

                row.onclick = () => focusAircraft(plane);
                list.appendChild(row);
            });
        }

function updateCategoryCounts(planes) {
            const counts = {
                Civilian: 0,
                Commercial: 0,
                Military: 0,
                Unknown: 0,
            };

            planes.forEach((plane) => {
                const category = plane.category || "Unknown";
                counts[category] = (counts[category] || 0) + 1;
            });

            $("category-counts").innerText = `Commercial: ${counts.Commercial} | Civilian: ${counts.Civilian} | Military: ${counts.Military} | Unknown: ${counts.Unknown}`;
        }

function updateFavoritesPanel(planes) {
            const panel = $("favorites-panel");
            const favoritesInRange = planes.filter((plane) => state.favoriteAircraft.has(plane.icao_hex));

            if (favoritesInRange.length === 0) {
                panel.innerHTML = `
                    <div style="padding:10px;">
                        <strong>⭐ Favorites (${state.favoriteAircraft.size})</strong><br>
                        🟢 In Range: 0<br>
                        ⚫ Out of Range: ${state.favoriteAircraft.size}
                    </div>
                `;
                return;
            }

            let html = `
                <div style="padding:10px;">
                    <strong>⭐ Favorites (${state.favoriteAircraft.size})</strong><br>
                    🟢 In Range: ${favoritesInRange.length}<br>
                    ⚫ Out of Range: ${state.favoriteAircraft.size - favoritesInRange.length}
                    <hr>
                </div>
            `;

            favoritesInRange
                .sort((a, b) => (a.distance_miles || 999) - (b.distance_miles || 999))
                .forEach((plane) => {
                    html += `
                        <div onclick="focusAircraftByHex('${plane.icao_hex}')" style="padding:7px 10px;border-top:1px solid #777700;cursor:pointer;">
                            <strong>${getAircraftBadges(plane)} ${plane.callsign || plane.icao_hex}</strong><br>
                            ${plane.aircraft_type || "Unknown"} | ${plane.distance_miles} mi | ${getAltitudeDisplay(plane)} | ${Math.round(plane.speed || 0)} kt
                        </div>
                    `;
                });

            panel.innerHTML = html;
        }

function updateHotAircraftPanel(planes) {
            const panel = $("hot-aircraft-panel");
            const hotPlanes = [...planes]
                .filter((plane) => shouldShowPlane(plane))
                .map((plane) => ({ ...plane, score: (plane.analysis || analyzeAircraft(plane)).score }))
                .filter((plane) => plane.score > 0)
                .sort((a, b) => b.score - a.score)
                .slice(0, 8);

            let html = `
                <div style="display:grid;grid-template-columns:1fr 70px 55px;padding:6px 8px;font-weight:bold;border-bottom:1px solid #555;color:#ccc;font-size:12px;">
                    <div>Tail / Call</div><div>Type</div><div>Score</div>
                </div>
            `;

            if (hotPlanes.length === 0) {
                panel.innerHTML = html + `<div style="padding:10px;color:#aaa;">No hot aircraft right now.</div>`;
                return;
            }

            hotPlanes.forEach((plane) => {
                html += `
                    <div onclick="focusAircraftByHex('${plane.icao_hex}')" style="display:grid;grid-template-columns:1fr 70px 55px;padding:7px 8px;border-bottom:1px solid #333;cursor:pointer;font-size:12px;">
                        <div><strong>${getAircraftBadges(plane)} ${plane.tail_number || plane.callsign || plane.icao_hex}</strong><br><span style="color:#aaa;">${plane.callsign || plane.icao_hex}</span></div>
                        <div>${plane.category}</div>
                        <div><strong>${plane.score}</strong></div>
                    </div>
                `;
            });

            panel.innerHTML = html;
        }

function updateLeadersPanel(planes) {
            const panel = $("leaders-panel");
            const visiblePlanes = planes.filter((plane) => shouldShowPlane(plane));

            let html = `
                <div style="display:grid;grid-template-columns:90px 1fr 70px;padding:6px 8px;font-weight:bold;border-bottom:1px solid #555;color:#ccc;font-size:12px;">
                    <div>Leader</div><div>Tail / Call</div><div>Value</div>
                </div>
            `;

            if (visiblePlanes.length === 0) {
                panel.innerHTML = html + `<div style="padding:10px;color:#aaa;">No visible aircraft.</div>`;
                return;
            }

            const closest = [...visiblePlanes].sort((a, b) => (a.distance_miles || 999) - (b.distance_miles || 999))[0];
            const fastest = [...visiblePlanes].sort((a, b) => (b.speed || 0) - (a.speed || 0))[0];
            const highest = [...visiblePlanes].sort((a, b) => getAltitudeValue(b) - getAltitudeValue(a))[0];
            const hottest = [...visiblePlanes].map((plane) => ({ ...plane, score: (plane.analysis || analyzeAircraft(plane)).score })).sort((a, b) => b.score - a.score)[0];

            const rows = [
                ["Closest", closest, `${closest.distance_miles} mi`],
                ["Highest", highest, getAltitudeDisplay(highest)],
                ["Fastest", fastest, `${Math.round(fastest.speed || 0)} kt`],
                ["Hot", hottest, `${hottest.score}`],
            ];

            rows.forEach(([label, plane, value]) => {
                html += `
                    <div onclick="focusAircraftByHex('${plane.icao_hex}')" style="display:grid;grid-template-columns:90px 1fr 70px;padding:7px 8px;border-bottom:1px solid #333;cursor:pointer;font-size:12px;">
                        <div><strong>${label}</strong></div>
                        <div><strong>${getAircraftBadges(plane)} ${plane.tail_number || plane.callsign || plane.icao_hex}</strong><br><span style="color:#aaa;">${plane.callsign || plane.icao_hex}</span></div>
                        <div><strong>${value}</strong></div>
                    </div>
                `;
            });

            panel.innerHTML = html;
        }

function updateMilitaryAlerts(planes) {
            const panel = $("military-alerts-panel");
            const military = planes
                .filter((plane) => plane.category === "Military")
                .sort((a, b) => (a.distance_miles || 999) - (b.distance_miles || 999));

            if (military.length === 0) {
                panel.innerHTML = `<div style="padding:10px;"><strong>Military Alerts</strong><br>None active</div>`;
                return;
            }

            let html = `<div style="padding:10px;"><strong>Military Alerts</strong></div>`;

            military.slice(0, 8).forEach((plane) => {
                html += `
                    <div onclick="focusAircraftByHex('${plane.icao_hex}')" style="padding:7px 10px;border-top:1px solid #aa0000;cursor:pointer;">
                        <strong>${getAircraftBadges(plane)} ${plane.callsign || plane.icao_hex}</strong><br>
                        ${plane.aircraft_type || "Unknown"} | ${plane.distance_miles} mi | ${getAltitudeDisplay(plane)} | ${Math.round(plane.speed || 0)} kt
                    </div>
                `;
            });

            panel.innerHTML = html;
        }

function updateSidebarHeaderCounts(planes) {
            const militaryPlanes = planes.filter((plane) => plane.category === "Military");
            const visiblePlanes = planes.filter((plane) => shouldShowPlane(plane));

            $("aircraft-list-header-count").innerText = visiblePlanes.length;
            $("favorites-header-count").innerText = state.favoriteAircraft.size;
            $("military-header-count").innerText = militaryPlanes.length;
            $("notifications-header-count").innerText = state.notifications.length;
        }
