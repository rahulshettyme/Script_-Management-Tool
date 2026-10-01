// Internal regression test (not deployed). Run from project root: node "Internal Tests/js/master_flow_dropdowns.test.js"
// Loads components/master_flow.js against a stubbed DOM + mocked backend; no network calls.
const fs = require('fs'); const assert = require('assert');
const vals = {};
const mkClassList = () => { const set = new Set(); return { toggle(c, on) { (on === undefined ? !set.has(c) : on) ? set.add(c) : set.delete(c); },
  add(c) { set.add(c); }, remove(c) { set.delete(c); }, contains(c) { return set.has(c); } }; };
const mk = id => {
  const own = {};
  const e = { id, get value() { return vals[id] ?? ''; }, set value(v) { vals[id] = v; },
    get checked() { return !!vals['chk:' + id]; }, set checked(v) { vals['chk:' + id] = v; },
    disabled: false, textContent: '', children: [], classList: mkClassList(), style: {},
    setAttribute() {}, closest() { return null; }, appendChild(c) { this.children.push(c); },
    addEventListener(evt, fn) { own[evt] = fn; }, _fire(evt) { own[evt] && own[evt]({ preventDefault() {} }); } };
  Object.defineProperty(e, 'innerHTML', { set() { this.children = []; }, get() { return ''; } });
  return e;
};
const els = {}; let optSeq = 0;
global.document = { getElementById: id => (els[id] = els[id] || mk(id)), createElement: tag => mk('new-' + tag + (optSeq++)) };
global.window = {}; global.alert = m => { throw new Error('ALERT: ' + m); }; global.confirm = () => true;
global.TEMPLATES = { M: { filename: 'QA_Data_Setup_Master.py', batchSize: 5 } }; global.selectedDataType = 'M';
global.authToken = null; global.currentEnvironment = 'QA2'; global.currentTenant = 'qazone2';
global.getEnvUrls = () => ({ apiBaseUrl: 'http://x' });
global.elements = { executeBtn: mk('exec'), loginSection: mk('login-section') };
global.executionResults = []; global.startExecution = () => { executionResults = []; }; global.completeExecution = () => {};
global.updateProgress = () => {}; global.renderExecutionResults = () => {}; global.evaluateRowStatus = r => ({ isPass: r.Status === 'Pass' });

const SOIL = JSON.parse(fs.readFileSync(require('path').join(__dirname, '..', 'fixtures', 'soil_types.json'), 'utf8'));
const IRR = JSON.parse(fs.readFileSync(require('path').join(__dirname, '..', 'fixtures', 'irrigation_types.json'), 'utf8'));
const masterCalls = []; let failIrrigation = false;
global.fetch = async (url, opts) => {
  if (url.startsWith('/api/data-generate/user-info')) return { ok: true, json: async () => ({ id: 1, name: 'U', companyId: 1251 }) };
  if (url.startsWith('/api/data-generate/asset-masters')) {
    masterCalls.push(url); assert.strictEqual(opts.headers.Authorization, 'Bearer ' + authToken);
    const type = new URL('http://h' + url).searchParams.get('type');
    if (type === 'irrigation' && failIrrigation) return { ok: false, status: 500 };
    return { ok: true, json: async () => (type === 'soil' ? SOIL : IRR) };
  }
  throw new Error('unexpected fetch ' + url);
};
const calls = [];
global.ScriptExecutorV2 = class { async execute(n, rows, t, cfg) { calls.push(cfg.masterFlow.asset); return []; } };
eval(fs.readFileSync('components/master_flow.js', 'utf8'));
const MF = window.MasterFlow;
const tick = () => new Promise(r => setTimeout(r, 0));
const settle = async () => { for (let i = 0; i < 6; i++) await tick(); };
const options = id => els[id].children.map(o => [o.value, o.textContent]);

(async () => {
  // logged out: nothing loaded
  MF.refresh(); await settle();
  assert.strictEqual(masterCalls.length, 0);

  // first login: user-info fails for irrigation list -> soil ok, irrigation failed
  authToken = 'tok'; failIrrigation = true; MF.refresh(); await settle();
  assert.deepStrictEqual(masterCalls.sort(), ['/api/data-generate/asset-masters?type=irrigation&environment=QA2&tenant=qazone2',
    '/api/data-generate/asset-masters?type=soil&environment=QA2&tenant=qazone2']);
  const soilOpts = options('mf-soil-type');
  assert.deepStrictEqual(soilOpts[0], ['', 'Select soil type']);
  assert.deepStrictEqual(soilOpts.slice(1), SOIL.map(s => [String(s.id), s.name]), 'value=id, label=name');
  assert.deepStrictEqual(options('mf-irrigation-type'), [['', '⚠ Failed to load irrigation types - click to retry']]);

  // no automatic retry on later refreshes
  masterCalls.length = 0; MF.refresh(); MF.refresh(); await settle();
  assert.strictEqual(masterCalls.length, 0, 'failed list not auto-retried, loaded list not re-fetched: ' + JSON.stringify(masterCalls));

  // user clicks the failed dropdown -> retry once
  failIrrigation = false; els['mf-irrigation-type']._fire('mousedown'); await settle();
  assert.deepStrictEqual(masterCalls, ['/api/data-generate/asset-masters?type=irrigation&environment=QA2&tenant=qazone2']);
  assert.deepStrictEqual(options('mf-irrigation-type').slice(1), IRR.map(s => [String(s.id), s.name]));
  els['mf-irrigation-type']._fire('mousedown'); await settle();
  assert.strictEqual(masterCalls.length, 1, 'loaded list not re-fetched on click');

  // select by id -> name (+id) sent to the asset step
  vals['mf-soil-type'] = '1060'; vals['mf-irrigation-type'] = '1109';
  vals['chk:mf-existing-farmer'] = true; vals['chk:mf-step-asset'] = true;
  Object.assign(vals, { 'mf-existing-farmer-ids': '5982402', 'mf-asset-prefix': 'RS A', 'mf-assets-per-farmer': '1',
    'mf-asset-address': 'Blr', 'mf-declared-area': '1' });
  await MF.execute();
  assert.deepStrictEqual(calls[0], { soilType: 'Lime', soilTypeId: '1060', irrigationType: 'Dam', irrigationTypeId: '1109', address: 'Blr', declaredArea: '1' });

  // re-login (other tenant) -> lists reload, stale selection cleared if id not present
  masterCalls.length = 0; authToken = 'tok-2'; currentTenant = 'other'; MF.refresh(); await settle();
  assert.strictEqual(masterCalls.length, 2, 'reloaded for new login');
  assert.strictEqual(vals['mf-soil-type'], '', 'selection cleared on new login (ids are tenant-specific)');
  console.log('soil/irrigation dropdown tests: all passed');
})().catch(e => { console.error(e); process.exit(1); });
