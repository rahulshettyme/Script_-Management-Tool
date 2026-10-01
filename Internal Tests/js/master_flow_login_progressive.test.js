// Internal regression test (not deployed). Run from project root: node "Internal Tests/js/master_flow_login_progressive.test.js"
// Loads components/master_flow.js against a stubbed DOM + mocked backend; no network calls.
const fs = require('fs'); const assert = require('assert');
const vals = {};
const mk = id => ({ id, get value() { return vals[id] ?? ''; }, set value(v) { vals[id] = v; },
  get checked() { return !!vals['chk:' + id]; }, set checked(v) { vals['chk:' + id] = v; },
  disabled: false, textContent: '', classList: { toggle(){}, add(){}, remove(){}, contains(){ return false; } },
  style: {}, innerHTML: '', setAttribute(k, v){ this['attr:' + k] = v; }, addEventListener(){}, closest(){ return null; } });
const els = {}; global.document = { getElementById: id => { const e = (els[id] = els[id] || mk(id)); e.appendChild = e.appendChild || (() => {}); return e; }, createElement: tag => Object.assign(mk('new-' + tag), { appendChild() {} }) }; global.window = {};
global.alert = m => { throw new Error('ALERT: ' + m); }; global.confirm = () => true;
// script.js globals used by master_flow
global.TEMPLATES = { M: { filename: 'QA_Data_Setup_Master.py', batchSize: 5 } }; global.selectedDataType = 'M';
global.authToken = null; global.currentEnvironment = 'QA2'; global.currentTenant = 't';
global.getEnvUrls = () => ({ apiBaseUrl: 'http://x' });
global.elements = { executeBtn: mk('exec'), loginSection: mk('login-section'), minLat: mk('a'), maxLat: mk('b'), minLong: mk('c'), maxLong: mk('d') };
global.executionResults = []; const renders = [];
global.startExecution = () => { executionResults = []; }; global.completeExecution = () => {};
global.updateProgress = () => {}; global.renderExecutionResults = () => renders.push(executionResults.length);
global.evaluateRowStatus = r => ({ isPass: r.Status === 'Pass' });
let userInfoCalls = 0; let userInfoFails = false;
global.fetch = async (url, opts) => {
  if (url.startsWith('/api/data-generate/asset-masters')) { const t = new URL('http://h' + url).searchParams.get('type');
    return { ok: true, json: async () => (t === 'soil' ? [{ id: 1059, name: 'Black' }] : [{ id: 1102, name: 'Drip' }]) }; }
  userInfoCalls++; assert.ok(url.startsWith('/api/data-generate/user-info?environment=QA2'));
  assert.strictEqual(opts.headers.Authorization, 'Bearer ' + authToken);
  if (userInfoFails) return { ok: false, status: 500 };
  return { ok: true, json: async () => ({ id: 3388201, name: 'RS qa2 user 1', companyId: 1251 }) }; };
// Fake backend emulating the master script
const calls = [];
global.ScriptExecutorV2 = class {
  async execute(name, rows, tok, cfg) {
    assert.strictEqual(cfg.companyId, 1251, 'companyId from user-info passed to run'); const st = cfg.masterFlow.steps;
    calls.push({ steps: st.farmer ? 'farmer' : 'assets', rows: rows.map(r => ({ ...r })) });
    if (st.farmer) return rows.map(r => r['Farmer #'] === 2
      ? { 'Farmer ID': '', 'Farmer Status': 'Fail', Status: 'Fail', Response: 'Farmer: API Error 400: dup' }
      : { 'Farmer ID': '9' + r['Farmer #'], 'Farmer Status': 'Pass', Status: 'Pass', Response: 'Success' });
    const out = [];
    rows.forEach(r => r['Asset Names'].forEach(n => out.push({ 'Farmer ID': r['Existing Farmer ID'], 'Asset Name': n,
      Status: r['Farmer Status'] === 'Fail' ? 'Fail' : 'Pass' })));
    return out;
  }
};
eval(fs.readFileSync('components/master_flow.js', 'utf8'));
const h = window.MasterFlow._helpers;

// ---- counter rule ----
assert.strictEqual(h.seriesValue('RS F', 0, 1), 'RS F');
assert.strictEqual(h.seriesValue('RS F 26171001', 0, 1), 'RS F 26171001');
assert.deepStrictEqual([0, 4].map(i => h.seriesValue('RS F', i, 5)), ['RS F 1', 'RS F 5']);
assert.deepStrictEqual([0, 9].map(i => h.seriesValue('RS F', i, 10)), ['RS F 01', 'RS F 10']);
assert.deepStrictEqual([0, 99].map(i => h.seriesValue('RS F ', i, 100)), ['RS F 001', 'RS F 100']);
assert.deepStrictEqual([0, 1, 2].map(i => h.seriesValue('RS F 26171001', i, 3)), ['RS F 26171001', 'RS F 26171002', 'RS F 26171003']);
assert.deepStrictEqual([0, 2].map(i => h.seriesValue('RS A2', i, 3)), ['RS A2', 'RS A4']);
assert.deepStrictEqual([0, 1, 2].map(i => h.seriesValue('RS A 09', i, 3)), ['RS A 09', 'RS A 10', 'RS A 11']);
assert.strictEqual(h.seriesValue('A 99', 1, 2), 'A 100');
assert.deepStrictEqual(h.buildAssetNames('RS Test Auto A', 1), ['RS Test Auto A']);

const p1 = h.buildFarmerPlans({ existing: false, userIds: ['7'], farmersPerUser: 1, name: 'RS F', code: 'CODE',
  phone: '+91 9126300901', withAssets: true, assetPrefix: 'RS A', assetsPerFarmer: 1 });
assert.deepStrictEqual([p1[0]['Farmer Name'], p1[0]['Farmer Code'], p1[0]['Phone Number'], p1[0]['Asset Names'][0]],
  ['RS F', 'CODE', '91 9126300901', 'RS A']);

const p2 = h.buildFarmerPlans({ existing: false, userIds: ['7', '8'], farmersPerUser: 5, name: 'RS F', code: 'C',
  phone: '+91 9126300901', withAssets: true, assetPrefix: 'RS A', assetsPerFarmer: 10 });
assert.deepStrictEqual([p2[0]['Farmer Name'], p2[9]['Farmer Name'], p2[9]['Farmer Code'], p2[9]['Phone Number'], p2[5]['AssignedTo User ID']],
  ['RS F 01', 'RS F 10', 'C 10', '91 9126300910', '8']);
assert.deepStrictEqual([p2[0]['Asset Names'][0], p2[1]['Asset Names'][0], p2[9]['Asset Names'][9]], ['RS A 001', 'RS A 011', 'RS A 100']);

// asset grouping: 3 farmers x 4 assets, groups of 5 -> 5,5,2 ; farmer results carried
const pl = h.buildFarmerPlans({ existing: false, userIds: ['1'], farmersPerUser: 3, name: 'F1', code: 'C1',
  phone: '91 900001', withAssets: true, assetPrefix: 'A', assetsPerFarmer: 4 });
const gr = h.buildAssetGroups(pl, 5, [{ id: '11', status: 'Pass' }, { id: '', status: 'Fail', response: 'x' }, { id: '13', status: 'Pass' }]);
assert.deepStrictEqual(gr.map(g => g.reduce((n, r) => n + r['Asset Names'].length, 0)), [5, 5, 2]);
assert.deepStrictEqual(gr[0].map(r => [r['Existing Farmer ID'], r['Farmer Status'], r['Asset Names']]),
  [['11', 'Pass', ['A 01', 'A 02', 'A 03', 'A 04']], ['', 'Fail', ['A 05']]]);

// ---- execute(): 7 farmers x 3 assets, farmer #2 fails ----
(async () => {
  Object.assign(vals, { 'mf-user-ids': '5', 'mf-farmers-per-user': '7', 'mf-farmer-name': 'RS F', 'mf-farmer-code': 'C1',
    'mf-farmer-phone': '+91 9000000001', 'mf-asset-prefix': 'RS A', 'mf-assets-per-farmer': '3', 'mf-soil-type': '1059',
    'mf-irrigation-type': '1102', 'mf-asset-address': 'Blr', 'mf-declared-area': '1', 'mf-project-id': '1' });
  vals['chk:mf-step-asset'] = true; vals['chk:mf-step-validate'] = true;
  // logged out -> locked, login shown, Run disabled

  elements.executeBtn.disabled = true;
  window.MasterFlow.refresh();
  assert.strictEqual(els['mf-form-body'].style.pointerEvents, 'none');
  assert.ok(els['mf-login-notice'].innerHTML.includes('Login is required'));
  assert.strictEqual(elements.executeBtn.disabled, true);
  assert.strictEqual(userInfoCalls, 0);
  assert.strictEqual(window.MasterFlow.getSession(), null);
  // login with user-info failing -> stays locked with retry
  authToken = 'tok-fail'; userInfoFails = true;
  window.MasterFlow.refresh(); await new Promise(r => setTimeout(r, 0)); await new Promise(r => setTimeout(r, 0));
  assert.ok(els['mf-login-notice'].innerHTML.includes('Could not load user details'));
  assert.strictEqual(els['mf-form-body'].style.pointerEvents, 'none');
  assert.strictEqual(elements.executeBtn.disabled, true);
  assert.strictEqual(userInfoCalls, 1, 'failed user-info is not retried in a loop');
  window.MasterFlow.refresh(); window.MasterFlow.refresh(); await new Promise(r => setTimeout(r, 0));
  assert.strictEqual(userInfoCalls, 1, 'refresh after failure does not re-request');
  // successful login -> user-info once, unlocked, Run enabled
  authToken = 'tok'; userInfoFails = false; userInfoCalls = 0;
  window.MasterFlow.refresh(); window.MasterFlow.refresh();
  await new Promise(r => setTimeout(r, 0)); await new Promise(r => setTimeout(r, 0));
  assert.strictEqual(userInfoCalls, 1, 'user-info fetched once per login');
  assert.strictEqual(els['mf-form-body'].style.pointerEvents, '');
  assert.ok(els['mf-login-notice'].innerHTML.includes('Company ID <strong>1251</strong>'));
  assert.strictEqual(elements.executeBtn.disabled, false);
  assert.deepStrictEqual([window.MasterFlow.getSession().companyId, window.MasterFlow.getSession().userName], [1251, 'RS qa2 user 1']);
  window.MasterFlow.refresh(); await new Promise(r => setTimeout(r, 0));
  assert.strictEqual(userInfoCalls, 1, 'no re-fetch on later refreshes');
  // pickers/dropdowns are cleared on login; set selections after the session is ready
  vals['mf-user-ids'] = '5'; vals['mf-project-id'] = '1';
  vals['mf-soil-type'] = '1059'; vals['mf-irrigation-type'] = '1102';
  await window.MasterFlow.execute();

  const seq = calls.map(c => `${c.steps}:${c.steps === 'farmer' ? c.rows.length : c.rows.reduce((n, r) => n + r['Asset Names'].length, 0)}`);
  assert.deepStrictEqual(seq, ['farmer:5', 'assets:5', 'assets:5', 'assets:5', 'farmer:2', 'assets:5', 'assets:1']);
  assert.ok(calls[0].rows.every(r => r['Asset Names'].length === 0), 'farmer phase sends no assets');
  assert.strictEqual(executionResults.length, 21);
  assert.deepStrictEqual(renders, [5, 10, 15, 20, 21], 'rows rendered group by group');
  const assetRows = calls.filter(c => c.steps === 'assets').flatMap(c => c.rows);
  const failedFarmer = assetRows.filter(r => r['Farmer Status'] === 'Fail');
  // farmer #2's 3 assets span two groups (2 + 1)
  assert.deepStrictEqual(failedFarmer.map(r => r['Asset Names'].length), [2, 1]);
  assert.ok(failedFarmer.every(r => r['Existing Farmer ID'] === '' && r['Farmer Response'] === 'API Error 400: dup'));
  assert.ok(assetRows.filter(r => r['Farmer Status'] === 'Pass').every(r => /^9\d$/.test(r['Existing Farmer ID'])));
  assert.deepStrictEqual(calls[0].rows.map(r => r['Farmer Name']), ['RS F 1', 'RS F 2', 'RS F 3', 'RS F 4', 'RS F 5']);
  console.log('counter rule + grouping + progressive execute tests: all passed');
})().catch(e => { console.error(e); process.exit(1); });
