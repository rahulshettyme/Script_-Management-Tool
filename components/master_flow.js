/**
 * QA Data Setup (Master) - custom UI + execution for QA_Data_Setup_Master.py
 *
 * Loaded after script.js and uses its globals (elements, TEMPLATES, selectedDataType,
 * authToken, currentEnvironment, currentTenant, executionResults, startExecution,
 * updateProgress, renderExecutionResults, completeExecution, evaluateRowStatus, getEnvUrls).
 *
 * Instead of an Excel upload, farmer rows are generated here from the form and sent to
 * the master script in batches of farmers.
 */
(function () {
    const MASTER_FILENAME = 'QA_Data_Setup_Master.py';
    const $ = (id) => document.getElementById(id);

    const ui = {
        panel: $('master-flow-config'),
        existingFarmer: $('mf-existing-farmer'),
        existingFields: $('mf-existing-farmer-fields'),
        existingIds: $('mf-existing-farmer-ids'),
        newFields: $('mf-new-farmer-fields'),
        userIds: $('mf-user-ids'),
        farmersPerUser: $('mf-farmers-per-user'),
        farmerName: $('mf-farmer-name'),
        farmerCode: $('mf-farmer-code'),
        farmerPhone: $('mf-farmer-phone'),
        farmerAddress: $('mf-farmer-address'),
        stepAsset: $('mf-step-asset'),
        assetFields: $('mf-asset-fields'),
        assetPrefix: $('mf-asset-prefix'),
        assetsPerFarmer: $('mf-assets-per-farmer'),
        soilType: $('mf-soil-type'),
        irrigationType: $('mf-irrigation-type'),
        assetAddress: $('mf-asset-address'),
        declaredArea: $('mf-declared-area'),
        stepValidate: $('mf-step-validate'),
        validateFields: $('mf-validate-fields'),
        projectId: $('mf-project-id'),
        stepAreaAudit: $('mf-step-area-audit'),
        stepEditCa: $('mf-step-edit-ca'),
        editCaFields: $('mf-edit-ca-fields'),
        varietyId: $('mf-variety-id'),
        varietySearch: $('mf-variety-search'),
        varietyResults: $('mf-variety-results'),
        varietyChips: $('mf-variety-chips'),
        dos: $('mf-dos'),
        summary: $('mf-summary'),
        fileUploadArea: $('file-upload-area'),
        startRowInput: $('start-row-input'),
        exportBtn: $('export-btn'),
        importBtn: $('import-btn'),
        loginNotice: $('mf-login-notice'),
        formBody: $('mf-form-body'),
        userSearch: $('mf-user-search'),
        userResults: $('mf-user-results'),
        userChips: $('mf-user-chips'),
        farmerSearch: $('mf-farmer-search'),
        farmerResults: $('mf-farmer-results'),
        farmerChips: $('mf-farmer-chips'),
        projectSearch: $('mf-project-search'),
        projectResults: $('mf-project-results'),
        projectChips: $('mf-project-chips')
    };
    if (!ui.panel) return;

    // ---------------- Pure helpers (exported for testing) ----------------

    /** 'RS F 26171001' + 2 -> 'RS F 26171003' (keeps zero padding). Returns null if no trailing number. */
    function incrementTrailingNumber(value, offset) {
        const m = /^(.*?)(\d+)$/.exec(String(value || '').trim());
        if (!m) return null;
        const next = (BigInt(m[2]) + BigInt(offset)).toString();
        return m[1] + next.padStart(m[2].length, '0');
    }

    /**
     * Counter rule for Farmer Name / Code / Phone and Asset Name (index is 0-based):
     *  - total 1                 -> value exactly as entered
     *  - value ends with number  -> first = as entered, then +1 ('RS F 26171001' -> '...002')
     *  - otherwise               -> value + ' ' + counter from 1, padded to digits of total
     *                               (5 -> 1..5, 10 -> 01..10, 100 -> 001..100)
     */
    function seriesValue(value, index, total) {
        const base = String(value || '').trim();
        if (total <= 1) return base;
        const incremented = incrementTrailingNumber(base, index);
        if (incremented !== null) return incremented;
        return `${base} ${String(index + 1).padStart(String(total).length, '0')}`;
    }

    /** Add_Farmer expects '91 9876543210' (no '+'). */
    function toScriptPhone(phone) {
        return String(phone || '').trim().replace(/^\+/, '');
    }

    /** Continuous asset names across all farmers. */
    function buildAssetNames(prefix, total) {
        const names = [];
        for (let i = 0; i < total; i++) names.push(seriesValue(prefix, i, total));
        return names;
    }

    function splitList(text) {
        return String(text || '').split(',').map(s => s.trim()).filter(Boolean);
    }

    /**
     * Builds one plan row per farmer.
     * opts: { existing, existingIds[], userIds[], userNames{id: name}, farmersPerUser, name, code, phone, withAssets, assetPrefix, assetsPerFarmer }
     */
    function buildFarmerPlans(opts) {
        const plans = [];
        if (opts.existing) {
            opts.existingIds.forEach((id, i) => plans.push({
                'Farmer #': i + 1, 'Farmer Name': '', 'Farmer Code': '', 'Phone Number': '',
                'AssignedTo User ID': '', 'Existing Farmer ID': id
            }));
        } else {
            const total = opts.userIds.length * opts.farmersPerUser;
            let k = 0;
            opts.userIds.forEach(userId => {
                for (let j = 0; j < opts.farmersPerUser; j++, k++) {
                    plans.push({
                        'Farmer #': k + 1,
                        'Farmer Name': seriesValue(opts.name, k, total),
                        'Farmer Code': seriesValue(opts.code, k, total),
                        'Phone Number': toScriptPhone(seriesValue(opts.phone, k, total)),
                        'AssignedTo User ID': userId,
                        'AssignedTo User Name': (opts.userNames && opts.userNames[userId]) || '',   // display only
                        'Existing Farmer ID': ''
                    });
                }
            });
        }
        const perFarmer = opts.withAssets ? opts.assetsPerFarmer : 0;
        const names = perFarmer ? buildAssetNames(opts.assetPrefix, plans.length * perFarmer) : [];
        plans.forEach((p, i) => { p['Asset Names'] = names.slice(i * perFarmer, (i + 1) * perFarmer); });
        return plans;
    }

    /**
     * Splits farmer plans into asset groups of up to groupSize assets (in order).
     * Each group is a list of plan rows carrying only that group's 'Asset Names'.
     * farmerResults[i] (optional) = { id, status, response } from the farmer phase.
     */
    function buildAssetGroups(plans, groupSize, farmerResults) {
        const groups = [];
        let current = [];
        let count = 0;
        const flush = () => { if (current.length) groups.push(current); current = []; count = 0; };
        plans.forEach((plan, i) => {
            const fr = farmerResults ? farmerResults[i] : null;
            const base = { ...plan };
            if (fr) {
                base['Existing Farmer ID'] = fr.id || '';
                base['Farmer Status'] = fr.status;
                base['Farmer Response'] = fr.response || '';
            }
            let names = plan['Asset Names'] || [];
            while (names.length) {
                const take = names.slice(0, groupSize - count);
                current.push({ ...base, 'Asset Names': take });
                count += take.length;
                names = names.slice(take.length);
                if (count >= groupSize) flush();
            }
        });
        flush();
        return groups;
    }

    // ---------------- Form state ----------------

    function isMasterSelected() {
        const t = (typeof TEMPLATES !== 'undefined' && selectedDataType) ? TEMPLATES[selectedDataType] : null;
        return !!(t && t.filename === MASTER_FILENAME);
    }

    function intVal(el) {
        const n = parseInt(el.value, 10);
        return Number.isFinite(n) ? n : 0;
    }

    function readForm() {
        const existing = ui.existingFarmer.checked;
        const withAssets = ui.stepAsset.checked;
        return {
            existing,
            existingIds: splitList(ui.existingIds.value),
            userIds: splitList(ui.userIds.value),
            userNames: Object.fromEntries(userPicker.getSelected().map(u => [u.id, u.name])),
            farmersPerUser: intVal(ui.farmersPerUser),
            name: ui.farmerName.value.trim(),
            code: ui.farmerCode.value.trim(),
            phone: ui.farmerPhone.value.trim(),
            farmerAddress: ui.farmerAddress.value.trim(),
            withAssets,
            assetPrefix: ui.assetPrefix.value,
            assetsPerFarmer: intVal(ui.assetsPerFarmer),
            // dropdown value is the id; Add Asset takes the name and maps it to the id itself
            soilType: (selectedMaster('soil', ui.soilType) || {}).name || '',
            soilTypeId: (selectedMaster('soil', ui.soilType) || {}).id || '',
            irrigationType: (selectedMaster('irrigation', ui.irrigationType) || {}).name || '',
            irrigationTypeId: (selectedMaster('irrigation', ui.irrigationType) || {}).id || '',
            assetAddress: ui.assetAddress.value.trim(),
            declaredArea: ui.declaredArea.value.trim(),
            validate: withAssets && ui.stepValidate.checked,
            projectId: ui.projectId.value.trim(),
            areaAudit: withAssets && ui.stepValidate.checked && ui.stepAreaAudit.checked,
            editCa: withAssets && ui.stepValidate.checked && ui.stepEditCa.checked,
            varietyName: (selectedVariety() || {}).name || '',
            varietyId: (selectedVariety() || {}).id || '',
            dos: ui.dos.value
        };
    }

    function validate(f) {
        const errors = [];
        if (f.existing) {
            if (!f.existingIds.length) errors.push('Select at least one existing farmer (search by name).');
            if (f.existingIds.some(id => !/^\d+$/.test(id))) errors.push('Selected farmer IDs must be numbers.');
            if (!f.withAssets) errors.push('With existing farmers, select at least "Add Asset".');
        } else {
            if (!f.userIds.length) errors.push('Select at least one Assigned To user (search by name).');
            if (f.userIds.some(id => !/^\d+$/.test(id))) errors.push('Selected user IDs must be numbers.');
            if (f.farmersPerUser < 1) errors.push('Farmers per User must be at least 1.');
            if (!f.name) errors.push('Enter First Farmer Name.');
            if (!f.code) errors.push('Enter First Farmer Code.');
            if (!/^\+?\d{1,4}[ -]\d+$/.test(f.phone)) errors.push("Phone Number must be like '+91 9126271001'.");
        }
        if (f.withAssets) {
            if (!f.assetPrefix.trim()) errors.push('Enter an Asset Name Prefix.');
            if (f.assetsPerFarmer < 1) errors.push('Assets per Farmer must be at least 1.');
            if (!f.soilType) errors.push('Select Soil Type.');
            if (!f.irrigationType) errors.push('Select Irrigation Type.');
            if (!f.assetAddress) errors.push('Enter Asset Address.');
            if (f.declaredArea === '' || isNaN(Number(f.declaredArea))) errors.push('Declared Area must be a number.');
        }
        if (f.validate && !/^\d+$/.test(f.projectId)) errors.push('Select a project (search by name).');
        if (f.areaAudit) {
            const b = [elements.minLat, elements.maxLat, elements.minLong, elements.maxLong];
            if (b.some(el => !el || el.value === '' || isNaN(Number(el.value)))) {
                errors.push('Area Audit: set Min/Max Latitude and Longitude (use Resolve or a saved location).');
            }
        }
        if (f.editCa && !f.varietyName && !f.dos) errors.push('Crop/DOS step: select a Variety and/or enter Date of Sowing.');
        return errors;
    }

    function updateSummary() {
        const f = readForm();
        const farmerCount = f.existing ? f.existingIds.length : f.userIds.length * Math.max(f.farmersPerUser, 0);
        const parts = [];
        if (f.existing) {
            parts.push(`${farmerCount} existing farmer(s)`);
        } else if (farmerCount > 0 && f.name) {
            const first = seriesValue(f.name, 0, farmerCount);
            const last = seriesValue(f.name, farmerCount - 1, farmerCount);
            parts.push(`${farmerCount} farmer(s): ${first}${farmerCount > 1 ? ' → ' + last : ''}`);
        } else {
            parts.push(`${farmerCount} farmer(s)`);
        }
        if (f.withAssets && f.assetsPerFarmer > 0 && farmerCount > 0) {
            const total = farmerCount * f.assetsPerFarmer;
            const names = buildAssetNames(f.assetPrefix, total);
            parts.push(`${total} asset(s): ${names[0]}${total > 1 ? ' → ' + names[total - 1] : ''}`);
        }
        const steps = ['Farmer'];
        if (f.withAssets) steps.push('Asset');
        if (f.validate) steps.push('Validate');
        if (f.areaAudit) steps.push('Area Audit');
        if (f.editCa) steps.push('Crop/DOS');
        ui.summary.textContent = `Will create ${parts.join(', ')}. Steps: ${steps.join(' → ')}.`;
    }

    /** Keeps step dependencies and the visible fields in sync. */
    function syncSteps() {
        const existing = ui.existingFarmer.checked;
        ui.existingFields.classList.toggle('hidden', !existing);
        ui.newFields.classList.toggle('hidden', existing);

        const assetOn = ui.stepAsset.checked;
        ui.assetFields.classList.toggle('hidden', !assetOn);
        ui.stepValidate.disabled = !assetOn;
        if (!assetOn) ui.stepValidate.checked = false;

        const validateOn = assetOn && ui.stepValidate.checked;
        ui.validateFields.classList.toggle('hidden', !validateOn);
        [ui.stepAreaAudit, ui.stepEditCa].forEach(cb => {
            cb.disabled = !validateOn;
            if (!validateOn) cb.checked = false;
        });
        ui.editCaFields.classList.toggle('hidden', !ui.stepEditCa.checked);

        // Area Audit reuses the existing Area Audit V2 / Boundary inputs
        const showAudit = isMasterSelected() && ui.stepAreaAudit.checked;
        if (elements.boundaryConfig) elements.boundaryConfig.classList.toggle('hidden', !showAudit);
        if (elements.v2SpecificConfig) elements.v2SpecificConfig.classList.toggle('hidden', !showAudit);

        updateSummary();
    }

    function setUploadControlsVisible(visible) {
        if (ui.fileUploadArea) ui.fileUploadArea.style.display = visible ? '' : 'none';
        const startRowGroup = ui.startRowInput ? ui.startRowInput.closest('.form-group') : null;
        if (startRowGroup) startRowGroup.style.display = visible ? '' : 'none';
        if (ui.exportBtn) {
            const group = ui.exportBtn.closest('.form-group');
            if (group) group.style.display = visible ? '' : 'none';
        }
    }

    /** This script needs no template: label the login action as data creation (master only). */
    const IMPORT_BTN_MASTER_TEXT = '🔐 Login and Create Data';
    const IMPORT_LABEL_MASTER_TEXT = 'Create Data';
    const importGroup = ui.importBtn ? ui.importBtn.closest('.form-group') : null;
    const importLabel = importGroup ? importGroup.querySelector('label') : null;
    const importLabelDefault = importLabel ? importLabel.textContent.replace(/\s+/g, ' ').trim() : '';

    function setImportButtonForMaster(active) {
        if (!ui.importBtn) return;
        if (active) {
            ui.importBtn.textContent = IMPORT_BTN_MASTER_TEXT;
            if (importLabel) importLabel.textContent = IMPORT_LABEL_MASTER_TEXT;
        } else if (ui.importBtn.textContent === IMPORT_BTN_MASTER_TEXT) {
            // Restore defaults only if we changed them (other scripts set their own text)
            ui.importBtn.textContent = '📤 Login and Import Template';
            if (importLabel) importLabel.textContent = importLabelDefault;
        }
    }

    // ---------------- Mandatory login + user info ----------------
    // Master APIs need the logged-in user's context, so the form stays locked until
    // login succeeds AND user-info returns a companyId.

    let session = null;          // { key, companyId, userId, userName, raw }
    let sessionLoad = null;      // in-flight user-info promise
    let failedKey = null;        // login whose user-info failed: no auto-retry (prevents a request loop), only via Retry

    function sessionKey() {
        return authToken ? `${currentEnvironment}|${currentTenant}|${authToken.slice(-16)}` : null;
    }

    function setNotice(kind, html) {
        if (!ui.loginNotice) return;
        const styles = {
            login: 'background:#fff3cd;border:1px solid #ffe08a;color:#7a5b00;',
            loading: 'background:#e3f2fd;border:1px solid #90caf9;color:#0d47a1;',
            ok: 'background:#e8f5e9;border:1px solid #c8e6c9;color:#1b5e20;',
            error: 'background:#fdecea;border:1px solid #f5c2c0;color:#8a1c14;'
        };
        ui.loginNotice.style.cssText = 'margin-bottom:0.75rem;padding:0.6rem 0.75rem;border-radius:4px;font-size:0.8rem;' + styles[kind];
        ui.loginNotice.innerHTML = html;
    }

    function setFormLocked(locked) {
        if (!ui.formBody) return;
        ui.formBody.style.opacity = locked ? '0.5' : '';
        ui.formBody.style.pointerEvents = locked ? 'none' : '';
        ui.formBody.setAttribute('aria-disabled', locked ? 'true' : 'false');
    }

    function escapeHtml(v) {
        return String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    /** Shows the login form straight away (no template import step for this script). */
    function showLoginSection() {
        if (elements.loginSection) elements.loginSection.classList.remove('hidden');
        if (elements.loginComponentContainer) elements.loginComponentContainer.classList.remove('hidden');
    }

    /** GET user-info once per login; stores companyId for master APIs. */
    function loadSession() {
        const key = sessionKey();
        if (!key) { session = null; return Promise.resolve(null); }
        if (session && session.key === key) return Promise.resolve(session);
        if (failedKey === key) return Promise.resolve(null);
        if (sessionLoad) return sessionLoad;

        setNotice('loading', '⏳ Logged in. Fetching user details...');
        const query = `environment=${encodeURIComponent(currentEnvironment)}&tenant=${encodeURIComponent(currentTenant)}`;
        sessionLoad = fetch(`/api/data-generate/user-info?${query}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
            .then(async res => {
                if (!res.ok) throw new Error(res.status === 401 ? 'Session expired - please log in again' : `HTTP ${res.status}`);
                const info = await res.json();
                if (!info || info.companyId == null) throw new Error('companyId not found in user-info response');
                session = { key, companyId: info.companyId, userId: info.id, userName: info.name || '', raw: info };
                failedKey = null;
                return session;
            })
            .catch(err => {
                console.error('[MasterFlow] user-info failed:', err);
                session = null;
                failedKey = key;
                setNotice('error', `⚠ Could not load user details: ${escapeHtml(err.message)}. ` +
                    `<a href="#" id="mf-retry-session">Retry</a>`);
                const retry = $('mf-retry-session');
                if (retry) retry.addEventListener('click', e => { e.preventDefault(); failedKey = null; refresh(); });
                return null;
            })
            .finally(() => { sessionLoad = null; });
        return sessionLoad.then(s => { if (isMasterSelected()) applySessionState(); return s; });
    }

    /** Lock/unlock the form and update the notice from the current login/session state. */
    function applySessionState() {
        if (!authToken) {
            session = null;
            setFormLocked(true);
            setNotice('login', '🔐 Login is required for this script. Log in on the right to start.');
            showLoginSection();
            return;
        }
        if (session && session.key === sessionKey()) {
            resetPickersForSession();
            loadAssetMasters();
            setFormLocked(false);
            setNotice('ok', `✅ Logged in as <strong>${escapeHtml(session.userName)}</strong> ` +
                `(User ID ${escapeHtml(session.userId)}) · Company ID <strong>${escapeHtml(session.companyId)}</strong>`);
            enableRun();
            return;
        }
        setFormLocked(true);
        if (failedKey === sessionKey()) return;   // keep the error + Retry link; don't re-request
        loadSession();
    }

    // ---------------- Search pickers (multi-select) ----------------
    // Shared by Assigned To users and Existing Farmers: type 3+ chars -> debounced search ->
    // results show "name (ID id)" -> click to select/deselect -> selected 'id's go to a hidden input.

    const SEARCH_MIN_CHARS = 3;
    const SEARCH_DEBOUNCE_MS = 350;
    // Max rows drawn in a search dropdown. The list has a fixed height + scroll, so this only
    // bounds DOM rows; users narrow the search for more.
    const SEARCH_MAX_RESULTS = 50;

    /** Search response -> [{id, name}] (list may be bare or wrapped in data/content/items). */
    function toItems(payload, nameField) {
        const list = Array.isArray(payload) ? payload : ((payload && (payload.data || payload.content || payload.items)) || []);
        return list
            .filter(it => it && it.id != null)
            .map(it => ({ id: String(it.id), name: String(it[nameField] || '').trim() || `ID ${it.id}` }));
    }
    const toUsers = payload => toItems(payload, 'name');
    const toFarmers = payload => toItems(payload, 'firstName');

    /**
     * opts: { input, results, chips, hidden, noun, buildUrl(query) -> url, parse(json) -> [{id,name}],
     *         totalKnown (true when the API returns all matches, so the total can be shown),
     *         single (true = one selection; picking another result replaces it), plural (default noun + 's') }
     */
    function createSearchPicker(opts) {
        let selected = [];          // [{ id, name }]
        let forKey = null;          // session the selection belongs to
        let timer = null;
        let seq = 0;                // drops out-of-order responses
        let lastResults = [];
        const label = it => `${it.name} (ID ${it.id})`;
        const plural = opts.plural || `${opts.noun}s`;

        function sync() {
            if (opts.hidden) opts.hidden.value = selected.map(it => it.id).join(', ');
            renderChips();
            updateSummary();
            enableRun();
        }

        function renderChips() {
            if (!opts.chips) return;
            opts.chips.innerHTML = '';
            selected.forEach(it => {
                const chip = document.createElement('span');
                chip.style.cssText = 'display:inline-flex;align-items:center;gap:4px;padding:3px 4px 3px 8px;background:#e3f2fd;border:1px solid #90caf9;border-radius:12px;font-size:0.75rem;color:#0d47a1;';
                chip.textContent = label(it);
                const remove = document.createElement('button');
                remove.type = 'button';
                remove.textContent = '×';
                remove.title = `Remove ${it.name}`;
                remove.style.cssText = 'border:none;background:transparent;color:#0d47a1;cursor:pointer;font-size:0.9rem;line-height:1;padding:0 4px;';
                remove.addEventListener('click', () => toggle(it));
                chip.appendChild(remove);
                opts.chips.appendChild(chip);
            });
        }

        function message(text) {
            if (!opts.results) return;
            opts.results.innerHTML = '';
            const msg = document.createElement('div');
            msg.style.cssText = 'padding:8px 10px;color:#666;';
            msg.textContent = text;
            opts.results.appendChild(msg);
            opts.results.classList.remove('hidden');
        }

        function renderResults(items) {
            lastResults = items;
            if (!opts.results) return;
            if (!items.length) return message(`No ${plural} found`);
            opts.results.innerHTML = '';
            items.slice(0, SEARCH_MAX_RESULTS).forEach(it => {
                const isSel = selected.some(s => s.id === it.id);
                const row = document.createElement('div');
                row.style.cssText = `padding:7px 10px;cursor:pointer;border-bottom:1px solid #f0f0f0;${isSel ? 'background:#e8f5e9;font-weight:600;' : ''}`;
                row.textContent = `${isSel ? '✓ ' : ''}${label(it)}`;
                // mousedown (not click) so the input's blur doesn't close the list first
                row.addEventListener('mousedown', e => { e.preventDefault(); toggle(it); });
                opts.results.appendChild(row);
            });
            if (items.length > SEARCH_MAX_RESULTS) {
                const more = document.createElement('div');
                more.style.cssText = 'padding:7px 10px;color:#7a5b00;background:#fff8e1;font-size:0.75rem;';
                more.textContent = opts.totalKnown
                    ? `Showing first ${SEARCH_MAX_RESULTS} of ${items.length} matches. Type more characters to narrow the search.`
                    : `Showing first ${SEARCH_MAX_RESULTS} matches. Type more characters to narrow the search.`;
                opts.results.appendChild(more);
            }
            opts.results.classList.remove('hidden');
        }

        function toggle(item) {
            if (selected.some(s => s.id === item.id)) selected = selected.filter(s => s.id !== item.id);
            else if (opts.single) selected = [{ id: item.id, name: item.name }];   // replace the current choice
            else selected = selected.concat([{ id: item.id, name: item.name }]);
            sync();
            if (opts.results && !opts.results.classList.contains('hidden') && lastResults.length) renderResults(lastResults);
        }

        async function search(query) {
            const mySeq = ++seq;
            if (!sessionReady()) return message(`Log in first to search ${plural}`);
            message('Searching...');
            try {
                const res = await fetch(opts.buildUrl(query), { headers: { 'Authorization': `Bearer ${authToken}` } });
                if (mySeq !== seq) return;
                if (!res.ok) throw new Error(res.status === 401 ? 'session expired, please log in again' : `HTTP ${res.status}`);
                const items = opts.parse(await res.json());
                if (mySeq !== seq) return;
                renderResults(items);
            } catch (e) {
                if (mySeq !== seq) return;
                console.error(`[MasterFlow] ${opts.noun} search failed:`, e);
                message(`Search failed: ${e.message}`);
            }
        }

        function onInput() {
            clearTimeout(timer);
            const query = opts.input.value.trim();
            if (query.length < SEARCH_MIN_CHARS) {
                seq++;   // cancel any pending response
                lastResults = [];
                if (query.length) message(`Type at least ${SEARCH_MIN_CHARS} characters to search`);
                else if (opts.results) opts.results.classList.add('hidden');
                return;
            }
            timer = setTimeout(() => search(query), SEARCH_DEBOUNCE_MS);
        }

        /** Selection belongs to one login/company; clear it when that changes. */
        function resetForSession() {
            const key = session ? session.key : null;
            if (forKey === key) return;
            forKey = key;
            selected = [];
            lastResults = [];
            if (opts.input) opts.input.value = '';
            if (opts.results) opts.results.classList.add('hidden');
            sync();
        }

        if (opts.input) {
            opts.input.addEventListener('input', onInput);
            opts.input.addEventListener('focus', () => {
                if (opts.input.value.trim().length >= SEARCH_MIN_CHARS && lastResults.length) renderResults(lastResults);
            });
            opts.input.addEventListener('blur', () => setTimeout(() => opts.results && opts.results.classList.add('hidden'), 150));
            opts.input.addEventListener('keydown', e => {
                if (e.key === 'Escape' && opts.results) opts.results.classList.add('hidden');
                if (e.key === 'Enter') e.preventDefault();
            });
        }

        return { resetForSession, getSelected: () => selected.slice() };
    }

    const envQuery = () => `environment=${encodeURIComponent(currentEnvironment)}&tenant=${encodeURIComponent(currentTenant)}`;

    // Assigned To users: 'name' shown, 'id' -> AssignedTo User ID. API returns all matches.
    const userPicker = createSearchPicker({
        input: ui.userSearch, results: ui.userResults, chips: ui.userChips, hidden: ui.userIds, noun: 'user',
        totalKnown: true,
        parse: toUsers,
        buildUrl: q => `/api/data-generate/user-search?${envQuery()}&companyId=${encodeURIComponent(session.companyId)}&query=${encodeURIComponent(q)}`
    });

    // Existing farmers: 'firstName' shown, 'id' -> Existing Farmer ID. The API is paged, so ask for
    // one more than we show to know whether to suggest narrowing the search.
    const farmerPicker = createSearchPicker({
        input: ui.farmerSearch, results: ui.farmerResults, chips: ui.farmerChips, hidden: ui.existingIds, noun: 'farmer',
        totalKnown: false,
        parse: toFarmers,
        buildUrl: q => `/api/data-generate/farmer-search?${envQuery()}&size=${SEARCH_MAX_RESULTS + 1}&query=${encodeURIComponent(q)}`
    });

    // Project (single select): 'name' shown, 'id' -> Project ID for Assign & Validate. LIVE/UPCOMING projects
    // that are TO_BE_STARTED/STARTED (filters fixed in the backend route). Paged API -> ask for 51.
    const projectPicker = createSearchPicker({
        input: ui.projectSearch, results: ui.projectResults, chips: ui.projectChips, hidden: ui.projectId, noun: 'project',
        totalKnown: false,
        single: true,
        parse: payload => toItems(payload, 'name'),
        buildUrl: q => `/api/data-generate/project-search?${envQuery()}&size=${SEARCH_MAX_RESULTS + 1}&query=${encodeURIComponent(q)}`
    });

    /** Variety search response: crops with varieties nested in 'children' -> flat [{id, name}] (variety level). */
    function toVarieties(payload) {
        const crops = Array.isArray(payload) ? payload : ((payload && (payload.data || payload.content || payload.items)) || []);
        const out = [];
        crops.forEach(crop => (crop && Array.isArray(crop.children) ? crop.children : []).forEach(v => {
            if (v && v.id != null) out.push({ id: String(v.id), name: String(v.name || '').trim() || `ID ${v.id}` });
        }));
        return out;
    }

    // Variety (single select): 'name' shown, 'id' kept; the name goes to the unchanged Crop & DOS copy,
    // which looks it up with the same POST {search} call and maps it to the id.
    const varietyPicker = createSearchPicker({
        input: ui.varietySearch, results: ui.varietyResults, chips: ui.varietyChips, hidden: ui.varietyId, noun: 'variety', plural: 'varieties',
        totalKnown: false,
        single: true,
        parse: toVarieties,
        buildUrl: q => `/api/data-generate/variety-search?${envQuery()}&query=${encodeURIComponent(q)}`
    });

    function selectedVariety() {
        const sel = varietyPicker.getSelected()[0];
        return sel && ui.varietyId && ui.varietyId.value === sel.id ? sel : null;
    }

    function resetPickersForSession() {
        varietyPicker.resetForSession();
        userPicker.resetForSession();
        farmerPicker.resetForSession();
        projectPicker.resetForSession();
    }

    // ---------------- Soil / Irrigation type dropdowns ----------------
    // Small lists -> plain dropdowns loaded once per login. Option value = 'id', label = 'name'.
    // The unchanged Add Asset copy takes the name and maps it to the tenant id itself.

    const ASSET_MASTERS = [
        { type: 'soil', select: () => ui.soilType, noun: 'soil type' },
        { type: 'irrigation', select: () => ui.irrigationType, noun: 'irrigation type' }
    ];
    const masterLists = { soil: [], irrigation: [] };   // [{ id, name }]
    const masterState = {};                              // type -> { key, status: 'loading'|'ok'|'failed' }

    function fillMasterSelect(select, items, placeholder) {
        if (!select) return;
        const previous = select.value;
        select.innerHTML = '';
        const first = document.createElement('option');
        first.value = '';
        first.textContent = placeholder;
        select.appendChild(first);
        items.forEach(it => {
            const opt = document.createElement('option');
            opt.value = it.id;
            opt.textContent = it.name;
            select.appendChild(opt);
        });
        if (items.some(it => it.id === previous)) select.value = previous;
        else select.value = '';
    }

    /** Loads once per login. A failed list is only retried when the user clicks it (retry=true). */
    async function loadAssetMaster(m, retry = false) {
        const key = session ? session.key : null;
        const state = masterState[m.type];
        if (!key) return;
        if (state && state.key === key && !(retry && state.status === 'failed')) return;
        masterState[m.type] = { key, status: 'loading' };
        fillMasterSelect(m.select(), [], `Loading ${m.noun}s...`);
        try {
            const res = await fetch(`/api/data-generate/asset-masters?type=${m.type}&${envQuery()}`,
                { headers: { 'Authorization': `Bearer ${authToken}` } });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const items = toItems(await res.json(), 'name');
            if (!session || session.key !== key) return;          // login changed meanwhile
            masterLists[m.type] = items;
            masterState[m.type] = { key, status: 'ok' };
            fillMasterSelect(m.select(), items, items.length ? `Select ${m.noun}` : `No ${m.noun}s found`);
        } catch (e) {
            console.error(`[MasterFlow] Failed to load ${m.type} types:`, e);
            masterLists[m.type] = [];
            masterState[m.type] = { key, status: 'failed' };
            fillMasterSelect(m.select(), [], `⚠ Failed to load ${m.noun}s - click to retry`);
        }
        updateSummary();
    }

    // explicit arrow: forEach's index argument must not be taken as 'retry'
    function loadAssetMasters() { ASSET_MASTERS.forEach(m => loadAssetMaster(m)); }

    /** Selected { id, name } of a dropdown, or null. */
    function selectedMaster(type, select) {
        const id = select ? select.value : '';
        return masterLists[type].find(it => it.id === id) || null;
    }

    // Retry a failed list only when the user opens that dropdown (never automatically)
    ASSET_MASTERS.forEach(m => {
        const select = m.select();
        if (!select) return;
        select.addEventListener('mousedown', () => {
            const st = masterState[m.type];
            if (st && st.status === 'failed') loadAssetMaster(m, true);
        });
    });

    /** Called by script.js after a script is selected, after login, and on reset. */
    function refresh() {
        const active = isMasterSelected();
        ui.panel.classList.toggle('hidden', !active);
        setUploadControlsVisible(!active);
        setImportButtonForMaster(active);
        if (!active) return;
        applySessionState();
        if (elements.templateInfo) elements.templateInfo.classList.add('hidden');
        if (elements.advancedSettingsSection) elements.advancedSettingsSection.classList.add('hidden');
        if (elements.batchSizeContainer) elements.batchSizeContainer.style.display = 'none';
        syncSteps();
        enableRun();
    }

    function sessionReady() {
        return !!(authToken && session && session.key === sessionKey() && session.companyId != null);
    }

    function enableRun() {
        if (isMasterSelected() && elements.executeBtn && sessionReady() && !window.isExecutionActive) {
            elements.executeBtn.disabled = false;
            elements.executeBtn.textContent = '🚀 Run QA Data Setup';
        }
    }

    // ---------------- Execution ----------------

    async function execute() {
        if (!sessionReady()) return alert('Please log in first. User details (company) must load before creating data.');
        const f = readForm();
        const errors = validate(f);
        if (errors.length) return alert('Please fix the following:\n\n• ' + errors.join('\n• '));

        const plans = buildFarmerPlans(f);
        if (!plans.length) return alert('Nothing to create.');
        updateSummary();
        if (!confirm(ui.summary.textContent + '\n\nProceed?')) return;

        const template = TEMPLATES[selectedDataType] || {};
        const farmersPerCall = Math.max(parseInt(template.batchSize, 10) || 5, 1);
        const envData = getEnvUrls(currentEnvironment);
        const config = {
            environment: currentEnvironment,
            tenant: currentTenant,
            apiurl: envData.apiBaseUrl,
            apiBaseUrl: envData.apiBaseUrl,
            boundary: {
                minLat: elements.minLat ? elements.minLat.value : '',
                maxLat: elements.maxLat ? elements.maxLat.value : '',
                minLong: elements.minLong ? elements.minLong.value : '',
                maxLong: elements.maxLong ? elements.maxLong.value : '',
                locationName: elements.locationName ? elements.locationName.value : ''
            },
            targetLocation: elements.v2LocationName ? elements.v2LocationName.value : '',
            area_size: f.areaAudit && elements.v2AreaSize ? elements.v2AreaSize.value : undefined,
            area_unit: f.areaAudit && elements.v2AreaUnit ? elements.v2AreaUnit.value : undefined,
            allowAdditionalAttributes: false,
            additionalAttributes: [],
            batchSize: farmersPerCall,
            // from user-info at login (runner_bridge skips its own lookup when companyId is present)
            companyId: session.companyId,
            company_id: session.companyId,
            masterFlow: {
                steps: { farmer: !f.existing, asset: f.withAssets, validate: f.validate, areaAudit: f.areaAudit, editCa: f.editCa },
                farmerAddress: f.farmerAddress,
                asset: { soilType: f.soilType, soilTypeId: f.soilTypeId, irrigationType: f.irrigationType,
                    irrigationTypeId: f.irrigationTypeId, address: f.assetAddress, declaredArea: f.declaredArea },
                projectId: f.projectId,
                editCa: { varietyName: f.varietyName, varietyId: f.varietyId, dos: f.dos }
            }
        };

        startExecution('⏳ Running QA Data Setup...');
        const groupSize = farmersPerCall;
        const totalRows = f.withAssets ? plans.reduce((n, p) => n + p['Asset Names'].length, 0) : plans.length;
        let processed = 0, pass = 0, fail = 0;
        let farmersDone = 0;
        updateProgress(0, totalRows, 0, 0);

        const stepsFarmerOnly = { farmer: true, asset: false, validate: false, areaAudit: false, editCa: false };
        const stepsAssetChain = { farmer: false, asset: true, validate: f.validate, areaAudit: f.areaAudit, editCa: f.editCa };

        /** One master call. Returns result rows, or throws on session expiry. */
        async function callMaster(rows, steps, fallbackRows) {
            const executor = new ScriptExecutorV2({ apiBaseUrl: envData.apiBaseUrl, debug: true });
            const callConfig = { ...config, masterFlow: { ...config.masterFlow, steps } };
            try {
                const result = await executor.execute(MASTER_FILENAME, rows, authToken, callConfig, callConfig.boundary);
                return Array.isArray(result) ? result : fallbackRows('Batch failed: unexpected response from server');
            } catch (err) {
                if (String(err.message).includes('401')) throw Object.assign(new Error('Session Expired'), { status: 401 });
                return fallbackRows(`Batch failed: ${err.message}`);
            }
        }

        /** Rows shown when a whole call fails: one per asset (or per farmer when no assets). */
        function failedRows(rows, message) {
            const out = [];
            rows.forEach(p => {
                const base = {
                    'User Name': p['AssignedTo User Name'] || '', 'Farmer Name': p['Farmer Name'], 'Farmer ID': p['Existing Farmer ID'] || '',
                    'Farmer Code': p['Farmer Code'], 'Phone Number': p['Phone Number']
                };
                const names = p['Asset Names'] || [];
                if (!names.length) out.push({ ...base, 'Status': 'Fail', 'Response': message });
                names.forEach(n => out.push({ ...base, 'Asset Name': n, 'Status': 'Fail', 'Response': message }));
            });
            return out;
        }

        /** Adds finished rows to the table immediately. */
        function showRows(rows) {
            executionResults = executionResults.concat(rows);
            rows.forEach(r => { if (evaluateRowStatus(r, template).isPass) pass++; else fail++; });
            processed += rows.length;
            updateProgress(processed, totalRows, pass, fail);
            renderExecutionResults();
        }

        function setPhase(text) { elements.executeBtn.textContent = text; }

        async function runAssetGroups(planSlice, farmerResults) {
            const groups = buildAssetGroups(planSlice, groupSize, farmerResults);
            for (const group of groups) {
                setPhase(`⏳ Assets ${processed + 1}–${Math.min(processed + groupSize, totalRows)} of ${totalRows}...`);
                showRows(await callMaster(group, stepsAssetChain, msg => failedRows(group, msg)));
            }
        }

        try {
            if (f.existing) {
                // Existing farmers: straight to asset groups
                await runAssetGroups(plans, null);
            } else {
                for (let i = 0; i < plans.length; i += groupSize) {
                    const chunk = plans.slice(i, i + groupSize);
                    setPhase(`⏳ Farmers ${i + 1}–${i + chunk.length} of ${plans.length}...`);
                    // Farmer phase: master returns one row per farmer, in order
                    const farmerOnlyRows = chunk.map(p => ({ ...p, 'Asset Names': [] }));
                    const farmerRows = await callMaster(farmerOnlyRows, stepsFarmerOnly, msg => failedRows(farmerOnlyRows, msg));
                    farmersDone += chunk.length;

                    if (!f.withAssets) {
                        showRows(farmerRows);
                        continue;
                    }
                    // Carry each farmer's result into its asset rows (failed farmers -> assets Skipped)
                    const farmerResults = chunk.map((p, k) => {
                        const r = farmerRows[k] || {};
                        const ok = r['Farmer Status'] === 'Pass' && r['Farmer ID'];
                        return {
                            id: ok ? String(r['Farmer ID']) : '',
                            status: ok ? 'Pass' : 'Fail',
                            response: ok ? '' : String(r['Response'] || 'Farmer creation failed').replace(/^Farmer:\s*/, '')
                        };
                    });
                    await runAssetGroups(chunk, farmerResults);
                }
            }
        } catch (error) {
            console.error('[MasterFlow] Execution stopped:', error);
            if (error.status === 401) {
                alert(`🛑 Session Expired\n\nStopped after ${processed} of ${totalRows} row(s)${f.existing ? '' : ` (${farmersDone} farmer(s) created or attempted)`}. Re-login and run again for the remaining data (adjust the first Name/Code/Phone and Asset Prefix).`);
            } else {
                alert('Execution Interrupted: ' + error.message);
            }
        } finally {
            completeExecution();
        }
    }

    // ---------------- Wiring ----------------

    [ui.existingFarmer, ui.stepAsset, ui.stepValidate, ui.stepAreaAudit, ui.stepEditCa]
        .forEach(el => el.addEventListener('change', syncSteps));
    // Any edit updates the preview and re-enables Run (after a completed run the button
    // stays disabled until inputs change, to avoid re-running the same names by accident)
    ['input', 'change'].forEach(evt => ui.panel.addEventListener(evt, () => { updateSummary(); enableRun(); }));

    window.MasterFlow = {
        MASTER_FILENAME,
        isMasterSelected,
        refresh,
        execute,
        /** Logged-in user context from user-info ({ companyId, userId, userName, raw }) or null. */
        getSession: () => (sessionReady() ? session : null),
        // exported for tests
        _helpers: { incrementTrailingNumber, seriesValue, toScriptPhone, buildAssetNames, buildFarmerPlans, buildAssetGroups, splitList, toUsers, toFarmers, toVarieties },
        _getSelectedUsers: () => userPicker.getSelected(),
        _getSelectedFarmers: () => farmerPicker.getSelected(),
        _getSelectedProject: () => projectPicker.getSelected()[0] || null,
        _getSelectedVariety: () => varietyPicker.getSelected()[0] || null
    };
})();
