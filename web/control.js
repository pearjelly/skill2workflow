(function () {
  const EXAMPLE_URL = "../examples/control-plane-snapshot.json";
  const state = {
    snapshot: null,
    view: "operator",
    selected: null,
    filter: "",
  };

  const els = {};

  window.addEventListener("DOMContentLoaded", init);

  function init() {
    cacheElements();
    bindEvents();
    loadExample();
  }

  function cacheElements() {
    els.loadExample = document.getElementById("load-example");
    els.snapshotFile = document.getElementById("snapshot-file");
    els.filterInput = document.getElementById("filter-input");
    els.status = document.getElementById("status-pill");
    els.tabs = Array.from(document.querySelectorAll(".tab"));
    els.panels = Array.from(document.querySelectorAll("[data-panel]"));
    els.metricWorkflows = document.getElementById("metric-workflows");
    els.metricRuns = document.getElementById("metric-runs");
    els.metricAttention = document.getElementById("metric-attention");
    els.metricAudit = document.getElementById("metric-audit");
    els.metricConnectors = document.getElementById("metric-connectors");
    els.attentionRows = document.getElementById("attention-rows");
    els.recentEventRows = document.getElementById("recent-event-rows");
    els.connectorEventRows = document.getElementById("connector-event-rows");
    els.operatorVersionRows = document.getElementById("operator-version-rows");
    els.workflowRows = document.getElementById("workflow-rows");
    els.runRows = document.getElementById("run-rows");
    els.auditRows = document.getElementById("audit-rows");
    els.connectorRows = document.getElementById("connector-rows");
    els.versionRows = document.getElementById("version-rows");
    els.detailTitle = document.getElementById("detail-title");
    els.statusGrid = document.getElementById("status-grid");
    els.detailJson = document.getElementById("detail-json");
  }

  function bindEvents() {
    els.loadExample.addEventListener("click", loadExample);
    els.snapshotFile.addEventListener("change", loadSelectedFile);
    els.filterInput.addEventListener("input", function () {
      state.filter = els.filterInput.value.trim().toLowerCase();
      renderTables();
    });
    els.tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        setView(tab.dataset.view);
      });
    });
  }

  async function loadExample() {
    setStatus("Loading", "");
    try {
      const response = await fetch(EXAMPLE_URL, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("snapshot unavailable");
      }
      loadSnapshot(await response.json(), "Example Snapshot");
    } catch (error) {
      setStatus("Invalid", "is-invalid");
      showDetail("Error", { error: error.message });
    }
  }

  async function loadSelectedFile(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) {
      return;
    }
    try {
      loadSnapshot(JSON.parse(await file.text()), file.name);
    } catch (error) {
      setStatus("Invalid", "is-invalid");
      showDetail("Error", { error: error.message });
    }
  }

  function loadSnapshot(snapshot, label) {
    const errors = validateSnapshot(snapshot);
    if (errors.length) {
      setStatus("Invalid", "is-invalid");
      showDetail("Invalid Snapshot", { label: label, errors: errors });
      return;
    }
    state.snapshot = snapshot;
    state.selected = { kind: "snapshot", value: snapshot.summary || {} };
    setStatus("Loaded", "is-valid");
    render();
  }

  function validateSnapshot(snapshot) {
    const errors = [];
    if (!snapshot || typeof snapshot !== "object") errors.push("snapshot must be an object");
    if (!Array.isArray(snapshot.workflows)) errors.push("workflows must be an array");
    if (!Array.isArray(snapshot.runs)) errors.push("runs must be an array");
    if (!Array.isArray(snapshot.audit_events)) errors.push("audit_events must be an array");
    if (!Array.isArray(snapshot.connectors)) errors.push("connectors must be an array");
    if (!Array.isArray(snapshot.version_comparisons)) errors.push("version_comparisons must be an array");
    return errors;
  }

  function render() {
    renderSummary();
    renderTabs();
    renderTables();
    renderDetail();
  }

  function renderSummary() {
    const summary = state.snapshot && state.snapshot.summary ? state.snapshot.summary : {};
    const insights = state.snapshot && state.snapshot.operator_insights ? state.snapshot.operator_insights : {};
    els.metricWorkflows.textContent = String(summary.workflow_count || 0);
    els.metricRuns.textContent = String(summary.run_count || 0);
    els.metricAttention.textContent = String(totalAttention(insights.attention_counts || {}));
    els.metricAudit.textContent = String(summary.audit_event_count || 0);
    els.metricConnectors.textContent = String(summary.connector_count || 0);
  }

  function renderTabs() {
    els.tabs.forEach(function (tab) {
      tab.classList.toggle("is-active", tab.dataset.view === state.view);
    });
    els.panels.forEach(function (panel) {
      panel.hidden = panel.dataset.panel !== state.view;
    });
  }

  function renderTables() {
    const snapshot = state.snapshot || emptySnapshot();
    renderOperatorTables(snapshot.operator_insights || emptyOperatorInsights());
    renderTable(
      els.workflowRows,
      filterRows(snapshot.workflows),
      function (record) {
        return [
          linkCell(record.workflow_id || ""),
          textCell(record.version || ""),
          pillCell(record.status || ""),
          textCell(record.artifact || ""),
          textCell(formatDate(record.published_at || "")),
        ];
      },
      "workflow",
    );
    renderTable(
      els.runRows,
      filterRows(snapshot.runs),
      function (run) {
        return [
          linkCell(run.run_id || ""),
          textCell((run.workflow_id || "") + "@" + (run.workflow_version || "")),
          pillCell(run.status || ""),
          textCell(run.current_node || ""),
          textCell(String(run.event_count || 0)),
        ];
      },
      "run",
    );
    renderTable(
      els.auditRows,
      filterRows(snapshot.audit_events),
      function (event) {
        return [
          pillCell(event.type || ""),
          textCell((event.workflow_id || "") + "@" + (event.workflow_version || "")),
          textCell(event.run_id || ""),
          textCell(event.node_id || ""),
          textCell(formatDate(event.timestamp || "")),
        ];
      },
      "audit",
    );
    renderTable(
      els.versionRows,
      filterRows(snapshot.version_comparisons),
      function (comparison) {
        return [
          linkCell(comparison.workflow_id || ""),
          textCell((comparison.versions || []).join(" -> ")),
          pillCell(String(Boolean(comparison.checksum_changed))),
          textCell(formatDelta(comparison.node_count_delta)),
          textCell(formatDelta(comparison.edge_count_delta)),
        ];
      },
      "version comparison",
    );
    renderTable(
      els.connectorRows,
      filterRows(snapshot.connectors),
      function (connector) {
        return [
          linkCell(connector.name || connector.id || ""),
          textCell(connector.kind || ""),
          pillCell(connector.status || ""),
          textCell((connector.node_types || []).join(", ")),
          textCell(connector.description || ""),
        ];
      },
      "connector",
    );
  }

  function renderOperatorTables(insights) {
    renderTable(
      els.attentionRows,
      filterRows(insights.attention_items || []),
      function (item) {
        return [
          pillCell(item.severity || ""),
          textCell(item.kind || ""),
          textCell((item.workflow_id || "") + "@" + (item.workflow_version || "")),
          textCell(item.run_id || ""),
          textCell(item.message || ""),
        ];
      },
      "attention",
    );
    renderTable(
      els.recentEventRows,
      filterRows(insights.recent_events || []),
      function (event) {
        return [
          pillCell(event.type || ""),
          textCell((event.workflow_id || "") + "@" + (event.workflow_version || "")),
          textCell(event.run_id || ""),
          textCell(event.node_id || ""),
          textCell(formatDate(event.timestamp || "")),
        ];
      },
      "recent event",
    );
    renderTable(
      els.connectorEventRows,
      filterRows(connectorEventRows(insights.connector_event_counts || {})),
      function (event) {
        return [
          pillCell(event.type || ""),
          textCell(String(event.count || 0)),
          textCell(event.status || ""),
          textCell(event.kind || "connector"),
          textCell(event.scope || "control plane"),
        ];
      },
      "connector event",
    );
    renderTable(
      els.operatorVersionRows,
      filterRows(insights.version_changes || []),
      function (change) {
        return [
          linkCell(change.workflow_id || ""),
          textCell((change.versions || []).join(" -> ")),
          pillCell(String(Boolean(change.checksum_changed))),
          textCell(formatDelta(change.node_count_delta)),
          textCell(formatDelta(change.edge_count_delta)),
        ];
      },
      "version change",
    );
  }

  function renderTable(tbody, rows, cellsForRow, kind) {
    tbody.replaceChildren();
    if (!rows.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 5;
      td.textContent = "No " + kind + " records";
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }
    rows.forEach(function (row) {
      const tr = document.createElement("tr");
      if (state.selected && state.selected.value === row) {
        tr.classList.add("is-selected");
      }
      tr.addEventListener("click", function () {
        state.selected = { kind: kind, value: row };
        renderTables();
        renderDetail();
      });
      cellsForRow(row).forEach(function (cell) {
        tr.appendChild(cell);
      });
      tbody.appendChild(tr);
    });
  }

  function textCell(value) {
    const td = document.createElement("td");
    td.textContent = value;
    return td;
  }

  function linkCell(value) {
    const td = document.createElement("td");
    const span = document.createElement("span");
    span.className = "mono";
    span.textContent = value;
    td.appendChild(span);
    return td;
  }

  function pillCell(value) {
    const td = document.createElement("td");
    const span = document.createElement("span");
    span.className = "pill " + String(value).toLowerCase().replace(/[^a-z0-9_-]/g, "_");
    span.textContent = value;
    td.appendChild(span);
    return td;
  }

  function renderDetail() {
    const selected = state.selected || { kind: "snapshot", value: {} };
    const value = selected.value || {};
    showDetail(titleForSelection(selected), value);
  }

  function showDetail(title, value) {
    els.detailTitle.textContent = title;
    els.detailJson.textContent = JSON.stringify(value, null, 2);
    renderStatusGrid(value);
  }

  function renderStatusGrid(value) {
    els.statusGrid.replaceChildren();
    const pairs = detailPairs(value);
    pairs.forEach(function (pair) {
      const item = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = pair[0];
      dd.textContent = pair[1];
      item.appendChild(dt);
      item.appendChild(dd);
      els.statusGrid.appendChild(item);
    });
  }

  function detailPairs(value) {
    if (!value || typeof value !== "object") return [["Type", "Empty"]];
    if (value.workflow_id && value.version) {
      return [["Workflow", value.workflow_id], ["Version", value.version], ["Status", value.status || ""], ["Checksum", shorten(value.checksum || "")]];
    }
    if (value.kind && value.severity) {
      return [["Kind", value.kind || ""], ["Severity", value.severity || ""], ["Workflow", value.workflow_id || ""], ["Run", value.run_id || ""]];
    }
    if (value.run_id) {
      return [["Run", value.run_id], ["Workflow", value.workflow_id || ""], ["Status", value.status || ""], ["Events", String(value.event_count || 0)]];
    }
    if (value.type) {
      return [["Type", value.type], ["Workflow", value.workflow_id || ""], ["Run", value.run_id || ""], ["Time", formatDate(value.timestamp || "")]];
    }
    if (value.id && value.kind) {
      return [["Connector", value.name || value.id], ["ID", value.id || ""], ["Status", value.status || ""], ["Node Types", (value.node_types || []).join(", ")]];
    }
    if (value.versions) {
      return [["Workflow", value.workflow_id || ""], ["Versions", value.versions.join(" -> ")], ["Checksum", String(Boolean(value.checksum_changed))], ["Node Delta", formatDelta(value.node_count_delta)]];
    }
    return [["Workflows", String(value.workflow_count || 0)], ["Runs", String(value.run_count || 0)], ["Audit", String(value.audit_event_count || 0)], ["Connectors", String(value.connector_count || 0)]];
  }

  function titleForSelection(selected) {
    const value = selected.value || {};
    if (selected.kind === "workflow") return value.workflow_id + "@" + value.version;
    if (selected.kind === "run") return value.run_id || "Run";
    if (selected.kind === "audit") return value.type || "Audit";
    if (selected.kind === "connector") return value.name || value.id || "Connector";
    if (selected.kind === "version comparison") return value.workflow_id || "Comparison";
    if (selected.kind === "attention") return value.kind || "Attention";
    if (selected.kind === "recent event") return value.type || "Recent Event";
    if (selected.kind === "connector event") return value.type || "Connector Event";
    if (selected.kind === "version change") return value.workflow_id || "Version Change";
    return "Snapshot";
  }

  function filterRows(rows) {
    if (!state.filter) return rows;
    return rows.filter(function (row) {
      return JSON.stringify(row).toLowerCase().indexOf(state.filter) !== -1;
    });
  }

  function setView(view) {
    state.view = view;
    renderTabs();
  }

  function setStatus(text, className) {
    els.status.textContent = text;
    els.status.className = "status-pill" + (className ? " " + className : "");
  }

  function emptySnapshot() {
    return {
      workflows: [],
      runs: [],
      audit_events: [],
      connectors: [],
      version_comparisons: [],
      operator_insights: emptyOperatorInsights(),
    };
  }

  function emptyOperatorInsights() {
    return {
      attention_counts: {},
      attention_items: [],
      recent_events: [],
      connector_event_counts: {},
      version_changes: [],
    };
  }

  function totalAttention(counts) {
    return Object.keys(counts).reduce(function (total, key) {
      return total + Number(counts[key] || 0);
    }, 0);
  }

  function connectorEventRows(counts) {
    return Object.keys(counts).sort().map(function (key) {
      return {
        type: key,
        count: counts[key],
        status: key.replace("connector_", ""),
        kind: "connector",
        scope: "audit events",
      };
    });
  }

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toISOString().replace(".000Z", "Z");
  }

  function formatDelta(value) {
    const number = Number(value || 0);
    return (number > 0 ? "+" : "") + String(number);
  }

  function shorten(value) {
    return value.length > 12 ? value.slice(0, 12) : value;
  }
})();
