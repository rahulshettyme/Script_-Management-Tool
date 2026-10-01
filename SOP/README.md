# Data Generate - Internal SOPs

**Internal only.** This folder is tracked in the source git repo but is **not** deployed:
`sync_push.bat` → `sync_links.py` copies only `backend/`, `System/`, `Converted Scripts/`, `components/`
and a fixed list of root files to `..\Cropin Cloud Github\QA-Ops_Workbench`; `publish_release.py` copies
only its `INCLUDE_PATHS` whitelist. Never move these files into one of those synced folders.

| SOP | Covers |
|---|---|
| [SCRIPT_CREATION_SOP.md](SCRIPT_CREATION_SOP.md) | Script Management page → generate (Gemini) → draft → test run → register |
| [SCRIPT_MOVEMENT_SOP.md](SCRIPT_MOVEMENT_SOP.md) | Folders, registry, script lifecycle (rename/delete/team), sync push/pull, deployment, git |
| [SCRIPT_EXECUTION_SOP.md](SCRIPT_EXECUTION_SOP.md) | Bulk data page → `/api/scripts/execute` → `runner_bridge.py` → results/export/audit |
| [QA_DATA_SETUP_MASTER_SOP.md](QA_DATA_SETUP_MASTER_SOP.md) | The QA Data Setup (Master) flow: step copies, phases, pickers, counter rule |

Related internal tooling:
- Regression suite: `python "Internal Tests/run_regression.py"` (see `.claude/skills/regression-guard/SKILL.md`)
- Project rules: [`PROJECT_RULES.md`](../PROJECT_RULES.md)

## How these SOPs are maintained (same model as the My Dashboard project)
1. **SOP-first lookup** - check the relevant SOP before searching code for a rule, field, default or behavior.
2. **Backfill** - if it is not in the SOP, find it in code and add it to the SOP in the same task.
3. **Update on change** - a code change that alters behavior documented here must update the SOP in the
   same task, and the SOP edit must be called out in the response.
4. **Verified, not intended** - every statement reflects the code as it is (file:line where useful).
   Known bugs are listed as *Caveats* rather than silently "fixed" in the text.

Line numbers are as of 2026-10-01 and will drift; search for the quoted symbol if a line no longer matches.
