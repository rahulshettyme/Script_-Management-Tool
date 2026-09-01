/**
 * ExecutionHistoryManager
 * Manages the Audit Trail for QA-Ops Workbench.
 * 
 * Responsibilities:
 *  - Fetch history records from the backend API
 *  - Render the history table with sorting and filtering
 *  - Display role-filtered records (meta-csm sees CS only)
 * 
 * Used by: history.html
 * Backend: /api/audit/history (GET), /api/audit/record (POST)
 */
class ExecutionHistoryManager {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.userRole = options.userRole || null;
        this.allRecords = [];
        this.filteredRecords = [];
        this.sortKey = 'dateTime';
        this.sortDir = 'desc'; // newest first by default

        if (!this.container) {
            console.error('[ExecutionHistory] Container not found:', containerId);
            return;
        }

        this._init();
    }

    async _init() {
        this._renderShell();
        await this._loadRole();
        await this._loadRecords();
        this._applyFilters();
        this._renderTable();
        this._attachFilterEvents();
    }

    // -------------------------------------------------------
    // Load role from backend (same pattern as main script.js)
    // -------------------------------------------------------
    async _loadRole() {
        if (this.userRole) return; // Already set (e.g. from iframe message in prod)
        try {
            const res = await fetch('/api/env-urls');
            const data = await res.json();
            const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            if (isLocal && data.local_role) {
                this.userRole = data.local_role;
                console.log(`[ExecutionHistory] Local role: ${this.userRole}`);
            }
        } catch (e) {
            console.warn('[ExecutionHistory] Could not load role:', e);
        }
    }

    // -------------------------------------------------------
    // Fetch records from backend
    // -------------------------------------------------------
    async _loadRecords() {
        const tableBody = this.container.querySelector('#eh-tbody');
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="10" class="eh-loading">⏳ Loading history...</td></tr>`;
        }

        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        try {
            const res = await fetch(`/api/audit/history?role=${encodeURIComponent(this.userRole || '')}&isLocal=${isLocal}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            this.allRecords = Array.isArray(data.records) ? data.records : [];
            console.log(`[ExecutionHistory] Loaded ${this.allRecords.length} records.`);
            this._populateDynamicFilters();
        } catch (e) {
            console.error('[ExecutionHistory] Failed to load records:', e);
            this.allRecords = [];
            if (tableBody) {
                tableBody.innerHTML = `<tr><td colspan="10" class="eh-loading" style="color:#ef4444;">❌ Failed to load history. Is the server running?</td></tr>`;
            }
        }
    }

    // -------------------------------------------------------
    // Populate dropdowns from table data
    _populateDynamicFilters() {
        const userSelect = this.container.querySelector('#eh-filter-user');
        const scriptSelect = this.container.querySelector('#eh-filter-script');
        const tenantSelect = this.container.querySelector('#eh-filter-tenant');
        const teamSelect = this.container.querySelector('#eh-filter-team');
        if (!userSelect || !scriptSelect || !tenantSelect || !teamSelect) return;

        const currentUserId = userSelect.value;
        const currentScript = scriptSelect.value;
        const currentTenant = tenantSelect.value;
        const currentTeam = teamSelect.value;

        const dateFromFilter = (this.container.querySelector('#eh-filter-date-from')?.value || '');
        const dateToFilter = (this.container.querySelector('#eh-filter-date-to')?.value || '');

        const matchesStaticFilters = (r) => {
            if (dateFromFilter) {
                const recordDate = new Date(r.dateTime).toISOString().slice(0, 10);
                if (recordDate < dateFromFilter) return false;
            }
            if (dateToFilter) {
                const recordDate = new Date(r.dateTime).toISOString().slice(0, 10);
                if (recordDate > dateToFilter) return false;
            }
            return true;
        };

        // 1. Teams matching User, Tenant, and Script filters (excluding Team filter)
        const recordsForTeams = this.allRecords.filter(r => {
            if (!matchesStaticFilters(r)) return false;
            if (currentUserId && r.user !== currentUserId) return false;
            if (currentTenant && r.tenant !== currentTenant) return false;
            if (currentScript && r.script !== currentScript) return false;
            return true;
        });
        const teams = [...new Set(recordsForTeams.map(r => r.team).filter(Boolean))].sort();

        // 2. Users matching Team, Tenant, and Script filters (excluding User filter)
        const recordsForUsers = this.allRecords.filter(r => {
            if (!matchesStaticFilters(r)) return false;
            if (currentTeam && r.team !== currentTeam) return false;
            if (currentTenant && r.tenant !== currentTenant) return false;
            if (currentScript && r.script !== currentScript) return false;
            return true;
        });
        const users = [...new Set(recordsForUsers.map(r => r.user).filter(Boolean))].sort();

        // 3. Scripts matching User, Team, and Tenant filters (excluding Script filter)
        const recordsForScripts = this.allRecords.filter(r => {
            if (!matchesStaticFilters(r)) return false;
            if (currentUserId && r.user !== currentUserId) return false;
            if (currentTeam && r.team !== currentTeam) return false;
            if (currentTenant && r.tenant !== currentTenant) return false;
            return true;
        });
        const scripts = [...new Set(recordsForScripts.map(r => r.script).filter(Boolean))].sort();

        // 4. Tenants matching User, Team, and Script filters (excluding Tenant filter)
        const recordsForTenants = this.allRecords.filter(r => {
            if (!matchesStaticFilters(r)) return false;
            if (currentUserId && r.user !== currentUserId) return false;
            if (currentTeam && r.team !== currentTeam) return false;
            if (currentScript && r.script !== currentScript) return false;
            return true;
        });
        const tenants = [...new Set(recordsForTenants.map(r => r.tenant).filter(Boolean))].sort();

        // Populate selects
        teamSelect.innerHTML = '<option value="">All Teams</option>' + 
            teams.map(t => {
                const label = t === 'cs_team' ? 'CS Team' : (t === 'qa_team' ? 'QA Team' : t);
                return `<option value="${this._esc(t)}" ${t === currentTeam ? 'selected' : ''}>${this._esc(label)}</option>`;
            }).join('');

        userSelect.innerHTML = '<option value="">All Users</option>' + 
            users.map(u => `<option value="${this._esc(u)}" ${u === currentUserId ? 'selected' : ''}>${this._esc(u)}</option>`).join('');

        scriptSelect.innerHTML = '<option value="">All Scripts</option>' + 
            scripts.map(s => `<option value="${this._esc(s)}" ${s === currentScript ? 'selected' : ''}>${this._esc(s)}</option>`).join('');

        tenantSelect.innerHTML = '<option value="">All Tenants</option>' + 
            tenants.map(t => `<option value="${this._esc(t)}" ${t === currentTenant ? 'selected' : ''}>${this._esc(t)}</option>`).join('');
    }

    // -------------------------------------------------------
    // Filter logic
    // -------------------------------------------------------
    _applyFilters() {
        const userFilter = (this.container.querySelector('#eh-filter-user')?.value || '');
        const teamFilter = (this.container.querySelector('#eh-filter-team')?.value || '');
        const tenantFilter = (this.container.querySelector('#eh-filter-tenant')?.value || '');
        const scriptFilter = (this.container.querySelector('#eh-filter-script')?.value || '');
        const dateFromFilter = (this.container.querySelector('#eh-filter-date-from')?.value || '');
        const dateToFilter = (this.container.querySelector('#eh-filter-date-to')?.value || '');

        this.filteredRecords = this.allRecords.filter(r => {
            if (userFilter && r.user !== userFilter) return false;
            if (teamFilter && r.team !== teamFilter) return false;
            if (tenantFilter && r.tenant !== tenantFilter) return false;
            if (scriptFilter && r.script !== scriptFilter) return false;

            if (dateFromFilter) {
                const recordDate = new Date(r.dateTime).toISOString().slice(0, 10);
                if (recordDate < dateFromFilter) return false;
            }
            if (dateToFilter) {
                const recordDate = new Date(r.dateTime).toISOString().slice(0, 10);
                if (recordDate > dateToFilter) return false;
            }
            return true;
        });

        this._sort();
        this._updateStats();
    }

    // -------------------------------------------------------
    // Sort logic
    // -------------------------------------------------------
    _sort() {
        this.filteredRecords.sort((a, b) => {
            if (this.sortKey === 'user') {
                const teamA = String(a.team || '').toLowerCase();
                const teamB = String(b.team || '').toLowerCase();
                if (teamA !== teamB) {
                    if (teamA < teamB) return this.sortDir === 'asc' ? -1 : 1;
                    if (teamA > teamB) return this.sortDir === 'asc' ? 1 : -1;
                }
                const userA = String(a.user || '').toLowerCase();
                const userB = String(b.user || '').toLowerCase();
                if (userA < userB) return this.sortDir === 'asc' ? -1 : 1;
                if (userA > userB) return this.sortDir === 'asc' ? 1 : -1;
                return 0;
            }

            let va = a[this.sortKey] || '';
            let vb = b[this.sortKey] || '';

            if (this.sortKey === 'dateTime') {
                va = new Date(va).getTime() || 0;
                vb = new Date(vb).getTime() || 0;
            } else {
                va = String(va).toLowerCase();
                vb = String(vb).toLowerCase();
            }

            if (va < vb) return this.sortDir === 'asc' ? -1 : 1;
            if (va > vb) return this.sortDir === 'asc' ? 1 : -1;
            return 0;
        });
    }

    _setSort(key) {
        if (this.sortKey === key) {
            this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortKey = key;
            this.sortDir = key === 'dateTime' ? 'desc' : 'asc';
        }

        // Update header icons
        this.container.querySelectorAll('.eh-table th[data-sort]').forEach(th => {
            th.classList.remove('eh-sort-active');
            th.querySelector('.eh-sort-icon').textContent = '⇅';
        });

        const activeTh = this.container.querySelector(`.eh-table th[data-sort="${key}"]`);
        if (activeTh) {
            activeTh.classList.add('eh-sort-active');
            activeTh.querySelector('.eh-sort-icon').textContent = this.sortDir === 'asc' ? '↑' : '↓';
        }

        this._sort();
        this._renderRows();
    }

    // -------------------------------------------------------
    // Stats update
    // -------------------------------------------------------
    _updateStats() {
        const totalEl = this.container.querySelector('#eh-stat-total');
        if (totalEl) totalEl.textContent = this.filteredRecords.length;
    }

    // -------------------------------------------------------
    // Rendering
    // -------------------------------------------------------
    _renderShell() {
        this.container.innerHTML = `
            <!-- Filter Bar -->
            <div class="eh-filter-bar">
                <div class="eh-filter-group">
                    <label>Team</label>
                    <select id="eh-filter-team" class="eh-filter-select">
                        <option value="">All Teams</option>
                    </select>
                </div>
                <div class="eh-filter-group">
                    <label>User</label>
                    <select id="eh-filter-user" class="eh-filter-select">
                        <option value="">All Users</option>
                    </select>
                </div>
                <div class="eh-filter-group">
                    <label>Tenant</label>
                    <select id="eh-filter-tenant" class="eh-filter-select">
                        <option value="">All Tenants</option>
                    </select>
                </div>
                <div class="eh-filter-group">
                    <label>Script</label>
                    <select id="eh-filter-script" class="eh-filter-select">
                        <option value="">All Scripts</option>
                    </select>
                </div>
                <div class="eh-filter-group">
                    <label>Date From</label>
                    <input id="eh-filter-date-from" class="eh-filter-input" type="date">
                </div>
                <div class="eh-filter-group">
                    <label>Date To</label>
                    <input id="eh-filter-date-to" class="eh-filter-input" type="date">
                </div>
                <div class="eh-filter-actions">
                    <button id="eh-filter-clear" class="eh-filter-clear-btn">✕ Clear</button>
                    <div class="eh-total-count">
                        📋 Total: <strong id="eh-stat-total">0</strong>
                    </div>
                </div>
            </div>

            <!-- Table -->
            <div class="eh-table-wrapper">
                <table class="eh-table">
                    <thead>
                        <tr>
                            <th data-sort="user">User / Team <span class="eh-sort-icon">⇅</span></th>
                            <th data-sort="tenant">Tenant / Login <span class="eh-sort-icon">⇅</span></th>
                            <th data-sort="dateTime" class="eh-sort-active">Date Time <span class="eh-sort-icon">↓</span></th>
                            <th data-sort="script">Script <span class="eh-sort-icon">⇅</span></th>
                            <th data-sort="executionTime">Exec. Time <span class="eh-sort-icon">⇅</span></th>
                            <th>Files</th>
                            <th data-sort="passCount">Status <span class="eh-sort-icon">⇅</span></th>
                            <th>Consent & Feedback</th>
                        </tr>
                    </thead>
                    <tbody id="eh-tbody">
                        <tr><td colspan="8" class="eh-loading">⏳ Initializing...</td></tr>
                    </tbody>
                </table>
            </div>
        `;
    }

    _renderTable() {
        this._renderRows();
        this._updateSortHeaders();
    }

    _renderRows() {
        const tbody = this.container.querySelector('#eh-tbody');
        if (!tbody) return;

        if (this.filteredRecords.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8">
                        <div class="eh-empty-state">
                            <div class="eh-empty-icon">📭</div>
                            <p>No execution records found.</p>
                            <p style="font-size:0.8rem; color:#b0bec5;">Run a script in the Workbench to create your first record.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.filteredRecords.map(r => {
            const initials = (r.user || '?').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
            const teamLabel = r.team === 'cs_team' ? 'CS Team' : (r.team === 'qa_team' ? 'QA Team' : (r.team || '—'));
            const teamClass = r.team === 'cs_team' ? 'eh-team-cs' : 'eh-team-qa';
            const dateTimeStr = r.dateTime ? this._formatDateTime(r.dateTime) : '—';
            const passCount = r.passCount ?? 0;
            const failCount = r.failCount ?? 0;

            const inputFileCell = r.inputFile
                ? `<a class="eh-file-link" href="/api/audit/file?path=${encodeURIComponent(r.inputFile)}" title="${this._esc(r.originalInputFile || this._basename(r.inputFile))}" download style="white-space: nowrap;">📥 Template</a>`
                : `<span class="eh-no-file">—</span>`;

            const outputFileCell = r.outputFile
                ? `<a class="eh-file-link" href="/api/audit/file?path=${encodeURIComponent(r.outputFile)}" title="${this._esc(r.originalOutputFile || this._basename(r.outputFile))}" download style="white-space: nowrap;">📤 Results</a>`
                : `<span class="eh-no-file">—</span>`;

            const consentCell = r.preReqChecked
                ? `<div class="eh-consent-cell">
                      <span class="eh-consent-badge">✅ Accepted</span>
                      <div class="eh-consent-tooltip">
                          <strong style="color: #6366f1;">Feedback Comment:</strong><br>
                          ${this._esc(r.preReqReason || 'No feedback comment provided.')}
                      </div>
                   </div>`
                : `<span class="eh-no-file">—</span>`;

            return `
                <tr>
                    <td data-label="User / Team">
                        <div class="eh-cell-user">
                            <div class="eh-avatar">${initials}</div>
                            <div style="display: flex; flex-direction: column; gap: 2px;">
                                <span style="font-weight: 600;">${this._esc(r.user || '—')}</span>
                                <span class="eh-team-badge ${teamClass}" style="font-size: 0.7rem; padding: 1px 6px; width: fit-content; border-radius: 4px;">${teamLabel}</span>
                            </div>
                        </div>
                    </td>
                    <td data-label="Tenant / Login">
                        <div style="display: flex; flex-direction: column; gap: 2px;">
                            <span class="eh-tenant-cell" style="font-weight: 500;">${this._esc(r.tenant || '—')}</span>
                            <span class="eh-login-cell" style="font-size: 0.75rem; color: #64748b;">${this._esc(r.loginUser || '—')}</span>
                        </div>
                    </td>
                    <td data-label="Date Time" class="eh-datetime">${dateTimeStr}</td>
                    <td data-label="Script" style="font-weight: 500;">${this._esc(r.script || '—')}</td>
                    <td data-label="Exec. Time" class="eh-duration">${this._esc(r.executionTime || '—')}</td>
                    <td data-label="Files">
                        <div style="display: flex; flex-direction: column; gap: 4px;">
                            ${inputFileCell}
                            ${outputFileCell}
                        </div>
                    </td>
                    <td data-label="Status">
                        <div class="eh-status-cell">
                            <span class="eh-pass-count">✅ ${passCount}</span>
                            <span style="color:#b0bec5;">|</span>
                            <span class="eh-fail-count">❌ ${failCount}</span>
                        </div>
                    </td>
                    <td data-label="Consent & Feedback">
                        ${consentCell}
                    </td>
                </tr>
            `;
        }).join('');
    }

    _updateSortHeaders() {
        this.container.querySelectorAll('.eh-table th[data-sort]').forEach(th => {
            const key = th.getAttribute('data-sort');
            const icon = th.querySelector('.eh-sort-icon');
            if (key === this.sortKey) {
                th.classList.add('eh-sort-active');
                if (icon) icon.textContent = this.sortDir === 'asc' ? '↑' : '↓';
            } else {
                th.classList.remove('eh-sort-active');
                if (icon) icon.textContent = '⇅';
            }
        });
    }

    // -------------------------------------------------------
    // Event Listeners
    // -------------------------------------------------------
    _attachFilterEvents() {
        const filterInputs = this.container.querySelectorAll('.eh-filter-input, .eh-filter-select');
        filterInputs.forEach(el => {
            el.addEventListener('input', () => {
                this._applyFilters();
                this._populateDynamicFilters();
                this._renderRows();
            });
        });

        const clearBtn = this.container.querySelector('#eh-filter-clear');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                filterInputs.forEach(el => el.value = '');
                this._applyFilters();
                this._populateDynamicFilters();
                this._renderRows();
            });
        }

        // Sort via header click
        this.container.querySelectorAll('.eh-table th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                this._setSort(th.getAttribute('data-sort'));
            });
        });
    }

    // -------------------------------------------------------
    // Helpers
    // -------------------------------------------------------
    _formatDateTime(iso) {
        try {
            const d = new Date(iso);
            const date = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
            const time = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            return `${date}, ${time}`;
        } catch {
            return iso;
        }
    }

    _basename(filePath) {
        return filePath ? filePath.split(/[\\/]/).pop() : '—';
    }

    _esc(str) {
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}

// Expose globally
window.ExecutionHistoryManager = ExecutionHistoryManager;
