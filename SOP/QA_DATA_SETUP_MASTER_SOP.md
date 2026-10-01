# QA Data Setup (Master) SOP

Audited against code on 2026-10-01. Files: `Converted Scripts/QA_Data_Setup_Master.py`,
`Converted Scripts/master_components/*.py`, `components/master_flow.js`, `createbulkdata.html`
(`#master-flow-config`), `backend/api.js` (data-generate routes), registry entry `QA_Data_Setup_Master.py`.
Tests: `Manager/test_qa_data_setup_master.py`, `Internal Tests/js/master_flow_*.test.js`.

---

## 1. Purpose & strict rules
Creates fresh QA data in one run from a form (no Excel): **Add Farmer** (or existing farmers) → **Add Asset**
→ **Assign & Validate to Project** → optional **Area Audit V2** and/or **Crop & DOS** on the new CAs.

- Steps run the existing scripts as **byte-identical copies** in `Converted Scripts/master_components/`
  (Add_Farmer, Add_Asset, Assign_and_Validate_asset_to_Project, Area_Audit_V2, Add_or_update_Crop_and_DOS_to_CA).
  **Never edit the copies or the standalone originals.** All adaptation lives in the master's glue code.
- If a standalone script is changed with the user's explicit approval, re-copy it (`cp`) into
  `master_components/` - the regression suite fails while they differ.
- Each copy is loaded as its own module (`master_step_<key>`), so module globals never clash.

## 2. Step selection (UI → `masterFlow.steps`)
- Farmer is always step 1 (create, or "Add for existing farmer" = skip Add Farmer).
- Asset requires Farmer; Validate requires Asset; Area Audit and Crop/DOS each require Validate and are
  **independent of each other**. The run stops after the last selected step.
- Python enforces the same: `do_validate = do_asset and validate`, audit/edit require validate.

## 3. Inputs & mapping
| UI field | Source / API | Sent to step |
|---|---|---|
| Login (mandatory) | `/api/data-generate/user-info` → `companyId`, id, name | `env_config.companyId` (runner skips its own lookup) |
| Assigned To users | search `/api/data-generate/user-search` → `/services/user/api/users/search/companies/{companyId}?query=` | `AssignedTo User ID` = user `id` |
| Existing farmers | search `/api/data-generate/farmer-search` → `/services/farm/api/farmers/dropdownList?page=0&size=51&sort=lastModifiedDate,Desc&query=` | `Existing Farmer ID` = farmer `id` (label `firstName`) |
| Soil Type | dropdown `/api/data-generate/asset-masters?type=soil` → `/services/farm/api/soil-types?size=5000` | **name** (Add Asset maps name → tenant id) |
| Irrigation Type | dropdown `?type=irrigation` → `/services/master/api/irrigation-types?size=5000` (same source as Add Asset's master_search) | **name** |
| Project (single select) | search `/api/data-generate/project-search` → `/services/farm/api/projects/search?page=0&size=51&projectStatus=LIVE&projectExecutionStatus=TO_BE_STARTED&projectExecutionStatus=STARTED&projectStatus=UPCOMING&query=` | `Project ID` = project `id` (label `name`), sent as a number |
| Area Audit | existing V2 boundary + area size/unit inputs | `env_config.boundary`, `area_size`, `area_unit` |
| Variety (single select) | search `/api/data-generate/variety-search` → **POST** `/services/farm/api/crops/details/filter?page=0&size=100&sort=name,asc` body `{"search": "<query>"}`; varieties are flattened from each crop's `children` | `Variety Name` = variety **name** (Crop & DOS maps name → id with the same POST call); id kept as `editCa.varietyId` |
| DOS | `<input type="date">` → `YYYY-MM-DD` (e.g. `2026-09-01`) | `Date of Sowing (YYYY-MM-DD)` unchanged; the Crop & DOS copy's `parse_excel_date` PUTs `sowingDate: "2026-09-01T00:00:00.000+0000"` - identical to the standalone script fed an Excel date (serial 46266). Empty DOS → `sowingDate` not sent. Verified by `Internal Tests/python/test_dos_format.py` against the real copy. |

- Search pickers (shared `createSearchPicker`): min **3** characters, 350 ms debounce, out-of-order responses
  dropped, max **50** rows shown (+ "type more characters" note), multi-select chips "name (ID id)",
  selections cleared on login/tenant change. Users and farmers are multi-select; **project and variety are single-select**
  (`single: true` - picking another project replaces the current one; picking it again deselects).
  Project status filters (LIVE/UPCOMING, TO_BE_STARTED/STARTED) are fixed in the backend route.
- Soil/irrigation lists load once per login; a failed list is retried **only when the user clicks it**.
- Numeric IDs are passed as numbers (`_as_number`) - e.g. assign payload `[5982501]`, matching an Excel import.

## 4. Counter rule (`seriesValue`) - Farmer Name, Code, Phone, Asset Name
- Total 1 → value exactly as entered.
- Ends with a number → first as entered, then +1 keeping zero padding (`RS F 26171001` → `...002`; `A 99` → `A 100`).
- Otherwise → `value + ' ' + counter` padded to digits of total (`RS F 1..5`, `01..10`, `001..100`).
- Farmers number continuously across users (users × farmers per user); assets continuously across farmers.
- Phone: leading `+` removed (Add Farmer needs `91 9126271001`). Duplicates are left for the server to reject.

## 5. Execution (progressive)
1. Farmers in groups of 5 (`batchSize`) with steps `{farmer:true}` only → one row per farmer.
2. Right after each farmer group, that group's assets in groups of 5 with steps
   `{farmer:false, asset, validate, areaAudit, editCa}`; each row carries the farmer result
   (`Existing Farmer ID`, `Farmer Status`, `Farmer Response`) - failed farmers' assets come back `Skipped`.
3. Each group's rows are rendered as soon as it returns. Existing-farmer mode skips phase 1.
4. 401 → stop with a message (no auto-resume); other call failures → `Fail` rows for that group, run continues.

## 6. Output (one row per asset; order fixed, matches registry uiMapping)
`User Name, Farmer Name, Farmer ID, Farmer Code, Phone Number, Asset Name, Asset ID, CA ID, Audited Area,
Variety, DOS, Farmer Status, Asset Status, Validate Status, Area Audit Status, Crop/DOS Status, Status, Response`
(names before ids). `User Name` comes from the user picker selection (plan key `AssignedTo User Name`, display
only - never sent to Add Farmer); blank in existing-farmer mode.
Status = Pass only if every selected step is Pass/Existing; Response lists each failing step's own message
(each asset row has its own message list). `SKIP_INPUT_MERGE = True` so input plans are not merged in.
Logs: `[MASTER] <step> input i/n: ...` before every step.

## 7. Caveats
| # | Caveat |
|---|---|
| Q1 | Assign & Validate requires `recordsCompleted == 1`; an asset already pending in the project returns 2 and fails (seen in QA2). Use fresh assets. |
| Q2 | CA name is assumed to equal the asset name for Area Audit / Crop & DOS. |
| Q3 | User search returns users from other companies too; they are shown (not filtered). |
| Q4 | Farmer-search note cannot show a total (paged API); user search can. |
| Q5 | Each asset-group call re-fetches Add Asset master lists and V2 unit settings (a few extra GETs per group). |
| Q6 | Master detection is by filename (`MASTER_FILENAME`), not the registry `isMasterFlow` flag. |
| Q7 | Crop & DOS maps the variety by exact (case-insensitive) name; if no exact match it falls back to the **first variety of the first crop** returned. Picking from the search avoids this; duplicate variety names across crops resolve to the first match. |

## 8. Change log
- 2026-09-27 - Created (copies, orchestrator, form, registry entry); output User → Farmer → Asset → CA.
- 2026-09-27 - Fix: asset rows shared one message list (wrong Response on sibling assets).
- 2026-09-30 - Counter rule + progressive two-phase execution; static soil/irrigation names (later replaced).
- 2026-10-01 - Numeric IDs + step input logging; Project ID digits-only; mandatory login + user-info;
  user search, farmer search (shared picker, 50 cap); soil/irrigation dropdowns from tenant APIs.
- 2026-10-01 - Project ID replaced by single-select project search (`/api/data-generate/project-search`);
  shared picker gained the `single` option.
- 2026-10-01 - Variety text box replaced by single-select variety search (`/api/data-generate/variety-search`,
  new POST proxy helper `handlePostJsonRequest`); picker `plural` option ("No varieties found").
- 2026-10-01 - Output: `User ID` replaced by `User Name`; name columns now precede id columns (farmer, asset).
