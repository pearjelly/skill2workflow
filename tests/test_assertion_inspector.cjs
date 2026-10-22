const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
const start = source.indexOf('  function renderHttpAssertionReview(');
const end = source.indexOf('  function renderInspector(', start);

class Element {
  constructor() { this.children = []; this.textContent = ''; this.value = ''; this.hidden = false; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; this.textContent = ''; }
  set innerHTML(value) { throw new Error('Review must never interpret markup'); }
}

function setup() {
  assert.ok(start >= 0 && end > start, 'The actual inspector renderer must exist');
  const els = Object.fromEntries(['assertionSection', 'nodeAssertionMethod', 'nodeAssertionUrl',
    'nodeAssertionRules', 'nodeAssertionSuccess', 'nodeAssertionFailure', 'nodeAssertionConfig']
    .map(key => [key, new Element()]));
  const currentWorkflowDsl = { nodes: [
    { id: 'verify', on_success: 'deliver', on_failure: 'failure' },
    { id: 'deliver', title: 'Deliver result' }, { id: 'failure', title: 'Failure' },
  ] };
  const context = { els, currentWorkflowDsl, document: { createElement: () => new Element() } };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return context;
}

function binding() {
  return { id: 'http_assert', kind: 'http_assert', request: { url: 'https://example.invalid/result' },
    assertions: [{ path: '/ready', equals: true }, { path: '/value', equals: 'true' },
      { path: '/count', equals: 0 }, { path: '/empty', equals: null }] };
}
function text(element) { return [element.textContent, ...element.children.map(text)].join(' '); }

test('renders typed expectations and authoritative source destinations', () => {
  const context = setup();
  context.renderHttpAssertionReview({ properties: { workflow_node_id: 'verify' } }, binding());
  assert.equal(context.els.assertionSection.hidden, false);
  assert.equal(context.els.nodeAssertionMethod.textContent, 'GET');
  assert.equal(context.els.nodeAssertionUrl.value, 'https://example.invalid/result');
  const rules = text(context.els.nodeAssertionRules);
  for (const value of ['/ready', 'true', '"true"', '0', 'null']) assert.ok(rules.includes(value));
  assert.match(context.els.nodeAssertionSuccess.textContent, /Deliver result.*deliver/);
  assert.match(context.els.nodeAssertionFailure.textContent, /Failure.*failure/);
});

test('hostile strings stay literal and rendering never changes bindings or DSL', () => {
  const context = setup();
  const connector = binding();
  connector.assertions[0] = { path: '/<img src=x onerror=alert(1)>', equals: '</textarea><script>alert(1)</script>' };
  const before = JSON.stringify({ connector, workflow: context.currentWorkflowDsl });
  context.renderHttpAssertionReview({ properties: { workflow_node_id: 'verify' } }, connector);
  assert.ok(text(context.els.nodeAssertionRules).includes('<script>'));
  assert.equal(JSON.stringify({ connector, workflow: context.currentWorkflowDsl }), before);
  assert.deepEqual(JSON.parse(context.els.nodeAssertionConfig.value), connector);
});

test('selection changes hide and clear the complete prior review', () => {
  const context = setup();
  context.renderHttpAssertionReview({ properties: { workflow_node_id: 'verify' } }, binding());
  context.renderHttpAssertionReview({ properties: {} }, { id: 'http' });
  assert.equal(context.els.assertionSection.hidden, true);
  assert.equal(context.els.nodeAssertionUrl.value, '');
  assert.equal(context.els.nodeAssertionConfig.value, '');
  assert.equal(context.els.nodeAssertionRules.children.length, 0);
  assert.equal(context.els.nodeAssertionSuccess.textContent, '');
  assert.equal(context.els.nodeAssertionFailure.textContent, '');
  context.renderHttpAssertionReview(null, null);
  assert.equal(context.els.assertionSection.hidden, true);
});

test('missing assertions and absent source DSL have honest empty states', () => {
  const context = setup();
  context.currentWorkflowDsl = null;
  context.renderHttpAssertionReview({ properties: {} }, { id: 'http_assert', request: {} });
  assert.match(text(context.els.nodeAssertionRules), /No assertions/);
  assert.match(context.els.nodeAssertionSuccess.textContent, /Source DSL unavailable/);
});

test('JSON-shaped method and destination titles cannot interrupt review', () => {
  const context = setup();
  for (const value of [{ toString: null }, ['GET'], 1, false, null, '']) {
    const connector = binding();
    connector.request.method = value;
    context.currentWorkflowDsl.nodes[1].title = value;
    const before = JSON.stringify({ connector, workflow: context.currentWorkflowDsl });
    context.renderHttpAssertionReview({ properties: { workflow_node_id: 'verify' } }, connector);
    assert.equal(context.els.nodeAssertionMethod.textContent, 'Invalid method');
    assert.equal(context.els.nodeAssertionSuccess.textContent, 'deliver (deliver)');
    assert.deepEqual(JSON.parse(context.els.nodeAssertionConfig.value), connector);
    assert.equal(JSON.stringify({ connector, workflow: context.currentWorkflowDsl }), before);
  }
});
