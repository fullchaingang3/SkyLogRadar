function destinationPoint(lat, lon, bearingDeg, distanceMiles) {
            const R = 3958.8;
            const bearing = bearingDeg * Math.PI / 180;
            const distance = distanceMiles / R;
            const lat1 = lat * Math.PI / 180;
            const lon1 = lon * Math.PI / 180;

            const lat2 = Math.asin(
                Math.sin(lat1) * Math.cos(distance)
                + Math.cos(lat1) * Math.sin(distance) * Math.cos(bearing),
            );

            const lon2 = lon1 + Math.atan2(
                Math.sin(bearing) * Math.sin(distance) * Math.cos(lat1),
                Math.cos(distance) - Math.sin(lat1) * Math.sin(lat2),
            );

            return [lat2 * 180 / Math.PI, lon2 * 180 / Math.PI];
        }

function getAltitudeValue(plane) {
            if (!plane.altitude) {
                return -1;
            }

            const alt = String(plane.altitude).toUpperCase();

            if (alt === "GROUND" || alt === "GND") {
                return -1;
            }

            return parseInt(alt, 10) || 0;
        }

function getAltitudeDisplay(plane) {
            const alt = getAltitudeValue(plane);

            if (alt < 0) {
                return `<span class="altitude-pill alt-ground">GROUND</span>`;
            }

            if (alt < 5000) {
                return `<span class="altitude-pill alt-low">${alt.toLocaleString()} ft</span>`;
            }

            if (alt < 20000) {
                return `<span class="altitude-pill alt-medium">${alt.toLocaleString()} ft</span>`;
            }

            return `<span class="altitude-pill alt-high">${alt.toLocaleString()} ft</span>`;
        }

function getColor(category) {
            if (category === "Civilian") return "Green";
            if (category === "Commercial") return "Blue";
            if (category === "Military") return "red";
            return "yellow";
        }

function getScoreStars(score) {
            if (score >= 90) return "★★★★★";
            if (score >= 70) return "★★★★☆";
            if (score >= 50) return "★★★☆☆";
            if (score >= 25) return "★★☆☆☆";
            return "★☆☆☆☆";
        }

function getAircraftPhotoUrl(plane) {
            if (!plane.tail_number) {
                return "";
            }

            return `https://www.planespotters.net/search?q=${encodeURIComponent(plane.tail_number)}`;
        }

function heatmapEnabled() {
            return $("toggle-heatmap").checked;
        }

function labelsEnabled() {
            return $("toggle-labels").checked;
        }

function sweepEnabled() {
            return $("toggle-sweep").checked;
        }

function trailsEnabled() {
            return $("toggle-trails").checked;
        }

function shouldShowPlane(plane) {
    if (state.missionMode) {
        const analysis = plane.analysis || analyzeAircraft(plane);

        return (
            analysis.score >= 70
            || state.favoriteAircraft.has(plane.icao_hex)
        );
    }

            if (plane.category === "Civilian") return $("filter-civilian").checked;
            if (plane.category === "Commercial") return $("filter-commercial").checked;
            if (plane.category === "Military") return $("filter-military").checked;
            return $("filter-unknown").checked;
        }
/* ------------------------------------------------------------------
   Function: isFavorite
   Returns true if the aircraft is saved as a favorite.
------------------------------------------------------------------ */
function isFavorite(hex) {
    return state.favoriteAircraft.has(hex);
}