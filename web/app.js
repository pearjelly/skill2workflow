(function () {
  const GRAPH_VERSION = "skill2workflow-litegraph-0.1.0";
  const SKILL_COMPILE_URL = "/api/v1/skill-compiles";
  const SKILL_COMPILE_REVIEW_SCHEMA_VERSION = "skill2workflow-skill-compile-review-0.1.0";
  const WORKFLOW_VALIDATION_URL = "/api/v1/workflow-validations";
  const WORKFLOW_VALIDATION_SCHEMA_VERSION = "skill2workflow-local-workflow-validation-0.1.0";
  const MAX_SKILL_INPUT_BYTES = 2 * 1024 * 1024;
  const MAX_SKILL_COMPILE_REVIEW_COUNT = 10000;
  const MAX_WORKFLOW_VALIDATION_ERROR_COUNT = 100000;
  const MAX_WORKFLOW_VALIDATION_ERRORS = 100;
  const MAX_WORKFLOW_VALIDATION_NODE_INDEX = 100000;
  const SKILL_COMPILE_REVIEW_NOTICES = {
    checklist_not_found: "No checklist steps were found. This draft uses the compiler's generic review step.",
    human_gate_not_inferred: "No human approval node was inferred. Add an explicit review before real-world effects.",
    verification_not_inferred: "No verification node was inferred. Add a confirmation or validation step before relying on the result.",
  };
  const NODE_TYPES = ["start", "step", "human_gate", "tool_call", "verification", "instruction", "failure", "end"];
  const TYPE_THEME = {
    start: { color: "#1769aa", background: "#eaf4fc" },
    step: { color: "#3b5b92", background: "#edf2fb" },
    human_gate: { color: "#8a5a00", background: "#fff4dc" },
    tool_call: { color: "#00796b", background: "#e7f6f3" },
    verification: { color: "#5d3fd3", background: "#f0edff" },
    instruction: { color: "#4f5b66", background: "#eef1f4" },
    failure: { color: "#b42318", background: "#fdeceb" },
    end: { color: "#087443", background: "#e9f7ef" },
  };
  const STATUS_THEME = {
    not_started: "#7d8794",
    running: "#1769aa",
    waiting: "#a15c07",
    completed: "#087443",
    approved: "#087443",
    rejected: "#b42318",
    failed: "#b42318",
    cancelled: "#5d6673",
    interrupted: "#b42318",
  };
  const TERMINAL_TYPES = new Set(["end", "failure"]);
  const EXAMPLES = {
    "approval-flow.workflow.json": "../examples/workflows/approval-flow.workflow.json",
    "sales-follow-up.workflow.json": "../examples/workflows/sales-follow-up.workflow.json",
    "customer-service-escalation.workflow.json": "../examples/workflows/customer-service-escalation.workflow.json",
    "risk-review.workflow.json": "../examples/workflows/risk-review.workflow.json",
    "operations-analysis.workflow.json": "../examples/workflows/operations-analysis.workflow.json",
    "http-connector.workflow.json": "../examples/workflows/http-connector.workflow.json",
  };

  let graph;
  let canvas;
  let selectedNode = null;
  let currentWorkflow = {};
  let currentWorkflowDsl = null;
  let validationErrors = [];
  let stagedSkillMarkdown = null;
  let skillCompileLoading = false;

  const els = {};

  window.addEventListener("DOMContentLoaded", init);

  function init() {
    cacheElements();
    if (!window.LiteGraph || !window.LGraph || !window.LGraphCanvas) {
      setStatus("LiteGraph unavailable", "invalid");
      return;
    }

    registerNodeTypes();
    graph = new LGraph();
    canvas = new LGraphCanvas(els.canvas, graph);
    canvas.background_image = "";
    canvas.render_canvas_border = false;
    canvas.onNodeSelected = function (node) {
      renderInspector(node);
    };
    canvas.onNodeDeselected = function () {
      renderInspector(null);
    };
    window.skill2workflowEditor = {
      get graph() {
        return graph;
      },
      get canvas() {
        return canvas;
      },
      validateGraph: validateGraph,
      toWorkflowDsl: function () {
        return currentWorkflowDsl ? workflowDslFromGraph() : null;
      },
    };

    bindEvents();
    resizeCanvas();
    graph.start();
    loadSample();
  }

  function cacheElements() {
    els.canvas = document.getElementById("graph-canvas");
    els.exampleSelect = document.getElementById("example-select");
    els.loadSample = document.getElementById("load-sample");
    els.fileInput = document.getElementById("file-input");
    els.skillInput = document.getElementById("skill-input");
    els.compileSkill = document.getElementById("compile-skill");
    els.fitView = document.getElementById("fit-view");
    els.validateGraph = document.getElementById("validate-graph");
    els.saveWorkflow = document.getElementById("save-workflow");
    els.saveGraph = document.getElementById("save-graph");
    els.status = document.getElementById("status-pill");
    els.nodeHeading = document.getElementById("node-heading");
    els.nodeId = document.getElementById("node-id");
    els.nodeType = document.getElementById("node-type");
    els.nodeStatus = document.getElementById("node-status");
    els.nodeOverlay = document.getElementById("node-overlay");
    els.nodeTitle = document.getElementById("node-title");
    els.nodeDescription = document.getElementById("node-description");
    els.nodeTimeout = document.getElementById("node-timeout");
    els.nodeAction = document.getElementById("node-action");
    els.nodeRetryMax = document.getElementById("node-retry-max");
    els.nodeRetryBackoff = document.getElementById("node-retry-backoff");
    els.connectorSection = document.getElementById("connector-section");
    els.nodeConnectorId = document.getElementById("node-connector-id");
    els.nodeConnectorKind = document.getElementById("node-connector-kind");
    els.httpSection = document.getElementById("http-section");
    els.nodeHttpMethod = document.getElementById("node-http-method");
    els.nodeHttpUrl = document.getElementById("node-http-url");
    els.nodeHttpHeaders = document.getElementById("node-http-headers");
    els.nodeHttpBody = document.getElementById("node-http-body");
    els.nodeHttpTimeout = document.getElementById("node-http-timeout");
    els.nodeSource = document.getElementById("node-source");
    els.validationList = document.getElementById("validation-list");
    els.skillReviewPanel = document.getElementById("skill-review-panel");
    els.skillReviewList = document.getElementById("skill-review-list");
  }

  function bindEvents() {
    window.addEventListener("resize", resizeCanvas);
    els.loadSample.addEventListener("click", loadSample);
    els.fitView.addEventListener("click", fitGraph);
    els.validateGraph.addEventListener("click", validateCurrentWorkflow);
    els.saveWorkflow.addEventListener("click", saveWorkflow);
    els.saveGraph.addEventListener("click", saveGraph);
    els.fileInput.addEventListener("change", loadSelectedFile);
    els.skillInput.addEventListener("change", stageSelectedSkill);
    els.compileSkill.addEventListener("click", compileStagedSkill);
    els.nodeTitle.addEventListener("input", updateSelectedNode);
    els.nodeDescription.addEventListener("input", updateSelectedNode);
    els.nodeAction.addEventListener("input", updateSelectedNode);
    els.nodeRetryMax.addEventListener("input", updateSelectedNode);
    els.nodeHttpMethod.addEventListener("input", updateSelectedNode);
    els.nodeHttpUrl.addEventListener("input", updateSelectedNode);
    els.nodeHttpHeaders.addEventListener("input", updateSelectedNode);
    els.nodeHttpBody.addEventListener("input", updateSelectedNode);
    els.nodeHttpTimeout.addEventListener("input", updateSelectedNode);
  }

  function registerNodeTypes() {
    NODE_TYPES.forEach(function (nodeType) {
      function WorkflowNode() {
        this.properties = {
          workflow_node_id: "",
          node_type: nodeType,
          description: "",
          run_status: "not_started",
          source: {},
        };
        this.size = [260, 110];
        if (nodeType !== "start") {
          this.addInput("in", "flow");
        }
        if (!TERMINAL_TYPES.has(nodeType)) {
          this.addOutput("success", "flow");
          if (nodeType !== "start") {
            this.addOutput("failure", "flow");
          }
        }
      }

      WorkflowNode.title = titleForType(nodeType);
      WorkflowNode.desc = "skill2workflow " + nodeType;
      WorkflowNode.prototype.onDrawForeground = drawNodeOverlay;
      WorkflowNode.prototype.onConnectionsChange = function () {
        window.requestAnimationFrame(validateGraph);
      };
      WorkflowNode.prototype.onConnectOutput = function (slot, type, input, targetNode) {
        return connectionAllowed(this, slot, targetNode);
      };

      LiteGraph.registerNodeType("skill2workflow/" + nodeType, WorkflowNode);
    });
  }

  function drawNodeOverlay(ctx) {
    const props = this.properties || {};
    const status = props.run_status || "not_started";
    const nodeType = props.node_type || "step";
    const statusColor = STATUS_THEME[status] || "#637083";
    const typeTheme = TYPE_THEME[nodeType] || TYPE_THEME.step;
    const width = this.size ? this.size[0] : 260;
    const height = this.size ? this.size[1] : 110;

    ctx.save();
    ctx.fillStyle = statusColor;
    ctx.beginPath();
    roundedRect(ctx, width - 82, 8, 72, 20, 4);
    ctx.fill();
    ctx.fillStyle = "#ffffff";
    ctx.font = "10px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(status.replace("_", " "), width - 46, 22);

    ctx.fillStyle = typeTheme.color;
    ctx.font = "11px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(props.workflow_node_id || nodeType, 12, height - 14);
    ctx.restore();
  }

  function roundedRect(ctx, x, y, width, height, radius) {
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
  }

  async function loadSample() {
    setStatus("Loading", "idle");
    const exampleName = els.exampleSelect && els.exampleSelect.value ? els.exampleSelect.value : "approval-flow.workflow.json";
    const exampleUrl = EXAMPLES[exampleName] || EXAMPLES["approval-flow.workflow.json"];
    try {
      const response = await fetch(exampleUrl, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("example workflow unavailable");
      }
      loadDocument(await response.json(), exampleName);
    } catch (error) {
      loadDocument(defaultWorkflow(), "embedded-example");
    }
  }

  async function loadSelectedFile(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) {
      return;
    }
    try {
      const documentJson = JSON.parse(await file.text());
      loadDocument(documentJson, file.name);
    } catch (error) {
      renderValidation(["Could not load JSON: " + error.message], new Set());
      setStatus("Invalid JSON", "invalid");
    } finally {
      event.target.value = "";
    }
  }

  async function stageSelectedSkill(event) {
    const file = event.target.files && event.target.files[0];
    stagedSkillMarkdown = null;
    updateSkillCompileControls();
    if (!file) return;
    try {
      if (typeof file.size !== "number" || file.size < 1 || file.size > MAX_SKILL_INPUT_BYTES) {
        throw new Error("SKILL.md is outside the 2 MiB limit");
      }
      if (typeof TextDecoder !== "function") {
        throw new Error("this browser cannot verify UTF-8 SKILL.md input");
      }
      const markdown = new TextDecoder("utf-8", { fatal: true }).decode(
        await file.arrayBuffer()
      );
      if (!markdown || new TextEncoder().encode(markdown).length > MAX_SKILL_INPUT_BYTES) {
        throw new Error("SKILL.md is outside the 2 MiB limit");
      }
      stagedSkillMarkdown = markdown;
      setStatus("SKILL staged", "valid");
    } catch (error) {
      renderValidation(["Could not stage SKILL.md: " + error.message], new Set());
      setStatus("SKILL rejected", "invalid");
    } finally {
      event.target.value = "";
      updateSkillCompileControls();
    }
  }

  async function compileStagedSkill() {
    if (!stagedSkillMarkdown || skillCompileLoading) return;
    skillCompileLoading = true;
    updateSkillCompileControls();
    setStatus("Compiling SKILL", "idle");
    try {
      const response = await fetch(SKILL_COMPILE_URL, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_markdown: stagedSkillMarkdown }),
      });
      if (!response.ok) {
        throw new Error(response.status === 404
          ? "Use skill2workflow ui instead of a static HTTP server to compile SKILL.md"
          : "local SKILL compilation is unavailable");
      }
      const compiled = parseSkillCompileResponse(await response.json());
      loadDocument(compiled.workflow, "Compiled SKILL.md", compiled.review);
    } catch (error) {
      renderValidation(["Could not compile SKILL.md: " + error.message], new Set());
      setStatus("SKILL compile failed", "invalid");
    } finally {
      skillCompileLoading = false;
      updateSkillCompileControls();
    }
  }

  function updateSkillCompileControls() {
    els.compileSkill.disabled = !stagedSkillMarkdown || skillCompileLoading;
    els.compileSkill.textContent = skillCompileLoading ? "Compiling SKILL…" : "Compile SKILL";
  }

  function loadDocument(documentJson, label, skillCompileReview) {
    try {
      const normalized = normalizeDocument(documentJson);
      const graphJson = normalized.graphJson;
      graph.clear();
      graph.configure(graphJson);
      currentWorkflow = graphJson.workflow || {};
      currentWorkflowDsl = normalized.workflowDsl ? deepClone(normalized.workflowDsl) : null;
      applyNodeTheme(new Set());
      renderInspector(null);
      validateGraph();
      renderSkillCompileReview(skillCompileReview || null);
      fitGraph();
      setStatus(label || "Loaded", validationErrors.length ? "invalid" : "valid");
    } catch (error) {
      renderSkillCompileReview(null);
      renderValidation([error.message], new Set());
      setStatus("Load failed", "invalid");
    }
  }

  function parseSkillCompileResponse(payload) {
    if (!plainObject(payload) || !plainObject(payload.workflow) || !plainObject(payload.review)) {
      throw new Error("local SKILL compilation returned an invalid response");
    }
    const review = payload.review;
    if (review.schema_version !== SKILL_COMPILE_REVIEW_SCHEMA_VERSION) {
      throw new Error("local SKILL compilation returned an unsupported review");
    }
    const countFields = [
      "ordered_step_count",
      "executable_node_count",
      "human_gate_count",
      "verification_node_count",
      "hard_gate_count",
    ];
    countFields.forEach(function (field) {
      if (!Number.isSafeInteger(review[field]) || review[field] < 0 || review[field] > MAX_SKILL_COMPILE_REVIEW_COUNT) {
        throw new Error("local SKILL compilation returned an invalid review");
      }
    });
    if (!Array.isArray(review.notices) || review.notices.length > 3) {
      throw new Error("local SKILL compilation returned an invalid review");
    }
    const seenNotices = new Set();
    review.notices.forEach(function (notice) {
      if (!Object.prototype.hasOwnProperty.call(SKILL_COMPILE_REVIEW_NOTICES, notice) || seenNotices.has(notice)) {
        throw new Error("local SKILL compilation returned an invalid review");
      }
      seenNotices.add(notice);
    });
    return { workflow: payload.workflow, review: review };
  }

  function normalizeDocument(documentJson) {
    if (documentJson.version === GRAPH_VERSION && Array.isArray(documentJson.nodes) && Array.isArray(documentJson.links)) {
      const sourceWorkflow = documentJson.extra && documentJson.extra.source_workflow;
      return {
        graphJson: documentJson,
        workflowDsl: sourceWorkflow && sourceWorkflow.nodes ? sourceWorkflow : null,
      };
    }
    if (Array.isArray(documentJson.nodes) && Array.isArray(documentJson.edges) && documentJson.workflow) {
      return {
        graphJson: workflowDslToLiteGraph(documentJson),
        workflowDsl: documentJson,
      };
    }
    throw new Error("Expected Workflow DSL JSON or skill2workflow LiteGraph JSON.");
  }

  function workflowDslToLiteGraph(workflow) {
    const nodes = workflow.nodes || [];
    const nodeIdMap = {};
    nodes.forEach(function (node, index) {
      nodeIdMap[node.id] = index + 1;
    });

    const graphNodes = nodes.map(function (node, index) {
      const nodeType = node.type || "step";
      const source = node.metadata && node.metadata.source ? node.metadata.source : {};
      return {
        id: index + 1,
        type: "skill2workflow/" + nodeType,
        pos: nodePosition(index + 1, nodeType),
        size: [260, 110],
        flags: {},
        order: index + 1,
        mode: 0,
        title: node.title || node.id,
        inputs: nodeType === "start" ? [] : [{ name: "in", type: "flow", link: null }],
        outputs: nodeOutputs(Boolean(node.on_success), Boolean(node.on_failure)),
        properties: {
          workflow_node_id: node.id,
          node_type: nodeType,
          description: node.description || "",
          ...(Object.prototype.hasOwnProperty.call(node, "timeout_ms") ? { timeout_ms: node.timeout_ms } : {}),
          run_status: "not_started",
          source: source,
          requires: cloneOrDefault(node.requires, []),
          produces: cloneOrDefault(node.produces, []),
          guard: cloneOrDefault(node.guard, null),
          action: cloneOrDefault(node.action, null),
          retry: cloneOrDefault(node.retry, null),
          connector: cloneOrDefault(node.connector, null),
        },
      };
    });

    const graphLinks = [];
    const edges = workflow.edges && workflow.edges.length ? workflow.edges : derivedEdges(nodes);
    edges.forEach(function (edge) {
      if (!nodeIdMap[edge.from] || !nodeIdMap[edge.to]) {
        return;
      }
      const sourceNode = nodes.find(function (node) {
        return node.id === edge.from;
      });
      const linkId = graphLinks.length + 1;
      const sourceGraphId = nodeIdMap[edge.from];
      const targetGraphId = nodeIdMap[edge.to];
      const sourceSlot = sourceSlotFor(edge, sourceNode || {});
      const targetSlot = graphLinks.filter(function (link) {
        return link[3] === targetGraphId;
      }).length;
      graphLinks.push([linkId, sourceGraphId, sourceSlot, targetGraphId, targetSlot, "flow"]);
      attachOutputLink(graphNodes[sourceGraphId - 1], sourceSlot, linkId);
      attachInputLink(graphNodes[targetGraphId - 1], targetSlot, linkId);
    });

    const workflowMeta = workflow.workflow || {};
    return {
      version: GRAPH_VERSION,
      workflow: {
        id: workflowMeta.id || "workflow",
        name: workflowMeta.name || "workflow",
        version: workflowMeta.version || "0.1.0",
        status: workflowMeta.status || "draft",
        description: workflowMeta.description || "",
        entry: workflow.entry || "start",
      },
      last_node_id: graphNodes.length,
      last_link_id: graphLinks.length,
      nodes: graphNodes,
      links: graphLinks,
      groups: [],
      config: {},
      extra: {
        source_schema_version: workflow.schema_version,
        truth_source: "workflow_dsl",
        source_workflow: deepClone(workflow),
      },
    };
  }

  function nodeOutputs(hasSuccess, hasFailure) {
    const outputs = [];
    if (hasSuccess) {
      outputs.push({ name: "success", type: "flow", links: [] });
    }
    if (hasFailure) {
      outputs.push({ name: "failure", type: "flow", links: [] });
    }
    return outputs;
  }

  function nodePosition(index, nodeType) {
    if (nodeType === "failure") {
      return [260 * Math.max(index - 2, 0) + 80, 260];
    }
    if (nodeType === "end") {
      return [260 * Math.max(index - 1, 0) + 80, 80];
    }
    return [260 * (index - 1) + 80, 80];
  }

  function derivedEdges(nodes) {
    const edges = [];
    nodes.forEach(function (node) {
      if (node.on_success) {
        edges.push({ from: node.id, to: node.on_success, label: "success" });
      }
      if (node.on_failure) {
        edges.push({ from: node.id, to: node.on_failure, label: "failure" });
      }
    });
    return edges;
  }

  function sourceSlotFor(edge, sourceNode) {
    if (edge.label === "failure" || edge.to === sourceNode.on_failure) {
      return 1;
    }
    return 0;
  }

  function attachOutputLink(node, slot, linkId) {
    if (!node || !node.outputs || !node.outputs[slot]) {
      return;
    }
    node.outputs[slot].links = node.outputs[slot].links || [];
    node.outputs[slot].links.push(linkId);
  }

  function attachInputLink(node, slot, linkId) {
    if (!node || !node.inputs) {
      return;
    }
    while (slot >= node.inputs.length) {
      node.inputs.push({ name: "in_" + (slot + 1), type: "flow", link: null });
    }
    node.inputs[slot].link = linkId;
  }

  function validateGraph() {
    if (!graph) {
      return [];
    }
    const errors = [];
    const invalidNodeIds = new Set();
    const workflowIds = new Set();

    graph._nodes.forEach(function (node) {
      const workflowId = node.properties && node.properties.workflow_node_id;
      if (!workflowId) {
        errors.push("Node " + node.id + " is missing workflow_node_id.");
        invalidNodeIds.add(node.id);
        return;
      }
      if (workflowIds.has(workflowId)) {
        errors.push("Duplicate workflow node id: " + workflowId + ".");
        invalidNodeIds.add(node.id);
      }
      workflowIds.add(workflowId);
    });

    currentLinks().forEach(function (link) {
      const source = getNodeByGraphId(link.origin_id);
      const target = getNodeByGraphId(link.target_id);
      if (!source || !target) {
        errors.push("Link " + link.id + " references a missing node.");
        if (source) invalidNodeIds.add(source.id);
        if (target) invalidNodeIds.add(target.id);
        return;
      }

      const sourceType = source.properties && source.properties.node_type;
      const targetType = target.properties && target.properties.node_type;
      const output = source.outputs && source.outputs[link.origin_slot];
      const outputName = output && output.name ? output.name : "success";
      if (TERMINAL_TYPES.has(sourceType)) {
        errors.push(source.title + " is terminal and cannot have outgoing links.");
        invalidNodeIds.add(source.id);
      }
      if (outputName === "failure" && targetType !== "failure") {
        errors.push(source.title + " failure output must target a failure node.");
        invalidNodeIds.add(source.id);
        invalidNodeIds.add(target.id);
      }
      if (outputName === "success" && targetType === "failure") {
        errors.push(source.title + " success output cannot target failure.");
        invalidNodeIds.add(source.id);
        invalidNodeIds.add(target.id);
      }
    });

    validationErrors = errors;
    applyNodeTheme(invalidNodeIds);
    renderValidation(errors, invalidNodeIds);
    setStatus(errors.length ? "Invalid" : "Valid", errors.length ? "invalid" : "valid");
    if (canvas) {
      canvas.setDirty(true, true);
    }
    return errors;
  }

  function currentLinks() {
    if (!graph || !graph.links) {
      return [];
    }
    if (Array.isArray(graph.links)) {
      return graph.links.map(normalizeLink).filter(Boolean);
    }
    return Object.keys(graph.links)
      .map(function (key) {
        return normalizeLink(graph.links[key]);
      })
      .filter(Boolean);
  }

  function normalizeLink(link) {
    if (Array.isArray(link)) {
      return linkFromArray(link);
    }
    if (link && typeof link === "object") {
      return link;
    }
    return null;
  }

  function linkFromArray(link) {
    if (!Array.isArray(link) || link.length < 5) {
      return null;
    }
    return {
      id: link[0],
      origin_id: link[1],
      origin_slot: link[2],
      target_id: link[3],
      target_slot: link[4],
      type: link[5],
    };
  }

  function getNodeByGraphId(id) {
    if (graph.getNodeById) {
      return graph.getNodeById(id);
    }
    return graph._nodes.find(function (node) {
      return node.id === id;
    });
  }

  function connectionAllowed(sourceNode, sourceSlot, targetNode) {
    if (!sourceNode || !targetNode) {
      return true;
    }
    const sourceType = sourceNode.properties && sourceNode.properties.node_type;
    const targetType = targetNode.properties && targetNode.properties.node_type;
    const output = sourceNode.outputs && sourceNode.outputs[sourceSlot];
    const outputName = output && output.name ? output.name : "success";

    if (TERMINAL_TYPES.has(sourceType)) {
      return false;
    }
    if (outputName === "failure") {
      return targetType === "failure";
    }
    return targetType !== "failure";
  }

  function applyNodeTheme(invalidNodeIds) {
    if (!graph) {
      return;
    }
    graph._nodes.forEach(function (node) {
      const nodeType = node.properties && node.properties.node_type ? node.properties.node_type : "step";
      const theme = TYPE_THEME[nodeType] || TYPE_THEME.step;
      if (invalidNodeIds.has(node.id)) {
        node.color = "#b42318";
        node.bgcolor = "#fdeceb";
        node.boxcolor = "#b42318";
      } else {
        node.color = theme.color;
        node.bgcolor = theme.background;
        node.boxcolor = theme.color;
      }
    });
  }

  function renderValidation(errors) {
    els.validationList.innerHTML = "";
    if (!errors.length) {
      const item = document.createElement("li");
      item.className = "ok";
      item.textContent = "Graph structure is valid.";
      els.validationList.appendChild(item);
      return;
    }
    errors.forEach(function (error) {
      const item = document.createElement("li");
      item.className = "error";
      item.textContent = error;
      els.validationList.appendChild(item);
    });
  }

  function renderSkillCompileReview(review) {
    els.skillReviewList.innerHTML = "";
    els.skillReviewPanel.hidden = !review;
    if (!review) return;

    const summary = document.createElement("li");
    summary.className = "ok";
    summary.textContent = "Compiler inferred " + review.executable_node_count + " executable node(s), "
      + review.human_gate_count + " human gate(s), "
      + review.verification_node_count + " verification node(s), and "
      + review.hard_gate_count + " hard-gate declaration(s).";
    els.skillReviewList.appendChild(summary);
    review.notices.forEach(function (notice) {
      const item = document.createElement("li");
      item.textContent = SKILL_COMPILE_REVIEW_NOTICES[notice];
      els.skillReviewList.appendChild(item);
    });
  }

  function renderInspector(node) {
    selectedNode = node;
    const hasNode = Boolean(node);
    const props = hasNode ? node.properties || {} : {};
    const action = props.action && typeof props.action === "object" ? props.action : null;
    const retry = props.retry && typeof props.retry === "object" ? props.retry : null;
    const connector = props.connector && typeof props.connector === "object" ? props.connector : null;
    const request = connector && connector.request && typeof connector.request === "object" ? connector.request : {};
    els.nodeHeading.textContent = hasNode ? node.title : "No selection";
    els.nodeId.value = hasNode ? props.workflow_node_id || "" : "";
    els.nodeType.value = hasNode ? props.node_type || "" : "";
    els.nodeStatus.value = hasNode ? props.run_status || "" : "";
    els.nodeOverlay.value = hasNode ? JSON.stringify(props.run_overlay || {}, null, 2) : "";
    els.nodeTitle.value = hasNode ? node.title || "" : "";
    els.nodeDescription.value = hasNode ? props.description || "" : "";
    els.nodeTimeout.value = hasNode && props.timeout_ms !== undefined ? props.timeout_ms : "";
    els.nodeAction.value = action ? action.prompt || action.instruction || "" : "";
    els.nodeRetryMax.value = retry && retry.max_attempts !== undefined ? retry.max_attempts : "";
    els.nodeRetryBackoff.value = retry && retry.backoff_ms !== undefined ? retry.backoff_ms : "";
    els.nodeConnectorId.value = connector ? connector.id || "" : "";
    els.nodeConnectorKind.value = connector ? connector.kind || "" : "";
    els.nodeHttpMethod.value = request.method || "";
    els.nodeHttpUrl.value = request.url || "";
    els.nodeHttpHeaders.value = stringifyJsonInput(request.headers || {});
    els.nodeHttpBody.value = stringifyJsonInput(request.body === undefined ? {} : request.body);
    els.nodeHttpTimeout.value = request.timeout_ms !== undefined ? request.timeout_ms : "";
    els.nodeSource.value = hasNode ? JSON.stringify(props.source || {}, null, 2) : "";
    els.connectorSection.hidden = !connector;
    els.httpSection.hidden = !connector || connector.id !== "http";
    els.nodeTitle.disabled = !hasNode;
    els.nodeDescription.disabled = !hasNode;
    els.nodeTimeout.disabled = !hasNode;
    els.nodeAction.disabled = !hasNode || !action;
    els.nodeRetryMax.disabled = !hasNode || !retry;
    els.nodeRetryBackoff.disabled = !hasNode || !retry;
    els.nodeHttpMethod.disabled = !hasNode || !connector || connector.id !== "http";
    els.nodeHttpUrl.disabled = !hasNode || !connector || connector.id !== "http";
    els.nodeHttpHeaders.disabled = !hasNode || !connector || connector.id !== "http";
    els.nodeHttpBody.disabled = !hasNode || !connector || connector.id !== "http";
    els.nodeHttpTimeout.disabled = !hasNode || !connector || connector.id !== "http";
  }

  function updateSelectedNode() {
    if (!selectedNode) {
      return;
    }
    const syncResult = syncInspectorToSelectedNode(false);
    if (!syncResult.ok) {
      renderValidation([syncResult.error]);
      setStatus("Invalid input", "invalid");
      return;
    }
    selectedNode.title = els.nodeTitle.value;
    selectedNode.properties.description = els.nodeDescription.value;
    selectedNode.setDirtyCanvas(true, true);
    els.nodeHeading.textContent = selectedNode.title;
    validateGraph();
  }

  function syncInspectorToSelectedNode(strict) {
    if (!selectedNode || !selectedNode.properties) {
      return { ok: true };
    }
    const props = selectedNode.properties;
    if (props.action && typeof props.action === "object") {
      if (Object.prototype.hasOwnProperty.call(props.action, "prompt")) {
        props.action.prompt = els.nodeAction.value;
      } else if (Object.prototype.hasOwnProperty.call(props.action, "instruction")) {
        props.action.instruction = els.nodeAction.value;
      }
    }
    if (els.nodeTimeout.value !== "") {
      const nodeTimeout = Number(els.nodeTimeout.value);
      if (!Number.isInteger(nodeTimeout) || nodeTimeout < 0 || nodeTimeout > 86400000) {
        return { ok: false, error: "Node timeout must be an integer between 0 and 86400000 ms." };
      }
      props.timeout_ms = nodeTimeout;
    } else if (Object.prototype.hasOwnProperty.call(props, "timeout_ms")) {
      props.timeout_ms = null;
    }
    if (props.retry && typeof props.retry === "object" && els.nodeRetryMax.value !== "") {
      const maxAttempts = Number(els.nodeRetryMax.value);
      if (!Number.isInteger(maxAttempts) || maxAttempts < 0) {
        return { ok: false, error: "Retry attempts must be a non-negative integer." };
      }
      props.retry.max_attempts = maxAttempts;
    }
    if (props.retry && typeof props.retry === "object" && els.nodeRetryBackoff.value !== "") {
      const backoffMs = Number(els.nodeRetryBackoff.value);
      if (!Number.isInteger(backoffMs) || backoffMs < 0 || backoffMs > 60000) {
        return { ok: false, error: "Retry backoff must be an integer between 0 and 60000 ms." };
      }
      props.retry.backoff_ms = backoffMs;
    }
    const connector = props.connector;
    if (!connector || typeof connector !== "object" || connector.id !== "http") {
      return { ok: true };
    }
    connector.request = connector.request && typeof connector.request === "object" ? connector.request : {};
    connector.request.method = els.nodeHttpMethod.value.trim();
    connector.request.url = els.nodeHttpUrl.value.trim();
    if (els.nodeHttpTimeout.value !== "") {
      const timeout = Number(els.nodeHttpTimeout.value);
      if (!Number.isInteger(timeout) || timeout < 0) {
        return { ok: false, error: "HTTP timeout must be a non-negative integer." };
      }
      connector.request.timeout_ms = timeout;
    }
    const headers = parseJsonInput(els.nodeHttpHeaders.value, "Headers JSON", strict);
    if (!headers.ok) {
      return headers;
    }
    if (headers.hasValue) {
      if (!headers.value || typeof headers.value !== "object" || Array.isArray(headers.value)) {
        return { ok: false, error: "Headers JSON must be an object." };
      }
      connector.request.headers = headers.value;
    }
    const body = parseJsonInput(els.nodeHttpBody.value, "Body JSON", strict);
    if (!body.ok) {
      return body;
    }
    if (body.hasValue) {
      connector.request.body = body.value;
    }
    return { ok: true };
  }

  function parseJsonInput(text, label, strict) {
    const trimmed = String(text || "").trim();
    if (!trimmed) {
      return { ok: true, hasValue: false };
    }
    try {
      return { ok: true, hasValue: true, value: JSON.parse(trimmed) };
    } catch (error) {
      if (!strict) {
        return { ok: false, error: label + " must be valid JSON." };
      }
      return { ok: false, error: label + " must be valid JSON: " + error.message };
    }
  }

  function stringifyJsonInput(value) {
    return JSON.stringify(value, null, 2);
  }

  function saveGraph() {
    if (validateGraph().length) {
      return;
    }
    const serialized = graph.serialize();
    let sourceWorkflow = null;
    if (currentWorkflowDsl) {
      try {
        sourceWorkflow = workflowDslFromGraph();
      } catch (error) {
        renderValidation([error.message]);
        setStatus("Invalid DSL", "invalid");
        return;
      }
    }
    const graphJson = Object.assign({}, serialized, {
      version: GRAPH_VERSION,
      workflow: currentWorkflow,
      extra: Object.assign(
        {},
        serialized.extra || {},
        { truth_source: "workflow_dsl" },
        sourceWorkflow ? { source_workflow: sourceWorkflow } : {}
      ),
    });
    downloadJson(graphJson, (currentWorkflow.name || "workflow") + ".litegraph.json");
  }

  async function saveWorkflow() {
    const workflow = workflowFromEditor();
    if (!workflow) return;

    const validation = await requestWorkflowValidation(workflow);
    if (validation === false) return;
    if (!validation) {
      downloadJson(workflow, (currentWorkflow.name || "workflow") + ".workflow.json");
      renderValidation([
        "DSL saved after local checks only. Start skill2workflow ui or run the CLI validate command before publishing.",
      ]);
      setStatus("DSL saved (local checks)", "idle");
      return;
    }
    downloadJson(workflow, (currentWorkflow.name || "workflow") + ".workflow.json");
    setStatus("DSL saved", "valid");
  }

  async function validateCurrentWorkflow() {
    const workflow = workflowFromEditor();
    if (!workflow) return;
    const validation = await requestWorkflowValidation(workflow);
    if (validation === false) return;
    if (!validation) {
      renderValidation([
        "Full compiler validation is unavailable. Start skill2workflow ui or run the CLI validate command.",
      ]);
      setStatus("Local checks only", "idle");
      return;
    }
    renderWorkflowValidation(validation);
  }

  function workflowFromEditor() {
    const graphErrors = validateGraph();
    if (graphErrors.length) return null;
    if (!currentWorkflowDsl) {
      renderValidation(["Load Workflow DSL or a LiteGraph JSON with embedded source workflow before saving DSL."]);
      setStatus("No source DSL", "invalid");
      return null;
    }
    let workflow;
    try {
      workflow = workflowDslFromGraph();
    } catch (error) {
      renderValidation([error.message]);
      setStatus("Invalid DSL", "invalid");
      return null;
    }
    const workflowErrors = validateWorkflowDsl(workflow);
    if (workflowErrors.length) {
      renderValidation(workflowErrors);
      setStatus("Invalid DSL", "invalid");
      return null;
    }
    return workflow;
  }

  async function requestWorkflowValidation(workflow) {
    try {
      const response = await fetch(WORKFLOW_VALIDATION_URL, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow: workflow }),
      });
      if (response.status === 404) return null;
      if (!response.ok) {
        throw new Error("local Workflow DSL validation is unavailable");
      }
      const validation = parseWorkflowValidationResponse(await response.json());
      if (!validation.valid) {
        renderWorkflowValidation(validation);
        return false;
      }
      return validation;
    } catch (error) {
      renderValidation(["Could not validate Workflow DSL: " + error.message]);
      setStatus("DSL validation failed", "invalid");
      return false;
    }
  }

  function parseWorkflowValidationResponse(payload) {
    if (!plainObject(payload)
      || Object.keys(payload).length !== 5
      || payload.schema_version !== WORKFLOW_VALIDATION_SCHEMA_VERSION
      || typeof payload.valid !== "boolean"
      || !Number.isSafeInteger(payload.error_count)
      || payload.error_count < 0
      || payload.error_count > MAX_WORKFLOW_VALIDATION_ERROR_COUNT
      || !Array.isArray(payload.errors)
      || payload.errors.length > MAX_WORKFLOW_VALIDATION_ERRORS
      || typeof payload.truncated !== "boolean") {
      throw new Error("local Workflow DSL validation returned an invalid response");
    }
    if (payload.valid !== (payload.error_count === 0)
      || payload.errors.length > payload.error_count
      || payload.truncated !== (payload.error_count > payload.errors.length)) {
      throw new Error("local Workflow DSL validation returned an invalid response");
    }
    payload.errors.forEach(function (error) {
      const errorKeys = plainObject(error) ? Object.keys(error) : [];
      if (!plainObject(error)
        || !errorKeys.includes("code")
        || errorKeys.length > 2
        || typeof error.code !== "string"
        || !/^[a-z0-9_]{1,64}$/.test(error.code)
        || (Object.prototype.hasOwnProperty.call(error, "node_index")
          && (!Number.isSafeInteger(error.node_index)
            || error.node_index < 0
            || error.node_index > MAX_WORKFLOW_VALIDATION_NODE_INDEX))) {
        throw new Error("local Workflow DSL validation returned an invalid response");
      }
    });
    return payload;
  }

  function renderWorkflowValidation(validation) {
    if (validation.valid) {
      renderValidation([]);
      setStatus("Workflow valid", "valid");
      return;
    }
    const errors = validation.errors.map(function (error) {
      const location = Object.prototype.hasOwnProperty.call(error, "node_index")
        ? " node " + (error.node_index + 1)
        : "";
      return "Workflow DSL" + location + ": " + error.code.replace(/_/g, " ") + ".";
    });
    if (validation.truncated) {
      errors.push("Workflow DSL: additional validation errors were omitted from this bounded response.");
    }
    renderValidation(errors);
    setStatus("Invalid DSL", "invalid");
  }

  function workflowDslFromGraph() {
    const syncResult = syncInspectorToSelectedNode(true);
    if (!syncResult.ok) {
      throw new Error(syncResult.error);
    }
    const workflow = deepClone(currentWorkflowDsl);
    const graphNodeByWorkflowId = {};
    graph._nodes.forEach(function (node) {
      if (node.properties && node.properties.workflow_node_id) {
        graphNodeByWorkflowId[node.properties.workflow_node_id] = node;
      }
    });
    workflow.nodes.forEach(function (node) {
      const graphNode = graphNodeByWorkflowId[node.id];
      if (!graphNode) {
        return;
      }
      node.title = graphNode.title || node.title;
      const description = graphNode.properties && graphNode.properties.description ? graphNode.properties.description : "";
      if (description || Object.prototype.hasOwnProperty.call(node, "description")) {
        node.description = description;
      }
      applyAuthoringProperties(node, graphNode.properties || {});
    });
    return workflow;
  }

  function applyAuthoringProperties(node, props) {
    applyNodeTimeoutProperties(node, props.timeout_ms);
    applyActionProperties(node, props.action);
    applyRetryProperties(node, props.retry);
    applyConnectorProperties(node, props.connector);
  }

  function applyNodeTimeoutProperties(node, graphTimeout) {
    if (graphTimeout === undefined) {
      return;
    }
    if (graphTimeout === null) {
      delete node.timeout_ms;
      return;
    }
    const timeout = Number(graphTimeout);
    if (!Number.isInteger(timeout) || timeout < 0 || timeout > 86400000) {
      throw new Error(node.id + " timeout_ms must be an integer between 0 and 86400000.");
    }
    node.timeout_ms = timeout;
  }

  function applyActionProperties(node, graphAction) {
    if (!node.action || !graphAction) {
      return;
    }
    if (graphAction.kind !== node.action.kind) {
      throw new Error(node.id + " action kind cannot be changed.");
    }
    if (Object.prototype.hasOwnProperty.call(node.action, "prompt") && graphAction.prompt !== undefined) {
      node.action.prompt = String(graphAction.prompt || "");
    }
    if (Object.prototype.hasOwnProperty.call(node.action, "instruction") && graphAction.instruction !== undefined) {
      node.action.instruction = String(graphAction.instruction || "");
    }
  }

  function applyRetryProperties(node, graphRetry) {
    if (!node.retry || !graphRetry) {
      return;
    }
    if (graphRetry.max_attempts !== undefined) {
      const maxAttempts = Number(graphRetry.max_attempts);
      if (!Number.isInteger(maxAttempts) || maxAttempts < 0) {
        throw new Error(node.id + " retry.max_attempts must be a non-negative integer.");
      }
      node.retry.max_attempts = maxAttempts;
    }
    if (graphRetry.backoff_ms !== undefined) {
      const backoffMs = Number(graphRetry.backoff_ms);
      if (!Number.isInteger(backoffMs) || backoffMs < 0 || backoffMs > 60000) {
        throw new Error(node.id + " retry.backoff_ms must be an integer between 0 and 60000.");
      }
      node.retry.backoff_ms = backoffMs;
    }
  }

  function applyConnectorProperties(node, graphConnector) {
    if (!node.connector || !graphConnector) {
      return;
    }
    if (graphConnector.id !== node.connector.id || graphConnector.kind !== node.connector.kind) {
      throw new Error(node.id + " connector identity cannot be changed.");
    }
    if (node.connector.id !== "http" || !graphConnector.request) {
      return;
    }
    node.connector.request = node.connector.request && typeof node.connector.request === "object"
      ? node.connector.request
      : {};
    const request = graphConnector.request;
    if (request.method !== undefined) node.connector.request.method = String(request.method || "");
    if (request.url !== undefined) node.connector.request.url = String(request.url || "");
    if (request.headers !== undefined) node.connector.request.headers = deepClone(request.headers);
    if (request.body !== undefined) node.connector.request.body = deepClone(request.body);
    if (request.timeout_ms !== undefined) {
      const timeout = Number(request.timeout_ms);
      if (!Number.isInteger(timeout) || timeout < 0) {
        throw new Error(node.id + " connector.request.timeout_ms must be a non-negative integer.");
      }
      node.connector.request.timeout_ms = timeout;
    }
  }

  function validateWorkflowDsl(workflow) {
    const errors = [];
    if (!workflow || !Array.isArray(workflow.nodes) || !Array.isArray(workflow.edges)) {
      return ["Workflow DSL must contain nodes and edges arrays."];
    }
    const nodeIds = workflow.nodes.map(function (node) {
      return node.id;
    });
    const nodeIdSet = new Set(nodeIds);
    if (nodeIdSet.size !== nodeIds.length) {
      errors.push("Workflow node ids must be unique.");
    }
    if (!nodeIdSet.has(workflow.entry)) {
      errors.push("Workflow entry must reference an existing node.");
    }
    if (!workflow.nodes.some(function (node) { return node.type === "end"; })) {
      errors.push("Workflow must contain at least one end node.");
    }
    const workflowEdges = workflowEdgeSet(workflow);
    const graphEdges = graphEdgeSet();
    if (!sameSet(workflowEdges, graphEdges)) {
      errors.push("Graph topology does not match Workflow DSL.");
    }
    workflow.nodes.forEach(function (node) {
      if (node.timeout_ms !== undefined) {
        const nodeTimeout = Number(node.timeout_ms);
        if (!Number.isInteger(nodeTimeout) || nodeTimeout < 0 || nodeTimeout > 86400000) {
          errors.push(node.id + " timeout_ms must be an integer between 0 and 86400000.");
        }
      }
      if (TERMINAL_TYPES.has(node.type)) {
        if (node.on_success || node.on_failure) {
          errors.push(node.id + " is terminal and must not define transitions.");
        }
        return;
      }
      if (!node.on_success) {
        errors.push(node.id + " must define on_success.");
      }
      if (node.type === "human_gate" && !node.on_failure) {
        errors.push(node.id + " human_gate must define on_failure.");
      }
      if (node.type === "tool_call" && (!node.connector || !node.connector.id)) {
        errors.push(node.id + " tool_call must define connector.id.");
      }
      if (node.retry && node.retry.max_attempts !== undefined) {
        const maxAttempts = Number(node.retry.max_attempts);
        if (!Number.isInteger(maxAttempts) || maxAttempts < 0) {
          errors.push(node.id + " retry.max_attempts must be a non-negative integer.");
        }
      }
      if (node.retry && node.retry.backoff_ms !== undefined) {
        const backoffMs = Number(node.retry.backoff_ms);
        if (!Number.isInteger(backoffMs) || backoffMs < 0 || backoffMs > 60000) {
          errors.push(node.id + " retry.backoff_ms must be an integer between 0 and 60000.");
        }
      }
      if (node.connector && node.connector.id === "http" && node.connector.request) {
        if (node.connector.request.headers !== undefined && !plainObject(node.connector.request.headers)) {
          errors.push(node.id + " connector.request.headers must be an object.");
        }
        if (node.connector.request.timeout_ms !== undefined) {
          const timeout = Number(node.connector.request.timeout_ms);
          if (!Number.isInteger(timeout) || timeout < 0) {
            errors.push(node.id + " connector.request.timeout_ms must be a non-negative integer.");
          }
        }
      }
      ["on_success", "on_failure"].forEach(function (key) {
        if (node[key] && !nodeIdSet.has(node[key])) {
          errors.push(node.id + "." + key + " references missing node " + node[key] + ".");
        }
      });
    });
    workflow.edges.forEach(function (edge) {
      if (!nodeIdSet.has(edge.from)) {
        errors.push(edge.id + ".from references missing node " + edge.from + ".");
      }
      if (!nodeIdSet.has(edge.to)) {
        errors.push(edge.id + ".to references missing node " + edge.to + ".");
      }
    });
    return errors;
  }

  function workflowEdgeSet(workflow) {
    return new Set(
      workflow.edges.map(function (edge) {
        const kind = String(edge.label || "").toLowerCase() === "failure" ? "failure" : "success";
        return edge.from + "->" + edge.to + ":" + kind;
      })
    );
  }

  function graphEdgeSet() {
    const graphNodeById = {};
    graph._nodes.forEach(function (node) {
      graphNodeById[node.id] = node;
    });
    const edges = new Set();
    currentLinks().forEach(function (link) {
      const source = graphNodeById[link.origin_id];
      const target = graphNodeById[link.target_id];
      if (!source || !target || !source.properties || !target.properties) {
        return;
      }
      const output = source.outputs && source.outputs[link.origin_slot];
      const kind = output && output.name === "failure" ? "failure" : "success";
      edges.add(source.properties.workflow_node_id + "->" + target.properties.workflow_node_id + ":" + kind);
    });
    return edges;
  }

  function sameSet(left, right) {
    if (left.size !== right.size) {
      return false;
    }
    for (const item of left) {
      if (!right.has(item)) {
        return false;
      }
    }
    return true;
  }

  function plainObject(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
  }

  function downloadJson(value, filename) {
    const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function deepClone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function cloneOrDefault(value, fallback) {
    if (value === undefined || value === null) {
      return fallback;
    }
    return deepClone(value);
  }

  function fitGraph() {
    if (!graph || !canvas || !graph._nodes.length || !canvas.ds) {
      return;
    }
    const bounds = graph._nodes.reduce(
      function (acc, node) {
        const pos = node.pos || [0, 0];
        const size = node.size || [260, 110];
        acc.minX = Math.min(acc.minX, pos[0]);
        acc.minY = Math.min(acc.minY, pos[1]);
        acc.maxX = Math.max(acc.maxX, pos[0] + size[0]);
        acc.maxY = Math.max(acc.maxY, pos[1] + size[1]);
        return acc;
      },
      { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity }
    );
    const width = els.canvas.clientWidth || 800;
    const height = els.canvas.clientHeight || 500;
    const graphWidth = Math.max(bounds.maxX - bounds.minX, 1);
    const graphHeight = Math.max(bounds.maxY - bounds.minY, 1);
    const scale = Math.min(1.2, Math.max(0.35, Math.min((width - 80) / graphWidth, (height - 80) / graphHeight)));
    canvas.ds.scale = scale;
    canvas.ds.offset = [40 - bounds.minX * scale, 40 - bounds.minY * scale];
    canvas.setDirty(true, true);
  }

  function resizeCanvas() {
    if (!els.canvas || !els.canvas.parentElement) {
      return;
    }
    const rect = els.canvas.parentElement.getBoundingClientRect();
    els.canvas.width = Math.max(1, Math.floor(rect.width));
    els.canvas.height = Math.max(1, Math.floor(rect.height));
    if (canvas && canvas.resize) {
      canvas.resize();
      canvas.setDirty(true, true);
    }
  }

  function setStatus(text, state) {
    els.status.textContent = text;
    els.status.className = "status-pill";
    if (state === "valid") {
      els.status.classList.add("status-valid");
    } else if (state === "invalid") {
      els.status.classList.add("status-invalid");
    } else {
      els.status.classList.add("status-idle");
    }
  }

  function titleForType(type) {
    return type
      .split("_")
      .map(function (part) {
        return part.charAt(0).toUpperCase() + part.slice(1);
      })
      .join(" ");
  }

  function defaultWorkflow() {
    return {
      schema_version: "0.1.0",
      workflow: {
        id: "workflow_embedded_approval",
        name: "embedded-approval",
        description: "Embedded approval example.",
        version: "0.1.0",
        status: "draft",
      },
      entry: "start",
      nodes: [
        { id: "start", type: "start", title: "Start", description: "Workflow entry point.", on_success: "draft" },
        {
          id: "draft",
          type: "step",
          title: "Draft workflow",
          description: "Create the workflow draft.",
          on_success: "review",
          on_failure: "failure",
        },
        {
          id: "review",
          type: "human_gate",
          title: "Ask user for approval",
          description: "Pause until the user approves the draft.",
          on_success: "publish",
          on_failure: "failure",
        },
        {
          id: "publish",
          type: "step",
          title: "Publish workflow",
          description: "Publish after approval.",
          on_success: "end",
          on_failure: "failure",
        },
        { id: "failure", type: "failure", title: "Failure", description: "Terminal failure node." },
        { id: "end", type: "end", title: "End", description: "Workflow completed." },
      ],
      edges: [
        { id: "edge_start_draft", from: "start", to: "draft", label: "next" },
        { id: "edge_draft_review", from: "draft", to: "review", label: "next" },
        { id: "edge_review_publish", from: "review", to: "publish", label: "next" },
        { id: "edge_publish_end", from: "publish", to: "end", label: "next" },
        { id: "edge_draft_failure", from: "draft", to: "failure", label: "failure" },
        { id: "edge_review_failure", from: "review", to: "failure", label: "failure" },
        { id: "edge_publish_failure", from: "publish", to: "failure", label: "failure" },
      ],
    };
  }
})();
