/* contribute.js - the "Add / Review Mandal" page */

let pickMap = null;
let pinMarker = null;
let config = null;

document.addEventListener("DOMContentLoaded", init);

async function init() {
  try {
    config = await api("/api/config");
    const mandals = await api("/api/mandals");
    fillAreas(config.areas);
    fillMandalSelects(mandals);
  } catch (err) {
    setStatus(err.message, true);
  }

  document.querySelectorAll(".option").forEach((btn) =>
    btn.addEventListener("click", () => showPanel(btn.dataset.target)));

  document.getElementById("form-add").addEventListener("submit", submitAdd);
  document.getElementById("form-review").addEventListener("submit", submitReview);
  document.getElementById("form-photos").addEventListener("submit", submitPhoto);

  // Deep links such as /contribute?mandal=3#review
  const hash = location.hash.replace("#", "");
  if (["add", "review", "photos"].includes(hash)) showPanel(hash);
  const preselect = new URLSearchParams(location.search).get("mandal");
  if (preselect) document.querySelectorAll(".mandal-select").forEach((s) => (s.value = preselect));
}

/* ---------------------------------------------------------- helpers */
function setStatus(message, isError = false) {
  const el = document.getElementById("status");
  el.textContent = message;
  el.className = "status " + (message ? (isError ? "error" : "ok") : "");
}

function fillAreas(areas) {
  document.getElementById("add-area").innerHTML =
    `<option value="">Choose an area</option>` +
    areas.map((a) => `<option value="${esc(a)}">${esc(a)}</option>`).join("");
}

function fillMandalSelects(mandals) {
  const options = `<option value="">Choose a mandal</option>` +
    mandals.map((m) => `<option value="${m.id}">${esc(m.name)}</option>`).join("");
  document.querySelectorAll(".mandal-select").forEach((s) => (s.innerHTML = options));
}

function showPanel(name) {
  setStatus("");
  ["add", "review", "photos"].forEach((p) => {
    document.getElementById(`panel-${p}`).hidden = p !== name;
  });
  document.querySelectorAll(".option").forEach((b) =>
    b.setAttribute("aria-selected", String(b.dataset.target === name)));
  history.replaceState(null, "", `${location.search}#${name}`);
  if (name === "add") initPickMap();
  document.getElementById(`panel-${name}`).scrollIntoView({ behavior: "smooth", block: "start" });
}

/* --------------------------------------------------- location picker */
function initPickMap() {
  if (pickMap || !config) {
    if (pickMap) setTimeout(() => pickMap.invalidateSize(), 50); // panel was hidden
    return;
  }
  pickMap = makeMap("pick-map", config.bounds);
  pickMap.on("click", (e) => placePin(e.latlng));
  setTimeout(() => pickMap.invalidateSize(), 50);
}

function placePin(latlng) {
  if (!pinMarker) {
    pinMarker = L.marker(latlng, { draggable: true }).addTo(pickMap);
    pinMarker.on("dragend", () => updateReadout(pinMarker.getLatLng()));
  } else {
    pinMarker.setLatLng(latlng);
  }
  updateReadout(latlng);
}

function updateReadout(ll) {
  document.getElementById("pin-readout").textContent =
    `Pin placed at ${ll.lat.toFixed(5)}, ${ll.lng.toFixed(5)}`;
}

/* ------------------------------------------------------------ submits */
async function submitAdd(e) {
  e.preventDefault();
  const form = e.target;
  if (!pinMarker) return setStatus("Please click the map to place the pin.", true);
  const ll = pinMarker.getLatLng();
  const payload = {
    name: form.name.value,
    area: form.area.value,
    nearest_station: form.nearest_station.value,
    established_year: form.established_year.value,
    description: form.description.value,
    lat: ll.lat,
    lng: ll.lng,
  };
  try {
    await api("/api/mandals", jsonPost(payload));
    setStatus("Thank you! The mandal has been added to the map.");
    form.reset();
    pinMarker.remove();
    pinMarker = null;
    document.getElementById("pin-readout").textContent = "No pin placed yet.";
    refreshMandalSelects();
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function submitReview(e) {
  e.preventDefault();
  const form = e.target;
  if (!form.mandal_id.value) return setStatus("Please choose a mandal.", true);
  const payload = {
    reviewer: form.reviewer.value,
    overall: form.overall.value,
    crowd: form.crowd.value,
    parking: form.parking.value,
    comment: form.comment.value,
  };
  try {
    await api(`/api/mandals/${form.mandal_id.value}/reviews`, jsonPost(payload));
    setStatus("Thank you! Your review has been saved.");
    form.reset();
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function submitPhoto(e) {
  e.preventDefault();
  const form = e.target;
  if (!form.mandal_id.value) return setStatus("Please choose a mandal.", true);
  if (!form.photo.files.length) return setStatus("Please choose a photo.", true);
  const body = new FormData();
  body.append("photo", form.photo.files[0]);
  body.append("uploader", form.uploader.value);
  try {
    await api(`/api/mandals/${form.mandal_id.value}/photos`, { method: "POST", body });
    setStatus("Thank you! Your photo has been uploaded.");
    form.reset();
  } catch (err) {
    setStatus(err.message, true);
  }
}

function jsonPost(payload) {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  };
}

async function refreshMandalSelects() {
  try { fillMandalSelects(await api("/api/mandals")); } catch (_) { /* keep old list */ }
}
