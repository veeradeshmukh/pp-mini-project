/* main.js - home page: map, filters, mandal cards, detail dialog */

let mandals = [];
const markers = {};   // mandal id -> Leaflet marker
let map;

document.addEventListener("DOMContentLoaded", init);

async function init() {
  try {
    const [config, list] = await Promise.all([api("/api/config"), api("/api/mandals")]);
    mandals = list;
    map = makeMap("map", config.bounds);
    addMarkers();
    fillAreaFilter();
    wireFilters();
    wireDialog();
    render();
  } catch (err) {
    document.getElementById("cards").innerHTML =
      `<p class="empty">Could not load mandals: ${esc(err.message)}</p>`;
  }
}

/* ------------------------------------------------------------- map */
function addMarkers() {
  mandals.forEach((m) => {
    const marker = L.marker([m.lat, m.lng], { title: m.name }).addTo(map);
    marker.bindPopup(popupHtml(m), { closeButton: false, offset: [0, -4] });

    // Hover opens the popup. The popup stays open until you click the map or
    // another pin, so you have time to move onto the button and tap it.
    marker.on("mouseover", () => marker.openPopup());
    // Phones have no hover, so a tap opens it too (Leaflet does this by default).
    markers[m.id] = marker;
  });
}

function popupHtml(m) {
  const approx = m.coords_verified ? "" : `<div class="popup-note">Pin is approximate</div>`;
  return `
    <div class="popup">
      <div class="popup-name">${esc(m.name)}</div>
      ${approx}
      <a class="maps-btn" href="${mapsUrl(m)}" target="_blank" rel="noopener noreferrer">
        Open in Google Maps
      </a>
    </div>`;
}

function showOnMap(id) {
  const m = mandals.find((x) => x.id === id);
  if (!m) return;
  document.getElementById("map-section").scrollIntoView({ behavior: "smooth", block: "start" });
  map.flyTo([m.lat, m.lng], 16, { duration: 0.8 });
  markers[id].openPopup();
}

/* --------------------------------------------------------- filters */
const filters = { search: "", area: "", minRating: 0, maxCrowd: 5, minParking: 0, sort: "name" };

function fillAreaFilter() {
  const areas = [...new Set(mandals.map((m) => m.area))].sort();
  document.getElementById("f-area").innerHTML =
    `<option value="">All areas</option>` +
    areas.map((a) => `<option value="${esc(a)}">${esc(a)}</option>`).join("");
}

function wireFilters() {
  const bind = (id, key, parse = (v) => v) =>
    document.getElementById(id).addEventListener("input", (e) => {
      filters[key] = parse(e.target.value);
      render();
    });
  bind("f-search", "search", (v) => v.trim().toLowerCase());
  bind("f-area", "area");
  bind("f-rating", "minRating", Number);
  bind("f-crowd", "maxCrowd", Number);
  bind("f-parking", "minParking", Number);
  bind("f-sort", "sort");

  document.getElementById("f-reset").addEventListener("click", () => {
    document.getElementById("filter-form").reset();
    Object.assign(filters, { search: "", area: "", minRating: 0, maxCrowd: 5, minParking: 0, sort: "name" });
    render();
  });
}

function passes(m) {
  if (filters.search && !(m.name + " " + m.area).toLowerCase().includes(filters.search)) return false;
  if (filters.area && m.area !== filters.area) return false;
  // Unrated mandals (no data) are hidden whenever a rating filter is active.
  if (filters.minRating > 0 && !(m.avg_overall >= filters.minRating)) return false;
  if (filters.maxCrowd < 5 && !(m.avg_crowd <= filters.maxCrowd)) return false;
  if (filters.minParking > 0 && !(m.avg_parking >= filters.minParking)) return false;
  return true;
}

function sorted(list) {
  const by = {
    name: (a, b) => a.name.localeCompare(b.name),
    rating: (a, b) => (b.avg_overall ?? -1) - (a.avg_overall ?? -1),
    crowd: (a, b) => (a.avg_crowd ?? 99) - (b.avg_crowd ?? 99),
    parking: (a, b) => (b.avg_parking ?? -1) - (a.avg_parking ?? -1),
  };
  return [...list].sort(by[filters.sort]);
}

/* ----------------------------------------------------------- cards */
function render() {
  const list = sorted(mandals.filter(passes));
  document.getElementById("result-count").textContent =
    `${list.length} of ${mandals.length} mandals`;
  const box = document.getElementById("cards");
  if (!list.length) {
    box.innerHTML = `<p class="empty">No mandals match these filters. Try loosening one.</p>`;
    return;
  }
  box.innerHTML = list.map(cardHtml).join("");
  box.querySelectorAll("[data-map]").forEach((b) =>
    b.addEventListener("click", () => showOnMap(Number(b.dataset.map))));
  box.querySelectorAll("[data-details]").forEach((b) =>
    b.addEventListener("click", () => openDetails(Number(b.dataset.details))));
}

function cardHtml(m) {
  const photo = m.cover_photo
    ? `<img class="card-photo" src="/static/uploads/${esc(m.cover_photo)}" alt="Photo of ${esc(m.name)}" loading="lazy">`
    : `<div class="card-photo placeholder" aria-hidden="true">Photo coming soon</div>`;
  const reviews = m.review_count
    ? `${m.review_count} review${m.review_count === 1 ? "" : "s"}`
    : "No visitor reviews yet";
  return `
    <article class="card">
      ${photo}
      <div class="card-body">
        <h3>${esc(m.name)}</h3>
        <p class="muted">${esc(m.area)}${m.established_year ? " &middot; since " + m.established_year : ""}</p>
        <dl class="stats">
          <div><dt>Rating</dt><dd>${ratingText(m.avg_overall)}</dd></div>
          <div><dt>Crowd</dt><dd>${crowdLabel(m.avg_crowd)}</dd></div>
          <div><dt>Parking</dt><dd>${parkingLabel(m.avg_parking)}</dd></div>
        </dl>
        <p class="muted small">${reviews}</p>
        <div class="card-actions">
          <button class="btn btn-ghost" data-map="${m.id}">Show on map</button>
          <button class="btn btn-ghost" data-details="${m.id}">Details</button>
        </div>
      </div>
    </article>`;
}

/* ---------------------------------------------------------- dialog */
function wireDialog() {
  const dlg = document.getElementById("details");
  document.getElementById("details-close").addEventListener("click", () => dlg.close());
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); }); // click backdrop
}

async function openDetails(id) {
  const dlg = document.getElementById("details");
  const body = document.getElementById("details-body");
  body.innerHTML = `<p class="muted">Loading...</p>`;
  dlg.showModal();
  try {
    const m = await api(`/api/mandals/${id}`);
    const photos = m.photos.length
      ? `<div class="gallery">${m.photos.map((p) =>
          `<img src="/static/uploads/${esc(p.filename)}" alt="Photo of ${esc(m.name)} by ${esc(p.uploader)}" loading="lazy">`).join("")}</div>`
      : `<p class="muted">No photos yet.</p>`;
    const reviews = m.reviews.length
      ? m.reviews.map((r) => `
          <div class="review">
            <strong>${esc(r.reviewer)}</strong>
            <span class="muted small">Rating ${r.overall}/5 &middot; Crowd ${r.crowd}/5 &middot; Parking ${r.parking}/5</span>
            ${r.comment ? `<p>${esc(r.comment)}</p>` : ""}
          </div>`).join("")
      : `<p class="muted">No visitor reviews yet. Be the first!</p>`;
    body.innerHTML = `
      <h2>${esc(m.name)}</h2>
      <p class="muted">${esc(m.area)}${m.nearest_station ? " &middot; Nearest station: " + esc(m.nearest_station) : ""}</p>
      ${m.description ? `<p>${esc(m.description)}</p>` : ""}
      <p><a class="btn btn-primary" href="${mapsUrl(m)}" target="_blank" rel="noopener noreferrer">Open in Google Maps</a>
         <a class="btn btn-ghost" href="/contribute?mandal=${m.id}#review">Write a review</a></p>
      <h3>Photos</h3>${photos}
      <h3>Reviews</h3>${reviews}`;
  } catch (err) {
    body.innerHTML = `<p class="empty">${esc(err.message)}</p>`;
  }
}
