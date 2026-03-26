let trendChart = null;
let usageChart = null;

async function initDashboard() {
  if (!isLoggedIn()) {
    window.location.href = "index.html";
    return;
  }
  await Promise.all([
    loadOverview(),
    loadUsageStats()
  ]);
}

// ── Section switching ─────────────────────────────────────────────────────────
function showSection(name) {
  document.querySelectorAll(".dash-section").forEach(s =>
    s.classList.toggle("hidden", !s.id.endsWith(name))
  );
  document.querySelectorAll(".dash-nav-item").forEach(a =>
    a.classList.toggle("active", a.textContent.toLowerCase().includes(name))
  );

  if (name === "accuracy") loadAccuracy();
  if (name === "queries")  loadQueryHistory();
}

// ── Overview ──────────────────────────────────────────────────────────────────
async function loadOverview() {
  try {
    const res  = await fetch(`${API}/ragas/summary`, {
      headers: authHeaders()
    });
    const data = await res.json();

    setValue("kpi-overall",    pct(data.overall_score));
    setValue("kpi-sql",        pct(data.sql_correctness));
    setValue("kpi-faith",      pct(data.faithfulness));
    setValue("kpi-relevancy",  pct(data.answer_relevancy));
    setValue("kpi-precision",  pct(data.context_precision));
    setValue("kpi-total",      data.total_evaluated || 0);

    const score = parseFloat(data.overall_score) || 0;
    const grade = score >= 85 ? "Excellent" :
                  score >= 70 ? "Good"      :
                  score >= 55 ? "Fair"      : "Needs improvement";
    setValue("kpi-overall-sub", grade);

    await loadTrendChart();
  } catch (e) { /* silent */ }
}

async function loadTrendChart() {
  try {
    const res  = await fetch(`${API}/ragas/trend?days=14`, {
      headers: authHeaders()
    });
    const data = await res.json();

    const labels     = data.map(d => d.date);
    const overall    = data.map(d => d.avg_score || 0);
    const sql        = data.map(d => d.sql_score  || 0);

    const canvas = document.getElementById("trend-chart");
    if (!canvas) return;
    if (trendChart) trendChart.destroy();

    Chart.defaults.color       = "#6b7280";
    Chart.defaults.borderColor = "rgba(255,255,255,0.04)";

    trendChart = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label:           "Overall Score",
            data:            overall,
            borderColor:     "rgba(220,38,38,1)",
            backgroundColor: "rgba(220,38,38,0.1)",
            borderWidth:     2,
            tension:         0.4,
            fill:            true,
            pointRadius:     4,
            pointBackgroundColor: "rgba(220,38,38,1)"
          },
          {
            label:           "SQL Score",
            data:            sql,
            borderColor:     "rgba(153,27,27,1)",
            backgroundColor: "rgba(153,27,27,0.05)",
            borderWidth:     2,
            tension:         0.4,
            fill:            false,
            pointRadius:     3,
            pointBackgroundColor: "rgba(153,27,27,1)"
          }
        ]
      },
      options: {
        responsive:          true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            labels:  { color: "#9ca3af", font: { size: 11 } }
          }
        },
        scales: {
          x: {
            ticks: { color: "#6b7280", font: { size: 10 } },
            grid:  { color: "rgba(255,255,255,0.04)" }
          },
          y: {
            min:   0,
            max:   100,
            ticks: { color: "#6b7280", font: { size: 10 },
                     callback: v => v + "%" },
            grid:  { color: "rgba(255,255,255,0.04)" }
          }
        }
      }
    });
  } catch (e) { /* silent */ }
}

// ── Accuracy ──────────────────────────────────────────────────────────────────
async function loadAccuracy() {
  try {
    const [summaryRes, lowRes] = await Promise.all([
      fetch(`${API}/ragas/summary`, { headers: authHeaders() }),
      fetch(`${API}/ragas/low`,     { headers: authHeaders() })
    ]);

    const summary = await summaryRes.json();
    const low     = await lowRes.json();

    // Metric bars
    const breakdown = document.getElementById("metrics-breakdown");
    if (breakdown) {
      const metrics = [
        { label: "SQL Correctness",   key: "sql_correctness",   icon: "✓" },
        { label: "Faithfulness",       key: "faithfulness",       icon: "⬡" },
        { label: "Answer Relevancy",   key: "answer_relevancy",   icon: "◈" },
        { label: "Context Precision",  key: "context_precision",  icon: "▲" },
        { label: "Overall Score",      key: "overall_score",      icon: "◉" }
      ];
      breakdown.innerHTML = metrics.map(m => {
        const val = parseFloat(summary[m.key]) || 0;
        const cls = val >= 80 ? "good" : val >= 60 ? "fair" : "poor";
        return `
          <div class="metric-row">
            <div class="metric-left">
              <span class="metric-icon">${m.icon}</span>
              <span class="metric-label">${m.label}</span>
            </div>
            <div class="metric-bar-wrap">
              <div class="metric-bar-fill ${cls}"
                   style="width:${val}%"></div>
            </div>
            <div class="metric-val">${val}%</div>
          </div>`;
      }).join("");
    }

    // Low scoring queries
    const lowList = document.getElementById("low-queries-list");
    if (lowList) {
      if (!low || low.length === 0) {
        lowList.innerHTML = `<p class="empty-hint">
          No low scoring queries yet.</p>`;
      } else {
        lowList.innerHTML = `
          <div class="low-query-list">
            ${low.map(q => `
              <div class="low-query-item">
                <div class="lq-question">${escHtml(q.question)}</div>
                <div class="lq-meta">
                  <span class="lq-score ${
                    parseFloat(q.overall_score)*100 < 50 ? "poor" : "fair"
                  }">
                    Score: ${Math.round(parseFloat(q.overall_score)*100)}%
                  </span>
                  <span class="lq-date">${q.date}</span>
                </div>
                <code class="lq-sql">${escHtml(q.sql_query || "")}</code>
              </div>`).join("")}
          </div>`;
      }
    }
  } catch (e) { /* silent */ }
}

// ── Usage ─────────────────────────────────────────────────────────────────────
async function loadUsageStats() {
  try {
    const [statsRes, dailyRes] = await Promise.all([
      fetch(`${API}/history/stats`, { headers: authHeaders() }),
      fetch(`${API}/ragas/daily?days=30`, { headers: authHeaders() })
    ]);

    const stats = await statsRes.json();
    const daily = await dailyRes.json();

    setValue("u-total",   stats.total       || 0);
    setValue("u-success", stats.successful  || 0);
    setValue("u-rate",    (stats.success_rate || 0) + "%");

    // Usage chart
    const canvas = document.getElementById("usage-chart");
    if (!canvas) return;
    if (usageChart) usageChart.destroy();

    Chart.defaults.color       = "#6b7280";
    Chart.defaults.borderColor = "rgba(255,255,255,0.04)";

    usageChart = new Chart(canvas, {
      type: "bar",
      data: {
        labels:   daily.map(d => d.date),
        datasets: [{
          label:           "Queries",
          data:            daily.map(d => d.total || 0),
          backgroundColor: "rgba(220,38,38,0.7)",
          borderColor:     "rgba(220,38,38,1)",
          borderWidth:     1,
          borderRadius:    3
        }]
      },
      options: {
        responsive:          true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            ticks: { color: "#6b7280", font: { size: 10 } },
            grid:  { color: "rgba(255,255,255,0.04)" }
          },
          y: {
            ticks: { color: "#6b7280", font: { size: 10 } },
            grid:  { color: "rgba(255,255,255,0.04)" }
          }
        }
      }
    });
  } catch (e) { /* silent */ }
}

// ── Query History ─────────────────────────────────────────────────────────────
async function loadQueryHistory() {
  try {
    const res  = await fetch(`${API}/history`, { headers: authHeaders() });
    const data = await res.json();

    const container = document.getElementById("query-history-table");
    if (!data || data.length === 0) {
      container.innerHTML = `<p class="empty-hint">No queries yet.</p>`;
      return;
    }

    container.innerHTML = `
      <div class="history-table-wrap">
        <table class="history-table">
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
                <td class="hq-question">
                  ${escHtml(q.question?.slice(0, 60) || "")}
                  ${(q.question?.length || 0) > 60 ? "..." : ""}
                </td>
                <td>
                  <span class="status-chip ${q.success ? "ok" : "fail"}">
                    ${q.success ? "✓ OK" : "✗ Failed"}
                  </span>
                </td>
                <td>${q.row_count || 0}</td>
                <td>${q.response_ms || 0}ms</td>
                <td class="hq-date">${
                  q.timestamp ? q.timestamp.split(" ")[0] : ""
                }</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>`;
  } catch (e) { /* silent */ }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function pct(val) {
  const n = parseFloat(val);
  return isNaN(n) ? "—" : n + "%";
}

function setValue(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

document.addEventListener("DOMContentLoaded", initDashboard);