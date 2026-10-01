// Internal regression test (not deployed). Run from project root: node "Internal Tests/js/master_flow_farmer_search.test.js"
// Loads components/master_flow.js against a stubbed DOM + mocked backend; no network calls.
const fs = require('fs'); const assert = require('assert');
const vals = {}; const handlers = {};
const mkClassList = () => { const set = new Set(); return { toggle(c, on) { (on === undefined ? !set.has(c) : on) ? set.add(c) : set.delete(c); },
  add(c) { set.add(c); }, remove(c) { set.delete(c); }, contains(c) { return set.has(c); } }; };
const mk = id => {
  const own = {};
  const e = { id, get value() { return vals[id] ?? ''; }, set value(v) { vals[id] = v; },
    get checked() { return !!vals['chk:' + id]; }, set checked(v) { vals['chk:' + id] = v; },
    disabled: false, textContent: '', children: [], classList: mkClassList(), style: {},
    setAttribute() {}, closest() { return null; },
    appendChild(c) { this.children.push(c); },
    addEventListener(evt, fn) { own[evt] = fn; (handlers[id + ':' + evt] = handlers[id + ':' + evt] || []).push(fn); },
    _fire(evt) { own[evt] && own[evt]({ preventDefault() {} }); } };
  Object.defineProperty(e, 'innerHTML', { set() { this.children = []; }, get() { return ''; } });
  return e;
};
const els = {};
global.document = { getElementById: id => (els[id] = els[id] || mk(id)), createElement: tag => mk('new-' + tag) };
global.window = {}; global.alert = m => { throw new Error('ALERT: ' + m); }; global.confirm = () => true;
global.TEMPLATES = { M: { filename: 'QA_Data_Setup_Master.py', batchSize: 5 } }; global.selectedDataType = 'M';
global.authToken = null; global.currentEnvironment = 'QA2'; global.currentTenant = 'qazone2';
global.getEnvUrls = () => ({ apiBaseUrl: 'http://x' });
global.elements = { executeBtn: mk('exec'), loginSection: mk('login-section') };
global.executionResults = []; global.startExecution = () => { executionResults = []; }; global.completeExecution = () => {};
global.updateProgress = () => {}; global.renderExecutionResults = () => {}; global.evaluateRowStatus = r => ({ isPass: r.Status === 'Pass' });

const FARMERS = JSON.parse(fs.readFileSync(require('path').join(__dirname, '..', 'fixtures', 'farmer_search.json'), 'utf8'));
const searches = [];
global.fetch = async (url, opts) => {
  if (url.startsWith('/api/data-generate/user-info')) return { ok: true, json: async () => ({ id: 3388201, name: 'RS qa2 user 1', companyId: 1251 }) };
  if (url.startsWith('/api/data-generate/asset-masters')) { const t = new URL('http://h' + url).searchParams.get('type');
    return { ok: true, json: async () => (t === 'soil' ? [{ id: 1059, name: 'Black' }] : [{ id: 1102, name: 'Drip' }]) }; }
  if (url.startsWith('/api/data-generate/farmer-search')) {
    searches.push({ url, auth: opts.headers.Authorization });
    const p = new URL('http://h' + url).searchParams; const q = p.get('query');
    const size = Number(p.get('size'));
    if (q === 'many') return { ok: true, json: async () => Array.from({ length: size }, (_, i) => ({ id: 8000000 + i, firstName: 'Farmer ' + i })) };
    return { ok: true, json: async () => (q === 'none' ? [] : FARMERS) };
  }
  throw new Error('unexpected fetch ' + url);
};
const calls = [];
global.ScriptExecutorV2 = class { async execute(n, rows, t, cfg) { calls.push({ steps: cfg.masterFlow.steps, rows: rows.map(r => ({ ...r })) }); return []; } };
eval(fs.readFileSync('components/master_flow.js', 'utf8'));
const MF = window.MasterFlow;
const tick = (ms = 0) => new Promise(r => setTimeout(r, ms));
const type = async (text, wait = 400) => { vals['mf-farmer-search'] = text; handlers['mf-farmer-search:input'].forEach(f => f()); await tick(wait); };
const results = () => els['mf-farmer-results'].children.map(c => c.textContent);
const pick = text => { const row = els['mf-farmer-results'].children.find(c => c.textContent.includes(text)); assert.ok(row, 'row ' + text); row._fire('mousedown'); };

(async () => {
  assert.deepStrictEqual(MF._helpers.toFarmers(FARMERS).slice(0, 2), [{ id: '5982402', name: 'RS Test Auto 2 F 2' }, { id: '5982401', name: 'RS Test Auto 2 F 1' }]);

  authToken = 'tok'; MF.refresh(); await tick(); await tick();
  await type('rs'); assert.strictEqual(searches.length, 0, 'min 3 chars');
  await type('rs te');
  assert.strictEqual(searches.length, 1);
  assert.strictEqual(searches[0].url, '/api/data-generate/farmer-search?environment=QA2&tenant=qazone2&size=51&query=rs%20te');
  assert.strictEqual(searches[0].auth, 'Bearer tok');
  assert.strictEqual(results()[0], 'RS Test Auto 2 F 2 (ID 5982402)');
  assert.strictEqual(results().length, 7);

  // multi-select -> hidden existing farmer IDs
  pick('5982402'); pick('5981552');
  assert.strictEqual(vals['mf-existing-farmer-ids'], '5982402, 5981552');
  assert.deepStrictEqual(els['mf-farmer-chips'].children.map(c => c.textContent), ['RS Test Auto 2 F 2 (ID 5982402)', 'RS Test Auto F 26300901 (ID 5981552)']);
  assert.deepStrictEqual(MF._getSelectedUsers(), [], 'user picker independent');

  // capped: 51 returned -> 50 rows + note without a total
  await type('many');
  assert.strictEqual(results().length, 51);
  assert.strictEqual(results()[50], 'Showing first 50 matches. Type more characters to narrow the search.');
  await type('none'); assert.deepStrictEqual(results(), ['No farmers found']);

  // existing-farmer run uses selected IDs for asset groups, no farmer creation
  vals['chk:mf-existing-farmer'] = true; vals['chk:mf-step-asset'] = true;
  Object.assign(vals, { 'mf-asset-prefix': 'RS A', 'mf-assets-per-farmer': '2', 'mf-soil-type': '1059', 'mf-irrigation-type': '1102',
    'mf-asset-address': 'Blr', 'mf-declared-area': '1' });
  await MF.execute();
  assert.ok(calls.every(c => c.steps.farmer === false), 'no farmer creation');
  assert.deepStrictEqual(calls.flatMap(c => c.rows).map(r => [r['Existing Farmer ID'], r['Asset Names']]),
    [['5982402', ['RS A 1', 'RS A 2']], ['5981552', ['RS A 3', 'RS A 4']]]);

  // re-login clears selection
  authToken = 'tok-2'; MF.refresh(); await tick(); await tick();
  assert.deepStrictEqual(MF._getSelectedFarmers(), []); assert.strictEqual(vals['mf-existing-farmer-ids'], '');
  console.log('farmer search tests: all passed');
})().catch(e => { console.error(e); process.exit(1); });
