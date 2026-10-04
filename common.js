/* common.js - small helpers shared by both pages */

// Escape user-written text before putting it into HTML.
// Without this, someone could submit a mandal named "<script>...</script>"
// and run code in every visitor's browser (XSS).
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// fetch() wrapper: returns parsed JSON, or throws Error(message from server).
async function api(url, options) {
  const res = await fetch(url, options);
  let data = {};
  try { data = await res.json(); } catch (_) { /* no JSON body */ }
  if (!res.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}

// Google Maps link. Seeded mandals use a name search (finds the real place
// even if our pin is approximate); user-added mandals use their exact pin.
function mapsUrl(m) {
  const query = m.maps_query ? m.maps_query : `${m.lat},${m.lng}`;
  return "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(query);
}

function crowdLabel(avg) {
  if (avg === null || avg === undefined) return "No data";
  if (avg <= 2) return "Light";
  if (avg <= 3.5) return "Moderate";
  return "Very crowded";
}

function parkingLabel(avg) {
  if (avg === null || avg === undefined) return "No data";
  if (avg <= 2) return "Hard";
  if (avg <= 3.5) return "Limited";
  return "Easy";
}

function ratingText(avg) {
  return avg === null || avg === undefined ? "Not rated" : `${avg.toFixed(1)} / 5`;
}

// Map limits come from the server so Python is the single source of truth.
function boundsToLeaflet(b) {
  return L.latLngBounds([b.south, b.west], [b.north, b.east]);
}

function makeMap(elementId, bounds) {
  const map = L.map(elementId, {
    maxBounds: boundsToLeaflet(bounds),
    maxBoundsViscosity: 1.0,   // makes the edge "solid" when dragging
    minZoom: 12,
    maxZoom: 18,
    zoomControl: true,
  }).fitBounds(boundsToLeaflet(bounds));
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  return map;
}
