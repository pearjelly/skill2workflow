const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const vm = require('node:vm');
const test = require('node:test');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'web/app.js'), 'utf8');
const vendor = fs.readFileSync(path.join(root, 'web/vendor/litegraph-0.7.18/litegraph.min.js'), 'utf8');
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'examples/workflows/approval-flow.workflow.json'), 'utf8'));
const clone = value => JSON.parse(JSON.stringify(value));

class Element {
  constructor() { this._value = ''; this.textContent = ''; this.children = []; this.classList = {add() {}}; }
  set value(value) { this._value = value == null ? '' : String(value); }
  get value() { return this._value; }
  appendChild(child) { this.children.push(child); }
  replaceChildren(...children) { this.children = children; this.textContent = ''; }
  set innerHTML(value) { assert.equal(value, ''); this.children = []; }
}

function setup() {
  const context = vm.createContext({console: {log() {}, warn() {}, error() {}}, setTimeout, clearTimeout});
  vm.runInContext(vendor, context);
  const elements = new Map();
  const downloads = [];
  let blob;
  context.window = {addEventListener() {}, requestAnimationFrame() {}};
  context.document = {
    getElementById(id) { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
    createElement(tag) {
      if (tag !== 'a') return new Element();
      return {click() { downloads.push({filename:this.download, document:JSON.parse(blob.parts.join(''))}); }};
    },
  };
  context.Blob = class {constructor(parts) { this.parts = parts; }};
  context.URL = {createObjectURL(value) { blob = value; return 'blob:local-test'; }, revokeObjectURL() {}};
  const expose = `window.graphTest = {cacheElements, registerNodeTypes, saveGraph, renderInspector,
    get graph() {return graph;}, get source() {return currentWorkflowDsl;},
    addType(type) {const node=LiteGraph.createNode('skill2workflow/'+type);
      node.properties.workflow_node_id='test_'+type; graph.add(node); return node;},
    load(workflow) {currentWorkflowDsl=deepClone(workflow); currentWorkflow=deepClone(workflow.workflow);
      graph=new LGraph(); graph.configure(workflowDslToLiteGraph(currentWorkflowDsl));},
    loadGraph(document) {currentWorkflowDsl=document.extra.source_workflow ? deepClone(document.extra.source_workflow) : null;
      currentWorkflow=deepClone(document.workflow); graph=new LGraph(); graph.configure(deepClone(document));}};`;
  assert.match(source, /\}\)\(\);\s*$/);
  vm.runInContext(source.replace(/\}\)\(\);\s*$/, expose + '\n})();'), context);
  const api = context.window.graphTest;
  api.cacheElements();
  api.registerNodeTypes();
  api.load(fixture);
  return {api, downloads, elements, node:id => api.graph._nodes.find(node => node.properties.workflow_node_id === id),
    save() { api.saveGraph(); return downloads.at(-1)?.document; }};
}

function writeBack(graph, workflow=fixture) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'skill2workflow-graph-test-'));
  try {
    const original = path.join(directory, 'workflow.json');
    const input = path.join(directory, 'graph.json');
    const output = path.join(directory, 'updated.json');
    fs.writeFileSync(original, JSON.stringify(workflow));
    fs.writeFileSync(input, JSON.stringify(graph));
    const result = spawnSync(process.env.SKILL2WORKFLOW_TEST_PYTHON || 'python3',
      ['-m', 'skill2workflow.cli', 'write-back', original, input, '-o', output],
      {cwd:root, env:{...process.env, PYTHONPATH:path.join(root, 'src')}, encoding:'utf8'});
    if (result.error) throw result.error;
    return {status:result.status, message:result.stdout + result.stderr,
      workflow:fs.existsSync(output) ? JSON.parse(fs.readFileSync(output, 'utf8')) : null};
  } finally { fs.rmSync(directory, {recursive:true, force:true}); }
}

test('Save Graph materializes titles omitted by the real pinned LiteGraph serializer', () => {
  const context = setup();
  const raw = clone(context.api.graph.serialize());
  assert.equal(raw.nodes.find(node => node.properties.workflow_node_id === 'start').title, undefined);
  const exported = context.save();
  for (const node of exported.nodes) {
    assert.equal(node.title, context.api.graph.getNodeById(node.id).title);
  }
  const result = writeBack(exported);
  assert.equal(result.status, 0, result.message);
  assert.deepEqual(result.workflow, fixture);
});

test('custom and type-default title edits survive CLI write-back without changing execution fields', () => {
  const context = setup();
  const before = clone(context.api.source);
  const step = context.api.graph._nodes.find(node => node.properties.node_type === 'step');
  step.title = 'Step';
  context.node('start').title = '开始 العربية 😀 <script>literal</script>';
  const exported = context.save();
  const result = writeBack(exported);
  assert.equal(result.status, 0, result.message);
  const expected = clone(fixture);
  expected.nodes.find(node => node.id === step.properties.workflow_node_id).title = 'Step';
  expected.nodes.find(node => node.id === 'start').title = context.node('start').title;
  assert.deepEqual(result.workflow, expected);
  assert.deepEqual(exported.extra.source_workflow, expected);
  assert.deepEqual(clone(context.api.source), before);
});

test('all registered types retain explicit titles even in graph-only exports', () => {
  const context = setup();
  context.api.loadGraph({workflow:clone(fixture.workflow),extra:{},nodes:[],links:[]});
  const types = ['start','step','human_gate','tool_call','verification','instruction','failure','end'];
  for (const type of types) {
    context.api.addType(type);
  }
  assert.ok(context.api.graph.serialize().nodes.every(node => node.title === undefined));
  const exported = context.save();
  assert.equal(exported.nodes.length, types.length);
  assert.equal(exported.extra.source_workflow, undefined);
  for (const node of exported.nodes) assert.equal(node.title, context.api.graph.getNodeById(node.id).title);
});

test('repeated Save Graph and reload preserves titles, bindings and topology', () => {
  const context = setup();
  for (let index=0; index<3; index++) {
    const graph = context.save();
    const result = writeBack(graph);
    assert.equal(result.status, 0, result.message);
    assert.deepEqual(result.workflow, fixture);
    context.api.loadGraph(graph);
  }
});

test('title completion never repairs explicit blanks, changed identities or topology', () => {
  const context = setup();
  context.node('start').title = '';
  const empty = context.save();
  assert.equal(empty.nodes.find(node => node.properties.workflow_node_id === 'start').title, '');
  const result = writeBack(empty);
  assert.equal(result.status, 1);
  assert.match(result.message, /title must not be empty/);
  context.node('start').title = 'Start';
  const graph = context.save();
  const topology = clone(graph);
  topology.links.pop();
  assert.match(writeBack(topology).message, /graph topology does not match/);
  const identity = clone(graph);
  identity.nodes[0].properties.workflow_node_id = 'forged';
  assert.match(writeBack(identity).message, /graph node set does not match/);
});

test('invalid inspector input blocks graph download and valid saves announce success', () => {
  for (const graphOnly of [false,true]) {
    const context = setup();
    const document = context.save();
    assert.equal(context.elements.get('status-pill').textContent, 'Graph saved');
    assert.equal(context.downloads.length, 1);
    if (graphOnly) {
      delete document.extra.source_workflow;
      context.api.loadGraph(document);
    }
    const node = context.api.graph._nodes.find(node => node.properties.node_type === 'step');
    node.properties.connector = {id:'http',kind:'http',request:{url:'https://example.invalid'}};
    context.api.renderInspector(node);
    context.elements.get('node-http-body').value = '{';
    context.api.saveGraph();
    assert.equal(context.downloads.length, 1);
    assert.equal(context.elements.get('status-pill').textContent, 'Invalid DSL');
  }
});

test('Save Graph synchronizes pending allowlisted form edits before serialization', () => {
  for (const graphOnly of [false,true]) {
    const context = setup();
    if (graphOnly) {
      const document = context.save();
      delete document.extra.source_workflow;
      context.api.loadGraph(document);
    }
    const node = context.api.graph._nodes.find(node => node.properties.node_type === 'step');
    context.api.renderInspector(node);
    context.elements.get('node-timeout').value = '1234';
    context.elements.get('node-retry-backoff').value = '25';
    const graph = context.save();
    const exported = graph.nodes.find(item => item.id === node.id);
    assert.equal(exported.properties.timeout_ms, 1234);
    assert.equal(exported.properties.retry.backoff_ms, 25);
    const result = writeBack(graph);
    assert.equal(result.status, 0, result.message);
    const expected = clone(fixture);
    const changed = expected.nodes.find(item => item.id === node.properties.workflow_node_id);
    changed.timeout_ms = 1234;
    changed.retry.backoff_ms = 25;
    assert.deepEqual(result.workflow, expected);
    if (!graphOnly) assert.deepEqual(result.workflow, graph.extra.source_workflow);
  }
});

test('workflow input contracts survive browser graph save and strict CLI write-back', () => {
  const context = setup();
  const workflow = clone(fixture);
  workflow.input_schema = {type:'object',properties:{record_id:{type:'string',minLength:1}},
    required:['record_id'],additionalProperties:false};
  context.api.load(workflow);
  const graph = context.save();
  assert.deepEqual(graph.extra.source_workflow.input_schema, workflow.input_schema);
  const result = writeBack(graph, workflow);
  assert.equal(result.status, 0, result.message);
  assert.deepEqual(result.workflow, workflow);
  assert.deepEqual(clone(context.api.source), workflow);
});
