// Internal regression test (not deployed). Run from project root: node "Internal Tests/js/master_flow_user_search.test.js"
// Loads components/master_flow.js against a stubbed DOM + mocked backend; no network calls.
const fs = require('fs'); const assert = require('assert');
const vals = {}; const handlers = {};
const mkClassList = () => { const set = new Set(); return { toggle(c, on) { (on === undefined ? !set.has(c) : on) ? set.add(c) : set.delete(c); },
  add(c) { set.add(c); }, remove(c) { set.delete(c); }, contains(c) { return set.has(c); } }; };
const mk = id => ({ id, get value() { return vals[id] ?? ''; }, set value(v) { vals[id] = v; },
  get checked() { return !!vals['chk:' + id]; }, set checked(v) { vals['chk:' + id] = v; },
  disabled: false, textContent: '', innerHTML: '', children: [], classList: mkClassList(), style: {},
  setAttribute() {}, closest() { return null; },
  appendChild(c) { this.children.push(c); }, addEventListener(evt, fn) { (handlers[id + ':' + evt] = handlers[id + ':' + evt] || []).push(fn); } });
const els = {};
global.document = {
  getElementById: id => (els[id] = els[id] || mk(id)),
  createElement: tag => { const e = mk('new-' + tag); Object.defineProperty(e, 'innerHTML', { set(v) { this.children = []; }, get() { return ''; } }); return e; }
};
// children reset when innerHTML = '' on real stub elements too
for (const id of ['mf-user-results', 'mf-user-chips']) { const e = document.getElementById(id); Object.defineProperty(e, 'innerHTML', { set(v) { this.children = []; }, get() { return ''; } }); }
global.window = {}; global.alert = m => { throw new Error('ALERT: ' + m); }; global.confirm = () => true;
global.TEMPLATES = { M: { filename: 'QA_Data_Setup_Master.py', batchSize: 5 } }; global.selectedDataType = 'M';
global.authToken = null; global.currentEnvironment = 'QA2'; global.currentTenant = 'qazone2';
global.getEnvUrls = () => ({ apiBaseUrl: 'http://x' });
global.elements = { executeBtn: mk('exec'), loginSection: mk('login-section') };
global.executionResults = []; global.startExecution = () => { executionResults = []; }; global.completeExecution = () => {};
global.updateProgress = () => {}; global.renderExecutionResults = () => {}; global.evaluateRowStatus = r => ({ isPass: r.Status === 'Pass' });

const SEARCH_RESPONSE = JSON.parse(fs.readFileSync(require('path').join(__dirname, '..', 'fixtures', 'user_search.json'), 'utf8'));
const searches = []; let searchDelay = 0;
global.fetch = async (url, opts) => {
  if (url.startsWith('/api/data-generate/user-info')) return { ok: true, json: async () => ({ id: 3388201, name: 'RS qa2 user 1', companyId: 1251 }) };
  if (url.startsWith('/api/data-generate/user-search')) {
    searches.push({ url, auth: opts.headers.Authorization });
    const q = new URL('http://h' + url).searchParams.get('query');
    if (searchDelay) await new Promise(r => setTimeout(r, searchDelay));
    return { ok: true, json: async () => (q === 'zzz' ? [] : q === 'big' ? Array.from({ length: 1200 }, (_, i) => ({ id: 7000000 + i, name: 'Bulk User ' + i })) : SEARCH_RESPONSE) };
  }
  throw new Error('unexpected fetch ' + url);
};
const calls = [];
global.ScriptExecutorV2 = class { async execute(n, rows, t, cfg) { calls.push(rows.map(r => ({ ...r })));
  return rows.map(r => ({ 'Farmer ID': '9' + r['Farmer #'], 'Farmer Status': 'Pass', Status: 'Pass' })); } };
eval(fs.readFileSync('components/master_flow.js', 'utf8'));
const MF = window.MasterFlow;
const tick = (ms = 0) => new Promise(r => setTimeout(r, ms));
const type = async (text, wait = 400) => { vals['mf-user-search'] = text; handlers['mf-user-search:input'].forEach(f => f()); await tick(wait); };
const results = () => els['mf-user-results'].children.map(c => c.textContent);
const clickResult = i => els['mf-user-results'].children[i].addEventListener.length; // not used
const pick = text => { const row = els['mf-user-results'].children.find(c => c.textContent.includes(text));
  assert.ok(row, 'result row for ' + text); handlers[row.id + ':mousedown'] ? 0 : 0; row._fire('mousedown'); };

(async () => {
  // capture per-row handlers: createElement stubs register under 'new-div:<evt>' -> make each row fire its own handler
  const origCreate = document.createElement;
  document.createElement = tag => { const e = origCreate(tag); const own = {}; e.addEventListener = (evt, fn) => { own[evt] = fn; };
    e._fire = evt => own[evt] && own[evt]({ preventDefault() {} }); return e; };

  // ---- toUsers maps only id + name ----
  const mapped = MF._helpers.toUsers(SEARCH_RESPONSE);
  assert.deepStrictEqual(mapped, [
    { id: '5761751', name: 'RS Angular Test user' }, { id: '5769301', name: 'RS Angular User 2' },
    { id: '5827651', name: 'RS Angular 12 User' }, { id: '5827652', name: 'RS Angular 12 Executive User' }]);

  // ---- login -> session ----
  authToken = 'tok'; MF.refresh(); await tick(); await tick();
  assert.ok(MF.getSession() && MF.getSession().companyId === 1251);

  // ---- min 3 chars: no API call ----
  await type('r'); await type('rs');
  assert.strictEqual(searches.length, 0, 'no search under 3 chars');
  assert.ok(results()[0].includes('at least 3 characters'));

  // ---- debounce: rapid typing -> one call ----
  vals['mf-user-search'] = 'rs '; handlers['mf-user-search:input'].forEach(f => f());
  await type('rs a');
  assert.strictEqual(searches.length, 1, 'debounced to one request');
  assert.strictEqual(searches[0].url, '/api/data-generate/user-search?environment=QA2&tenant=qazone2&companyId=1251&query=rs%20a');
  assert.strictEqual(searches[0].auth, 'Bearer tok');
  assert.deepStrictEqual(results(), ['RS Angular Test user (ID 5761751)', 'RS Angular User 2 (ID 5769301)',
    'RS Angular 12 User (ID 5827651)', 'RS Angular 12 Executive User (ID 5827652)']);

  // ---- multi-select + toggle off ----
  pick('5827651'); pick('5769301');
  assert.deepStrictEqual(MF._getSelectedUsers().map(u => u.id), ['5827651', '5769301']);
  assert.strictEqual(vals['mf-user-ids'], '5827651, 5769301');
  assert.ok(results().find(t => t.includes('5827651')).startsWith('✓ '), 'selected rows marked');
  assert.deepStrictEqual(els['mf-user-chips'].children.map(c => c.textContent), ['RS Angular 12 User (ID 5827651)', 'RS Angular User 2 (ID 5769301)']);
  pick('5769301');
  assert.strictEqual(vals['mf-user-ids'], '5827651');
  pick('5769301');

  // ---- no results ----
  await type('zzz'); assert.deepStrictEqual(results(), ['No users found']);

  // ---- large result set capped at 50 rows + narrow-search note ----
  await type('big');
  const rows = results();
  assert.strictEqual(rows.length, 51, '50 user rows + 1 note');
  assert.strictEqual(rows[49], 'Bulk User 49 (ID 7000049)');
  assert.strictEqual(rows[50], 'Showing first 50 of 1200 matches. Type more characters to narrow the search.');
  pick('7000003'); assert.ok(MF._getSelectedUsers().some(u => u.id === '7000003'));
  assert.strictEqual(results().length, 51, 'still capped after re-render'); pick('7000003');
  // ---- stale response dropped: slow 'rs a' then fast 'zzz' ----
  searchDelay = 300; vals['mf-user-search'] = 'rs a'; handlers['mf-user-search:input'].forEach(f => f()); await tick(400);
  searchDelay = 0; await type('zzz', 500);
  assert.deepStrictEqual(results(), ['No users found'], 'older response did not overwrite newer');

  // ---- selected IDs drive the farmer step (2 users x 2 farmers = 4) ----
  Object.assign(vals, { 'mf-farmers-per-user': '2', 'mf-farmer-name': 'RS F', 'mf-farmer-code': 'C', 'mf-farmer-phone': '+91 9000000001' });
  vals['chk:mf-step-asset'] = false;
  await MF.execute();
  assert.deepStrictEqual(calls.flat().map(r => r['AssignedTo User ID']), ['5827651', '5827651', '5769301', '5769301']);
  assert.deepStrictEqual(calls.flat().map(r => r['AssignedTo User Name']),
    ['RS Angular 12 User', 'RS Angular 12 User', 'RS Angular User 2', 'RS Angular User 2'], 'selected user names carried for the output');

  // ---- new login clears selection ----
  authToken = 'tok-other-session'; MF.refresh(); await tick(); await tick();
  assert.deepStrictEqual(MF._getSelectedUsers(), []);
  assert.strictEqual(vals['mf-user-ids'], '');
  console.log('user search tests: all passed');
})().catch(e => { console.error(e); process.exit(1); });
