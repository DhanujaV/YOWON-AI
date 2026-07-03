const BASE_URL = "http://localhost:8000";

// ── Safe fetch helper ────────────────────────────────────────────────────────
// Never throws on HTTP error — returns null instead, keeping callers safe.
async function safeFetch(url, options = {}) {
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      console.error(`API error ${res.status} for ${url}`);
      return null;
    }
    return res.json();
  } catch (err) {
    console.error(`Network error fetching ${url}:`, err);
    return null;
  }
}

export const client = {
  // ── Audit lifecycle ──────────────────────────────────────────────────────
  startAudit: async (url, pageLimit) => {
    const res = await fetch(`${BASE_URL}/api/audits`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, page_limit: pageLimit })
    });
    return res.json();
  },

  startImageAudit: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${BASE_URL}/api/audits/image`, {
      method: "POST",
      body: formData
    });
    return res.json();
  },

  listAudits: async () => {
    const data = await safeFetch(`${BASE_URL}/api/audits`);
    return Array.isArray(data) ? data : [];
  },

  // ── Core audit data ───────────────────────────────────────────────────────
  getAudit: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}`);
    return data || {};
  },

  getJourney: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/journey`);
    // Normalise response: always return { pages: [], steps: [], is_available: bool }
    if (!data) return { pages: [], steps: [], is_available: false, success: false, message: "Journey unavailable." };
    return {
      pages: Array.isArray(data.pages) ? data.pages : [],
      steps: Array.isArray(data.steps) ? data.steps : [],
      is_available: data.is_available !== false,
      success: data.success !== false,
      message: data.message || "",
    };
  },

  getIssues: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/issues`);
    return Array.isArray(data) ? data : [];
  },

  // ── Analytics panels ──────────────────────────────────────────────────────
  getBusinessImpact: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/business-impact`);
    return data || {};
  },

  getPersonas: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/personas`);
    return Array.isArray(data) ? data : [];
  },

  getTheme: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/theme`);
    return data || {};
  },

  getPriorityAgent: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/priority-agent`);
    return data || { top_issues: [] };
  },

  getExecutiveSummary: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/executive-summary`);
    return data || {};
  },

  // ── New analytics endpoints ───────────────────────────────────────────────
  getPriorities: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/priorities`);
    return Array.isArray(data) ? data : [];
  },

  getBeforeAfter: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/before-after`);
    return Array.isArray(data) ? data : [];
  },

  getProgressHistory: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/progress-history`);
    return data || {};
  },

  getNavigationGraph: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/navigation-graph`);
    return Array.isArray(data) ? data : [];
  },

  getScoreBreakdown: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/score-breakdown`);
    return Array.isArray(data) ? data : [];
  },

  getJourneys: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/journeys`);
    return Array.isArray(data) ? data : [];
  },

  getLayoutMetrics: async (auditId) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/layout-metrics`);
    return Array.isArray(data) ? data : [];
  },

  // ── Tools ─────────────────────────────────────────────────────────────────
  runQueryStream: async (auditId, query, onToken) => {
    try {
      const res = await fetch(`${BASE_URL}/api/audits/${auditId}/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        onToken(decoder.decode(value));
      }
    } catch (err) {
      console.error("Stream query failed:", err);
    }
  },

  uploadDiff: async (auditId, file) => {
    const formData = new FormData();
    formData.append("file", file);
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/diff`, {
      method: "POST",
      body: formData
    });
    return data || { diff: "" };
  },

  reAudit: async (auditId, fixIds) => {
    const data = await safeFetch(`${BASE_URL}/api/audits/${auditId}/re-audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fix_ids: fixIds })
    });
    return data || {};
  },

  getExportUrl: (auditId) => `${BASE_URL}/api/audits/${auditId}/export`,

  getProgressSource: (auditId) =>
    new EventSource(`${BASE_URL}/api/audits/${auditId}/progress`),

  getStaticUrl: (path) => {
    if (!path) return "";
    return `${BASE_URL}/${path.replace(/^\//, "")}`;
  },

  getConsistencyUrl: (auditId) =>
    `${BASE_URL}/api/audits/${auditId}/consistency`,
};
