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
        varietyName: $('mf-variety-name'),
        dos: $('mf-dos'),
        summary: $('mf-summary'),
        fileUploadArea: $('file-upload-area'),
        startRowInput: $('start-row-input'),
        exportBtn: $('export-btn'),
        importBtn: $('import-btn')
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

    /** Add_Farmer expects '91 9876543210' (no '+'). */
    function toScriptPhone(phone) {
        return String(phone || '').trim().replace(/^\+/, '');
    }

    /** Continuous asset names; counter width = digits of total (10 -> 01..10, 100 -> 001..100). */
    function buildAssetNames(prefix, total) {
        const width = String(total).length;
        const names = [];
        for (let i = 1; i <= total; i++) names.push(`${prefix}${String(i).padStart(width, '0')}`);
        return names;
    }

    function splitList(text) {
        return String(text || '').split(',').map(s => s.trim()).filter(Boolean);
    }

    /**
     * Builds one plan row per farmer.
     * opts: { existing, existingIds[], userIds[], farmersPerUser, name, code, phone, withAssets, assetPrefix, assetsPerFarmer }
     */
    function buildFarmerPlans(opts) {
        const plans = [];
        if (opts.existing) {
            opts.existingIds.forEach((id, i) => plans.push({
                'Farmer #': i + 1, 'Farmer Name': '', 'Farmer Code': '', 'Phone Number': '',
                'AssignedTo User ID': '', 'Existing Farmer ID': id
            }));
        } else {
            let k = 0;
            opts.userIds.forEach(userId => {
                for (let j = 0; j < opts.farmersPerUser; j++, k++) {
                    plans.push({
                        'Farmer #': k + 1,
                        'Farmer Name': incrementTrailingNumber(opts.name, k),
                        'Farmer Code': incrementTrailingNumber(opts.code, k),
                        'Phone Number': toScriptPhone(incrementTrailingNumber(opts.phone, k)),
                        'AssignedTo User ID': userId,
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
            farmersPerUser: intVal(ui.farmersPerUser),
            name: ui.farmerName.value.trim(),
            code: ui.farmerCode.value.trim(),
            phone: ui.farmerPhone.value.trim(),
            farmerAddress: ui.farmerAddress.value.trim(),
            withAssets,
            assetPrefix: ui.assetPrefix.value,
            assetsPerFarmer: intVal(ui.assetsPerFarmer),
            soilType: ui.soilType.value.trim(),
            irrigationType: ui.irrigationType.value.trim(),
            assetAddress: ui.assetAddress.value.trim(),
            declaredArea: ui.declaredArea.value.trim(),
            validate: withAssets && ui.stepValidate.checked,
            projectId: ui.projectId.value.trim(),
            areaAudit: withAssets && ui.stepValidate.checked && ui.stepAreaAudit.checked,
            editCa: withAssets && ui.stepValidate.checked && ui.stepEditCa.checked,
            varietyName: ui.varietyName.value.trim(),
            dos: ui.dos.value
        };
    }

    function validate(f) {
        const errors = [];
        if (f.existing) {
            if (!f.existingIds.length) errors.push('Enter at least one existing Farmer ID.');
            if (f.existingIds.some(id => !/^\d+$/.test(id))) errors.push('Existing Farmer IDs must be numbers.');
            if (!f.withAssets) errors.push('With existing farmers, select at least "Add Asset".');
        } else {
            if (!f.userIds.length) errors.push('Enter at least one AssignedTo User ID.');
            if (f.userIds.some(id => !/^\d+$/.test(id))) errors.push('AssignedTo User IDs must be numbers.');
            if (f.farmersPerUser < 1) errors.push('Farmers per User must be at least 1.');
            if (!/\d$/.test(f.name)) errors.push("First Farmer Name must end with a number (e.g. 'RS F 26171001').");
            if (!/\d$/.test(f.code)) errors.push('First Farmer Code must end with a number.');
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
        if (f.validate && !/^\d+$/.test(f.projectId)) errors.push('Enter a numeric Project ID.');
        if (f.areaAudit) {
            const b = [elements.minLat, elements.maxLat, elements.minLong, elements.maxLong];
            if (b.some(el => !el || el.value === '' || isNaN(Number(el.value)))) {
                errors.push('Area Audit: set Min/Max Latitude and Longitude (use Resolve or a saved location).');
            }
        }
        if (f.editCa && !f.varietyName && !f.dos) errors.push('Crop/DOS step: enter Variety Name and/or Date of Sowing.');
        return errors;
    }

    function updateSummary() {
        const f = readForm();
        const farmerCount = f.existing ? f.existingIds.length : f.userIds.length * Math.max(f.farmersPerUser, 0);
        const parts = [];
        if (f.existing) {
            parts.push(`${farmerCount} existing farmer(s)`);
        } else if (farmerCount > 0 && /\d$/.test(f.name)) {
            const last = incrementTrailingNumber(f.name, farmerCount - 1);
            parts.push(`${farmerCount} farmer(s): ${f.name}${farmerCount > 1 ? ' → ' + last : ''}`);
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

    /** Called by script.js after a script is selected, after login, and on reset. */
    function refresh() {
        const active = isMasterSelected();
        ui.panel.classList.toggle('hidden', !active);
        setUploadControlsVisible(!active);
        setImportButtonForMaster(active);
        if (!active) return;
        if (elements.templateInfo) elements.templateInfo.classList.add('hidden');
        if (elements.advancedSettingsSection) elements.advancedSettingsSection.classList.add('hidden');
        if (elements.batchSizeContainer) elements.batchSizeContainer.style.display = 'none';
        syncSteps();
        enableRun();
    }

    function enableRun() {
        if (isMasterSelected() && elements.executeBtn && authToken && !window.isExecutionActive) {
            elements.executeBtn.disabled = false;
            elements.executeBtn.textContent = '🚀 Run QA Data Setup';
        }
    }

    // ---------------- Execution ----------------

    async function execute() {
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
            masterFlow: {
                steps: { farmer: !f.existing, asset: f.withAssets, validate: f.validate, areaAudit: f.areaAudit, editCa: f.editCa },
                farmerAddress: f.farmerAddress,
                asset: { soilType: f.soilType, irrigationType: f.irrigationType, address: f.assetAddress, declaredArea: f.declaredArea },
                projectId: f.projectId,
                editCa: { varietyName: f.varietyName, dos: f.dos }
            }
        };

        startExecution('⏳ Running QA Data Setup...');
        const total = plans.length;
        let processed = 0, pass = 0, fail = 0;
        updateProgress(0, total, 0, 0);

        try {
            for (let i = 0; i < plans.length; i += farmersPerCall) {
                const chunk = plans.slice(i, i + farmersPerCall);
                const executor = new ScriptExecutorV2({ apiBaseUrl: envData.apiBaseUrl, debug: true });
                let chunkResults;
                try {
                    chunkResults = await executor.execute(MASTER_FILENAME, chunk, authToken, config, config.boundary);
                } catch (err) {
                    if (String(err.message).includes('401')) throw Object.assign(new Error('Session Expired'), { status: 401 });
                    chunkResults = chunk.map(p => ({
                        'User ID': p['AssignedTo User ID'], 'Farmer ID': p['Existing Farmer ID'], 'Farmer Name': p['Farmer Name'],
                        'Farmer Code': p['Farmer Code'], 'Phone Number': p['Phone Number'],
                        'Asset Name': (p['Asset Names'] || []).join(', '),
                        'Status': 'Fail', 'Response': `Batch failed: ${err.message}`
                    }));
                }
                executionResults = executionResults.concat(chunkResults);
                chunkResults.forEach(r => { if (evaluateRowStatus(r, template).isPass) pass++; else fail++; });
                processed += chunk.length;
                updateProgress(processed, total, pass, fail);
                renderExecutionResults();
            }
        } catch (error) {
            console.error('[MasterFlow] Execution stopped:', error);
            if (error.status === 401) {
                alert(`🛑 Session Expired\n\nStopped after ${processed} of ${total} farmer(s). Re-login and run again for the remaining farmers (adjust the first Name/Code/Phone and Asset Prefix).`);
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
        // exported for tests
        _helpers: { incrementTrailingNumber, toScriptPhone, buildAssetNames, buildFarmerPlans, splitList }
    };
})();
