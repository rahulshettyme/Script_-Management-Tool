# Script Movement SOP (folders, registry, lifecycle, sync & deployment)

Audited against code on 2026-10-01. Files: `backend/api.js`, `System/scripts_registry.json`,
`sync_links.py`, `sync_push.bat`, `sync_pull.bat`, `publish_release.py`, `.gitignore`, `Dockerfile`,
`.github/workflows/prod-workflow.yaml`, `script_dashboard.js`.

---

## 1. Folders

| Folder | Role | Deployed by sync push? |
|---|---|---|
| `Draft Scripts/` | Work-in-progress `<name>.py` (raw, unconverted) + `<name>.py.meta.json` | No (git-ignored too) |
| `Converted Scripts/` | Runnable scripts executed by `/api/scripts/execute`; `thread_utils.py`, `geofence_utils.py` | **Yes** (`/MIR`) |
| `Converted Scripts/master_components/` | Byte-identical step copies used only by `QA_Data_Setup_Master.py` | **Yes** (git whitelisted) |
| `components/` | Shared Python (`master_search`, `attribute_utils`, `geofence_utils`) + JS (`master_flow`, `executor_v2`, ...) | **Yes** |
| `backend/` | `api.js` (all routes) | **Yes** |
| `System/` | `server.js`, `scripts_registry.json`, `db.json` (env URLs, SSO, master_data_config, saved locations), `secrets.json` (keys) | **Yes** except `secrets.json`, `audittrail*.json`, `*.txt`, `*.bak` |
| `Manager/` | Tooling (generator, converter, analyzer, reverser, tests) | Only `runner_bridge.py` |
| `temp_data/` | Per-run `run_data_<ts>.json`, deleted after each run | No |
| `SOP/`, `Internal Tests/`, `.claude/`, `.agents/` | **Internal only** - in source git, never synced | No |

Two different `geofence_utils.py` files exist (`components/` returns the full Google result;
`Converted Scripts/` returns only bounds). Most scripts import `components.geofence_utils`.

---

## 2. Script lifecycle

| Action | Route | Files touched |
|---|---|---|
| Save draft | `POST /api/scripts/save-draft` | `Draft Scripts/<safe>.py` + `.meta.json`; old draft deleted on rename |
| Test | `POST /api/scripts/test-run` | temp `Converted Scripts/TEST_<ts>.py` (deleted) |
| Register (publish) | `POST /api/scripts/register` | `Converted Scripts/<safe>.py`, registry upsert, draft deleted |
| Assign team | `POST /api/scripts/update-meta` (Script Dashboard) | registry `team` / `isReusable` / `description` |
| Rename | `POST /api/scripts/rename` | draft `.py`/meta, converted `.py`, registry name+filename |
| Delete | `POST /api/scripts/delete` | draft `.py`/meta, converted `.py`, registry entry - **not** `master_components/` copies |
| Upload (bulk page) | `POST /api/scripts/upload` | writes file to `Converted Scripts/` as-is; **does not** register |

**A script appears on the bulk data page only if** it has a registry entry whose `team` contains `qa`/`cs`
or is `Both` (missing team defaults to QA). **`Unassigned` = hidden.**

## 3. Registry (`System/scripts_registry.json`)
- 2-space-indented JSON **array**; every writer uses `JSON.stringify(registry, null, 2)`. A parse error makes
  `/api/scripts/custom` return 500 and **empties the dropdown for everyone** - edit only when the server is idle,
  and only with a JSON-aware tool (round-trip the whole file; verify the diff is additions only).
- Fields read by the bulk page (`loadCustomScripts`): name, filename, team, description, columns /
  expected_columns, requiresLogin, isMultithreaded, batchSize, allowLargeBatch, groupByColumn,
  enableGeofencing, allowAdditionalAttributes, additionalAttributes, outputConfig.
- Ignored by the bulk page: `status`, `comments`, `isReusable`, `generation_prompt`, `isMasterFlow`,
  `outputColumns` (the master flow is detected by filename, not `isMasterFlow`).
- Template key = registry `name` (not filename) - see Execution SOP caveat on `syncTemplateWithLiveMeta`.

## 4. Sync push / pull & deployment
- **`sync_push.bat` → `sync_links.py`**: breaks old junction links, deletes target `System/secrets.json`, then
  `robocopy /MIR` for `backend`, `System`, `Converted Scripts`, `components` (excluding `*.log *.txt *.bak
  secrets.json audittrail*.json`, `__pycache__ .git .vscode`), and copies root files `Manager/runner_bridge.py`,
  `createbulkdata.html`, `script.js`, `style.css`, `package.json`, `requirements.txt`, `logo.png`.
  Target: `..\Cropin Cloud Github\QA-Ops_Workbench`.
- **`sync_pull.bat` (`--back`)** mirrors the deploy repo **over local with deletion** - local-only files in
  the four folders are removed. Commit/back up local work first.
- **`publish_release.py`** (alternative): copies `INCLUDE_PATHS`; unlike sync it **does** copy `*.txt`,
  `*.bak`, `audittrail*.json`, `TEST_*.py`. Run from the project root.
- **Production**: `.github/workflows/prod-workflow.yaml` builds the Docker image from the deploy repo on push to
  `main`; `Dockerfile` does `COPY . .` (so anything inside the deploy repo ships).
- **New internal-only content** must live outside the four synced folders (e.g. `SOP/`, `Internal Tests/`).
  **New runtime content** inside a synced folder must also be checked against **both** `.gitignore` files
  (`git check-ignore -v <path>` in this repo and in QA-Ops_Workbench - the deploy repo's `.gitignore` is NOT synced).

## 5. Git (`.gitignore` privacy whitelist)
- `Converted Scripts/*` + `!Converted Scripts/*.py` + `!Converted Scripts/master_components/`
- `Manager/*` + `!Manager/runner_bridge.py`; `Draft Scripts/`; `*.txt` (except requirements.txt); `*.bak`;
  `System/*.json` except `db.json` and `scripts_registry.json`; `System/secrets.json`.
- Commit messages are provided by the agent; **the agent never commits or pushes** (PROJECT_RULES).

## 6. Caveats
| # | Caveat |
|---|---|
| M1 | Re-register resets `team` to `Unassigned` → script vanishes from the dropdown. Re-assign after every update. |
| M2 | `TEST_*.py` are **not** git-ignored (the `!Converted Scripts/*.py` rule wins) - a leftover would be committed and synced. The regression suite flags leftovers. |
| M3 | `.gitignore` only affects untracked files; several ignored-pattern files are already tracked. |
| M4 | `express.static` serves the whole project root locally (incl. `System/db.json`, `Draft Scripts/`, and `secrets.json` locally) - relevant when sharing via `share_script_tool.bat` (ngrok). |
| M5 | Updating/deleting a standalone step script does **not** update `master_components/` copies (and vice versa). |
| M6 | All sync/link scripts hardcode `C:\Users\rahul.shetty\...` paths. |
| M7 | Registry names are inconsistent (`'Generate Coordinates.py'`, `PR Enable.py` with a space). |

## 7. Change log
- 2026-09-27 - `.gitignore` (both repos): `!Converted Scripts/master_components/` so master step copies deploy.
- 2026-09-27 - Registry: added `QA Data Setup (Master)` (team QA, `isMasterFlow`, uiMapping).
- 2026-10-01 - Added internal-only `SOP/`, `Internal Tests/`, `.claude/skills/regression-guard/` (not synced).
