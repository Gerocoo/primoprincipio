const degreeDays = JSON.parse(document.getElementById('degree-days-data').textContent);
const modelConfig = document.getElementById('model-config');
const modelThreshold = parseFloat(modelConfig.dataset.threshold);
const todayIndex = parseInt(modelConfig.dataset.todayIndex, 10);


function renderChart(alertThresholds = []) {
  const categories = degreeDays.map(item => 'DOY ' + item.doy);
  const series = degreeDays.map(item => Number(item.degree_day));
  const maxSeries = Math.max(...series, 0);
  const yMax = Math.max(maxSeries, modelThreshold) * 1.10;

  const yPlotLines = [
    {
      color: '#ff9800',
      width: 2,
      value: modelThreshold,
      dashStyle: 'ShortDash',
      zIndex: 5,
      label: {
        text: 'Soglia Sordidus = ' + modelThreshold,
        align: 'left',
        x: 10,
        y: -8,
        useHTML: false,
        style: {
          color: '#ff9800',
          fontSize: '12px',
          fontWeight: '700',
          textOutline: 'none'
        }
      }
    }
  ];

  alertThresholds.filter(a => a.active).forEach(a => {
    yPlotLines.push({
      color: '#c62828',
      width: 1.5,
      value: Number(a.threshold),
      dashStyle: 'Dot',
      zIndex: 4,
      label: {
        text: 'Allarme ' + a.threshold,
        align: 'right',
        x: -10,
        y: -4,
        style: {
          color: '#c62828',
          fontSize: '11px',
          fontWeight: '600',
          textOutline: 'none'
        }
      }
    });
  });

  Highcharts.chart('chart', {
    chart: {
      type: 'line',
      spacingTop: 30
    },
    title: {
      text: 'Gradi Giorno cumulati'
    },
    xAxis: {
      categories,
      plotLines: Number.isInteger(todayIndex) && todayIndex >= 0 ? [{
        color: '#d32f2f',
        width: 2,
        value: todayIndex,
        zIndex: 5,
        label: {
          text: 'Today'
        }
      }] : []
    },
    yAxis: {
      min: 0,
      max: yMax,
      title: {
        text: 'Gradi Giorno'
      },
      plotLines: yPlotLines
    },
    series: [{
      name: 'Gradi Giorno',
      data: series
    }],
    credits: {
      enabled: false
    }
  });
}


async function loadAlerts() {
  const res = await fetch('/api/alerts/list/');
  const data = await res.json();

  const box = document.getElementById('alerts-list');
  box.innerHTML = data.map(item => `
    <div class="alert-item">
      <div><strong>${item.threshold}</strong> - ${item.email} - ${item.active ? 'attiva' : 'disattivata'}</div>
      <div class="actions">
        <button onclick="toggleAlert(${item.id}, ${!item.active})">${item.active ? 'Disattiva' : 'Attiva'}</button>
        <button onclick="deleteAlert(${item.id})">Cancella</button>
      </div>
    </div>
  `).join('');

  renderChart(data);
}


document.getElementById('alert-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const payload = {
    threshold: fd.get('threshold'),
    email: fd.get('email')
  };

  const res = await fetch('/api/alerts/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    alert('Errore salvataggio soglia');
    return;
  }

  e.target.reset();
  loadAlerts();
});


async function toggleAlert(id, active) {
  await fetch('/api/alerts/', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, active })
  });
  loadAlerts();
}


async function deleteAlert(id) {
  const res = await fetch('/api/alerts/', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id })
  });
  const data = await res.json();
  if (data.error) alert(data.error);
  loadAlerts();
}


loadAlerts();