const API = "http://localhost:5000/api";

function getToken()    { return localStorage.getItem("qm_token"); }
function setToken(t)   { localStorage.setItem("qm_token", t); }
function clearToken()  {
  localStorage.removeItem("qm_token");
  localStorage.removeItem("qm_user");
}
function setUser(u)    { localStorage.setItem("qm_user", JSON.stringify(u)); }
function getUser()     {
  const u = localStorage.getItem("qm_user");
  return u ? JSON.parse(u) : null;
}
function isLoggedIn()  { return !!getToken(); }
function authHeaders() {
  return {
    "Content-Type":  "application/json",
    "Authorization": `Bearer ${getToken()}`
  };
}

function showAuthModal(tab = "login") {
  document.getElementById("auth-modal").classList.add("active");
  switchAuthTab(tab);
}

function hideAuthModal() {
  document.getElementById("auth-modal").classList.remove("active");
  clearAuthErrors();
}

function switchAuthTab(tab) {
  document.getElementById("login-form").style.display =
    tab === "login" ? "flex" : "none";
  document.getElementById("register-form").style.display =
    tab === "register" ? "flex" : "none";
  document.querySelectorAll(".auth-tab").forEach(t =>
    t.classList.toggle("active", t.dataset.tab === tab)
  );
}

function clearAuthErrors() {
  document.querySelectorAll(".auth-error").forEach(e =>
    e.textContent = "");
}

async function register() {
  const name     = document.getElementById("reg-name").value.trim();
  const email    = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value.trim();
  const errorEl  = document.getElementById("register-error");
  const btn      = document.getElementById("register-btn");

  errorEl.textContent = "";
  if (!name || !email || !password) {
    errorEl.textContent = "All fields required."; return;
  }

  btn.textContent = "Creating..."; btn.disabled = true;
  try {
    const res  = await fetch(`${API}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password })
    });
    const data = await res.json();
    if (res.ok) {
      setToken(data.token); setUser(data.user);
      hideAuthModal(); onLoginSuccess(data.user);
    } else {
      errorEl.textContent = data.error || "Registration failed.";
    }
  } catch (e) {
    errorEl.textContent = "Server connection failed.";
  }
  btn.textContent = "Create Account"; btn.disabled = false;
}

async function login() {
  const email    = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value.trim();
  const errorEl  = document.getElementById("login-error");
  const btn      = document.getElementById("login-submit-btn");

  errorEl.textContent = "";
  if (!email || !password) {
    errorEl.textContent = "Email and password required."; return;
  }

  btn.textContent = "Signing in..."; btn.disabled = true;
  try {
    const res  = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (res.ok) {
      setToken(data.token); setUser(data.user);
      hideAuthModal(); onLoginSuccess(data.user);
    } else {
      errorEl.textContent = data.error || "Login failed.";
    }
  } catch (e) {
    errorEl.textContent = "Server connection failed.";
  }
  btn.textContent = "Sign In"; btn.disabled = false;
}

function loginWithGoogle() {
  window.location.href = `${API}/auth/google`;
}

function handleOAuthCallback() {
  const params = new URLSearchParams(window.location.search);
  const token  = params.get("token");
  const error  = params.get("error");
  if (error) {
    showAuthModal("login");
    document.getElementById("login-error").textContent =
      `Google login failed: ${error}`;
    return;
  }
  if (token) {
    setToken(token);
    fetch(`${API}/auth/me`, {
      headers: { "Authorization": `Bearer ${token}` }
    }).then(r => r.json()).then(user => {
      setUser(user); onLoginSuccess(user);
      window.history.replaceState(
        {}, document.title, window.location.pathname);
    });
  }
}

function logout() {
  if (!confirm("Are you sure you want to sign out?")) return;
  clearToken();
  document.getElementById("app-container").classList.remove("visible");
  document.getElementById("landing-screen").classList.add("visible");
  resetAppState();
}

function onLoginSuccess(user) {
  const initials = user.name
    .split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
  document.getElementById("user-avatar").textContent   = initials;
  document.getElementById("topbar-user-name").textContent =
    user.name.split(" ")[0];

  document.getElementById("landing-screen").classList.remove("visible");
  document.getElementById("app-container").classList.add("visible");
  document.getElementById("auth-modal").classList.remove("active");

  loadSessions();
  loadConnections();
}

function resetAppState() {
  const chat = document.getElementById("chat-messages");
  if (chat) {
    chat.innerHTML = `<div class="chat-welcome" id="chat-welcome">
      <div class="welcome-graphic">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="3"/>
          <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83
                   M16.95 16.95l2.83 2.83M1 12h4M19 12h4
                   M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
        </svg>
      </div>
      <h2>Connect a database to get started</h2>
      <p>Choose a connection from the sidebar or add a new one.</p>
    </div>`;
  }
  setConnStatus("offline", "Not connected");
}

async function initAuth() {
  handleOAuthCallback();
  if (!isLoggedIn()) {
    document.getElementById("landing-screen").classList.add("visible");
    return;
  }
  try {
    const res = await fetch(`${API}/auth/me`, {
      headers: { "Authorization": `Bearer ${getToken()}` }
    });
    if (res.ok) {
      const user = await res.json();
      setUser(user); onLoginSuccess(user);
    } else {
      clearToken();
      document.getElementById("landing-screen").classList.add("visible");
    }
  } catch (e) {
    document.getElementById("landing-screen").classList.add("visible");
  }
}