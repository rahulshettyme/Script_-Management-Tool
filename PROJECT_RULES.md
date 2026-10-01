# Project Rules for Changes

For every change implemented in this codebase, the developer/agent MUST provide a response containing the following six items:

1. **New files created** — A list of any new files added to the codebase.
2. **Files modified** — A list of existing files that were updated.
3. **Why each file modification was needed** — A brief, technical rationale for each change.
4. **Risk to be taken care of during testing** — Potential pitfalls, edge cases, or issues to monitor during QA/verification.
5. **Probable impact areas** — Areas of the application that might be affected by the changes.
6. **Commit message** — A ready-to-use git commit message for the change (subject line + short body). **STRICT:** provide the message only; do NOT run `git commit`, `git push` or any other git write/push activity unless the user explicitly asks.

## SOP Rules (internal SOPs in `SOP/`)
- **SOP before change:** BEFORE proposing or making a change to script creation, script execution, script
  movement/sync, or the QA Data Setup (Master) flow, read the matching SOP (`SOP/README.md` lists them).
- **SOP-first lookup & backfill:** to answer a question about a rule, field, default or behavior, check the SOP
  first. Only if it is missing, search the code - then add the finding to the SOP in the same task.
  The SOP is a fast path for lookups, not a substitute for verifying current code before changing it.
- **SOP update on change:** if a change alters behavior an SOP documents, update that SOP (incl. its change log)
  in the same task and call the SOP edit out explicitly in the response.
- **Internal only:** `SOP/`, `Internal Tests/`, `.claude/` and `.agents/` are tracked in git but must never be
  placed inside the folders copied by sync push (`backend/`, `System/`, `Converted Scripts/`, `components/`).

## Testing Rules
- **No Feature Automation Testing:** Do not perform browser-based or feature automation testing after code changes/fixes are made.
- **Backend Testing & Code Review:** Always perform code reviews and run backend tests automatically.
- **Mandatory regression suite:** on every code change run `python "Internal Tests/run_regression.py"` from the
  project root (skill: `.claude/skills/regression-guard/SKILL.md`), add offline tests for the change, and report
  `X/X passing (Y existing, Z new)` using the baseline in `Internal Tests/baseline.json`.
- **Legacy execution protection:** changes to the shared execution path (`/api/scripts/execute`,
  `Manager/runner_bridge.py`, `thread_utils.py`, `components/*.py`, the bulk page execute/render/export code)
  must be opt-in and default to existing behavior, so legacy scripts run exactly as before.
- **Manual User Testing:** Inform the user to perform manual testing for verification of feature changes.

## Script Failures and Modification Rules
- **STRICT — No Manual Script Edits:** Never edit any script in `Draft Scripts/` or `Converted Scripts/` (including `TEST_*.py` copies and `.meta.json` files) by hand. Any script generation or conversion issue MUST be fixed in the tool (`Manager/script_generator.py`, `Manager/script_converter.py`, `Manager/runner_bridge.py`, `System/server.js`, etc.). The only exception is when the user manually and explicitly asks for a specific script to be edited.
- **Tool Updates Over Direct Script Fixes:** Any script failures or bugs in generated/converted scripts must be treated as a tool failure (e.g., in `script_generator.py`). Scripts must not be modified directly unless the user explicitly and specifically requests it.
- **Regeneration Workflow:** Always fix the underlying generator tool first, then let the user recreate/regenerate the failed script using the updated tool.

## Geocoding and API Key Rules
- **Geocoding Key Standardization:** The application must strictly use the official `Geocoding_api_key` key (loaded from `env_config.get('Geocoding_api_key')`) for all geocoding, address, and geolocation tasks.
- **GOOGLE_API_KEY Restriction:** The `GOOGLE_API_KEY` (loaded from the user's personal config/environment) is restricted ONLY for script creation/onboarding (calling Gemini API to generate scripts).
- **Backend Key Injection:** The Node.js backend must always inject `Geocoding_api_key` (obtained via `getGeocodingApiKey()`) into the `envConfig` payload before spawning or testing any Python scripts.
