let eventsChart = null;
let summaryChart = null;
let activeRunId = null;

const palette = [
  '#0f766e', '#2563eb', '#dc2626', '#7c3aed',
  '#ea580c', '#16a34a', '#db2777', '#0891b2'
];

async function fetchRuns() {
  const response = await fetch('/api/runs/');
  if (!response.ok) throw new Error('Errore nel caricamento dei run');
  return await response.json();
}

async function fetchRunDetail(runId) {
  const response = await fetch(`/api/runs/${runId}/`);
  if (!response.ok) throw new Error('Errore nel caricamento del dettaglio run');
  return await response.json();
}

function renderRunList(runs) {
  const container = document.getElementById('runList');
  container.innerHTML = '';

  runs.forEach((run, index) => {
    const item = document.createElement('div');
    item.className = 'run-item';
    item.dataset.runId = run.id;
    item.innerHTML = `
      <strong>Run #${run.id}</strong><br>
      <span class="muted">DOY ${run.first_doy} - ${run.last_doy}</span><br>
      <span class="muted">Snapshot: ${run.snapshot_count}</span>
    `;

    item.addEventListener('click', async () => {
      document.querySelectorAll('.run-item').forEach(el => el.classList.remove('active'));
      item.classList.add('active');
      activeRunId = run.id;
      const detail = await fetchRunDetail(run.id);
      renderRunDetail(detail);
    });

    container.appendChild(item);

    if (index === 0) {
      item.classList.add('active');
      activeRunId = run.id;
    }
  });
}

function renderStats(detail) {
  const run = detail.run;
  const snapshots = detail.snapshots;
  const eventCount = detail.event_series.length;

  document.getElementById('stats').innerHTML = `
    <div class="stat">
      <div class="label">Run ID</div>
      <div class="value">${run.id}</div>
    </div>
    <div class="stat">
      <div class="label">Intervallo DOY</div>
      <div class="value">${run.first_doy}-${run.last_doy}</div>
    </div>
    <div class="stat">
      <div class="label">Eventi distinti</div>
      <div class="value">${eventCount}</div>
    </div>
    <div class="stat">
      <div class="label">Snapshot salvati</div>
      <div class="value">${snapshots.length}</div>
    </div>
  `;
}

function renderEventsChart(detail) {
  const labels = detail.summary_by_day.map(row => row.doy);

  const datasets = detail.event_series.map((series, i) => ({
    label: `Evento ${series.event_index}`,
    data: series.points.map(p => p.x_value),
    borderColor: palette[i % palette.length],
    backgroundColor: palette[i % palette.length],
    borderWidth: 2,
    spanGaps: false,
    tension: 0.25
  }));

  if (eventsChart) eventsChart.destroy();

  const ctx = document.getElementById('eventsChart').getContext('2d');
  eventsChart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      interaction: { mode: 'nearest', intersect: false },
      scales: {
        y: {
          min: 0,
          max: 1,
          title: { display: true, text: 'X' }
        },
        x: {
          title: { display: true, text: 'DOY' }
        }
      }
    }
  });
}

function renderSummaryChart(detail) {
  const labels = detail.summary_by_day.map(row => row.doy);

  const datasets = [
    {
      label: 'Eventi attivi',
      data: detail.summary_by_day.map(row => row.active_events),
      borderColor: '#2563eb',
      backgroundColor: '#2563eb',
      borderWidth: 2,
      tension: 0.25,
      yAxisID: 'y'
    },
    {
      label: 'X medio',
      data: detail.summary_by_day.map(row => row.mean_x),
      borderColor: '#dc2626',
      backgroundColor: '#dc2626',
      borderWidth: 2,
      tension: 0.25,
      yAxisID: 'y1'
    }
  ];

  if (summaryChart) summaryChart.destroy();

  const ctx = document.getElementById('summaryChart').getContext('2d');
  summaryChart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      interaction: { mode: 'nearest', intersect: false },
      scales: {
        y: {
          beginAtZero: true,
          position: 'left',
          title: { display: true, text: 'Eventi attivi' }
        },
        y1: {
          beginAtZero: true,
          max: 1,
          position: 'right',
          grid: { drawOnChartArea: false },
          title: { display: true, text: 'X medio' }
        }
      }
    }
  });
}

function renderSnapshotTable(detail) {
  const body = document.getElementById('snapshotTable');
  body.innerHTML = '';

  detail.snapshots.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.doy}</td>
      <td>${row.event_index}</td>
      <td>${Number(row.x_value).toFixed(4)}</td>
    `;
    body.appendChild(tr);
  });
}

function renderRunDetail(detail) {
  renderStats(detail);
  renderEventsChart(detail);
  renderSummaryChart(detail);
  renderSnapshotTable(detail);
}

async function initDashboard() {
  try {
    const runs = await fetchRuns();
    renderRunList(runs);

    if (runs.length > 0) {
      const detail = await fetchRunDetail(runs[0].id);
      renderRunDetail(detail);
    } else {
      document.getElementById('runList').innerHTML = "<p class='muted'>Nessun run disponibile.</p>";
    }
  } catch (error) {
    document.getElementById('runList').innerHTML = `<p class='muted'>${error.message}</p>`;
  }
}

initDashboard();
