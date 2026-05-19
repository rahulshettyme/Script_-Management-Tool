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
    // -------------------------------------------------------
    _populateDynamicFilters() {
        const userSelect = this.container.querySelector('#eh-filter-user');
        const scriptSelect = this.container.querySelector('#eh-filter-script');
        if (!userSelect || !scriptSelect) return;

        const currentUserId = userSelect.value;
        const currentScript = scriptSelect.value;

        // Get unique users and scripts
        const users = [...new Set(this.allRecords.map(r => r.user).filter(Boolean))].sort();
        const scripts = [...new Set(this.allRecords.map(r => r.script).filter(Boolean))].sort();

        // Populate User Select
        userSelect.innerHTML = '<option value="">All Users</option>' + 
            users.map(u => `<option value="${this._esc(u)}" ${u === currentUserId ? 'selected' : ''}>${this._esc(u)}</option>`).join('');

        // Populate Script Select
        scriptSelect.innerHTML = '<option value="">All Scripts</option>' + 
            scripts.map(s => `<option value="${this._esc(s)}" ${s === currentScript ? 'selected' : ''}>${this._esc(s)}</option>`).join('');
    }

    // -------------------------------------------------------
    // Filter logic
    // -------------------------------------------------------
    _applyFilters() {
        const userFilter = (this.container.querySelector('#eh-filter-user')?.value || '').toLowerCase().trim();
        const teamFilter = (this.container.querySelector('#eh-filter-team')?.value || '');
        const scriptFilter = (this.container.querySelector('#eh-filter-script')?.value || '').toLowerCase().trim();
        const dateFromFilter = (this.container.querySelector('#eh-filter-date-from')?.value || '');
        const dateToFilter = (this.container.querySelector('#eh-filter-date-to')?.value || '');

        this.filteredRecords = this.allRecords.filter(r => {
            if (userFilter && !(r.user || '').toLowerCase().includes(userFilter)) return false;
            if (teamFilter && r.team !== teamFilter) return false;
            if (scriptFilter && !(r.script || '').toLowerCase().includes(scriptFilter)) return false;

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
                    <label>User</label>
                    <select id="eh-filter-user" class="eh-filter-select">
                        <option value="">All Users</option>
                    </select>
                </div>
                <div class="eh-filter-group">
                    <label>Team</label>
                    <select id="eh-filter-team" class="eh-filter-select">
                        <option value="">All Teams</option>
                        <option value="cs_team">CS Team</option>
                        <option value="qa_team">QA Team</option>
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
                            <th data-sort="user">User <span class="eh-sort-icon">⇅</span></th>
                            <th data-sort="team">Team <span class="eh-sort-icon">⇅</span></th>
                            <th data-sort="tenant">Tenant <span class="eh-sort-icon">⇅</span></th>
                            <th data-sort="loginUser">Login <span class="eh-sort-icon">⇅</span></th>
                            <th data-sort="dateTime" class="eh-sort-active">Date Time <span class="eh-sort-icon">↓</span></th>
                            <th data-sort="script">Script <span class="eh-sort-icon">⇅</span></th>
                            <th data-sort="executionTime">Exec. Time <span class="eh-sort-icon">⇅</span></th>
                            <th>Input File</th>
                            <th>Output File</th>
                            <th data-sort="passCount">Status <span class="eh-sort-icon">⇅</span></th>
                        </tr>
                    </thead>
                    <tbody id="eh-tbody">
                        <tr><td colspan="10" class="eh-loading">⏳ Initializing...</td></tr>
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
                    <td colspan="10">
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
                ? `<a class="eh-file-link" href="/api/audit/file?path=${encodeURIComponent(r.inputFile)}" title="${r.inputFile}" download>📥 ${this._esc(r.originalInputFile || this._basename(r.inputFile))}</a>`
                : `<span class="eh-no-file">—</span>`;

            const outputFileCell = r.outputFile
                ? `<a class="eh-file-link" href="/api/audit/file?path=${encodeURIComponent(r.outputFile)}" title="${r.outputFile}" download>📤 ${this._esc(r.originalOutputFile || this._basename(r.outputFile))}</a>`
                : `<span class="eh-no-file">—</span>`;

            return `
                <tr>
                    <td>
                        <div class="eh-cell-user">
                            <div class="eh-avatar">${initials}</div>
                            ${this._esc(r.user || '—')}
                        </div>
                    </td>
                    <td><span class="eh-team-badge ${teamClass}">${teamLabel}</span></td>
                    <td><span class="eh-tenant-cell">${this._esc(r.tenant || '—')}</span></td>
                    <td><span class="eh-login-cell">${this._esc(r.loginUser || '—')}</span></td>
                    <td class="eh-datetime">${dateTimeStr}</td>
                    <td>${this._esc(r.script || '—')}</td>
                    <td class="eh-duration">${this._esc(r.executionTime || '—')}</td>
                    <td>${inputFileCell}</td>
                    <td>${outputFileCell}</td>
                    <td>
                        <div class="eh-status-cell">
                            <span class="eh-pass-count">✅ ${passCount}</span>
                            <span style="color:#b0bec5;">|</span>
                            <span class="eh-fail-count">❌ ${failCount}</span>
                        </div>
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
                this._renderRows();
            });
        });

        const clearBtn = this.container.querySelector('#eh-filter-clear');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                filterInputs.forEach(el => el.value = '');
                this._applyFilters();
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
