// Internal regression test (not deployed). Run from project root: node "Internal Tests/js/master_flow_variety_search.test.js"
// Loads components/master_flow.js against a stubbed DOM + mocked backend; no network calls.
// Covers the single-select Variety search used by the Crop & DOS step (POST upstream, nested children).
const fs = require('fs'); const path = require('path'); const assert = require('assert');
const vals = {}; const handlers = {};
const mkClassList = () => { const set = new Set(); return { toggle(c, on) { (on === undefined ? !set.has(c) : on) ? set.add(c) : set.delete(c); },
  add(c) { set.add(c); }, remove(c) { set.delete(c); }, contains(c) { return set.has(c); } }; };
const mk = id => {
  const own = {};
  const e = { id, get value() { return vals[id] ?? ''; }, set value(v) { vals[id] = v; },
    get checked() { return !!vals['chk:' + id]; }, set checked(v) { vals['chk:' + id] = v; },
    disabled: false, textContent: '', children: [], classList: mkClassList(), style: {},
    setAttribute() {}, closest() { return null; }, appendChild(c) { this.children.push(c); },
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

const CROPS = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'fixtures', 'variety_search.json'), 'utf8'));
const searches = [];
global.fetch = async (url, opts) => {
  if (url.startsWith('/api/data-generate/user-info')) return { ok: true, json: async () => ({ id: 1, name: 'U', companyId: 1251 }) };
  if (url.startsWith('/api/data-generate/asset-masters')) { const t = new URL('http://h' + url).searchParams.get('type');
    return { ok: true, json: async () => (t === 'soil' ? [{ id: 1059, name: 'Black' }] : [{ id: 1102, name: 'Drip' }]) }; }
  if (url.startsWith('/api/data-generate/variety-search')) {
    searches.push({ url, auth: opts.headers.Authorization });
    const q = new URL('http://h' + url).searchParams.get('query');
    return { ok: true, json: async () => (q === 'none' ? [] : CROPS) };
  }
  throw new Error('unexpected fetch ' + url);
};
const calls = [];
global.ScriptExecutorV2 = class { async execute(n, rows, t, cfg) { calls.push({ masterFlow: cfg.masterFlow, rows: rows.map(r => ({ ...r })) }); return []; } };
eval(fs.readFileSync('components/master_flow.js', 'utf8'));
const MF = window.MasterFlow;
const tick = (ms = 0) => new Promise(r => setTimeout(r, ms));
const settle = async () => { for (let i = 0; i < 6; i++) await tick(); };
const type = async (text, wait = 400) => { vals['mf-project-search'] = text; handlers['mf-project-search:input'].forEach(f => f()); await tick(wait); };
const results = () => els['mf-project-results'].children.map(c => c.textContent);
const pick = text => { const row = els['mf-project-results'].children.find(c => c.textContent.includes(text)); assert.ok(row, 'row ' + text); row._fire('mousedown'); };

(async () => {
  // flattening: varieties come from crops[].children, crop rows themselves are not offered
  const flat = MF._helpers.toVarieties(CROPS);
  assert.strictEqual(flat.length, 14);
  assert.deepStrictEqual(flat[0], { id: '3590701', name: 'RS PR IN Cotton' });
  assert.ok(!flat.some(v => v.id === '1010'), 'crop ids are not varieties');
  assert.deepStrictEqual(MF._helpers.toVarieties([{ id: 1, name: 'NoKids' }, null]), []);

  authToken = 'tok'; MF.refresh(); await settle();
  const type = async (text, wait = 400) => { vals['mf-variety-search'] = text; handlers['mf-variety-search:input'].forEach(f => f()); await tick(wait); };
  const results = () => els['mf-variety-results'].children.map(c => c.textContent);
  const pick = text => { const row = els['mf-variety-results'].children.find(c => c.textContent.includes(text)); assert.ok(row, 'row ' + text); row._fire('mousedown'); };

  await type('rs'); assert.strictEqual(searches.length, 0, 'min 3 chars');
  await type('rs pr');
  assert.strictEqual(searches.length, 1);
  assert.strictEqual(searches[0].url, '/api/data-generate/variety-search?environment=QA2&tenant=qazone2&query=rs%20pr');
  assert.strictEqual(searches[0].auth, 'Bearer tok');
  assert.strictEqual(results().length, 14);
  assert.strictEqual(results()[2], 'RS PR Maize (ID 3417101)');

  // single select
  pick('3417101'); pick('3424001');
  assert.strictEqual(vals['mf-variety-id'], '3424001', 'second pick replaces the first');
  assert.deepStrictEqual(els['mf-variety-chips'].children.map(c => c.textContent), ['RS PR Potato (ID 3424001)']);
  pick('3424001'); assert.strictEqual(vals['mf-variety-id'], '');
  pick('3424001');
  await type('none'); assert.deepStrictEqual(results(), ['No varieties found']);

  // run: Crop & DOS step gets the variety NAME (script maps name -> id) + id for reference
  vals['chk:mf-existing-farmer'] = true; vals['chk:mf-step-asset'] = true; vals['chk:mf-step-validate'] = true; vals['chk:mf-step-edit-ca'] = true;
  Object.assign(vals, { 'mf-existing-farmer-ids': '5982402', 'mf-asset-prefix': 'RS A', 'mf-assets-per-farmer': '1',
    'mf-soil-type': '1059', 'mf-irrigation-type': '1102', 'mf-asset-address': 'Blr', 'mf-declared-area': '1', 'mf-project-id': '5902751', 'mf-dos': '' });
  await MF.execute();
  assert.deepStrictEqual(calls[0].masterFlow.editCa, { varietyName: 'RS PR Potato', varietyId: '3424001', dos: '' });
  assert.strictEqual(calls[0].masterFlow.steps.editCa, true);

  // Crop & DOS needs a variety and/or DOS
  await type('rs pr'); pick('3424001'); assert.strictEqual(vals['mf-variety-id'], '');
  await assert.rejects(MF.execute(), /select a Variety and\/or enter Date of Sowing/);

  // re-login clears the selection
  pick('3424001'); authToken = 'tok-2'; MF.refresh(); await settle();
  assert.strictEqual(MF._getSelectedVariety(), null); assert.strictEqual(vals['mf-variety-id'], '');
  console.log('variety search tests: all passed');
})().catch(e => { console.error(e); process.exit(1); });
