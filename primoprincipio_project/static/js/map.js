function readMapData() {
  const el = document.getElementById('map');
  return {
    risk: {
      level: el.dataset.riskLevel,
      color: el.dataset.riskColor,
      action: el.dataset.riskAction
    },
    currentDD: el.dataset.currentDd,
    threshold: el.dataset.threshold,
    position: {
      lat: Number(el.dataset.pinLat),
      lng: Number(el.dataset.pinLng)
    }
  };
}

function pinColor(color) {
  if (color === 'red') return 'https://maps.google.com/mapfiles/ms/icons/red-dot.png';
  if (color === 'yellow') return 'https://maps.google.com/mapfiles/ms/icons/yellow-dot.png';
  return 'https://maps.google.com/mapfiles/ms/icons/green-dot.png';
}

function buildLegend() {
  const legend = document.createElement('div');
  legend.className = 'map-legend';
  legend.innerHTML = `
    <div class="map-legend-row">
      <span class="dot green"></span>
      <span>Rischio assente</span>
    </div>
    <div class="map-legend-row">
      <span class="dot yellow"></span>
      <span>Rischio medio</span>
    </div>
    <div class="map-legend-row">
      <span class="dot red"></span>
      <span>Rischio alto</span>
    </div>
  `;
  return legend;
}

function initMap() {
  const { risk, currentDD, threshold, position } = readMapData();

  const map = new google.maps.Map(document.getElementById('map'), {
    center: position,
    zoom: 13,
    mapTypeId: 'satellite',
    fullscreenControl: true,
    mapTypeControl: false,
    streetViewControl: false,
    rotateControl: false
  });

  const marker = new google.maps.Marker({
    position,
    map,
    icon: pinColor(risk.color),
    title: `Rischio ${risk.level.toUpperCase()}`
  });

  const isHighRisk = risk.level.toUpperCase() === 'ALTO';

  const assistenzaLink = isHighRisk
    ? ' <a href="https://wiki.wiforagri.com/wiki/assistenza" target="_blank" rel="noopener noreferrer">ASSISTENZA</a>'
    : '';

  const info = new google.maps.InfoWindow({
    content: `
      <div class="info-window">
        <div class="info-badge ${risk.color}">Rischio ${risk.level.toUpperCase()}</div>
        <div class="info-row"><strong>Gradi Giorno:</strong> ${currentDD}</div>
        <div class="info-row"><strong>Soglia:</strong> ${threshold}</div>
        <div class="info-row"><strong>Azione:</strong> ${risk.action}${assistenzaLink}</div>
      </div>
    `
  });

  const legend = buildLegend();
  map.controls[google.maps.ControlPosition.LEFT_BOTTOM].push(legend);


  let closeTimer = null;
  const closeDelay = 300; // ms

  function scheduleClose() {
    clearTimeout(closeTimer);
    closeTimer = setTimeout(() => info.close(), closeDelay);
  }

  function cancelClose() {
    clearTimeout(closeTimer);
  }

  marker.addListener('mouseover', () => {
    cancelClose();
    info.open({ anchor: marker, map });
  });

  marker.addListener('mouseout', scheduleClose);

  google.maps.event.addListener(info, 'domready', () => {
    const bubble = document.querySelector('.info-window')?.closest('.gm-style-iw');
    if (!bubble) return;

    bubble.addEventListener('mouseenter', cancelClose);
    bubble.addEventListener('mouseleave', scheduleClose);
  });

  // Il click sul marker naviga al modello: comportamento invariato.
  marker.addListener('click', () => {
    window.location.href = '/model/';
  });
}

window.initMap = initMap;
