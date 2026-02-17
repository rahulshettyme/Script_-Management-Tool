/**
 * SCRIPT MANAGEMENT V2 (Development/Test Environment)
 * 
 * CRITICAL ARCHITECTURE RULE:
 * This file handles the "Test Run" logic for scripts.
 * The Production execution logic is located in `Data Generate/script.js` (Bulk Executor).
 * 
 * ANY change to execution logic, attribute handling, or environment resolution HERE
 * MUST be mirrored in `script.js` to ensure the Test environment accurately mocks Production.
 * 
 * Associated Backend Endpoints:
 * - Test: /api/scripts/test-run
 * - Prod: /api/scripts/execute
 */
const API_BASE = window.location.origin; // Dynamic Base URL (works for localhost & ngrok)

// State
let lastOutputData = null;
let detectedColumns = [];
let envConfig = {};
let authToken = localStorage.getItem('authToken');
let userEnv = localStorage.getItem('selectedEnvironment') || 'QA';
let currentFilename = null; // For draft
let originalFilename = null; // For Rename Logic
let currentTeam = "Unassigned"; // PRESERVE TEAM ASSIGNMENT
let isDraftSaved = false;

// TEMP: Custom Base URL for Auth
let customBaseUrl = localStorage.getItem('customBaseUrl') || "";

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
    await fetchEnvConfig();
    fetchMapsKeyAndInit(); // Fire and forget (async load)

    // Setup Custom URL Input
    const urlInput = document.getElementById('tempBaseUrl');
    if (urlInput) {
        urlInput.value = customBaseUrl;
        urlInput.addEventListener('change', () => {
            const val = urlInput.value.trim();
            // Remove trailing slash
            const cleanVal = val.endsWith('/') ? val.slice(0, -1) : val;
            localStorage.setItem('customBaseUrl', cleanVal);
            location.reload(); // Reload to apply
        });
    }

    // Default View: Ensure "Create" view is active
    const descGroup = document.getElementById('descGroup');
    if (descGroup) descGroup.style.display = 'block';

    const editorGroup = document.getElementById('editorGroup');
    if (editorGroup) editorGroup.style.display = 'block';
    // Removed specific display properties for loadScriptGroup as it is now in modal

    // Check for URL params to auto-load script
    const urlParams = new URLSearchParams(window.location.search);
    const filename = urlParams.get('filename');

    if (filename) {
        console.log("Auto-loading script:", filename);
        // We trigger fetch to populate cache for future opens, but we don't need to wait for it 
        // to load the script itself if we trust the filename. 
        // However, to know if it's a draft, we might need the list.
        await fetchScriptsList();

        // Find if it's a draft
        // cachedScriptListData is populated by fetchScriptsList
        const draftItem = cachedScriptListData.find(i => i.name === filename && i.isDraft);

        if (draftItem) {
            await loadScriptByName(`DRAFT:${filename}`);
        } else {
            // Fallback to trying Active
            await loadScriptByName(filename);
        }
    }
});

// --- Modal Handlers ---

window.toggleAdditionalAttributes = function (checkbox) {
    const container = document.getElementById('attributesContainer');
    if (container) {
        // Global toggle decides if the box is visible at all
        container.style.display = checkbox.checked ? 'block' : 'none';

        // If hidden/unchecked, ensure the runtime toggle is also reset? 
        // No, keep state. But maybe uncheck runtime if global is off.
    }
}

window.toggleTestAttributesInput = function (checkbox) {
    const inputWrapper = document.getElementById('testAttributesInputWrapper');
    if (inputWrapper) {
        inputWrapper.style.display = checkbox.checked ? 'block' : 'none';
    }
}

function toggleThreadSize(checkbox) {
    const container = document.getElementById('threadSizeContainer');
    if (container) {
        container.style.opacity = checkbox.checked ? '1' : '0.3';
        container.style.pointerEvents = checkbox.checked ? 'all' : 'none';
        // Note: We don't hide it completely so user sees the option exists
    }
}

window.toggleGeofence = function (checkbox) {
    const geoContainer = document.getElementById('geofenceContainer');
    if (geoContainer) {
        geoContainer.style.display = checkbox.checked ? 'block' : 'none';
        if (checkbox.checked && !window.googleMapsLoaded) {
            fetchMapsKeyAndInit();
        }
    }
}

// Google Maps Integration
window.googleMapsLoaded = false;
async function fetchMapsKeyAndInit() {
    if (window.googleMapsLoaded) return;
    try {
        const res = await fetch('/api/config/maps-key');
        const data = await res.json();
        if (data.key) {
            loadGoogleMaps(data.key);
        } else {
            console.warn("Google Maps API Key not found in backend.");
        }
    } catch (e) {
        console.error("Failed to fetch Maps Key:", e);
    }
}

function loadGoogleMaps(apiKey) {
    if (window.googleMapsLoaded) return;

    // Check if script already exists
    if (document.querySelector('script[src*="maps.googleapis.com"]')) {
        window.googleMapsLoaded = true;
        initAutocomplete();
        return;
    }

    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&callback=initAutocomplete`;
    script.async = true;
    script.defer = true;
    script.onerror = () => console.error("Google Maps Script Failed to Load");
    document.head.appendChild(script);
    window.googleMapsLoaded = true; // Optimistic set
}

window.initAutocomplete = function () {
    console.log("Initializing Google Maps Autocomplete...");
    const input = document.getElementById('targetLocation');
    if (!input) return;

    // Check if google is available
    if (!window.google || !window.google.maps || !window.google.maps.places) {
        console.warn("Google Maps Places lib not loaded yet.");
        return;
    }

    const autocomplete = new google.maps.places.Autocomplete(input, {
        types: ['(regions)'] // Cities, Administrative Areas (Matches Geofence logic)
    });

    autocomplete.addListener('place_changed', () => {
        const place = autocomplete.getPlace();
        if (place.formatted_address) {
            console.log("Selected Location:", place.formatted_address);
            input.value = place.formatted_address; // Use the clean name
        }
    });
}

window.openPasteModal = function () {
    document.getElementById('pasteModal').style.display = 'flex';
    document.getElementById('pasteCodeEditor').focus();
}

window.closePasteModal = function () {
    document.getElementById('pasteModal').style.display = 'none';
}

window.handlePasteCode = async function () {
    const code = document.getElementById('pasteCodeEditor').value;
    if (!code || code.trim().length < 10) return alert("Please paste valid Python code.");

    const btn = document.getElementById('btnLoadReverse');
    const originalText = btn.innerHTML;
    btn.innerHTML = "Reversing... ⏳";
    btn.disabled = true;

    try {
        document.getElementById('scriptName').placeholder = "Imported Script";

        // Sync UI Configuration (Grouping, Threading) from # CONFIG comments
        // syncUIFromCode(code); // Removed, will be called with cleanCode later

        // --- NEW: Auto-Extract Description from Comments ---
        try {
            const lines = code.split('\n');

            let codeStartIndex = 0;
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();

                // STOP only if we hit actual code start
                if (line.startsWith('import ') || line.startsWith('from ') || line.startsWith('def ') || line.startsWith('class ') || line.startsWith('@')) {
                    codeStartIndex = i;
                    break;
                }

                // If line starts with #, process it
                if (line.startsWith('#')) {
                    // It's a comment, so code *could* start here (e.g. headers), 
                    // BUT we want to capture description. 
                    // If we treat # as code start, we include headers in the code.
                    // If we treat it as description, we might strip it.
                    // Strategy: Comments are valid python, so we CAN leave them in the code.
                    // However, to be "smart", if we extracted it as description, maybe we don't need it?
                    // User request: "Original Script ... has these info".
                    // Safest: Keep comments in the code, but strip PURE GARBAGE.

                    // So, if we hit a #, that is potentially the start of the "Script File".
                    // But the user's snippet has "Folder highlights" BEFORE "Author:".
                    // "Folder highlights" is garbage.
                    // "# Author:" is valid comment.

                    // Logic: The "Script" starts at the first line that is EITHER valid code OR a comment.
                    // Garbage lines (no #, no code) should be skipped.
                    // So we shouldn't break on #, we should just mark it as "Valid Line".
                    // But we need to know where to slice.

                    // If I iterate until I hit 'import', I might skip valid top-level comments.
                    // e.g. 
                    // Garbage
                    // # Valid Comment
                    // import foo

                    // If I break at import, I exclude # Valid Comment? 
                    // No, I need to break at the *first* "Non-Garbage" line.

                }
            }

            // Re-Scan to find CLEAN start
            let cleanStart = 0;
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line) continue;
                // If it is code or comment, this is the start
                if (line.startsWith('#') || line.startsWith('import ') || line.startsWith('from ') || line.startsWith('def ') || line.startsWith('class ') || line.startsWith('@')) {
                    cleanStart = i;
                    break;
                }
                // Else it is garbage text, continue skipping
            }

            // Extract Description Loop (Keep existing logic but use it purely for description)
            let descriptionLines = [];
            for (let i = 0; i < lines.length; i++) {
                // ... (Existing extraction logic) ...
                const line = lines[i].trim();
                if (line.startsWith('import ') || line.startsWith('from ') || line.startsWith('def ') || line.startsWith('class ') || line.startsWith('@')) break;
                if (line.startsWith('#')) {
                    const content = line.substring(1).trim();
                    if (content.toLowerCase().startsWith('author:')) continue;
                    if (content.toLowerCase().startsWith('copyright')) continue;
                    if (content.includes('EXPECTED_INPUT_COLUMNS')) continue;
                    if (content.startsWith('CONFIG:')) continue;
                    if (content.length > 0) descriptionLines.push(content);
                }
            }

            if (descriptionLines.length > 0) {
                document.getElementById('scriptDescription').value = descriptionLines.join('\n');
            }

            // CLEAN THE EDITOR CONTENT
            // Re-construct code from cleanStart
            const cleanCode = lines.slice(cleanStart).join('\n');
            document.getElementById('pythonCode').value = cleanCode;

            // Sync UI from CLEAN code
            syncUIFromCode(cleanCode);

        } catch (descErr) {
            console.warn("Description extraction failed", descErr);
            // Fallback
            document.getElementById('pythonCode').value = code;
        }

        // Auto-trigger Reverse Analysis (Unified)
        // Use cleanCode if available, else code
        await autoPopulateStepsFromAI(document.getElementById('pythonCode').value);

        // Single Source of Truth: The AI Reversal now populates both Builder AND Analysis visuals.
        // No need to call analyzeScript() separately.
    } catch (e) {
        console.error("Paste Logic Error:", e);
        alert("Error processing code: " + e.message);
    } finally {
        closePasteModal();
        // Clear the paste area
        document.getElementById('pasteCodeEditor').value = '';

        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

window.openLoadModal = function () {
    document.getElementById('loadScriptModal').style.display = 'flex';
    fetchScriptsList(); // Refresh list on open
}

window.closeLoadModal = function () {
    document.getElementById('loadScriptModal').style.display = 'none';
}

// handleLoadScript() is removed as items are clickable directly


// Helper to load by name (refactored from loadSelectedScript)
async function loadScriptByName(filenameKey) {
    // filenameKey can be "DRAFT:name.py" or "name.py"
    let filename = filenameKey;

    // TRACK ORIGINAL FILENAME FOR RENAME LOGIC
    // If it's a draft, we track it directly. If active, we still track it as base name.
    // Logic: If user saves as different name, we send this. Backend checks if different.
    window.originalFilename = filename.replace("DRAFT:", "");

    let isDraft = false;
    let displayMsg = "Script loaded! You can now analyze, test, or Update it.";

    // Check if it's explicitly a draft selection
    if (filename.startsWith("DRAFT:")) {
        isDraft = true;
        filename = filename.replace("DRAFT:", "");
    } else {
        // It's an Active script selection.
        // Check if a hidden draft exists (window.availableDraftFiles populated by fetchScriptsList)
        const hiddenDraft = window.availableDraftFiles && window.availableDraftFiles.find(d => d.name === filename);
        if (hiddenDraft) {
            console.log(`Auto-switching to Draft version for ${filename}`);
            isDraft = true;
            displayMsg = `Loaded DRAFT version for '${filename}' (continuing work).`;
        }
    }

    try {
        const endpoint = isDraft ? `/api/scripts/content-draft?filename=${filename}` : `/api/scripts/content?filename=${filename}`;
        const res = await fetch(endpoint, { cache: "no-store" });
        const data = await res.json();

        if (data.content) {
            document.getElementById('pythonCode').value = data.content;

            // V2 UI Toggle
            if (window.toggleAreaAuditV2UI) {
                window.toggleAreaAuditV2UI(filename.replace('.py', '')); // Pass the script name (e.g. Area_Audit_V2.py)
            }

            // Enable Proceed button immediately (Analysis optional)
            document.getElementById('proceedBtn').style.display = 'inline-block';
            document.getElementById('scriptName').value = filename.replace('.py', '');
            window.lastGeneratedDescription = data.generationPrompt || "";

            const mtCheckbox = document.getElementById('isMultithreaded');
            if (mtCheckbox) {
                // If isMultithreaded is explicitly false, unchecked. Else default (true) or checked.
                mtCheckbox.checked = (data.meta && data.meta.isMultithreaded === false) ? false : true;
                toggleThreadSize(mtCheckbox); // Update UI state
            }

            const threadSizeSelect = document.getElementById('threadSize');
            if (threadSizeSelect) {
                threadSizeSelect.value = (data.meta && data.meta.batchSize) ? data.meta.batchSize : 10;
            }

            // Populate Description
            const descInput = document.getElementById('scriptDescription');
            if (descInput) {
                descInput.value = (data.meta && data.meta.description) ? data.meta.description : "";
            }

            // New Flags
            if (document.getElementById('allowAdditionalAttributes')) {
                const attrCheckbox = document.getElementById('allowAdditionalAttributes');
                const isAttrEnabled = !!(data.meta && data.meta.allowAdditionalAttributes);
                attrCheckbox.checked = isAttrEnabled;

                // Trigger visibility toggle
                if (window.toggleAdditionalAttributes) window.toggleAdditionalAttributes(attrCheckbox);

                // Populate Inputs if enabled
                if (isAttrEnabled && data.meta && data.meta.additionalAttributes) {
                    const attrInput = document.getElementById('testAttributes');
                    if (attrInput) {
                        attrInput.value = Array.isArray(data.meta.additionalAttributes)
                            ? data.meta.additionalAttributes.join(', ')
                            : "";
                    }
                }
            }
            if (document.getElementById('enableGeofencing')) {
                const geoCheckbox = document.getElementById('enableGeofencing');
                const isGeoEnabled = !!(data.meta && data.meta.enableGeofencing);
                geoCheckbox.checked = isGeoEnabled;
            }

            const groupByInput = document.getElementById('groupByColumn');
            if (groupByInput) {
                // Event Listener for Manual Input
                groupByInput.addEventListener('input', function () {
                    const mtCheckbox = document.getElementById('isMultithreaded');
                    const mtLabel = mtCheckbox.nextElementSibling;

                    if (this.value.trim()) {
                        // Grouping Active -> Disable External Threading
                        mtCheckbox.checked = false;
                        mtCheckbox.disabled = true;
                        mtLabel.innerHTML = "External Threading Disabled (Using Internal Script Threads) 🔒";
                        mtLabel.style.color = "#64748b"; // Slate-500
                        toggleThreadSize(mtCheckbox);
                    } else {
                        // Grouping Empty -> Enable Control
                        mtCheckbox.disabled = false;
                        mtLabel.innerHTML = "Enable Multithreading 🚀";
                        mtLabel.style.color = "#cbd5e1"; // Reset color
                    }
                });

                // Initial State Check
                const groupVal = (data.meta && data.meta.groupByColumn);
                groupByInput.value = groupVal || "";

                if (groupVal) {
                    const mtCheckbox = document.getElementById('isMultithreaded');
                    if (mtCheckbox) {
                        mtCheckbox.checked = false;
                        mtCheckbox.disabled = true;

                        const mtLabel = mtCheckbox.nextElementSibling;
                        if (mtLabel) {
                            mtLabel.innerHTML = "External Threading Disabled (Using Internal Script Threads) 🔒";
                            mtLabel.style.color = "#64748b";
                        }
                        toggleThreadSize(mtCheckbox);
                    }
                }
            }

            // Restore Additional Attributes
            const allowAttr = document.getElementById('allowAdditionalAttributes');
            const testAttrInput = document.getElementById('testAttributes');
            const useAttrCheckbox = document.getElementById('useTestAttributes');

            if (allowAttr) {
                // 1. Set Capability
                allowAttr.checked = !!(data.meta && data.meta.allowAdditionalAttributes);
                window.toggleAdditionalAttributes(allowAttr); // Show/Hide Container

                // 2. Set Runtime Values & Toggle
                if (data.meta && data.meta.additionalAttributes && data.meta.additionalAttributes.length > 0) {
                    // Restore logic: e.g. ["color=red", "size=large"] -> "color=red, size=large"
                    const val = Array.isArray(data.meta.additionalAttributes) ?
                        data.meta.additionalAttributes.join(', ') :
                        data.meta.additionalAttributes;

                    if (testAttrInput) testAttrInput.value = val;

                    // If values exist, we assume user wanted them enabled?
                    // Or we default to OFF? User said "should be just like how we will have in data generate page" (usually off by default?)
                    // But for a draft, if I saved it with values, I probably want them back.
                    if (useAttrCheckbox) {
                        useAttrCheckbox.checked = true;
                        if (window.toggleTestAttributesInput) window.toggleTestAttributesInput(useAttrCheckbox);
                    }
                } else {
                    if (testAttrInput) testAttrInput.value = "";
                    if (useAttrCheckbox) {
                        useAttrCheckbox.checked = false;
                        if (window.toggleTestAttributesInput) window.toggleTestAttributesInput(useAttrCheckbox);
                    }
                }
            }
            // Brace removed here to keep window.currentTeam inside the main block
            window.currentTeam = (data.meta && data.meta.team) ? data.meta.team : "Unassigned";
            console.log(`Loaded Team: ${window.currentTeam}`);

            // --- Output Config Population (Modal) ---
            if (data.meta && data.meta.outputConfig) {
                const conf = data.meta.outputConfig;

                // 1. UI Mapping (Dynamic)
                const uiContainer = document.getElementById('uiOutputRowsContainer');
                if (uiContainer) {
                    uiContainer.innerHTML = ''; // Clear
                    const msg = document.getElementById('noUiRowsMsg');
                    if (conf.uiMapping && Array.isArray(conf.uiMapping) && conf.uiMapping.length > 0) {
                        if (msg) msg.style.display = 'none';
                        conf.uiMapping.forEach(row => {
                            if (window.addUIOutputRow) window.addUIOutputRow(row);
                        });
                    } else if (conf.nameAttribute || conf.codeAttribute || conf.responseAttribute) {
                        // FALLBACK: Legacy Fields in Meta -> Convert to Dynamic Rows
                        if (msg) msg.style.display = 'none';
                        if (conf.nameAttribute) window.addUIOutputRow({ colName: 'Name', value: conf.nameAttribute, logic: conf.nameLogic });
                        if (conf.codeAttribute) window.addUIOutputRow({ colName: 'Code', value: conf.codeAttribute, logic: conf.codeLogic });
                        if (conf.responseAttribute) window.addUIOutputRow({ colName: 'Response', value: conf.responseAttribute, logic: conf.responseLogic });
                    } else {
                        // Empty
                        if (msg) msg.style.display = 'block';
                    }
                }

                if (document.getElementById('modalOutputInstructions')) document.getElementById('modalOutputInstructions').value = conf.aiInstructions || "";

                // Excel Rows
                const excelContainer = document.getElementById('excelOutputRowsContainer');
                if (excelContainer) {
                    excelContainer.innerHTML = ''; // Clear
                    if (conf.excelMapping && Array.isArray(conf.excelMapping)) {
                        conf.excelMapping.forEach(row => {
                            if (window.addExcelOutputRow) window.addExcelOutputRow(row);
                        });
                    } else {
                        // Show default msg if empty
                        excelContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #64748b; font-style: italic;" id="noExcelRowsMsg">No Excel columns defined. The script will output raw API response by default.</div>';
                    }
                }
            } else {
                // Clear fields if no config
                const uiContainer = document.getElementById('uiOutputRowsContainer');
                if (uiContainer) {
                    uiContainer.innerHTML = `
                             <div style="text-align: center; padding: 20px; color: #64748b; font-style: italic; background: rgba(15, 23, 42, 0.3); border-radius: 6px;" id="noUiRowsMsg">
                                No UI columns defined. Default columns (Name, Code, Response) might be used if empty.
                            </div>`;
                }

                if (document.getElementById('modalOutputInstructions')) document.getElementById('modalOutputInstructions').value = "";

                const excelContainer = document.getElementById('excelOutputRowsContainer');
                if (excelContainer) excelContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #64748b; font-style: italic;" id="noExcelRowsMsg">No Excel columns defined. The script will output raw API response by default.</div>';
            }
            // --------------------------------

            // Populate Steps
            let stepsParsed = false;
            if (data.generationPrompt) {
                parseAndPopulateSteps(data.generationPrompt);
                const rows = document.querySelectorAll('#stepsContainer .step-row');
                if (rows.length > 0) stepsParsed = true;
            }

            if (!stepsParsed) {
                const container = document.getElementById('stepsContainer');
                container.innerHTML = `
                    <div style="text-align: center; color: #64748b; padding: 20px;">
                        Draft copy of steps is not present.<br>
                        <span style="font-size: 0.9em; color: #94a3b8;">Use <strong>✨ AI Auto-Steps</strong> or <strong>Analyze Script</strong> to generate them.</span>
                    </div>`;
            }
            // Trigger Analysis automatically on load to show visual representation
            // analyzeScript(); // Optional? Maybe explicit is better. User might just want to edit.

            // alert(displayMsg); // Removed alert for smoother UX
            console.log(displayMsg);

            // Update Analysis View
            // analyzeScript(); 

        } else {
            alert("Failed to load content.");
        }
    } catch (e) {
        alert("Error loading script: " + e.message);
    }
}

// --- DUPLICATE / COPY LOGIC ---
async function loadScriptAsCopy(filename, isDraft) {
    const key = isDraft ? `DRAFT:${filename}` : filename;
    await loadScriptByName(key);

    // 1. Append _copy to name
    const nameInput = document.getElementById('scriptName');
    if (nameInput) {
        nameInput.value = nameInput.value + "_copy";
    }

    // 2. Clear originalFilename tracking so it saves as NEW file, not rename
    window.originalFilename = null;
    currentFilename = null;
    window.currentTeam = "Unassigned"; // Reset team for copies
    isDraftSaved = false; // Reset saved state

    console.log("Loaded as copy. Original filename cleared.");
    // Alert user?
    // alert("Script loaded as copy. Please Save/Proceed to Test to create the new draft.");

    closeLoadModal(); // Close the popup
}

// --- Load Script Logic ---
// --- Load Script Logic ---
// --- Load Script Logic ---
let cachedScriptListData = []; // Store for filtering

async function fetchScriptsList() {
    const listContainer = document.getElementById('scriptListContainer');
    if (!listContainer) return;

    listContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b;">Loading...</div>';

    try {
        const [resProd, resDraft] = await Promise.all([
            fetch('/api/scripts/list'),
            fetch('/api/scripts/list-drafts')
        ]);

        const prodFiles = await resProd.json();
        const draftFiles = await resDraft.json();

        window.availableDraftFiles = draftFiles;

        cachedScriptListData = [];

        // 1. Process Drafts
        // Group by Name to find unique scripts
        const activeNames = new Set(prodFiles.map(f => f.name));

        // Orphan Drafts
        draftFiles.forEach(d => {
            if (!activeNames.has(d.name)) {
                cachedScriptListData.push({
                    name: d.name,
                    isDraft: true,
                    date: new Date(d.mtime),
                    display: d.name
                });
            }
        });

        // 2. Registered Scripts
        prodFiles.forEach(f => {
            cachedScriptListData.push({
                name: f.name,
                isDraft: false,
                date: new Date(f.mtime),
                display: f.name
            });
        });

        // Sort: Drafts on Top, then by Date Descending
        cachedScriptListData.sort((a, b) => {
            if (a.isDraft !== b.isDraft) {
                return a.isDraft ? -1 : 1; // Draft comes first
            }
            return b.date - a.date;
        });

        renderScriptList(cachedScriptListData);

    } catch (e) {
        listContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #ef4444;">Error loading scripts</div>';
        console.error(e);
    }
}

function renderScriptList(items) {
    const listContainer = document.getElementById('scriptListContainer');
    listContainer.innerHTML = '';

    if (items.length === 0) {
        listContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b;">No scripts found.</div>';
        return;
    }

    items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'script-list-item'; // We adding styles for this? yes
        div.style = `
            padding: 12px; 
            border-bottom: 1px solid #334155; 
            cursor: pointer; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            transition: background 0.2s;
        `;
        div.onmouseover = function () { this.style.background = '#1e293b'; };
        div.onmouseout = function () { this.style.background = 'transparent'; };
        div.onclick = () => confirmLoadScript(item.name, item.isDraft);

        const icon = item.isDraft ? '📝' : '✅';
        const typeLabel = item.isDraft ? '<span style="font-size:0.75rem; background:#f59e0b; color:black; padding:2px 6px; border-radius:4px; margin-right:8px;">DRAFT</span>' : '';

        div.innerHTML = `
            <div>
                <div style="font-weight: 500; color: #e2e8f0; margin-bottom: 2px;">${icon} ${item.display}</div>
                <div style="font-size: 0.8rem; color: #94a3b8;">${item.date.toLocaleString()}</div>
            </div>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                 ${typeLabel}
                 <button title="Copy Script" onclick="event.stopPropagation(); loadScriptAsCopy('${item.name}', ${item.isDraft})" style="background:none; border:none; cursor:pointer; font-size:1.1rem;">📋</button>
            </div>
        `;
        listContainer.appendChild(div);
    });
}

function filterScriptList() {
    const query = document.getElementById('scriptSearch').value.toLowerCase();
    const filtered = cachedScriptListData.filter(item => item.name.toLowerCase().includes(query));
    renderScriptList(filtered);
}

async function confirmLoadScript(filename, isDraft) {
    // Determine the key for loadScriptByName
    const key = isDraft ? `DRAFT:${filename}` : filename;
    await loadScriptByName(key);
    closeLoadModal();
}

// --- Add Dependent Script Logic ---

function openAddScriptModal() {
    document.getElementById('addScriptModal').style.display = 'flex';
    fetchHelperScripts();
}

function closeAddScriptModal() {
    document.getElementById('addScriptModal').style.display = 'none';
}

async function fetchHelperScripts() {
    const listContainer = document.getElementById('helperScriptListContainer');
    listContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b;">Loading reusable scripts...</div>';

    try {
        // Reuse the main list API
        const res = await fetch('/api/scripts/custom');
        // Note: fetchScriptsList uses /api/scripts/list (metadata), but /api/scripts/custom gives registry content?
        // Let's check api.js. /api/scripts/custom returns registry content.
        // /api/scripts/list returns file stats. 
        // "isReusable" is in registry (scripts_registry.json), NOT in file stats.
        // So we MUST use /api/scripts/custom to filter by isReusable.

        const registry = await res.json();

        // Filter by isReusable: true
        const reusableScripts = registry.filter(s => s.isReusable === true);

        listContainer.innerHTML = '';
        if (reusableScripts.length === 0) {
            listContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b;">No reusable scripts found. Configured "isReusable": true in registry?</div>';
            return;
        }

        reusableScripts.forEach(script => {
            const div = document.createElement('div');
            div.style = `
                padding: 12px; 
                border-bottom: 1px solid #334155; 
                cursor: pointer; 
                display: flex; 
                flex-direction: column;
                transition: background 0.2s;
            `;
            div.onmouseover = function () { this.style.background = '#1e293b'; };
            div.onmouseout = function () { this.style.background = 'transparent'; };
            div.onclick = () => {
                addScriptStep(script.filename || script.name); // Prefer filename
                closeAddScriptModal();
            };

            div.innerHTML = `
                <div style="font-weight: 500; color: #e2e8f0; margin-bottom: 2px;">⚡ ${script.name}</div>
                <div style="font-size: 0.8rem; color: #94a3b8;">${script.description || 'No description'}</div>
            `;
            listContainer.appendChild(div);
        });

    } catch (e) {
        listContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #ef4444;">Error loading helper scripts</div>';
        console.error(e);
    }
}

function addScriptStep(scriptName) {
    addStep('SCRIPT');
    // The last added step is the one we want to configure
    const container = document.getElementById('stepsContainer');
    const row = container.lastElementChild;
    if (row && row.querySelector('.step-type').value === 'SCRIPT') {
        const input = row.querySelector('.step-script-name');
        if (input) {
            input.value = scriptName;
            input.disabled = true; // Lock it
        }
    }
}

// --- NEW helper to Repopulate Steps ---
function parseAndPopulateSteps(description) {
    try {
        const container = document.getElementById('stepsContainer');
        container.innerHTML = ''; // Clear existing
        stepCount = 0; // Reset counter

        // 1. Extract Global Columns
        const colMatch = description.match(/Excel Columns: (.*)/);
        if (colMatch) {
            document.getElementById('globalInputColumns').value = colMatch[1].trim();
        }

        // 2. Extract Output Mapping Configuration (Recover from Text)
        const configBlockMatch = description.match(/OUTPUT MAPPING CONFIGURATION:([\s\S]*?)(?=Step \d+|$)/); // Read until Steps start
        if (configBlockMatch) {
            const configText = configBlockMatch[1];

            // Clear Dynamic UI Rows first
            const uiContainer = document.getElementById('uiOutputRowsContainer');
            if (uiContainer) uiContainer.innerHTML = '';


            // NEW: UI Output Definition
            const uiBlockMatch = configText.match(/- UI Output Definition:([\s\S]*?)(?=- Excel|- Status|- General|IMPORTANT|$)/);
            if (uiBlockMatch) {
                const uiText = uiBlockMatch[1];
                const uiRowRegex = /- UI Column '(.*?)': Set to '(.*?)' \(Logic: ([\s\S]*?)\)/g;
                let match;
                while ((match = uiRowRegex.exec(uiText)) !== null) {
                    if (window.addUIOutputRow) {
                        window.addUIOutputRow({
                            colName: match[1],
                            value: match[2],
                            logic: match[3]
                        });
                    }
                }
            } else {
                // FALLBACK: Try Legacy Fixed fields (If text has them, map them to dynamic rows)
                const nameMatch = configText.match(/- UI 'Name' Column: Map from '(.*?)'(?:\. Logic: (.*))?/);
                if (nameMatch) {
                    window.addUIOutputRow({ colName: 'Name', value: nameMatch[1], logic: nameMatch[2] || "Default Logic" });
                }
                const codeMatch = configText.match(/- UI 'Code' Column: Map from '(.*?)'(?:\. Logic: (.*))?/);
                if (codeMatch) {
                    window.addUIOutputRow({ colName: 'Code', value: codeMatch[1], logic: codeMatch[2] || "HTTP Status" });
                }
                const respMatch = configText.match(/- UI 'Response' Column: Map from '(.*?)' to key 'API response'(?:\. Logic: (.*))?/);
                if (respMatch) {
                    window.addUIOutputRow({ colName: 'Response', value: respMatch[1], logic: respMatch[2] || "API Response" });
                }
            }



            // Instructions
            const instrMatch = configText.match(/- General Instructions: (.*)/);
            if (instrMatch && document.getElementById('modalOutputInstructions')) {
                document.getElementById('modalOutputInstructions').value = instrMatch[1].trim();
            }

            // Excel Rows
            const excelBlockMatch = configText.match(/- Excel Output Definition:([\s\S]*?)(?=IMPORTANT|$)/);
            if (excelBlockMatch) {
                const excelText = excelBlockMatch[1];
                // Regex for row: - Column 'col': Set to 'val' (Logic: logic)
                const rowRegex = /- Column '(.*?)': Set to '(.*?)' \(Logic: ([\s\S]*?)\)/g;
                let match;

                // Clear existing Excel first
                const excelContainer = document.getElementById('excelOutputRowsContainer');
                if (excelContainer) excelContainer.innerHTML = '';

                while ((match = rowRegex.exec(excelText)) !== null) {
                    if (window.addExcelOutputRow) {
                        window.addExcelOutputRow({
                            colName: match[1],
                            value: match[2],
                            logic: match[3]
                        });
                    }
                }
            }
        }

        // 3. Split into Blocks
        // Regex to match "Step X [TYPE]:"
        // Regex to match "Step X [TYPE]:" (tolerant to whitespace)
        // Regex to match "Step X [TYPE]:" (tolerant to whitespace inside/outside brackets)
        const stepRegex = /Step\s+\d+\s*\[\s*(.*?)\s*\]\s*:/g;

        // We need to capture the type and the content following it until the next step or end
        // Simplest strategy: Split by the regex, capturing the group (Type)
        const parts = description.split(stepRegex);
        // parts[0] = preamble
        // parts[1] = TYPE
        // parts[2] = BODY
        // ...

        for (let i = 1; i < parts.length; i += 2) {
            const type = parts[i];
            const body = parts[i + 1];

            addStep(type); // Create the UI Row
            const row = container.lastElementChild;

            if (type === 'API') {
                // Parse API Fields
                const nameM = body.match(/- Step\/Variable Name: (.*)/);
                if (nameM) row.querySelector('.step-api-name').value = nameM[1].trim();

                const callM = body.match(/- Call (\w+) (.*)/);
                if (callM) {
                    const method = callM[1].trim();
                    row.querySelector('.step-method').value = method;
                    row.querySelector('.step-endpoint').value = callM[2].trim();

                    // Trigger UI update for Method (hide/show payload)
                    updateStepUI(row.querySelector('.step-method'));
                }

                const payTypeM = body.match(/- Payload Type: (.*)/);
                if (payTypeM) row.querySelector('.step-payload-type').value = payTypeM[1].trim();

                const payM = body.match(/- Payload Example: (.*)/);
                if (payM) row.querySelector('.step-payload').value = payM[1].trim();

                const respM = body.match(/- Expected Response: (.*)/);
                if (respM) row.querySelector('.step-response').value = respM[1].trim();

                const instrM = body.match(/- Instructions: (.*)/);
                if (instrM) row.querySelector('.step-instruction').value = instrM[1].trim();

                // Parse Run Once
                if (body.includes("Run Once: Yes")) {
                    const runOnceBox = row.querySelector('.step-run-once');
                    if (runOnceBox) runOnceBox.checked = true;
                }

            } else if (type === 'LOGIC') {
                // Match logic until end of the block (supports multiline)
                const logicM = body.match(/- Logic: ([\s\S]*)/);
                if (logicM) row.querySelector('.step-logic').value = logicM[1].trim();

            } else if (type === 'GEO') {
                // Match Geo Location Logic
                // We generated it as: - Geo Location Logic: ${logic}
                const geoM = body.match(/- Geo Location Logic: ([\s\S]*?)(\n  - IMPORTANT:|$)/);
                // match until the mandatory text starts or end of block

                if (geoM) {
                    row.querySelector('.step-logic').value = geoM[1].trim();
                } else {
                    // Fallback if parsing fails (maybe old format or edited)
                    const simpleM = body.match(/- Geo Location Logic: ([\s\S]*)/);
                    if (simpleM) row.querySelector('.step-logic').value = simpleM[1].trim();
                }
            } else if (type === 'MASTER') {
                // Parse MASTER Step Fields
                const masterTypeM = body.match(/- Master Type: (.*)/);
                if (masterTypeM) {
                    const masterType = masterTypeM[1].trim();
                    row.querySelector('.step-master-type').value = masterType;

                    // Trigger the onchange event to populate run method
                    const selectElement = row.querySelector('.step-master-type');
                    if (selectElement && window.updateMasterTypeInfo) {
                        window.updateMasterTypeInfo(selectElement);
                    }
                }

                const inputColM = body.match(/- Input Column: (.*)/);
                if (inputColM) row.querySelector('.step-input-column').value = inputColM[1].trim();

                const outputColM = body.match(/- Output Column: (.*)/);
                if (outputColM) row.querySelector('.step-output-column').value = outputColM[1].trim();

                const lookupPathM = body.match(/- Lookup Path: (.*)/);
                if (lookupPathM) row.querySelector('.step-lookup-path').value = lookupPathM[1].trim();

                // Parse "On Failure" checkbox
                const onFailureM = body.match(/- On Failure: (.*)/);
                if (onFailureM) {
                    const failureAction = onFailureM[1].trim();
                    const skipCheckbox = row.querySelector('.step-skip-on-failure');
                    if (skipCheckbox) {
                        skipCheckbox.checked = failureAction.toLowerCase().includes('skip');
                    }
                }
            }
        }

    } catch (e) {
        console.error("Failed to parse description:", e);
        // Fallback: don't crash, just let user see empty steps
    }
}

// 1. Generate Script
// 1. Generate Script (Legacy)
async function generateScript() {
    // Keep for backward compat if needed, but our UI now uses generateScriptFromSteps
    return generateScriptFromSteps();
}

// --- Dynamic Steps Logic ---
let stepCount = 0;

function addStep(type) {
    stepCount++;
    const container = document.getElementById('stepsContainer');

    // Clear "No steps" message if first step
    if (container.children.length === 1 && container.children[0].innerText.includes('No steps')) {
        container.innerHTML = '';
    }

    const div = document.createElement('div');
    div.className = 'step-row';
    div.id = `step-${stepCount}`;
    div.id = `step-${stepCount}`;
    div.style = "background: rgba(30, 41, 59, 0.5); border: 1px solid #475569; padding: 10px; margin-bottom: 10px; border-radius: 4px; position: relative;";

    // Header Row with Remove and Move Buttons (Fixed type="button")
    let html = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px; align-items: center;">
            <strong style="color: ${type === 'API' ? '#38bdf8' : type === 'GEO' ? '#86efac' : type === 'MASTER' ? '#c084fc' : '#eab308'}">${type} Step</strong>
            <div style="display: flex; gap: 5px; align-items: center;">
                <button type="button" onclick="moveStepUp(this)" title="Move Up" style="background: rgba(255,255,255,0.05); border: 1px solid #475569; color: #94a3b8; cursor: pointer; border-radius: 4px; padding: 2px 6px; font-size: 0.8rem;">⬆️</button>
                <button type="button" onclick="moveStepDown(this)" title="Move Down" style="background: rgba(255,255,255,0.05); border: 1px solid #475569; color: #94a3b8; cursor: pointer; border-radius: 4px; padding: 2px 6px; font-size: 0.8rem;">⬇️</button>
                <button type="button" onclick="removeStep(${stepCount})" title="Remove" style="background: none; border: none; color: #ef4444; cursor: pointer; margin-left: 5px; font-size: 1rem;">✖</button>
            </div>
        </div>
        <input type="hidden" class="step-type" value="${type}">
    `;

    if (type === 'API') {
        html += `
            <div style="display: grid; grid-template-columns: 1fr 1fr 2fr; gap: 5px; margin-bottom: 5px;">
                <input type="text" class="step-api-name" placeholder="Name (e.g. create_farmer)" style="padding: 5px; background: #0f172a; color: #38bdf8; border: 1px solid #334155; font-weight: bold;">
                <select class="step-method" onchange="updateStepUI(this)" style="padding: 5px; background: #0f172a; color: white; border: 1px solid #334155;">
                    <option value="GET">GET</option>
                    <option value="POST" selected>POST</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                </select>
                <input type="text" class="step-endpoint" placeholder="/services/..." style="padding: 5px; background: #0f172a; color: white; border: 1px solid #334155;">
            </div>
            
            <div style="margin-bottom: 5px; display: flex; align-items: center;">
                 <label class="switch" style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" class="step-run-once">
                    <span style="font-size: 0.8rem; color: #c084fc; margin-left: 0.5rem;">⚡ Run Once (Master Data) - Fetch before row processing</span>
                </label>
            </div>

             <div class="payload-group" style="margin-bottom: 5px;">
                 <label style="font-size: 0.8rem; color: #94a3b8;">Payload Type</label>
                 <select class="step-payload-type" style="padding: 5px; background: #0f172a; color: white; border: 1px solid #334155;">
                    <option value="JSON" selected>JSON Body</option>
                    <option value="DTO_FILE">Multipart (DTO File)</option>
                    <option value="QUERY">Query Parameters</option>
                </select>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px;">
                <div class="payload-input-group" style="display: flex; flex-direction: column;">
                    <label class="payload-label" style="font-size: 0.75rem; color: #64748b; margin-bottom: 2px;">Payload (JSON)</label>
                    <textarea class="step-payload" rows="3" placeholder='{"key": "value"}' style="flex: 1; padding: 5px; background: #0f172a; color: #cbd5e1; border: 1px solid #334155; font-family: monospace; font-size: 0.8rem;"></textarea>
                </div>
                <div style="display: flex; flex-direction: column;">
                    <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 2px;">Expected Response (Optional)</label>
                    <textarea class="step-response" rows="5" placeholder='{"id": 123}' style="flex: 1; padding: 5px; background: #0f172a; color: #cbd5e1; border: 1px solid #334155; font-family: monospace; font-size: 0.8rem;"></textarea>
                </div>
            </div>
            <div style="margin-top: 5px;">
                 <label style="font-size: 0.75rem; color: #eab308; margin-bottom: 2px;">Step Instructions / Logic (What to do with this API?)</label>
                 <textarea class="step-instruction" rows="5" placeholder="e.g. Check if 'tags' attribute exists, if not fail the row..." style="width: 100%; padding: 5px; background: #0f172a; color: #fef08a; border: 1px solid #334155; font-size: 0.8rem;"></textarea>
            </div>
        `;
    } else if (type === 'SCRIPT') {
        html += `
            <div style="margin-bottom: 5px;">
                <label style="font-size: 0.8rem; color: #94a3b8;">Reusable Script Name</label>
                <input type="text" class="step-script-name" placeholder="Script Name" style="width: 100%; padding: 5px; background: #0f172a; color: #f59e0b; border: 1px solid #334155; font-weight: bold;" readonly>
            </div>
            <div style="margin-top: 5px;">
                 <label style="font-size: 0.75rem; color: #eab308; margin-bottom: 2px;">Step Instructions / Logic (What to do with this Script?)</label>
                 <textarea class="step-instruction" rows="5" placeholder="e.g. Use the output ID from previous step as input for this script..." style="width: 100%; padding: 5px; background: #0f172a; color: #fef08a; border: 1px solid #334155; font-size: 0.8rem;"></textarea>
            </div>
        `;
    } else if (type === 'GEO') {
        html += `
             <div style="margin-bottom: 5px;">
                 <label style="font-size: 0.8rem; color: #86efac;">Geofencing Requirement</label>
                 <textarea class="step-logic" rows="4" placeholder="e.g. Verify that the plot coordinates are within the village boundary..." style="width: 100%; padding: 5px; background: #0f172a; color: #bbf7d0; border: 1px solid #334155; font-size: 0.8rem;"></textarea>
                 <small style="color: #64748b; font-size: 0.75rem;">(AI will automatically use 'geofence_utils' component)</small>
            </div>
        `;
    } else if (type === 'MASTER') {
        html += `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 5px;">
                <div>
                    <label style="font-size: 0.8rem; color: #c084fc;">Master Type</label>
                    <select class="step-master-type" onchange="updateMasterTypeInfo(this)" style="width: 100%; padding: 5px; background: #0f172a; color: #c084fc; border: 1px solid #a855f7; font-weight: bold;">
                        <option value="">-- Select Master Type --</option>
                        <option value="user">User</option>
                        <option value="farmer">Farmer</option>
                        <option value="soiltype">Soil Type</option>
                        <option value="irrigationtype">Irrigation Type</option>
                        <option value="project">Project</option>
                        <option value="farmertag">Farmer Tag</option>
                        <option value="assettag">Asset Tag</option>
                        <option value="plottag">Plot Tag</option>
                    </select>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: #94a3b8;">Run Method</label>
                    <input type="text" class="step-run-method" readonly placeholder="Auto-detected" style="width: 100%; padding: 5px; background: #1e293b; color: #64748b; border: 1px solid #334155; font-style: italic;">
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 5px;">
                <div>
                    <label style="font-size: 0.8rem; color: #c084fc;">Input Column (Excel)</label>
                    <input type="text" class="step-input-column" placeholder="e.g. AssignedTo, Manager" style="width: 100%; padding: 5px; background: #0f172a; color: white; border: 1px solid #334155;">
                    <small style="color: #64748b; font-size: 0.7rem;">Column to read from Excel</small>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: #c084fc;">Output Column</label>
                    <input type="text" class="step-output-column" placeholder="e.g. AssignedTo_id" style="width: 100%; padding: 5px; background: #0f172a; color: white; border: 1px solid #334155;">
                    <small style="color: #64748b; font-size: 0.7rem;">Column to write result to</small>
                </div>
            </div>
            
            <div style="margin-bottom: 5px;">
                <label style="font-size: 0.8rem; color: #94a3b8;">Lookup Path (JSON)</label>
                <input type="text" class="step-lookup-path" placeholder="e.g. id, data.id, response[0].id" value="id" style="width: 100%; padding: 5px; background: #0f172a; color: white; border: 1px solid #334155;">
                <small style="color: #64748b; font-size: 0.7rem;">Path to extract from API response</small>
            </div>
            
            <div style="margin-top: 5px; padding: 8px; background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; border-radius: 4px;">
                <label style="display: flex; align-items: center; font-size: 0.75rem; color: #fca5a5;">
                    <input type="checkbox" class="step-skip-on-failure" checked style="margin-right: 5px;">
                    Skip row on lookup failure (recommended)
                </label>
            </div>
            
            <small style="color: #64748b; font-size: 0.75rem; margin-top: 5px; display: block;">(AI will automatically use 'master_search' component)</small>
        `;
    } else {
        html += `
            <textarea class="step-logic" rows="5" placeholder="Describe logic..." style="width: 100%; padding: 5px; background: #0f172a; color: white; border: 1px solid #334155;"></textarea>
        `;
    }

    div.innerHTML = html;
    container.appendChild(div);
}

function moveStepUp(btn) {
    const row = btn.closest('.step-row');
    if (row.previousElementSibling) {
        row.parentNode.insertBefore(row, row.previousElementSibling);
    }
}

function moveStepDown(btn) {
    const row = btn.closest('.step-row');
    if (row.nextElementSibling) {
        row.parentNode.insertBefore(row.nextElementSibling, row);
    }
}


function updateMasterTypeInfo(select) {
    const stepRow = select.closest('.step-row');
    const masterType = select.value;
    const runMethodInput = stepRow.querySelector('.step-run-method');
    const outputColumnInput = stepRow.querySelector('.step-output-column');
    const inputColumnInput = stepRow.querySelector('.step-input-column');

    // Master data config mapping (matches db.json)
    const masterConfig = {
        'user': { runMethod: 'search', suffix: '_id' },
        'farmer': { runMethod: 'search', suffix: '_id' },
        'soiltype': { runMethod: 'once', suffix: '_id' },
        'irrigationtype': { runMethod: 'once', suffix: '_id' },
        'project': { runMethod: 'once', suffix: '_id' },
        'farmertag': { runMethod: 'once', suffix: '_id' },
        'assettag': { runMethod: 'once', suffix: '_id' },
        'plottag': { runMethod: 'once', suffix: '_id' }
    };

    if (masterType && masterConfig[masterType]) {
        const config = masterConfig[masterType];
        if (runMethodInput) {
            runMethodInput.value = config.runMethod.toUpperCase();
        }

        // Auto-suggest output column based on input column
        if (inputColumnInput && outputColumnInput) {
            inputColumnInput.addEventListener('blur', function () {
                if (this.value && !outputColumnInput.value) {
                    outputColumnInput.value = this.value + config.suffix;
                }
            });
        }
    } else {
        if (runMethodInput) runMethodInput.value = '';
    }
}

function updateStepUI(select) {
    const stepRow = select.closest('.step-row');
    const method = select.value;
    const payloadGroup = stepRow.querySelector('.payload-group');
    const payloadType = stepRow.querySelector('.step-payload-type');
    const payloadLabel = stepRow.querySelector('.payload-label');
    const payloadInput = stepRow.querySelector('.step-payload');

    if (method === 'GET' || method === 'DELETE') {
        if (payloadGroup) payloadGroup.style.display = 'none';
        if (payloadType) payloadType.value = 'QUERY';
        if (payloadLabel) payloadLabel.innerText = "Query Parameters (e.g. ?id=1)";
        if (payloadInput) payloadInput.placeholder = "id=123&type=small";
    } else {
        if (payloadGroup) payloadGroup.style.display = 'block';
        if (payloadLabel) payloadLabel.innerText = "Payload (JSON)";
        if (payloadInput) payloadInput.placeholder = '{"key": "value"}';
    }
}

function removeStep(id) {
    const el = document.getElementById(`step-${id}`);
    if (el) el.remove();
}

async function generateScriptFromSteps() {
    // 1. Compile Steps into a Text Description for the AI
    const container = document.getElementById('stepsContainer');
    const steps = container.getElementsByClassName('step-row');
    const name = document.getElementById('scriptName').value;
    const globalCols = document.getElementById('globalInputColumns').value;

    if (!name) return alert("Script name is mandatory!");
    if (steps.length === 0) return alert("Please add at least one step.");

    const description = buildDescriptionFromSteps(name, globalCols, steps);




    // Save to window for Registration later
    window.lastGeneratedDescription = description;

    // 2. Send to Backend (Simulate "Generate Script")
    // UI Feedback
    const btn = document.querySelector('button[onclick="generateScriptFromSteps()"]');
    const originalText = btn.innerHTML;
    btn.innerHTML = "Generating... ⏳";
    btn.disabled = true;

    try {
        const res = await fetch('/api/scripts/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description: description,
                // If we have loaded code, send it for "Update Mode"
                // existing_code: document.getElementById('pythonCode').value, // DISABLE MERGE: Always regenerate fresh from steps
                scriptName: name,
                inputColumns: globalCols, // Persist manually entered columns
                isMultithreaded: document.getElementById('isMultithreaded') ? document.getElementById('isMultithreaded').checked : true,
                allowAdditionalAttributes: document.getElementById('allowAdditionalAttributes') ? document.getElementById('allowAdditionalAttributes').checked : false,
                enableGeofencing: document.getElementById('enableGeofencing') ? document.getElementById('enableGeofencing').checked : false,
                outputConfig: getOutputConfigFromUI() // explicit config for generator
            })
        });
        const data = await res.json();

        if (data.status === 'success') {
            document.getElementById('pythonCode').value = data.script;
            // Enable Proceed button immediately (Analysis optional)
            document.getElementById('proceedBtn').style.display = 'inline-block';
        } else {
            alert('Generation Failed: ' + data.message);
        }
    } catch (e) {
        alert('Error: ' + e.message);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// 2. Analyze Script
async function analyzeScript() {
    const code = document.getElementById('pythonCode').value;
    // ... same analysis logic ...
    const btn = document.querySelector('button[onclick="analyzeScript()"]');
    btn.innerHTML = "Analyzing... ⏳";
    btn.disabled = true;

    try {
        const res = await fetch('/api/scripts/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        renderAnalysis(data);

        // Show Proceed Button
        document.getElementById('proceedBtn').style.display = 'inline-block';
        // document.getElementById('analysisSection').style.opacity = '1'; // Removed
        // document.getElementById('analysisSection').style.pointerEvents = 'all'; // Removed

    } catch (e) {
        alert("Analysis Failed: " + e.message);
    } finally {
        btn.innerHTML = "Analyze Script ⚡";
        btn.disabled = false;
    }
}

function renderAnalysis(data) {
    const container = document.getElementById('analysisSteps');
    container.innerHTML = ''; // Clear

    if (data.workflowDescription) {
        data.workflowDescription.forEach(html => {
            const div = document.createElement('div');
            div.className = 'step-card';
            div.innerHTML = html;
            container.appendChild(div);
        });
    }

    detectedColumns = data.inputColumns || [];
    const colStr = detectedColumns.join(', ');
    document.getElementById('detectedColumnsDisplay').value = colStr;

    // UI Columns
    const uiCols = data.uiColumns || [];
    const uiColStr = uiCols.join(', ');
    if (document.getElementById('detectedUIColumnsDisplay')) {
        document.getElementById('detectedUIColumnsDisplay').value = uiColStr;
    }

    // manualColumns is now hidden, but we still set it as source of truth for downstream logic
    document.getElementById('manualColumns').value = colStr;

    // Auto-populate Group By if detected
    if (data.groupByColumn) {
        const groupInput = document.getElementById('groupByColumn');
        if (groupInput) {
            groupInput.value = data.groupByColumn;
            console.log("Auto-detected grouping by:", data.groupByColumn);
            // FORCE CHECK: If grouping is present, we Auto-Configure for "Group Mode"
            if (data.groupByColumn) {
                const mtCheckbox = document.getElementById('isMultithreaded');
                const batchInput = document.getElementById('threadSize'); // Corrected from batchSize to threadSize

                if (mtCheckbox) {
                    mtCheckbox.checked = true; // Default to Threaded
                    const mtLabel = mtCheckbox.nextElementSibling;
                    if (mtLabel) {
                        mtLabel.innerHTML = "Multithreading Enabled (Group Mode) 🚀";
                        mtLabel.style.color = "#10b981";
                    }
                    toggleThreadSize(mtCheckbox);
                }

                if (batchInput) {
                    // If the script itself didn't specify a batch size, or if it was the old default
                    // We suggest 1 (1 Group per Batch) as the safe default for Grouping.
                    if (!data.batchSize || data.batchSize > 50) {
                        batchInput.value = 1;
                    }
                }
            }
        }
    }

    // Auto-populate Threading Configs
    if (data.isMultithreaded !== undefined) {
        const mtCheckbox = document.getElementById('isMultithreaded');
        if (mtCheckbox) {
            mtCheckbox.checked = data.isMultithreaded;
            toggleThreadSize(mtCheckbox);
            console.log("Auto-detected threading:", data.isMultithreaded);
        }
    }

    if (data.batchSize) {
        const bsSelect = document.getElementById('threadSize');
        if (bsSelect) {
            // Ensure option exists or add it? For now assume standard options or set value
            // If value not in list, maybe add it temporary?
            // HTMLSelectElement.value sets it if exists.
            bsSelect.value = data.batchSize;

            // If custom value (e.g. 1000) not in dropdown, force it
            if (bsSelect.value != data.batchSize) {
                const opt = document.createElement('option');
                opt.value = data.batchSize;
                opt.text = data.batchSize;
                opt.selected = true;
                bsSelect.add(opt);
            }
        }
    }
}

// 3. Proceed to Test (Save Draft)
async function proceedToTest() {
    console.log("Proceeding...");
    // alert("Debug: Proceed clicked"); // Debugging click
    const code = document.getElementById('pythonCode').value;
    const name = document.getElementById('scriptName').value;

    if (!name) return alert("Script name is mandatory!");
    if (!code) return alert("Please provide Code");

    // Verify Columns
    const manualVal = document.getElementById('manualColumns').value;
    let finalCols = manualVal ? manualVal.split(',').map(s => s.trim()).filter(s => s) : detectedColumns;

    // SAFETY: Filter out UI Output columns from finalCols if they were accidentally included during analysis
    const outConfig = getOutputConfigFromUI();
    if (outConfig.uiMapping && outConfig.uiMapping.length > 0) {
        const uiOutputNames = new Set(outConfig.uiMapping.map(m => m.colName));
        finalCols = finalCols.filter(c => !uiOutputNames.has(c));
    }

    // CAPTURE CURRENT DESCRIPTION (Ensure Logic Steps are saved!)
    let currentDesc = window.lastGeneratedDescription || "Draft Script";
    const container = document.getElementById('stepsContainer');
    if (container.children.length > 0) {
        const steps = container.getElementsByClassName('step-row');
        // Rebuild description using helper
        currentDesc = buildDescriptionFromSteps(name, document.getElementById('globalInputColumns').value, steps);
        window.lastGeneratedDescription = currentDesc;
    }

    try {
        const res = await fetch('/api/scripts/save-draft', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code,
                name,
                team: window.currentTeam || "Unassigned", // Use preserved team
                description: document.getElementById('scriptDescription').value || "", // Human description
                generationPrompt: currentDesc, // Steps logic for AI
                inputColumns: finalCols,
                isMultithreaded: document.getElementById('isMultithreaded').checked,
                allowAdditionalAttributes: document.getElementById('allowAdditionalAttributes') ? document.getElementById('allowAdditionalAttributes').checked : false,
                additionalAttributes: (document.getElementById('allowAdditionalAttributes') && document.getElementById('allowAdditionalAttributes').checked)
                    ? (document.getElementById('testAttributes').value.split(',').map(s => s.trim()).filter(s => s))
                    : [],
                enableGeofencing: document.getElementById('enableGeofencing') ? document.getElementById('enableGeofencing').checked : false,
                targetLocation: document.getElementById('targetLocation') ? document.getElementById('targetLocation').value : "",
                batchSize: parseInt(document.getElementById('threadSize').value) || 10,
                groupByColumn: document.getElementById('groupByColumn').value,
                outputConfig: getOutputConfigFromUI(),
                status: 'draft',
                originalFilename: window.originalFilename
            })
        });
        const data = await res.json();

        if (data.success) {
            currentFilename = `${name}.py`;
            isDraftSaved = true;

            // Unlock Test Section
            document.getElementById('testSection').style.opacity = '1';
            document.getElementById('testSection').style.pointerEvents = 'all';

            // Lock Source Section mostly?
            // document.getElementById('pythonCode').disabled = true; 

            alert("Draft Saved! Please proceed to Test.");
        }
    } catch (e) {
        alert("Failed to save draft: " + e.message);
    }
}

// 4. Run Test (Debug Trace)
async function runTest() {
    if (!isDraftSaved) return alert("Please click 'Proceed to Test' first.");
    if (!authToken) return alert("Please Login first.");

    const fileInput = document.getElementById('testFile');
    if (!fileInput.files.length) return alert("Upload Excel file.");

    const timeline = document.getElementById('debugTimeline');
    timeline.innerHTML = '<div style="color:#fbbf24; text-align:center;">Running Debug Trace...</div>';

    const btn = document.querySelector('.action-btn-main');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = "Running... ⏳";
    }

    const targetLoc = document.getElementById('targetLocation') ? document.getElementById('targetLocation').value : '';

    try {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('filename', currentFilename);
        formData.append('env_config', JSON.stringify({
            ...window.lastEnvConfig,
            targetLocation: targetLoc
        }));

        // Ensure envConfig in JSON body also has it
        const finalEnvConfig = {
            environment: window.globalEnv || "QA2",
            apiBaseUrl: (envConfig.apiurl && envConfig.apiurl[window.globalEnv || "QA2"]) || "",
            targetLocation: targetLoc,
            batchSize: document.getElementById('threadSize') ? document.getElementById('threadSize').value : 1,
            allowAdditionalAttributes: document.getElementById('allowAdditionalAttributes') ? document.getElementById('allowAdditionalAttributes').checked : false,
            additionalAttributes: document.getElementById('useTestAttributes') && document.getElementById('useTestAttributes').checked ?
                document.getElementById('testAttributes').value.split(',').map(s => s.trim()).filter(s => s) : [],
            // Merge V2 Params if active
            ...(window.getAreaAuditV2Params ? window.getAreaAuditV2Params() : {})
        };
        const file = fileInput.files[0];
        const arrayBuffer = await file.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer);
        const rows = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]]);

        if (rows.length === 0) throw new Error("Excel empty");

        // CHECK ADDITIONAL ATTRIBUTES
        // Logic: The 'testAttributes' input defines columns. 
        // If 'Use Additional Attributes' is CHECKED -> We allow them (do nothing, they are in Excel).
        // If 'Use Additional Attributes' is UNCHECKED -> We should STRIP them if they exist in Excel, to ensure default behavior.

        const allowGlobal = document.getElementById('allowAdditionalAttributes').checked;
        const useRuntime = document.getElementById('useTestAttributes') && document.getElementById('useTestAttributes').checked;
        const attrInput = document.getElementById('testAttributes');

        if (allowGlobal && attrInput && attrInput.value.trim()) {
            const keysToManage = attrInput.value.split(',').map(s => s.trim()).filter(k => k);

            if (!useRuntime) {
                // STRIP mode: User has these columns defined but chose NOT to use them for this run.
                console.log("Stripping Additional Attributes (Runtime Disabled):", keysToManage);
                rows.forEach(row => {
                    keysToManage.forEach(k => {
                        delete row[k];
                    });
                });
            } else {
                console.log("Allowing Additional Attributes (Runtime Enabled):", keysToManage);
                // Pass through
            }
        }

        // Only run first 5 rows for debug to avoid chaos?
        // No, user wants threading check.

        console.log("Starting Test Run Payload Prep...");

        try {
            console.log("Stringifying payload...");
            const payload = JSON.stringify({
                code: document.getElementById('pythonCode').value,
                rows: rows,
                token: authToken,
                envConfig: finalEnvConfig,
                columns: document.getElementById('manualColumns').value.split(',').map(s => s.trim()).filter(s => s)
            });
            console.log("Payload size:", payload.length);
        } catch (jsonErr) {
            console.error("JSON Stringify Failed:", jsonErr);
            alert("Critical Error: Failed to prepare data. " + jsonErr.message);
            return;
        }

        const res = await fetch('/api/scripts/test-run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code: document.getElementById('pythonCode').value, // Send code again or filename? Using Code for immediate update
                rows: rows,
                token: authToken,
                envConfig: finalEnvConfig,
                columns: document.getElementById('manualColumns').value.split(',').map(s => s.trim()).filter(s => s)
            })
        });

        console.log("Fetch completed, status:", res.status);
        const result = await res.json();
        console.log("JSON parsed, result keys:", Object.keys(result));

        // CHECK FOR ERROR
        if (!res.ok || result.error) {
            console.error("Test Run Failed:", result);
            const errorMsg = `❌ EXECUTION FAILED ❌\nError: ${result.error}\n\n=== STDERR (Traceback) ===\n${result.details || "No details provided"}\n\n=== STDOUT ===\n`;

            // Append explicit error details to logs so they show in timeline
            result.logs = errorMsg + (result.logs || "");

            // Alert user with full error - REMOVED for better UX (logs are available)
            // alert(`EXECUTION FAILED\n\nError: ${result.error}\n\nDetails (Stderr):\n${result.details || 'No details'}\n\nLogs (Stdout):\n${result.logs ? result.logs.substring(0, 500) : 'No logs'}`);
        }

        // PARSE LOGS FOR TIMELINE
        let rawLogs = result.logs || result.rawOutput || "";

        // CHECK FOR DATA DUMP
        const dumpRegex = /\[OUTPUT_DATA_DUMP\]([\s\S]*?)\[\/OUTPUT_DATA_DUMP\]/;
        const match = rawLogs.match(dumpRegex);

        if (match) {
            try {
                lastOutputData = JSON.parse(match[1]);
                document.getElementById('downloadOutputBtn').style.display = 'inline-block';
                // Remove dump from logs for cleaner display
                rawLogs = rawLogs.replace(match[0], '');

                // RENDER MOCK RESULTS
                renderMockResults(lastOutputData);
            } catch (e) {
                console.error("Failed to parse output dump", e);
            }
        } else {
            document.getElementById('downloadOutputBtn').style.display = 'none';
            document.getElementById('mockResultSection').style.display = 'none'; // Hide if no data
        }

        window.lastExecutionLogs = rawLogs;
        console.log("About to render timeline, logs length:", rawLogs.length);
        renderTimeline(window.lastExecutionLogs);
        console.log("Timeline rendered successfully");

    } catch (e) {
        window.lastExecutionLogs = `Critical Error: ${e.message}\nStack: ${e.stack}`;
        timeline.innerHTML = `<div style="color:red;">Error: ${e.message}</div>`;
    } finally {
        const btn = document.querySelector('.action-btn-main');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = "Run Debug Trace 🐞";
        }
    }
}

function renderTimeline(logs) {
    const timeline = document.getElementById('debugTimeline');
    timeline.innerHTML = '';

    // CRITICAL FIX: Truncate massive logs to prevent browser freeze
    const MAX_LOG_LENGTH = 1048576; // 1MB max display (Increased from 50KB)
    let displayLogs = logs;
    let wasTruncated = false;

    if (logs.length > MAX_LOG_LENGTH) {
        wasTruncated = true;
        // Show last 1MB (most recent logs)
        displayLogs = logs.substring(logs.length - MAX_LOG_LENGTH);
    }

    // Create Pre Element for raw logs
    const pre = document.createElement('div');
    pre.style.fontFamily = "monospace";
    pre.style.whiteSpace = "pre-wrap";
    pre.style.fontSize = "0.85rem";
    pre.style.color = "#e2e8f0";

    if (wasTruncated) {
        const warning = document.createElement('div');
        warning.style.background = "#fbbf24";
        warning.style.color = "#000";
        warning.style.padding = "10px";
        warning.style.marginBottom = "10px";
        warning.style.borderRadius = "4px";
        warning.innerHTML = `⚠️ <strong>Logs Truncated</strong>: Original size was ${logs.length.toLocaleString()} characters. Showing last ${MAX_LOG_LENGTH.toLocaleString()} characters. Full logs are still available in browser memory (window.lastExecutionLogs).`;
        timeline.appendChild(warning);
    }

    pre.innerText = displayLogs;
    timeline.appendChild(pre);

    // CRITICAL FIX: Return early to prevent browser freeze
    // The line-by-line processing below creates thousands of DOM elements which freezes the browser
    console.log("Timeline rendered successfully");
    return;

    // === CODE BELOW IS DISABLED TO PREVENT BROWSER FREEZE ===
    // If we want mixed mode (Timeline + Raw), we can append raw below or toggle.
    // User asked for "actual request, response API calls output", so raw logs are best.

    const lines = logs.split('\n');
    let events = [];

    // Regex Parsers
    // [TRACE_DATA_READ] [Row 0] Key: Name | Value: John
    // [TRACE_API_REQ] Method: POST | URL: ...
    // [DEBUG_STEP] URL: ...
    const rgxData = /\[TRACE_DATA_READ\] \[Row (\d+)\] Key: (.*?) \| Found: .*? \| Value: (.*)/;
    const rgxDebug = /\[DEBUG_STEP\] (.*)/;

    let lastDiv = null;

    lines.forEach(line => {
        let div = document.createElement('div');
        div.style.marginBottom = "5px";
        div.style.padding = "5px";
        div.style.borderRadius = "4px";
        div.style.fontSize = "0.85rem";
        let isTagged = false;

        if (line.includes('[TRACE_DATA_READ]')) {
            div.style.background = "rgba(16, 185, 129, 0.1)";
            div.style.borderLeft = "3px solid #10b981";
            div.innerText = line;
            isTagged = true;
        }
        else if (line.includes('[API_DEBUG]')) {
            div.style.background = "#f1f5f9"; // Slate 100
            div.style.borderLeft = "3px solid #64748b"; // Slate 500
            div.style.fontFamily = "monospace";
            div.style.whiteSpace = "pre-wrap";
            div.style.color = "#334155";
            div.innerText = line.replace('[API_DEBUG]', '').trim();
            isTagged = true;
        }
        else if (line.includes('[DEBUG_STEP]')) {
            // Fallback for older logs
            div.style.background = "rgba(59, 130, 246, 0.1)";
            div.style.borderLeft = "3px solid #3b82f6";
            div.innerText = line.replace('[DEBUG_STEP]', '🐞 DEBUG:');
            isTagged = true;
        }
        else if (line.includes('[TRACE_ERR]') || line.includes('[FAIL]')) {
            div.style.background = "rgba(239, 68, 68, 0.1)";
            div.style.borderLeft = "3px solid #ef4444";
            div.style.color = "#fca5a5";
            div.innerText = line;
            isTagged = true;
        }

        if (isTagged) {
            timeline.appendChild(div);
            lastDiv = div;
        } else {
            // Continuation of previous block (e.g. JSON body)
            if (lastDiv) {
                lastDiv.innerText += "\n" + line;
            } else {
                // Orphan line (start of log without tag?)
                div.style.color = "#94a3b8";
                div.innerText = line;
                timeline.appendChild(div);
                lastDiv = div;
            }
        }
    });

    if (timeline.children.length === 0) {
        timeline.innerHTML = '<div style="color: grey; text-align: center; padding: 10px;">No specific trace events captured.<br>Check Logs via "Copy Logs" button.</div>';
    }
}

function copyTraceLogs() {
    if (!window.lastExecutionLogs || window.lastExecutionLogs.length === 0) {
        return alert("No logs recorded. Please run a test first.");
    }

    navigator.clipboard.writeText(window.lastExecutionLogs).then(() => {
        alert(`Copied ${window.lastExecutionLogs.length} chars to clipboard! 📋`);
    }).catch(err => {
        alert("Failed to copy logs: " + err);
    });
}

// 5. Discard / Import
async function discardScript() {
    if (!currentFilename) return;
    if (!confirm("Discard this draft? This will delete the file.")) return;

    await fetch('/api/scripts/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: currentFilename })
    });

    location.reload(); // Reset
}

function buildDescriptionFromSteps(name, globalCols, steps) {
    let description = `Script Name: ${name}\n`;
    if (globalCols) description += `Excel Columns: ${globalCols}\n\n`;

    // --- Output Configuration Injection (Modal) ---
    const outName = document.getElementById('modalOutputName') ? document.getElementById('modalOutputName').value : '';
    const outNameLogic = document.getElementById('modalOutputNameLogic') ? document.getElementById('modalOutputNameLogic').value : '';
    const outCode = document.getElementById('modalOutputCode') ? document.getElementById('modalOutputCode').value : '';
    const outCodeLogic = document.getElementById('modalOutputCodeLogic') ? document.getElementById('modalOutputCodeLogic').value : '';
    const outResp = document.getElementById('modalOutputResponse') ? document.getElementById('modalOutputResponse').value : '';
    const outRespLogic = document.getElementById('modalOutputResponseLogic') ? document.getElementById('modalOutputResponseLogic').value : '';
    const outInstr = document.getElementById('modalOutputInstructions') ? document.getElementById('modalOutputInstructions').value : '';



    // Excel Rows
    const excelRows = [];
    const eRows = document.querySelectorAll('#excelOutputRowsContainer .excel-row');
    eRows.forEach(r => {
        const c = r.querySelector('.excel-col-name').value;
        const v = r.querySelector('.excel-col-val').value;
        const l = r.querySelector('.excel-col-logic').value;
        if (c) excelRows.push(`   - Column '${c}': Set to '${v}' (Logic: ${l})`);
    });

    const outConfig = getOutputConfigFromUI(); // Get the full output config

    if (outConfig.uiMapping && outConfig.uiMapping.length > 0) {
        description += `OUTPUT MAPPING CONFIGURATION:\n`;
        description += `- UI Output Definition:\n`;
        description += outConfig.uiMapping.map(m => `- UI Column '${m.colName}': Set to '${m.value}' (Logic: ${m.logic})`).join('\n');
        description += `\n`;
    } else {
        // Legacy or Default support if needed, or just skip
    }

    if (excelRows.length > 0) {
        if (!description.includes('OUTPUT MAPPING CONFIGURATION:')) description += `OUTPUT MAPPING CONFIGURATION:\n`;
        description += `- Excel Output Definition:\n${excelRows.join('\n')}\n`;
    }


    if (outConfig.aiInstructions) {
        if (!description.includes('OUTPUT MAPPING CONFIGURATION:')) description += `OUTPUT MAPPING CONFIGURATION:\n`;
        description += `- General Instructions: ${outConfig.aiInstructions}\n`;
    }

    if (description.includes('OUTPUT MAPPING CONFIGURATION:')) {
        description += `IMPORTANT: Include this configuration as a comment block at the top of the generated Python script for reference.\n\n`;
    }
    // --------------------------------------

    // Master Config Definition (Local copy for generation logic)
    const masterConfig = {
        'user': { runMethod: 'search', suffix: '_id' },
        'farmer': { runMethod: 'search', suffix: '_id' },
        'soiltype': { runMethod: 'once', suffix: '_id' },
        'irrigationtype': { runMethod: 'once', suffix: '_id' },
        'project': { runMethod: 'once', suffix: '_id' },
        'farmertag': { runMethod: 'once', suffix: '_id' },
        'assettag': { runMethod: 'once', suffix: '_id' }
    };

    Array.from(steps).forEach((step, index) => {
        const type = step.querySelector('.step-type').value;
        description += `Step ${index + 1} [${type}]:\n`;

        if (type === 'API') {
            const apiName = step.querySelector('.step-api-name').value || `api_step_${index + 1}`;
            const method = step.querySelector('.step-method').value;
            const endpoint = step.querySelector('.step-endpoint').value;
            const payloadType = step.querySelector('.step-payload-type').value;
            let payload = step.querySelector('.step-payload').value;
            const response = step.querySelector('.step-response').value;
            const instruction = step.querySelector('.step-instruction').value;

            // New: Run Once Flag
            const isRunOnceEl = step.querySelector('.step-run-once');
            const isRunOnce = isRunOnceEl ? isRunOnceEl.checked : false;

            // FIX: Auto-extract query parameters from endpoint for QUERY type payloads
            // This ensures ALL parameters (like size=5000) are included in the generation prompt
            if (payloadType === 'QUERY' && endpoint && endpoint.includes('?')) {
                const [basePath, queryString] = endpoint.split('?');
                const params = new URLSearchParams(queryString);
                const paramsObj = {};
                params.forEach((value, key) => {
                    paramsObj[key] = value;
                });

                // If user didn't provide a payload example, auto-generate from query params
                if (!payload || payload.trim() === '') {
                    payload = JSON.stringify(paramsObj);
                } else {
                    // If user provided partial payload, merge with extracted params
                    try {
                        const userPayload = JSON.parse(payload);
                        const mergedPayload = { ...paramsObj, ...userPayload };
                        payload = JSON.stringify(mergedPayload);
                    } catch (e) {
                        // If payload is not valid JSON, use extracted params
                        payload = JSON.stringify(paramsObj);
                    }
                }
            }

            description += `  - Step/Variable Name: ${apiName}\n`;
            description += `  - Call ${method} ${endpoint}\n`;
            if (isRunOnce) {
                description += `  - Run Once: Yes (Master Data / Setup Step)\n`;
            }
            description += `  - Payload Type: ${payloadType}\n`;
            if (payload) description += `  - Payload Example: ${payload.replace(/\n/g, '')}\n`;
            if (response) description += `  - Expected Response: ${response.replace(/\n/g, '')}\n`;
            if (instruction) description += `  - Instructions: ${instruction.replace(/\n/g, ' ')}\n`;
        } else if (type === 'SCRIPT') {
            const scriptName = step.querySelector('.step-script-name').value;
            const instruction = step.querySelector('.step-instruction').value;
            description += `  - Execute Script: ${scriptName}\n`;
            if (instruction) description += `  - Instructions: ${instruction.replace(/\n/g, ' ')}\n`;
        } else if (type === 'GEO') {
            const logic = step.querySelector('.step-logic').value;
            description += `  - Geo Location Logic: ${logic}\n`;
            description += `  - IMPORTANT: You MUST import and use 'components.geofence_utils' for this step.\n`;
            description += `  - Usage: boundary_data = geofence_utils.get_boundary(location_name, env_config.get('google_api_key'))\n`;
            description += `  - CRITICAL: 'boundary_data' IS the direct result object. It is NOT wrapped in 'google_response' or 'data'.\n`;
            description += `  - 'boundary_data' structure: { "formatted_address": "...", "geometry": { "location": {...}, "viewport": {...}, "bounds": {...} }, "place_id": "...", "address_components": [...], "geojson_polygon": {...} }\n`;
            description += `  - NOTE: 'geojson_polygon' is ALREADY a FeatureCollection. DO NOT wrap it in another FeatureCollection or check for 'Polygon' type.\n`;
            description += `  - CRITICAL: When mapping 'bounds' and 'geoInfo', ALWAYS prioritize 'geometry.bounds' over 'geometry.viewport' if available, as 'bounds' is the strict geopolitical boundary.\n`;
            description += `  - CRITICAL: The final Output column MUST be a JSON string. Use 'json.dumps(output_payload)' to populate the row.\n`;
            description += `  - YOU MUST PARSE 'boundary_data' directly to extract fields required by the logic (e.g. boundary_data['formatted_address'], boundary_data['geometry']['location']).\n`;
        } else if (type === 'MASTER') {
            const masterType = step.querySelector('.step-master-type').value;
            const inputColumn = step.querySelector('.step-input-column').value;
            const outputColumn = step.querySelector('.step-output-column').value;
            const lookupPath = step.querySelector('.step-lookup-path').value || 'id';
            const skipOnFailure = step.querySelector('.step-skip-on-failure') ? step.querySelector('.step-skip-on-failure').checked : true;

            const config = masterConfig[masterType] || {};
            const runMethod = config.runMethod || 'search';

            description += `  - Master Type: ${masterType}\n`;
            description += `  - Input Column: ${inputColumn}\n`;
            description += `  - Output Column: ${outputColumn}\n`;
            description += `  - Lookup Path: ${lookupPath}\n`;
            description += `  - On Failure: ${skipOnFailure ? 'Skip Row' : 'Continue'}\n`;
            description += `  - Run Method: ${runMethod}\n`;
            description += `  - IMPORTANT: You MUST import and use 'components.master_search' for this step.\n`;

            if (runMethod === 'once') {
                description += `  - CRITICAL OPTIMIZATION: This master type is configured as 'Run Once'.\n`;
                description += `  - 1. use 'master_search.fetch_all("${masterType}", env_config)' OUTSIDE the loop to get all items.\n`;
                description += `  - 2. use 'master_search.lookup_from_cache(cache_data, "name", input_value, "${lookupPath}")' INSIDE the loop.\n`;
                description += `  - 3. Do NOT use 'master_search.search()' inside the loop for this type.\n`;
            } else {
                description += `  - The master_data_config is available in env_config, so master_search will auto-detect run_method (usually 'search').\n`;
            }
        } else {
            const logic = step.querySelector('.step-logic').value;
            description += `  - Logic: ${logic}\n`;
        }
        description += '\n';
    });
    return description;
}

async function importScript() {
    if (!currentFilename) return;
    const comment = document.getElementById('reviewComments').value;

    // Construct generation prompt from current steps if possible, or use loaded one
    let currentPrompt = "";

    // Quick rebuild of description for saving
    const container = document.getElementById('stepsContainer');
    if (container.children.length > 0) {
        const steps = container.getElementsByClassName('step-row');
        const name = document.getElementById('scriptName').value;
        const globalCols = document.getElementById('globalInputColumns').value;

        currentPrompt = buildDescriptionFromSteps(name, globalCols, steps);

        // Update global var too just in case
        window.lastGeneratedDescription = currentPrompt;
    } else {
        // Fallback to what we loaded initially if no steps were rendered/modified
        currentPrompt = window.lastGeneratedDescription || "";
    }

    // Capture Columns (Priority: User Edited Global > Manual > Detected)
    const manualVal = document.getElementById('manualColumns').value;
    const detectedVal = document.getElementById('detectedColumnsDisplay').value;
    const globalVal = document.getElementById('globalInputColumns').value;

    let finalColsStr = globalVal || manualVal || detectedVal || "";
    let inputColumns = [];

    // SAFETY: Filter out UI Output columns from registration if they were accidentally included
    const outMapping = getOutputConfigFromUI();
    const uiOutputNames = new Set(outMapping.uiMapping ? outMapping.uiMapping.map(m => m.colName) : []);
    const excelOutputNames = new Set(outMapping.excelMapping ? outMapping.excelMapping.map(m => m.colName) : []);

    if (finalColsStr) {
        inputColumns = finalColsStr.split(',')
            .map(s => s.trim())
            .filter(s => s && !uiOutputNames.has(s) && !excelOutputNames.has(s))
            .map(c => ({
                name: c,
                type: "Mandatory",
                description: "Auto-detected"
            }));
    }

    await fetch('/api/scripts/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            code: document.getElementById('pythonCode').value,
            name: currentFilename.replace('.py', ''),
            team: "Unassigned",
            // Use the new input field, fallback to static default
            description: document.getElementById('scriptDescription').value || "User Script",
            generationPrompt: window.lastGeneratedDescription || window.loadedGenerationPrompt || "",
            inputColumns: inputColumns, // Send captured columns
            comments: comment,
            // Pass configs
            isMultithreaded: document.getElementById('isMultithreaded').checked,
            allowAdditionalAttributes: document.getElementById('allowAdditionalAttributes') ? document.getElementById('allowAdditionalAttributes').checked : false,
            // Capture the list of attributes
            additionalAttributes: (document.getElementById('allowAdditionalAttributes') && document.getElementById('allowAdditionalAttributes').checked)
                ? (document.getElementById('testAttributes').value.split(',').map(s => s.trim()).filter(s => s))
                : [],
            enableGeofencing: document.getElementById('enableGeofencing') ? document.getElementById('enableGeofencing').checked : false,
            groupByColumn: document.getElementById('groupByColumn').value,
            batchSize: document.getElementById('threadSize').value,
            outputConfig: getOutputConfigFromUI()
        })
    });

    alert("Script Registered Successfully! 🎉");

    // Refresh definitions in script.js so columns are updated immediately
    if (typeof loadCustomScripts === 'function') {
        console.log("Refreshing Custom Scripts Definitions...");
        loadCustomScripts();
    }
    location.reload();
}

// Helper to flatten nested JSON
function flattenObject(obj, prefix = '', res = {}) {
    for (const key in obj) {
        if (!obj.hasOwnProperty(key)) continue;
        const val = obj[key];
        const newKey = prefix ? `${prefix}_${key}` : key;
        if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
            flattenObject(val, newKey, res);
        } else {
            res[newKey] = val;
        }
    }
    return res;
}

function downloadTestOutput() {
    if (!lastOutputData) return alert("No output data available.");

    // Flatten data for better Excel compatibility
    const flatData = lastOutputData.map(row => {
        const flat = flattenObject(row);
        // Remove internal 'row' index if present to avoid duplicate/confusing columns
        delete flat['row'];
        return flat;
    });

    const ws = XLSX.utils.json_to_sheet(flatData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Output");
    XLSX.writeFile(wb, "Test_Output.xlsx");
}

// --- Helpers (Fetch Config etc) copied from previous ---
async function fetchEnvConfig() {
    // ... existing fetchEnvConfig ...
    try {
        const res = await fetch('/api/env-urls');
        const data = await res.json();
        envConfig = { apiurl: data.environment_api_urls, selectedEnvironment: userEnv };
        const envSelect = document.getElementById('loginEnv');
        if (envSelect) {
            envSelect.innerHTML = '';
            Object.keys(envConfig.apiurl).forEach(env => {
                const option = document.createElement('option');
                option.value = env;
                option.textContent = env;
                if (env === userEnv) option.selected = true;
                envSelect.appendChild(option);
            });
        }
    } catch (e) { }
}

// Initialize Login Component on Load
// Initialize Login Component on Load
// Initialize Login Component on Load
document.addEventListener("DOMContentLoaded", () => {
    // FIX: Clear Session to ensure fresh start on reload (User Request)
    localStorage.removeItem('authToken');
    localStorage.removeItem('username');
    localStorage.removeItem('tenant');
    localStorage.removeItem('selectedEnvironment');
    authToken = null;

    const savedToken = null;
    const savedUser = null;
    const savedTenant = null;
    const savedEnv = null;

    // Validate Session Data
    let initialState = null;
    /* USER REQUESTED TO DISABLE AUTO-LOGIN RESTORE
    if (savedToken && savedUser) {
        initialState = {
            username: savedUser,
            environment: savedEnv || '',
            tenant: savedTenant || '',
            access_token: savedToken // Pass token for validation
        };
        // Restore global env
        if (savedEnv) window.globalEnv = savedEnv;
    } else {
        // Partial/Legacy session detected (Token exists but no User details)
        // Force logout to ensure clean state
        if (savedToken) {
            localStorage.removeItem('authToken');
            localStorage.removeItem('username');
            localStorage.removeItem('tenant');
        }
    }
    */

    new LoginComponent("login-container", {
        initialState: initialState,
        apiEndpoint: customBaseUrl ? `${customBaseUrl}/api/user-aggregate/token` : '/api/user-aggregate/token',
        onLoginSuccess: (token, userDetails) => {
            authToken = token;
            localStorage.setItem('authToken', token);
            localStorage.setItem('username', userDetails.username);
            localStorage.setItem('tenant', userDetails.tenant);
            localStorage.setItem('selectedEnvironment', userDetails.environment);

            window.globalEnv = userDetails.environment;
        },
        onLogout: () => {
            authToken = null;
            localStorage.removeItem('authToken');
            // We can keep username/tenant for convenience or clear them? 
            // Better clear to avoid confusion.
            localStorage.removeItem('username');
            localStorage.removeItem('tenant');
            // localStorage.removeItem('selectedEnvironment'); // Keep env preference?
            window.globalEnv = null;
        }
    });
});


function downloadTemplate() {
    // Start Analysis Animation? No, just download based on detected/manual columns
    const manualVal = document.getElementById('manualColumns').value;
    const globalVal = document.getElementById('globalInputColumns').value;
    const attrInput = document.getElementById('testAttributes');

    let finalCols = [];

    // Priority 1: User Edited/Global Input directly (The comma separated field)
    if (globalVal && globalVal.trim()) {
        finalCols = globalVal.split(',').map(s => s.trim()).filter(s => s);
    }
    // Priority 2: Manual / Detected Fallback (Old Logic)
    else {
        finalCols = manualVal ? manualVal.split(',').map(s => s.trim()).filter(s => s) : [...detectedColumns];
    }

    // Append Custom Attributes to Columns
    if (document.getElementById('allowAdditionalAttributes').checked && attrInput && attrInput.value.trim()) {
        const parts = attrInput.value.split(',').map(s => s.trim()).filter(s => s);
        parts.forEach(p => {
            const key = p.split('=')[0].trim();
            if (key && !finalCols.includes(key)) finalCols.push(key);
        });
    }

    // Fallback to globalInputColumns if still empty (e.g. loaded script but didn't run analysis)
    if ((!finalCols || finalCols.length === 0) && globalVal) {
        finalCols = globalVal.split(',').map(s => s.trim()).filter(s => s);
    }

    if (!finalCols || finalCols.length === 0) {
        alert("No columns detected or entered. Please enter column names manually.");
        return;
    }
    const ws = XLSX.utils.json_to_sheet([], { header: finalCols });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Template");
    const name = document.getElementById('scriptName').value || "Template";
    XLSX.writeFile(wb, `${name}_Template.xlsx`);
}

function copyLogs() {
    const logs = document.getElementById('debugTimeline').innerText; // Copy Debug timeline text
    navigator.clipboard.writeText(logs);
}

// 6. Save Feedback Context for AI
async function saveFeedbackContext() {
    const btn = document.getElementById('aiUpdateBtn');
    const code = document.getElementById('pythonCode').value;
    const comments = document.getElementById('reviewComments').value;
    const logs = window.lastExecutionLogs || "No logs available";
    const scriptName = document.getElementById('scriptName').value;

    if (!comments) return alert("Please add some comments explaining what to update.");

    const originalText = btn.innerText;
    btn.innerText = "Sending...";
    btn.disabled = true;

    try {
        const res = await fetch('/api/scripts/save-feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scriptName,
                code,
                comments,
                logs,
                timestamp: new Date().toISOString()
            })
        });
        const data = await res.json();
        if (data.success) {
            alert("Context Sent to AI! 🤖\nPlease return to the chat to continue.");
        } else {
            alert("Failed to send context: " + data.error);
        }
    } catch (e) {
        alert("Error sending context: " + e.message);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

// --- Code Editor Modal Logic ---
// --- Code Editor Modal Logic ---
window.openCodeModal = function () {
    const code = document.getElementById('pythonCode').value;
    const editor = document.getElementById('modalCodeEditor');
    editor.value = code;
    editor.readOnly = true; // Read Only
    editor.style.background = "#0f172a"; // Darker background to indicate readonly

    // UI Adjustments for "View Only" mode
    document.querySelector('#codeModal h3').innerText = "Python Script Viewer";
    // Hide Save Button
    const saveBtn = document.querySelector('#codeModal .btn-primary');
    if (saveBtn) saveBtn.style.display = 'none';
    // Rename Cancel to Close
    const closeBtn = document.querySelector('#codeModal .btn-secondary');
    if (closeBtn) closeBtn.innerText = "Close";

    document.getElementById('codeModal').style.display = 'flex';
}

window.closeCodeModal = function () {
    document.getElementById('codeModal').style.display = 'none';
}

// saveCodeModal is effectively disabled/hidden, but kept for reference if we revert
window.saveCodeModal = function () {
    // Disabled
    closeCodeModal();
}

// --- Output Config Modal Logic ---
window.openOutputConfigModal = function () {
    document.getElementById('outputConfigModal').style.display = 'flex';

    // Populate Datalist
    const globalVal = document.getElementById('globalInputColumns').value;
    // const manualVal = document.getElementById('manualColumns').value; // REMOVED: potentially stale
    const list = document.getElementById('inputColumnsList');
    list.innerHTML = ""; // Clear

    const allCols = new Set();
    if (globalVal) globalVal.split(',').forEach(s => allCols.add(s.trim()));
    // if (manualVal) manualVal.split(',').forEach(s => allCols.add(s.trim())); // REMOVED

    allCols.forEach(col => {
        if (col) {
            const opt = document.createElement('option');
            opt.value = col;
            list.appendChild(opt);
        }
    });

    // Reset/Check UI Rows
    // If we want to persist between opens WITHOUT parsing steps, we should leave it alone?
    // But if steps were cleared, this might be stale.
    // Ideally, the modal reflects the Current Steps' config.
    // Since we don't have "state" other than the DOM, we assume the DOM is the state.
    // However, if we just opened it, maybe we should check if empty?
    const container = document.getElementById('uiOutputRowsContainer');
    const rows = container.getElementsByClassName('ui-output-row');
    const msg = document.getElementById('noUiRowsMsg');

    // Logic: If user opens modal, they expect to see what they configured.
    // If they haven't configured anything, it might be empty (or matching generated steps).
    // We do NOT clear it here, because getOutputConfigFromUI reads from HERE.
    // If we clear it, we lose the config.

    if (rows.length === 0) {
        if (msg) msg.style.display = 'block';
    } else {
        if (msg) msg.style.display = 'none';
    }
}

window.closeOutputConfigModal = function () {
    document.getElementById('outputConfigModal').style.display = 'none';
}

window.switchOutputTab = function (tab) {
    // Hide all
    document.getElementById('tabContent-ui').style.display = 'none';
    document.getElementById('tabContent-excel').style.display = 'none';

    document.getElementById('tabBtn-ui').style.borderBottomColor = 'transparent';
    document.getElementById('tabBtn-excel').style.borderBottomColor = 'transparent';
    document.getElementById('tabBtn-ui').style.color = '#64748b';
    document.getElementById('tabBtn-excel').style.color = '#64748b';

    // Show active
    document.getElementById(`tabContent-${tab}`).style.display = 'block';
    const btn = document.getElementById(`tabBtn-${tab}`);
    btn.style.borderBottomColor = '#a78bfa';
    btn.style.color = 'white';
}

window.addExcelOutputRow = function (data = {}) {
    // Remove "No rows" msg
    const msg = document.getElementById('noExcelRowsMsg');
    if (msg) msg.style.display = 'none';

    const container = document.getElementById('excelOutputRowsContainer');
    const div = document.createElement('div');
    div.className = 'excel-row';
    div.style = "display: grid; grid-template-columns: 1fr 1fr 1fr 30px; gap: 10px; margin-bottom: 10px; align-items: start;";

    const colName = data.colName || "";
    const val = data.value || "";
    const logic = data.logic || "";

    div.innerHTML = `
        <input type="text" class="excel-col-name" list="inputColumnsList" placeholder="Column Name" value="${colName}" style="background: #0f172a; border: 1px solid #334155; padding: 8px; color: white; border-radius: 4px;">
        <input type="text" class="excel-col-val" placeholder="Value (e.g. data.id)" value="${val}" style="background: #0f172a; border: 1px solid #334155; padding: 8px; color: white; border-radius: 4px;">
        <textarea class="excel-col-logic" rows="5" placeholder="Logic (e.g. 'Pass/Fail')" style="background: #0f172a; border: 1px solid #334155; padding: 8px; color: white; border-radius: 4px; resize: vertical;">${logic}</textarea>
        <button onclick="this.parentElement.remove()" style="background:none; border:none; color: #ef4444; cursor: pointer;">✖</button>
    `;

    container.appendChild(div);
}

window.addUIOutputRow = function (data = {}) {
    const container = document.getElementById('uiOutputRowsContainer');
    const msg = document.getElementById('noUiRowsMsg');
    if (msg) msg.style.display = 'none';

    const div = document.createElement('div');
    div.className = 'ui-output-row';
    div.style = "display: grid; grid-template-columns: 1fr 1fr 1fr 30px; gap: 10px; margin-bottom: 10px; align-items: start;";

    const colName = data.colName || "";
    const val = data.value || "";
    const logic = data.logic || "";

    div.innerHTML = `
        <input type="text" class="ui-col-name" placeholder="Column Name (e.g. Name)" value="${colName}" style="background: #0f172a; border: 1px solid #334155; padding: 8px; color: white; border-radius: 4px;">
        <input type="text" class="ui-col-val" placeholder="Value (e.g. data.name)" value="${val}" style="background: #0f172a; border: 1px solid #334155; padding: 8px; color: white; border-radius: 4px;">
        <textarea class="ui-col-logic" rows="3" placeholder="Logic (e.g. 'Use fallback')" style="background: #0f172a; border: 1px solid #334155; padding: 8px; color: white; border-radius: 4px; resize: vertical;">${logic}</textarea>
        <button onclick="this.parentElement.remove()" style="background:none; border:none; color: #ef4444; cursor: pointer; padding-top: 10px;">✖</button>
    `;

    container.appendChild(div);
}

function getOutputConfigFromUI() {
    // 1. UI Tab (Dynamic)
    const uiMapping = [];
    const uiRows = document.querySelectorAll('#uiOutputRowsContainer .ui-output-row');
    uiRows.forEach(r => {
        const c = r.querySelector('.ui-col-name').value;
        const v = r.querySelector('.ui-col-val').value;
        const l = r.querySelector('.ui-col-logic').value;
        if (c) {
            uiMapping.push({ colName: c, value: v, logic: l });
        }
    });

    const aiInstructions = document.getElementById('modalOutputInstructions') ? document.getElementById('modalOutputInstructions').value : "";

    // 2. Excel Tab
    const excelMapping = [];
    const rows = document.querySelectorAll('#excelOutputRowsContainer .excel-row');
    rows.forEach(r => {
        const c = r.querySelector('.excel-col-name').value;
        const v = r.querySelector('.excel-col-val').value;
        const l = r.querySelector('.excel-col-logic').value;
        if (c) {
            excelMapping.push({ colName: c, value: v, logic: l });
        }
    });

    return { uiMapping, aiInstructions, excelMapping, isDynamicUI: true };
}


// --- REFACTORED: Unified Visual & Step Generation ---
function renderVisualsFromSteps(steps, inputColumns, uiColumns) {
    const container = document.getElementById('analysisSteps');
    container.innerHTML = ''; // Clear

    // Populate UI Columns Display
    const uiInput = document.getElementById('detectedUIColumnsDisplay');
    if (uiInput) {
        uiInput.value = (uiColumns && uiColumns.length) ? uiColumns.join(', ') : "";
    }

    if (!steps || steps.length === 0) {
        container.innerHTML = "<div style='color:gray;'>No steps detected.</div>";
        return;
    }

    steps.forEach((step, idx) => {
        const stepType = step.type || "LOGIC";
        const name = step.apiName || `Step ${idx + 1}`;
        const color = stepType === "API" ? "#38bdf8" : "#eab308";

        const badge = `<span style='background:${color}aa; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-right:8px; color:white; border:1px solid ${color};'>${stepType}</span>`;
        const header = `<div>${badge}<strong>${name}</strong></div>`;

        const details = [];
        if (stepType === "API") {
            if (step.method || step.endpoint) {
                details.push(`<li><strong>Call:</strong> ${step.method || ''} <code>${step.endpoint || ''}</code></li>`);
            }
            if (step.payload && step.payload !== "None") {
                let p = step.payload;
                if (p.length > 150) p = p.substring(0, 147) + "...";
                details.push(`<li><strong>Payload:</strong> ${p}</li>`);
            }
            if (step.response) {
                details.push(`<li><strong>Response:</strong> ${step.response}</li>`);
            }
        }

        const logic = step.instruction || step.logic;
        if (logic) {
            details.push(`<li style='color:#cbd5e1;'>${logic}</li>`);
        }

        let ulHtml = "";
        if (details.length > 0) {
            ulHtml = `<ul style='margin-top:5px; margin-bottom:10px; font-size:0.85em; color:var(--text-secondary); padding-left:20px; list-style-type: disc;'>${details.join('')}</ul>`;
        }

        const div = document.createElement('div');
        div.className = 'step-card';
        div.innerHTML = header + ulHtml;
        container.appendChild(div);
    });

    // Update Columns
    detectedColumns = inputColumns || [];
    const colStr = detectedColumns.join(', ');

    // Correct ID for the Builder View
    const globalInput = document.getElementById('globalInputColumns');
    if (globalInput) globalInput.value = colStr;

    // Legacy/Analysis View IDs (optional to keep for safety)
    const displayInput = document.getElementById('detectedColumnsDisplay');
    if (displayInput) displayInput.value = colStr;
    const manualInput = document.getElementById('manualColumns');
    if (manualInput) manualInput.value = colStr;
}

async function autoPopulateStepsFromAI(code) {
    // UI Feedback
    document.getElementById('stepsContainer').innerHTML = '<div style="text-align: center; color: #64748b; padding: 20px;">🤖 Analyzing code to auto-generate steps...</div>';
    document.getElementById('analysisSteps').innerHTML = '<div style="text-align: center; color: #64748b; padding: 20px;">Syncing with Steps...</div>';

    try {
        const res = await fetch('/api/scripts/reverse-engineer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        const result = await res.json();

        if (result.steps && result.steps.length > 0) {
            // 1. Populate Builder (Editable)
            document.getElementById('stepsContainer').innerHTML = '';
            stepCount = 0;

            result.steps.forEach(step => {
                addStep(step.type); // Creates the DOM elements
                const currentRowId = stepCount;
                const row = document.getElementById(`step-${currentRowId}`);

                if (step.type === 'API') {
                    row.querySelector('.step-api-name').value = step.apiName || '';
                    row.querySelector('.step-method').value = step.method || 'GET';
                    row.querySelector('.step-endpoint').value = step.endpoint || '';
                    row.querySelector('.step-payload-type').value = step.payloadType || 'JSON';
                    row.querySelector('.step-payload').value = step.payload || '';
                    row.querySelector('.step-response').value = step.response || 'resp';
                    row.querySelector('.step-instruction').value = step.instruction || '';

                    if (step.runOnce) {
                        const roBox = row.querySelector('.step-run-once');
                        if (roBox) roBox.checked = true;
                    }
                    const methodSelect = row.querySelector('.step-method');
                    if (methodSelect.onchange) methodSelect.onchange();
                } else {
                    row.querySelector('.step-logic').value = step.logic || '';
                }
            });

            // 2. Populate Visuals (Analysis Tab) Locally
            renderVisualsFromSteps(result.steps, result.excelColumns, result.uiColumns);

            // Show Proceed Button (Unlocked)
            document.getElementById('proceedBtn').style.display = 'inline-block';

            // Notify user
            const notif = document.createElement('div');
            notif.innerHTML = "<small style='color:#10b981; margin-left:10px;'>✨ Steps auto-generated by AI</small>";
            const label = document.querySelector('#descGroup label');
            if (label) label.appendChild(notif);
            return true;

        } else {
            throw new Error(result.error || "No steps returned by AI");
        }
    } catch (e) {
        console.warn("AI Reverse Engineering failed:", e);
        document.getElementById('stepsContainer').innerHTML = `<div style="text-align: center; color: #ef4444; padding: 20px;">Analysis Failed: ${e.message}</div>`;
        document.getElementById('analysisSteps').innerHTML = `<div style="text-align: center; color: #ef4444; padding: 20px;">Analysis Failed</div>`;
        alert("Analysis Failed: " + e.message); // Explicit alert for user visibility
        return false;
    }
}


// =============================================
// HELPER: Sync UI Fields from Code Comments
// =============================================
function syncUIFromCode(code) {
    if (!code) return;

    // 1. Group By Column
    const groupMatch = code.match(/#\s*CONFIG:\s*groupByColumn\s*=\s*["']([^"']+)["']/);
    const groupByInput = document.getElementById('groupByColumn');
    if (groupByInput) {
        if (groupMatch && groupMatch[1]) {
            console.log("Auto-Detected Grouping:", groupMatch[1]);
            groupByInput.value = groupMatch[1];
            // Trigger input event to update UI state (disable threading checkbox etc)
            const event = new Event('input', { bubbles: true });
            groupByInput.dispatchEvent(event);
        }
    }

    // 2. Batch Size
    const batchMatch = code.match(/#\s*CONFIG:\s*batchSize\s*=\s*(\d+)/);
    const batchInput = document.getElementById('threadSize');
    if (batchInput && batchMatch && batchMatch[1]) {
        batchInput.value = batchMatch[1];
    }

    // 3. Multithreading
    const mtMatch = code.match(/#\s*CONFIG:\s*isMultithreaded\s*=\s*(True|False|true|false)/i);
    const mtCheckbox = document.getElementById('isMultithreaded');
    if (mtCheckbox && mtMatch && mtMatch[1]) {
        const isTrue = mtMatch[1].toLowerCase() === 'true';
        // Only update if not disabled by grouping logic
        if (!mtCheckbox.disabled) {
            mtCheckbox.checked = isTrue;
            toggleThreadSize(mtCheckbox);
        }
    }
}

// =============================================
// RENDER MOCK RESULTS (Preview Window)
// =============================================
function renderMockResults(data) {
    if (!data || !Array.isArray(data) || data.length === 0) {
        document.getElementById('mockResultSection').style.display = 'none';
        return;
    }

    const container = document.getElementById('mockResultSection');
    const thead = document.getElementById('mockResultsHead');
    const tbody = document.getElementById('mockResultsBody');
    const passEl = document.getElementById('mockPass');
    const failEl = document.getElementById('mockFail');

    container.style.display = 'block';
    tbody.innerHTML = '';
    thead.innerHTML = ''; // Clear headers

    let passCount = 0;
    let failCount = 0;

    // 1. Determine Columns dynamically
    let keys = [];
    if (data.length > 0) {
        // Try to respect UI Mapping if available
        const outMapping = getOutputConfigFromUI();
        const uiCols = outMapping.uiMapping ? outMapping.uiMapping.map(m => m.colName).filter(c => c) : [];

        if (uiCols.length > 0) {
            // Use configured columns
            keys = uiCols;
        } else {
            // Fallback: Show all keys from first row (excluding internal ones)
            keys = Object.keys(data[0]).filter(k => k !== 'row');
        }

        const trHead = document.createElement('tr');
        // Add Row # Column
        const thRow = document.createElement('th');
        thRow.innerText = 'Row';
        trHead.appendChild(thRow);

        keys.forEach(k => {
            const th = document.createElement('th');
            th.innerText = k;
            trHead.appendChild(th);
        });
        thead.appendChild(trHead);

        // 2. Populate Rows
        data.forEach((row, index) => {
            const tr = document.createElement('tr');

            // Row Number
            const tdRow = document.createElement('td');
            tdRow.innerText = index + 1;
            tr.appendChild(tdRow);

            keys.forEach(k => {
                const td = document.createElement('td');
                const val = row[k];

                // Handle specific status coloring
                if (k.toLowerCase() === 'status') {
                    const sVal = String(val).toLowerCase();
                    if (sVal === 'pass' || sVal === 'success' || sVal === 'true') {
                        td.innerHTML = `<span class="badge bg-success">${val}</span>`;
                        passCount++;
                    } else {
                        td.innerHTML = `<span class="badge bg-danger">${val}</span>`;
                        failCount++;
                    }
                } else {
                    // Check for objects
                    if (typeof val === 'object' && val !== null) {
                        td.innerText = JSON.stringify(val);
                    } else {
                        td.innerText = (val !== undefined && val !== null) ? val : '';
                    }
                }
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }


    passEl.textContent = passCount;
    failEl.textContent = failCount;
}
