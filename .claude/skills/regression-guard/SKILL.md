---
name: regression-guard
description: Test, review and regression-check any code change in Data Generate (script creation tool, execution tool, QA Data Setup master flow) so legacy script execution never changes. Use after every code change, before reporting it done, or when the user asks to test/review changes.
---

# Regression Guard (Data Generate)

Internal tooling - lives outside the synced folders, never deployed.
Run everything from the project root.

## 1. Before changing code
1. Read the SOP for the area you touch (`SOP/README.md` index):
   creation → `SOP/SCRIPT_CREATION_SOP.md`, execution → `SOP/SCRIPT_EXECUTION_SOP.md`,
   folders/registry/sync → `SOP/SCRIPT_MOVEMENT_SOP.md`, master flow → `SOP/QA_DATA_SETUP_MASTER_SOP.md`.
2. Classify the change:
   - **Shared execution path** (`backend/api.js` `/api/scripts/execute`, `Manager/runner_bridge.py`,
     `Converted Scripts/thread_utils.py`, `components/*.py`, `script.js` execute/render/export, `components/executor_v2.js`)
     → every existing script runs through it: **highest risk**.
   - **Creation tool** (`script_generator.py`, `script_converter.py`, `script_management_v2.js`, register/save-draft routes)
     → affects newly generated/registered scripts only; existing files in `Converted Scripts/` must not change.
   - **Master flow only** (`QA_Data_Setup_Master.py`, `components/master_flow.js`, `#master-flow-config`, data-generate routes).

## 2. Legacy-safety review checklist (block the change if any answer is "no")
- [ ] No hand edit to any script in `Converted Scripts/` or `Draft Scripts/` (incl. `master_components/`, `TEST_*`,
      `.meta.json`) unless the user explicitly asked for that specific script. Script bugs are fixed in the tool.
- [ ] Shared-path changes are **opt-in** and default to old behavior (pattern: a module flag like
      `SKIP_INPUT_MERGE`, a new env_config key, a new route) - nothing existing scripts already rely on changes:
      `run(data, token, env_config)` signature, row merge by index, `---JSON_START---` envelope,
      `[OUTPUT_DATA_DUMP]`, builtins (data/token/env_config/output_columns), `thread_utils.run_in_parallel`
      ordering + fallback, `batchSize` = worker count, env_config keys, interceptor retry/injection.
- [ ] Existing routes keep path, inputs and response shape; new behavior goes in a new route or optional param.
- [ ] Registry edits are JSON-round-tripped and additions-only (`git diff System/scripts_registry.json`).
- [ ] No new request loops: any auto-load/retry is once per key; failures retry only on user action.
- [ ] Internal-only files stay out of `backend/ System/ Converted Scripts/ components/` (synced by sync push);
      new deployable files are checked with `git check-ignore -v` in **both** repos.
- [ ] No secrets added to logs, responses or committed files.

## 3. Add tests for the change
| Change area | Where to add the test |
|---|---|
| Master orchestration (Python) | `Manager/test_qa_data_setup_master.py` (fake step modules, no network) |
| Real step-copy behavior (formats, payloads) | `Internal Tests/python/test_*.py` (load the real copy, patch `requests` in-process, assert the captured request) |
| Master flow UI / pickers / dropdowns | `Internal Tests/js/master_flow_*.test.js` (stub DOM + mocked fetch) |
| New/changed backend route | `Internal Tests/js/backend_routes.test.js` (stub app; add to `REQUIRED`, assert 400s + upstream path) |
| Runner / shared execution path | extend `check_smoke()` in `Internal Tests/run_regression.py` (offline: `apiBaseUrl` `http://127.0.0.1:9`) |
| New structural invariant | add a `record(...)` check in `Internal Tests/run_regression.py` |
Every test must be offline (no real Cropin/Google calls) and must fail on the bug it guards against.
Any JS test that could hang (loops, retries) must finish quickly - the runner kills JS tests after 60 s.

## 4. Run the suite (mandatory on every code change)
```
python "Internal Tests/run_regression.py"
```
- If the user explicitly approved editing a standalone script: add `--allow-script <File>.py` (repeatable),
  then re-copy it into `master_components/` if it is a master step.
- Must end with `RESULT: PASS`. Fix failures; never weaken a check to make it pass.
- **Baseline ratchet** (`Internal Tests/baseline.json` = checks that existed before this task):
  if this task added N checks, report N new, then run once more with `--update-baseline`
  so the next task starts from the new total. If no checks were added, "new" must read 0
  (update the baseline first if it is stale).

## 5. Report (closing block of the response)
Follow PROJECT_RULES.md items 1-6 (new files, modified files, why, risks, impact areas, commit message -
message only, never commit/push), mention any SOP updated in the same task, ask the user to test manually
(no browser automation), and end with:
```
✅ Regression suite: python "Internal Tests/run_regression.py" → X/X passing (Y existing, Z new)
📝 Suggested commit message:
<commit message>
```
