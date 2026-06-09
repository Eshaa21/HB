const API_BASE = window.location.origin;

const addAreaForm = document.getElementById("addAreaForm");
const removeAreaForm = document.getElementById("removeAreaForm");
const addPipelineForm = document.getElementById("addPipelineForm");
const removePipelineForm = document.getElementById("removePipelineForm");
const manageMessage = document.getElementById("manageMessage");
const areaDataSelect = document.getElementById("areaDataSelect");
const alertAreaSelect = document.getElementById("alertAreaSelect");
const areaBalanceChart = document.getElementById("areaBalanceChart");
const leakPriorityChart = document.getElementById("leakPriorityChart");

let areas = [];
let pipelines = [];
let alerts = [];
let analytics = {};

addAreaForm.addEventListener("submit", async function (event) {
  event.preventDefault();
  const areaName = document.getElementById("addAreaName").value.trim();
  await sendJson("/areas", "POST", { area_name: areaName });
  addAreaForm.reset();
  await loadManagementData("Area added");
});

removeAreaForm.addEventListener("submit", async function (event) {
  event.preventDefault();
  const areaName = document.getElementById("removeAreaName").value;
  await sendJson("/areas", "DELETE", { area_name: areaName });
  await loadManagementData("Area removed");
});

addPipelineForm.addEventListener("submit", async function (event) {
  event.preventDefault();
  const areaName = document.getElementById("pipelineAreaName").value;
  const pipelineName = document.getElementById("addPipelineName").value.trim();
  await sendJson("/pipelines", "POST", { area_name: areaName, pipeline_name: pipelineName });
  addPipelineForm.reset();
  await loadManagementData("Pipeline added");
});

removePipelineForm.addEventListener("submit", async function (event) {
  event.preventDefault();
  const selected = document.getElementById("removePipelineName").value;
  const parts = selected.split("|");
  await sendJson("/pipelines", "DELETE", { area_name: parts[0], pipeline_name: parts[1] });
  await loadManagementData("Pipeline removed");
});

areaDataSelect.addEventListener("change", function () {
  showCurrentArea(areaDataSelect.value);
});

alertAreaSelect.addEventListener("change", function () {
  showAreaWiseData(alertAreaSelect.value);
});

async function loadManagementData(message) {
  const selectedCurrentArea = areaDataSelect.value || "ALL";
  const selectedAlertArea = alertAreaSelect.value || "ALL";
  areas = await getJson("/areas", []);
  pipelines = await getJson("/pipelines", []);
  alerts = await getJson("/alerts", []);
  analytics = await getJson("/analytics", {});

  fillAreaOptions();
  fillAlertAreaOptions();
  fillPipelineOptions();
  areaDataSelect.value = selectedCurrentArea === "ALL" || areas.some(function (area) {
    return area.area_name === selectedCurrentArea;
  }) ? selectedCurrentArea : "ALL";
  alertAreaSelect.value = selectedAlertArea === "ALL" || areas.some(function (area) {
    return area.area_name === selectedAlertArea;
  }) ? selectedAlertArea : "ALL";
  showCurrentArea(areaDataSelect.value || "ALL");
  showAreaWiseData(alertAreaSelect.value || "ALL");
  showAnalysisCharts();

  if (message) {
    manageMessage.textContent = message;
  }
}

function fillAreaOptions() {
  const currentAreaOptions = [
    '<option value="ALL">All Areas</option>'
  ].concat(areas.map(function (area) {
    return `<option value="${area.area_name}">${area.area_name}</option>`;
  })).join("");

  const areaOptions = areas.map(function (area) {
    return `<option value="${area.area_name}">${area.area_name}</option>`;
  }).join("");

  document.getElementById("removeAreaName").innerHTML = areaOptions;
  document.getElementById("pipelineAreaName").innerHTML = areas.map(function (area) {
    return `<option value="${area.area_name}">${area.area_name}</option>`;
  }).join("");
  areaDataSelect.innerHTML = currentAreaOptions;
}

function fillAlertAreaOptions() {
  const options = [
    '<option value="ALL">All areas</option>'
  ].concat(areas.map(function (area) {
    return `<option value="${area.area_name}">${area.area_name}</option>`;
  })).join("");

  alertAreaSelect.innerHTML = options;
}

function fillPipelineOptions() {
  document.getElementById("removePipelineName").innerHTML = pipelines.map(function (pipeline) {
    const value = `${pipeline.area_name}|${pipeline.pipeline_name}`;
    return `<option value="${value}">${pipeline.area_name} - ${pipeline.pipeline_name}</option>`;
  }).join("");
}

function showLists() {
  const selectedArea = areaDataSelect.value || "ALL";
  const areaCards = areas.map(function (area) {
    const isSelected = area.area_name === selectedArea;
    const pipelineCount = pipelines.filter(function (pipeline) {
      return pipeline.area_name === area.area_name;
    }).length;
    const areaPipelines = pipelines.filter(function (pipeline) {
      return pipeline.area_name === area.area_name;
    });

    return `
      <div class="area-item area-card ${isSelected ? "area-highlight" : ""}">
        <button type="button" class="area-toggle" data-area="${escapeText(area.area_name)}">
          <span class="area-toggle-label">
            <strong>${area.area_name}</strong>
            <small>${pipelineCount} pipelines</small>
          </span>
          <span class="area-toggle-arrow">${isSelected ? "&dtrif;" : "&rtrif;"}</span>
        </button>
        <div class="area-pipelines ${isSelected ? "open" : "closed"}">
          ${areaPipelines.map(function (pipeline) {
            return `
              <div class="pipeline-chip">
                <strong>${pipeline.pipeline_name}</strong>
              </div>
            `;
          }).join("") || "<p>No pipelines in this area</p>"}
        </div>
      </div>
    `;
  }).join("");

  document.getElementById("areaList").innerHTML = areaCards || "<p>No areas available</p>";

  document.querySelectorAll(".area-toggle").forEach(function (button) {
    button.addEventListener("click", function () {
      const areaName = button.dataset.area;
      const nextValue = areaDataSelect.value === areaName ? "ALL" : areaName;
      areaDataSelect.value = nextValue;
      showCurrentArea(nextValue);
    });
  });
}
function showCurrentArea(areaName) {
  showLists();
}

function showAreaWiseData(areaName) {
  const filteredAlerts = alerts.filter(function (alert) {
    return !areaName || areaName === "ALL" || alert.area_name === areaName;
  });

  document.getElementById("areaData").innerHTML = filteredAlerts.length
    ? filteredAlerts.map(function (alert) {
      return `
        <div class="alert-item">
          <strong>${alert.pipeline_name}</strong>
          <p>${alert.alert_type} | ${alert.severity}</p>
          <p>${alert.message}</p>
          <small>Timestamp: ${formatTimestamp(alert.timestamp)}</small>
        </div>
      `;
    }).join("")
    : "<p>No open alerts for this area</p>";
}

function showAnalysisCharts() {
  const areaStats = ((analytics && analytics.area_wise_statistics) || []).slice(0, 6);
  areaBalanceChart.innerHTML = areaStats.length
    ? renderGroupedBarChart(areaStats)
    : "<p>No analytics available</p>";

  const openAlerts = alerts;
  const alertCounts = openAlerts.reduce(function (acc, alert) {
    const key = alert.area_name || "Unknown area";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const alertEntries = Object.keys(alertCounts).map(function (key) {
    return [key, alertCounts[key]];
  }).sort(function (left, right) {
    return right[1] - left[1];
  }).slice(0, 6);
  const maxAlerts = Math.max.apply(null, alertEntries.map(function (entry) {
    return entry[1];
  }).concat([1]));

  leakPriorityChart.innerHTML = alertEntries.length
    ? renderDonutChart(alertEntries, maxAlerts)
    : "<p>No open alerts</p>";
}

function renderGroupedBarChart(areaStats) {
  const maxValue = Math.max.apply(null, areaStats.map(function (area) {
    return Math.max(area.average_flow || 0, area.average_consumption || 0, 1);
  }).concat([1]));

  return `
    <svg viewBox="0 0 760 360" class="svg-chart" role="img" aria-label="Area water balance bar chart">
      <defs>
        <linearGradient id="flowGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#2e7d8a" />
          <stop offset="100%" stop-color="#6ab7c5" />
        </linearGradient>
        <linearGradient id="useGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#2f8f5b" />
          <stop offset="100%" stop-color="#7dcf8c" />
        </linearGradient>
      </defs>
      ${areaStats.map(function (area, index) {
        const y = 30 + index * 50;
        const flowWidth = Math.max((area.average_flow || 0) / maxValue * 260, 4);
        const useWidth = Math.max((area.average_consumption || 0) / maxValue * 260, 4);
        const loss = Math.max((area.average_flow || 0) - (area.average_consumption || 0), 0);
        return `
          <text x="10" y="${y + 16}" class="chart-label">${escapeText(area.area_name)}</text>
          <rect x="160" y="${y}" width="${flowWidth}" height="14" rx="7" fill="url(#flowGrad)"></rect>
          <rect x="160" y="${y + 20}" width="${useWidth}" height="14" rx="7" fill="url(#useGrad)"></rect>
          <text x="${170 + flowWidth}" y="${y + 12}" class="chart-value">Flow</text>
          <text x="${170 + useWidth}" y="${y + 32}" class="chart-value">Use</text>
          <text x="470" y="${y + 16}" class="chart-note">Loss: ${formatValue(loss)}</text>
        `;
      }).join("")}
      <line x1="150" y1="18" x2="150" y2="330" class="chart-axis"></line>
      <line x1="150" y1="330" x2="730" y2="330" class="chart-axis"></line>
      <text x="160" y="350" class="chart-legend">Blue = water supplied, Green = water used</text>
    </svg>
  `;
}

function renderDonutChart(alertEntries, maxAlerts) {
  const total = alertEntries.reduce(function (sum, entry) {
    return sum + entry[1];
  }, 0);
  let offset = 25;
  const radius = 72;
  const circumference = 2 * Math.PI * radius;
  const segments = alertEntries.map(function (entry, index) {
    const fraction = entry[1] / total;
    const dash = circumference * fraction;
    const gap = circumference - dash;
    const color = index % 2 === 0 ? "#b83232" : "#ef7a58";
    const rotate = offset;
    offset += fraction * 360;
    return `<circle cx="120" cy="120" r="${radius}" fill="none" stroke="${color}" stroke-width="28" stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${circumference * 0.25}" transform="rotate(${rotate} 120 120)"></circle>`;
  }).join("");

  return `
    <div class="donut-wrap">
      <svg viewBox="0 0 240 240" class="svg-donut" role="img" aria-label="Leak priority donut chart">
        <circle cx="120" cy="120" r="72" class="donut-base"></circle>
        ${segments}
        <text x="120" y="114" text-anchor="middle" class="donut-total">${total}</text>
        <text x="120" y="136" text-anchor="middle" class="donut-caption">open alerts</text>
      </svg>
      <div class="chart-box donut-list">
        ${alertEntries.map(function (entry, index) {
          return `
            <div class="chart-row">
              <div class="chart-row-head">
                <strong>${escapeText(entry[0])}</strong>
                <span>${entry[1]} alerts</span>
              </div>
              <div class="bar-track">
                <div class="bar-fill alert" style="width:${Math.min((entry[1] / maxAlerts) * 100, 100)}%"></div>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `;
}

function escapeText(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function getJson(path, fallback) {
  try {
    const response = await fetch(API_BASE + path);
    if (!response.ok) {
      return fallback;
    }
    return await response.json();
  } catch (error) {
    return fallback;
  }
}

async function sendJson(path, method, body) {
  const response = await fetch(API_BASE + path, {
    method: method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const error = await response.json();
    manageMessage.textContent = error.detail || "Action failed";
  }
}

function formatValue(value) {
  return Number(value || 0).toFixed(2);
}

function formatTimestamp(value) {
  if (!value) {
    return "N/A";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

loadManagementData();


