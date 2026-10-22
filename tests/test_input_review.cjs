const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const file = path.join(__dirname, '../web/input-review.js');

class Element {
  constructor() { this.children = []; this.textContent = ''; this.value = ''; this.disabled = false; this.hidden = false; this.open = false; this.dataset = {}; this.events = {}; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; this.textContent = ''; }
  addEventListener(name, callback) { this.events[name] = callback; }
  setAttribute(name, value) { this[name] = value; }
  dispatch(name) { if (this.events[name]) this.events[name](); }
  set innerHTML(value) { throw new Error('Input review must not interpret markup'); }
}
function text(element) { return [element.textContent, ...element.children.map(text)].join(' '); }
function draft() {
  return { workflow: { id: 'workflow_review', version: '0.1.0', status: 'draft' },
    input_schema: { type: 'object', properties: { id: { type: 'string', minLength: 1 }, nested: { type: 'object' } }, required: ['id'], additionalProperties: false },
    nodes: [{ id: 'submit', title: 'Submit', connector: { request: { input_mapping: [{ from: '/input/id', to: '/body/id' }] } } }] };
}
function report(workflow, ready = true) {
  return { schema_version: 'skill2workflow-workflow-preflight-0.1.0', workflow: workflow.workflow, ready,
    input: { status: 'valid' }, summary: { node_count: 1, connector_node_count: 1,
      side_effecting_node_count: 1, mapping_count: 1, blocked_node_count: ready ? 0 : 1, issue_count: ready ? 0 : 1 },
    nodes: [{}], issues: ready ? [] : [{ code: 'required_mapping_input_missing', severity: 'error', node_id: 'submit', path: ['connector', 'request', 'input_mapping', 0, 'from'] }],
    safety: { side_effect_free: true, connector_calls: false, credentials_resolved: false, raw_values_included: false } };
}
function response(payload, status = 200) {
  const bytes = new TextEncoder().encode(JSON.stringify(payload));
  return { ok: status >= 200 && status < 300, status,
    headers: { get: () => String(bytes.length) }, body: new ReadableStream({ start(c) { c.enqueue(bytes); c.close(); } }) };
}
function setup(fetcher) {
  const elements = Object.fromEntries(['panel', 'summary', 'fields', 'schema', 'schemaDetails', 'input', 'check', 'clear', 'status', 'issues'].map(key => [key, new Element()]));
  const context = { window: {}, document: { createElement: () => new Element() }, TextEncoder, TextDecoder,
    AbortController, fetch: fetcher || (async () => response(report(context.workflow))), workflow: draft() };
  vm.createContext(context);
  vm.runInContext(fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '', context);
  assert.equal(typeof context.window.skill2workflowInputReview?.create, 'function', 'Actual input-review module must exist');
  const review = context.window.skill2workflowInputReview.create({ elements, getWorkflow: () => context.workflow });
  review.reset(context.workflow);
  return { context, elements, review };
}

test('contract review exposes types and required fields without changing the DSL', () => {
  const { context, elements, review } = setup();
  context.workflow.input_schema.properties['<img onerror=alert(1)>'] = { type: 'string', enum: ['</textarea><script>x</script>'] };
  const before = JSON.stringify(context.workflow);
  review.reset(context.workflow);
  assert.match(text(elements.fields), /id.*string.*Required/);
  assert.match(text(elements.fields), /nested.*object.*Optional/);
  assert.ok(text(elements.fields).includes('<img'));
  assert.equal(JSON.stringify(JSON.parse(elements.schema.value)), JSON.stringify(context.workflow.input_schema));
  assert.equal(elements.panel.open, true);
  assert.equal(JSON.stringify(context.workflow), before);
});

test('new documents clear ephemeral input and graph-only/absent schema states are honest', () => {
  const { context, elements, review } = setup();
  elements.input.value = 'private-value';
  review.reset(null);
  assert.equal(elements.input.value, '');
  assert.equal(elements.check.disabled, true);
  assert.match(elements.status.textContent, /source DSL/i);
  const open = draft(); delete open.input_schema;
  context.workflow = open; review.reset(open);
  assert.equal(elements.check.disabled, false);
  assert.match(text(elements.fields), /No declared input schema/);
  assert.match(text(elements.fields), /mappings/);
});

test('checking uses exact raw JSON numbers and never mixes test input into source', async () => {
  let observed;
  const { context, elements, review } = setup(async (url, options) => { observed = { url, options }; return response(report(context.workflow)); });
  const before = JSON.stringify(context.workflow);
  elements.input.value = '{"id":"private-input-canary","large":9007199254740993}';
  await review.check();
  assert.equal(observed.url, '/api/v1/draft-input-preflights');
  assert.equal(observed.options.credentials, 'omit');
  assert.ok(observed.options.body.includes('9007199254740993'));
  assert.equal(elements.status.dataset.state, 'ready');
  assert.match(elements.status.textContent, /Input ready/);
  assert.ok(!text(elements.status).includes('private-input-canary'));
  assert.equal(JSON.stringify(context.workflow), before);
});

test('blocked mappings identify their source and node, not submitted values', async () => {
  const { context, elements, review } = setup(async () => response(report(context.workflow, false)));
  elements.input.value = '{"private":"input-value-canary"}';
  await review.check();
  assert.equal(elements.status.dataset.state, 'blocked');
  assert.match(text(elements.issues), /\/input\/id/);
  assert.match(text(elements.issues), /Submit/);
  assert.ok(!text(elements.issues).includes('input-value-canary'));
});

test('input edits and document replacement invalidate pending ready responses', async () => {
  for (const replace of [false, true]) {
    let resolve;
    const { context, elements, review } = setup(() => new Promise(r => { resolve = r; }));
    elements.input.value = '{"id":"old"}';
    const pending = review.check();
    assert.equal(elements.status.dataset.state, 'checking');
    if (replace) { context.workflow = draft(); review.reset(context.workflow); }
    else { elements.input.value = '{"id":"new"}'; elements.input.dispatch('input'); }
    resolve(response(report(context.workflow)));
    await pending;
    assert.notEqual(elements.status.dataset.state, 'ready');
    assert.equal(elements.issues.children.length, 0);
    assert.equal(elements.check.disabled, false);
    if (replace) assert.equal(elements.input.value, '');
  }
});

test('draft edits during a check cannot repaint an earlier ready result', async () => {
  let resolve;
  const { context, elements, review } = setup(() => new Promise(r => { resolve = r; }));
  const old = JSON.parse(JSON.stringify(context.workflow));
  const pending = review.check();
  context.workflow.nodes[0].title = 'Changed title';
  resolve(response(report(old)));
  await pending;
  assert.notEqual(elements.status.dataset.state, 'ready');
  assert.match(elements.status.textContent, /changed|again/i);
});

test('invalid and oversized input never sends a request; clear removes prior results', async () => {
  let calls = 0;
  const { elements, review } = setup(async () => { calls++; throw new Error('unexpected'); });
  for (const value of ['{', '[]', 'null', '{"x":1e309}', '{"x":"' + 'x'.repeat(1048576) + '"}']) {
    elements.input.value = value;
    await review.check();
    assert.equal(elements.status.dataset.state, 'error');
  }
  assert.equal(calls, 0);
  elements.clear.dispatch('click');
  assert.equal(elements.input.value, '');
  assert.equal(elements.issues.children.length, 0);
});

test('static hosting, malformed and unsafe responses do not claim validation passed', async () => {
  for (const mode of ['offline', 'unsupported-post', 'method-not-allowed', 'malformed', 'unsafe', 'oversized']) {
    const { context, elements, review } = setup(async () => {
      if (mode === 'offline') return response({}, 404);
      if (mode === 'unsupported-post') return response({}, 501);
      if (mode === 'method-not-allowed') return response({}, 405);
      if (mode === 'oversized') return response({ text: 'x'.repeat(65536) });
      const payload = report(context.workflow);
      if (mode === 'malformed') payload.schema_version = 'wrong';
      if (mode === 'unsafe') payload.safety.connector_calls = true;
      return response(payload);
    });
    await review.check();
    assert.notEqual(elements.status.dataset.state, 'ready');
    if (['offline', 'unsupported-post', 'method-not-allowed'].includes(mode)) {
      assert.equal(elements.status.dataset.state, 'unavailable');
      assert.match(elements.status.textContent, /Static hosting/);
    }
  }
});
