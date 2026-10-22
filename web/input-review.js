(function () {
  const URL = "/api/v1/draft-input-preflights";
  const VERSION = "skill2workflow-workflow-preflight-0.1.0";
  const INPUT_BYTES = 1024 * 1024;
  const REPORT_BYTES = 64 * 1024;
  const encoder = new TextEncoder();
  function object(value) { return value !== null && typeof value === "object" && !Array.isArray(value); }
  function count(value, max) { return Number.isInteger(value) && value >= 0 && value <= max; }

  async function readReport(response) {
    if (Number(response.headers.get("Content-Length")) > REPORT_BYTES) throw new Error("invalid report");
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8", { fatal: true });
    let total = 0, text = "";
    try {
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        total += chunk.value.byteLength;
        if (total > REPORT_BYTES) { await reader.cancel(); throw new Error("invalid report"); }
        text += decoder.decode(chunk.value, { stream: true });
      }
      text += decoder.decode();
      return JSON.parse(text);
    } finally { reader.releaseLock(); }
  }

  function validateReport(report, workflow) {
    if (!object(report) || report.schema_version !== VERSION || typeof report.ready !== "boolean"
      || !object(report.workflow) || !object(report.input) || !object(report.summary)
      || !Array.isArray(report.nodes) || !Array.isArray(report.issues) || !object(report.safety)
      || report.nodes.length > 1000 || report.issues.length > 64
      || !["valid", "invalid"].includes(report.input.status)
      || report.safety.side_effect_free !== true || report.safety.connector_calls !== false
      || report.safety.credentials_resolved !== false || report.safety.raw_values_included !== false) throw new Error("invalid report");
    for (const key of ["id", "version", "status"]) {
      if (report.workflow[key] !== workflow.workflow[key]) throw new Error("wrong draft");
    }
    for (const key of ["node_count", "connector_node_count", "side_effecting_node_count", "mapping_count", "blocked_node_count", "issue_count"]) {
      if (!count(report.summary[key], 2000000)) throw new Error("invalid report");
    }
    if (report.summary.node_count !== report.nodes.length || report.summary.issue_count !== report.issues.length
      || report.ready !== (report.input.status === "valid" && report.issues.length === 0)
      || (report.ready && report.summary.blocked_node_count !== 0)) throw new Error("invalid report");
    for (const issue of report.issues) {
      if (!object(issue) || !["input_invalid", "required_mapping_input_missing"].includes(issue.code)
        || issue.severity !== "error" || !(issue.node_id === null || typeof issue.node_id === "string")
        || !Array.isArray(issue.path) || issue.path.length > 16
        || issue.path.some(part => !(typeof part === "string" && part.length <= 128) && !count(part, 1000000))) throw new Error("invalid report");
    }
    return report;
  }

  function create(options) {
    const els = options.elements;
    let source = null, revision = 0, controller = null;
    function status(message, state) {
      els.status.textContent = message;
      els.status.dataset.state = state;
    }
    function invalidate() {
      revision++;
      if (controller) { controller.abort(); controller = null; }
      els.issues.replaceChildren();
      els.check.disabled = !source;
      status(source ? "Not checked. Check this draft with the current input." : "Load source DSL to check input.", "unchecked");
    }
    function reset(workflow) {
      source = workflow;
      els.input.value = "";
      els.input.disabled = !source;
      els.clear.disabled = !source;
      els.fields.replaceChildren();
      els.schema.value = "";
      els.schemaDetails.hidden = true;
      const schema = workflow && workflow.input_schema;
      const properties = object(schema) && object(schema.properties) ? schema.properties : {};
      const required = object(schema) && Array.isArray(schema.required) ? schema.required : [];
      const names = Object.keys(properties);
      els.summary.textContent = !source ? "Source unavailable" : schema ? names.length + " fields · " + required.length + " required" : "No declared schema";
      els.panel.open = Boolean(schema);
      if (!schema) {
        const item = document.createElement("li");
        item.textContent = source ? "No declared input schema. Required connector mappings can still need input." : "A graph without embedded source DSL cannot be checked.";
        els.fields.appendChild(item);
      } else {
        names.slice(0, 128).forEach(name => {
          const item = document.createElement("li");
          const property = properties[name];
          item.textContent = name + " · " + (object(property) && typeof property.type === "string" ? property.type : "unspecified")
            + " · " + (required.includes(name) ? "Required" : "Optional");
          els.fields.appendChild(item);
        });
        try {
          const encoded = JSON.stringify(schema, null, 2);
          els.schema.value = encoder.encode(encoded).length <= REPORT_BYTES ? encoded : "Schema is too large to display. Validate the source DSL.";
        } catch (_error) { els.schema.value = "Schema cannot be displayed. Validate the source DSL."; }
        els.schemaDetails.hidden = false;
      }
      invalidate();
    }
    async function check() {
      invalidate();
      if (!source) return;
      const current = revision;
      let workflow, snapshot, raw;
      try {
        workflow = options.getWorkflow();
        if (!workflow) { status("Fix the draft's DSL errors, then check input again.", "error"); return; }
        snapshot = JSON.stringify(workflow);
        raw = els.input.value;
        if (encoder.encode(raw).length > INPUT_BYTES) throw new Error("size");
        if (raw.trim()) {
          const parsed = JSON.parse(raw, (_key, value) => {
            if (typeof value === "number" && !Number.isFinite(value)) throw new Error("finite");
            return value;
          });
          if (!object(parsed)) throw new Error("object");
        }
      } catch (_error) {
        status("Use a finite JSON object of at most 1 MiB. Correct the input and check again.", "error");
        return;
      }
      // Send the original JSON text so browser number rounding never changes the payload.
      const body = "{\"workflow\":" + snapshot + (raw.trim() ? ",\"input\":" + raw : "") + "}";
      if (encoder.encode(snapshot).length > 2 * INPUT_BYTES || encoder.encode(body).length > 3 * INPUT_BYTES + 1024) {
        status("This draft exceeds the local check's size limit. Use the CLI preflight.", "error"); return;
      }
      controller = new AbortController();
      const signal = controller.signal;
      els.check.disabled = true;
      status("Checking input and required mappings…", "checking");
      try {
        const response = await fetch(URL, { method: "POST", credentials: "omit", cache: "no-store",
          headers: { "Content-Type": "application/json" }, body, signal });
        if (current !== revision) return;
        if ([404, 405, 501].includes(response.status)) {
          status("Start skill2workflow ui to check input. Static hosting cannot run this check.", "unavailable"); return;
        }
        if (!response.ok) throw new Error("unavailable");
        const report = validateReport(await readReport(response), workflow);
        if (current !== revision) return;
        if (els.input.value !== raw || JSON.stringify(options.getWorkflow()) !== snapshot) {
          invalidate(); status("The draft or input changed. Check input again.", "unchecked"); return;
        }
        status(report.ready ? "Input ready. Schema and required mapping sources pass; no workflow was run."
          : "Input blocked. Correct the fields or mappings below and check again.", report.ready ? "ready" : "blocked");
        for (const issue of report.issues) {
          const item = document.createElement("li");
          const node = workflow.nodes.find(node => node.id === issue.node_id);
          const index = issue.path[3];
          const mapping = node && node.connector && node.connector.request && node.connector.request.input_mapping;
          const pointer = Array.isArray(mapping) && count(index, 2000) && mapping[index] && mapping[index].from;
          item.textContent = issue.code === "input_invalid" ? "Input does not match the contract: " + issue.path.join(" / ")
            : "Missing required mapping source " + (typeof pointer === "string" ? pointer : issue.path.join(" / "))
              + (node ? " · " + (node.title || node.id) : "");
          els.issues.appendChild(item);
        }
        if (report.issues.length === 64) {
          const item = document.createElement("li"); item.textContent = "Report limit reached. Review the draft's remaining mappings."; els.issues.appendChild(item);
        }
      } catch (_error) {
        if (current === revision) status("Could not check input. Use valid JSON without duplicate keys, validate DSL, and retry with skill2workflow ui.", "error");
      } finally {
        if (current === revision) { controller = null; els.check.disabled = !source; }
      }
    }
    els.input.addEventListener("input", invalidate);
    els.check.addEventListener("click", check);
    els.clear.addEventListener("click", function () { els.input.value = ""; invalidate(); });
    return { reset, invalidate, check };
  }
  window.skill2workflowInputReview = { create };
})();
