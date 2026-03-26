let isConnected    = false;
let isLoading      = false;
let currentSession = null;
let chartInstances = {};

// ── Sidebar tabs ──────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll(".sidebar-panel").forEach(p =>
    p.classList.toggle("hidden", p.id !== `panel-${name}`)
  );
  document.querySelectorAll(".sidebar-tab").forEach(t =>
    t.classList.toggle("active", t.dataset.tab === name)
  );
}

// ── DB type tabs ──────────────────────────────────────────────────────────────
function switchDbType(type) {
  ["mysql", "sqlite", "url"].forEach(t => {
    const el = document.getElementById(`form-${t}`);
    if (el) el.style.display = t === type ? "flex" : "none";
  });
  document.querySelectorAll(".db-type-tab").forEach(t =>
    t.classList.toggle("active", t.dataset.type === type)
  );
}

// ── Connect MySQL ─────────────────────────────────────────────────────────────
async function connectMySQL() {
  const btn = document.getElementById("mysql-btn");
  btn.textContent = "Connecting..."; btn.disabled = true;
  setConnStatus("connecting", "Connecting...");
  try {
    const res  = await fetch(`${API}/connect/mysql`, {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({
        host:     val("mysql-host"),
        port:     val("mysql-port"),
        username: val("mysql-user"),
        password: val("mysql-pass"),
        database: val("mysql-db"),
        nickname: val("mysql-nick")
      })
    });
    const data = await res.json();
    if (res.ok) {
      isConnected = true;
      setConnStatus("online", val("mysql-db") || "MySQL");
      toast(`Connected — ${data.tables_indexed} tables indexed`, "success");
      await newSession("mysql", val("mysql-db"));
      loadSchemaExplorer(); loadSuggestions(); loadConnections();
    } else {
      setConnStatus("offline", "Failed");
      toast(data.error, "error");
    }
  } catch (e) {
    setConnStatus("offline", "Error"); toast(e.message, "error");
  }
  btn.textContent = "Connect"; btn.disabled = false;
}

// ── Connect SQLite ────────────────────────────────────────────────────────────
async function connectSQLite() {
  const btn = document.getElementById("sqlite-btn");
  btn.textContent = "Connecting..."; btn.disabled = true;
  setConnStatus("connecting", "Connecting...");
  try {
    const res  = await fetch(`${API}/connect/sqlite`, {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({ filepath: val("sqlite-path") })
    });
    const data = await res.json();
    if (res.ok) {
      isConnected = true;
      setConnStatus("online", "SQLite");
      toast(`Connected — ${data.tables_indexed} tables indexed`, "success");
      await newSession("sqlite", "SQLite");
      loadSchemaExplorer(); loadSuggestions(); loadConnections();
    } else {
      setConnStatus("offline", "Failed"); toast(data.error, "error");
    }
  } catch (e) {
    setConnStatus("offline", "Error"); toast(e.message, "error");
  }
  btn.textContent = "Connect"; btn.disabled = false;
}

// ── Connect URL ───────────────────────────────────────────────────────────────
async function connectURL() {
  const btn = document.getElementById("url-btn");
  btn.textContent = "Connecting..."; btn.disabled = true;
  setConnStatus("connecting", "Connecting...");
  try {
    const res  = await fetch(`${API}/connect/url`, {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({
        url:      val("db-url"),
        nickname: val("url-nick")
      })
    });
    const data = await res.json();
    if (res.ok) {
      isConnected = true;
      setConnStatus("online", "Remote DB");
      toast(`Connected — ${data.tables_indexed} tables indexed`, "success");
      await newSession("url", "Remote DB");
      loadSchemaExplorer(); loadSuggestions(); loadConnections();
    } else {
      setConnStatus("offline", "Failed"); toast(data.error, "error");
    }
  } catch (e) {
    setConnStatus("offline", "Error"); toast(e.message, "error");
  }
  btn.textContent = "Connect"; btn.disabled = false;
}

// ── Upload file ───────────────────────────────────────────────────────────────
async function uploadFile() {
  const fileInput = document.getElementById("file-input");
  if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
    toast("Please select a file first.", "warning"); return;
  }

  const file     = fileInput.files[0];
  const allowed  = [".csv", ".sqlite", ".db", ".sql"];
  const ext      = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();

  if (!allowed.includes(ext)) {
    toast("Unsupported file. Use .csv, .sqlite, .db, or .sql", "error");
    return;
  }

  const btn = document.getElementById("upload-btn");
  btn.textContent = "Uploading..."; btn.disabled = true;
  setConnStatus("connecting", "Uploading...");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res  = await fetch(`${API}/connect/upload`, {
      method:  "POST",
      headers: { "Authorization": `Bearer ${getToken()}` },
      body:    formData
    });
    const data = await res.json();
    if (res.ok) {
      isConnected = true;
      setConnStatus("online", data.original_name || "Uploaded DB");
      toast(`Uploaded — ${data.tables_indexed} tables indexed`, "success");
      await newSession("upload", data.original_name || "Upload");
      loadSchemaExplorer(); loadSuggestions(); loadConnections();
    } else {
      setConnStatus("offline", "Failed"); toast(data.error, "error");
    }
  } catch (e) {
    setConnStatus("offline", "Error"); toast(e.message, "error");
  }
  btn.textContent = "Upload & Connect"; btn.disabled = false;
}

// ── Reconnect saved ───────────────────────────────────────────────────────────
async function reconnect(connId, label) {
  setConnStatus("connecting", "Reconnecting...");
  try {
    const res  = await fetch(`${API}/connect/saved/${connId}`, {
      method: "POST", headers: authHeaders()
    });
    const data = await res.json();
    if (res.ok) {
      isConnected = true;
      setConnStatus("online", label);
      toast(`Reconnected — ${data.tables_indexed} tables indexed`, "success");
      await newSession(data.db_type, label);
      loadSchemaExplorer(); loadSuggestions();
      switchTab("chat");
    } else {
      setConnStatus("offline", "Failed"); toast(data.error, "error");
    }
  } catch (e) {
    setConnStatus("offline", "Error"); toast(e.message, "error");
  }
}

// ── Status ────────────────────────────────────────────────────────────────────
function setConnStatus(state, text) {
  const dot  = document.getElementById("conn-dot");
  const lbl  = document.getElementById("conn-label");
  if (dot)  dot.className  = `conn-dot ${state}`;
  if (lbl) lbl.textContent = text;
}

// ── Session ───────────────────────────────────────────────────────────────────
async function newSession(dbType, dbName) {
  try {
    const res  = await fetch(`${API}/sessions/new`, {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({ db_type: dbType, db_name: dbName })
    });
    const data = await res.json();
    currentSession = data.session_id;
    clearChat();
    loadSessions();
  } catch (e) { currentSession = null; }
}

async function loadSessions() {
  try {
    const res  = await fetch(`${API}/sessions`, { headers: authHeaders() });
    const list = await res.json();
    renderSessions(list);
  } catch (e) { /* silent */ }
}

function renderSessions(sessions) {
  const el = document.getElementById("sessions-list");
  if (!el) return;
  if (!sessions || sessions.length === 0) {
    el.innerHTML = `<p class="empty-hint">No sessions yet</p>`; return;
  }
  el.innerHTML = sessions.map(s => `
    <div class="session-row ${s.session_id === currentSession ? "active" : ""}"
         onclick="loadSession('${s.session_id}','${esc(s.title)}')">
      <div class="session-row-info">
        <div class="session-row-title">${esc(s.title || "Untitled")}</div>
        <div class="session-row-meta">
          ${esc(s.db_name || "")} &middot; ${s.message_count || 0} messages
        </div>
      </div>
      <button class="icon-btn-sm"
              onclick="event.stopPropagation();deleteSession('${s.session_id}')">
        &times;
      </button>
    </div>`).join("");
}

async function loadSession(sessionId, title) {
  currentSession = sessionId;
  clearChat();
  document.getElementById("chat-session-label").textContent = title;

  try {
    const res  = await fetch(
      `${API}/sessions/${sessionId}/messages`, { headers: authHeaders() });
    const msgs = await res.json();
    msgs.forEach(m => {
      if (m.role === "user") pushUser(m.content);
      else pushAI({
        sql:         m.sql_query || "",
        explanation: m.content,
        columns:     m.columns  || [],
        rows:        m.rows     || [],
        row_count:   m.row_count || 0,
        chart_data:  m.chart_data || {},
        corrected:   false,
        insights:    [],
        anomalies:   [],
        forecast:    {}
      }, true);
    });
    loadSessions();
    switchTab("chat");
  } catch (e) { toast("Failed to load session", "error"); }
}

async function deleteSession(id) {
  await fetch(`${API}/sessions/${id}`, {
    method: "DELETE", headers: authHeaders()
  });
  if (id === currentSession) { currentSession = null; clearChat(); }
  loadSessions();
}

// ── Connections ───────────────────────────────────────────────────────────────
async function loadConnections() {
  try {
    const res   = await fetch(`${API}/connections`, { headers: authHeaders() });
    const conns = await res.json();
    renderConnections(conns);
  } catch (e) { /* silent */ }
}

function renderConnections(conns) {
  const el = document.getElementById("connections-list");
  if (!el) return;
  if (!conns || conns.length === 0) {
    el.innerHTML = `<p class="empty-hint">No saved connections</p>`; return;
  }
  el.innerHTML = conns.map(c => `
    <div class="conn-row">
      <div class="conn-row-info">
        <div class="conn-row-name">${esc(c.nickname)}</div>
        <div class="conn-row-meta">
          ${esc(c.db_type)} &middot; ${esc(c.database_name || c.filepath || "")}
        </div>
      </div>
      <button class="btn-sm-red"
              onclick="reconnect(${c.id},'${esc(c.nickname)}')">
        Connect
      </button>
    </div>`).join("");
}

// ── Schema explorer ───────────────────────────────────────────────────────────
async function loadSchemaExplorer() {
  try {
    const res  = await fetch(`${API}/schema/explorer`, { headers: authHeaders() });
    const data = await res.json();
    if (!data.tables) return;
    const el = document.getElementById("schema-list");
    if (!el) return;
    el.innerHTML = data.tables.map(t => `
      <div class="schema-table">
        <div class="schema-table-header"
             onclick="toggleSchema('${t.name}',this)">
          <svg width="12" height="12" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2"
               class="schema-arrow">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
          <span class="schema-table-name">${esc(t.name)}</span>
          <span class="schema-col-count">${t.columns.length} cols</span>
        </div>
        <div class="schema-table-cols hidden" id="scols-${t.name}">
          ${t.columns.map(c => `
            <div class="schema-col-row">
              <span class="schema-col-name">${esc(c.name)}</span>
              <span class="schema-col-type">${esc(c.type)}</span>
            </div>`).join("")}
          <button class="schema-preview-btn"
                  onclick="loadPreview('${t.name}')">
            Preview rows
          </button>
          <div id="preview-${t.name}"></div>
        </div>
      </div>`).join("");
  } catch (e) { /* silent */ }
}

function toggleSchema(name, header) {
  const body  = document.getElementById(`scols-${name}`);
  const arrow = header.querySelector(".schema-arrow");
  if (!body) return;
  body.classList.toggle("hidden");
  if (arrow) {
    arrow.style.transform = body.classList.contains("hidden")
      ? "rotate(0deg)" : "rotate(90deg)";
  }
}

async function loadPreview(tableName) {
  const el = document.getElementById(`preview-${tableName}`);
  if (!el) return;
  el.innerHTML = `<p class="empty-hint">Loading...</p>`;
  try {
    const res  = await fetch(
      `${API}/schema/sample/${tableName}`, { headers: authHeaders() });
    const data = await res.json();
    if (data.columns && data.rows) {
      const ths = data.columns.map(c => `<th>${esc(c)}</th>`).join("");
      const trs = data.rows.map(r =>
        `<tr>${r.map(v =>
          `<td>${esc(v === null ? "NULL" : String(v))}</td>`
        ).join("")}</tr>`
      ).join("");
      el.innerHTML = `
        <div class="preview-table-wrap">
          <table class="preview-table">
            <thead><tr>${ths}</tr></thead>
            <tbody>${trs}</tbody>
          </table>
        </div>`;
    }
  } catch (e) {
    el.innerHTML = `<p class="empty-hint">Failed to load</p>`;
  }
}

// ── Suggestions ───────────────────────────────────────────────────────────────
async function loadSuggestions() {
  if (!isConnected) return;
  try {
    const res  = await fetch(`${API}/suggestions`, { headers: authHeaders() });
    const data = await res.json();
    if (data.suggestions) {
      const el = document.getElementById("suggestion-chips");
      if (el) {
        el.innerHTML = data.suggestions.map(q =>
          `<button class="chip"
                   onclick="sendDirect('${esc(q).replace(/'/g,"\\'")}')">
            ${esc(q)}
          </button>`
        ).join("");
      }
    }
  } catch (e) { /* silent */ }
}

function sendDirect(q) {
  document.getElementById("chat-input").value = q;
  sendQuestion();
}

// ── Ask ───────────────────────────────────────────────────────────────────────
function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault(); sendQuestion();
  }
}

async function sendQuestion() {
  if (isLoading) return;
  const input    = document.getElementById("chat-input");
  const question = input.value.trim();
  if (!question) return;
  if (!isConnected) {
    toast("Connect to a database first.", "warning"); return;
  }

  input.value = ""; input.style.height = "auto";
  isLoading   = true;
  document.getElementById("send-btn").disabled = true;

  removeWelcome();
  pushUser(question);
  const lid = pushLoader();

  try {
    const res  = await fetch(`${API}/ask`, {
      method:  "POST",
      headers: authHeaders(),
      body:    JSON.stringify({
        question,
        session_id: currentSession
      })
    });
    const data = await res.json();
    removeLoader(lid);

    if (res.status === 429) {
      toast(data.error, "error");
    } else if (res.ok && data.success) {
      pushAI(data);
      loadSessions();
    } else {
      pushError(data);
    }
  } catch (e) {
    removeLoader(lid); toast(e.message, "error");
  }

  isLoading = false;
  document.getElementById("send-btn").disabled = false;
  scrollBottom();
}

// ── Chat rendering ────────────────────────────────────────────────────────────
function scrollBottom() {
  const c = document.getElementById("chat-messages");
  if (c) c.scrollTop = c.scrollHeight;
}

function removeWelcome() {
  const w = document.getElementById("chat-welcome");
  if (w) w.remove();
}

function clearChat() {
  const c = document.getElementById("chat-messages");
  if (c) c.innerHTML = `
    <div class="chat-welcome" id="chat-welcome">
      <div class="welcome-graphic">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="3"/>
          <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83
                   M16.95 16.95l2.83 2.83M1 12h4M19 12h4
                   M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
        </svg>
      </div>
      <h2>What would you like to know?</h2>
      <p>Ask anything about your data in plain English.</p>
      <div class="suggestion-chips" id="suggestion-chips"></div>
    </div>`;
  if (isConnected) loadSuggestions();
}

function pushUser(text) {
  const c   = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "msg user-msg";
  div.innerHTML = `<div class="msg-bubble user-bubble">${esc(text)}</div>`;
  c.appendChild(div); scrollBottom();
}

function pushLoader() {
  const c   = document.getElementById("chat-messages");
  const id  = "ld-" + Date.now();
  const div = document.createElement("div");
  div.id        = id;
  div.className = "msg ai-msg";
  div.innerHTML = `
    <div class="ai-icon">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <circle cx="12" cy="12" r="10"/>
      </svg>
    </div>
    <div class="msg-bubble ai-bubble loader-bubble">
      <div class="loader-dots">
        <span></span><span></span><span></span>
      </div>
    </div>`;
  c.appendChild(div); scrollBottom();
  return id;
}

function removeLoader(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function pushAI(data, isReplay = false) {
  const c      = document.getElementById("chat-messages");
  const div    = document.createElement("div");
  div.className = "msg ai-msg";

  const sqlId   = "sql-" + Date.now() + Math.random().toString(36).slice(2);
  const chartId = "ch-"  + Date.now() + Math.random().toString(36).slice(2);
  const tblId   = "tb-"  + Date.now() + Math.random().toString(36).slice(2);

  // Table HTML
  let tableHtml = "";
  if (data.rows && data.rows.length > 0) {
    const ths = data.columns.map((c, i) =>
      `<th class="sortable" onclick="sortCol('${tblId}',${i})">
        ${esc(String(c))}
        <span class="sort-icon">&#8597;</span>
      </th>`
    ).join("");
    const trs = data.rows.map(r =>
      `<tr>${r.map(v =>
        `<td>${esc(v === null ? "NULL" : String(v))}</td>`
      ).join("")}</tr>`
    ).join("");
    tableHtml = `
      <div class="result-block">
        <div class="result-toolbar">
          <span class="result-count">
            ${data.row_count} row${data.row_count !== 1 ? "s" : ""}
          </span>
          <div class="result-actions">
            <button class="toolbar-btn"
                    onclick="toggleFilter('${tblId}')">
              Filter
            </button>
            <button class="toolbar-btn"
                    onclick="exportCSV('${tblId}',
                    ${JSON.stringify(data.columns)})">
              Export CSV
            </button>
          </div>
        </div>
        <input type="text" class="filter-input hidden"
               id="fi-${tblId}"
               placeholder="Filter results..."
               oninput="filterRows('${tblId}',this.value)"/>
        <div class="table-scroll">
          <table id="${tblId}" class="data-table">
            <thead><tr>${ths}</tr></thead>
            <tbody>${trs}</tbody>
          </table>
        </div>
      </div>`;
  } else {
    tableHtml = `<p class="no-rows">Query returned 0 rows.</p>`;
  }

  // Data summary
  let summaryHtml = "";
  if (data.data_summary && Object.keys(data.data_summary).length > 0) {
    summaryHtml = `
      <div class="summary-strip">
        ${Object.entries(data.data_summary).map(([col, s]) => `
          <div class="summary-item">
            <div class="summary-col-name">${esc(col)}</div>
            <div class="summary-nums">
              <span>MIN <b>${s.min}</b></span>
              <span>MAX <b>${s.max}</b></span>
              <span>AVG <b>${s.avg}</b></span>
            </div>
          </div>`).join("")}
      </div>`;
  }

  // Chart
  const hasChart = data.chart_data &&
    Object.keys(data.chart_data).length > 0;
  const chartHtml = hasChart ? `
    <div class="chart-block">
      <div class="chart-toolbar">
        <span class="chart-label">Visualization</span>
        <div class="chart-type-btns">
          <button class="chart-type-btn active"
                  onclick="switchChart('${chartId}','bar',this)">
            Bar
          </button>
          <button class="chart-type-btn"
                  onclick="switchChart('${chartId}','line',this)">
            Line
          </button>
          <button class="chart-type-btn"
                  onclick="switchChart('${chartId}','pie',this)">
            Pie
          </button>
        </div>
      </div>
      <div class="chart-wrap">
        <canvas id="${chartId}"></canvas>
      </div>
    </div>` : "";

  // Insights
  let insightsHtml = "";
  if (data.insights && data.insights.length > 0) {
    insightsHtml = `
      <div class="insights-block">
        <div class="insights-label">
          <svg width="14" height="14" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          Insights
        </div>
        <ul class="insights-list">
          ${data.insights.map(i =>
            `<li>${esc(i)}</li>`).join("")}
        </ul>
      </div>`;
  }

  // Anomalies
  let anomalyHtml = "";
  if (data.anomalies && data.anomalies.length > 0) {
    anomalyHtml = `
      <div class="anomaly-block">
        <div class="anomaly-label">
          <svg width="14" height="14" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94
                     a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          Anomalies Detected
        </div>
        ${data.anomalies.map(a => `
          <div class="anomaly-item ${a.severity}">
            ${esc(a.message)}
          </div>`).join("")}
      </div>`;
  }

  // Forecast
  let forecastHtml = "";
  if (data.forecast && data.forecast.available) {
    const f = data.forecast;
    forecastHtml = `
      <div class="forecast-block">
        <div class="forecast-label">
          <svg width="14" height="14" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
          Forecast — ${f.forecast_label}
        </div>
        <p class="forecast-msg">${esc(f.message)}</p>
        <div class="forecast-vals">
          ${f.forecast.map((v, i) =>
            `<span class="forecast-val">
              Period ${i + 1}: <b>${v.toLocaleString()}</b>
            </span>`).join("")}
        </div>
      </div>`;
  }

  // Save button
  const saveBtn = !isReplay ? `
    <button class="action-link"
            onclick="openSave('${esc(data.question || "").replace(/'/g,"\\'")}',
                              '${esc(data.sql || "").replace(/'/g,"\\'")}')">
      Save query
    </button>` : "";

  div.innerHTML = `
    <div class="ai-icon">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <circle cx="12" cy="12" r="10"/>
      </svg>
    </div>
    <div class="msg-bubble ai-bubble">

      <div class="sql-block">
        <div class="sql-header">
          <span class="sql-label">SQL</span>
          <div style="display:flex;gap:8px;align-items:center;">
            ${data.corrected
              ? `<span class="badge badge-warn">Auto-corrected</span>`
              : ""}
            ${data.response_ms
              ? `<span class="badge badge-dim">${data.response_ms}ms</span>`
              : ""}
            <button class="copy-link"
                    onclick="copyEl('${sqlId}',this)">Copy</button>
          </div>
        </div>
        <code id="${sqlId}" class="sql-code">${esc(data.sql || "")}</code>
      </div>

      <p class="explain-text">${esc(data.explanation || "")}</p>

      ${tableHtml}
      ${summaryHtml}
      ${chartHtml}
      ${insightsHtml}
      ${anomalyHtml}
      ${forecastHtml}

      ${!isReplay ? `<div class="msg-footer">${saveBtn}</div>` : ""}

    </div>`;

  c.appendChild(div);

  if (hasChart) {
    setTimeout(() => renderChart(chartId, data.chart_data), 80);
  }

  scrollBottom();
}

function pushError(data) {
  const c   = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "msg ai-msg";

  const sqlHtml = data.sql ? `
    <div class="sql-block">
      <div class="sql-header"><span class="sql-label">SQL</span></div>
      <code class="sql-code">${esc(data.sql)}</code>
    </div>` : "";

  const note = data.blocked
    ? `<p class="explain-text">Query blocked by safety guardrail.</p>`
    : data.corrected_attempted
    ? `<p class="explain-text">Auto-correction attempted but failed.</p>`
    : "";

  div.innerHTML = `
    <div class="ai-icon">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <circle cx="12" cy="12" r="10"/>
      </svg>
    </div>
    <div class="msg-bubble ai-bubble">
      ${sqlHtml}
      ${note}
      <div class="error-msg">${esc(data.error || "Unknown error")}</div>
    </div>`;

  c.appendChild(div); scrollBottom();
}

// ── Table helpers ─────────────────────────────────────────────────────────────
let _sortState = {};

function sortCol(tblId, colIdx) {
  const table = document.getElementById(tblId);
  if (!table) return;
  const tbody = table.querySelector("tbody");
  const rows  = Array.from(tbody.querySelectorAll("tr"));
  const key   = `${tblId}-${colIdx}`;
  const dir   = (_sortState[key] === 1) ? -1 : 1;
  _sortState[key] = dir;

  rows.sort((a, b) => {
    const av = a.cells[colIdx]?.textContent || "";
    const bv = b.cells[colIdx]?.textContent || "";
    const an = parseFloat(av), bn = parseFloat(bv);
    if (!isNaN(an) && !isNaN(bn)) return (an - bn) * dir;
    return av.localeCompare(bv) * dir;
  });
  rows.forEach(r => tbody.appendChild(r));
}

function toggleFilter(tblId) {
  const el = document.getElementById(`fi-${tblId}`);
  if (el) el.classList.toggle("hidden");
}

function filterRows(tblId, val) {
  const table = document.getElementById(tblId);
  if (!table) return;
  const q = val.toLowerCase();
  table.querySelectorAll("tbody tr").forEach(row => {
    row.style.display =
      row.textContent.toLowerCase().includes(q) ? "" : "none";
  });
}

function exportCSV(tblId, columns) {
  const table = document.getElementById(tblId);
  if (!table) return;
  let csv = columns.join(",") + "\n";
  table.querySelectorAll("tbody tr").forEach(row => {
    const cells = Array.from(row.cells).map(
      c => `"${c.textContent.replace(/"/g,'""')}"`);
    csv += cells.join(",") + "\n";
  });
  const a    = document.createElement("a");
  a.href     = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = "querymind_export.csv";
  a.click();
}

// ── Chart ─────────────────────────────────────────────────────────────────────
function renderChart(chartId, chartData) {
  const canvas = document.getElementById(chartId);
  if (!canvas || !window.Chart) return;
  if (chartInstances[chartId]) chartInstances[chartId].destroy();
  Chart.defaults.color       = "#6b7280";
  Chart.defaults.borderColor = "rgba(0,0,0,0.06)";
  chartInstances[chartId]    = new Chart(canvas, chartData);
}

function switchChart(chartId, type, btn) {
  const inst = chartInstances[chartId];
  if (!inst) return;
  inst.config.type = type;
  inst.update();
  btn.closest(".chart-type-btns")
     .querySelectorAll(".chart-type-btn")
     .forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
}

// ── Profile dropdown ──────────────────────────────────────────────────────────
function toggleProfile() {
  const dd = document.getElementById("profile-dropdown");
  if (dd) dd.classList.toggle("visible");
}

async function loadProfileData() {
  try {
    const res  = await fetch(`${API}/profile`, { headers: authHeaders() });
    const data = await res.json();
    const u    = data.user;
    const s    = data.stats || {};

    const nameEl  = document.getElementById("pd-name");
    const emailEl = document.getElementById("pd-email");
    const statsEl = document.getElementById("pd-stats");

    if (nameEl)  nameEl.textContent  = u?.name  || "";
    if (emailEl) emailEl.textContent = u?.email || "";
    if (statsEl) {
      statsEl.innerHTML = `
        <div class="pd-stat">
          <span class="pd-stat-val">${s.total || 0}</span>
          <span class="pd-stat-label">Queries</span>
        </div>
        <div class="pd-stat">
          <span class="pd-stat-val">${s.success_rate || 0}%</span>
          <span class="pd-stat-label">Success rate</span>
        </div>
        <div class="pd-stat">
          <span class="pd-stat-val">${data.today_usage || 0}</span>
          <span class="pd-stat-label">Today</span>
        </div>`;
    }
  } catch (e) { /* silent */ }
}

// Close dropdown when clicking outside
document.addEventListener("click", e => {
  const dd  = document.getElementById("profile-dropdown");
  const btn = document.getElementById("profile-btn");
  if (dd && btn && !dd.contains(e.target) && !btn.contains(e.target)) {
    dd.classList.remove("visible");
  }
});

// ── Save query ────────────────────────────────────────────────────────────────
let _pendingSave = {};

function openSave(question, sql) {
  _pendingSave = { question, sql };
  document.getElementById("save-modal").classList.add("active");
  document.getElementById("save-q-name").value       = question.slice(0, 40);
  document.getElementById("save-q-collection").value = "General";
}

function closeSave() {
  document.getElementById("save-modal").classList.remove("active");
}

async function confirmSave() {
  const name = document.getElementById("save-q-name").value.trim();
  const coll = document.getElementById("save-q-collection").value.trim() || "General";
  if (!name) return;
  try {
    const res = await fetch(`${API}/saved/save`, {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({
        name, collection: coll,
        question: _pendingSave.question,
        sql:      _pendingSave.sql
      })
    });
    if (res.ok) { closeSave(); toast(`Saved: ${name}`, "success"); }
  } catch (e) { /* silent */ }
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, type = "info") {
  const el  = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.getElementById("toasts").appendChild(el);
  setTimeout(() => el.classList.add("show"), 10);
  setTimeout(() => { el.classList.remove("show"); setTimeout(() => el.remove(), 300); }, 3500);
}

// ── Utils ─────────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function val(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : "";
}

async function copyEl(id, btn) {
  const text = document.getElementById(id)?.textContent || "";
  await navigator.clipboard.writeText(text);
  btn.textContent = "Copied";
  setTimeout(() => btn.textContent = "Copy", 2000);
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const ta = document.getElementById("chat-input");
  if (ta) {
    ta.addEventListener("input", () => {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 130) + "px";
    });
  }
  initAuth();
});