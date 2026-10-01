---
name: "Regression Guard"
description: "Tests, reviews and regression-checks Data Generate code changes so legacy script execution never changes."
---

# Regression Guard

The canonical instructions live in `.claude/skills/regression-guard/SKILL.md` - read and follow that file.

Quick reference:
1. Read the relevant SOP in `SOP/` before changing code.
2. Apply the legacy-safety review checklist (no script hand-edits; shared execution path changes must be opt-in).
3. Add offline tests for the change (`Manager/test_qa_data_setup_master.py`, `Internal Tests/js/*.test.js`,
   `Internal Tests/run_regression.py`).
4. Run `python "Internal Tests/run_regression.py"` on every code change; report X/X passing (existing vs new,
   baseline in `Internal Tests/baseline.json`).
5. Report per PROJECT_RULES.md (incl. commit message only - never commit/push).
