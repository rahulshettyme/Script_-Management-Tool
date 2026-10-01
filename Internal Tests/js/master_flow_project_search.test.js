// Internal regression test (not deployed). Run from project root: node "Internal Tests/js/master_flow_project_search.test.js"
// Loads components/master_flow.js against a stubbed DOM + mocked backend; no network calls.
// Covers the single-select Project search used by the Assign & Validate step.
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

const PROJECTS = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'fixtures', 'project_search.json'), 'utf8'));
const searches = [];
global.fetch = async (url, opts) => {
  if (url.startsWith('/api/data-generate/user-info')) return { ok: true, json: async () => ({ id: 1, name: 'U', companyId: 1251 }) };
  if (url.startsWith('/api/data-generate/asset-masters')) { const t = new URL('http://h' + url).searchParams.get('type');
    return { ok: true, json: async () => (t === 'soil' ? [{ id: 1059, name: 'Black' }] : [{ id: 1102, name: 'Drip' }]) }; }
  if (url.startsWith('/api/data-generate/project-search')) {
    searches.push({ url, auth: opts.headers.Authorization });
    const q = new URL('http://h' + url).searchParams.get('query');
    return { ok: true, json: async () => (q === 'none' ? [] : PROJECTS) };
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
  authToken = 'tok'; MF.refresh(); await settle();

  // min 3 chars, then exact URL contract
  await type('rs'); assert.strictEqual(searches.length, 0, 'min 3 chars');
  await type('rs n');
  assert.strictEqual(searches.length, 1);
  assert.strictEqual(searches[0].url, '/api/data-generate/project-search?environment=QA2&tenant=qazone2&size=51&query=rs%20n');
  assert.strictEqual(searches[0].auth, 'Bearer tok');
  assert.strictEqual(results()[0], 'RS New indices Testing (ID 3440401)');
  assert.strictEqual(results().length, 8);

  // single select: picking another replaces; picking the same deselects
  pick('5902751');
  assert.strictEqual(vals['mf-project-id'], '5902751');
  pick('5972951');
  assert.strictEqual(vals['mf-project-id'], '5972951', 'second pick replaces the first');
  assert.deepStrictEqual(els['mf-project-chips'].children.map(c => c.textContent), ['RS New Germination Testing (ID 5972951)']);
  assert.ok(results().find(t => t.includes('5972951')).startsWith('✓ '));
  assert.ok(!results().find(t => t.includes('5902751')).startsWith('✓ '));
  pick('5972951'); assert.strictEqual(vals['mf-project-id'], '', 'same pick deselects');
  pick('5902751');
  assert.deepStrictEqual(MF._getSelectedProject(), { id: '5902751', name: 'RS New Sync Testing' });
  await type('none'); assert.deepStrictEqual(results(), ['No projects found']);

  // run: selected project id goes to Assign & Validate (master turns it into a number)
  vals['chk:mf-existing-farmer'] = true; vals['chk:mf-step-asset'] = true; vals['chk:mf-step-validate'] = true;
  Object.assign(vals, { 'mf-existing-farmer-ids': '5982402', 'mf-asset-prefix': 'RS A', 'mf-assets-per-farmer': '1',
    'mf-soil-type': '1059', 'mf-irrigation-type': '1102', 'mf-asset-address': 'Blr', 'mf-declared-area': '1' });
  await MF.execute();
  assert.ok(calls.length >= 1);
  assert.strictEqual(calls[0].masterFlow.projectId, '5902751');
  assert.strictEqual(calls[0].masterFlow.steps.validate, true);

  // validation: no project selected -> blocked
  await type('rs n'); pick('5902751'); assert.strictEqual(vals['mf-project-id'], '');
  await assert.rejects(MF.execute(), /Select a project/);

  // re-login clears the selection
  pick('5902751'); authToken = 'tok-2'; MF.refresh(); await settle();
  assert.strictEqual(MF._getSelectedProject(), null); assert.strictEqual(vals['mf-project-id'], '');
  console.log('project search tests: all passed');
})().catch(e => { console.error(e); process.exit(1); });
