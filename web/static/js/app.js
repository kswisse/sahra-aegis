import { api } from "./api.js";

// Global State
const state = {
  currentTab: "overview",
  zones: [],
  selectedZone: null,
  currentPopulationGroup: "school",
  liveResult: null,
  dayResult: null,
  currentHourIndex: 14, // default to peak afternoon
  isPlaying: false,
  playTimer: null,
  playbackSpeed: 1000,
  chartInstance: null,
  auditFilter: "all",
  auditRecords: [],
  pendingQueue: [],
  sandboxParams: {
    air_temp_c: 44.0,
    humidity_pct: 60.0,
    solar_wm2: 850.0,
    wind_ms: 2.5,
    enable_dispute: false,
    site_wbgt_c: 29.0,
    group: "school",
  },
};

// Colors mapping (Light / Neon White Theme)
const RISK_COLORS = {
  low: { bg: "bg-emerald-50", border: "border-emerald-300", text: "text-emerald-800", hex: "#059669", label: "LOW RISK (< 28°C)" },
  moderate: { bg: "bg-amber-50", border: "border-amber-300", text: "text-amber-800", hex: "#d97706", label: "MODERATE RISK (28 - 30°C)" },
  high: { bg: "bg-orange-50", border: "border-orange-300", text: "text-orange-800", hex: "#ea580c", label: "HIGH RISK (30 - 32°C)" },
  extreme: { bg: "bg-red-50", border: "border-red-300", text: "text-red-800", hex: "#dc2626", label: "EXTREME HAZARD (≥ 32°C)" },
};

// Initialize Application
document.addEventListener("DOMContentLoaded", async () => {
  initClock();
  setupTabNavigation();
  setupEventListeners();

  try {
    await loadInitialData();
  } catch (err) {
    console.error("Initialization error:", err);
    showToast("Error loading data: " + err.message, "error");
  }
});

// Live Dubai Clock (UTC+4)
function initClock() {
  const clockEl = document.getElementById("dubai-clock");
  if (!clockEl) return;

  function update() {
    const now = new Date();
    const dubaiTime = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Dubai" }));
    const timeStr = dubaiTime.toLocaleTimeString("en-GB", { hour12: false });
    const dateStr = dubaiTime.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
    clockEl.innerHTML = `<span class="text-sky-700 font-mono font-bold">${timeStr}</span> <span class="text-slate-500 text-xs">GST (Dubai UTC+4) · ${dateStr}</span>`;
  }
  update();
  setInterval(update, 1000);
}

// Tab Navigation
function setupTabNavigation() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      switchTab(target);
    });
  });
}

function switchTab(tabName) {
  state.currentTab = tabName;
  document.querySelectorAll(".nav-tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === tabName);
  });
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.toggle("hidden", pane.id !== `tab-${tabName}`);
  });

  // Tab specific refreshes
  if (tabName === "supervisor" && !state.chartInstance) {
    initOrUpdateChart();
  } else if (tabName === "hitl") {
    refreshPendingQueue();
  } else if (tabName === "audit") {
    refreshAuditTrail();
  } else if (tabName === "benchmarks") {
    loadBenchmarks();
  }
}

// Load Initial Data
async function loadInitialData() {
  // Load zones
  const zones = await api.getZones();
  state.zones = zones;
  state.selectedZone = zones[0];

  const zoneSelect = document.getElementById("zone-selector");
  if (zoneSelect) {
    zoneSelect.innerHTML = zones
      .map((z) => `<option value="${z.id}">${z.name} [${z.category}]</option>`)
      .join("");
    zoneSelect.addEventListener("change", (e) => {
      const z = state.zones.find((item) => item.id === e.target.value);
      if (z) {
        state.selectedZone = z;
        if (z.group) {
          state.currentPopulationGroup = z.group;
          updateGroupToggleUI();
        }
        triggerZoneExecution(z);
      }
    });
  }

  // Load initial cycle & day simulation
  await triggerZoneExecution(state.selectedZone);
  await refreshPendingQueue();
}

// Execute zone analysis
async function triggerZoneExecution(zone) {
  showLoading(true);
  try {
    const fixture = zone.default_fixture || "dubai_hourly_2026-08-13.json";

    // Run day simulation
    const dayData = await api.simulateDay(fixture, zone.id, state.currentPopulationGroup);
    state.dayResult = dayData;

    // Pick hour step (default 14:00 or peak)
    const peakHourStr = dayData.peak_at ? dayData.peak_at.substring(11, 16) : "14:00";
    let targetIdx = dayData.steps.findIndex((s) => s.hour === peakHourStr);
    if (targetIdx === -1) targetIdx = Math.min(14, dayData.steps.length - 1);
    state.currentHourIndex = targetIdx;

    const currentStep = dayData.steps[state.currentHourIndex];

    // Run single cycle for rich multi-agent transcript inspection
    const wx = zone.default_weather || {
      air_temp_c: currentStep.air_temp_c || 42.0,
      humidity_pct: 55.0,
      solar_wm2: 900.0,
      wind_ms: 2.0,
    };
    const site = zone.default_site ? zone.default_site.wbgt_c : null;
    const sat = zone.default_satellite ? zone.default_satellite.lst_c : null;

    const cycleData = await api.simulateCycle({
      zone_id: zone.id,
      group: state.currentPopulationGroup,
      air_temp_c: wx.air_temp_c,
      humidity_pct: wx.humidity_pct,
      solar_wm2: wx.solar_wm2 || 800.0,
      wind_ms: wx.wind_ms || 2.0,
      site_wbgt_c: site,
      satellite_lst_c: sat,
    });
    state.liveResult = cycleData;

    // Render components
    renderOverview();
    renderSupervisorStep(state.currentHourIndex);
    initOrUpdateChart();
    renderMultiAgent();
    await refreshPendingQueue();
  } catch (err) {
    console.error(err);
    showToast(err.message, "error");
  } finally {
    showLoading(false);
  }
}

// Render Overview Tab
function renderOverview() {
  const result = state.liveResult;
  if (!result) return;

  const assessment = result.assessment;
  const stateData = result.state;
  const level = assessment.level.toLowerCase();
  const cfg = RISK_COLORS[level] || RISK_COLORS.low;

  // WBGT Gauge & Badge
  const wbgtVal = document.getElementById("overview-wbgt");
  if (wbgtVal) wbgtVal.textContent = assessment.wbgt_c.toFixed(1);

  const riskBadge = document.getElementById("overview-risk-badge");
  if (riskBadge) {
    riskBadge.className = `px-3 py-1 rounded-full text-xs font-bold tracking-wider uppercase border ${cfg.bg} ${cfg.border} ${cfg.text}`;
    riskBadge.textContent = cfg.label;
  }

  const scoreEl = document.getElementById("overview-risk-score");
  if (scoreEl) scoreEl.textContent = (assessment.score * 100).toFixed(1) + "%";

  const groupWeightEl = document.getElementById("overview-vulnerability");
  if (groupWeightEl) {
    groupWeightEl.textContent = state.currentPopulationGroup === "school" ? "1.00x (Standard Education)" : "1.05x (MOHRE Outdoor Work)";
  }

  // Telemetry Cards
  document.getElementById("card-air-temp").textContent = stateData.air_temp_c.toFixed(1) + " °C";
  document.getElementById("card-humidity").textContent = stateData.humidity_pct.toFixed(0) + " %";

  const lstEl = document.getElementById("card-lst");
  if (lstEl) lstEl.textContent = stateData.lst_c ? stateData.lst_c.toFixed(1) + " °C" : "N/A (Optical Cloud / Inactive)";

  const sourceTierEl = document.getElementById("card-source-tier");
  if (sourceTierEl) sourceTierEl.textContent = stateData.source_tier;

  // Midday Ban Indicator
  const middayBanBanner = document.getElementById("mohre-midday-banner");
  if (middayBanBanner) {
    const isOutdoor = state.currentPopulationGroup === "outdoor_worker";
    const isExtremeOrPeak = assessment.wbgt_c >= 32.0;
    if (isOutdoor && isExtremeOrPeak) {
      middayBanBanner.classList.remove("hidden");
    } else {
      middayBanBanner.classList.add("hidden");
    }
  }

  // Interventions List (clean, no emojis)
  const actionsList = document.getElementById("overview-actions-list");
  if (actionsList) {
    if (result.actions.length === 0) {
      actionsList.innerHTML = `<div class="text-slate-500 text-xs italic">No active interventions required for current thermal index.</div>`;
    } else {
      actionsList.innerHTML = result.actions
        .map((a) => {
          const isRefused = a.status === "refused";
          const statusBadge = isRefused
            ? `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-300">REFUSED (Approval Gate)</span>`
            : `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-300">EXECUTED</span>`;

          return `
            <div class="p-3.5 rounded-lg border ${isRefused ? "border-rose-300 bg-rose-50/50" : "border-slate-200 bg-white/70"} flex items-start justify-between gap-3 shadow-sm">
              <div class="flex items-start gap-3">
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-slate-800 capitalize">${a.intervention.kind.replace("_", " ")}</span>
                    ${statusBadge}
                  </div>
                  <p class="text-xs text-slate-600 mt-1">${a.intervention.reason}</p>
                  <p class="text-[11px] text-slate-400 mt-1 font-mono">Risk Reduction: ${(a.intervention.expected_risk_reduction * 100).toFixed(0)}% · Consequential: ${a.intervention.consequential ? "YES" : "NO"}</p>
                </div>
              </div>
            </div>
          `;
        })
        .join("");
    }
  }

  // Advisory Output Box
  const advisoryBox = document.getElementById("overview-advisory-text");
  if (advisoryBox) {
    const lines = [
      `SAHRA AEGIS OFFICIAL DISPATCH - ZONE: ${result.zone_id.toUpperCase()}`,
      `Timestamp: ${result.at}`,
      `Risk Level: ${assessment.level.toUpperCase()} (WBGT ${assessment.wbgt_c.toFixed(1)} C, Occupational Threshold 28.0 C)`,
      `Population Profile: ${assessment.group} (Weight: ${assessment.score > 0 ? "Applied" : "Nominal"})`,
      `--- MANDATED PROTOCOLS ---`,
    ];
    result.actions.forEach((a) => {
      lines.push(`[${a.status.toUpperCase()}] ${a.intervention.kind.toUpperCase()}: ${a.intervention.reason}`);
    });
    advisoryBox.textContent = lines.join("\n");
  }
}

// Render 24-Hour Supervisor Chart & Controls
function initOrUpdateChart() {
  const ctx = document.getElementById("supervisorChart");
  if (!ctx || !state.dayResult) return;

  const steps = state.dayResult.steps;
  const labels = steps.map((s) => s.hour);
  const wbgtData = steps.map((s) => s.wbgt_c);
  const airData = steps.map((s) => s.air_temp_c);

  if (state.chartInstance) {
    state.chartInstance.destroy();
  }

  // Chart.js configuration tailored for Neon White / Light background
  state.chartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Derived WBGT (°C)",
          data: wbgtData,
          borderColor: "#ea580c",
          backgroundColor: "rgba(234, 88, 12, 0.12)",
          borderWidth: 2.5,
          tension: 0.35,
          fill: true,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: "#ea580c",
        },
        {
          label: "Ambient Air Temp (°C)",
          data: airData,
          borderColor: "#0284c7",
          backgroundColor: "transparent",
          borderWidth: 2,
          borderDash: [4, 4],
          tension: 0.35,
          pointRadius: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          labels: { color: "#334155", font: { family: "Arial", size: 12, weight: "bold" } },
        },
        tooltip: {
          backgroundColor: "rgba(255, 255, 255, 0.95)",
          titleColor: "#0f172a",
          bodyColor: "#334155",
          borderColor: "rgba(203, 213, 225, 0.9)",
          borderWidth: 1,
          padding: 10,
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(203, 213, 225, 0.4)" },
          ticks: { color: "#475569", font: { family: "Courier New", size: 11 } },
        },
        y: {
          grid: { color: "rgba(203, 213, 225, 0.4)" },
          ticks: { color: "#475569", font: { family: "Courier New", size: 11 } },
          min: 20,
          max: 48,
        },
      },
    },
  });
}

function renderSupervisorStep(index) {
  if (!state.dayResult || !state.dayResult.steps[index]) return;
  const step = state.dayResult.steps[index];

  document.getElementById("step-hour-display").textContent = step.hour;
  document.getElementById("step-slider").value = index;
  document.getElementById("step-wbgt").textContent = step.wbgt_c.toFixed(1) + " °C";
  document.getElementById("step-air").textContent = step.air_temp_c.toFixed(1) + " °C";

  const cfg = RISK_COLORS[step.level.toLowerCase()] || RISK_COLORS.low;
  const badge = document.getElementById("step-band-badge");
  badge.className = `px-3 py-1 rounded-full text-xs font-bold uppercase border ${cfg.bg} ${cfg.border} ${cfg.text}`;
  badge.textContent = step.level.toUpperCase();

  // Dispatched & Active Kinds
  const dispatchedEl = document.getElementById("step-dispatched-kinds");
  if (step.dispatched_kinds.length === 0) {
    dispatchedEl.innerHTML = `<span class="text-slate-400 italic text-xs">None new this hour</span>`;
  } else {
    dispatchedEl.innerHTML = step.dispatched_kinds
      .map((k) => `<span class="px-2 py-0.5 rounded text-xs bg-sky-50 text-sky-800 border border-sky-200 font-mono">${k}</span>`)
      .join(" ");
  }

  const activeEl = document.getElementById("step-active-kinds");
  if (step.actions.length === 0) {
    activeEl.innerHTML = `<span class="text-slate-400 italic text-xs">No active interventions</span>`;
  } else {
    activeEl.innerHTML = step.actions
      .map((a) => {
        const isRefused = a.status === "refused";
        const color = isRefused ? "bg-rose-50 text-rose-800 border-rose-200" : "bg-emerald-50 text-emerald-800 border-emerald-200";
        return `<span class="px-2 py-0.5 rounded text-xs font-mono border ${color}">${a.kind} = ${a.status}</span>`;
      })
      .join(" ");
  }

  // Peak callout
  const peakBox = document.getElementById("step-peak-info");
  if (peakBox && state.dayResult.peak_wbgt_c) {
    const peakHour = state.dayResult.peak_at.substring(11, 16);
    peakBox.innerHTML = `Peak Day WBGT: <span class="text-red-700 font-bold">${state.dayResult.peak_wbgt_c.toFixed(1)} °C</span> at <span class="text-slate-900 font-bold">${peakHour} local</span> (Extreme Band Escalation)`;
  }
}

// Render Multi-Agent Architecture & Transcript (no emojis)
function renderMultiAgent() {
  const result = state.liveResult;
  if (!result || !result.transcript) return;

  const transcriptFeed = document.getElementById("agent-transcript-feed");
  if (!transcriptFeed) return;

  const roleColors = {
    monitor: "text-blue-800 border-blue-200 bg-blue-50",
    predict: "text-amber-800 border-amber-200 bg-amber-50",
    arbiter: "text-purple-800 border-purple-200 bg-purple-50",
    plan: "text-emerald-800 border-emerald-200 bg-emerald-50",
    act: "text-rose-800 border-rose-200 bg-rose-50",
    verify: "text-cyan-800 border-cyan-200 bg-cyan-50",
  };

  transcriptFeed.innerHTML = result.transcript
    .map((msg) => {
      const senderStyle = roleColors[msg.sender] || "text-slate-700";
      const recipientStyle = roleColors[msg.recipient] || "text-slate-700";

      let summary = "";
      if (msg.kind === "observation") {
        summary = `Observing zone ${msg.payload.state?.zone_id || ""}: Weather WBGT ${msg.payload.weather_wbgt_c ?? "N/A"}°C, Site WBGT ${msg.payload.site_wbgt_c ?? "None"}`;
      } else if (msg.kind === "dispute") {
        summary = `DISPUTE RAISED: Readings diverge > 1.0°C! (${msg.payload.topic})`;
      } else if (msg.kind === "ruling") {
        summary = `ARBITER RULING: Policy=${msg.payload.policy} -> Chose ${msg.payload.chosen_c}°C. Reason: ${msg.payload.reasoning}`;
      } else if (msg.kind === "assessment") {
        summary = `Assessed WBGT ${msg.payload.assessment?.wbgt_c}°C, Level: ${msg.payload.assessment?.level}, Score: ${msg.payload.assessment?.score}`;
      } else if (msg.kind === "proposal") {
        summary = `Proposed ${msg.payload.interventions?.length || 0} interventions: ${msg.payload.interventions?.map((i) => i.kind).join(", ")}`;
      } else if (msg.kind === "decision") {
        summary = `Decisions: ${msg.payload.actions?.map((a) => `${a.intervention.kind}=${a.status}`).join(", ")}`;
      } else {
        summary = JSON.stringify(msg.payload);
      }

      return `
        <div class="p-3 rounded-lg border border-slate-200 bg-white font-mono text-xs shadow-sm">
          <div class="flex items-center justify-between gap-2 mb-1.5 pb-1 border-b border-slate-100">
            <div class="flex items-center gap-1.5">
              <span class="px-2 py-0.5 rounded font-bold uppercase border ${senderStyle}">${msg.sender}</span>
              <span class="text-slate-400 font-bold">-></span>
              <span class="px-2 py-0.5 rounded font-bold uppercase border ${recipientStyle}">${msg.recipient}</span>
              <span class="ml-2 px-1.5 py-0.5 rounded bg-slate-100 text-sky-800 text-[10px] uppercase font-bold tracking-wider">${msg.kind}</span>
            </div>
            <span class="text-slate-400 text-[10px]">${msg.at.substring(11, 19)} UTC</span>
          </div>
          <div class="text-slate-700 pl-1 leading-relaxed">${summary}</div>
        </div>
      `;
    })
    .join("");

  // Arbiter Highlight Box
  const disputeAlert = document.getElementById("arbiter-ruling-card");
  if (disputeAlert) {
    if (result.dispute_detected && result.ruling) {
      disputeAlert.classList.remove("hidden");
      document.getElementById("ruling-chosen-val").textContent = result.ruling.chosen_c + " °C";
      document.getElementById("ruling-reasoning").textContent = result.ruling.reasoning;
    } else {
      disputeAlert.classList.add("hidden");
    }
  }

  // Verifier Status
  const verifierBadge = document.getElementById("verifier-badge");
  if (verifierBadge) {
    const isOk = result.verification && result.verification.ok;
    verifierBadge.className = isOk ? "text-emerald-700 font-bold font-mono text-xs" : "text-rose-700 font-bold font-mono text-xs";
    verifierBadge.textContent = isOk ? "VERIFICATION PASSED (Invariant Guardrails Valid)" : "VERIFICATION FAILED";
  }
}

// Refresh Pending Queue (HITL) - clean, no emojis
async function refreshPendingQueue() {
  try {
    const queue = await api.getQueue();
    state.pendingQueue = queue;

    const countBadge = document.getElementById("hitl-badge-count");
    if (countBadge) {
      countBadge.textContent = queue.length;
      countBadge.className = queue.length > 0 ? "ml-1.5 px-2 py-0.2 text-[10px] font-bold rounded-full bg-rose-600 text-white" : "ml-1.5 px-2 py-0.2 text-[10px] font-bold rounded-full bg-slate-200 text-slate-700";
    }

    const container = document.getElementById("hitl-cards-container");
    if (!container) return;

    if (queue.length === 0) {
      container.innerHTML = `
        <div class="p-8 text-center text-slate-500 glass-panel">
          <p class="font-bold text-slate-800 text-sm">Approval Queue Empty</p>
          <p class="text-xs text-slate-500 mt-1">No consequential actions are currently waiting for human supervisor sign-off.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = queue
      .map((item) => {
        return `
        <div class="p-5 glass-panel-accent border border-rose-300 relative overflow-hidden" id="card-${item.request_id}">
          <div class="flex items-start justify-between">
            <div>
              <div class="flex items-center gap-2">
                <span class="text-rose-800 font-bold text-xs uppercase tracking-wide">Pending Authorization</span>
                <span class="px-2 py-0.5 bg-rose-100 text-rose-800 text-xs rounded font-mono border border-rose-200">REQ: ${item.request_id}</span>
              </div>
              <h3 class="text-base font-bold text-slate-900 mt-1 capitalize">Intervention: ${item.intervention.kind.replace("_", " ")}</h3>
              <p class="text-xs text-slate-500 mt-0.5">Target Zone: <span class="font-mono text-slate-800">${item.zone_id}</span></p>
            </div>
            <div class="text-right">
              <span class="text-xs text-slate-500">Worst Severity Observed</span>
              <div class="text-2xl font-bold text-rose-700 font-mono">${item.severity ? item.severity.toFixed(1) : "32+"} °C WBGT</div>
            </div>
          </div>

          <div class="my-4 p-3 rounded bg-slate-50 border border-slate-200 text-xs text-slate-700">
            <span class="text-slate-500 font-semibold block mb-1">Gate Refusal Reason:</span>
            <p>${item.intervention.reason}</p>
            <div class="mt-2 text-[11px] text-slate-400 font-mono">
              Requested: ${item.requested_at ? item.requested_at.substring(11, 19) : ""} UTC
              ${item.refreshed_at ? ` · Refreshed: ${item.refreshed_at.substring(11, 19)} UTC` : ""}
            </div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-200">
            <div class="flex items-center gap-2">
              <label class="text-xs text-slate-600 font-medium">Supervisor ID:</label>
              <input type="text" id="approver-input-${item.request_id}" value="coordinator@dxbops" class="bg-white border border-slate-300 text-slate-800 text-xs px-2.5 py-1.5 rounded focus:outline-none focus:border-sky-500 font-mono w-48 shadow-sm">
            </div>
            <div class="flex items-center gap-2">
              <button onclick="window.decideRequest('${item.request_id}', false)" class="px-3 py-1.5 rounded text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition">
                Decline (Keep Refused)
              </button>
              <button onclick="window.decideRequest('${item.request_id}', true)" class="px-4 py-1.5 rounded text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition">
                Authorize & Execute
              </button>
            </div>
          </div>
        </div>
      `;
      })
      .join("");
  } catch (err) {
    console.error("Queue refresh error:", err);
  }
}

// Global decision handler
window.decideRequest = async (requestId, approve) => {
  const input = document.getElementById(`approver-input-${requestId}`);
  const approver = input ? input.value.trim() : "coordinator@dxbops";
  if (!approver) {
    showToast("Please enter an approver ID", "warning");
    return;
  }

  try {
    await api.decideQueue(requestId, approver, approve);
    showToast(`Request ${requestId} ${approve ? "APPROVED" : "DECLINED"} by ${approver}`, "success");
    await refreshPendingQueue();
    await refreshAuditTrail();
  } catch (err) {
    showToast("Decision failed: " + err.message, "error");
  }
};

// Refresh Audit Trail
async function refreshAuditTrail() {
  const tbody = document.getElementById("audit-table-body");
  if (!tbody) return;

  try {
    const records = await api.getAudit(50, state.auditFilter);
    state.auditRecords = records;

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-400 text-xs">No audit records logged yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = records
      .map((r) => {
        const isRefused = r.status === "refused";
        const statusBadge = isRefused
          ? `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-800 border border-rose-300">REFUSED</span>`
          : `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-300">EXECUTED</span>`;

        const approverStr = r.approved_by ? `<span class="text-sky-700 font-mono font-bold">${r.approved_by}</span>` : `<span class="text-slate-400 font-mono">None</span>`;

        return `
        <tr class="border-b border-slate-200 hover:bg-slate-50 text-xs transition">
          <td class="p-3 font-mono text-slate-600">${r.action_id}</td>
          <td class="p-3 text-slate-700">${r.at ? r.at.substring(0, 19).replace("T", " ") : ""}</td>
          <td class="p-3 font-semibold text-slate-800 capitalize">${r.intervention?.kind || ""}</td>
          <td class="p-3">${statusBadge}</td>
          <td class="p-3">${approverStr}</td>
          <td class="p-3 text-right">
            <button onclick="window.viewAuditTrace('${r.action_id}')" class="text-sky-700 hover:text-sky-900 font-mono text-xs font-semibold">
              View Trace
            </button>
          </td>
        </tr>
      `;
      })
      .join("");
  } catch (err) {
    console.error("Audit load error:", err);
  }
}

window.viewAuditTrace = (actionId) => {
  const record = state.auditRecords.find((r) => r.action_id === actionId);
  if (!record) return;

  const modal = document.getElementById("trace-modal");
  const content = document.getElementById("trace-modal-content");
  if (!modal || !content) return;

  content.innerHTML = `
    <div class="space-y-3 font-mono text-xs">
      <div><span class="text-slate-500">Action ID:</span> <span class="text-sky-800 font-bold">${record.action_id}</span></div>
      <div><span class="text-slate-500">Intervention:</span> <span class="text-slate-800 font-semibold">${record.intervention.kind}</span></div>
      <div><span class="text-slate-500">Status:</span> <span class="text-slate-800 font-semibold">${record.status}</span></div>
      <div><span class="text-slate-500">Approved By:</span> <span class="text-slate-800">${record.approved_by || "None"}</span></div>
      <div><span class="text-slate-500">Timestamp:</span> <span class="text-slate-800">${record.at}</span></div>
      <div class="pt-2 border-t border-slate-200">
        <span class="text-slate-500 block mb-1">Reason Trace (Audit Evidence Chain):</span>
        <div class="bg-slate-50 p-3 rounded border border-slate-200 space-y-1">
          ${record.reason_trace.map((t) => `<div class="text-slate-700">• ${t}</div>`).join("")}
        </div>
      </div>
    </div>
  `;
  modal.classList.remove("hidden");
};

window.closeTraceModal = () => {
  const modal = document.getElementById("trace-modal");
  if (modal) modal.classList.add("hidden");
};

// Sandbox Calculations
async function updateSandboxPhysics() {
  const temp = parseFloat(document.getElementById("slider-air-temp").value);
  const rh = parseFloat(document.getElementById("slider-rh").value);
  const solar = parseFloat(document.getElementById("slider-solar").value);
  const wind = parseFloat(document.getElementById("slider-wind").value);
  const enableDispute = document.getElementById("toggle-dispute").checked;
  const siteWbgt = parseFloat(document.getElementById("slider-site-wbgt").value);

  document.getElementById("val-air-temp").textContent = temp.toFixed(1) + " °C";
  document.getElementById("val-rh").textContent = rh.toFixed(0) + " %";
  document.getElementById("val-solar").textContent = solar.toFixed(0) + " W/m²";
  document.getElementById("val-wind").textContent = wind.toFixed(1) + " m/s";
  document.getElementById("val-site-wbgt").textContent = siteWbgt.toFixed(1) + " °C";

  const siteWbgtContainer = document.getElementById("container-site-wbgt");
  if (siteWbgtContainer) {
    siteWbgtContainer.classList.toggle("hidden", !enableDispute);
  }

  try {
    const calc = await api.calculateRisk({
      air_temp_c: temp,
      humidity_pct: rh,
      solar_wm2: solar,
      wind_ms: wind,
      group: state.currentPopulationGroup,
    });

    document.getElementById("sb-out-wbgt").textContent = calc.wbgt_outdoor_c.toFixed(1);
    document.getElementById("sb-out-fallback").textContent = calc.wbgt_fallback_c.toFixed(1) + " °C";
    document.getElementById("sb-out-globe").textContent = calc.globe_temp_c.toFixed(1) + " °C";
    document.getElementById("sb-out-solar-delta").textContent = "+" + calc.solar_delta_c.toFixed(1) + " °C";

    const cfg = RISK_COLORS[calc.risk_level.toLowerCase()] || RISK_COLORS.low;
    const badge = document.getElementById("sb-out-band");
    badge.className = `px-3 py-1 rounded-full text-xs font-bold uppercase border ${cfg.bg} ${cfg.border} ${cfg.text}`;
    badge.textContent = calc.risk_level.toUpperCase();
  } catch (err) {
    console.error("Sandbox calc error:", err);
  }
}

// Setup Event Listeners
function setupEventListeners() {
  // Population Group Toggle
  const groupToggleBtns = document.querySelectorAll(".group-toggle-btn");
  groupToggleBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      state.currentPopulationGroup = btn.dataset.group;
      updateGroupToggleUI();
      if (state.selectedZone) {
        triggerZoneExecution(state.selectedZone);
      }
    });
  });

  // Supervisor Playback Controls
  const stepSlider = document.getElementById("step-slider");
  if (stepSlider) {
    stepSlider.addEventListener("input", (e) => {
      state.currentHourIndex = parseInt(e.target.value);
      renderSupervisorStep(state.currentHourIndex);
    });
  }

  const btnPrev = document.getElementById("btn-prev-hour");
  const btnNext = document.getElementById("btn-next-hour");
  const btnPlay = document.getElementById("btn-play-pause");

  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      if (state.currentHourIndex > 0) {
        state.currentHourIndex--;
        renderSupervisorStep(state.currentHourIndex);
      }
    });
  }

  if (btnNext) {
    btnNext.addEventListener("click", () => {
      if (state.dayResult && state.currentHourIndex < state.dayResult.steps.length - 1) {
        state.currentHourIndex++;
        renderSupervisorStep(state.currentHourIndex);
      }
    });
  }

  if (btnPlay) {
    btnPlay.addEventListener("click", () => {
      state.isPlaying = !state.isPlaying;
      btnPlay.textContent = state.isPlaying ? "Pause" : "Play";
      if (state.isPlaying) {
        startPlayTimer();
      } else {
        clearInterval(state.playTimer);
      }
    });
  }

  // Sandbox inputs
  ["slider-air-temp", "slider-rh", "slider-solar", "slider-wind", "slider-site-wbgt"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", updateSandboxPhysics);
  });

  const toggleDispute = document.getElementById("toggle-dispute");
  if (toggleDispute) toggleDispute.addEventListener("change", updateSandboxPhysics);

  const btnRunSandbox = document.getElementById("btn-run-sandbox");
  if (btnRunSandbox) {
    btnRunSandbox.addEventListener("click", async () => {
      const temp = parseFloat(document.getElementById("slider-air-temp").value);
      const rh = parseFloat(document.getElementById("slider-rh").value);
      const solar = parseFloat(document.getElementById("slider-solar").value);
      const wind = parseFloat(document.getElementById("slider-wind").value);
      const enableDispute = document.getElementById("toggle-dispute").checked;
      const siteWbgt = enableDispute ? parseFloat(document.getElementById("slider-site-wbgt").value) : null;

      try {
        showLoading(true);
        const res = await api.simulateCycle({
          zone_id: "sandbox-custom-zone",
          group: state.currentPopulationGroup,
          air_temp_c: temp,
          humidity_pct: rh,
          solar_wm2: solar,
          wind_ms: wind,
          site_wbgt_c: siteWbgt,
        });
        state.liveResult = res;
        renderOverview();
        renderMultiAgent();
        switchTab("multiagent");
        showToast("Sandbox cycle executed successfully.", "success");
      } catch (err) {
        showToast(err.message, "error");
      } finally {
        showLoading(false);
      }
    });
  }

  // Audit filter
  const auditFilterSel = document.getElementById("audit-filter-status");
  if (auditFilterSel) {
    auditFilterSel.addEventListener("change", (e) => {
      state.auditFilter = e.target.value;
      refreshAuditTrail();
    });
  }
}

function startPlayTimer() {
  clearInterval(state.playTimer);
  state.playTimer = setInterval(() => {
    if (!state.dayResult) return;
    if (state.currentHourIndex < state.dayResult.steps.length - 1) {
      state.currentHourIndex++;
    } else {
      state.currentHourIndex = 0;
    }
    renderSupervisorStep(state.currentHourIndex);
  }, 1200);
}

function updateGroupToggleUI() {
  document.querySelectorAll(".group-toggle-btn").forEach((btn) => {
    const isActive = btn.dataset.group === state.currentPopulationGroup;
    btn.classList.toggle("bg-sky-600", isActive);
    btn.classList.toggle("text-white", isActive);
    btn.classList.toggle("bg-transparent", !isActive);
    btn.classList.toggle("text-slate-600", !isActive);
  });
}

// Load Benchmark Days
async function loadBenchmarks() {
  const container = document.getElementById("benchmarks-container");
  if (!container) return;

  try {
    const data = await api.getReplay();
    document.getElementById("benchmark-note").textContent = data.note;

    container.innerHTML = data.days
      .map((d) => {
        const diff = d.record_air_temp_c ? (d.air_temp_c - d.record_air_temp_c).toFixed(1) : null;
        const diffBadge = diff ? `<span class="text-xs font-mono ${Math.abs(diff) > 3 ? "text-amber-700" : "text-slate-500"}">(${diff > 0 ? "+" : ""}${diff}°C vs NCM)</span>` : "";

        const cfg = RISK_COLORS[d.band.toLowerCase()] || RISK_COLORS.low;

        return `
        <tr class="border-b border-slate-200 text-xs hover:bg-slate-50">
          <td class="p-3 font-mono text-slate-800 font-semibold">${d.place}</td>
          <td class="p-3 text-slate-600">${d.date}</td>
          <td class="p-3 font-mono text-slate-900">${d.air_temp_c.toFixed(1)} °C ${diffBadge}</td>
          <td class="p-3 font-mono text-slate-600">${d.humidity_pct}%</td>
          <td class="p-3 font-mono font-bold text-orange-700">${d.outdoor_wbgt_c.toFixed(1)} °C</td>
          <td class="p-3 font-mono text-slate-600">${d.fallback_wbgt_c.toFixed(1)} °C</td>
          <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${cfg.bg} ${cfg.border} ${cfg.text}">${d.band}</span></td>
          <td class="p-3 text-slate-600">${d.mohre_compliance}</td>
        </tr>
      `;
      })
      .join("");
  } catch (err) {
    console.error("Benchmark error:", err);
  }
}

// Toast Notifications (clean, no emojis)
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  const bg = type === "error" ? "bg-rose-50 text-rose-900 border-rose-300" : type === "success" ? "bg-emerald-50 text-emerald-900 border-emerald-300" : "bg-sky-50 text-sky-900 border-sky-300";

  toast.className = `p-3.5 rounded-lg border text-xs shadow-lg flex items-center gap-2 animate-fade-in ${bg}`;
  toast.innerHTML = `<span>${message}</span>`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function showLoading(active) {
  const spinner = document.getElementById("global-spinner");
  if (spinner) spinner.classList.toggle("hidden", !active);
}
