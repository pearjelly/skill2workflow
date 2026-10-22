const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(process.env.S2W_EDITOR_MODULE || path.join(root, 'web/app.js'), 'utf8');
const vendor = fs.readFileSync(process.env.S2W_EDITOR_VENDOR || path.join(root, 'web/vendor/litegraph-0.7.18/litegraph.min.js'), 'utf8');
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'examples/workflows/approval-flow.workflow.json'), 'utf8'));
const markdown = '---\nname: reviewed\ndescription: Synthetic example.\nname: private-value-canary\n---\n## Steps\n1. Review\n';
const version = 'skill2workflow-skill-compile-diagnostic-0.1.0';
const rejected = (code='frontmatter_duplicate_key', line=4) => ({error:'skill compile rejected', diagnostic:{schema_version:version, code, line}});
class Element {
  constructor() {this.value='';this.textContent='';this.children=[];this.classList={add(){}};}
  appendChild(child) {this.children.push(child);}
  replaceChildren(...children) {this.children=children;this.textContent='';}
  set innerHTML(value) {assert.equal(value,'');this.children=[];}
}
function response(payload, status=400, raw=JSON.stringify(payload)) {
  const bytes=new TextEncoder().encode(raw);
  return {ok:status>=200 && status<300,status,headers:{get:()=>String(bytes.length)},json:async()=>payload,
    body:new ReadableStream({start(c){c.enqueue(bytes);c.close();}})};
}
function setup(fetcher) {
  const elements=new Map();
  const context=vm.createContext({console:{log(){},warn(){},error(){}},setTimeout,clearTimeout,TextEncoder,TextDecoder,AbortController,fetch:fetcher});
  vm.runInContext(vendor,context);
  context.window={addEventListener(){},requestAnimationFrame(){}};
  context.document={getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement(){return new Element();}};
  const expose=`window.recoveryTest={cacheElements,registerNodeTypes,stageSelectedSkill,compileStagedSkill,loadDocument,
    get graph(){return graph;},get source(){return currentWorkflowDsl;},
    load(workflow){graph=new LGraph();loadDocument(workflow,'Loaded test draft');}};`;
  vm.runInContext(source.replace(/\}\)\(\);\s*$/,expose+'\n})();'),context);
  const api=context.window.recoveryTest;
  api.cacheElements();api.registerNodeTypes();api.load(JSON.parse(JSON.stringify(fixture)));
  return {context,api,elements,issues:()=>elements.get('skill-compile-feedback').textContent,
    async stage(text=markdown){const bytes=new TextEncoder().encode(text);await api.stageSelectedSkill({target:{value:'',files:[{size:bytes.length,arrayBuffer:async()=>bytes.buffer}]}});}};
}
function compiled() {return {workflow:JSON.parse(JSON.stringify(fixture)),review:{schema_version:'skill2workflow-skill-compile-review-0.1.0',ordered_step_count:4,executable_node_count:4,human_gate_count:1,verification_node_count:0,hard_gate_count:1,notices:[]}};}

test('compile refusal gives a safe location and recovery without replacing the active draft',async()=>{
  let observed;
  const ui=setup(async(url,options)=>{observed={url,options};return response(rejected());});
  const before=JSON.stringify(ui.api.source);
  await ui.stage();await ui.api.compileStagedSkill();
  assert.equal(JSON.parse(observed.options.body).diagnostics,true);
  assert.equal(observed.options.credentials,'omit');
  assert.match(ui.issues(),/line 4/i);assert.match(ui.issues(),/one declaration/i);assert.match(ui.issues(),/choose.*compile again/i);
  assert.doesNotMatch(ui.issues(),/private-value-canary|frontmatter_duplicate_key/);
  assert.equal(JSON.stringify(ui.api.source),before);
  assert.equal(ui.elements.get('skill-compile-feedback').hidden,false);
  assert.equal(ui.elements.get('validation-list').children[0].textContent,'Graph structure is valid.');
});

test('oversized and invalid UTF-8 diagnostics are bounded and never displayed',async()=>{
  for(const declared of [true,false]){
    let canceled=false;const r=response({private:'private-value-canary'.repeat(200)});
    const bytes=new TextEncoder().encode('private-value-canary'.repeat(200));
    r.headers.get=()=>declared?String(bytes.length):null;
    r.body=new ReadableStream({start(c){c.enqueue(bytes);},cancel(){canceled=true;}});
    const ui=setup(async()=>r);await ui.stage();await ui.api.compileStagedSkill();assert.equal(canceled,true);assert.doesNotMatch(ui.issues(),/private-value-canary/);
  }
  const r=response({});r.headers.get=()=>null;r.body=new ReadableStream({start(c){c.enqueue(new Uint8Array([255]));c.close();}});
  const ui=setup(async()=>r);await ui.stage();await ui.api.compileStagedSkill();assert.match(ui.issues(),/Review/);
});

test('known syntax and unsupported forms explain the next edit in fixed copy',async()=>{
  for(const [code,expected] of [['frontmatter_invalid',/quoting.*indentation/i],['frontmatter_unsupported',/supported.*strings|flat metadata/i]]){
    const ui=setup(async()=>response(rejected(code,3)));await ui.stage();await ui.api.compileStagedSkill();
    assert.match(ui.issues(),/line 3/i);assert.match(ui.issues(),expected);
  }
});

test('malformed, private, unknown and oversized error evidence never becomes visible source text',async()=>{
  const cases=[{error:'private-response-canary'},rejected('private-code-canary'),rejected('frontmatter_invalid',true),
    rejected('frontmatter_invalid',99999),{...rejected(),diagnostic:{...rejected().diagnostic,schema_version:'private-version-canary'}},
    {...rejected(),diagnostic:{...rejected().diagnostic,extra:'private-extra-canary'}},{huge:'private-value-canary'.repeat(200)},null];
  for(const payload of cases){const ui=setup(async()=>response(payload));await ui.stage();await ui.api.compileStagedSkill();
    assert.doesNotMatch(ui.issues(),/private-|line 4|line 99999/);assert.match(ui.issues(),/correct|review/i);}
});

test('static, size, offline and older-helper failures have honest fallback actions',async()=>{
  for(const [fetcher,expected] of [[async()=>response({},404),/skill2workflow ui/i],
    [async()=>response({},413),/limit.*CLI|CLI.*limit/i],[async()=>{throw new Error('private-network-canary');},/retry|try again/i],
    [async()=>response({error:'skill compile rejected'}),/rejected.*correct|review/i]]){
    const ui=setup(fetcher);await ui.stage();await ui.api.compileStagedSkill();assert.match(ui.issues(),expected);assert.doesNotMatch(ui.issues(),/private-network-canary/);}
});

test('correcting and reselecting a Skill can compile successfully after a rejection',async()=>{
  let next=response(rejected());const ui=setup(async()=>next);await ui.stage();await ui.api.compileStagedSkill();
  next=response(compiled(),200);await ui.stage('---\nname: corrected\n---\n## Steps\n1. Review\n');await ui.api.compileStagedSkill();
  assert.equal(ui.elements.get('status-pill').textContent,'Compiled SKILL.md');assert.doesNotMatch(ui.issues(),/repeats|rejected|failed/i);
});

test('selection replacement prevents stale failures and permits a new compile',async()=>{
  let resolve;const ui=setup(()=>new Promise(done=>{resolve=done;}));await ui.stage();const pending=ui.api.compileStagedSkill();
  await ui.stage('---\nname: corrected\n---\n## Steps\n1. Review\n');
  assert.equal(ui.elements.get('compile-skill').disabled,false);
  resolve(response(rejected()));await pending;assert.doesNotMatch(ui.issues(),/line 4|repeated|repeats/);
});

test('draft replacement and edits cannot be overwritten by an earlier compile response',async()=>{
  for(const edit of [false,true]){let resolve;const ui=setup(()=>new Promise(done=>{resolve=done;}));await ui.stage();const pending=ui.api.compileStagedSkill();
    if(edit)ui.api.graph._nodes[1].title='Current local edit';
    else{const newer=compiled().workflow;newer.workflow.name='Newly loaded draft';ui.api.loadDocument(newer,'Newly loaded draft');}
    const snapshot=JSON.stringify(ui.api.graph.serialize());resolve(response(compiled(),200));await pending;
    assert.equal(JSON.stringify(ui.api.graph.serialize()),snapshot);
    if(!edit)assert.equal(ui.api.source.workflow.name,'Newly loaded draft');}
});

test('a slower prior file read cannot replace the most recently selected Skill',async()=>{
  let finish;let sent;
  const ui=setup(async(_url,options)=>{sent=JSON.parse(options.body);return response(rejected('skill_invalid',null));});
  const older=ui.api.stageSelectedSkill({target:{value:'',files:[{size:5,arrayBuffer:()=>new Promise(done=>{finish=done;})}]}});
  const current='---\nname: current\n---\n## Steps\n1. Review\n';await ui.stage(current);
  finish(new TextEncoder().encode('older').buffer);await older;await ui.api.compileStagedSkill();assert.equal(sent.skill_markdown,current);
});

test('a pending file read cannot repaint feedback after a document replacement',async()=>{
  let finish;let calls=0;const ui=setup(async()=>{calls++;return response(rejected());});
  const pending=ui.api.stageSelectedSkill({target:{value:'',files:[{size:5,arrayBuffer:()=>new Promise(done=>{finish=done;})}]}});
  ui.api.loadDocument(compiled().workflow,'Newly loaded draft');finish(new Uint8Array([255]).buffer);await pending;
  assert.equal(ui.elements.get('status-pill').textContent,'Newly loaded draft');assert.equal(ui.issues(),'');
  await ui.api.compileStagedSkill();assert.equal(calls,0);
});

test('invalid successful responses do not echo response text or replace the draft',async()=>{
  const r=response({},200);r.json=async()=>{throw new Error('private-success-canary');};
  const ui=setup(async()=>r);const before=JSON.stringify(ui.api.source);await ui.stage();await ui.api.compileStagedSkill();
  assert.doesNotMatch(ui.issues(),/private-success-canary/);assert.match(ui.issues(),/invalid compiled draft/);assert.equal(JSON.stringify(ui.api.source),before);
});

test('actual backend diagnostics render through the real editor module',async()=>{
  let fixtures;
  if(process.env.S2W_EDITOR_MODULE){
    assert.ok(process.env.S2W_COMPILE_DIAGNOSTICS && process.env.S2W_EDITOR_VENDOR,'Served-module qualification requires real reports and the served vendor');
    fixtures=JSON.parse(fs.readFileSync(process.env.S2W_COMPILE_DIAGNOSTICS,'utf8'));
  }else{
    const inputs=[markdown,'---\nname: reviewed\ndescription: "private-value-canary\n---',
      '---\nname: reviewed\ndescription: *private-value-canary\n---','## Workflow\n1. Review\n## Steps\n1. Deliver\n'];
    const code='import json,sys\nfrom skill2workflow.parser import parse_skill_text\nfrom skill2workflow.frontmatter import skill_compile_diagnostic\nrows=[]\nfor text in json.load(sys.stdin):\n try: parse_skill_text(text)\n except ValueError as error: rows.append({"source":text,"reply":{"error":"skill compile rejected","diagnostic":skill_compile_diagnostic(error)}})\nprint(json.dumps(rows))';
    const child=spawnSync(process.env.SKILL2WORKFLOW_TEST_PYTHON||'python3',['-c',code],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},input:JSON.stringify(inputs),encoding:'utf8',timeout:5000});
    if(child.error)throw child.error;assert.equal(child.status,0,child.stderr);fixtures=JSON.parse(child.stdout);
  }
  assert.equal(fixtures.length,4);
  const expected=[/one declaration/i,/quoting.*indentation/i,/supported.*strings|flat metadata/i,/was rejected.*Review/];
  for(const [index,fixture] of fixtures.entries()){
    const ui=setup(async()=>response(fixture.reply));await ui.stage(fixture.source);await ui.api.compileStagedSkill();
    assert.match(ui.issues(),expected[index]);assert.doesNotMatch(ui.issues(),/private-|frontmatter_duplicate_key|skill_invalid/);
  }
});
