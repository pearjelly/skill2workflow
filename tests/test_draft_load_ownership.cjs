const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(process.env.S2W_EDITOR_MODULE || path.join(root, 'web/app.js'), 'utf8');
const vendor = fs.readFileSync(process.env.S2W_EDITOR_VENDOR || path.join(root, 'web/vendor/litegraph-0.7.18/litegraph.min.js'), 'utf8');
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'examples/workflows/approval-flow.workflow.json'), 'utf8'));
const copy = value => JSON.parse(JSON.stringify(value));
const draft = name => {const value=copy(fixture);value.workflow.name=name;return value;};
const deferred = () => {let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const reply = data => ({ok:true,json:async()=>data});
const compiled = name => ({workflow:draft(name),review:{schema_version:'skill2workflow-skill-compile-review-0.1.0',ordered_step_count:4,executable_node_count:4,human_gate_count:1,verification_node_count:0,hard_gate_count:1,notices:[]}});
class Element {
  constructor(){this.value='';this.textContent='';this.children=[];this.listeners={};this.classList={add(){}};}
  addEventListener(type,listener){(this.listeners[type] ||= []).push(listener);}
  emit(type){for(const listener of this.listeners[type]||[])listener({target:this});}
  appendChild(child){this.children.push(child);}
  replaceChildren(...children){this.children=children;this.textContent='';}
  set innerHTML(value){assert.equal(value,'');this.children=[];}
}
function setup(fetcher=async()=>reply(draft('Example'))){
  const elements=new Map();
  const context=vm.createContext({console:{log(){},warn(){},error(){}},setTimeout,clearTimeout,TextEncoder,TextDecoder,AbortController,fetch:fetcher});
  vm.runInContext(vendor,context);
  context.window={addEventListener(){},requestAnimationFrame(){}};
  context.document={getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement(){return new Element();}};
  const expose=`window.ownershipTest={cacheElements,registerNodeTypes,bindEvents,loadSelectedFile,loadSample,stageSelectedSkill,compileStagedSkill,loadDocument,
    get graph(){return graph;},get source(){return currentWorkflowDsl;},
    load(value){graph=new LGraph();loadDocument(value,'Loaded test draft');}};`;
  vm.runInContext(source.replace(/\}\)\(\);\s*$/,expose+'\n})();'),context);
  const api=context.window.ownershipTest;api.cacheElements();api.registerNodeTypes();api.load(draft('Original'));api.bindEvents();
  return {api,elements,context,snapshot:()=>JSON.stringify({workflow:api.source,graph:api.graph.serialize()}),
    feedback:()=>elements.get('skill-compile-feedback').textContent,
    json(text,name='selected.json'){return api.loadSelectedFile({target:{value:name,files:[{name,text:()=>text instanceof Promise?text:Promise.resolve(text)}]}});},
    async stage(text='---\nname: reviewed\n---\n## Steps\n1. Review\n'){
      const bytes=new TextEncoder().encode(text);await api.stageSelectedSkill({target:{value:'SKILL.md',files:[{size:bytes.length,arrayBuffer:async()=>bytes.buffer}]}});
    }};
}

test('the most recent JSON selection owns the draft even when an older read finishes last',async()=>{
  const ui=setup(),old=deferred();const first=ui.json(old.promise,'older.json');
  await ui.json(JSON.stringify(draft('Newest')),'newest.json');const after=ui.snapshot();
  old.resolve(JSON.stringify(draft('Older')));await first;assert.equal(ui.snapshot(),after);assert.equal(ui.api.source.workflow.name,'Newest');
});

test('an obsolete JSON read failure cannot repaint the current draft or expose its parser message',async()=>{
  const ui=setup(),old=deferred();const first=ui.json(old.promise);await ui.json(JSON.stringify(draft('Current')));
  const after=ui.snapshot();old.reject(new Error('private-read-canary'));await first;
  assert.equal(ui.snapshot(),after);assert.equal(ui.feedback(),'');assert.equal(ui.elements.get('validation-list').children[0].textContent,'Graph structure is valid.');
});

test('a late example success cannot replace a subsequently loaded JSON draft',async()=>{
  const slow=deferred();let signal;let parsed=false;
  const ui=setup(async(_url,options)=>{signal=options.signal;return slow.promise;});const pending=ui.api.loadSample();
  await ui.json(JSON.stringify(draft('Current JSON')));const after=ui.snapshot();
  slow.resolve({ok:true,json:async()=>{parsed=true;return draft('Old example');}});await pending;
  assert.equal(ui.snapshot(),after);assert.equal(signal.aborted,true);assert.equal(parsed,false);
});

test('an obsolete example failure cannot inject the embedded fallback into a newer draft',async()=>{
  const slow=deferred(),ui=setup(async()=>slow.promise);const pending=ui.api.loadSample();
  await ui.json(JSON.stringify(draft('Current JSON')));const after=ui.snapshot();slow.reject(new Error('private-network-canary'));await pending;
  assert.equal(ui.snapshot(),after);assert.equal(ui.feedback(),'');
});

test('example body parsing is also fenced after a newer example request',async()=>{
  const body=deferred();let calls=0;const ui=setup(async()=>++calls===1?{ok:true,json:()=>body.promise}:reply(draft('New example')));
  const pending=ui.api.loadSample();await Promise.resolve();await ui.api.loadSample();const after=ui.snapshot();
  body.resolve(draft('Old body'));await pending;assert.equal(ui.snapshot(),after);assert.equal(ui.api.source.workflow.name,'New example');
});

test('staging a Skill abandons pending JSON and example loads without needing to compile it',async()=>{
  for(const kind of ['json','example']){
    const old=deferred(),ui=setup(async()=>old.promise);const pending=kind==='json'?ui.json(old.promise):ui.api.loadSample();
    await ui.stage();const after=ui.snapshot();old.resolve(kind==='json'?JSON.stringify(draft('Old JSON')):reply(draft('Old example')));await pending;
    assert.equal(ui.snapshot(),after);assert.equal(ui.elements.get('compile-skill').disabled,false);assert.equal(ui.elements.get('status-pill').textContent,'SKILL staged');
  }
});

test('choosing JSON immediately aborts an older Skill compile before the new file read completes',async()=>{
  const response=deferred(),file=deferred();let signal;const ui=setup(async(_url,options)=>{signal=options.signal;return response.promise;});
  await ui.stage();const compile=ui.api.compileStagedSkill();const before=ui.snapshot();const selected=ui.json(file.promise);
  response.resolve(reply(compiled('Obsolete compiled Skill')));await compile;assert.equal(signal.aborted,true);assert.equal(ui.snapshot(),before);
  file.resolve(JSON.stringify(draft('New JSON')));await selected;assert.equal(ui.api.source.workflow.name,'New JSON');assert.equal(ui.elements.get('compile-skill').disabled,true);
});

test('a pending Skill byte read cannot repaint after a newer JSON selection starts',async()=>{
  const bytes=deferred(),file=deferred(),ui=setup();const staged=ui.api.stageSelectedSkill({target:{value:'',files:[{size:5,arrayBuffer:()=>bytes.promise}]}});
  const selected=ui.json(file.promise);bytes.resolve(new Uint8Array([255]).buffer);await staged;assert.equal(ui.feedback(),'');
  file.resolve(JSON.stringify(draft('New JSON')));await selected;assert.equal(ui.api.source.workflow.name,'New JSON');
});

test('even an uncommitted form edit invalidates pending reads and example responses',async()=>{
  for(const kind of ['json','example'])for(const failure of [false,true]){
    const slow=deferred(),ui=setup(async()=>slow.promise);const pending=kind==='json'?ui.json(slow.promise):ui.api.loadSample();
    ui.elements.get('node-form').emit('input');const after=ui.snapshot();
    if(failure)slow.reject(new Error('private-pending-canary'));else slow.resolve(kind==='json'?JSON.stringify(draft('Old JSON')):reply(draft('Old example')));
    await pending;assert.equal(ui.snapshot(),after);assert.equal(ui.feedback(),'');assert.equal(ui.elements.get('status-pill').textContent,'Draft changed');
  }
});

test('layout changes during a pending import preserve the current graph snapshot',async()=>{
  for(const kind of ['json','example']){
    const slow=deferred(),ui=setup(async()=>slow.promise);const pending=kind==='json'?ui.json(slow.promise):ui.api.loadSample();
    ui.api.graph._nodes[0].pos[0]+=40;const after=ui.snapshot();slow.resolve(kind==='json'?JSON.stringify(draft('Old JSON')):reply(draft('Old example')));
    await pending;assert.equal(ui.snapshot(),after);assert.equal(ui.elements.get('status-pill').textContent,'Draft changed');
  }
});

test('an earlier JSON read cannot overwrite a subsequently compiled Skill',async()=>{
  const old=deferred(),ui=setup(async()=>reply(compiled('Current compiled Skill')));const pending=ui.json(old.promise);
  await ui.stage();await ui.api.compileStagedSkill();const after=ui.snapshot();old.resolve(JSON.stringify(draft('Old JSON')));await pending;
  assert.equal(ui.snapshot(),after);assert.equal(ui.api.source.workflow.name,'Current compiled Skill');
});

test('direct document replacement invalidates pending JSON and example work',async()=>{
  for(const kind of ['json','example']){
    const old=deferred(),ui=setup(async()=>old.promise);const pending=kind==='json'?ui.json(old.promise):ui.api.loadSample();
    ui.api.loadDocument(draft('Direct replacement'),'New document');const after=ui.snapshot();
    old.resolve(kind==='json'?JSON.stringify(draft('Old JSON')):reply(draft('Old example')));await pending;assert.equal(ui.snapshot(),after);
  }
});

test('current JSON read errors offer fixed recovery while keeping the active graph valid',async()=>{
  const ui=setup();const before=ui.snapshot();await ui.json(Promise.reject(new Error('private-read-canary')));
  assert.equal(ui.snapshot(),before);assert.match(ui.feedback(),/Could not load JSON.*Choose.*JSON/i);assert.doesNotMatch(ui.feedback(),/private-read-canary/);
  assert.equal(ui.elements.get('validation-list').children[0].textContent,'Graph structure is valid.');
  await ui.json(JSON.stringify(draft('Corrected')));assert.equal(ui.feedback(),'');assert.equal(ui.api.source.workflow.name,'Corrected');
});

test('the current unavailable example still loads the existing embedded fallback',async()=>{
  const ui=setup(async()=>{throw new Error('offline');});await ui.api.loadSample();
  assert.ok(ui.api.source);assert.equal(ui.elements.get('status-pill').textContent,'embedded-example');assert.equal(ui.feedback(),'');
});

test('revision fencing still works when fetch cancellation is unavailable',async()=>{
  const slow=deferred(),ui=setup(async()=>slow.promise);ui.context.AbortController=undefined;
  const pending=ui.api.loadSample();await ui.json(JSON.stringify(draft('Current JSON')));const after=ui.snapshot();
  slow.resolve(reply(draft('Obsolete example')));await pending;assert.equal(ui.snapshot(),after);
});
