# Script Creation SOP (Script Management tool)

Single source of truth for how a script is defined, generated, tested and registered.
Audited against code on 2026-10-01. Files: `script_management.html`, `script_management_v2.js`,
`backend/api.js`, `Manager/script_generator.py`, `Manager/script_converter.py`,
`Manager/script_analyzer.py`, `Manager/script_reverser.py`.

> **Strict rule (PROJECT_RULES.md):** never hand-edit scripts in `Draft Scripts/` or `Converted Scripts/`.
> A bad generated script is a **tool bug** - fix the generator/converter/prompt builder, then regenerate.

---

## 1. End-to-end flow

```
Script Management page
  define steps + columns + output mapping + flags
        │  Generate Script ──► POST /api/scripts/generate ──► Manager/script_generator.py (Gemini)
        ▼                                                     (code returned to hidden #pythonCode)
  Proceed to Test ──► POST /api/scripts/save-draft ──► Draft Scripts/<name>.py + <name>.py.meta.json (raw code)
        ▼
  Run Debug Trace ──► POST /api/scripts/test-run ──► script_converter.py ──► Converted Scripts/TEST_<ts>.py
        │                                             ──► runner_bridge.py --debug (90 s) ──► TEST file deleted
        ▼
  Register Script ✅ ──► POST /api/scripts/register ──► script_converter.py ──► Converted Scripts/<name>.py
                                                     ──► System/scripts_registry.json upsert ──► draft deleted
        ▼
  Script Dashboard ──► POST /api/scripts/update-meta (assign team QA / CS / Both)  ← required to show in dropdown
```
There is **no "Save Draft" or "Publish" button**: *Proceed to Test* saves the draft; *Register Script ✅*
publishes. `/api/scripts/publish` exists but nothing in the UI calls it (legacy).

---

## 2. Defining a script (UI)

**Fields**: Script Name, Description, User Input Columns (comma list), Output Columns, Group-by column.

**Flags** (each change rewrites the `# CONFIG:` lines in the code via `syncCodeConfigsFromUI`; editing the
code re-reads them via `syncUIFromCode`):

| Flag | Effect |
|---|---|
| Enable Parallel Processing (`isMultithreaded`) | thread count 1/2/5/10; mutually exclusive with Batch |
| Enable Batch Processing | batch size 1/5/10/20/25/50/100 (same `threadSize` select) |
| Allow > 100 (`allowLargeBatch`) | batch max 10000 instead of 100 on the bulk page |
| Allow Additional Attributes | extra Excel columns → payload `data` (see execution SOP) |
| Enable Geofencing | target location (Google Places autocomplete) |

**Team is not set here** - it lives in `window.currentTeam` and is assigned on the Script Dashboard.

**Step types** (`addStep`, script_management_v2.js ~1214):
- **API** - method, endpoint, Run Once, payload type `JSON` / `DTO_FILE` (multipart) / `QUERY` (forced for
  GET/DELETE), payload example, expected response, instructions, delay.
- **MASTER** - master type (user, farmer, soiltype, irrigationtype, closePlotReason, project, farmertag,
  assettag, plottag), input/output column, lookup path, skip-on-failure. Run method is read-only, from a map
  hardcoded in JS (user/farmer = search, others = once) - duplicated at ~1406 and ~2148, not read from db.json.
- **LOGIC** (free text), **SCRIPT** (reusable script + instructions), **GEO** (geofencing text).

**Output mapping** (`getOutputConfigFromUI`): `{ uiMapping[], excelMapping[], aiInstructions,
isDynamicUI: true, passCriteria: {column, values[]} | null }`. `uiMapping` = the columns the bulk page shows.

**Prompt** = `buildDescriptionFromSteps()` (~2095): `Script Name`, `Excel Columns`, an
`OUTPUT MAPPING CONFIGURATION:` block, then one `Step N [TYPE]:` block per step. This text is saved as
`generationPrompt` / `generation_prompt` and parsed back by `parseAndPopulateSteps` when a script is reopened
(SCRIPT steps are **not** restored).

---

## 3. Generation (`/api/scripts/generate` → `script_generator.py`)

- Node spawns `python Manager/script_generator.py` with `GOOGLE_API_KEY` and the JSON body on stdin.
  **5-minute hard timeout** → process killed, HTTP 504 `{status:'error', message}`; stderr is logged and a
  short tail is returned on failure. (Added 2026-09-27 - previously the request could hang forever.)
- **IPv4 forced** at the top of `script_generator.py` (`urllib3...allowed_gai_family = AF_INET`). On this
  network IPv6 is unreachable and Gemini resolves to 8 AAAA records first; without this every call stalled
  minutes. (Added 2026-09-27.)
- **Key**: env `GOOGLE_API_KEY` → `System/secrets.json` (`google_api_key`/`gemini_api_key`) → `System/db.json`.
  `GOOGLE_API_KEY` is reserved for script creation; scripts must use `Geocoding_api_key` for geocoding.
- **Models**: discovered via `v1beta/models` (5 s), filtered to gemini + generateContent, priority
  2.0-flash > 1.5-pro > 1.5-flash > pro > flash; fallback `gemini-1.5-flash, gemini-pro`. Each model: 2
  attempts, 90 s timeout; 400/403/404 → next model; 429/503 → retry.
- **The UI always generates fresh** (`existing_code` is commented out) - `update_script_with_ai` is unreachable
  from the current UI.
- **Header written**: `# AI Generated - <IST>`, `# CONFIG: enableGeofencing`, `# CONFIG: allowAdditionalAttributes`,
  `# EXPECTED_INPUT_COLUMNS:`. `isMultithreaded` / `batchSize` / `groupByColumn` CONFIG lines are added by the UI.
- Output: `{"status":"success","script":...}` on stdout (no delimiter needed; parsed as last JSON).

---

## 4. Test run (`/api/scripts/test-run`)

- Converts **the editor code** (not the saved draft) with `script_converter.py` (**never** `--no-threading`),
  writes `Converted Scripts/TEST_<Date.now()>.py`, runs `runner_bridge.py ... --data <rows JSON> --debug`.
- envConfig enrichment: `apiBaseUrl` from db.json, `Geocoding_api_key`, `master_data_config` from db.json.
- 90 s timeout; TEST file deleted on timeout/error/close (also by `/execute` if a `TEST_` name is executed).
- Non-zero exit still returns 200 if `[OUTPUT_DATA_DUMP]` is present (partial success).

## 5. Register (`/api/scripts/register`) - the publish step

1. Converts the request code (`--no-threading` only when `isMultithreaded === false`).
2. File name = `name.replace(/[^a-zA-Z0-9_-]/g,'_') + '.py'` → `Converted Scripts/`.
3. **Code beats UI**: `# CONFIG:` lines override groupByColumn/batchSize/isMultithreaded/enableGeofencing/
   allowAdditionalAttributes (default batchSize 10).
4. Upserts `System/scripts_registry.json` (match on name or filename; `{...existing, ...config}`), deletes the draft.
5. **Then assign a team on the Script Dashboard** - register always sends `team: "Unassigned"` (see C3).

## 6. Converter (`script_converter.py`) - what changes in the registered file
- Wraps everything in `def run(data, token, env_config)`; user `run` → `_user_run`.
- `requests.get/post/put/delete` → `_log_get/_log_post/...` (`[API_DEBUG]` logs; payload print disabled).
- Only `# CONFIG:` and `# EXPECTED_INPUT_COLUMNS:` comments survive (`ast.unparse`) - all other comments lost.
- Injects `builtins.data_df`, Mock workbook (prints `[OUTPUT_DATA_DUMP]`), legacy-script transforms
  (read_excel → data_df, removes `exit()`, token/base_url assignments, etc.).

---

## 7. Caveats (known, verified in code)

| # | Caveat |
|---|---|
| C1 | **Sync Steps from Code** only fills the Analysis panel, not the editable steps; it unticks Parallel/Batch, so the next Proceed to Test writes `isMultithreaded = False`, `batchSize = 1`. Paste Code → reverse-engineer is what repopulates steps. |
| C2 | Generator prompt tells the AI to `import components.geofence_utils_v2` (script_generator.py ~225, ~619) but **that module does not exist** - other prompt lines say `components.geofence_utils`. Geofencing scripts can fail with ImportError. |
| C3 | **Re-registering resets team to Unassigned** (and `additionalAttributes` to `[]`) → script disappears from the bulk page dropdown until re-assigned on the dashboard. |
| C4 | Generation failures look like success: no key → heuristic stub; AI failure → `# error:` + stub - both return `status: success`. Always read the top of the generated code. |
| C5 | Timeouts don't line up: generator model list × 2 × 90 s can exceed the 5-min cap (→ 504); analyze 90 s vs reverser up to 9 min; `/reverse-engineer` has no timeout. |
| C6 | Test-run's close handler can respond after the timeout already responded (no `headersSent` guard). |
| C7 | Test-run passes rows as a CLI argument (`--data`); very large test files may hit the Windows command-line limit (`/execute` uses `--data-file`). |
| C8 | `valid_token.txt` in the server's cwd silently overrides the token in every converted script (converter ~572). |
| C9 | `[Master Search]` detection never fires for UI prompts (UI writes `[MASTER]`); the always-on master-search block still instructs the import. |
| C10 | `/api/config/maps-key` returns the Gemini key to the browser. |
| C11 | `save-feedback` route is defined twice; the second is unreachable. `/upload` replies "registered" but never touches the registry. |
| C12 | Filename sanitisation differs: save-draft/register replace every non `[a-zA-Z0-9_-]` with `_`; rename/delete/content replace spaces and **drop** other chars. |

## 8. Change log (tool changes affecting creation)
- 2026-09-27 - `script_generator.py`: force IPv4 for outbound calls (fixes "Generating..." hang).
- 2026-09-27 - `/api/scripts/generate`: 5-minute timeout, stderr capture, spawn-error handling, single response.
- 2026-09-27 - PROJECT_RULES: strict no-manual-script-edit rule (fix the tool, regenerate).
