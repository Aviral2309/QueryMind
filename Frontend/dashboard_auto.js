let dashCharts = {};

async function initDash() {
  if (!isLoggedIn()) {
    window.location.href = "index.html"; return;
  }
  await loadDashboard();
}

function showSection(name) {
  document.querySelectorAll(".dash-section").forEach(s =>
    s.classList.toggle("hidden", !s.id.endsWith(name))
  );
  document.querySelectorAll(".dash-nav-btn").forEach(b =>
    b.classList.toggle("active",
      b.textContent.toLowerCase().includes(name))
  );
  if (name === "profiler") loadProfiler();
  if (name === "history")  loadHistory();
}

async function loadDashboard() {
  try {
    const res  = await fetch(`${API}/dashboard`, {
      headers: authHeaders()
    });

    if (!res.ok) {
      if (res.status === 400) {
        document.getElementById("kpi-grid").innerHTML =
          `<p class="empty-hint">
            No database connected.
            <a href="index.html">Connect one</a>
          </p>`;
        return;
      }
    }

    const data = await res.json();
    renderKPIs(data.kpis || []);
    renderTables(data.tables || []);
    renderCharts(data.charts || []);
    loadPerfChart();

  } catch (e) {
    document.getElementById("kpi-grid").innerHTML =
      `<p class="empty-hint">Failed to load dashboard.</p>`;
  }
}

function renderKPIs(kpis) {
  const el = document.getElementById("kpi-grid");
  if (!kpis || kpis.length === 0) {
    el.innerHTML = `<p class="empty-hint">No KPI data available.</p>`;
    return;
  }
  el.innerHTML = kpis.map(k => `
    <div class="kpi-card">
      <div class="kpi-val">${esc(k.value)}</div>
      <div class="kpi-label">${esc(k.label)}</div>
      ${k.sub ? `<div class="kpi-sub">${esc(k.sub)}</div>` : ""}
    </div>`).join("");
}

function renderTables(tables) {
  const el = document.getElementById("tables-grid");
  if (!tables || tables.length === 0) {
    el.innerHTML = `<p class="empty-hint">No tables found.</p>`;
    return;
  }
  el.innerHTML = tables.map(t => `
    <div class="table-card">
      <div class="table-card-name">${esc(t.name)}</div>
      <div class="table-card-meta">
        <span>${Number(t.row_count).toLocaleString()} rows</span>
        <span>${t.col_count} columns</span>
      </div>
    </div>`).join("");
}

function renderCharts(charts) {
  const el = document.getElementById("charts-grid");
  if (!charts || charts.length === 0) {
    el.innerHTML = `<p class="empty-hint">No charts generated.</p>`;
    return;
  }
  el.innerHTML = charts.map((c, i) => `
    <div class="chart-card">
      <div class="chart-card-title">${esc(c.title)}</div>
      <div class="chart-card-wrap">
        <canvas id="dash-chart-${i}"></canvas>
      </div>
    </div>`).join("");

  charts.forEach((c, i) => {
    setTimeout(() => {
      const canvas = document.getElementById(`dash-chart-${i}`);
      if (!canvas || !window.Chart) return;
      if (dashCharts[i]) dashCharts[i].destroy();
      Chart.defaults.color       = "#6b7280";
      Chart.defaults.borderColor = "rgba(0,0,0,0.06)";
      dashCharts[i] = new Chart(canvas, c.data);
    }, i * 50);
  });
}

async function loadPerfChart() {
  try {
    const res  = await fetch(
      `${API}/analytics/trend`, { headers: authHeaders() });
    const data = await res.json();

    const canvas = document.getElementById("perf-chart");
    if (!canvas) return;
    if (dashCharts["perf"]) dashCharts["perf"].destroy();

    Chart.defaults.color       = "#6b7280";
    Chart.defaults.borderColor = "rgba(0,0,0,0.06)";

    dashCharts["perf"] = new Chart(canvas, {
      type: "line",
      data: {
        labels:   data.map(d => d.date),
        datasets: [{
          label:           "Accuracy Score",
          data:            data.map(d => d.avg_score || 0),
          borderColor:     "#dc2626",
          backgroundColor: "rgba(220,38,38,0.08)",
          borderWidth:     2,
          tension:         0.4,
          fill:            true,
          pointRadius:     3,
          pointBackgroundColor: "#dc2626"
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { font: { size: 11 } },
               grid:  { color: "rgba(0,0,0,0.04)" } },
          y: { min: 0, max: 100,
               ticks: { font: { size: 11 },
                        callback: v => v + "%" },
               grid: { color: "rgba(0,0,0,0.04)" } }
        }
      }
    });
  } catch (e) { /* silent */ }
}

async function loadProfiler() {
  const el = document.getElementById("profiler-content");
  el.innerHTML = `<p class="empty-hint">Loading...</p>`;
  try {
    const res  = await fetch(
      `${API}/profile/db`, { headers: authHeaders() });
    const data = await res.json();

    if (data.error) {
      el.innerHTML = `<p class="empty-hint">${esc(data.error)}</p>`;
      return;
    }

    el.innerHTML = Object.entries(data).map(([table, info]) => {
      if (info.error) return `
        <div class="profiler-table">
          <div class="profiler-table-name">${esc(table)}</div>
          <p class="empty-hint">Error: ${esc(info.error)}</p>
        </div>`;

      const colRows = Object.entries(info.stats || {}).map(
        ([col, s]) => `
          <tr>
            <td class="profiler-col-name">${esc(col)}</td>
            <td>${esc(s.type)}</td>
            <td>${s.null_pct}%</td>
            <td>${s.unique_count}</td>
            <td>${s.is_numeric
              ? `${s.min} / ${s.avg} / ${s.max}`
              : "—"}</td>
          </tr>`
      ).join("");

      return `
        <div class="profiler-table">
          <div class="profiler-table-header">
            <span class="profiler-table-name">${esc(table)}</span>
            <span class="profiler-table-meta">
              ${Number(info.row_count).toLocaleString()} rows &middot;
              ${info.column_count} columns
            </span>
          </div>
          <div class="profiler-table-body">
            <table class="profiler-data-table">
              <thead>
                <tr>
                  <th>Column</th>
                  <th>Type</th>
                  <th>Nulls</th>
                  <th>Unique</th>
                  <th>Min / Avg / Max</th>
                </tr>
              </thead>
              <tbody>${colRows}</tbody>
            </table>
          </div>
        </div>`;
    }).join("");

  } catch (e) {
    el.innerHTML = `<p class="empty-hint">Failed to load profiler.</p>`;
  }
}

async function loadHistory() {
  const el = document.getElementById("history-content");
  el.innerHTML = `<p class="empty-hint">Loading...</p>`;
  try {
    const res  = await fetch(
      `${API}/history`, { headers: authHeaders() });
    const data = await res.json();

    if (!data || data.length === 0) {
      el.innerHTML = `<p class="empty-hint">No queries yet.</p>`;
      return;
    }

    el.innerHTML = `
      <div class="history-table-wrap">
        <table class="history-data-table">
          <thead>
            <tr>
              <th>Question</th>
              <th>Status</th>
              <th>Rows</th>
              <th>Time</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            ${data.map(q => `
              <tr>
                <td class="history-q">
                  ${esc((q.question || "").slice(0,70))}
                  ${(q.question || "").length > 70 ? "…" : ""}
                </td>
                <td>
                  <span class="status-pill ${q.success ? "ok" : "fail"}">
                    ${q.success ? "OK" : "Failed"}
                  </span>
                </td>
                <td>${q.row_count || 0}</td>
                <td>${q.response_ms || 0}ms</td>
                <td class="history-date">
                  ${(q.timestamp || "").split(" ")[0]}
                </td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>`;
  } catch (e) {
    el.innerHTML = `<p class="empty-hint">Failed to load history.</p>`;
  }
}

function esc(s) {
  return String(s || "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

document.addEventListener("DOMContentLoaded", initDash);