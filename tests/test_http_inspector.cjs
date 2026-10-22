const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
const clone = value => JSON.parse(JSON.stringify(value));

class Element {
  constructor() { this._value = ''; this.children = []; this.textContent = ''; }
  set value(value) { this._value = value == null ? '' : String(value); }
  get value() { return this._value; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; }
  set innerHTML(value) { throw new Error('Inspector must not interpret markup'); }
}

function setup(connector) {
  const elements = new Map();
  const context = { window: { addEventListener() {} }, document: {
    getElementById(id) { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
    createElement() { return new Element(); },
  } };
  vm.createContext(context);
  const exposure = `window.inspectorTest = {cacheElements, renderInspector, syncInspectorToSelectedNode,
    workflowDslFromGraph, setContext(workflow, nodes) { currentWorkflowDsl = workflow; graph = {_nodes:nodes}; }};`;
  assert.match(source, /\}\)\(\);\s*$/);
  vm.runInContext(source.replace(/\}\)\(\);\s*$/, exposure + '\n})();'), context);
  const api = context.window.inspectorTest;
  const workflow = {nodes:[{id:'api', type:'tool_call', title:'API', connector:clone(connector)}], edges:[]};
  const node = {title:'API', properties:{workflow_node_id:'api', node_type:'tool_call', connector:clone(connector)}};
  api.setContext(workflow, [node]);
  api.cacheElements();
  api.renderInspector(node);
  return {api, node, workflow, field:id => elements.get('node-http-' + id)};
}

function binding(request) { return {id:'http', kind:'http', request}; }
function exported(context) { return clone(context.api.workflowDslFromGraph().nodes[0].connector); }

test('inspecting and saving a bodyless GET preserves every omitted field', () => {
  const connector = binding({url:'https://example.invalid/read', response_mode:'metadata',
    input_mapping:[{from:'/input/id',to:'/query/id'}], allowed_origins:['https://example.invalid']});
  connector.credentials = [{target:'header',name:'Authorization',handle:'api_token'}];
  const context = setup(connector);
  assert.deepEqual(exported(context), connector);
  assert.deepEqual(clone(context.node.properties.connector), connector);
});

test('a placeholder HTTP binding stays unconfigured until a request is edited', () => {
  const connector = {id:'http',kind:'http'};
  const context = setup(connector);
  assert.deepEqual(exported(context), connector);
  context.field('url').value = 'https://example.invalid/new';
  assert.deepEqual(exported(context), binding({url:'https://example.invalid/new'}));
});

test('explicit JSON body values and zero timeout are not confused with omission', () => {
  for (const body of [null, false, 0, '', [], {}, {message:'中文 العربية 😀 <script>literal</script>'}]) {
    const connector = binding({method:'POST',url:'https://example.invalid/send',body,headers:{},timeout_ms:0});
    assert.deepEqual(exported(setup(connector)), connector);
  }
});

test('changing one field preserves mappings, retention, handles and other omissions', () => {
  const connector = binding({url:'https://example.invalid/read',response_mode:'metadata',
    input_mapping:[{from:'/input/name',to:'/body/name'}]});
  connector.credentials = [{target:'header',name:'Authorization',handle:'api_token'}];
  const context = setup(connector);
  context.field('method').value = 'POST';
  assert.equal(context.api.syncInspectorToSelectedNode(false).ok, true);
  assert.deepEqual(exported(context), {...connector, request:{...connector.request,method:'POST'}});
});

test('reverting controls restores the original request including property absence', () => {
  const connector = binding({url:'https://example.invalid/read'});
  const context = setup(connector);
  const initial = {method:context.field('method').value,body:context.field('body').value};
  context.field('method').value = 'POST';
  context.field('body').value = '{"title":"draft"}';
  assert.equal(context.api.syncInspectorToSelectedNode(false).ok, true);
  context.field('method').value = initial.method;
  context.field('body').value = initial.body;
  assert.deepEqual(exported(context), connector);
});

test('invalid JSON and timeout edits do not partially change the HTTP request', () => {
  for (const [field,value] of [['body','{'],['headers','[]'],['timeout','-1']]) {
    const connector = binding({method:'GET',url:'https://example.invalid/read',body:{original:true}});
    const context = setup(connector);
    context.field('method').value = 'POST';
    context.field('url').value = 'https://example.invalid/changed';
    context.field(field).value = value;
    assert.equal(context.api.syncInspectorToSelectedNode(false).ok, false);
    assert.deepEqual(clone(context.node.properties.connector), connector);
    assert.throws(() => context.api.workflowDslFromGraph());
  }
});

test('clearing declared JSON is explicit rather than silently keeping a hidden payload', () => {
  for (const [field,original,recovery] of [['body',{send:true},/null/],['headers',{'X-Example':'value'},/\{\}/]]) {
    const connector = binding({url:'https://example.invalid/send',[field]:original});
    const context = setup(connector);
    context.field(field).value = '';
    const result = context.api.syncInspectorToSelectedNode(false);
    assert.equal(result.ok, false);
    assert.match(result.error, recovery);
    assert.deepEqual(clone(context.node.properties.connector), connector);
    context.field(field).value = field === 'body' ? 'null' : '{}';
    assert.equal(context.api.syncInspectorToSelectedNode(false).ok, true);
    assert.deepEqual(exported(context).request[field], field === 'body' ? null : {});
  }
});

test('selection changes cannot reuse another node snapshot or edit assertion bindings', () => {
  const context = setup(binding({url:'https://example.invalid/first'}));
  const second = {title:'Other',properties:{workflow_node_id:'other',node_type:'tool_call',
    connector:binding({url:'https://example.invalid/second',body:{second:true}})}};
  context.api.renderInspector(second);
  assert.equal(context.api.syncInspectorToSelectedNode(false).ok, true);
  assert.deepEqual(clone(second.properties.connector), binding({url:'https://example.invalid/second',body:{second:true}}));
  const check = {id:'http_assert',kind:'http_assert',request:{url:'https://example.invalid/check'},assertions:[{path:'/ready',equals:true}]};
  second.properties.connector = clone(check);
  context.api.renderInspector(second);
  context.field('body').value = '{"forbidden":true}';
  assert.equal(context.api.syncInspectorToSelectedNode(false).ok, true);
  assert.deepEqual(clone(second.properties.connector), check);
});

test('empty declared method, timeout and URL have explicit recovery and never partially apply', () => {
  for (const [field,recovery] of [['method',/GET/],['timeout',/0/],['url',/URL/]]) {
    const connector = binding({method:'POST',url:'https://example.invalid/send',timeout_ms:1000});
    const context = setup(connector);
    context.field(field).value = '';
    const result = context.api.syncInspectorToSelectedNode(false);
    assert.equal(result.ok, false);
    assert.match(result.error, recovery);
    assert.deepEqual(clone(context.node.properties.connector), connector);
  }
});
