// Internal regression test (not deployed). Run from project root: node "Internal Tests/js/backend_routes.test.js"
// Loads backend/api.js against a stub Express app (no server, no network) and checks the route contract:
// every core route the creation/execution tools depend on must still be registered, and the master-flow
// proxy routes must keep rejecting bad input before any upstream call.
const assert = require('assert');
const path = require('path');
const https = require('https');

const upstream = []; const sent = [];
https.request = (opts) => {
  const rec = { path: opts.path, method: opts.method, body: '' };
  upstream.push(opts.path); sent.push(rec);
  return { on() {}, end() {}, write(b) { rec.body += b; } };
};

const routes = {};
const app = {
  get: (p, h) => { routes['GET ' + p] = h; }, post: (p, h) => { routes['POST ' + p] = h; },
  put: (p, h) => { routes['PUT ' + p] = h; }, delete: (p, h) => { routes['DELETE ' + p] = h; }, use() {}
};
require(path.join(process.cwd(), 'backend', 'api.js'))(app);

// Core contract used by script creation (script_management) and execution (createbulkdata / master flow)
const REQUIRED = [
  'GET /api/scripts/custom', 'POST /api/scripts/execute', 'GET /api/scripts/content',
  'POST /api/scripts/generate', 'POST /api/scripts/analyze', 'POST /api/scripts/test-run',
  'POST /api/scripts/save-draft', 'GET /api/scripts/list-drafts', 'GET /api/scripts/content-draft',
  'POST /api/scripts/register', 'POST /api/scripts/update-meta', 'POST /api/scripts/delete',
  'POST /api/scripts/rename', 'POST /api/user-aggregate/token', 'GET /api/env-urls', 'POST /api/geocode',
  'GET /api/data-generate/user-info', 'GET /api/data-generate/user-search',
  'GET /api/data-generate/farmer-search', 'GET /api/data-generate/project-search', 'GET /api/data-generate/variety-search',
  'GET /api/data-generate/asset-masters',
  'POST /api/audit/record'
];
const missing = REQUIRED.filter(r => !routes[r]);
assert.deepStrictEqual(missing, [], 'missing routes: ' + missing.join(', '));

const call = (route, query, headers = {}) => new Promise(resolve => {
  const res = { code: 200, status(c) { this.code = c; return this; }, json(b) { resolve([this.code, b]); } };
  routes[route]({ query, headers }, res);
  setTimeout(() => resolve(['proxied']), 50);
});

(async () => {
  // input validation happens before any upstream request
  assert.strictEqual((await call('GET /api/data-generate/user-search', { companyId: 'x', query: 'rs a' }))[0], 400);
  assert.strictEqual((await call('GET /api/data-generate/user-search', { companyId: '1251', query: 'rs' }))[0], 400);
  assert.strictEqual((await call('GET /api/data-generate/farmer-search', { query: 'rs' }))[0], 400);
  assert.strictEqual((await call('GET /api/data-generate/project-search', { query: 'rs' }))[0], 400);
  assert.strictEqual((await call('GET /api/data-generate/variety-search', { query: 'rs' }))[0], 400);
  assert.strictEqual((await call('GET /api/data-generate/asset-masters', { type: 'crop' }))[0], 400);
  // auth required before proxying
  assert.deepStrictEqual(await call('GET /api/data-generate/user-info', { environment: 'QA2' }), [401, { error: 'Missing token' }]);
  assert.strictEqual(upstream.length, 0, 'no upstream call for rejected requests');
  // proxied paths (contract with the platform APIs)
  const auth = { authorization: 'Bearer t' };
  await call('GET /api/data-generate/asset-masters', { type: 'soil', environment: 'QA2' }, auth);
  await call('GET /api/data-generate/asset-masters', { type: 'irrigation', environment: 'QA2' }, auth);
  await call('GET /api/data-generate/user-search', { companyId: '1251', query: 'rs a', environment: 'QA2' }, auth);
  await call('GET /api/data-generate/farmer-search', { query: 'rs te', size: '51', environment: 'QA2' }, auth);
  await call('GET /api/data-generate/project-search', { query: 'rs n', size: '51', environment: 'QA2' }, auth);
  await call('GET /api/data-generate/variety-search', { query: 'rs pr', environment: 'QA2' }, auth);
  assert.ok(upstream[0].endsWith('/services/farm/api/soil-types?size=5000'), upstream[0]);
  assert.ok(upstream[1].endsWith('/services/master/api/irrigation-types?size=5000'), upstream[1]);
  assert.ok(upstream[2].endsWith('/services/user/api/users/search/companies/1251?query=rs%20a'), upstream[2]);
  assert.ok(upstream[3].endsWith('/services/farm/api/farmers/dropdownList?page=0&size=51&sort=lastModifiedDate,Desc&query=rs%20te'), upstream[3]);
  assert.ok(upstream[4].endsWith('/services/farm/api/projects/search?page=0&size=51&projectStatus=LIVE&projectExecutionStatus=TO_BE_STARTED&projectExecutionStatus=STARTED&projectStatus=UPCOMING&query=rs%20n'), upstream[4]);
  assert.ok(upstream[5].endsWith('/services/farm/api/crops/details/filter?page=0&size=100&sort=name,asc'), upstream[5]);
  assert.strictEqual(sent[5].method, 'POST');
  assert.deepStrictEqual(JSON.parse(sent[5].body), { search: 'rs pr' });
  assert.ok(sent.slice(0, 5).every(r => r.method === 'GET'), 'existing proxies stay GET');
  console.log(`backend route contract tests: all passed (${REQUIRED.length} core routes registered)`);
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
