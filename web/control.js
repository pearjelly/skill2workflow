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
  const LIVE_SCHEDULE_DISPATCH_PAGE_PREFIX = "/api/v1/recurring-schedule-dispatch-pages/";
  const LIVE_SCHEDULE_DISPATCH_REVIEW_PREFIX = "/api/v1/recurring-schedule-dispatch-reviews/";
  const LIVE_OPERATIONAL_READINESS_URL = "/api/v1/operational-readiness";
  const LIVE_WORKFLOW_INVENTORY_URL = "/api/v1/workflows";
  const LIVE_WORKFLOW_EXPLANATION_PREFIX = "/api/v1/workflow-explanations/";
  const LIVE_WORKFLOW_DIFF_PREFIX = "/api/v1/workflow-diffs/";
  const LIVE_WORKFLOW_PREFLIGHT_PREFIX = "/api/v1/workflow-preflights/";
  const LIVE_WORKFLOW_EMPTY_TRIGGER_URL = "/api/v1/workflow-empty-triggers";
  const LIVE_WORKFLOW_INPUT_PREFLIGHT_URL = "/api/v1/workflow-input-preflights";
  const LIVE_WORKFLOW_INPUT_TRIGGER_URL = "/api/v1/workflow-input-triggers";
  const LIVE_WORKFLOW_RELEASE_URL = "/api/v1/workflow-releases";
  const LIVE_WORKFLOW_RELEASE_PREFLIGHT_URL = "/api/v1/workflow-release-preflights";
  const LIVE_WORKFLOW_RELEASE_TARGET_REVIEW_URL = "/api/v1/workflow-release-target-reviews";
  const LIVE_WORKFLOW_PROMOTION_URL = "/api/v1/workflow-promotions";
  const LIVE_WORKFLOW_DEPRECATION_URL = "/api/v1/workflow-deprecations";
  const RUN_DETAIL_SCHEMA = "skill2workflow-run-detail-0.1.0";
  const RUN_PAGE_SCHEMA = "skill2workflow-run-list-0.2.0";
  const AUDIT_PAGE_SCHEMA = "skill2workflow-audit-event-list-0.1.0";
  const SCHEDULE_LIST_SCHEMA = "skill2workflow-recurring-schedule-list-0.1.0";
  const SCHEDULE_DISPATCH_PAGE_SCHEMA = "skill2workflow-recurring-schedule-dispatch-page-0.1.0";
  const SCHEDULE_DISPATCH_REVIEW_SCHEMA = "skill2workflow-recurring-schedule-dispatch-review-0.1.0";
  const OPERATIONAL_READINESS_SCHEMA = "skill2workflow-operational-readiness-0.1.0";
  const WORKFLOW_INVENTORY_SCHEMA = "skill2workflow-workflow-inventory-0.1.0";
  const WORKFLOW_EXPLANATION_SCHEMA = "skill2workflow-workflow-explanation-0.1.0";
  const WORKFLOW_DIFF_SCHEMA = "skill2workflow-workflow-diff-0.1.0";
  const WORKFLOW_PREFLIGHT_SCHEMA = "skill2workflow-workflow-preflight-0.1.0";
  const WORKFLOW_RELEASE_SCHEMA = "skill2workflow-workflow-release-0.1.0";
  const WORKFLOW_RELEASE_PREFLIGHT_SCHEMA = "skill2workflow-workflow-release-preflight-0.1.0";
  const WORKFLOW_RELEASE_TARGET_REVIEW_SCHEMA = "skill2workflow-workflow-release-target-review-0.1.0";
  const WORKFLOW_PROMOTION_SCHEMA = "skill2workflow-workflow-promotion-0.1.0";
  const WORKFLOW_DEPRECATION_SCHEMA = "skill2workflow-workflow-deprecation-0.1.0";
  const LIVE_RUN_ROWS_MAX = 500;
  const LIVE_AUDIT_ROWS_MAX = 500;
  const SERVICE_PROBE_SCHEMA = "skill2workflow-service-probe-0.1.0";
  const AUTO_REFRESH_INTERVAL_MS = 10000;
  const MAX_WORKFLOW_RELEASE_BYTES = 1024 * 1024;
  const MAX_WORKFLOW_INPUT_BYTES = 1024 * 1024;
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
    liveRunActionConflict: false,
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
    liveScheduleDispatchPage: null,
    liveScheduleDispatchRows: null,
    liveScheduleDispatchScheduleId: "",
    liveScheduleDispatchCursor: "",
    liveScheduleDispatchHasMore: false,
    liveScheduleDispatchLoading: false,
    liveScheduleDispatchError: false,
    liveScheduleDispatchReviewLoading: false,
    liveScheduleDispatchReviewError: false,
    liveScheduleDispatchReviewConflict: false,
    liveReadiness: null,
    liveReadinessLoading: false,
    liveWorkflowInventory: null,
    liveWorkflowInventoryLoading: false,
    liveWorkflowExplanation: null,
    liveWorkflowExplanationKey: "",
    liveWorkflowExplanationLoading: false,
    liveWorkflowExplanationError: false,
    liveWorkflowDiff: null,
    liveWorkflowDiffKey: "",
    liveWorkflowDiffLoading: false,
    liveWorkflowDiffError: false,
    liveWorkflowPreflight: null,
    liveWorkflowPreflightKey: "",
    liveWorkflowPreflightLoading: false,
    liveWorkflowPreflightError: false,
    liveWorkflowEmptyTriggerAttempt: null,
    liveWorkflowEmptyTriggerLoading: false,
    liveWorkflowEmptyTriggerError: false,
    liveWorkflowInputCandidate: null,
    liveWorkflowInputPreflightLoading: false,
    liveWorkflowInputTriggerAttempt: null,
    liveWorkflowInputTriggerLoading: false,
    liveWorkflowInputTriggerError: false,
    liveWorkflowTriggeredRun: null,
    liveWorkflowReleaseCandidate: null,
    liveWorkflowReleasePreflightLoading: false,
    liveWorkflowReleaseTargetReviewLoading: false,
    liveWorkflowReleaseLoading: false,
    liveWorkflowReleaseError: false,
    liveWorkflowPromotionLoading: false,
    liveWorkflowPromotionError: false,
    liveWorkflowPromotionConflict: false,
    liveWorkflowDeprecationLoading: false,
    liveWorkflowDeprecationError: false,
    liveWorkflowDeprecationConflict: false,
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
    els.workflowReleaseFileAction = document.getElementById("workflow-release-file-action");
    els.workflowReleaseFile = document.getElementById("workflow-release-file");
    els.preflightStagedWorkflow = document.getElementById("preflight-staged-workflow");
    els.reviewStagedWorkflowTarget = document.getElementById("review-staged-workflow-target");
    els.publishWorkflow = document.getElementById("publish-workflow");
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
    els.scheduleDispatchActions = document.getElementById("schedule-dispatch-actions");
    els.scheduleDispatchStatus = document.getElementById("schedule-dispatch-status");
    els.loadScheduleDispatches = document.getElementById("load-schedule-dispatches");
    els.loadOlderScheduleDispatches = document.getElementById("load-older-schedule-dispatches");
    els.scheduleDispatchReviewTarget = document.getElementById("schedule-dispatch-review-target");
    els.scheduleDispatchReviewOutcome = document.getElementById("schedule-dispatch-review-outcome");
    els.scheduleDispatchReviewStatus = document.getElementById("schedule-dispatch-review-status");
    els.reviewScheduleDispatch = document.getElementById("review-schedule-dispatch");
    els.readinessPageStatus = document.getElementById("readiness-page-status");
    els.workflowPageStatus = document.getElementById("workflow-page-status");
    els.workflowExplanationActions = document.getElementById("workflow-explanation-actions");
    els.workflowExplanationStatus = document.getElementById("workflow-explanation-status");
    els.loadWorkflowExplanation = document.getElementById("load-workflow-explanation");
    els.workflowDiffTarget = document.getElementById("workflow-diff-target");
    els.workflowDiffStatus = document.getElementById("workflow-diff-status");
    els.loadWorkflowDiff = document.getElementById("load-workflow-diff");
    els.workflowPreflightStatus = document.getElementById("workflow-preflight-status");
    els.loadWorkflowPreflight = document.getElementById("load-workflow-preflight");
    els.triggerWorkflowEmpty = document.getElementById("trigger-workflow-empty");
    els.workflowEmptyTriggerStatus = document.getElementById("workflow-empty-trigger-status");
    els.workflowInputTriggerActions = document.getElementById("workflow-input-trigger-actions");
    els.workflowInputFileAction = document.getElementById("workflow-input-file-action");
    els.workflowInputFile = document.getElementById("workflow-input-file");
    els.preflightWorkflowInput = document.getElementById("preflight-workflow-input");
    els.triggerWorkflowInput = document.getElementById("trigger-workflow-input");
    els.workflowInputTriggerStatus = document.getElementById("workflow-input-trigger-status");
    els.workflowRunHandoffActions = document.getElementById("workflow-run-handoff-actions");
    els.reviewTriggeredRun = document.getElementById("review-triggered-run");
    els.workflowRunHandoffStatus = document.getElementById("workflow-run-handoff-status");
    els.promoteWorkflow = document.getElementById("promote-workflow");
    els.workflowPromotionStatus = document.getElementById("workflow-promotion-status");
    els.deprecateWorkflow = document.getElementById("deprecate-workflow");
    els.workflowDeprecationStatus = document.getElementById("workflow-deprecation-status");
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
    els.loadScheduleDispatches.addEventListener("click", function () {
      loadLiveScheduleDispatches({ reset: true });
    });
    els.loadOlderScheduleDispatches.addEventListener("click", function () {
      loadLiveScheduleDispatches({ reset: false });
    });
    els.reviewScheduleDispatch.addEventListener("click", reviewLiveScheduleDispatch);
    els.scheduleDispatchReviewTarget.addEventListener("change", updateLiveScheduleDispatchReviewControls);
    els.scheduleDispatchReviewOutcome.addEventListener("change", updateLiveScheduleDispatchReviewControls);
    els.loadLiveReadiness.addEventListener("click", loadLiveReadiness);
    els.loadLiveWorkflows.addEventListener("click", loadLiveWorkflows);
    els.workflowReleaseFile.addEventListener("change", stageWorkflowReleaseFile);
    els.preflightStagedWorkflow.addEventListener("click", preflightStagedWorkflow);
    els.reviewStagedWorkflowTarget.addEventListener("click", reviewStagedWorkflowTarget);
    els.publishWorkflow.addEventListener("click", publishStagedWorkflow);
    els.loadWorkflowExplanation.addEventListener("click", loadLiveWorkflowExplanation);
    els.loadWorkflowDiff.addEventListener("click", loadLiveWorkflowDiff);
    els.workflowDiffTarget.addEventListener("change", function () {
      state.liveWorkflowDiff = null;
      state.liveWorkflowDiffKey = "";
      state.liveWorkflowDiffError = false;
      renderDetail();
    });
    els.loadWorkflowPreflight.addEventListener("click", loadLiveWorkflowPreflight);
    els.triggerWorkflowEmpty.addEventListener("click", triggerLiveWorkflowEmpty);
    els.workflowInputFile.addEventListener("change", stageWorkflowInputFile);
    els.preflightWorkflowInput.addEventListener("click", preflightStagedWorkflowInput);
    els.triggerWorkflowInput.addEventListener("click", triggerStagedWorkflowInput);
    els.reviewTriggeredRun.addEventListener("click", reviewTriggeredRun);
    els.promoteWorkflow.addEventListener("click", promoteLiveWorkflow);
    els.deprecateWorkflow.addEventListener("click", deprecateLiveWorkflow);
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

  async function loadLiveScheduleDispatches(options) {
    const schedule = selectedLiveSchedule();
    const reset = Boolean(options && options.reset);
    if (!schedule || state.liveScheduleDispatchLoading || (!reset && !state.liveScheduleDispatchHasMore)) {
      return;
    }
    const scheduleId = schedule.schedule_id;
    const cursor = reset ? "" : state.liveScheduleDispatchCursor;
    state.liveScheduleDispatchLoading = true;
    state.liveScheduleDispatchError = false;
    state.liveScheduleDispatchReviewLoading = false;
    state.liveScheduleDispatchReviewError = false;
    if (reset) {
      state.liveScheduleDispatchRows = null;
      state.liveScheduleDispatchPage = null;
      state.liveScheduleDispatchCursor = "";
      state.liveScheduleDispatchHasMore = false;
    }
    state.liveScheduleDispatchScheduleId = scheduleId;
    updateLiveScheduleDispatchControls();
    setScheduleDispatchStatus(
      cursor ? "Loading older dispatch evidence…" : "Loading bounded dispatch evidence…",
      "",
    );
    try {
      const url = LIVE_SCHEDULE_DISPATCH_PAGE_PREFIX + encodeURIComponent(scheduleId) +
        (cursor ? "/" + encodeURIComponent(cursor) : "");
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("schedule dispatch page unavailable");
      }
      const page = await response.json();
      if (!validateRecurringScheduleDispatchPage(page, scheduleId)) {
        throw new Error("schedule dispatch page unavailable");
      }
      state.liveScheduleDispatchPage = page;
      state.liveScheduleDispatchRows = mergeLiveScheduleDispatchRows(
        state.liveScheduleDispatchRows || [],
        page.dispatches,
      );
      state.liveScheduleDispatchCursor = page.window.next_cursor || "";
      state.liveScheduleDispatchHasMore = Boolean(page.window.has_more && page.window.next_cursor);
      if (reset) {
        state.liveScheduleDispatchReviewError = false;
        state.liveScheduleDispatchReviewConflict = false;
      }
      renderDetail();
      setScheduleDispatchStatus(
        "Loaded " + state.liveScheduleDispatchRows.length + " retained dispatch records" +
          (state.liveScheduleDispatchHasMore ? "; older evidence available." : "."),
        "is-valid",
      );
      setStatus("Loaded", "is-valid");
    } catch (error) {
      state.liveScheduleDispatchError = true;
      renderDetail();
      setScheduleDispatchStatus(
        "Dispatch evidence unavailable; schedule metadata remains visible.",
        "is-invalid",
      );
    } finally {
      state.liveScheduleDispatchLoading = false;
      updateLiveScheduleDispatchControls();
    }
  }

  function mergeLiveScheduleDispatchRows(existing, additions) {
    const rows = [];
    const seen = Object.create(null);
    (existing || []).concat(additions || []).forEach(function (dispatch) {
      if (!dispatch || typeof dispatch.dispatch_id !== "string" || seen[dispatch.dispatch_id]) {
        return;
      }
      seen[dispatch.dispatch_id] = true;
      rows.push(dispatch);
    });
    return rows.slice(-500);
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
      state.liveWorkflowPromotionError = false;
      state.liveWorkflowPromotionConflict = false;
      state.liveWorkflowDeprecationError = false;
      state.liveWorkflowDeprecationConflict = false;
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

  async function loadLiveWorkflowDiff() {
    const workflow = selectedLiveWorkflow();
    const targetVersion = els.workflowDiffTarget.value;
    if (!workflow || !isSafeWorkflowRef(targetVersion) || targetVersion === workflow.version || state.liveWorkflowDiffLoading) {
      return;
    }
    const key = workflow.workflow_id + "@" + workflow.version + "@" + targetVersion;
    state.liveWorkflowDiffLoading = true;
    state.liveWorkflowDiffError = false;
    updateWorkflowDiffControls();
    setWorkflowDiffStatus("Loading bounded structural diff…", "");
    try {
      const url =
        LIVE_WORKFLOW_DIFF_PREFIX +
        encodeURIComponent(workflow.workflow_id) +
        "/" +
        encodeURIComponent(workflow.version) +
        "/" +
        encodeURIComponent(targetVersion);
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("workflow diff unavailable");
      }
      const diff = await response.json();
      if (!validateWorkflowDiff(diff, workflow, targetVersion)) {
        throw new Error("workflow diff unavailable");
      }
      state.liveWorkflowDiff = diff;
      state.liveWorkflowDiffKey = key;
      renderDetail();
      setWorkflowDiffStatus(
        "Structural diff loaded; no connector, credential, or workflow execution was invoked.",
        "is-valid",
      );
      setStatus("Compared", "is-valid");
    } catch (error) {
      state.liveWorkflowDiff = null;
      state.liveWorkflowDiffKey = key;
      state.liveWorkflowDiffError = true;
      renderDetail();
      setWorkflowDiffStatus("Workflow diff unavailable; version metadata remains visible.", "is-invalid");
    } finally {
      state.liveWorkflowDiffLoading = false;
      updateWorkflowDiffControls();
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

  function liveEmptyTriggerTarget() {
    const workflow = selectedLiveWorkflow();
    const key = workflow ? workflow.workflow_id + "@" + workflow.version : "";
    if (
      !workflow || workflow.status !== "published" ||
      !state.liveWorkflowPreflight || state.liveWorkflowPreflightKey !== key ||
      state.liveWorkflowPreflight.ready !== true
    ) {
      return null;
    }
    return { workflow: workflow, key: key };
  }

  function liveEmptyTriggerAttempt(target) {
    const attempt = state.liveWorkflowEmptyTriggerAttempt;
    if (
      attempt && attempt.key === target.key &&
      typeof attempt.idempotencyKey === "string" &&
      /^live-ui-[A-Za-z0-9_-]{24,64}$/.test(attempt.idempotencyKey)
    ) {
      return attempt;
    }
    const bytes = new Uint8Array(18);
    if (!window.crypto || typeof window.crypto.getRandomValues !== "function") {
      return null;
    }
    window.crypto.getRandomValues(bytes);
    const idempotencyKey = "live-ui-" + Array.from(bytes).map(function (value) {
      return value.toString(16).padStart(2, "0");
    }).join("");
    const next = { key: target.key, idempotencyKey: idempotencyKey, receipt: null };
    state.liveWorkflowEmptyTriggerAttempt = next;
    return next;
  }

  async function triggerLiveWorkflowEmpty() {
    const target = liveEmptyTriggerTarget();
    if (!target || state.liveWorkflowEmptyTriggerLoading) {
      return;
    }
    const attempt = liveEmptyTriggerAttempt(target);
    if (!attempt) {
      state.liveWorkflowEmptyTriggerError = true;
      setWorkflowEmptyTriggerStatus("Secure idempotency key generation is unavailable; no run was started.", "is-invalid");
      return;
    }
    const retry = Boolean(attempt.receipt === null && state.liveWorkflowEmptyTriggerError);
    if (typeof window.confirm === "function" && !window.confirm(
      (retry ? "Retry " : "Start ") + target.workflow.workflow_id + "@" + target.workflow.version +
      " with an empty trigger? This may execute its configured workflow and side effects."
    )) {
      return;
    }
    state.liveWorkflowEmptyTriggerLoading = true;
    state.liveWorkflowEmptyTriggerError = false;
    updateWorkflowEmptyTriggerControls();
    setWorkflowEmptyTriggerStatus(retry ? "Retrying the same idempotent empty trigger…" : "Starting the confirmed empty trigger…", "");
    try {
      const response = await fetch(LIVE_WORKFLOW_EMPTY_TRIGGER_URL, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow_id: target.workflow.workflow_id,
          version: target.workflow.version,
          idempotency_key: attempt.idempotencyKey,
        }),
      });
      if (!response.ok) {
        throw new Error("workflow empty trigger unavailable");
      }
      const receipt = await response.json();
      if (!validateWorkflowEmptyTrigger(receipt, target.workflow, attempt.idempotencyKey)) {
        throw new Error("workflow empty trigger unavailable");
      }
      attempt.receipt = receipt;
      state.liveWorkflowTriggeredRun = { key: target.key, receipt: receipt };
      setWorkflowEmptyTriggerStatus(
        "Empty trigger accepted as " + receipt.run_id + " (" + receipt.run_status + ").",
        "is-valid",
      );
      setStatus("Empty Trigger Started", "is-valid");
      renderDetail();
    } catch (error) {
      state.liveWorkflowEmptyTriggerError = true;
      setWorkflowEmptyTriggerStatus(
        "Start outcome is unavailable; retry uses the same idempotency key and never changes input.",
        "is-invalid",
      );
    } finally {
      state.liveWorkflowEmptyTriggerLoading = false;
      updateWorkflowEmptyTriggerControls();
    }
  }

  function validateWorkflowEmptyTrigger(receipt, workflow, idempotencyKey) {
    return isObject(receipt) && hasExactKeys(receipt, [
      "trigger_id", "workflow_id", "workflow_version", "run_id", "run_status",
      "source", "idempotency_key", "input_keys",
    ]) && receipt.workflow_id === workflow.workflow_id &&
      receipt.workflow_version === workflow.version && receipt.source === "live-ui" &&
      receipt.idempotency_key === idempotencyKey &&
      typeof receipt.trigger_id === "string" && /^trigger_[A-Za-z0-9_-]{1,123}$/.test(receipt.trigger_id) &&
      isSafeRunId(receipt.run_id) && ["created", "running", "waiting", "completed", "failed", "cancelled", "interrupted"].indexOf(receipt.run_status) !== -1 &&
      Array.isArray(receipt.input_keys) && receipt.input_keys.length === 0;
  }

  function liveInputTriggerTarget() {
    const workflow = selectedLiveWorkflow();
    const candidate = state.liveWorkflowInputCandidate;
    const key = workflow ? workflow.workflow_id + "@" + workflow.version : "";
    if (!workflow || workflow.status !== "published" || !candidate || candidate.key !== key ||
      !candidate.preflight || candidate.preflight.ready !== true) {
      return null;
    }
    return { workflow: workflow, candidate: candidate, key: key };
  }

  async function stageWorkflowInputFile(event) {
    const workflow = selectedLiveWorkflow();
    if (!workflow || workflow.status !== "published" || state.liveWorkflowInputPreflightLoading || state.liveWorkflowInputTriggerLoading) {
      return;
    }
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    state.liveWorkflowInputCandidate = null;
    state.liveWorkflowInputTriggerAttempt = null;
    state.liveWorkflowInputTriggerError = false;
    updateWorkflowInputTriggerControls();
    setWorkflowInputTriggerStatus("Staging trigger input…", "");
    try {
      if (typeof file.size !== "number" || file.size < 2 || file.size > MAX_WORKFLOW_INPUT_BYTES) {
        throw new Error("trigger input is too large");
      }
      const input = JSON.parse(await file.text());
      if (!isObject(input) || Object.keys(input).length > 128) {
        throw new Error("trigger input is malformed");
      }
      const encoded = JSON.stringify(input);
      const requestEnvelope = JSON.stringify({
        workflow_id: workflow.workflow_id,
        version: workflow.version,
        idempotency_key: "live-ui-" + "0".repeat(36),
        input: input,
      });
      if (!encoded || !requestEnvelope || new TextEncoder().encode(requestEnvelope).length > MAX_WORKFLOW_INPUT_BYTES) {
        throw new Error("trigger input is too large");
      }
      state.liveWorkflowInputCandidate = {
        key: workflow.workflow_id + "@" + workflow.version,
        input: input,
        inputKeys: Object.keys(input).sort(),
        preflight: null,
      };
      setWorkflowInputTriggerStatus("Input staged in browser memory; check it before starting.", "is-valid");
    } catch (error) {
      setWorkflowInputTriggerStatus("Input was rejected locally; use one JSON object within the limit.", "is-invalid");
    } finally {
      event.target.value = "";
      updateWorkflowInputTriggerControls();
    }
  }

  async function preflightStagedWorkflowInput() {
    const workflow = selectedLiveWorkflow();
    const candidate = state.liveWorkflowInputCandidate;
    if (!workflow || !candidate || candidate.key !== workflow.workflow_id + "@" + workflow.version ||
      state.liveWorkflowInputPreflightLoading || state.liveWorkflowInputTriggerLoading) {
      return;
    }
    candidate.preflight = null;
    state.liveWorkflowInputPreflightLoading = true;
    updateWorkflowInputTriggerControls();
    setWorkflowInputTriggerStatus("Checking staged input without executing…", "");
    try {
      const response = await fetch(LIVE_WORKFLOW_INPUT_PREFLIGHT_URL, {
        method: "POST", cache: "no-store", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow_id: workflow.workflow_id, version: workflow.version, input: candidate.input }),
      });
      if (!response.ok) throw new Error("workflow input preflight unavailable");
      const report = await response.json();
      if (!validateWorkflowPreflight(report, workflow, true)) {
        throw new Error("workflow input preflight unavailable");
      }
      candidate.preflight = report;
      setWorkflowInputTriggerStatus(
        report.ready
          ? "Staged input is ready; no connector or credential was invoked."
          : "Staged input is blocked; review the value-free preflight report.",
        report.ready ? "is-valid" : "is-invalid",
      );
      renderDetail();
    } catch (error) {
      setWorkflowInputTriggerStatus("Input preflight unavailable; no run was started.", "is-invalid");
    } finally {
      state.liveWorkflowInputPreflightLoading = false;
      updateWorkflowInputTriggerControls();
    }
  }

  function liveInputTriggerAttempt(target) {
    const attempt = state.liveWorkflowInputTriggerAttempt;
    if (attempt && attempt.key === target.key && attempt.candidate === target.candidate &&
      typeof attempt.idempotencyKey === "string" && /^live-ui-[A-Za-z0-9_-]{24,64}$/.test(attempt.idempotencyKey)) {
      return attempt;
    }
    const bytes = new Uint8Array(18);
    if (!window.crypto || typeof window.crypto.getRandomValues !== "function") return null;
    window.crypto.getRandomValues(bytes);
    const idempotencyKey = "live-ui-" + Array.from(bytes).map(function (value) {
      return value.toString(16).padStart(2, "0");
    }).join("");
    const next = { key: target.key, candidate: target.candidate, idempotencyKey: idempotencyKey, receipt: null };
    state.liveWorkflowInputTriggerAttempt = next;
    return next;
  }

  async function triggerStagedWorkflowInput() {
    const target = liveInputTriggerTarget();
    if (!target || state.liveWorkflowInputTriggerLoading) return;
    const attempt = liveInputTriggerAttempt(target);
    if (!attempt) {
      setWorkflowInputTriggerStatus("Secure idempotency key generation is unavailable; no run was started.", "is-invalid");
      return;
    }
    const retry = Boolean(attempt.receipt === null && state.liveWorkflowInputTriggerError);
    if (typeof window.confirm === "function" && !window.confirm(
      (retry ? "Retry " : "Start ") + target.workflow.workflow_id + "@" + target.workflow.version +
      " with the staged input? Input becomes durable run context and this may execute configured side effects."
    )) return;
    state.liveWorkflowInputTriggerLoading = true;
    state.liveWorkflowInputTriggerError = false;
    updateWorkflowInputTriggerControls();
    setWorkflowInputTriggerStatus(retry ? "Retrying the same idempotent staged input…" : "Starting the confirmed staged input…", "");
    try {
      const response = await fetch(LIVE_WORKFLOW_INPUT_TRIGGER_URL, {
        method: "POST", cache: "no-store", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow_id: target.workflow.workflow_id, version: target.workflow.version,
          idempotency_key: attempt.idempotencyKey, input: target.candidate.input,
        }),
      });
      if (!response.ok) throw new Error("workflow input trigger unavailable");
      const receipt = await response.json();
      if (!validateWorkflowInputTrigger(receipt, target.workflow, attempt.idempotencyKey, target.candidate.inputKeys)) {
        throw new Error("workflow input trigger unavailable");
      }
      attempt.receipt = receipt;
      state.liveWorkflowTriggeredRun = { key: target.key, receipt: receipt };
      setWorkflowInputTriggerStatus("Staged input accepted as " + receipt.run_id + " (" + receipt.run_status + ").", "is-valid");
      setStatus("Staged Input Started", "is-valid");
      renderDetail();
    } catch (error) {
      state.liveWorkflowInputTriggerError = true;
      setWorkflowInputTriggerStatus("Start outcome is unavailable; retry uses the same key and unchanged staged input.", "is-invalid");
    } finally {
      state.liveWorkflowInputTriggerLoading = false;
      updateWorkflowInputTriggerControls();
    }
  }

  function validateWorkflowInputTrigger(receipt, workflow, idempotencyKey, inputKeys) {
    return isObject(receipt) && hasExactKeys(receipt, [
        "trigger_id", "workflow_id", "workflow_version", "run_id", "run_status",
        "source", "idempotency_key", "input_keys",
      ]) && receipt.workflow_id === workflow.workflow_id && receipt.workflow_version === workflow.version &&
      receipt.source === "live-ui" && receipt.idempotency_key === idempotencyKey &&
      typeof receipt.trigger_id === "string" && /^trigger_[A-Za-z0-9_-]{1,123}$/.test(receipt.trigger_id) &&
      isSafeRunId(receipt.run_id) && ["created", "running", "waiting", "completed", "failed", "cancelled", "interrupted"].indexOf(receipt.run_status) !== -1 &&
      Array.isArray(receipt.input_keys) && receipt.input_keys.join("\u0000") === inputKeys.join("\u0000");
  }

  function liveWorkflowTriggeredRunTarget() {
    const workflow = selectedLiveWorkflow();
    const handoff = state.liveWorkflowTriggeredRun;
    const key = workflow ? workflow.workflow_id + "@" + workflow.version : "";
    if (!workflow || !handoff || handoff.key !== key || !handoff.receipt ||
      !isSafeRunId(handoff.receipt.run_id) || handoff.receipt.workflow_id !== workflow.workflow_id ||
      handoff.receipt.workflow_version !== workflow.version) {
      return null;
    }
    return handoff.receipt;
  }

  function reviewTriggeredRun() {
    const receipt = liveWorkflowTriggeredRunTarget();
    if (!receipt || state.liveRunDetailLoading) return;
    state.selected = {
      kind: "run",
      value: {
        run_id: receipt.run_id,
        workflow_id: receipt.workflow_id,
        workflow_version: receipt.workflow_version,
        status: receipt.run_status,
      },
    };
    state.liveRunDetail = null;
    state.liveRunDetailId = "";
    state.liveRunDetailLoading = false;
    state.liveRunDetailError = false;
    state.runCancelLoading = false;
    renderTables();
    renderDetail();
    loadLiveRunDetail(receipt.run_id);
  }

  async function stageWorkflowReleaseFile(event) {
    if (!state.liveModeConfigured || !isLiveSnapshot() || state.liveWorkflowReleaseLoading) {
      return;
    }
    const file = event.target.files && event.target.files[0];
    if (!file) {
      return;
    }
    state.liveWorkflowReleaseCandidate = null;
    state.liveWorkflowReleaseLoading = true;
    state.liveWorkflowReleaseError = false;
    updateWorkflowReleaseControls();
    setStatus("Staging", "");
    try {
      if (typeof file.size !== "number" || file.size < 1 || file.size > MAX_WORKFLOW_RELEASE_BYTES) {
        throw new Error("workflow publication body is too large");
      }
      const workflow = JSON.parse(await file.text());
      const candidate = buildWorkflowReleaseCandidate(workflow);
      if (!candidate) {
        throw new Error("workflow publication body is malformed");
      }
      state.liveWorkflowReleaseCandidate = candidate;
      setStatus("Workflow staged; check it before publishing", "is-valid");
    } catch (error) {
      state.liveWorkflowReleaseError = true;
      setStatus("Workflow rejected", "is-invalid");
    } finally {
      event.target.value = "";
      state.liveWorkflowReleaseLoading = false;
      updateWorkflowReleaseControls();
    }
  }

  function buildWorkflowReleaseCandidate(workflow) {
    if (!isObject(workflow) || !isObject(workflow.workflow) ||
      workflow.schema_version !== "0.1.0" ||
      !isSafeWorkflowRef(workflow.workflow.id) ||
      !isSafeWorkflowRef(workflow.workflow.version)) {
      return null;
    }
    let body;
    try {
      body = JSON.stringify({ workflow: workflow });
    } catch (error) {
      return null;
    }
    if (!body || new TextEncoder().encode(body).length > MAX_WORKFLOW_RELEASE_BYTES) {
      return null;
    }
    return {
      workflow: workflow,
      workflowId: workflow.workflow.id,
      version: workflow.workflow.version,
      preflight: null,
      targetReview: null,
    };
  }

  async function preflightStagedWorkflow() {
    const candidate = state.liveWorkflowReleaseCandidate;
    if (!candidate || !state.liveModeConfigured || !isLiveSnapshot() ||
      state.liveWorkflowReleaseLoading || state.liveWorkflowReleasePreflightLoading) {
      return;
    }
    candidate.preflight = null;
    candidate.targetReview = null;
    state.liveWorkflowReleasePreflightLoading = true;
    state.liveWorkflowReleaseError = false;
    updateWorkflowReleaseControls();
    setStatus("Checking staged workflow", "");
    try {
      const response = await fetch(LIVE_WORKFLOW_RELEASE_PREFLIGHT_URL, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow: candidate.workflow }),
      });
      if (!response.ok) {
        throw new Error("workflow release preflight unavailable");
      }
      const result = await response.json();
      if (!validateWorkflowReleasePreflight(result, candidate)) {
        throw new Error("workflow release preflight unavailable");
      }
      candidate.preflight = result;
      setStatus(
        result.empty_trigger_ready
          ? "Staged workflow validated; empty trigger is ready"
          : "Staged workflow validated; empty trigger needs input",
        "is-valid",
      );
    } catch (error) {
      state.liveWorkflowReleaseError = true;
      setStatus("Staged workflow validation unavailable", "is-invalid");
    } finally {
      state.liveWorkflowReleasePreflightLoading = false;
      updateWorkflowReleaseControls();
    }
  }

  async function publishStagedWorkflow() {
    const candidate = state.liveWorkflowReleaseCandidate;
    if (!candidate || !candidate.preflight || !candidate.targetReview ||
      !candidate.targetReview.publication_ready || !state.liveModeConfigured ||
      !isLiveSnapshot() || state.liveWorkflowReleaseLoading ||
      state.liveWorkflowReleasePreflightLoading || state.liveWorkflowReleaseTargetReviewLoading) {
      return;
    }
    if (typeof window.confirm === "function" && !window.confirm(
      "Publish " + candidate.workflowId + "@" + candidate.version +
      "? This creates an immutable version but does not promote an alias or execute it."
    )) {
      return;
    }
    state.liveWorkflowReleaseLoading = true;
    state.liveWorkflowReleaseError = false;
    updateWorkflowReleaseControls();
    setStatus("Publishing", "");
    try {
      const response = await fetch(LIVE_WORKFLOW_RELEASE_URL, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow: candidate.workflow }),
      });
      if (!response.ok) {
        if (response.status === 409) {
          candidate.targetReview = null;
          throw new Error("workflow publication target changed");
        }
        throw new Error("workflow publication unavailable");
      }
      const result = await response.json();
      if (!validateWorkflowRelease(result, candidate)) {
        throw new Error("workflow publication unavailable");
      }
      state.liveWorkflowReleaseCandidate = null;
      setStatus("Published", "is-valid");
      await loadLiveWorkflows();
    } catch (error) {
      state.liveWorkflowReleaseError = true;
      if (error && error.message === "workflow publication target changed") {
        setStatus("Publish target changed; review it again before another publication", "is-invalid");
      } else {
        setStatus("Publication unavailable", "is-invalid");
      }
    } finally {
      state.liveWorkflowReleaseLoading = false;
      updateWorkflowReleaseControls();
    }
  }

  function validateWorkflowRelease(result, candidate) {
    return isObject(result) &&
      result.schema_version === WORKFLOW_RELEASE_SCHEMA &&
      hasExactKeys(result, ["schema_version", "workflow_id", "version", "status", "checksum"]) &&
      result.workflow_id === candidate.workflowId &&
      result.version === candidate.version &&
      result.status === "published" &&
      isChecksum(result.checksum);
  }

  function validateWorkflowReleasePreflight(result, candidate) {
    if (!isObject(result) || result.schema_version !== WORKFLOW_RELEASE_PREFLIGHT_SCHEMA ||
      !hasExactKeys(result, ["schema_version", "workflow", "document_valid", "empty_trigger_ready", "summary", "issues", "safety"]) ||
      !isObject(result.workflow) || !hasExactKeys(result.workflow, ["id", "version"]) ||
      result.workflow.id !== candidate.workflowId || result.workflow.version !== candidate.version ||
      result.document_valid !== true || typeof result.empty_trigger_ready !== "boolean" ||
      !isObject(result.summary) || !hasExactKeys(result.summary, ["node_count", "connector_node_count", "side_effecting_node_count", "mapping_count", "blocked_node_count", "issue_count"]) ||
      !Array.isArray(result.issues) || result.issues.length > 64 ||
      !isObject(result.safety) || !hasExactKeys(result.safety, ["side_effect_free", "connector_calls", "credentials_resolved", "raw_values_included"]) || result.safety.side_effect_free !== true ||
      result.safety.connector_calls !== false || result.safety.credentials_resolved !== false ||
      result.safety.raw_values_included !== false) {
      return false;
    }
    const summary = result.summary;
    if (!["node_count", "connector_node_count", "side_effecting_node_count", "mapping_count", "blocked_node_count", "issue_count"].every(function (field) {
      return isNonNegativeInteger(summary[field]);
    }) || summary.node_count > 1000 || summary.connector_node_count > summary.node_count ||
      summary.side_effecting_node_count > summary.connector_node_count ||
      summary.blocked_node_count > summary.node_count || summary.issue_count !== result.issues.length) {
      return false;
    }
    return result.issues.every(function (issue) {
      return isObject(issue) && hasExactKeys(issue, ["code", "severity", "node_id", "path"]) &&
        ["input_invalid", "required_mapping_input_missing"].indexOf(issue.code) !== -1 &&
        issue.severity === "error" && (issue.node_id === null || isSafeWorkflowRef(issue.node_id)) &&
        Array.isArray(issue.path) && issue.path.length <= 16 && issue.path.every(function (part) {
          return (typeof part === "string" && part.length <= 128) ||
            (Number.isInteger(part) && typeof part !== "boolean");
        });
    });
  }

  async function reviewStagedWorkflowTarget() {
    const candidate = state.liveWorkflowReleaseCandidate;
    if (!candidate || !candidate.preflight || !state.liveModeConfigured ||
      !isLiveSnapshot() || state.liveWorkflowReleaseLoading ||
      state.liveWorkflowReleasePreflightLoading || state.liveWorkflowReleaseTargetReviewLoading) {
      return;
    }
    candidate.targetReview = null;
    state.liveWorkflowReleaseTargetReviewLoading = true;
    state.liveWorkflowReleaseError = false;
    updateWorkflowReleaseControls();
    setStatus("Reviewing publication target", "");
    try {
      const response = await fetch(LIVE_WORKFLOW_RELEASE_TARGET_REVIEW_URL, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow: candidate.workflow }),
      });
      if (!response.ok) {
        throw new Error("workflow release target review unavailable");
      }
      const result = await response.json();
      if (!validateWorkflowReleaseTargetReview(result, candidate)) {
        throw new Error("workflow release target review unavailable");
      }
      candidate.targetReview = result;
      if (result.target.state === "new") {
        setStatus(
          "Publish target is free at review time; publication still checks atomically",
          "is-valid",
        );
      } else if (result.target.state === "idempotent") {
        setStatus("Publish target already matches; publication is an idempotent retry", "is-valid");
      } else {
        setStatus("Publish target conflicts with a different immutable version", "is-invalid");
      }
    } catch (error) {
      state.liveWorkflowReleaseError = true;
      setStatus("Publish target review unavailable", "is-invalid");
    } finally {
      state.liveWorkflowReleaseTargetReviewLoading = false;
      updateWorkflowReleaseControls();
    }
  }

  function validateWorkflowReleaseTargetReview(result, candidate) {
    if (!isObject(result) ||
      result.schema_version !== WORKFLOW_RELEASE_TARGET_REVIEW_SCHEMA ||
      !hasExactKeys(result, ["schema_version", "workflow", "candidate_checksum", "target", "publication_ready", "empty_trigger_ready", "summary", "issues", "safety"]) ||
      !isObject(result.workflow) || !hasExactKeys(result.workflow, ["id", "version"]) ||
      result.workflow.id !== candidate.workflowId || result.workflow.version !== candidate.version ||
      !isChecksum(result.candidate_checksum) || !isObject(result.target) ||
      !hasExactKeys(result.target, ["state", "published_checksum"]) ||
      ["new", "idempotent", "conflict"].indexOf(result.target.state) === -1 ||
      typeof result.publication_ready !== "boolean" ||
      typeof result.empty_trigger_ready !== "boolean" ||
      !isObject(result.summary) ||
      !hasExactKeys(result.summary, ["node_count", "connector_node_count", "side_effecting_node_count", "mapping_count", "blocked_node_count", "issue_count"]) ||
      !Array.isArray(result.issues) || result.issues.length > 64 ||
      !isObject(result.safety) ||
      !hasExactKeys(result.safety, ["side_effect_free", "connector_calls", "credentials_resolved", "raw_values_included"]) ||
      result.safety.side_effect_free !== true || result.safety.connector_calls !== false ||
      result.safety.credentials_resolved !== false || result.safety.raw_values_included !== false) {
      return false;
    }
    const target = result.target;
    if ((target.state === "new" && target.published_checksum !== null) ||
      (target.state !== "new" && !isChecksum(target.published_checksum)) ||
      result.publication_ready !== (target.state === "new" || target.state === "idempotent") ||
      (target.state === "idempotent" && target.published_checksum !== result.candidate_checksum) ||
      (target.state === "conflict" && target.published_checksum === result.candidate_checksum)) {
      return false;
    }
    const summary = result.summary;
    if (!["node_count", "connector_node_count", "side_effecting_node_count", "mapping_count", "blocked_node_count", "issue_count"].every(function (field) {
      return isNonNegativeInteger(summary[field]);
    }) || summary.node_count > 1000 || summary.connector_node_count > summary.node_count ||
      summary.side_effecting_node_count > summary.connector_node_count ||
      summary.blocked_node_count > summary.node_count || summary.issue_count !== result.issues.length) {
      return false;
    }
    return result.issues.every(function (issue) {
      return isObject(issue) && hasExactKeys(issue, ["code", "severity", "node_id", "path"]) &&
        ["input_invalid", "required_mapping_input_missing"].indexOf(issue.code) !== -1 &&
        issue.severity === "error" && (issue.node_id === null || isSafeWorkflowRef(issue.node_id)) &&
        Array.isArray(issue.path) && issue.path.length <= 16 && issue.path.every(function (part) {
          return (typeof part === "string" && part.length <= 128) ||
            (Number.isInteger(part) && typeof part !== "boolean");
        });
    });
  }

  async function promoteLiveWorkflow() {
    const workflow = selectedLiveWorkflow();
    const promotion = liveWorkflowPromotionTarget(workflow);
    if (!promotion || state.liveWorkflowPromotionLoading) {
      return;
    }
    if (typeof window.confirm === "function" && !window.confirm(
      "Promote " + workflow.workflow_id + "@" + workflow.version +
      " to the production alias? This changes the next alias-based trigger target."
    )) {
      return;
    }
    state.liveWorkflowPromotionLoading = true;
    state.liveWorkflowPromotionError = false;
    state.liveWorkflowPromotionConflict = false;
    updateWorkflowPromotionControls();
    setWorkflowPromotionStatus("Recording the compare-and-swap promotion…", "");
    try {
      const response = await fetch(LIVE_WORKFLOW_PROMOTION_URL, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow_id: workflow.workflow_id,
          version: workflow.version,
          alias: "production",
          expected_current_version: promotion.expectedCurrentVersion,
        }),
      });
      if (!response.ok) {
        if (response.status === 409) {
          state.liveWorkflowPromotionConflict = true;
          throw new Error("workflow promotion target changed");
        }
        throw new Error("workflow promotion unavailable");
      }
      const result = await response.json();
      if (!validateWorkflowPromotion(result, workflow)) {
        throw new Error("workflow promotion unavailable");
      }
      setWorkflowPromotionStatus(
        "Production alias promoted; reload the inventory to confirm the new target.",
        "is-valid",
      );
      setStatus("Promoted", "is-valid");
      await loadLiveWorkflows();
      const refreshed = state.liveWorkflowInventory && state.liveWorkflowInventory.versions.find(function (item) {
        return item && item.workflow_id === workflow.workflow_id && item.version === workflow.version;
      });
      if (refreshed) {
        state.selected = { kind: "live workflow", value: refreshed };
        render();
      }
    } catch (error) {
      state.liveWorkflowPromotionError = true;
      setWorkflowPromotionStatus(
        error && error.message === "workflow promotion target changed"
          ? "Promotion target changed; Reload Live Workflows before another promotion."
          : "Promotion unavailable; the production alias was not assumed to change.",
        "is-invalid",
      );
    } finally {
      state.liveWorkflowPromotionLoading = false;
      updateWorkflowPromotionControls();
    }
  }

  async function deprecateLiveWorkflow() {
    const workflow = selectedLiveWorkflow();
    const deprecation = liveWorkflowDeprecationTarget(workflow);
    if (!deprecation || state.liveWorkflowDeprecationLoading) {
      return;
    }
    if (typeof window.confirm === "function" && !window.confirm(
      "Deprecate " + workflow.workflow_id + "@" + workflow.version +
      "? This keeps the immutable artifact but prevents new starts through this version."
    )) {
      return;
    }
    state.liveWorkflowDeprecationLoading = true;
    state.liveWorkflowDeprecationError = false;
    state.liveWorkflowDeprecationConflict = false;
    updateWorkflowDeprecationControls();
    setWorkflowDeprecationStatus("Recording the checksum-and-alias compare-and-swap…", "");
    try {
      const response = await fetch(LIVE_WORKFLOW_DEPRECATION_URL, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow_id: workflow.workflow_id,
          version: workflow.version,
          expected_checksum: deprecation.expectedChecksum,
          expected_aliases: deprecation.expectedAliases,
        }),
      });
      if (!response.ok) {
        if (response.status === 409) {
          state.liveWorkflowDeprecationConflict = true;
          throw new Error("workflow deprecation target changed");
        }
        throw new Error("workflow deprecation unavailable");
      }
      const result = await response.json();
      if (!validateWorkflowDeprecation(result, workflow)) {
        throw new Error("workflow deprecation unavailable");
      }
      setWorkflowDeprecationStatus(
        "Version deprecated; its immutable artifact remains available for audit and rollback review.",
        "is-valid",
      );
      setStatus("Deprecated", "is-valid");
      await loadLiveWorkflows();
      const refreshed = state.liveWorkflowInventory && state.liveWorkflowInventory.versions.find(function (item) {
        return item && item.workflow_id === workflow.workflow_id && item.version === workflow.version;
      });
      if (refreshed) {
        state.selected = { kind: "live workflow", value: refreshed };
        render();
      }
    } catch (error) {
      state.liveWorkflowDeprecationError = true;
      setWorkflowDeprecationStatus(
        error && error.message === "workflow deprecation target changed"
          ? "Deprecation target changed; Reload Live Workflows before another deprecation."
          : "Deprecation unavailable; the version was not assumed to change.",
        "is-invalid",
      );
    } finally {
      state.liveWorkflowDeprecationLoading = false;
      updateWorkflowDeprecationControls();
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

  function liveWorkflowPromotionTarget(workflow) {
    if (
      !workflow || workflow.status !== "published" ||
      !state.liveWorkflowInventory || !Array.isArray(state.liveWorkflowInventory.versions)
    ) {
      return null;
    }
    const versions = state.liveWorkflowInventory.versions.filter(function (item) {
      return item && item.workflow_id === workflow.workflow_id;
    });
    const current = versions.filter(function (item) {
      return Array.isArray(item.aliases) && item.aliases.indexOf("production") !== -1;
    });
    if (current.length > 1 || (current.length === 1 && current[0].version === workflow.version)) {
      return null;
    }
    return {
      expectedCurrentVersion: current.length === 1 ? current[0].version : "",
    };
  }

  function liveWorkflowDeprecationTarget(workflow) {
    if (
      !workflow || workflow.status !== "published" ||
      !state.liveWorkflowInventory || !Array.isArray(state.liveWorkflowInventory.versions) ||
      !Array.isArray(workflow.aliases) || workflow.aliases.length !== 0 ||
      typeof workflow.checksum !== "string" || !/^[0-9a-f]{64}$/.test(workflow.checksum)
    ) {
      return null;
    }
    return {
      expectedChecksum: workflow.checksum,
      expectedAliases: [],
    };
  }

  function validateWorkflowPromotion(result, workflow) {
    return isObject(result) &&
      result.schema_version === WORKFLOW_PROMOTION_SCHEMA &&
      hasExactKeys(result, ["schema_version", "workflow_id", "version", "alias", "status", "checksum"]) &&
      result.workflow_id === workflow.workflow_id &&
      result.version === workflow.version &&
      result.alias === "production" &&
      result.status === "promoted" &&
      typeof result.checksum === "string" && /^[0-9a-f]{64}$/.test(result.checksum);
  }

  function validateWorkflowDeprecation(result, workflow) {
    return isObject(result) &&
      result.schema_version === WORKFLOW_DEPRECATION_SCHEMA &&
      hasExactKeys(result, ["schema_version", "workflow_id", "version", "status", "checksum"]) &&
      result.workflow_id === workflow.workflow_id &&
      result.version === workflow.version &&
      result.status === "deprecated" &&
      result.checksum === workflow.checksum &&
      typeof result.checksum === "string" && /^[0-9a-f]{64}$/.test(result.checksum);
  }

  function selectedLiveSchedule() {
    if (
      !isLiveSnapshot() ||
      !state.selected ||
      state.selected.kind !== "schedule" ||
      !state.selected.value
    ) {
      return null;
    }
    const schedule = state.selected.value;
    if (!isSafeScheduleRef(schedule.schedule_id)) {
      return null;
    }
    return schedule;
  }

  function isSafeScheduleRef(value) {
    return typeof value === "string" && /^[A-Za-z0-9_.-]{1,128}$/.test(value);
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

  function validateRecurringScheduleDispatchPage(page, scheduleId) {
    const statuses = ["claimed", "completed", "failed", "skipped", "uncertain", "other"];
    const dispatchFields = [
      "coalesced_occurrences", "completed_at", "dispatch_id", "error_type",
      "run_id", "scheduled_for", "schedule_id", "status", "trigger_id",
    ];
    if (
      !isObject(page) ||
      page.schema_version !== SCHEDULE_DISPATCH_PAGE_SCHEMA ||
      !hasExactKeys(page, ["schema_version", "schedule_id", "summary", "dispatches", "window"]) ||
      page.schedule_id !== scheduleId ||
      !isObject(page.summary) ||
      !hasExactKeys(page.summary, ["total", "status_counts"]) ||
      !isNonNegativeInteger(page.summary.total) ||
      !isObject(page.summary.status_counts) ||
      Object.keys(page.summary.status_counts).sort().join(",") !== statuses.slice().sort().join(",") ||
      Object.values(page.summary.status_counts).some(function (value) { return !isNonNegativeInteger(value); }) ||
      Object.values(page.summary.status_counts).reduce(function (total, value) { return total + value; }, 0) !== page.summary.total ||
      !Array.isArray(page.dispatches) ||
      page.dispatches.length > 100 ||
      !isObject(page.window) ||
      !hasExactKeys(page.window, ["max_items", "total", "returned", "has_more", "next_cursor"]) ||
      page.window.max_items !== 100 ||
      !isNonNegativeInteger(page.window.total) ||
      !isNonNegativeInteger(page.window.returned) ||
      page.window.returned !== page.dispatches.length ||
      page.window.returned > page.window.total ||
      page.window.returned > page.window.max_items ||
      typeof page.window.has_more !== "boolean" ||
      typeof page.window.next_cursor !== "string" ||
      page.window.next_cursor.length > 512 ||
      (page.window.next_cursor && !isSafeDispatchCursor(page.window.next_cursor)) ||
      page.window.has_more !== Boolean(page.window.next_cursor) ||
      page.window.total !== page.summary.total
    ) {
      return false;
    }
    return page.dispatches.every(function (dispatch) {
      return isObject(dispatch) &&
        Object.keys(dispatch).sort().join(",") === dispatchFields.slice().sort().join(",") &&
        isSafeWorkflowRef(dispatch.dispatch_id) &&
        dispatch.schedule_id === scheduleId &&
        isStringAtMost(dispatch.run_id, 128) &&
        isStringAtMost(dispatch.trigger_id, 128) &&
        isStringAtMost(dispatch.scheduled_for, 256) &&
        isStringAtMost(dispatch.completed_at, 256) &&
        statuses.indexOf(dispatch.status) !== -1 &&
        isStringAtMost(dispatch.error_type, 64) &&
        isNonNegativeInteger(dispatch.coalesced_occurrences);
    });
  }

  function validateRecurringScheduleDispatchReview(review, schedule, dispatch) {
    return isObject(review) &&
      review.schema_version === SCHEDULE_DISPATCH_REVIEW_SCHEMA &&
      hasExactKeys(review, [
        "schema_version", "dispatch_id", "schedule_id", "scheduled_for", "status",
        "expected_completed_at", "outcome", "reviewed_at", "changed",
      ]) &&
      review.dispatch_id === dispatch.dispatch_id &&
      review.schedule_id === schedule.schedule_id &&
      review.scheduled_for === dispatch.scheduled_for &&
      review.status === "uncertain" &&
      isBoundedString(review.expected_completed_at, 64) &&
      review.expected_completed_at === dispatch.completed_at &&
      ["effect_confirmed", "effect_not_observed", "no_conclusion"].indexOf(review.outcome) !== -1 &&
      isBoundedString(review.reviewed_at, 256) &&
      typeof review.changed === "boolean";
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
        validateWorkflowAliases(version.aliases) &&
        isChecksum(version.checksum)
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

  function validateWorkflowDiff(diff, selected, targetVersion) {
    const sections = ["workflow", "entry", "input_schema", "policies", "nodes", "edges", "other"];
    if (
      !isObject(diff) ||
      diff.schema_version !== WORKFLOW_DIFF_SCHEMA ||
      !hasExactKeys(diff, ["schema_version", "workflow_id", "from", "to", "changed", "changes"]) ||
      diff.workflow_id !== selected.workflow_id ||
      typeof diff.changed !== "boolean" ||
      !isObject(diff.from) ||
      !hasExactKeys(diff.from, ["version", "status", "checksum", "aliases"]) ||
      diff.from.version !== selected.version ||
      !isPublishedOrDeprecated(diff.from.status) ||
      !isChecksum(diff.from.checksum) ||
      !validateWorkflowAliases(diff.from.aliases) ||
      !isObject(diff.to) ||
      !hasExactKeys(diff.to, ["version", "status", "checksum", "aliases"]) ||
      diff.to.version !== targetVersion ||
      !isPublishedOrDeprecated(diff.to.status) ||
      !isChecksum(diff.to.checksum) ||
      !validateWorkflowAliases(diff.to.aliases) ||
      !isObject(diff.changes) ||
      !hasExactKeys(diff.changes, [
        "sections", "workflow_changed", "entry_changed", "input_schema_changed",
        "policies_changed", "other_changed", "nodes", "edges",
      ]) ||
      !Array.isArray(diff.changes.sections) ||
      diff.changes.sections.length > sections.length ||
      diff.changes.sections.some(function (section) { return sections.indexOf(section) === -1; }) ||
      !isUnique(diff.changes.sections) ||
      !["workflow_changed", "entry_changed", "input_schema_changed", "policies_changed", "other_changed"].every(function (field) {
        return typeof diff.changes[field] === "boolean";
      }) ||
      !validateDiffNames(diff.changes.nodes) ||
      !validateDiffNames(diff.changes.edges)
    ) {
      return false;
    }
    const changedSections = {
      workflow: diff.changes.workflow_changed,
      entry: diff.changes.entry_changed,
      input_schema: diff.changes.input_schema_changed,
      policies: diff.changes.policies_changed,
      nodes: diff.changes.nodes.added.length > 0 || diff.changes.nodes.removed.length > 0 || diff.changes.nodes.changed.length > 0,
      edges: diff.changes.edges.added.length > 0 || diff.changes.edges.removed.length > 0 || diff.changes.edges.changed.length > 0,
      other: diff.changes.other_changed,
    };
    return sections.every(function (section) {
      return diff.changes.sections.indexOf(section) !== -1 === changedSections[section];
    }) && diff.changed === diff.changes.sections.length > 0;
  }

  function isPublishedOrDeprecated(status) {
    return status === "published" || status === "deprecated";
  }

  function isChecksum(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function validateWorkflowAliases(aliases) {
    return Array.isArray(aliases) && aliases.length <= 16 && aliases.every(function (alias) {
      return isBoundedString(alias, 64);
    }) && isSortedUnique(aliases);
  }

  function validateDiffNames(change) {
    return isObject(change) && hasExactKeys(change, ["added", "removed", "changed"]) &&
      ["added", "removed", "changed"].every(function (field) {
        return Array.isArray(change[field]) && change[field].length <= 1000 &&
          change[field].every(function (name) { return isBoundedString(name, 128); }) &&
          isSortedUnique(change[field]);
      });
  }

  function isSortedUnique(values) {
    return values.every(function (value, index) {
      return index === 0 || values[index - 1] < value;
    });
  }

  function isUnique(values) {
    return new Set(values).size === values.length;
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

  function validateWorkflowPreflight(report, selected, inputProvided) {
    const expectedInputProvided = Boolean(inputProvided);
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
      report.input.provided !== expectedInputProvided ||
      (!expectedInputProvided && report.input.provided_property_count !== 0) ||
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

  function isSafeDispatchCursor(cursor) {
    return typeof cursor === "string" && /^[A-Za-z0-9_-]{1,512}$/.test(cursor);
  }

  async function decideSelectedRun(approved) {
    const run = selectedWaitingRun();
    if (!run || state.humanGateLoading || state.liveRunActionConflict) {
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
    state.liveRunActionConflict = false;
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
        if (response.status === 409) {
          state.liveRunActionConflict = true;
          throw new Error("run action target changed");
        }
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
      setStatus(
        error && error.message === "run action target changed"
          ? "Run changed"
          : "Unavailable",
        "is-invalid",
      );
    } finally {
      state.humanGateLoading = false;
      renderHumanGateActions();
    }
  }

  async function cancelSelectedRun() {
    const run = selectedCancellableRun();
    if (!run || state.runCancelLoading || state.liveRunActionConflict) {
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
    state.liveRunActionConflict = false;
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
        if (response.status === 409) {
          state.liveRunActionConflict = true;
          throw new Error("run action target changed");
        }
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
      setStatus(
        error && error.message === "run action target changed"
          ? "Run changed"
          : "Unavailable",
        "is-invalid",
      );
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
        updateWorkflowReleaseControls();
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
      updateWorkflowReleaseControls();
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
      updateWorkflowReleaseControls();
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
    const previousWorkflow =
      state.sourceLabel === "Live Service Snapshot" &&
      state.selected && state.selected.kind === "live workflow" && state.selected.value &&
      isSafeWorkflowRef(state.selected.value.workflow_id) &&
      isSafeWorkflowRef(state.selected.value.version)
        ? {
          workflow_id: state.selected.value.workflow_id,
          version: state.selected.value.version,
        }
        : null;
    const previousTriggeredRun = previousWorkflow && state.liveWorkflowTriggeredRun &&
      state.liveWorkflowTriggeredRun.key === previousWorkflow.workflow_id + "@" + previousWorkflow.version
      ? state.liveWorkflowTriggeredRun
      : null;
    state.snapshot = snapshot;
    state.sourceLabel = label;
    state.liveRunDetail = null;
    state.liveRunDetailId = "";
    state.liveRunDetailLoading = false;
    state.liveRunDetailError = false;
    state.liveRunActionConflict = false;
    state.runCancelLoading = false;
    state.liveWorkflowExplanation = null;
    state.liveWorkflowExplanationKey = "";
    state.liveWorkflowExplanationLoading = false;
    state.liveWorkflowExplanationError = false;
    state.liveWorkflowDiff = null;
    state.liveWorkflowDiffKey = "";
    state.liveWorkflowDiffLoading = false;
    state.liveWorkflowDiffError = false;
    state.liveWorkflowPreflight = null;
    state.liveWorkflowPreflightKey = "";
    state.liveWorkflowPreflightLoading = false;
    state.liveWorkflowPreflightError = false;
    state.liveWorkflowEmptyTriggerAttempt = null;
    state.liveWorkflowEmptyTriggerLoading = false;
    state.liveWorkflowEmptyTriggerError = false;
    state.liveWorkflowInputCandidate = null;
    state.liveWorkflowInputPreflightLoading = false;
    state.liveWorkflowInputTriggerAttempt = null;
    state.liveWorkflowInputTriggerLoading = false;
    state.liveWorkflowInputTriggerError = false;
    state.liveWorkflowTriggeredRun = null;
    state.liveWorkflowPromotionLoading = false;
    state.liveWorkflowPromotionError = false;
    state.liveWorkflowPromotionConflict = false;
    state.liveWorkflowDeprecationLoading = false;
    state.liveWorkflowDeprecationError = false;
    state.liveWorkflowDeprecationConflict = false;
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
    state.liveScheduleDispatchPage = null;
    state.liveScheduleDispatchRows = null;
    state.liveScheduleDispatchScheduleId = "";
    state.liveScheduleDispatchCursor = "";
    state.liveScheduleDispatchHasMore = false;
    state.liveScheduleDispatchLoading = false;
    state.liveScheduleDispatchError = false;
    state.liveScheduleDispatchReviewLoading = false;
    state.liveScheduleDispatchReviewError = false;
    state.liveScheduleDispatchReviewConflict = false;
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
      state.liveWorkflowReleaseCandidate = null;
      state.liveWorkflowReleaseLoading = false;
      state.liveWorkflowReleaseError = false;
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
    if (label === "Live Service Snapshot" && previousWorkflow && state.liveWorkflowInventory) {
      const refreshedWorkflow = state.liveWorkflowInventory.versions.find(function (workflow) {
        return workflow && workflow.workflow_id === previousWorkflow.workflow_id &&
          workflow.version === previousWorkflow.version;
      });
      if (refreshedWorkflow) {
        state.selected = { kind: "live workflow", value: refreshedWorkflow };
        state.liveWorkflowTriggeredRun = previousTriggeredRun;
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
    updateWorkflowReleaseControls();
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
    state.liveRunActionConflict = false;
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
    state.liveScheduleDispatchPage = null;
    state.liveScheduleDispatchRows = null;
    state.liveScheduleDispatchScheduleId = "";
    state.liveScheduleDispatchCursor = "";
    state.liveScheduleDispatchHasMore = false;
    state.liveScheduleDispatchLoading = false;
    state.liveScheduleDispatchError = false;
    state.liveReadiness = null;
    state.liveReadinessLoading = false;
    state.liveWorkflowInventory = null;
    state.liveWorkflowInventoryLoading = false;
    state.liveWorkflowExplanation = null;
    state.liveWorkflowExplanationKey = "";
    state.liveWorkflowExplanationLoading = false;
    state.liveWorkflowExplanationError = false;
    state.liveWorkflowPromotionLoading = false;
    state.liveWorkflowPromotionError = false;
    state.liveWorkflowPromotionConflict = false;
    state.liveWorkflowDeprecationLoading = false;
    state.liveWorkflowDeprecationError = false;
    state.liveWorkflowDeprecationConflict = false;
    state.liveWorkflowDiff = null;
    state.liveWorkflowDiffKey = "";
    state.liveWorkflowDiffLoading = false;
    state.liveWorkflowDiffError = false;
    state.liveWorkflowPreflight = null;
    state.liveWorkflowPreflightKey = "";
    state.liveWorkflowPreflightLoading = false;
    state.liveWorkflowPreflightError = false;
    state.liveWorkflowEmptyTriggerAttempt = null;
    state.liveWorkflowEmptyTriggerLoading = false;
    state.liveWorkflowEmptyTriggerError = false;
    state.liveWorkflowInputCandidate = null;
    state.liveWorkflowInputPreflightLoading = false;
    state.liveWorkflowInputTriggerAttempt = null;
    state.liveWorkflowInputTriggerLoading = false;
    state.liveWorkflowInputTriggerError = false;
    state.liveWorkflowTriggeredRun = null;
    state.liveWorkflowReleaseCandidate = null;
    state.liveWorkflowReleaseLoading = false;
    state.liveWorkflowReleaseError = false;
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
        state.liveWorkflowDiff = null;
        state.liveWorkflowDiffKey = "";
        state.liveWorkflowDiffLoading = false;
        state.liveWorkflowDiffError = false;
        state.liveWorkflowPreflight = null;
        state.liveWorkflowPreflightKey = "";
        state.liveWorkflowPreflightLoading = false;
        state.liveWorkflowPreflightError = false;
        state.liveWorkflowEmptyTriggerAttempt = null;
        state.liveWorkflowEmptyTriggerLoading = false;
        state.liveWorkflowEmptyTriggerError = false;
        state.liveWorkflowInputCandidate = null;
        state.liveWorkflowInputPreflightLoading = false;
        state.liveWorkflowInputTriggerAttempt = null;
        state.liveWorkflowInputTriggerLoading = false;
        state.liveWorkflowInputTriggerError = false;
        state.liveWorkflowTriggeredRun = null;
        state.liveWorkflowPromotionLoading = false;
        state.liveWorkflowPromotionError = false;
        state.liveWorkflowPromotionConflict = false;
        state.liveWorkflowDeprecationLoading = false;
        state.liveWorkflowDeprecationError = false;
        state.liveWorkflowDeprecationConflict = false;
        state.liveScheduleDispatchPage = null;
        state.liveScheduleDispatchRows = null;
        state.liveScheduleDispatchScheduleId = "";
        state.liveScheduleDispatchCursor = "";
        state.liveScheduleDispatchHasMore = false;
        state.liveScheduleDispatchLoading = false;
        state.liveScheduleDispatchError = false;
        state.liveScheduleDispatchReviewLoading = false;
        state.liveScheduleDispatchReviewError = false;
        state.liveScheduleDispatchReviewConflict = false;
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
    renderScheduleDispatchActions();
    renderRunDetailStatus(selected);
  }

  function renderScheduleDispatchActions() {
    const schedule = selectedLiveSchedule();
    const visible = Boolean(schedule);
    els.scheduleDispatchActions.hidden = !visible;
    renderLiveScheduleDispatchReviewChoices(schedule);
    updateLiveScheduleDispatchControls();
    if (!visible) {
      setScheduleDispatchStatus("Select a live schedule to inspect dispatch evidence.", "");
      return;
    }
    if (state.liveScheduleDispatchLoading && state.liveScheduleDispatchScheduleId === schedule.schedule_id) {
      setScheduleDispatchStatus(
        state.liveScheduleDispatchCursor ? "Loading older dispatch evidence…" : "Loading bounded dispatch evidence…",
        "",
      );
    } else if (state.liveScheduleDispatchError && state.liveScheduleDispatchScheduleId === schedule.schedule_id) {
      setScheduleDispatchStatus("Dispatch evidence unavailable; schedule metadata remains visible.", "is-invalid");
    } else if (state.liveScheduleDispatchPage && state.liveScheduleDispatchScheduleId === schedule.schedule_id) {
      const uncertain = state.liveScheduleDispatchPage.summary.status_counts.uncertain;
      setScheduleDispatchStatus(
        "Loaded " + state.liveScheduleDispatchRows.length + " retained records; " + uncertain + " uncertain in the reported total.",
        uncertain ? "is-invalid" : "is-valid",
      );
    } else {
      setScheduleDispatchStatus("Load bounded redacted dispatch outcomes; no replay or mutation is available.", "");
    }
  }

  function renderLiveScheduleDispatchReviewChoices(schedule) {
    const current = els.scheduleDispatchReviewTarget.value;
    els.scheduleDispatchReviewTarget.replaceChildren();
    const uncertain = schedule && state.liveScheduleDispatchRows
      ? state.liveScheduleDispatchRows.filter(function (dispatch) {
        return dispatch && dispatch.schedule_id === schedule.schedule_id && dispatch.status === "uncertain";
      })
      : [];
    uncertain.forEach(function (dispatch) {
      const option = document.createElement("option");
      option.value = dispatch.dispatch_id;
      option.textContent = dispatch.dispatch_id + " (" + (dispatch.completed_at || "no completion time") + ")";
      els.scheduleDispatchReviewTarget.appendChild(option);
    });
    if (uncertain.some(function (dispatch) { return dispatch.dispatch_id === current; })) {
      els.scheduleDispatchReviewTarget.value = current;
    }
    updateLiveScheduleDispatchReviewControls();
  }

  async function reviewLiveScheduleDispatch() {
    const schedule = selectedLiveSchedule();
    const dispatchId = els.scheduleDispatchReviewTarget.value;
    const outcome = els.scheduleDispatchReviewOutcome.value;
    const dispatch = state.liveScheduleDispatchRows && state.liveScheduleDispatchRows.find(function (item) {
      return item && item.dispatch_id === dispatchId && item.schedule_id === (schedule && schedule.schedule_id);
    });
    if (
      !schedule || !dispatch || dispatch.status !== "uncertain" ||
      !isBoundedString(dispatch.completed_at, 64) ||
      ["effect_confirmed", "effect_not_observed", "no_conclusion"].indexOf(outcome) === -1 ||
      state.liveScheduleDispatchReviewLoading
    ) {
      return;
    }
    if (typeof window.confirm === "function" && !window.confirm(
      "Record a review for this uncertain dispatch? This does not replay or mutate the dispatch."
    )) {
      return;
    }
    state.liveScheduleDispatchReviewLoading = true;
    state.liveScheduleDispatchReviewError = false;
    state.liveScheduleDispatchReviewConflict = false;
    updateLiveScheduleDispatchReviewControls();
    setScheduleDispatchReviewStatus("Recording the compare-and-swap review…", "");
    try {
      const response = await fetch(
        LIVE_SCHEDULE_DISPATCH_REVIEW_PREFIX + encodeURIComponent(dispatchId),
        {
          method: "POST",
          cache: "no-store",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ expected_completed_at: dispatch.completed_at, outcome: outcome }),
        },
      );
      if (!response.ok) {
        if (response.status === 409) {
          state.liveScheduleDispatchReviewConflict = true;
          throw new Error("dispatch review target changed");
        }
        throw new Error("dispatch review unavailable");
      }
      const review = await response.json();
      if (!validateRecurringScheduleDispatchReview(review, schedule, dispatch)) {
        throw new Error("dispatch review unavailable");
      }
      setScheduleDispatchReviewStatus(
        "Review recorded; dispatch remains uncertain and was not replayed.",
        "is-valid",
      );
      setStatus("Reviewed", "is-valid");
      await loadLiveScheduleDispatches({ reset: true });
    } catch (error) {
      state.liveScheduleDispatchReviewError = true;
      setScheduleDispatchReviewStatus(
        error && error.message === "dispatch review target changed"
          ? "Dispatch review changed; Load Dispatch Evidence before another review."
          : "Review unavailable; dispatch state was not replayed.",
        "is-invalid",
      );
    } finally {
      state.liveScheduleDispatchReviewLoading = false;
      updateLiveScheduleDispatchReviewControls();
    }
  }

  function renderWorkflowExplanationActions() {
    const workflow = selectedLiveWorkflow();
    const visible = Boolean(workflow);
    els.workflowExplanationActions.hidden = !visible;
    renderWorkflowDiffChoices(workflow);
    updateWorkflowPromotionControls();
    updateWorkflowDeprecationControls();
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
      setWorkflowEmptyTriggerStatus("A successful empty preflight is required before a confirmed start.", "");
      setWorkflowInputTriggerStatus("Stage a non-secret JSON object; it is retained as durable run context if started.", "");
      setWorkflowRunHandoffStatus("After an accepted trigger, review its bounded redacted run evidence and continue through the established operator controls.", "");
      setWorkflowDiffStatus("Select another version of this workflow to review a structural diff.", "");
      setWorkflowPromotionStatus("Select a published version that is not already the production target.", "");
      setWorkflowDeprecationStatus("Select a published version with no active alias before deprecating it.", "");
      updateWorkflowEmptyTriggerControls();
      updateWorkflowInputTriggerControls();
      updateWorkflowRunHandoffControls();
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
    updateWorkflowEmptyTriggerControls();
    const emptyTarget = liveEmptyTriggerTarget();
    if (state.liveWorkflowEmptyTriggerLoading) {
      setWorkflowEmptyTriggerStatus("Starting the confirmed empty trigger…", "");
    } else if (state.liveWorkflowEmptyTriggerError && emptyTarget) {
      setWorkflowEmptyTriggerStatus("Start outcome is unavailable; retry uses the same idempotency key and never changes input.", "is-invalid");
    } else if (emptyTarget && state.liveWorkflowEmptyTriggerAttempt && state.liveWorkflowEmptyTriggerAttempt.receipt) {
      const receipt = state.liveWorkflowEmptyTriggerAttempt.receipt;
      setWorkflowEmptyTriggerStatus("Empty trigger accepted as " + receipt.run_id + " (" + receipt.run_status + ").", "is-valid");
    } else if (!emptyTarget && workflow.status !== "published") {
      setWorkflowEmptyTriggerStatus("Only published versions can start an empty trigger.", "");
    } else if (!emptyTarget) {
      setWorkflowEmptyTriggerStatus("Run Check Empty Trigger first; it must report ready before a confirmed start.", "");
    } else {
      setWorkflowEmptyTriggerStatus("This starts only the checked empty input after an explicit confirmation.", "");
    }
    updateWorkflowInputTriggerControls();
    const inputCandidate = state.liveWorkflowInputCandidate;
    const inputTarget = liveInputTriggerTarget();
    if (state.liveWorkflowInputTriggerLoading) {
      setWorkflowInputTriggerStatus("Starting the confirmed staged input…", "");
    } else if (state.liveWorkflowInputTriggerError && inputTarget) {
      setWorkflowInputTriggerStatus("Start outcome is unavailable; retry uses the same key and unchanged staged input.", "is-invalid");
    } else if (inputTarget && state.liveWorkflowInputTriggerAttempt && state.liveWorkflowInputTriggerAttempt.receipt) {
      const inputReceipt = state.liveWorkflowInputTriggerAttempt.receipt;
      setWorkflowInputTriggerStatus("Staged input accepted as " + inputReceipt.run_id + " (" + inputReceipt.run_status + ").", "is-valid");
    } else if (workflow.status !== "published") {
      setWorkflowInputTriggerStatus("Only published versions can stage and start trigger input.", "");
    } else if (!inputCandidate || inputCandidate.key !== key) {
      setWorkflowInputTriggerStatus("Stage a non-secret JSON object; it is retained as durable run context if started.", "");
    } else if (state.liveWorkflowInputPreflightLoading) {
      setWorkflowInputTriggerStatus("Checking staged input without executing…", "");
    } else if (!inputCandidate.preflight) {
      setWorkflowInputTriggerStatus("Input is staged in browser memory; check it before starting.", "");
    } else if (!inputCandidate.preflight.ready) {
      setWorkflowInputTriggerStatus("Staged input is blocked; no run can be started.", "is-invalid");
    } else {
      setWorkflowInputTriggerStatus("Staged input is ready; explicit confirmation is still required.", "is-valid");
    }
    const triggeredRun = liveWorkflowTriggeredRunTarget();
    updateWorkflowRunHandoffControls();
    if (triggeredRun) {
      setWorkflowRunHandoffStatus(
        "Accepted run " + triggeredRun.run_id + " is ready for bounded redacted review.",
        "is-valid",
      );
    } else {
      setWorkflowRunHandoffStatus("After an accepted trigger, review its bounded redacted run evidence and continue through the established operator controls.", "");
    }
    const diffKey = workflow.workflow_id + "@" + workflow.version + "@" + els.workflowDiffTarget.value;
    if (state.liveWorkflowDiffLoading && state.liveWorkflowDiffKey === diffKey) {
      setWorkflowDiffStatus("Loading bounded structural diff…", "");
    } else if (state.liveWorkflowDiffError && state.liveWorkflowDiffKey === diffKey) {
      setWorkflowDiffStatus("Workflow diff unavailable; version metadata remains visible.", "is-invalid");
    } else if (state.liveWorkflowDiff && state.liveWorkflowDiffKey === diffKey) {
      setWorkflowDiffStatus("Structural diff loaded; no connector, credential, or workflow execution was invoked.", "is-valid");
    } else if (!els.workflowDiffTarget.value) {
      setWorkflowDiffStatus("Load Live Workflows with at least two versions of this workflow first.", "");
    } else {
      setWorkflowDiffStatus("Compare release structure without exposing workflow values.", "");
    }
    const promotion = liveWorkflowPromotionTarget(workflow);
    if (state.liveWorkflowPromotionLoading) {
      setWorkflowPromotionStatus("Recording the compare-and-swap promotion…", "");
    } else if (state.liveWorkflowPromotionConflict) {
      setWorkflowPromotionStatus("Promotion target changed; Reload Live Workflows before another promotion.", "is-invalid");
    } else if (state.liveWorkflowPromotionError) {
      setWorkflowPromotionStatus("Promotion unavailable; the production alias was not assumed to change.", "is-invalid");
    } else if (!state.liveWorkflowInventory) {
      setWorkflowPromotionStatus("Load Live Workflows before changing the production alias.", "");
    } else if (workflow.status !== "published") {
      setWorkflowPromotionStatus("Only published versions can receive the production alias.", "");
    } else if (!promotion) {
      setWorkflowPromotionStatus("This version is already the production target or the alias state is ambiguous.", "");
    } else {
      setWorkflowPromotionStatus("Promotion uses the observed production target as a compare-and-swap precondition.", "");
    }
    const deprecation = liveWorkflowDeprecationTarget(workflow);
    if (state.liveWorkflowDeprecationLoading) {
      setWorkflowDeprecationStatus("Recording the checksum-and-alias compare-and-swap…", "");
    } else if (state.liveWorkflowDeprecationConflict) {
      setWorkflowDeprecationStatus("Deprecation target changed; Reload Live Workflows before another deprecation.", "is-invalid");
    } else if (state.liveWorkflowDeprecationError) {
      setWorkflowDeprecationStatus("Deprecation unavailable; the version was not assumed to change.", "is-invalid");
    } else if (!state.liveWorkflowInventory) {
      setWorkflowDeprecationStatus("Load Live Workflows before changing version status.", "");
    } else if (workflow.status !== "published") {
      setWorkflowDeprecationStatus("Only published versions can be deprecated.", "");
    } else if (!Array.isArray(workflow.aliases) || workflow.aliases.length) {
      setWorkflowDeprecationStatus("Remove every alias before deprecating a version; production remains protected.", "");
    } else if (!deprecation) {
      setWorkflowDeprecationStatus("The observed version metadata is not safe to use for deprecation.", "is-invalid");
    } else {
      setWorkflowDeprecationStatus("Deprecation uses the observed checksum and alias set as compare-and-swap guards.", "");
    }
  }

  function renderWorkflowDiffChoices(workflow) {
    const current = els.workflowDiffTarget.value;
    els.workflowDiffTarget.replaceChildren();
    const versions = workflow && state.liveWorkflowInventory && Array.isArray(state.liveWorkflowInventory.versions)
      ? state.liveWorkflowInventory.versions.filter(function (version) {
        return version && version.workflow_id === workflow.workflow_id &&
          version.version !== workflow.version && isSafeWorkflowRef(version.version);
      })
      : [];
    versions.forEach(function (version) {
      const option = document.createElement("option");
      option.value = version.version;
      option.textContent = version.version + " (" + version.status + ")";
      els.workflowDiffTarget.appendChild(option);
    });
    if (versions.some(function (version) { return version.version === current; })) {
      els.workflowDiffTarget.value = current;
    }
    updateWorkflowDiffControls(versions.length > 0);
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
    els.approveRun.disabled = !visible || state.humanGateLoading || state.runCancelLoading || state.liveRunActionConflict;
    els.rejectRun.disabled = !visible || state.humanGateLoading || state.runCancelLoading || state.liveRunActionConflict;
    if (visible) {
      els.humanGateStatus.textContent = state.humanGateLoading
        ? "Submitting the decision…"
        : state.liveRunActionConflict
        ? "Run state changed; Load Live before another run action."
        : "This run is waiting for an explicit human decision.";
    }
  }

  function renderRunCancelActions() {
    const run = selectedCancellableRun();
    const visible = Boolean(run);
    els.runCancelActions.hidden = !visible;
    els.cancelRun.disabled =
      !visible || state.runCancelLoading || state.humanGateLoading || state.liveRunActionConflict;
    if (visible) {
      els.runCancelStatus.textContent = state.runCancelLoading
        ? "Recording cooperative cancellation…"
        : state.liveRunActionConflict
        ? "Run state changed; Load Live before another run action."
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
    if (
      workflow && state.liveWorkflowEmptyTriggerAttempt &&
      state.liveWorkflowEmptyTriggerAttempt.key === workflowKey &&
      state.liveWorkflowEmptyTriggerAttempt.receipt
    ) {
      detailEnvelope.redacted_empty_trigger_receipt = state.liveWorkflowEmptyTriggerAttempt.receipt;
      hasEnvelope = true;
    }
    if (
      workflow && state.liveWorkflowInputCandidate && state.liveWorkflowInputCandidate.key === workflowKey &&
      state.liveWorkflowInputCandidate.preflight
    ) {
      detailEnvelope.redacted_staged_input_preflight = state.liveWorkflowInputCandidate.preflight;
      hasEnvelope = true;
    }
    if (
      workflow && state.liveWorkflowInputTriggerAttempt && state.liveWorkflowInputTriggerAttempt.key === workflowKey &&
      state.liveWorkflowInputTriggerAttempt.receipt
    ) {
      detailEnvelope.redacted_staged_input_receipt = state.liveWorkflowInputTriggerAttempt.receipt;
      hasEnvelope = true;
    }
    const diffKey = workflow ? workflow.workflow_id + "@" + workflow.version + "@" + els.workflowDiffTarget.value : "";
    if (workflow && state.liveWorkflowDiff && state.liveWorkflowDiffKey === diffKey) {
      detailEnvelope.redacted_workflow_diff = state.liveWorkflowDiff;
      hasEnvelope = true;
    }
    const schedule = selectedLiveSchedule();
    if (
      schedule &&
      state.liveScheduleDispatchPage &&
      state.liveScheduleDispatchScheduleId === schedule.schedule_id
    ) {
      detailEnvelope.redacted_schedule_dispatch_page = state.liveScheduleDispatchPage;
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

  function setWorkflowInputTriggerStatus(text, className) {
    els.workflowInputTriggerStatus.textContent = text;
    els.workflowInputTriggerStatus.className = className || "";
  }

  function setWorkflowRunHandoffStatus(text, className) {
    els.workflowRunHandoffStatus.textContent = text;
    els.workflowRunHandoffStatus.className = className || "";
  }

  function setWorkflowDiffStatus(text, className) {
    els.workflowDiffStatus.textContent = text;
    els.workflowDiffStatus.className = className || "";
  }

  function setWorkflowPromotionStatus(text, className) {
    els.workflowPromotionStatus.textContent = text;
    els.workflowPromotionStatus.className = className || "";
  }

  function setWorkflowDeprecationStatus(text, className) {
    els.workflowDeprecationStatus.textContent = text;
    els.workflowDeprecationStatus.className = className || "";
  }

  function setScheduleDispatchStatus(text, className) {
    els.scheduleDispatchStatus.textContent = text;
    els.scheduleDispatchStatus.className = className || "";
  }

  function setScheduleDispatchReviewStatus(text, className) {
    els.scheduleDispatchReviewStatus.textContent = text;
    els.scheduleDispatchReviewStatus.className = className || "";
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

  function updateLiveScheduleDispatchControls() {
    const schedule = selectedLiveSchedule();
    const sameSchedule = Boolean(
      schedule && state.liveScheduleDispatchScheduleId === schedule.schedule_id
    );
    const loading = state.liveScheduleDispatchLoading;
    els.loadScheduleDispatches.disabled = !schedule || loading;
    els.loadScheduleDispatches.textContent = loading && !state.liveScheduleDispatchCursor
      ? "Loading Dispatches…"
      : "Load Dispatch Evidence";
    els.loadOlderScheduleDispatches.disabled = !schedule || !sameSchedule || loading || !state.liveScheduleDispatchHasMore;
    els.loadOlderScheduleDispatches.textContent = loading && state.liveScheduleDispatchCursor
      ? "Loading Older…"
      : "Load Older Dispatches";
  }

  function updateLiveScheduleDispatchReviewControls() {
    const schedule = selectedLiveSchedule();
    const target = els.scheduleDispatchReviewTarget.value;
    const hasTarget = Boolean(
      schedule && state.liveScheduleDispatchRows && state.liveScheduleDispatchRows.some(function (dispatch) {
        return dispatch && dispatch.schedule_id === schedule.schedule_id &&
          dispatch.dispatch_id === target && dispatch.status === "uncertain";
      })
    );
    const enabled = hasTarget && [
      "effect_confirmed", "effect_not_observed", "no_conclusion",
    ].indexOf(els.scheduleDispatchReviewOutcome.value) !== -1;
    const conflict = state.liveScheduleDispatchReviewConflict;
    els.scheduleDispatchReviewTarget.disabled = !schedule || !state.liveScheduleDispatchRows || state.liveScheduleDispatchReviewLoading || conflict;
    els.scheduleDispatchReviewOutcome.disabled = !enabled || state.liveScheduleDispatchReviewLoading || conflict;
    els.reviewScheduleDispatch.disabled = !enabled || state.liveScheduleDispatchReviewLoading || conflict;
    els.reviewScheduleDispatch.textContent = state.liveScheduleDispatchReviewLoading
      ? "Recording…"
      : "Record Review";
    if (conflict) {
      setScheduleDispatchReviewStatus("Dispatch review changed; Load Dispatch Evidence before another review.", "is-invalid");
    } else if (!schedule || !hasTarget) {
      setScheduleDispatchReviewStatus("Only uncertain dispatches can receive an explicit conclusion.", "");
    } else if (!state.liveScheduleDispatchReviewLoading && !state.liveScheduleDispatchReviewError) {
      setScheduleDispatchReviewStatus("The review uses the server-provided completion timestamp and a compare-and-swap check.", "");
    }
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

  function updateWorkflowReleaseControls() {
    const enabled = state.liveModeConfigured && isLiveSnapshot();
    const loading = state.liveWorkflowReleaseLoading ||
      state.liveWorkflowReleasePreflightLoading ||
      state.liveWorkflowReleaseTargetReviewLoading;
    els.workflowReleaseFile.disabled = !enabled || loading;
    els.workflowReleaseFileAction.classList.toggle("is-disabled", !enabled || loading);
    els.workflowReleaseFileAction.setAttribute("aria-disabled", String(!enabled || loading));
    const candidate = state.liveWorkflowReleaseCandidate;
    els.preflightStagedWorkflow.disabled = !enabled || !candidate || loading;
    els.preflightStagedWorkflow.textContent = state.liveWorkflowReleasePreflightLoading
      ? "Checking Staged Workflow…"
      : "Check Staged Workflow";
    els.reviewStagedWorkflowTarget.disabled = !enabled || !candidate ||
      !candidate.preflight || loading;
    els.reviewStagedWorkflowTarget.textContent = state.liveWorkflowReleaseTargetReviewLoading
      ? "Reviewing Publish Target…"
      : "Review Publish Target";
    els.publishWorkflow.disabled = !enabled || !candidate || !candidate.preflight ||
      !candidate.targetReview || !candidate.targetReview.publication_ready || loading;
    els.publishWorkflow.textContent = state.liveWorkflowReleaseLoading
      ? "Publishing Workflow…"
      : "Publish Staged Workflow";
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
    updateWorkflowEmptyTriggerControls();
  }

  function updateWorkflowEmptyTriggerControls() {
    const target = liveEmptyTriggerTarget();
    const loading = state.liveWorkflowEmptyTriggerLoading || state.liveWorkflowPreflightLoading;
    const retry = Boolean(target && state.liveWorkflowEmptyTriggerError &&
      state.liveWorkflowEmptyTriggerAttempt &&
      state.liveWorkflowEmptyTriggerAttempt.key === target.key &&
      state.liveWorkflowEmptyTriggerAttempt.receipt === null);
    els.triggerWorkflowEmpty.disabled = !target || loading;
    els.triggerWorkflowEmpty.textContent = state.liveWorkflowEmptyTriggerLoading
      ? "Starting Empty Trigger…"
      : retry
      ? "Retry Empty Trigger"
      : "Start Empty Trigger";
  }

  function updateWorkflowInputTriggerControls() {
    const workflow = selectedLiveWorkflow();
    const key = workflow ? workflow.workflow_id + "@" + workflow.version : "";
    const candidate = state.liveWorkflowInputCandidate;
    const published = Boolean(workflow && workflow.status === "published");
    const loading = state.liveWorkflowInputPreflightLoading || state.liveWorkflowInputTriggerLoading;
    const candidateCurrent = Boolean(candidate && candidate.key === key);
    const ready = Boolean(candidateCurrent && candidate.preflight && candidate.preflight.ready === true);
    const retry = Boolean(
      ready && state.liveWorkflowInputTriggerError && state.liveWorkflowInputTriggerAttempt &&
      state.liveWorkflowInputTriggerAttempt.key === key &&
      state.liveWorkflowInputTriggerAttempt.candidate === candidate &&
      state.liveWorkflowInputTriggerAttempt.receipt === null
    );
    els.workflowInputTriggerActions.hidden = !workflow;
    els.workflowInputFile.disabled = !published || loading;
    els.workflowInputFileAction.classList.toggle("is-disabled", !published || loading);
    els.workflowInputFileAction.setAttribute("aria-disabled", String(!published || loading));
    els.preflightWorkflowInput.disabled = !published || !candidateCurrent || loading;
    els.preflightWorkflowInput.textContent = state.liveWorkflowInputPreflightLoading
      ? "Checking Staged Input…"
      : "Check Staged Input";
    els.triggerWorkflowInput.disabled = !ready || loading;
    els.triggerWorkflowInput.textContent = state.liveWorkflowInputTriggerLoading
      ? "Starting Staged Input…"
      : retry
      ? "Retry Staged Input"
      : "Start Staged Input";
  }

  function updateWorkflowRunHandoffControls() {
    const workflow = selectedLiveWorkflow();
    const receipt = liveWorkflowTriggeredRunTarget();
    els.workflowRunHandoffActions.hidden = !workflow;
    els.reviewTriggeredRun.disabled = !receipt || state.liveRunDetailLoading;
  }

  function updateWorkflowDiffControls(hasTarget) {
    const workflow = selectedLiveWorkflow();
    const available = typeof hasTarget === "boolean"
      ? hasTarget
      : Boolean(workflow && els.workflowDiffTarget.value);
    els.workflowDiffTarget.disabled = !workflow || !available || state.liveWorkflowDiffLoading;
    els.loadWorkflowDiff.disabled = !workflow || !available || state.liveWorkflowDiffLoading;
    els.loadWorkflowDiff.textContent = state.liveWorkflowDiffLoading
      ? "Comparing…"
      : "Compare Versions";
  }

  function updateWorkflowPromotionControls() {
    const workflow = selectedLiveWorkflow();
    const target = liveWorkflowPromotionTarget(workflow);
    els.promoteWorkflow.disabled = !target || state.liveWorkflowPromotionLoading || state.liveWorkflowPromotionConflict;
    els.promoteWorkflow.textContent = state.liveWorkflowPromotionLoading
      ? "Promoting…"
      : "Promote to production";
  }

  function updateWorkflowDeprecationControls() {
    const workflow = selectedLiveWorkflow();
    const target = liveWorkflowDeprecationTarget(workflow);
    els.deprecateWorkflow.disabled = !target || state.liveWorkflowDeprecationLoading || state.liveWorkflowDeprecationConflict;
    els.deprecateWorkflow.textContent = state.liveWorkflowDeprecationLoading
      ? "Deprecating…"
      : "Deprecate version";
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
