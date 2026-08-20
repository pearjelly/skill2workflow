(function () {
  const EXAMPLE_URL = "../examples/control-plane-snapshot.json";
  const LIVE_SNAPSHOT_URL = "/api/v1/control-snapshot";
  const SERVICE_PROBE_URL = "/api/v1/service-probe";
  const SUPPORT_BUNDLE_URL = "/api/v1/support-bundle";
  const LIVE_RESUME_PREFIX = "/api/v1/runs/";
  const LIVE_RUN_DETAIL_PREFIX = "/api/v1/runs/";
  const LIVE_RUN_PAGE_URL = "/api/v1/run-page";
  const LIVE_AUDIT_PAGE_URL = "/api/v1/audit-page";
  const LIVE_SCHEDULE_LIST_URL = "/api/v1/recurring-schedules";
  const LIVE_OPERATIONAL_READINESS_URL = "/api/v1/operational-readiness";
  const LIVE_WORKFLOW_INVENTORY_URL = "/api/v1/workflows";
  const LIVE_WORKFLOW_EXPLANATION_PREFIX = "/api/v1/workflow-explanations/";
  const LIVE_WORKFLOW_PREFLIGHT_PREFIX = "/api/v1/workflow-preflights/";
  const RUN_DETAIL_SCHEMA = "skill2workflow-run-detail-0.1.0";
  const RUN_PAGE_SCHEMA = "skill2workflow-run-list-0.2.0";
  const AUDIT_PAGE_SCHEMA = "skill2workflow-audit-event-list-0.1.0";
  const SCHEDULE_LIST_SCHEMA = "skill2workflow-recurring-schedule-list-0.1.0";
  const OPERATIONAL_READINESS_SCHEMA = "skill2workflow-operational-readiness-0.1.0";
  const WORKFLOW_INVENTORY_SCHEMA = "skill2workflow-workflow-inventory-0.1.0";
  const WORKFLOW_EXPLANATION_SCHEMA = "skill2workflow-workflow-explanation-0.1.0";
  const WORKFLOW_PREFLIGHT_SCHEMA = "skill2workflow-workflow-preflight-0.1.0";
  const LIVE_RUN_ROWS_MAX = 500;
  const LIVE_AUDIT_ROWS_MAX = 500;
  const SERVICE_PROBE_SCHEMA = "skill2workflow-service-probe-0.1.0";
  const AUTO_REFRESH_INTERVAL_MS = 10000;
  const state = {
    snapshot: null,
    view: "operator",
    selected: null,
    filter: "",
    sourceLabel: "",
    liveModeConfigured: false,
    liveRefreshEnabled: false,
    liveRefreshTimer: null,
    liveLoading: false,
    humanGateLoading: false,
    runCancelLoading: false,
    liveRunDetail: null,
    liveRunDetailId: "",
    liveRunDetailLoading: false,
    liveRunDetailError: false,
    liveRunRows: null,
    liveRunPageCursor: "",
    liveRunPageHasMore: false,
    liveRunPageLoading: false,
    liveAuditRows: null,
    liveAuditPageCursor: "",
    liveAuditPageHasMore: false,
    liveAuditPageLoading: false,
    liveSchedules: null,
    liveSchedulesLoading: false,
    liveReadiness: null,
    liveReadinessLoading: false,
    liveWorkflowInventory: null,
    liveWorkflowInventoryLoading: false,
    liveWorkflowExplanation: null,
    liveWorkflowExplanationKey: "",
    liveWorkflowExplanationLoading: false,
    liveWorkflowExplanationError: false,
    liveWorkflowPreflight: null,
    liveWorkflowPreflightKey: "",
    liveWorkflowPreflightLoading: false,
    liveWorkflowPreflightError: false,
    lastLiveLoadedAt: "",
    liveRefreshError: false,
  };

  const els = {};

  window.addEventListener("DOMContentLoaded", init);

  function init() {
    cacheElements();
    bindEvents();
    loadServiceProbe();
    loadExample();
  }

  function cacheElements() {
    els.loadExample = document.getElementById("load-example");
    els.loadLive = document.getElementById("load-live");
    els.toggleRefresh = document.getElementById("toggle-refresh");
    els.downloadBundle = document.getElementById("download-bundle");
    els.loadOlderRuns = document.getElementById("load-older-runs");
    els.loadOlderAudit = document.getElementById("load-older-audit");
    els.loadLiveSchedules = document.getElementById("load-live-schedules");
    els.loadLiveReadiness = document.getElementById("load-live-readiness");
    els.loadLiveWorkflows = document.getElementById("load-live-workflows");
    els.snapshotFile = document.getElementById("snapshot-file");
    els.filterInput = document.getElementById("filter-input");
    els.status = document.getElementById("status-pill");
    els.snapshotScope = document.getElementById("snapshot-scope");
    els.snapshotScopeTitle = document.getElementById("snapshot-scope-title");
    els.snapshotScopeDetail = document.getElementById("snapshot-scope-detail");
    els.serviceStatus = document.getElementById("service-status");
    els.runPageStatus = document.getElementById("run-page-status");
    els.auditPageStatus = document.getElementById("audit-page-status");
    els.schedulePageStatus = document.getElementById("schedule-page-status");
    els.readinessPageStatus = document.getElementById("readiness-page-status");
    els.workflowPageStatus = document.getElementById("workflow-page-status");
    els.workflowExplanationActions = document.getElementById("workflow-explanation-actions");
    els.workflowExplanationStatus = document.getElementById("workflow-explanation-status");
    els.loadWorkflowExplanation = document.getElementById("load-workflow-explanation");
    els.workflowPreflightStatus = document.getElementById("workflow-preflight-status");
    els.loadWorkflowPreflight = document.getElementById("load-workflow-preflight");
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
    els.nodeOverlayRows = document.getElementById("node-overlay-rows");
    els.auditRows = document.getElementById("audit-rows");
    els.connectorRows = document.getElementById("connector-rows");
    els.scheduleRows = document.getElementById("schedule-rows");
    els.readinessRows = document.getElementById("readiness-rows");
    els.liveWorkflowRows = document.getElementById("live-workflow-rows");
    els.versionRows = document.getElementById("version-rows");
    els.detailTitle = document.getElementById("detail-title");
    els.statusGrid = document.getElementById("status-grid");
    els.humanGateActions = document.getElementById("human-gate-actions");
    els.humanGateStatus = document.getElementById("human-gate-status");
    els.approveRun = document.getElementById("approve-run");
    els.rejectRun = document.getElementById("reject-run");
    els.runCancelActions = document.getElementById("run-cancel-actions");
    els.runCancelStatus = document.getElementById("run-cancel-status");
    els.cancelRun = document.getElementById("cancel-run");
    els.runDetailStatus = document.getElementById("run-detail-status");
    els.detailJson = document.getElementById("detail-json");
  }

  function bindEvents() {
    els.loadExample.addEventListener("click", loadExample);
    els.loadLive.addEventListener("click", loadLiveSnapshot);
    els.toggleRefresh.addEventListener("click", toggleAutoRefresh);
    els.downloadBundle.addEventListener("click", downloadSupportBundle);
    els.loadOlderRuns.addEventListener("click", loadOlderRuns);
    els.loadOlderAudit.addEventListener("click", loadOlderAudit);
    els.loadLiveSchedules.addEventListener("click", loadLiveSchedules);
    els.loadLiveReadiness.addEventListener("click", loadLiveReadiness);
    els.loadLiveWorkflows.addEventListener("click", loadLiveWorkflows);
    els.loadWorkflowExplanation.addEventListener("click", loadLiveWorkflowExplanation);
    els.loadWorkflowPreflight.addEventListener("click", loadLiveWorkflowPreflight);
    els.approveRun.addEventListener("click", function () {
      decideSelectedRun(true);
    });
    els.rejectRun.addEventListener("click", function () {
      decideSelectedRun(false);
    });
    els.cancelRun.addEventListener("click", cancelSelectedRun);
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
    document.addEventListener("visibilitychange", function () {
      if (state.liveRefreshEnabled && document.visibilityState === "visible") {
        loadLiveSnapshot({ background: true });
      }
    });
  }

  async function loadExample() {
    stopAutoRefresh();
    setStatus("Loading", "");
    try {
      const response = await fetch(EXAMPLE_URL, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("snapshot unavailable");
      }
      loadSnapshot(await response.json(), "Example Snapshot");
    } catch (error) {
      rejectSnapshot("Example Snapshot", { error: error.message });
    }
  }

  async function loadLiveSnapshot(options) {
    const background = Boolean(options && options.background);
    if (state.liveLoading) {
      return;
    }
    state.liveLoading = true;
    setStatus(background ? "Refreshing" : "Loading", "");
    loadServiceProbe();
    try {
      const response = await fetch(LIVE_SNAPSHOT_URL, { cache: "no-store" });
      if (response.status === 404) {
        stopAutoRefresh();
      }
      if (!response.ok) {
        throw new Error("live snapshot unavailable");
      }
      loadSnapshot(await response.json(), "Live Service Snapshot");
    } catch (error) {
      if (background && state.snapshot) {
        state.liveRefreshError = true;
        setStatus("Unavailable", "is-invalid");
        renderSnapshotScope();
      } else {
        rejectSnapshot("Live Service Snapshot", { error: "live snapshot unavailable" });
      }
    } finally {
      state.liveLoading = false;
    }
  }

  function toggleAutoRefresh() {
    if (!state.liveModeConfigured) {
      return;
    }
    if (state.liveRefreshEnabled) {
      stopAutoRefresh();
      return;
    }
    state.liveRefreshEnabled = true;
    els.toggleRefresh.setAttribute("aria-pressed", "true");
    els.toggleRefresh.textContent = "Auto-refresh: On (10s)";
    state.liveRefreshTimer = window.setInterval(function () {
      if (document.visibilityState === "visible") {
        loadLiveSnapshot({ background: true });
      }
    }, AUTO_REFRESH_INTERVAL_MS);
    loadLiveSnapshot({ background: true });
  }

  function stopAutoRefresh() {
    if (state.liveRefreshTimer !== null) {
      window.clearInterval(state.liveRefreshTimer);
      state.liveRefreshTimer = null;
    }
    state.liveRefreshEnabled = false;
    if (els.toggleRefresh) {
      els.toggleRefresh.setAttribute("aria-pressed", "false");
      els.toggleRefresh.textContent = "Auto-refresh: Off";
    }
  }

  async function downloadSupportBundle() {
    if (!state.liveModeConfigured) {
      return;
    }
    setStatus("Downloading", "");
    try {
      const response = await fetch(SUPPORT_BUNDLE_URL, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("support bundle unavailable");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "skill2workflow-support-bundle.json";
      link.click();
      window.setTimeout(function () {
        URL.revokeObjectURL(url);
      }, 0);
      setStatus("Downloaded", "is-valid");
    } catch (error) {
      setStatus("Unavailable", "is-invalid");
    }
  }

  async function loadOlderRuns() {
    if (!isLiveSnapshot() || state.liveRunPageLoading || !state.liveRunPageHasMore) {
      return;
    }
    state.liveRunPageLoading = true;
    updateRunPageControls();
    setRunPageStatus("Loading older runs…", "");
    try {
      const url = state.liveRunPageCursor
        ? LIVE_RUN_PAGE_URL + "?cursor=" + encodeURIComponent(state.liveRunPageCursor)
        : LIVE_RUN_PAGE_URL;
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("run page unavailable");
      }
      const page = await response.json();
      if (!validateLiveRunPage(page)) {
        throw new Error("run page unavailable");
      }
      state.liveRunRows = mergeLiveRunRows(state.liveRunRows || state.snapshot.runs, page.runs);
      state.liveRunPageCursor = page.window.next_cursor || "";
      state.liveRunPageHasMore = page.window.has_more;
      renderTables();
      setRunPageStatus(
        String(state.liveRunRows.length) +
          " live runs loaded" +
          (state.liveRunPageHasMore ? "; more available." : "."),
        "is-valid",
      );
    } catch (error) {
      setRunPageStatus("Older runs unavailable; current rows are unchanged.", "is-invalid");
    } finally {
      state.liveRunPageLoading = false;
      updateRunPageControls();
    }
  }

  async function loadOlderAudit() {
    if (
      !isLiveSnapshot() ||
      state.liveAuditPageLoading ||
      !state.liveAuditPageHasMore
    ) {
      return;
    }
    state.liveAuditPageLoading = true;
    updateAuditPageControls();
    setAuditPageStatus("Loading older audit…", "");
    try {
      const url = state.liveAuditPageCursor
        ? LIVE_AUDIT_PAGE_URL + "?cursor=" + encodeURIComponent(state.liveAuditPageCursor)
        : LIVE_AUDIT_PAGE_URL;
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("audit page unavailable");
      }
      const page = await response.json();
      if (!validateLiveAuditPage(page)) {
        throw new Error("audit page unavailable");
      }
      state.liveAuditRows = mergeLiveAuditRows(
        state.liveAuditRows || (state.snapshot.audit_events || []),
        page.events,
      );
      state.liveAuditPageCursor = page.window.next_cursor || "";
      state.liveAuditPageHasMore = Boolean(
        page.window.truncated && page.window.next_cursor,
      );
      renderTables();
      setAuditPageStatus(
        state.liveAuditPageHasMore
          ? "Older audit loaded; more available."
          : "Older audit loaded.",
        "is-valid",
      );
      setStatus("Loaded", "is-valid");
    } catch (error) {
      setAuditPageStatus(
        "Older audit unavailable; current rows are unchanged.",
        "is-invalid",
      );
    } finally {
      state.liveAuditPageLoading = false;
      updateAuditPageControls();
    }
  }

  async function loadLiveSchedules() {
    if (!isLiveSnapshot() || !state.liveModeConfigured || state.liveSchedulesLoading) {
      return;
    }
    state.liveSchedulesLoading = true;
    updateLiveScheduleControls();
    setSchedulePageStatus("Loading live schedules…", "");
    try {
      const response = await fetch(LIVE_SCHEDULE_LIST_URL, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("schedule list unavailable");
      }
      const page = await response.json();
      if (!validateLiveScheduleList(page)) {
        throw new Error("schedule list unavailable");
      }
      state.liveSchedules = page.schedules;
      renderTables();
      setSchedulePageStatus(
        "Loaded " + page.window.returned + " of " + page.window.total +
          " schedules" + (page.window.truncated ? " (truncated)." : "."),
        "is-valid",
      );
      setStatus("Loaded", "is-valid");
    } catch (error) {
      setSchedulePageStatus(
        "Live schedules unavailable; current rows are unchanged.",
        "is-invalid",
      );
    } finally {
      state.liveSchedulesLoading = false;
      updateLiveScheduleControls();
    }
  }

  async function loadLiveReadiness() {
    if (!isLiveSnapshot() || !state.liveModeConfigured || state.liveReadinessLoading) {
      return;
    }
    state.liveReadinessLoading = true;
    updateLiveReadinessControls();
    setReadinessPageStatus("Loading live readiness…", "");
    try {
      const response = await fetch(LIVE_OPERATIONAL_READINESS_URL, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("operational readiness unavailable");
      }
      const report = await response.json();
      if (!validateOperationalReadiness(report)) {
        throw new Error("operational readiness unavailable");
      }
      state.liveReadiness = report;
      renderTables();
      const blocking = report.blocking_reasons.length;
      setReadinessPageStatus(
        report.status === "ready"
          ? "Ready: all production checks passed."
          : "Attention: " + blocking + " blocking " + (blocking === 1 ? "reason." : "reasons."),
        report.status === "ready" ? "is-valid" : "is-invalid",
      );
      setStatus(report.status === "ready" ? "Ready" : "Attention", report.status === "ready" ? "is-valid" : "is-invalid");
    } catch (error) {
      setReadinessPageStatus(
        "Live readiness unavailable; current rows are unchanged.",
        "is-invalid",
      );
    } finally {
      state.liveReadinessLoading = false;
      updateLiveReadinessControls();
    }
  }

  async function loadLiveWorkflows() {
    if (!isLiveSnapshot() || !state.liveModeConfigured || state.liveWorkflowInventoryLoading) {
      return;
    }
    state.liveWorkflowInventoryLoading = true;
    updateLiveWorkflowControls();
    setWorkflowPageStatus("Loading live workflows…", "");
    try {
      const response = await fetch(LIVE_WORKFLOW_INVENTORY_URL, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("workflow inventory unavailable");
      }
      const inventory = await response.json();
      if (!validateWorkflowInventory(inventory)) {
        throw new Error("workflow inventory unavailable");
      }
      state.liveWorkflowInventory = inventory;
      renderTables();
      setWorkflowPageStatus(
        "Loaded " + inventory.window.returned + " of " + inventory.window.total +
          " workflow versions" + (inventory.window.truncated ? " (truncated)." : "."),
        "is-valid",
      );
      setStatus("Loaded", "is-valid");
    } catch (error) {
      setWorkflowPageStatus(
        "Live workflows unavailable; current rows are unchanged.",
        "is-invalid",
      );
    } finally {
      state.liveWorkflowInventoryLoading = false;
      updateLiveWorkflowControls();
    }
  }

  async function loadLiveWorkflowExplanation() {
    const workflow = selectedLiveWorkflow();
    if (!workflow || state.liveWorkflowExplanationLoading) {
      return;
    }
    const key = workflow.workflow_id + "@" + workflow.version;
    state.liveWorkflowExplanationLoading = true;
    state.liveWorkflowExplanationError = false;
    updateWorkflowExplanationControls();
    setWorkflowExplanationStatus("Loading bounded workflow review…", "");
    try {
      const url =
        LIVE_WORKFLOW_EXPLANATION_PREFIX +
        encodeURIComponent(workflow.workflow_id) +
        "/" +
        encodeURIComponent(workflow.version);
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("workflow explanation unavailable");
      }
      const explanation = await response.json();
      if (!validateWorkflowExplanation(explanation, workflow)) {
        throw new Error("workflow explanation unavailable");
      }
      state.liveWorkflowExplanation = explanation;
      state.liveWorkflowExplanationKey = key;
      renderDetail();
      setWorkflowExplanationStatus(
        "Read-only review loaded; no connector or credential was invoked.",
        "is-valid",
      );
      setStatus("Reviewed", "is-valid");
    } catch (error) {
      state.liveWorkflowExplanation = null;
      state.liveWorkflowExplanationKey = key;
      state.liveWorkflowExplanationError = true;
      renderDetail();
      setWorkflowExplanationStatus(
        "Workflow review unavailable; metadata remains visible.",
        "is-invalid",
      );
    } finally {
      state.liveWorkflowExplanationLoading = false;
      updateWorkflowExplanationControls();
    }
  }

  async function loadLiveWorkflowPreflight() {
    const workflow = selectedLiveWorkflow();
    if (!workflow || state.liveWorkflowPreflightLoading) {
      return;
    }
    const key = workflow.workflow_id + "@" + workflow.version;
    state.liveWorkflowPreflightLoading = true;
    state.liveWorkflowPreflightError = false;
    updateWorkflowPreflightControls();
    setWorkflowPreflightStatus("Checking the empty trigger shape…", "");
    try {
      const url =
        LIVE_WORKFLOW_PREFLIGHT_PREFIX +
        encodeURIComponent(workflow.workflow_id) +
        "/" +
        encodeURIComponent(workflow.version);
      const response = await fetch(url, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!response.ok) {
        throw new Error("workflow preflight unavailable");
      }
      const report = await response.json();
      if (!validateWorkflowPreflight(report, workflow)) {
        throw new Error("workflow preflight unavailable");
      }
      state.liveWorkflowPreflight = report;
      state.liveWorkflowPreflightKey = key;
      renderDetail();
      setWorkflowPreflightStatus(
        report.ready
          ? "Empty trigger is ready; no connector or credential was invoked."
          : "Empty trigger is blocked; review missing input or mapping requirements.",
        report.ready ? "is-valid" : "is-invalid",
      );
      setStatus(report.ready ? "Preflight Ready" : "Preflight Blocked", report.ready ? "is-valid" : "is-invalid");
    } catch (error) {
      state.liveWorkflowPreflight = null;
      state.liveWorkflowPreflightKey = key;
      state.liveWorkflowPreflightError = true;
      renderDetail();
      setWorkflowPreflightStatus(
        "Preflight unavailable; metadata remains visible.",
        "is-invalid",
      );
    } finally {
      state.liveWorkflowPreflightLoading = false;
      updateWorkflowPreflightControls();
    }
  }

  function selectedLiveWorkflow() {
    if (
      !isLiveSnapshot() ||
      !state.selected ||
      state.selected.kind !== "live workflow" ||
      !state.selected.value
    ) {
      return null;
    }
    const workflow = state.selected.value;
    if (
      !isSafeWorkflowRef(workflow.workflow_id) ||
      !isSafeWorkflowRef(workflow.version)
    ) {
      return null;
    }
    return workflow;
  }

  function mergeLiveRunRows(existing, additions) {
    const rows = [];
    const seen = Object.create(null);
    (existing || []).concat(additions || []).forEach(function (run) {
      if (!run || typeof run.run_id !== "string" || seen[run.run_id]) {
        return;
      }
      seen[run.run_id] = true;
      rows.push(run);
    });
    return rows.slice(0, LIVE_RUN_ROWS_MAX);
  }

  function mergeLiveAuditRows(existing, additions) {
    const rows = Object.create(null);
    (existing || []).concat(additions || []).forEach(function (event) {
      if (!event || !Number.isInteger(event.sequence) || event.sequence < 1) {
        return;
      }
      rows[String(event.sequence)] = event;
    });
    return Object.keys(rows)
      .map(function (sequence) {
        return rows[sequence];
      })
      .sort(function (left, right) {
        return left.sequence - right.sequence;
      })
      .slice(-LIVE_AUDIT_ROWS_MAX);
  }

  function validateLiveRunPage(page) {
    const statuses = [
      "created", "running", "waiting", "completed", "failed", "cancelled", "interrupted", "other",
    ];
    if (
      !page ||
      typeof page !== "object" ||
      page.schema_version !== RUN_PAGE_SCHEMA ||
      Object.keys(page).sort().join(",") !== "filters,runs,schema_version,summary,window" ||
      !page.summary ||
      typeof page.summary !== "object" ||
      !page.filters ||
      typeof page.filters !== "object" ||
      !Array.isArray(page.runs) ||
      page.runs.length > 100 ||
      !page.window ||
      typeof page.window !== "object" ||
      page.window.max_items !== 100 ||
      Object.keys(page.window).sort().join(",") !==
        "has_more,max_items,next_cursor,returned,total" ||
      !Number.isInteger(page.window.total) ||
      page.window.total < 0 ||
      page.window.returned !== page.runs.length ||
      page.window.returned > page.window.total ||
      typeof page.window.has_more !== "boolean" ||
      page.window.has_more !== (page.window.returned < page.window.total) ||
      (page.window.has_more && !isSafeCursor(page.window.next_cursor)) ||
      (!page.window.has_more && page.window.next_cursor !== null)
    ) {
      return false;
    }
    if (
      Object.keys(page.summary).sort().join(",") !== "status_counts,total" ||
      Object.keys(page.filters).sort().join(",") !== "status,workflow_id" ||
      page.filters.status !== "" ||
      page.filters.workflow_id !== "" ||
      !Number.isInteger(page.summary.total) ||
      page.summary.total < 0 ||
      !page.summary.status_counts ||
      typeof page.summary.status_counts !== "object" ||
      Object.keys(page.summary.status_counts).sort().join(",") !==
        "cancelled,completed,created,failed,interrupted,other,running,waiting" ||
      Object.values(page.summary.status_counts).some(function (value) {
        return !Number.isInteger(value) || value < 0;
      }) ||
      Object.values(page.summary.status_counts).reduce(function (total, value) {
        return total + value;
      }, 0) !== page.summary.total ||
      page.window.total !== page.summary.total
    ) {
      return false;
    }
    return page.runs.every(function (run) {
      return (
        run &&
        typeof run === "object" &&
        isSafeRunId(run.run_id) &&
        typeof run.workflow_id === "string" &&
        typeof run.workflow_version === "string" &&
        statuses.indexOf(run.status) !== -1 &&
        typeof run.current_node === "string" &&
        Number.isInteger(run.event_count) &&
        run.event_count >= 0 &&
        Number.isInteger(run.node_result_count) &&
        run.node_result_count >= 0
      );
    });
  }

  function validateLiveAuditPage(page) {
    const eventFields = [
      "approved", "attempt", "backoff_ms", "connector_id", "connector_kind",
      "connector_status", "has_error", "max_attempts", "next_attempt", "node_id",
      "run_id", "sequence", "timestamp", "type", "workflow_id", "workflow_version",
    ];
    if (
      !page ||
      typeof page !== "object" ||
      page.schema_version !== AUDIT_PAGE_SCHEMA ||
      Object.keys(page).sort().join(",") !== "events,filters,schema_version,window" ||
      !page.filters ||
      typeof page.filters !== "object" ||
      Object.keys(page.filters).sort().join(",") !==
        "event_type,run_id,workflow_id,workflow_version" ||
      Object.values(page.filters).some(function (value) {
        return typeof value !== "string" || value;
      }) ||
      !Array.isArray(page.events) ||
      page.events.length > 100 ||
      !page.window ||
      typeof page.window !== "object" ||
      page.window.max_items !== 100 ||
      Object.keys(page.window).sort().join(",") !==
        "max_items,next_cursor,returned,total,truncated" ||
      !Number.isInteger(page.window.total) ||
      page.window.total < 0 ||
      !Number.isInteger(page.window.returned) ||
      page.window.returned !== page.events.length ||
      page.window.returned > page.window.total ||
      typeof page.window.truncated !== "boolean" ||
      typeof page.window.next_cursor !== "string" ||
      !isSafeCursor(page.window.next_cursor) ||
      page.window.truncated !== Boolean(page.window.next_cursor)
    ) {
      return false;
    }
    return page.events.every(function (event) {
      return (
        event &&
        typeof event === "object" &&
        Object.keys(event).sort().join(",") === eventFields.join(",") &&
        Number.isInteger(event.sequence) &&
        event.sequence >= 1 &&
        typeof event.type === "string" &&
        event.type.length > 0 &&
        event.type.length <= 64 &&
        ["run_id", "workflow_id", "workflow_version", "node_id", "connector_id",
          "connector_kind", "connector_status"].every(function (field) {
          return typeof event[field] === "string" && event[field].length <= 128;
        }) &&
        typeof event.timestamp === "string" &&
        event.timestamp.length <= 256 &&
        ["attempt", "max_attempts", "next_attempt", "backoff_ms"].every(function (field) {
          return Number.isInteger(event[field]) && event[field] >= 0;
        }) &&
        typeof event.approved === "boolean" &&
        typeof event.has_error === "boolean"
      );
    });
  }

  function validateLiveScheduleList(page) {
    const scheduleFields = [
      "enabled", "interval_seconds", "last_run_id", "last_scheduled_for",
      "last_trigger_id", "missed_run_policy", "next_run_at", "schedule_id",
      "starts_at", "status", "workflow_id", "workflow_version",
    ];
    if (
      !page ||
      typeof page !== "object" ||
      page.schema_version !== SCHEDULE_LIST_SCHEMA ||
      Object.keys(page).sort().join(",") !== "schedules,schema_version,summary,window" ||
      !page.summary ||
      typeof page.summary !== "object" ||
      Object.keys(page.summary).sort().join(",") !== "status_counts,total" ||
      !Number.isInteger(page.summary.total) ||
      page.summary.total < 0 ||
      !page.summary.status_counts ||
      typeof page.summary.status_counts !== "object" ||
      Object.keys(page.summary.status_counts).sort().join(",") !== "active,disabled,other" ||
      Object.values(page.summary.status_counts).some(function (value) {
        return !Number.isInteger(value) || value < 0;
      }) ||
      Object.values(page.summary.status_counts).reduce(function (total, value) {
        return total + value;
      }, 0) !== page.summary.total ||
      !Array.isArray(page.schedules) ||
      page.schedules.length > 100 ||
      !page.window ||
      typeof page.window !== "object" ||
      Object.keys(page.window).sort().join(",") !==
        "max_items,returned,total,truncated" ||
      page.window.max_items !== 100 ||
      !Number.isInteger(page.window.total) ||
      page.window.total < 0 ||
      !Number.isInteger(page.window.returned) ||
      page.window.returned !== page.schedules.length ||
      page.window.returned > page.window.total ||
      typeof page.window.truncated !== "boolean" ||
      page.window.truncated !== (page.window.returned < page.window.total) ||
      page.window.total !== page.summary.total
    ) {
      return false;
    }
    return page.schedules.every(function (schedule) {
      return (
        schedule &&
        typeof schedule === "object" &&
        Object.keys(schedule).sort().join(",") === scheduleFields.join(",") &&
        typeof schedule.schedule_id === "string" &&
        schedule.schedule_id.length > 0 &&
        schedule.schedule_id.length <= 128 &&
        typeof schedule.workflow_id === "string" &&
        schedule.workflow_id.length <= 128 &&
        typeof schedule.workflow_version === "string" &&
        schedule.workflow_version.length <= 128 &&
        ["active", "disabled", "other"].indexOf(schedule.status) !== -1 &&
        typeof schedule.enabled === "boolean" &&
        ["starts_at", "next_run_at", "last_scheduled_for"].every(function (field) {
          return typeof schedule[field] === "string" && schedule[field].length <= 256;
        }) &&
        ["last_run_id", "last_trigger_id"].every(function (field) {
          return typeof schedule[field] === "string" && schedule[field].length <= 128;
        }) &&
        ["latest", "skip"].indexOf(schedule.missed_run_policy) !== -1 &&
        Number.isInteger(schedule.interval_seconds) &&
        schedule.interval_seconds >= 1
      );
    });
  }

  function validateOperationalReadiness(report) {
    const reasons = [
      "service_not_ready", "state_layout_not_current", "workflow_artifacts_attention",
      "workflow_artifacts_unavailable", "audit_integrity_not_valid",
      "audit_integrity_unavailable", "offline_backup_unavailable",
    ];
    if (
      !report ||
      typeof report !== "object" ||
      report.schema_version !== OPERATIONAL_READINESS_SCHEMA ||
      Object.keys(report).sort().join(",") !==
        "blocking_reasons,checks,operator_notes,schema_version,status,service" ||
      ["ready", "attention"].indexOf(report.status) === -1 ||
      !report.service ||
      typeof report.service !== "object" ||
      Object.keys(report.service).sort().join(",") !==
        "ready,scheduler_lease_owned,state_layout_version,status,storage" ||
      ["starting", "ready", "draining", "stopped"].indexOf(report.service.status) === -1 ||
      typeof report.service.ready !== "boolean" ||
      report.service.storage !== "sqlite" ||
      report.service.state_layout_version !== "skill2workflow-sqlite-layout-0.1.0" ||
      typeof report.service.scheduler_lease_owned !== "boolean" ||
      !report.checks ||
      typeof report.checks !== "object" ||
      Object.keys(report.checks).sort().join(",") !==
        "audit_integrity,offline_backup,workflow_artifacts" ||
      !report.checks.workflow_artifacts ||
      typeof report.checks.workflow_artifacts !== "object" ||
      Object.keys(report.checks.workflow_artifacts).sort().join(",") !== "issue_count,status" ||
      ["clean", "attention", "unavailable"].indexOf(report.checks.workflow_artifacts.status) === -1 ||
      (report.checks.workflow_artifacts.status === "unavailable"
        ? report.checks.workflow_artifacts.issue_count !== null
        : !Number.isInteger(report.checks.workflow_artifacts.issue_count) ||
          report.checks.workflow_artifacts.issue_count < 0) ||
      !report.checks.audit_integrity ||
      typeof report.checks.audit_integrity !== "object" ||
      Object.keys(report.checks.audit_integrity).sort().join(",") !== "status" ||
      ["valid", "invalid", "legacy_unsealed", "unavailable"].indexOf(report.checks.audit_integrity.status) === -1 ||
      !report.checks.offline_backup ||
      typeof report.checks.offline_backup !== "object" ||
      Object.keys(report.checks.offline_backup).sort().join(",") !==
        "active_scheduler_lease,status" ||
      ["ready", "blocked", "unavailable"].indexOf(report.checks.offline_backup.status) === -1 ||
      (report.checks.offline_backup.status === "unavailable"
        ? report.checks.offline_backup.active_scheduler_lease !== null
        : typeof report.checks.offline_backup.active_scheduler_lease !== "boolean") ||
      !Array.isArray(report.blocking_reasons) ||
      report.blocking_reasons.length > reasons.length ||
      report.blocking_reasons.some(function (reason) {
        return reasons.indexOf(reason) === -1;
      }) ||
      new Set(report.blocking_reasons).size !== report.blocking_reasons.length ||
      !Array.isArray(report.operator_notes) ||
      report.operator_notes.length > 1 ||
      report.operator_notes.some(function (note) {
        return note !== "offline_backup_requires_stop";
      }) ||
      (report.checks.offline_backup.status === "blocked" &&
        JSON.stringify(report.operator_notes) !== JSON.stringify(["offline_backup_requires_stop"])) ||
      (report.checks.offline_backup.status !== "blocked" && report.operator_notes.length !== 0) ||
      report.status !== (report.blocking_reasons.length ? "attention" : "ready")
    ) {
      return false;
    }
    return true;
  }

  function validateWorkflowInventory(inventory) {
    if (
      !inventory ||
      typeof inventory !== "object" ||
      inventory.schema_version !== WORKFLOW_INVENTORY_SCHEMA ||
      Object.keys(inventory).sort().join(",") !== "schema_version,summary,versions,window" ||
      !inventory.summary ||
      typeof inventory.summary !== "object" ||
      Object.keys(inventory.summary).sort().join(",") !== "status_counts,total" ||
      !Number.isInteger(inventory.summary.total) ||
      inventory.summary.total < 0 ||
      !inventory.summary.status_counts ||
      typeof inventory.summary.status_counts !== "object" ||
      Object.keys(inventory.summary.status_counts).sort().join(",") !== "deprecated,other,published" ||
      Object.values(inventory.summary.status_counts).some(function (value) {
        return !Number.isInteger(value) || value < 0;
      }) ||
      Object.values(inventory.summary.status_counts).reduce(function (total, value) {
        return total + value;
      }, 0) !== inventory.summary.total ||
      !Array.isArray(inventory.versions) ||
      inventory.versions.length > 100 ||
      !inventory.window ||
      typeof inventory.window !== "object" ||
      Object.keys(inventory.window).sort().join(",") !== "max_items,returned,total,truncated" ||
      inventory.window.max_items !== 100 ||
      !Number.isInteger(inventory.window.total) ||
      inventory.window.total < 0 ||
      !Number.isInteger(inventory.window.returned) ||
      inventory.window.returned !== inventory.versions.length ||
      inventory.window.returned > inventory.window.total ||
      typeof inventory.window.truncated !== "boolean" ||
      inventory.window.truncated !== (inventory.window.returned < inventory.window.total) ||
      inventory.window.total !== inventory.summary.total
    ) {
      return false;
    }
    return inventory.versions.every(function (version) {
      return (
        version &&
        typeof version === "object" &&
        Object.keys(version).sort().join(",") === "aliases,checksum,status,version,workflow_id" &&
        typeof version.workflow_id === "string" &&
        version.workflow_id.length > 0 &&
        version.workflow_id.length <= 128 &&
        typeof version.version === "string" &&
        version.version.length > 0 &&
        version.version.length <= 128 &&
        ["published", "deprecated", "other"].indexOf(version.status) !== -1 &&
        Array.isArray(version.aliases) &&
        version.aliases.length <= 16 &&
        version.aliases.every(function (alias) {
          return typeof alias === "string" && alias.length > 0 && alias.length <= 64;
        }) &&
        typeof version.checksum === "string" &&
        /^[0-9a-f]{64}$/.test(version.checksum)
      );
    });
  }

  function validateWorkflowExplanation(explanation, selected) {
    if (
      !isObject(explanation) ||
      explanation.schema_version !== WORKFLOW_EXPLANATION_SCHEMA ||
      !hasExactKeys(explanation, [
        "schema_version", "workflow", "entry", "summary", "nodes", "edges",
        "input_contract", "policies", "safety",
      ]) ||
      !isObject(explanation.workflow) ||
      !hasExactKeys(explanation.workflow, ["id", "version", "status"]) ||
      explanation.workflow.id !== selected.workflow_id ||
      explanation.workflow.version !== selected.version ||
      ["published", "deprecated"].indexOf(explanation.workflow.status) === -1 ||
      !isBoundedString(explanation.entry, 128) ||
      !isObject(explanation.summary) ||
      !hasExactKeys(explanation.summary, [
        "node_count", "edge_count", "human_gate_count", "connector_node_count",
        "side_effecting_node_count", "terminal_node_count", "retrying_node_count",
        "timed_node_count", "input_property_count", "required_input_count",
      ]) ||
      ![
        "node_count", "edge_count", "human_gate_count", "connector_node_count",
        "side_effecting_node_count", "terminal_node_count", "retrying_node_count",
        "timed_node_count", "input_property_count", "required_input_count",
      ].every(function (field) {
        return isNonNegativeInteger(explanation.summary[field]);
      }) ||
      !Array.isArray(explanation.nodes) ||
      explanation.nodes.length > 1000 ||
      explanation.summary.node_count !== explanation.nodes.length ||
      !Array.isArray(explanation.edges) ||
      explanation.edges.length > 2000 ||
      explanation.summary.edge_count !== explanation.edges.length ||
      !validateExplanationInputContract(explanation.input_contract) ||
      explanation.summary.input_property_count !== explanation.input_contract.properties.length ||
      explanation.summary.required_input_count !== explanation.input_contract.required.length ||
      !validateExplanationPolicies(explanation.policies) ||
      !isObject(explanation.safety) ||
      !hasExactKeys(explanation.safety, [
        "side_effect_free", "connector_calls", "credentials_resolved", "raw_values_included",
      ]) ||
      explanation.safety.side_effect_free !== true ||
      explanation.safety.connector_calls !== false ||
      explanation.safety.credentials_resolved !== false ||
      explanation.safety.raw_values_included !== false
    ) {
      return false;
    }
    let humanGates = 0;
    let connectors = 0;
    let sideEffects = 0;
    let terminals = 0;
    let retrying = 0;
    let timed = 0;
    if (!explanation.nodes.every(function (node) {
      if (!isObject(node) || !hasExactKeys(node, [
        "id", "type", "transitions", "connector", "external_side_effect", "retry", "timeout_ms",
      ]) || !isBoundedString(node.id, 128) || !isBoundedString(node.type, 128) ||
        !isObject(node.transitions) || !hasExactKeys(node.transitions, ["success", "failure", "fallback"]) ||
        !["success", "failure", "fallback"].every(function (field) {
          return node.transitions[field] === null || isBoundedString(node.transitions[field], 128);
        }) || typeof node.external_side_effect !== "boolean" ||
        !isObject(node.retry) || !hasExactKeys(node.retry, ["max_attempts", "backoff_ms"]) ||
        !isNonNegativeInteger(node.retry.max_attempts) || !isNonNegativeInteger(node.retry.backoff_ms) ||
        (node.timeout_ms !== null && !isNonNegativeInteger(node.timeout_ms))
      ) {
        return false;
      }
      if (node.type === "human_gate") humanGates += 1;
      if (node.type === "end" || node.type === "failure") terminals += 1;
      if (node.retry.max_attempts > 0) retrying += 1;
      if (node.timeout_ms !== null && node.timeout_ms > 0) timed += 1;
      if (node.connector === null) {
        return true;
      }
      if (!isObject(node.connector) || !hasExactKeys(node.connector, [
        "id", "kind", "method", "credential_handle_count", "input_mapping_count", "external_side_effect",
      ]) || !isStringAtMost(node.connector.id, 128) || !isStringAtMost(node.connector.kind, 128) ||
        !isStringAtMost(node.connector.method, 128) ||
        !isNonNegativeInteger(node.connector.credential_handle_count) ||
        !isNonNegativeInteger(node.connector.input_mapping_count) ||
        typeof node.connector.external_side_effect !== "boolean"
      ) {
        return false;
      }
      connectors += 1;
      return true;
    })) {
      return false;
    }
    explanation.nodes.forEach(function (node) {
      if (node.external_side_effect) sideEffects += 1;
    });
    if (
      explanation.summary.human_gate_count !== humanGates ||
      explanation.summary.connector_node_count !== connectors ||
      explanation.summary.side_effecting_node_count !== sideEffects ||
      explanation.summary.terminal_node_count !== terminals ||
      explanation.summary.retrying_node_count !== retrying ||
      explanation.summary.timed_node_count !== timed
    ) {
      return false;
    }
    return explanation.edges.every(function (edge) {
      return isObject(edge) && hasExactKeys(edge, ["from", "to", "label", "conditioned"]) &&
        isBoundedString(edge.from, 128) && isBoundedString(edge.to, 128) &&
        [null, "next", "failure", "fallback", "custom"].indexOf(edge.label) !== -1 &&
        typeof edge.conditioned === "boolean";
    });
  }

  function validateExplanationInputContract(contract) {
    if (!isObject(contract) || !hasExactKeys(contract, [
      "present", "type", "required", "properties", "additional_properties",
    ]) || typeof contract.present !== "boolean" || !isStringAtMost(contract.type, 128) ||
      !Array.isArray(contract.required) || contract.required.length > 128 ||
      contract.required.some(function (name) { return !isBoundedString(name, 128); }) ||
      contract.required.some(function (name, index) {
        return index > 0 && contract.required[index - 1] >= name;
      }) ||
      !Array.isArray(contract.properties) || contract.properties.length > 128 ||
      !contract.properties.every(function (property) {
        return isObject(property) && hasExactKeys(property, ["name", "type", "required", "nested"]) &&
          isBoundedString(property.name, 128) && isStringAtMost(property.type, 128) &&
          typeof property.required === "boolean" && typeof property.nested === "boolean";
      }) || typeof contract.additional_properties !== "boolean"
    ) {
      return false;
    }
    return true;
  }

  function validateExplanationPolicies(policies) {
    return isObject(policies) && hasExactKeys(policies, [
      "default_retry", "default_timeout_ms", "workflow_timeout_ms",
    ]) && isObject(policies.default_retry) &&
      hasExactKeys(policies.default_retry, ["max_attempts", "backoff_ms"]) &&
      isNonNegativeInteger(policies.default_retry.max_attempts) &&
      isNonNegativeInteger(policies.default_retry.backoff_ms) &&
      (policies.default_timeout_ms === null || isNonNegativeInteger(policies.default_timeout_ms)) &&
      (policies.workflow_timeout_ms === null || isNonNegativeInteger(policies.workflow_timeout_ms));
  }

  function validateWorkflowPreflight(report, selected) {
    if (
      !isObject(report) ||
      report.schema_version !== WORKFLOW_PREFLIGHT_SCHEMA ||
      !hasExactKeys(report, ["schema_version", "workflow", "ready", "input", "summary", "nodes", "issues", "safety"]) ||
      !isObject(report.workflow) ||
      !hasExactKeys(report.workflow, ["id", "version", "status"]) ||
      report.workflow.id !== selected.workflow_id ||
      report.workflow.version !== selected.version ||
      ["published", "deprecated"].indexOf(report.workflow.status) === -1 ||
      typeof report.ready !== "boolean" ||
      !isObject(report.input) ||
      !hasExactKeys(report.input, [
        "provided", "status", "provided_property_count", "declared_property_count",
        "required_property_count", "missing_required_count", "unknown_property_count",
        "error_code", "error_path",
      ]) ||
      report.input.provided !== false ||
      report.input.provided_property_count !== 0 ||
      ["valid", "invalid"].indexOf(report.input.status) === -1 ||
      !["provided_property_count", "declared_property_count", "required_property_count", "missing_required_count", "unknown_property_count"].every(function (field) {
        return isNonNegativeInteger(report.input[field]) && report.input[field] <= 128;
      }) ||
      (report.input.status === "valid" && (report.input.error_code !== null || report.input.error_path !== null)) ||
      (report.input.status === "invalid" && (!isBoundedString(report.input.error_code, 128) || !Array.isArray(report.input.error_path))) ||
      (report.input.error_code !== null && !isSafeWorkflowRef(report.input.error_code)) ||
      (report.input.error_path !== null && (!Array.isArray(report.input.error_path) || report.input.error_path.length > 16 || report.input.error_path.some(function (part) {
        return (typeof part !== "string" && !Number.isInteger(part)) || typeof part === "boolean";
      }))) ||
      !isObject(report.summary) ||
      !hasExactKeys(report.summary, ["node_count", "connector_node_count", "side_effecting_node_count", "mapping_count", "blocked_node_count", "issue_count"]) ||
      !["node_count", "connector_node_count", "side_effecting_node_count", "mapping_count", "blocked_node_count", "issue_count"].every(function (field) {
        return isNonNegativeInteger(report.summary[field]);
      }) ||
      !Array.isArray(report.nodes) || report.nodes.length > 1000 ||
      report.summary.node_count !== report.nodes.length ||
      !Array.isArray(report.issues) || report.issues.length > 64 ||
      report.summary.issue_count !== report.issues.length ||
      !isObject(report.safety) ||
      !hasExactKeys(report.safety, ["side_effect_free", "connector_calls", "credentials_resolved", "raw_values_included"]) ||
      report.safety.side_effect_free !== true ||
      report.safety.connector_calls !== false ||
      report.safety.credentials_resolved !== false ||
      report.safety.raw_values_included !== false
    ) {
      return false;
    }
    let connectorCount = 0;
    let sideEffectCount = 0;
    let mappingCount = 0;
    let blockedCount = 0;
    if (!report.nodes.every(function (node) {
      if (!isObject(node) || !hasExactKeys(node, ["id", "type", "connector", "input_mapping"]) ||
        !isSafeWorkflowRef(node.id) || !isBoundedString(node.type, 128) ||
        !isObject(node.input_mapping) || !hasExactKeys(node.input_mapping, ["status", "mapping_count", "mapped_count", "missing_required_count", "missing_optional_count"]) ||
        ["not_applicable", "ready", "skipped", "blocked"].indexOf(node.input_mapping.status) === -1 ||
        !["mapping_count", "mapped_count", "missing_required_count", "missing_optional_count"].every(function (field) {
          return isNonNegativeInteger(node.input_mapping[field]);
        }) || node.input_mapping.mapping_count > 2000 ||
        node.input_mapping.mapped_count + node.input_mapping.missing_required_count + node.input_mapping.missing_optional_count !== node.input_mapping.mapping_count
      ) {
        return false;
      }
      mappingCount += node.input_mapping.mapping_count;
      if (node.input_mapping.status === "blocked") blockedCount += 1;
      if (node.connector === null) return true;
      if (!isObject(node.connector) || !hasExactKeys(node.connector, ["id", "kind", "external_side_effect", "credential_handle_count", "credentials_resolved"]) ||
        !isSafeWorkflowRef(node.connector.id) || !isStringAtMost(node.connector.kind, 128) ||
        typeof node.connector.external_side_effect !== "boolean" ||
        !isNonNegativeInteger(node.connector.credential_handle_count) ||
        node.connector.credentials_resolved !== false
      ) {
        return false;
      }
      connectorCount += 1;
      if (node.connector.external_side_effect) sideEffectCount += 1;
      return true;
    })) {
      return false;
    }
    if (!report.issues.every(function (issue) {
      return isObject(issue) && hasExactKeys(issue, ["code", "severity", "node_id", "path"]) &&
        ["input_invalid", "required_mapping_input_missing"].indexOf(issue.code) !== -1 &&
        issue.severity === "error" &&
        (issue.node_id === null || isSafeWorkflowRef(issue.node_id)) &&
        Array.isArray(issue.path) && issue.path.length <= 16 &&
        issue.path.every(function (part) {
          return (typeof part === "string" && part.length <= 128) || (Number.isInteger(part) && typeof part !== "boolean");
        });
    })) {
      return false;
    }
    return report.summary.connector_node_count === connectorCount &&
      report.summary.side_effecting_node_count === sideEffectCount &&
      report.summary.mapping_count === mappingCount &&
      report.summary.blocked_node_count === blockedCount &&
      report.ready === (report.input.status === "valid" && report.issues.length === 0);
  }

  function isObject(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
  }

  function hasExactKeys(value, keys) {
    return isObject(value) && Object.keys(value).sort().join(",") === keys.slice().sort().join(",");
  }

  function isBoundedString(value, maxLength) {
    return typeof value === "string" && value.length > 0 && value.length <= maxLength;
  }

  function isStringAtMost(value, maxLength) {
    return typeof value === "string" && value.length <= maxLength;
  }

  function isNonNegativeInteger(value) {
    return Number.isInteger(value) && value >= 0;
  }

  function isSafeWorkflowRef(value) {
    return typeof value === "string" && value.length > 0 && value.length <= 128 &&
      !/[\u0000-\u001f\u007f\/?#]/.test(value);
  }

  function isSafeCursor(cursor) {
    return typeof cursor === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(cursor);
  }

  async function decideSelectedRun(approved) {
    const run = selectedWaitingRun();
    if (!run || state.humanGateLoading) {
      return;
    }
    const decision = approved ? "approve" : "reject";
    if (
      typeof window.confirm === "function" &&
      !window.confirm(
        (approved ? "Approve" : "Reject") +
          " waiting run " +
          run.run_id +
          "? This records the human-gate decision and resumes the workflow.",
      )
    ) {
      return;
    }
    state.humanGateLoading = true;
    renderHumanGateActions();
    setStatus("Submitting", "");
    try {
      const response = await fetch(
        LIVE_RESUME_PREFIX + encodeURIComponent(run.run_id) + "/resume",
        {
          method: "POST",
          cache: "no-store",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ approved: approved }),
        },
      );
      if (!response.ok) {
        throw new Error(decision + " unavailable");
      }
      const payload = await response.json();
      if (
        !payload ||
        payload.run_id !== run.run_id ||
        payload.approved !== approved ||
        typeof payload.status !== "string" ||
        !payload.status
      ) {
        throw new Error(decision + " unavailable");
      }
      setStatus(approved ? "Approved" : "Rejected", "is-valid");
      await loadLiveSnapshot({ background: true });
    } catch (error) {
      setStatus("Unavailable", "is-invalid");
    } finally {
      state.humanGateLoading = false;
      renderHumanGateActions();
    }
  }

  async function cancelSelectedRun() {
    const run = selectedCancellableRun();
    if (!run || state.runCancelLoading) {
      return;
    }
    if (
      typeof window.confirm === "function" &&
      !window.confirm(
        "Cancel run " +
          run.run_id +
          "? Cancellation is cooperative; an in-flight connector attempt may finish.",
      )
    ) {
      return;
    }
    state.runCancelLoading = true;
    renderRunCancelActions();
    renderHumanGateActions();
    setStatus("Cancelling", "");
    try {
      const response = await fetch(
        LIVE_RESUME_PREFIX + encodeURIComponent(run.run_id) + "/cancel",
        {
          method: "POST",
          cache: "no-store",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        },
      );
      if (!response.ok) {
        throw new Error("cancellation unavailable");
      }
      const payload = await response.json();
      if (
        !payload ||
        payload.run_id !== run.run_id ||
        typeof payload.status !== "string" ||
        !payload.status
      ) {
        throw new Error("cancellation unavailable");
      }
      setStatus(
        payload.status === "cancelled" ? "Cancelled" : "Cancellation requested",
        "is-valid",
      );
      await loadLiveSnapshot({ background: true });
    } catch (error) {
      setStatus("Unavailable", "is-invalid");
    } finally {
      state.runCancelLoading = false;
      renderRunCancelActions();
      renderHumanGateActions();
    }
  }

  async function loadLiveRunDetail(runId) {
    if (!isLiveSnapshot() || !isSafeRunId(runId)) {
      return;
    }
    state.liveRunDetailId = runId;
    state.liveRunDetail = null;
    state.liveRunDetailLoading = true;
    state.liveRunDetailError = false;
    renderDetail();
    try {
      const response = await fetch(
        LIVE_RUN_DETAIL_PREFIX + encodeURIComponent(runId),
        { cache: "no-store" },
      );
      if (!response.ok) {
        throw new Error("run detail unavailable");
      }
      const detail = await response.json();
      if (!validateLiveRunDetail(detail, runId)) {
        throw new Error("run detail unavailable");
      }
      if (!selectedRunIs(runId)) {
        return;
      }
      state.liveRunDetail = detail;
    } catch (error) {
      if (selectedRunIs(runId)) {
        state.liveRunDetailError = true;
      }
    } finally {
      if (selectedRunIs(runId)) {
        state.liveRunDetailLoading = false;
        renderDetail();
      }
    }
  }

  function validateLiveRunDetail(detail, runId) {
    if (
      !detail ||
      typeof detail !== "object" ||
      detail.schema_version !== RUN_DETAIL_SCHEMA ||
      !detail.run ||
      typeof detail.run !== "object" ||
      detail.run.run_id !== runId ||
      !Array.isArray(detail.events) ||
      detail.events.length > 50 ||
      !detail.window ||
      typeof detail.window !== "object" ||
      detail.window.max_events !== 50 ||
      !Number.isInteger(detail.window.total) ||
      detail.window.total < 0 ||
      detail.window.returned !== detail.events.length ||
      detail.window.returned > detail.window.total ||
      typeof detail.window.truncated !== "boolean" ||
      detail.window.truncated !== (detail.window.returned < detail.window.total)
    ) {
      return false;
    }
    return detail.events.every(function (event) {
      return (
        event &&
        typeof event === "object" &&
        Number.isInteger(event.sequence) &&
        event.sequence >= 0 &&
        typeof event.type === "string" &&
        typeof event.has_error === "boolean"
      );
    });
  }

  function selectedRunIs(runId) {
    return Boolean(
      state.selected &&
      state.selected.kind === "run" &&
      state.selected.value &&
      state.selected.value.run_id === runId
    );
  }

  function isSafeRunId(runId) {
    return typeof runId === "string" && /^run_[A-Za-z0-9_-]{1,123}$/.test(runId);
  }

  function isLiveSnapshot() {
    return state.sourceLabel === "Live Service Snapshot" && Boolean(state.snapshot);
  }

  function selectedWaitingRun() {
    if (
      !isLiveSnapshot() ||
      !state.selected ||
      state.selected.kind !== "run"
    ) {
      return null;
    }
    const run = state.selected.value;
    if (
      !run ||
      run.status !== "waiting" ||
      typeof run.run_id !== "string" ||
      !/^run_[A-Za-z0-9_-]{1,123}$/.test(run.run_id)
    ) {
      return null;
    }
    return run;
  }

  function selectedCancellableRun() {
    if (!isLiveSnapshot() || !state.selected || state.selected.kind !== "run") {
      return null;
    }
    const run = state.selected.value;
    if (
      !run ||
      !isSafeRunId(run.run_id) ||
      ["created", "running", "waiting"].indexOf(run.status) === -1
    ) {
      return null;
    }
    return run;
  }

  async function loadServiceProbe() {
    setServiceStatus("Live service: checking", "");
    try {
      const response = await fetch(SERVICE_PROBE_URL, { cache: "no-store" });
      if (response.status === 404) {
        state.liveModeConfigured = false;
        stopAutoRefresh();
        els.toggleRefresh.disabled = true;
        els.downloadBundle.disabled = true;
        els.loadOlderRuns.disabled = true;
        els.loadOlderAudit.disabled = true;
        els.loadLiveSchedules.disabled = true;
        els.loadLiveReadiness.disabled = true;
        els.loadLiveWorkflows.disabled = true;
        setRunPageStatus("", "");
        setAuditPageStatus("", "");
        setSchedulePageStatus("", "");
        setReadinessPageStatus("", "");
        setWorkflowPageStatus("", "");
        setServiceStatus("Live service: static mode", "");
        renderDetail();
        return;
      }
      state.liveModeConfigured = true;
      els.toggleRefresh.disabled = false;
      els.downloadBundle.disabled = false;
      updateRunPageControls();
      updateAuditPageControls();
      updateLiveScheduleControls();
      updateLiveReadinessControls();
      updateLiveWorkflowControls();
      if (!response.ok) {
        throw new Error("service probe unavailable");
      }
      const probe = await response.json();
      if (!validateServiceProbe(probe)) {
        throw new Error("service probe unavailable");
      }
      const labels = {
        ready: ["Live service: ready", "is-valid"],
        not_ready: ["Live service: not ready", "is-invalid"],
        unavailable: ["Live service: unavailable", "is-invalid"],
      };
      setServiceStatus(labels[probe.status][0], labels[probe.status][1]);
      renderDetail();
    } catch (error) {
      state.liveModeConfigured = true;
      els.toggleRefresh.disabled = false;
      els.downloadBundle.disabled = false;
      updateRunPageControls();
      updateAuditPageControls();
      updateLiveScheduleControls();
      updateLiveReadinessControls();
      updateLiveWorkflowControls();
      setServiceStatus("Live service: unavailable", "is-invalid");
      renderDetail();
    }
  }

  function validateServiceProbe(probe) {
    return Boolean(
      probe &&
      typeof probe === "object" &&
      probe.schema_version === SERVICE_PROBE_SCHEMA &&
      ["ready", "not_ready", "unavailable"].indexOf(probe.status) !== -1 &&
      probe.health &&
      typeof probe.health === "object" &&
      probe.readiness &&
      typeof probe.readiness === "object",
    );
  }

  async function loadSelectedFile(event) {
    stopAutoRefresh();
    const file = event.target.files && event.target.files[0];
    if (!file) {
      return;
    }
    try {
      loadSnapshot(JSON.parse(await file.text()), file.name);
    } catch (error) {
      rejectSnapshot(file.name, { error: error.message });
    }
  }

  function loadSnapshot(snapshot, label) {
    const errors = validateSnapshot(snapshot);
    if (errors.length) {
      rejectSnapshot(label, { errors: errors });
      return;
    }
    const previousRunId =
      state.sourceLabel === "Live Service Snapshot" &&
      state.selected && state.selected.kind === "run" && state.selected.value
        ? state.selected.value.run_id
        : "";
    state.snapshot = snapshot;
    state.sourceLabel = label;
    state.liveRunDetail = null;
    state.liveRunDetailId = "";
    state.liveRunDetailLoading = false;
    state.liveRunDetailError = false;
    state.runCancelLoading = false;
    state.liveWorkflowExplanation = null;
    state.liveWorkflowExplanationKey = "";
    state.liveWorkflowExplanationLoading = false;
    state.liveWorkflowExplanationError = false;
    state.liveWorkflowPreflight = null;
    state.liveWorkflowPreflightKey = "";
    state.liveWorkflowPreflightLoading = false;
    state.liveWorkflowPreflightError = false;
    state.liveRunRows = null;
    state.liveRunPageCursor = "";
    state.liveRunPageHasMore = Boolean(
      label === "Live Service Snapshot" &&
      snapshot.window &&
      snapshot.window.runs &&
      snapshot.window.runs.truncated
    );
    state.liveRunPageLoading = false;
    state.liveAuditRows = null;
    state.liveAuditPageCursor = "";
    state.liveAuditPageHasMore = Boolean(
      label === "Live Service Snapshot" &&
      snapshot.window &&
      snapshot.window.audit_events &&
      snapshot.window.audit_events.truncated
    );
    state.liveAuditPageLoading = false;
    if (label !== "Live Service Snapshot") {
      state.liveSchedules = null;
      state.liveSchedulesLoading = false;
      setSchedulePageStatus("", "");
      state.liveReadiness = null;
      state.liveReadinessLoading = false;
      setReadinessPageStatus("", "");
      state.liveWorkflowInventory = null;
      state.liveWorkflowInventoryLoading = false;
      setWorkflowPageStatus("", "");
    }
    if (label === "Live Service Snapshot") {
      state.lastLiveLoadedAt = new Date().toISOString();
      state.liveRefreshError = false;
    } else {
      state.lastLiveLoadedAt = "";
      state.liveRefreshError = false;
    }
    state.selected = {
      kind: "snapshot",
      value: Object.assign(
        {},
        snapshot.summary || {},
        { window: snapshot.window || null },
      ),
    };
    if (label === "Live Service Snapshot" && isSafeRunId(previousRunId)) {
      const refreshedRun = (snapshot.runs || []).find(function (run) {
        return run && run.run_id === previousRunId;
      });
      if (refreshedRun) {
        state.selected = { kind: "run", value: refreshedRun };
      }
    }
    setStatus("Loaded", "is-valid");
    setRunPageStatus(
      state.liveRunPageHasMore ? "Older live runs available." : "",
      "",
    );
    setAuditPageStatus(
      state.liveAuditPageHasMore ? "Older live audit available." : "",
      "",
    );
    render();
    updateRunPageControls();
    updateAuditPageControls();
    updateLiveScheduleControls();
    updateLiveReadinessControls();
    updateLiveWorkflowControls();
    if (state.selected.kind === "run" && label === "Live Service Snapshot") {
      loadLiveRunDetail(state.selected.value.run_id);
    }
  }

  function rejectSnapshot(label, details) {
    state.snapshot = null;
    state.sourceLabel = label;
    state.liveRunDetail = null;
    state.liveRunDetailId = "";
    state.liveRunDetailLoading = false;
    state.liveRunDetailError = false;
    state.runCancelLoading = false;
    state.liveRunRows = null;
    state.liveRunPageCursor = "";
    state.liveRunPageHasMore = false;
    state.liveRunPageLoading = false;
    state.liveAuditRows = null;
    state.liveAuditPageCursor = "";
    state.liveAuditPageHasMore = false;
    state.liveAuditPageLoading = false;
    state.liveSchedules = null;
    state.liveSchedulesLoading = false;
    state.liveReadiness = null;
    state.liveReadinessLoading = false;
    state.liveWorkflowInventory = null;
    state.liveWorkflowInventoryLoading = false;
    state.liveWorkflowExplanation = null;
    state.liveWorkflowExplanationKey = "";
    state.liveWorkflowExplanationLoading = false;
    state.liveWorkflowExplanationError = false;
    state.liveWorkflowPreflight = null;
    state.liveWorkflowPreflightKey = "";
    state.liveWorkflowPreflightLoading = false;
    state.liveWorkflowPreflightError = false;
    setRunPageStatus("", "");
    setAuditPageStatus("", "");
    setSchedulePageStatus("", "");
    setReadinessPageStatus("", "");
    setWorkflowPageStatus("", "");
    state.selected = {
      kind: "error",
      value: Object.assign({ label: label }, details || {}),
    };
    setStatus("Invalid", "is-invalid");
    render();
    updateLiveScheduleControls();
    updateLiveReadinessControls();
    updateLiveWorkflowControls();
  }

  function validateSnapshot(snapshot) {
    const errors = [];
    if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)) {
      errors.push("snapshot must be an object");
      return errors;
    }
    if (snapshot.schema_version !== "skill2workflow-control-snapshot-0.1.0") {
      errors.push("schema_version is unsupported");
    }
    if (!snapshot.summary || typeof snapshot.summary !== "object" || Array.isArray(snapshot.summary)) {
      errors.push("summary must be an object");
    }
    const collectionFields = [
      "workflows",
      "runs",
      "audit_events",
      "connectors",
      "version_comparisons",
    ];
    collectionFields.forEach(function (field) {
      if (!Array.isArray(snapshot[field])) {
        errors.push(field + " must be an array");
      } else if (snapshot[field].some(function (item) {
        return !item || typeof item !== "object" || Array.isArray(item);
      })) {
        errors.push(field + " items must be objects");
      }
    });
    if (snapshot.window !== undefined) {
      validateSnapshotWindow(snapshot, collectionFields, errors);
    }
    return errors;
  }

  function validateSnapshotWindow(snapshot, collectionFields, errors) {
    const windowState = snapshot.window;
    if (!windowState || typeof windowState !== "object" || Array.isArray(windowState)) {
      errors.push("window must be an object");
      return;
    }
    const maxItems = windowState.max_items;
    if (!Number.isInteger(maxItems) || maxItems < 1) {
      errors.push("window.max_items must be a positive integer");
      return;
    }
    const summaryKeys = {
      workflows: "workflow_count",
      runs: "run_count",
      audit_events: "audit_event_count",
      connectors: "connector_count",
    };
    collectionFields.forEach(function (field) {
      const stats = windowState[field];
      if (!stats || typeof stats !== "object" || Array.isArray(stats)) {
        errors.push("window." + field + " must be an object");
        return;
      }
      const total = stats.total;
      const returned = stats.returned;
      const truncated = stats.truncated;
      const actualLength = Array.isArray(snapshot[field]) ? snapshot[field].length : -1;
      if (
        !isNonNegativeInteger(total) ||
        !isNonNegativeInteger(returned) ||
        typeof truncated !== "boolean" ||
        returned !== actualLength ||
        returned > total ||
        returned > maxItems ||
        truncated !== (returned < total)
      ) {
        errors.push("window." + field + " is inconsistent");
        return;
      }
      const summaryKey = summaryKeys[field];
      if (summaryKey && snapshot.summary && snapshot.summary[summaryKey] !== total) {
        errors.push("summary." + summaryKey + " does not match window." + field);
      }
    });
  }

  function isNonNegativeInteger(value) {
    return Number.isInteger(value) && value >= 0;
  }

  function render() {
    renderSnapshotScope();
    renderSummary();
    renderTabs();
    renderTables();
    renderDetail();
  }

  function renderSnapshotScope() {
    els.snapshotScope.className = "snapshot-scope";
    if (!state.snapshot) {
      els.snapshotScopeTitle.textContent = "No valid snapshot";
      els.snapshotScopeDetail.textContent = state.sourceLabel
        ? state.sourceLabel + " was rejected; previous data was cleared."
        : "Load an example or snapshot file to inspect its scope.";
      return;
    }
    const windowState = state.snapshot.window;
    if (!windowState) {
      els.snapshotScopeTitle.textContent = "Complete offline snapshot";
      els.snapshotScopeDetail.textContent = snapshotScopeDetail(
        state.sourceLabel + " contains the full exported collections."
      );
      return;
    }
    els.snapshotScope.classList.add("is-bounded");
    const fields = ["workflows", "runs", "audit_events", "connectors", "version_comparisons"];
    const truncated = fields.filter(function (field) {
      return windowState[field] && windowState[field].truncated;
    });
    if (truncated.length) {
      els.snapshotScope.classList.add("is-truncated");
    }
    const truncationLabel = truncated.length === 1
      ? "1 collection is truncated"
      : truncated.length + " collections are truncated";
    els.snapshotScopeTitle.textContent = "Bounded snapshot";
    els.snapshotScopeDetail.textContent = snapshotScopeDetail(truncated.length
      ? truncationLabel + ": " + truncated.join(", ") + ". Totals remain visible in Summary."
      : "All collections fit within the " + windowState.max_items + " item live window.");
  }

  function snapshotScopeDetail(detail) {
    if (state.sourceLabel !== "Live Service Snapshot" || !state.lastLiveLoadedAt) {
      return detail;
    }
    const updated = "Last updated " + formatDate(state.lastLiveLoadedAt) + ".";
    return state.liveRefreshError
      ? detail + " " + updated + " Last refresh failed; showing the previous snapshot."
      : detail + " " + updated;
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
      filterRows(state.liveRunRows || snapshot.runs),
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
      els.nodeOverlayRows,
      filterRows(nodeOverlayRows(snapshot.runs)),
      function (overlay) {
        return [
          linkCell(overlay.node_id || ""),
          textCell(overlay.run_id || ""),
          pillCell(overlay.status || ""),
          textCell(String(overlay.event_count || 0)),
          textCell(connectorLabel(overlay)),
        ];
      },
      "node overlay",
    );
    renderTable(
      els.auditRows,
      filterRows(state.liveAuditRows || snapshot.audit_events),
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
    renderTable(
      els.scheduleRows,
      filterRows(state.liveSchedules || []),
      function (schedule) {
        return [
          linkCell(schedule.schedule_id || ""),
          textCell((schedule.workflow_id || "") + "@" + (schedule.workflow_version || "")),
          pillCell(schedule.status || ""),
          textCell(String(Boolean(schedule.enabled))),
          textCell(formatDate(schedule.next_run_at || "")),
          textCell(formatInterval(schedule.interval_seconds)),
          textCell(schedule.last_run_id || "—"),
        ];
      },
      "schedule",
    );
    renderTable(
      els.readinessRows,
      filterRows(readinessRows(state.liveReadiness)),
      function (check) {
        return [
          linkCell(check.check),
          pillCell(check.status),
          textCell(check.details),
        ];
      },
      "readiness",
    );
    renderTable(
      els.liveWorkflowRows,
      filterRows((state.liveWorkflowInventory && state.liveWorkflowInventory.versions) || []),
      function (version) {
        return [
          linkCell(version.workflow_id),
          textCell(version.version),
          pillCell(version.status),
          textCell(version.aliases.join(", ") || "—"),
          linkCell(version.checksum.slice(0, 12)),
        ];
      },
      "live workflow",
    );
  }

  function readinessRows(report) {
    if (!report) return [];
    const service = report.service;
    const artifacts = report.checks.workflow_artifacts;
    const audit = report.checks.audit_integrity;
    const backup = report.checks.offline_backup;
    const rows = [
      {
        check: "service",
        status: service.ready ? "ready" : service.status,
        details:
          service.storage + "; layout " + service.state_layout_version +
          "; scheduler lease " + (service.scheduler_lease_owned ? "owned" : "not owned"),
      },
      {
        check: "workflow artifacts",
        status: artifacts.status,
        details: artifacts.issue_count === null
          ? "issue count unavailable"
          : String(artifacts.issue_count) + " issue(s)",
      },
      {
        check: "audit integrity",
        status: audit.status,
        details: "SQLite audit-chain verification",
      },
      {
        check: "offline backup",
        status: backup.status,
        details: backup.status === "blocked"
          ? "stop service before offline backup"
          : backup.status === "ready" ? "backup preflight passed" : "backup preflight unavailable",
      },
    ];
    if (report.blocking_reasons.length) {
      rows.push({
        check: "blocking reasons",
        status: "attention",
        details: report.blocking_reasons.join(", "),
      });
    }
    return rows;
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
        state.liveRunDetail = null;
        state.liveRunDetailId = "";
        state.liveRunDetailLoading = false;
        state.liveRunDetailError = false;
        state.runCancelLoading = false;
        state.liveWorkflowExplanation = null;
        state.liveWorkflowExplanationKey = "";
        state.liveWorkflowExplanationLoading = false;
        state.liveWorkflowExplanationError = false;
        state.liveWorkflowPreflight = null;
        state.liveWorkflowPreflightKey = "";
        state.liveWorkflowPreflightLoading = false;
        state.liveWorkflowPreflightError = false;
        renderTables();
        renderDetail();
        if (kind === "run" && isLiveSnapshot()) {
          loadLiveRunDetail(row.run_id || "");
        }
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
    renderHumanGateActions();
    renderRunCancelActions();
    renderWorkflowExplanationActions();
    renderRunDetailStatus(selected);
  }

  function renderWorkflowExplanationActions() {
    const workflow = selectedLiveWorkflow();
    const visible = Boolean(workflow);
    els.workflowExplanationActions.hidden = !visible;
    els.loadWorkflowExplanation.disabled =
      !visible || state.liveWorkflowExplanationLoading;
    els.loadWorkflowExplanation.textContent = state.liveWorkflowExplanationLoading
      ? "Loading Review…"
      : "Review Workflow Plan";
    els.loadWorkflowPreflight.disabled =
      !visible || state.liveWorkflowPreflightLoading;
    els.loadWorkflowPreflight.textContent = state.liveWorkflowPreflightLoading
      ? "Checking Trigger…"
      : "Check Empty Trigger";
    if (!visible) {
      setWorkflowExplanationStatus("Select a live workflow version to review its plan.", "");
      setWorkflowPreflightStatus("The preflight sends only an empty JSON object.", "");
      return;
    }
    const key = workflow.workflow_id + "@" + workflow.version;
    if (state.liveWorkflowExplanationLoading && state.liveWorkflowExplanationKey === key) {
      setWorkflowExplanationStatus("Loading bounded workflow review…", "");
    } else if (state.liveWorkflowExplanationError && state.liveWorkflowExplanationKey === key) {
      setWorkflowExplanationStatus("Workflow review unavailable; metadata remains visible.", "is-invalid");
    } else if (state.liveWorkflowExplanation && state.liveWorkflowExplanationKey === key) {
      setWorkflowExplanationStatus("Read-only review loaded; no connector or credential was invoked.", "is-valid");
    } else {
      setWorkflowExplanationStatus("Review topology, gates, side effects, retries, and timeouts before execution.", "");
    }
    if (state.liveWorkflowPreflightLoading && state.liveWorkflowPreflightKey === key) {
      setWorkflowPreflightStatus("Checking the empty trigger shape…", "");
    } else if (state.liveWorkflowPreflightError && state.liveWorkflowPreflightKey === key) {
      setWorkflowPreflightStatus("Preflight unavailable; metadata remains visible.", "is-invalid");
    } else if (state.liveWorkflowPreflight && state.liveWorkflowPreflightKey === key) {
      const report = state.liveWorkflowPreflight;
      setWorkflowPreflightStatus(
        report.ready
          ? "Empty trigger is ready; no connector or credential was invoked."
          : "Empty trigger is blocked; review missing input or mapping requirements.",
        report.ready ? "is-valid" : "is-invalid",
      );
    } else {
      setWorkflowPreflightStatus("The preflight sends only an empty JSON object.", "");
    }
  }

  function renderRunDetailStatus(selected) {
    const isRun = Boolean(
      isLiveSnapshot() && selected && selected.kind === "run" && selected.value
    );
    els.runDetailStatus.hidden = !isRun;
    els.runDetailStatus.className = "run-detail-status";
    if (!isRun) {
      return;
    }
    const runId = selected.value.run_id || "";
    if (state.liveRunDetailLoading && state.liveRunDetailId === runId) {
      els.runDetailStatus.textContent = "Loading bounded redacted run evidence…";
      return;
    }
    if (state.liveRunDetailError && state.liveRunDetailId === runId) {
      els.runDetailStatus.textContent = "Run evidence unavailable; summary remains visible.";
      els.runDetailStatus.classList.add("is-invalid");
      return;
    }
    if (state.liveRunDetail && state.liveRunDetailId === runId) {
      const windowState = state.liveRunDetail.window;
      els.runDetailStatus.textContent =
        "Redacted event tail loaded: " +
        windowState.returned +
        " of " +
        windowState.total +
        " events" +
        (windowState.truncated ? " (truncated)." : ".");
      els.runDetailStatus.classList.add("is-valid");
      return;
    }
    els.runDetailStatus.textContent = "Select a live run to load its bounded evidence.";
  }

  function renderHumanGateActions() {
    const run = selectedWaitingRun();
    const visible = Boolean(run);
    els.humanGateActions.hidden = !visible;
    els.approveRun.disabled = !visible || state.humanGateLoading || state.runCancelLoading;
    els.rejectRun.disabled = !visible || state.humanGateLoading || state.runCancelLoading;
    if (visible) {
      els.humanGateStatus.textContent = state.humanGateLoading
        ? "Submitting the decision…"
        : "This run is waiting for an explicit human decision.";
    }
  }

  function renderRunCancelActions() {
    const run = selectedCancellableRun();
    const visible = Boolean(run);
    els.runCancelActions.hidden = !visible;
    els.cancelRun.disabled =
      !visible || state.runCancelLoading || state.humanGateLoading;
    if (visible) {
      els.runCancelStatus.textContent = state.runCancelLoading
        ? "Recording cooperative cancellation…"
        : "Cancellation is cooperative; an in-flight connector attempt may finish.";
    }
  }

  function showDetail(title, value) {
    els.detailTitle.textContent = title;
    const detail =
      value &&
      value.run_id &&
      state.liveRunDetail &&
      state.liveRunDetailId === value.run_id
        ? { summary: value, redacted_detail: state.liveRunDetail }
        : value;
    const workflow = selectedLiveWorkflow();
    const workflowKey = workflow ? workflow.workflow_id + "@" + workflow.version : "";
    const detailEnvelope = { metadata: detail };
    let hasEnvelope = false;
    if (workflow && state.liveWorkflowExplanation && state.liveWorkflowExplanationKey === workflowKey) {
      detailEnvelope.redacted_workflow_plan = state.liveWorkflowExplanation;
      hasEnvelope = true;
    }
    if (workflow && state.liveWorkflowPreflight && state.liveWorkflowPreflightKey === workflowKey) {
      detailEnvelope.redacted_empty_trigger_preflight = state.liveWorkflowPreflight;
      hasEnvelope = true;
    }
    els.detailJson.textContent = JSON.stringify(hasEnvelope ? detailEnvelope : detail, null, 2);
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
    if (value.workflow_id && value.version && !Array.isArray(value.aliases)) {
      return [["Workflow", value.workflow_id], ["Version", value.version], ["Status", value.status || ""], ["Checksum", shorten(value.checksum || "")]];
    }
    if (value.kind && value.severity) {
      return [["Kind", value.kind || ""], ["Severity", value.severity || ""], ["Workflow", value.workflow_id || ""], ["Run", value.run_id || ""]];
    }
    if (value.node_id && Object.prototype.hasOwnProperty.call(value, "event_count")) {
      return [["Node", value.node_id], ["Status", value.status || ""], ["Events", String(value.event_count || 0)], ["Connector", connectorLabel(value)]];
    }
    if (value.run_id) {
      return [["Run", value.run_id], ["Workflow", value.workflow_id || ""], ["Status", value.status || ""], ["Events", String(value.event_count || 0)]];
    }
    if (value.schedule_id) {
      return [
        ["Schedule", value.schedule_id],
        ["Workflow", value.workflow_id || ""],
        ["Status", value.status || ""],
        ["Next Run", formatDate(value.next_run_at || "")],
      ];
    }
    if (value.check && value.status) {
      return [["Check", value.check], ["Status", value.status], ["Details", value.details || ""]];
    }
    if (value.workflow_id && value.version && value.checksum) {
      return [
        ["Workflow", value.workflow_id],
        ["Version", value.version],
        ["Status", value.status || ""],
        ["Aliases", (value.aliases || []).join(", ") || "—"],
        ["Checksum", value.checksum],
      ];
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
    if (selected.kind === "node overlay") return value.node_id || "Node";
    if (selected.kind === "audit") return value.type || "Audit";
    if (selected.kind === "connector") return value.name || value.id || "Connector";
    if (selected.kind === "version comparison") return value.workflow_id || "Comparison";
    if (selected.kind === "attention") return value.kind || "Attention";
    if (selected.kind === "recent event") return value.type || "Recent Event";
    if (selected.kind === "connector event") return value.type || "Connector Event";
    if (selected.kind === "schedule") return value.schedule_id || "Schedule";
    if (selected.kind === "readiness") return value.check || "Readiness";
    if (selected.kind === "live workflow") return value.workflow_id + "@" + value.version;
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

  function setServiceStatus(text, className) {
    els.serviceStatus.textContent = text;
    els.serviceStatus.className = "service-status" + (className ? " " + className : "");
  }

  function setRunPageStatus(text, className) {
    els.runPageStatus.textContent = text;
    els.runPageStatus.className = "run-page-status" + (className ? " " + className : "");
  }

  function setAuditPageStatus(text, className) {
    els.auditPageStatus.textContent = text;
    els.auditPageStatus.className = "audit-page-status" + (className ? " " + className : "");
  }

  function setSchedulePageStatus(text, className) {
    els.schedulePageStatus.textContent = text;
    els.schedulePageStatus.className = "schedule-page-status" + (className ? " " + className : "");
  }

  function setReadinessPageStatus(text, className) {
    els.readinessPageStatus.textContent = text;
    els.readinessPageStatus.className = "readiness-page-status" + (className ? " " + className : "");
  }

  function setWorkflowPageStatus(text, className) {
    els.workflowPageStatus.textContent = text;
    els.workflowPageStatus.className = "workflow-page-status" + (className ? " " + className : "");
  }

  function setWorkflowExplanationStatus(text, className) {
    els.workflowExplanationStatus.textContent = text;
    els.workflowExplanationStatus.className = className || "";
  }

  function setWorkflowPreflightStatus(text, className) {
    els.workflowPreflightStatus.textContent = text;
    els.workflowPreflightStatus.className = className || "";
  }

  function updateRunPageControls() {
    const enabled = isLiveSnapshot() && state.liveRunPageHasMore;
    els.loadOlderRuns.disabled = !enabled || state.liveRunPageLoading;
    els.loadOlderRuns.textContent = state.liveRunPageLoading
      ? "Loading Runs…"
      : "Load Older Runs";
  }

  function updateAuditPageControls() {
    const enabled = isLiveSnapshot() && state.liveAuditPageHasMore;
    els.loadOlderAudit.disabled = !enabled || state.liveAuditPageLoading;
    els.loadOlderAudit.textContent = state.liveAuditPageLoading
      ? "Loading Audit…"
      : "Load Older Audit";
  }

  function updateLiveScheduleControls() {
    const enabled = state.liveModeConfigured && isLiveSnapshot();
    els.loadLiveSchedules.disabled = !enabled || state.liveSchedulesLoading;
    els.loadLiveSchedules.textContent = state.liveSchedulesLoading
      ? "Loading Schedules…"
      : "Load Live Schedules";
  }

  function updateLiveReadinessControls() {
    const enabled = state.liveModeConfigured && isLiveSnapshot();
    els.loadLiveReadiness.disabled = !enabled || state.liveReadinessLoading;
    els.loadLiveReadiness.textContent = state.liveReadinessLoading
      ? "Loading Readiness…"
      : "Load Live Readiness";
  }

  function updateLiveWorkflowControls() {
    const enabled = state.liveModeConfigured && isLiveSnapshot();
    els.loadLiveWorkflows.disabled = !enabled || state.liveWorkflowInventoryLoading;
    els.loadLiveWorkflows.textContent = state.liveWorkflowInventoryLoading
      ? "Loading Workflows…"
      : "Load Live Workflows";
  }

  function updateWorkflowExplanationControls() {
    const workflow = selectedLiveWorkflow();
    els.loadWorkflowExplanation.disabled =
      !workflow || state.liveWorkflowExplanationLoading;
    els.loadWorkflowExplanation.textContent = state.liveWorkflowExplanationLoading
      ? "Loading Review…"
      : "Review Workflow Plan";
  }

  function updateWorkflowPreflightControls() {
    const workflow = selectedLiveWorkflow();
    els.loadWorkflowPreflight.disabled =
      !workflow || state.liveWorkflowPreflightLoading;
    els.loadWorkflowPreflight.textContent = state.liveWorkflowPreflightLoading
      ? "Checking Trigger…"
      : "Check Empty Trigger";
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

  function nodeOverlayRows(runs) {
    const rows = [];
    (runs || []).forEach(function (run) {
      const overlays = run.node_overlays || {};
      Object.keys(overlays).sort().forEach(function (nodeId) {
        const overlay = Object.assign({}, overlays[nodeId], {
          run_id: run.run_id || "",
          workflow_id: run.workflow_id || "",
          workflow_version: run.workflow_version || "",
        });
        rows.push(overlay);
      });
    });
    return rows;
  }

  function connectorLabel(overlay) {
    if (!overlay.connector_id) return "";
    const status = overlay.connector_status ? " " + overlay.connector_status : "";
    const attempts = overlay.attempts ? " x" + overlay.attempts : "";
    return overlay.connector_id + status + attempts;
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

  function formatInterval(value) {
    const seconds = Number(value || 0);
    if (!Number.isFinite(seconds) || seconds < 1) return "";
    if (seconds % 86400 === 0) return String(seconds / 86400) + "d";
    if (seconds % 3600 === 0) return String(seconds / 3600) + "h";
    if (seconds % 60 === 0) return String(seconds / 60) + "m";
    return String(seconds) + "s";
  }

  function shorten(value) {
    return value.length > 12 ? value.slice(0, 12) : value;
  }
})();
