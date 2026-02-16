
let allScripts = [];
let filteredScripts = [];
let currentPage = 1;
const rowsPerPage = 10;

document.addEventListener('DOMContentLoaded', async () => {
    await fetchScripts();
});

async function fetchScripts() {
    try {
        const customRes = await fetch('/api/scripts/custom');
        const customScripts = await customRes.json();
        const draftsRes = await fetch('/api/scripts/list-drafts');
        const draftScripts = await draftsRes.json();

        // 1. Registered Scripts
        const registered = customScripts.map(s => ({
            name: s.name,
            filename: s.filename || s.name,
            team: s.team || 'Unassigned',
            isReusable: s.isReusable || false,
            status: 'Active',
            description: s.description,
            mtime: s.mtime || Date.now()
        }));

        // 2. Drafts
        const drafts = draftScripts.map(d => ({
            name: d.name,
            filename: d.name,
            team: 'Unassigned',
            status: 'Draft',
            description: '',
            mtime: d.mtime
        }));

        allScripts = [...registered, ...drafts];

        // Default Sort: Status (Drafts first), then Name
        allScripts.sort((a, b) => {
            if (a.status === b.status) return a.name.localeCompare(b.name);
            return a.status === 'Draft' ? -1 : 1;
        });

        // DEDUPLICATION: If Active exists, hide Draft
        const uniqueScripts = [];
        const seenFilenames = new Set();
        const activeFilenames = new Set(allScripts.filter(s => s.status === 'Active').map(s => s.filename));

        allScripts.forEach(s => {
            // If this is a Draft, checks if Active exists
            if (s.status === 'Draft' && activeFilenames.has(s.filename)) {
                return; // Skip this Draft, show Active instead
            }
            uniqueScripts.push(s);
        });

        allScripts = uniqueScripts;
        filteredScripts = [...allScripts];
        updateStats();
        renderTable();

    } catch (e) {
        console.error("Failed to fetch scripts", e);
        document.getElementById('scriptTableBody').innerHTML = `<tr><td colspan="4" style="text-align:center; color: #ef4444; padding: 2rem;">Error loading scripts: ${e.message}</td></tr>`;
    }
}

function updateStats() {
    document.getElementById('totalScripts').innerText = allScripts.length;
    document.getElementById('activeScripts').innerText = allScripts.filter(s => s.status === 'Active').length;
    document.getElementById('draftScripts').innerText = allScripts.filter(s => s.status === 'Draft').length;
    // Exclude Drafts from Unassigned calculation
    document.getElementById('unassignedCount').innerText = allScripts.filter(s => (s.team === 'Unassigned' || !s.team) && s.status !== 'Draft').length;
}

function filterTable() {
    const term = document.getElementById('searchInput').value.toLowerCase();
    const teamFilter = document.getElementById('filterTeam').value;
    const statusFilter = document.getElementById('filterStatus') ? document.getElementById('filterStatus').value : 'ALL';

    filteredScripts = allScripts.filter(s => {
        // 1. Text Search
        const matchesTerm = s.name.toLowerCase().includes(term);

        // 2. Status Filter
        const matchesStatus = statusFilter === 'ALL' || s.status === statusFilter;

        // 3. Team Filter (Logic: Show if exact match OR if script is 'Both' and filter is CS/QA)
        // Normalize for safety
        const sTeam = (s.team || 'Unassigned').toLowerCase();
        const fTeam = teamFilter.toLowerCase();

        let matchesTeam = false;
        if (teamFilter === 'ALL') {
            matchesTeam = true;
        } else if (teamFilter === 'Unassigned') {
            matchesTeam = sTeam === 'unassigned';
        } else if (teamFilter === 'Both') {
            matchesTeam = sTeam === 'both';
        } else {
            // Filter is CS or QA
            // Show if script matches exactly OR script is 'Both'
            matchesTeam = (sTeam === fTeam) || (sTeam === 'both');
        }

        return matchesTerm && matchesTeam && matchesStatus;
    });

    currentPage = 1; // Reset to page 1 on filter
    renderTable();
}

function renderTable() {
    const tbody = document.getElementById('scriptTableBody');
    tbody.innerHTML = '';

    const totalPages = Math.ceil(filteredScripts.length / rowsPerPage);

    // Pagination Controls
    document.getElementById('pageInfo').innerText = `Page ${currentPage} of ${totalPages || 1}`;
    document.getElementById('prevBtn').disabled = currentPage === 1;
    document.getElementById('nextBtn').disabled = currentPage === totalPages || totalPages === 0;

    if (filteredScripts.length === 0) {
        document.getElementById('noDataMessage').style.display = 'block';
        return;
    }
    document.getElementById('noDataMessage').style.display = 'none';

    // Slice for Current Page
    const start = (currentPage - 1) * rowsPerPage;
    const end = start + rowsPerPage;
    const scriptsToShow = filteredScripts.slice(start, end);

    scriptsToShow.forEach((script) => {
        const tr = document.createElement('tr');

        // 1. Name & Description Column
        const nameTd = document.createElement('td');

        // --- Name Section ---
        const nameContainer = document.createElement('div');
        nameContainer.style.marginBottom = "8px";

        // Display Mode
        const nameDisplay = document.createElement('div');
        nameDisplay.style.display = 'flex';
        nameDisplay.style.alignItems = 'center';
        nameDisplay.style.gap = '8px';

        const nameText = document.createElement('span');
        nameText.style.fontWeight = "500";
        nameText.style.fontSize = "1rem";
        nameText.style.color = "#f8fafc";
        nameText.textContent = script.name.replace('.py', '');

        const nameEditBtn = document.createElement('button');
        nameEditBtn.className = 'action-btn';
        nameEditBtn.style.padding = '2px 6px';
        nameEditBtn.style.border = 'none';
        nameEditBtn.innerHTML = '✎';
        nameEditBtn.title = 'Edit Name';

        nameDisplay.appendChild(nameText);
        nameDisplay.appendChild(nameEditBtn);

        const fileSubtext = document.createElement('div');
        fileSubtext.style.fontSize = "0.75rem";
        fileSubtext.style.color = "#64748b";
        fileSubtext.textContent = script.filename;

        // Edit Mode (Hidden initially)
        const nameEditForm = document.createElement('div');
        nameEditForm.style.display = 'none';
        nameEditForm.style.gap = '8px';
        nameEditForm.style.alignItems = 'center';

        const nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.value = script.name.replace('.py', '');
        nameInput.className = 'search-input'; // Reuse style
        nameInput.style.padding = '4px 8px';
        nameInput.style.width = '200px';

        const nameSaveBtn = document.createElement('button');
        nameSaveBtn.className = 'btn-primary btn-success';
        nameSaveBtn.style.padding = '4px 8px';
        nameSaveBtn.style.fontSize = '0.8rem';
        nameSaveBtn.textContent = '✓';

        const nameCancelBtn = document.createElement('button');
        nameCancelBtn.className = 'action-btn';
        nameCancelBtn.style.padding = '4px 8px';
        nameCancelBtn.textContent = '✕';

        nameEditForm.appendChild(nameInput);
        nameEditForm.appendChild(nameSaveBtn);
        nameEditForm.appendChild(nameCancelBtn);

        // Name Logic
        nameEditBtn.onclick = () => {
            nameDisplay.style.display = 'none';
            nameEditForm.style.display = 'flex';
            nameInput.focus();
        };

        nameCancelBtn.onclick = () => {
            nameDisplay.style.display = 'flex';
            nameEditForm.style.display = 'none';
            nameInput.value = script.name.replace('.py', ''); // Reset
        };

        nameSaveBtn.onclick = async () => {
            const newName = nameInput.value.trim();
            if (newName && newName !== script.name.replace('.py', '')) {
                await handleRename(script, newName);
            } else {
                nameCancelBtn.click();
            }
        };

        nameContainer.appendChild(nameDisplay);
        nameContainer.appendChild(nameEditForm);
        nameContainer.appendChild(fileSubtext);

        // --- Description Section ---
        const descContainer = document.createElement('div');
        descContainer.style.marginTop = "6px";
        descContainer.style.paddingTop = "6px";
        descContainer.style.borderTop = "1px solid #334155";

        // Display Mode
        const descDisplay = document.createElement('div');
        descDisplay.style.display = 'flex';
        descDisplay.style.alignItems = 'flex-start'; // Align top
        descDisplay.style.gap = '8px';

        const descText = document.createElement('span');
        descText.style.fontSize = "0.85rem";
        descText.style.color = "#94a3b8";
        descText.style.flex = "1";
        descText.style.whiteSpace = "pre-wrap";
        descText.style.lineHeight = "1.4";
        // Truncate long descriptions
        if (script.description && script.description.length > 150) {
            descText.textContent = script.description.substring(0, 150) + '...';
            descText.title = script.description;
        } else {
            descText.textContent = script.description || "No description";
        }
        if (!script.description) descText.style.fontStyle = 'italic';

        const descEditBtn = document.createElement('button');
        descEditBtn.className = 'action-btn';
        descEditBtn.style.padding = '2px 6px';
        descEditBtn.style.border = 'none';

        if (script.status === 'Draft') {
            descEditBtn.style.opacity = '0.3';
            descEditBtn.style.cursor = 'not-allowed';
            descEditBtn.title = "Register script to edit description";
            // No onclick
        } else {
            descEditBtn.innerHTML = '✎';
            descEditBtn.title = 'Edit Description';
            descEditBtn.onclick = () => {
                descDisplay.style.display = 'none';
                descEditForm.style.display = 'flex';
                descInput.focus();
            };
        }

        descDisplay.appendChild(descText);
        descDisplay.appendChild(descEditBtn);

        // Edit Mode
        const descEditForm = document.createElement('div');
        descEditForm.style.display = 'none';
        descEditForm.style.flexDirection = 'column';
        descEditForm.style.gap = '8px';

        const descInput = document.createElement('textarea');
        descInput.className = 'search-input';
        descInput.style.width = '100%';
        descInput.style.minHeight = '60px';
        descInput.style.padding = '8px';
        descInput.style.fontFamily = 'inherit';
        descInput.value = script.description || '';

        const descBtnRow = document.createElement('div');
        descBtnRow.style.display = 'flex';
        descBtnRow.style.gap = '8px';

        const descSaveBtn = document.createElement('button');
        descSaveBtn.className = 'btn-primary btn-success';
        descSaveBtn.style.padding = '4px 12px';
        descSaveBtn.style.fontSize = '0.8rem';
        descSaveBtn.textContent = 'Save';

        const descCancelBtn = document.createElement('button');
        descCancelBtn.className = 'action-btn';
        descCancelBtn.style.padding = '4px 12px';
        descCancelBtn.textContent = 'Cancel';

        descBtnRow.appendChild(descSaveBtn);
        descBtnRow.appendChild(descCancelBtn);

        descEditForm.appendChild(descInput);
        descEditForm.appendChild(descBtnRow);

        // Description Logic
        // Handled in creation above for Draft status check
        // descEditBtn.onclick = ... (MOVED UP)

        descCancelBtn.onclick = () => {
            descDisplay.style.display = 'flex';
            descEditForm.style.display = 'none';
            descInput.value = script.description || '';
        };

        descSaveBtn.onclick = async () => {
            const newDesc = descInput.value.trim();
            if (newDesc !== (script.description || '')) {
                await handleDescriptionUpdate(script, newDesc);
            } else {
                descCancelBtn.click();
            }
        };

        descContainer.appendChild(descDisplay);
        descContainer.appendChild(descEditForm);

        nameTd.appendChild(nameContainer);
        nameTd.appendChild(descContainer);

        // 2. Status Column
        const statusTd = document.createElement('td');
        const statusBadge = document.createElement('span');
        statusBadge.className = `status-badge ${script.status === 'Active' ? 'status-active' : 'status-draft'}`;
        statusBadge.innerText = script.status;
        statusTd.appendChild(statusBadge);

        // 3. Team Column (Assignment)
        const teamTd = document.createElement('td');
        const container = document.createElement('div');
        container.style.display = 'flex';
        container.style.alignItems = 'center';

        const select = document.createElement('select');
        select.className = 'team-select';
        select.style.width = '100%'; // Ensure full width
        select.style.minWidth = '130px'; // Prevent shrink below readable "Unassigned"

        // Disable team selection for Drafts
        if (script.status === 'Draft') {
            select.disabled = true;
            select.style.opacity = '0.7';
            select.title = "Register script to assign team";
        }

        const teams = ['CS', 'QA', 'Both', 'Unassigned'];
        teams.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t;
            opt.innerText = t;
            if (script.team === t) opt.selected = true;
            select.appendChild(opt);
        });

        // Save Indicator Span
        const indicator = document.createElement('span');
        indicator.className = 'save-indicator';

        // Change Listener
        select.onchange = (e) => updateTeam(script, e.target.value, indicator);

        container.appendChild(select);
        container.appendChild(indicator);
        teamTd.appendChild(container);

        // 4. Reusable Column
        const reusableTd = document.createElement('td');
        const reuseContainer = document.createElement('div');
        reuseContainer.style.display = 'flex';
        reuseContainer.style.alignItems = 'center';

        const toggle = document.createElement('input');
        toggle.type = 'checkbox';
        toggle.checked = script.isReusable === true;
        toggle.style.cursor = 'pointer';
        toggle.style.transform = 'scale(1.2)';
        toggle.style.marginRight = '8px';

        const reuseIndicator = document.createElement('span');
        reuseIndicator.className = 'save-indicator';

        if (script.status === 'Draft') {
            toggle.disabled = true;
            toggle.title = "Register script first";
        } else {
            toggle.onchange = (e) => updateReusable(script, e.target.checked, reuseIndicator);
        }
        reuseContainer.appendChild(toggle);
        reuseContainer.appendChild(reuseIndicator);
        reusableTd.appendChild(reuseContainer);


        // 5. Actions Column (Delete)
        const actionsTd = document.createElement('td');
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'action-btn';
        deleteBtn.innerHTML = '🗑️'; // Trash icon
        deleteBtn.title = 'Delete Script';
        deleteBtn.style.color = '#ef4444'; // Red
        deleteBtn.style.borderColor = '#ef4444';
        deleteBtn.style.marginLeft = '0'; // align left or center

        deleteBtn.onmouseover = () => { deleteBtn.style.background = 'rgba(239, 68, 68, 0.1)'; };
        deleteBtn.onmouseout = () => { deleteBtn.style.background = 'transparent'; };

        deleteBtn.onclick = () => deleteScript(script);

        actionsTd.appendChild(deleteBtn);


        tr.appendChild(nameTd);
        tr.appendChild(statusTd);
        tr.appendChild(teamTd);
        tr.appendChild(reusableTd);
        tr.appendChild(actionsTd);

        tbody.appendChild(tr);
    });
}

// Pagination Logic
function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        renderTable();
    }
}

function nextPage() {
    const totalPages = Math.ceil(filteredScripts.length / rowsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        renderTable();
    }
}

async function updateTeam(script, newTeam, indicatorEl) {
    if (script.status === 'Draft') {
        alert("Drafts cannot be assigned. Please open and Register the script first.");
        fetchScripts();
        return;
    }

    // 1. Show Saving state
    indicatorEl.innerText = "Saving...";
    indicatorEl.className = 'save-indicator'; // Reset color
    indicatorEl.style.color = "#94a3b8"; // Neutral
    indicatorEl.style.opacity = 1;

    try {
        const res = await fetch('/api/scripts/update-meta', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: script.filename, team: newTeam })
        });
        const data = await res.json();

        if (data.success) {
            // 2. Show Success
            script.team = newTeam; // Update local model
            indicatorEl.innerHTML = "✓ Saved";
            indicatorEl.className = 'save-indicator save-success';

            // Re-calc stats in background without re-rendering entire table (to keep focus)
            updateStats();

            // Fade out after 2s
            setTimeout(() => {
                indicatorEl.style.opacity = 0;
            }, 2000);
        } else {
            // 3. Show Error
            indicatorEl.innerText = "❌ Error";
            indicatorEl.className = 'save-indicator save-error';
            console.error("Update failed:", data.error);
        }
    } catch (e) {
        indicatorEl.innerText = "❌ Network";
        indicatorEl.className = 'save-indicator save-error';
        console.error("Network error:", e);
    }
}

async function updateReusable(script, isReusable, indicatorEl) {
    // 1. Show Saving state
    indicatorEl.innerText = "..";
    indicatorEl.style.opacity = 1;

    try {
        const res = await fetch('/api/scripts/update-meta', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: script.filename, isReusable: isReusable })
        });
        const data = await res.json();

        if (data.success) {
            script.isReusable = isReusable;
            indicatorEl.innerText = "✓";
            indicatorEl.className = 'save-indicator save-success';
            setTimeout(() => { indicatorEl.style.opacity = 0; }, 1500);
        } else {
            indicatorEl.innerText = "❌";
            indicatorEl.className = 'save-indicator save-error';
            console.error("Update failed:", data.error);
        }
    } catch (e) {
        indicatorEl.innerText = "❌";
        console.error("Network error:", e);
    }
}

async function handleRename(script, newName) {
    const oldName = script.name.replace('.py', '');

    if (newName && newName.trim() !== "" && newName !== oldName) {
        try {
            const res = await fetch('/api/scripts/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ oldName: script.filename, newName: newName.trim() })
            });
            const data = await res.json();

            if (data.success) {
                // await fetchScripts(); // Reload table
                // Optimize: Just update local data and re-render current page
                // But filename changes, so re-fetching is safer.
                await fetchScripts();
            } else {
                alert('Rename failed: ' + data.error);
            }
        } catch (e) {
            console.error(e);
            alert('Rename failed: ' + e.message);
        }
    }
}

async function handleDescriptionUpdate(script, newDesc) {
    try {
        const res = await fetch('/api/scripts/update-meta', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: script.filename, description: newDesc })
        });
        const data = await res.json();

        if (data.success) {
            script.description = newDesc; // Update local model
            // No need to full reload, just re-render table to show updated desc
            renderTable();
        } else {
            alert('Update failed: ' + data.error);
        }
    } catch (e) {
        console.error(e);
        alert('Update failed: ' + e.message);
    }
}

async function deleteScript(script) {
    const confirmMsg = `Are you sure you want to delete "${script.name}"?\n\nThis will permanently delete the script file and configuration.`;
    if (!confirm(confirmMsg)) return;

    try {
        const res = await fetch('/api/scripts/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: script.filename })
        });
        const data = await res.json();

        if (data.success) {
            // Remove from local list
            allScripts = allScripts.filter(s => s.filename !== script.filename);
            // Re-filter and render
            filterTable();
        } else {
            alert('Delete failed: ' + data.error);
        }
    } catch (e) {
        console.error("Delete network error:", e);
        alert('Delete failed: ' + e.message);
    }
}
