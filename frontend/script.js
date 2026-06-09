const API_BASE = window.location.origin;
const AUTH_KEY = "hydrobytes_admin_authed";
let currentAnalytics = {};
let currentAlerts = [];
let currentAreas = [];
let currentPipelines = [];

// GET DOM ELEMENTS FIRST (before using them)
const loginPage = document.getElementById("loginPage");
const dashboard = document.getElementById("dashboard");
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const metricsBox = document.getElementById("metrics");
const alertsBox = document.getElementById("alerts");
const areasBox = document.getElementById("areas");

function showDashboard() {
  loginPage.classList.add("hidden");
  dashboard.classList.remove("hidden");
  loadDashboard();
}

function showLogin(resetForm) {
  dashboard.classList.add("hidden");
  loginPage.classList.remove("hidden");

  if (resetForm) {
    loginForm.reset();
    loginError.textContent = "";
  }
}

const currentPath = window.location.pathname;

if (currentPath === "/login") {
  showLogin(false);
} else if (currentPath === "/index" || localStorage.getItem(AUTH_KEY) === "1") {
  showDashboard();
}

loginForm.addEventListener("submit", async function (event) {
  event.preventDefault();

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  try {
    // Send credentials to backend API for validation
    const response = await fetch(API_BASE + "/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        email: username,
        password: password
      })
    });

    if (response.ok) {
      // Credentials are valid
      localStorage.setItem(AUTH_KEY, "1");
      window.location.href = "/index";
    } else {
      // Invalid credentials
      loginError.textContent = "Invalid admin credentials";
    }
  } catch (error) {
    loginError.textContent = "Error connecting to server";
  }
});

const logoutBtn = document.getElementById("logoutBtn");
logoutBtn.addEventListener("click", function () {
  localStorage.removeItem(AUTH_KEY);
  window.location.href = "/login";
});

const manageBtn = document.getElementById("manageBtn");
manageBtn.addEventListener("click", function () {
  window.location.href = "/manage";
});

async function getJson(path, fallback) {
  try {
    const response = await fetch(API_BASE + path);
    return await response.json();
  } catch (error) {
    return fallback;
  }
}

async function loadDashboard() {
  currentAnalytics = await getJson("/analytics", {});
  currentAlerts = await getJson("/alerts", []);
  currentAreas = await getJson("/areas", []);
  currentPipelines = await getJson("/pipelines", []);

  showMetrics(currentAnalytics, currentAlerts, currentAreas, currentPipelines);
  showAlerts(currentAlerts);
  const areaStats = currentAnalytics.area_wise_statistics || [];
  showAreas(areaStats.length ? areaStats : currentAreas);
}

function showMetrics(analytics, alerts, areas, pipelines) {
  const cards = [
    ["Total Water Flow", analytics.total_water_flow || 0, "Live estimate"],
    ["Total Consumption", analytics.total_consumption || 0, "Across all zones"],
    ["Average Pressure", analytics.average_pressure || 0, "Current operating level"],
    ["Leak Alerts", alerts.length, "Open and recent alerts"],
    ["Number of Areas", areas.length, "Registered areas"],
    ["Number of Pipelines", pipelines.length, "Registered pipelines"]
  ];

  metricsBox.innerHTML = cards.map(function (card) {
    return `
      <div class="metric-card">
        <span>${card[0]}</span>
        <strong>${formatValue(card[1])}</strong>
        <small>${card[2]}</small>
      </div>
    `;
  }).join("");
}

function showAlerts(alerts) {
  if (!alerts.length) {
    alertsBox.innerHTML = "<p>No open alerts</p>";
    return;
  }

  alertsBox.innerHTML = alerts.slice(0, 6).map(function (alert) {
    const areaName = alert.area_name || "Unknown area";
    const pipelineName = alert.pipeline_name || "Unknown pipeline";

    return `
      <div class="alert-item">
        <strong>${areaName}</strong>
        <p>Pipeline: ${pipelineName}</p>
        <p>${shortAlertMessage(alert)}</p>
        <button class="resolve-btn" data-id="${alert.id}">Resolve</button>
      </div>
    `;
  }).join("");

  document.querySelectorAll(".resolve-btn").forEach(function (button) {
    button.addEventListener("click", async function () {
      const response = await fetch(API_BASE + `/alerts/${button.dataset.id}`, {
        method: "DELETE"
      });

      if (!response.ok) {
        return;
      }

      await loadDashboard();
    });
  });
}

function showAreas(areas) {
  if (!areas.length) {
    areasBox.innerHTML = "<p>No area status available</p>";
    return;
  }

  areasBox.innerHTML = areas.map(function (area) {
    const name = area.area_name || "Area";
    const flow = area.average_flow || 0;
    const pressure = area.average_pressure || 0;
    const consumption = area.average_consumption || 0;
    const leaks = area.leak_count || 0;

    return `
      <div class="area-item">
        <strong>${name}</strong>
        <p>Flow: ${formatValue(flow)} | Consumption: ${formatValue(consumption)} | Pressure: ${formatValue(pressure)} | Alerts: ${leaks}</p>
      </div>
    `;
  }).join("");
}

function formatValue(value) {
  const number = Number(value);

  if (Number.isInteger(number)) {
    return String(number);
  }

  return number.toFixed(2);
}

function shortAlertMessage(alert) {
  const message = (alert.message || alert.alert_type || "Leak alert").toLowerCase();
  const severity = alert.severity ? `${alert.severity}: ` : "";

  if (message.includes("pressure")) {
    return severity + "Pressure issue detected.";
  }

  if (message.includes("flow")) {
    return severity + "Flow is higher than expected.";
  }

  if (message.includes("leak")) {
    return severity + "Possible leak detected.";
  }

  return severity + "Check this pipeline.";
}
