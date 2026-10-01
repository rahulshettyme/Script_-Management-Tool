# Script Execution SOP (bulk data page → runner)

Audited against code on 2026-10-01. Files: `createbulkdata.html`, `script.js`,
`components/executor_v2.js`, `components/login_component.js`, `backend/api.js`,
`Manager/runner_bridge.py`, `Converted Scripts/thread_utils.py`, `components/attribute_utils.py`,
`components/master_search.py`. The master flow has its own SOP (QA_DATA_SETUP_MASTER_SOP.md).

> **Legacy-execution guarantee:** changes to the shared path (`/api/scripts/execute`, `runner_bridge.py`,
> `thread_utils.py`, `script.js` execute handler, `executor_v2.js`) must be **opt-in** (default off) so every
> existing script behaves exactly as before. Example: `SKIP_INPUT_MERGE` is honoured only when a script
> defines it. Run `python "Internal Tests/run_regression.py"` - its smoke tests run a legacy script through
> the real runner.

---

## 1. Flow

```
createbulkdata.html (script.js)
  team → script → login → Excel upload → validate → (consent if > 10 rows) → Execute
        │ batches (batchSize rows, groupByColumn units never split)
        │ parallel: 5 batches at a time via ScriptExecutorV2 | sequential: one at a time
        ▼
POST /api/scripts/execute  (backend/api.js)
  envConfig.apiBaseUrl (server env map, overwrites) + Geocoding_api_key injected
  rows → temp_data/run_data_<ts>.json
  spawn: python -u Manager/runner_bridge.py --script "Converted Scripts/<file>" --data-file <tmp>
         --token <tok> --env <json> --columns <json>        (no --debug from the bulk page)
        ▼
runner_bridge.py
  load_config_and_secrets (keys, master_data_config from secrets.json → db.json, URL aliases)
  companyId auto-resolve via user-info (only if not already in env_config)
  sys.path: script dir, project root, components/, Converted Scripts/
  API interceptor on requests.Session.request (attribute injection, 429/503 retry ×3 after 30 s)
  results = module.run(data, token, env_config)
  merge input rows into results by index (unless module.SKIP_INPUT_MERGE)
  print [OUTPUT_DATA_DUMP] + ---JSON_START--- {"status":"success","data":[...]}
        ▼
api.js parses after the last ---JSON_START--- → rows (401 if any Response contains "Status: 401")
        ▼
script.js renders rows progressively → pass/fail counters → filter → Excel download → audit record
```

## 2. Bulk page details (script.js)
- **Team**: `cs_team` locks env to Prod; others default QA1 (unlocked). `meta-csm` role sees CS only.
- **Script list** from `/api/scripts/custom` (registry minus system files); `Unassigned` team never listed.
- **Selection**: `handleScriptSelection` shows description, boundary config (Generate Coordinates / Area Audit V2),
  Additional Attributes (if allowed), target location (if geofencing), V2 config, batch-size rules
  (max 100 or 10000 with allowLargeBatch; hidden when multithreaded), then `MasterFlow.refresh()`.
- **Upload**: first sheet only; `.json/.geojson` → single row `{GeoJSON_Data}`; `validateTemplate` checks
  required columns (trimmed, case-insensitive).
- **envConfig sent**: environment, tenant, apiurl, apiBaseUrl, google_api_key (""), boundary{minLat,maxLat,
  minLong,maxLong,locationName}, targetLocation, area_size/area_unit (only when V2 config visible),
  allowAdditionalAttributes, additionalAttributes[], batchSize.
- **Routing**: `LEGACY_SCRIPTS = ['Area_Audit','Area Audit','Area_Audit.py']` (substring match) → legacy fetch
  when sequential; everything else → `ScriptExecutorV2`. Parallel mode always uses ScriptExecutorV2.
- **Errors**: legacy sequential 401 → resume alert ("Start from Row"); other legacy batch errors mark the chunk
  `Error` and continue. V2 errors abort the run (see caveats).

## 3. Backend `/api/scripts/execute`
- `console.clear()` every request; 400 if no scriptName/rows; 404 if file missing.
- Columns: registry `expected_columns`/`columns`, else `# EXPECTED_INPUT_COLUMNS:` header.
- **Does not inject `master_data_config`** - runner_bridge loads it (secrets.json first, then db.json).
  `/test-run` injects it from db.json, so test and execute can differ if both files define it.
- Non-zero exit → 500 `{error:'Script execution failed', details}`; `status:'error'` → 500.

## 4. Runner contract (what every script can rely on)
- Signature `run(data, token, env_config)`; `data` = list of row dicts; return list of row dicts.
- `env_config` keys: apiBaseUrl/apiurl/base_url, Geocoding_api_key, token, companyId/company_id,
  master_data_config, batchSize, plus page keys above.
- `builtins`: data, token, env_config, output_columns, DEBUG_MODE.
- `thread_utils.run_in_parallel(process_func, items, token=, env_config=)` - workers = `env_config['batchSize']`
  (default 1), results in input order, crash → row copy with `Status='Fail'`, `API_Response`.
- Result rows are merged `{**input_row, **result_row}` by index (output wins) unless `SKIP_INPUT_MERGE = True`.

## 5. Results, export, audit
- Dynamic UI (`outputConfig.isDynamicUI`): columns from `uiMapping[].colName`; otherwise legacy columns
  Row/Name/Code/Status/Response.
- `evaluateRowStatus`: `passCriteria` if set, else `Status` pass/success/true/passed. Counters treat
  anything not pass as fail.
- Excel export `_getOrderedSheet` **drops `Status`, `Response`, `Name`, `Code`** for every script (the
  `inputColumns`/`outputColumns` override is never populated on templates).
- Audit: `/api/audit/record` (fire-and-forget) with input file, output xlsx, consent; history via
  `/api/audit/history`.

## 6. Caveats
| # | Caveat |
|---|---|
| E1 | `syncTemplateWithLiveMeta` looks up `TEMPLATES[filename stem]` but templates are keyed by registry `name` → live CONFIG/EXPECTED_INPUT_COLUMNS are ignored for ~32/35 scripts (registry values used). |
| E2 | V2 path: a 401 shows "Execution failed with status 401" (no resume row) and any 500 aborts the whole run. Only legacy sequential and the master flow handle 401 specially. |
| E3 | Parallel mode appends results in completion order - table/export can be out of input order across batches. |
| E4 | `batchSize` = rows per HTTP call **and** thread count inside `run_in_parallel`. |
| E5 | Attribute auto-injection only works inside `run_in_parallel` threads; a JSON **list** payload with attributes configured would raise. |
| E6 | Interceptor logs every request/payload whenever `allowAdditionalAttributes` is on (not only `--debug`). |
| E7 | Secrets in logs: `/execute` logs envConfig incl. `Geocoding_api_key`; token/env passed as CLI args; ExecutorV2 logs payload incl. token to the browser console. |
| E8 | `console.clear()` per request - parallel batches clear each other's server logs. |
| E9 | Script load errors happen outside runner_bridge's try → no JSON envelope → generic 500. |
| E10 | `Uploaded_File.xlsx` is resolved against the server cwd - concurrent runs can clash. |
| E11 | Group-by / GDPR UI elements referenced in script.js do not exist in the page (dead code). |
| E12 | Consent threshold uses full file row count (`> 10`), not rows after Start Row. |

## 7. Change log (tool changes affecting execution)
- 2026-09-27 - `runner_bridge.py`: skip input/result merge when the module sets `SKIP_INPUT_MERGE` (opt-in;
  legacy scripts unaffected - verified by the smoke tests).
- 2026-09-27 - `script.js`: hooks for `MasterFlow.refresh()` (selection, team change, login, logout) and the
  Execute branch to `MasterFlow.execute()` when the master script is selected. Excel flow unchanged.
- 2026-09-27 - `Area_Audit_V2.py` (user-approved edit): company from user-info + V1 unit-master conversion,
  no acre fallback.
