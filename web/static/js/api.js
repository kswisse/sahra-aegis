/**
 * SAHRA AEGIS API Client
 * Facilitates communication with the FastAPI backend
 */

const API_BASE = window.location.origin;

export const api = {
  async getStatus() {
    const res = await fetch(`${API_BASE}/api/status`);
    if (!res.ok) throw new Error("Failed to fetch system status");
    return await res.json();
  },

  async getZones() {
    const res = await fetch(`${API_BASE}/api/zones`);
    if (!res.ok) throw new Error("Failed to fetch zones");
    return await res.json();
  },

  async getFixtures() {
    const res = await fetch(`${API_BASE}/api/fixtures`);
    if (!res.ok) throw new Error("Failed to fetch fixtures");
    return await res.json();
  },

  async simulateCycle(params) {
    const res = await fetch(`${API_BASE}/api/simulate/cycle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Cycle simulation failed");
    }
    return await res.json();
  },

  async simulateDay(fixtureFilename, zoneId = null, group = "school") {
    const res = await fetch(`${API_BASE}/api/simulate/day`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fixture_filename: fixtureFilename,
        zone_id: zoneId,
        group: group,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Day simulation failed");
    }
    return await res.json();
  },

  async getQueue() {
    const res = await fetch(`${API_BASE}/api/hitl/queue`);
    if (!res.ok) throw new Error("Failed to fetch HITL queue");
    return await res.json();
  },

  async decideQueue(requestId, approver, approve = true) {
    const res = await fetch(`${API_BASE}/api/hitl/decide`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: requestId,
        approver: approver,
        approve: approve,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Decision failed");
    }
    return await res.json();
  },

  async getAudit(limit = 100, status = "all") {
    const res = await fetch(`${API_BASE}/api/audit?limit=${limit}&status=${status}`);
    if (!res.ok) throw new Error("Failed to fetch audit trail");
    return await res.json();
  },

  async calculateRisk(params) {
    const res = await fetch(`${API_BASE}/api/calculate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    if (!res.ok) throw new Error("Calculation failed");
    return await res.json();
  },

  async getReplay() {
    const res = await fetch(`${API_BASE}/api/replay`);
    if (!res.ok) throw new Error("Failed to fetch replay benchmark");
    return await res.json();
  },
};
