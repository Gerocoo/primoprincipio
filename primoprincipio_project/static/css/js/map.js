let mapInstance = null;
let markerInstance = null;

function readMapData() {
  const el = document.getElementById("map-data");
  return {
    riskLevel: el.dataset.riskLevel,
    riskColor: el.dataset.riskColor,
    riskAction: el.dataset.riskAction,
    currentDd: el.dataset.currentDd,
    threshold: el.dataset.threshold,
    pinLat: parseFloat(el.dataset.pinLat),
    pinLng: parseFloat(el.dataset.pinLng),
    googleKey: el.dataset.googleKey
  };
}

function pinColor(color) {
  if (color === "red") return "https://maps.google.com/mapfiles/ms/icons/red-dot.png";
  if (color === "yellow") return "https://maps.google.com/mapfiles/ms/icons/yellow-dot.png";
  return "https://maps.google.com/mapfiles/ms/icons/green-dot.png";
}

function buildLegend() {
  const legend = document.createElement("div");
  legend.className = "map-legend";
  legend.innerHTML = `
    <div class="map-legend-row"><span class="dot green"></span><span>Rischio assente</span></div>
    <div class="map-legend-row"><span class="dot yellow"></span><span>Rischio medio</span></div>
    <div class="map-legend-row"><span class="dot red"></span><span>Rischio alto</span></div>
  `;
  return legend;
}

function initMap() {
  const data = readMapData();
  const position = { lat: data.pinLat, lng: data.pinLng };

  mapInstance = new google.maps.Map(document.getElementById("map"), {
    center: position,
    zoom: 13,
    mapTypeId: "satellite",
    fullscreenControl: true,
    mapTypeControl: false,
    streetViewControl: false,
    rotateControl: false
  });

  markerInstance = new google.maps.Marker({
    position,
    map: mapInstance,
    icon: pinColor(data.riskColor),
    title: `Rischio ${data.riskLevel.toUpperCase()}`
  });

  const isHighRisk = data.riskLevel.toUpperCase() === "ALTO";
  const assistenzaLink = isHighRisk
    ? ' <a href="https://wiki.wiforagri.com/wiki/assistenza" target="_blank" rel="noopener noreferrer">ASSISTENZA</a>'
    : "";

  const info = new google.maps.InfoWindow({
    content: `
      <div class="info-window">
        <div class="info-badge ${data.riskColor}">Rischio ${data.riskLevel.toUpperCase()}</div>
        <div class="info-row"><strong>Gradi Giorno:</strong> ${data.currentDd}</div>
        <div class="info-row"><strong>Soglia:</strong> ${data.threshold}</div>
        <div class="info-row"><strong>Azione:</strong> ${data.riskAction}${assistenzaLink}</div>
      </div>
    `
  });

  const legend = buildLegend();
  mapInstance.controls[google.maps.ControlPosition.LEFT_BOTTOM].push(legend);

  let closeTimer = null;
  const closeDelay = 300;

  function scheduleClose() {
    clearTimeout(closeTimer);
    closeTimer = setTimeout(() => info.close(), closeDelay);
  }

  function cancelClose() {
    clearTimeout(closeTimer);
  }

  markerInstance.addListener("mouseover", () => {
    cancelClose();
    info.open({ anchor: markerInstance, map: mapInstance });
  });

  markerInstance.addListener("mouseout", scheduleClose);

  google.maps.event.addListener(info, "domready", () => {
    const bubble = document.querySelector(".info-window")?.closest(".gm-style-iw");
    if (!bubble) return;
    bubble.addEventListener("mouseenter", cancelClose);
    bubble.addEventListener("mouseleave", scheduleClose);
  });

  markerInstance.addListener("click", () => {
    window.location.href = "/model/";
  });
}

window.initMap = initMap;