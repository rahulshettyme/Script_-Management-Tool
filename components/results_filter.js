/**
 * RESULTS FILTER ENGINE (Shared Component) — results_filter.js
 * =============================================================
 * PROJECT RULE: Every results table in QA-Ops Workbench MUST use this engine
 * for column filtering and smart downloads. No table-specific filter logic should
 * be written outside this file.
 *
 * Usage:
 *   const filter = new ResultsFilter({
 *     tableEl   : document.querySelector('.results-table'),
 *     getData   : () => executionResults,
 *     isPassFn  : (row) => evaluateRowStatus(row, template).isPass,
 *     getFileName: () => `Results_${selectedDataType}`,
 *     onDownload: (data, filename) => _doXlsxDownload(data, filename),
 *     darkTheme : false   // true for onboarding dark UI
 *   });
 *   filter.init();   // Once, after table headers are rendered
 *   filter.sync();   // After each batch of rows are appended
 *   filter.reset();  // On new execution start
 *   filter.destroy();// On full page reset (optional cleanup)
 */
(function (global) {
    'use strict';

    class ResultsFilter {

        /**
         * @param {Object} config
         * @param {HTMLTableElement} config.tableEl      The <table> element to attach to.
         * @param {Function}         config.getData      Returns the full data array (all rows).
         * @param {Function}         config.isPassFn     (row) => boolean — pass/fail evaluator.
         * @param {Function}         config.getFileName  () => string — base filename for downloads.
         * @param {Function}         config.onDownload   (data[], filename) => void — XLSX writer.
         * @param {boolean}          [config.darkTheme]  Use dark CSS theme. Default: false.
         */
        constructor(config) {
            this.tableEl    = config.tableEl;
            this.getData    = config.getData;
            this.isPassFn   = config.isPassFn;
            this.getFileName = config.getFileName;
            this.onDownload = config.onDownload;
            this.darkTheme  = !!config.darkTheme;

            this._state = { column: 'all', text: '' };
            this._barEl   = null;
            this._countEl = null;
            this._initialized = false;
        }

        // ─── PUBLIC API ───────────────────────────────────────────────────────

        /**
         * Insert the filter bar above the table's scroll wrapper.
         * Safe to call multiple times — only initializes once.
         */
        init() {
            if (this._initialized) return;
            this._buildFilterBar();
            this._initialized = true;
        }

        /**
         * Re-apply the current filter state to all tbody <tr> rows.
         * Call this after each render cycle (batch append).
         */
        sync() {
            if (!this._initialized) return;
            this._applyToDom();
        }

        /**
         * Reset filter to show all rows. Clears UI controls.
         */
        reset() {
            this._state = { column: 'all', text: '' };
            if (this._barEl) {
                const sel = this._barEl.querySelector('.rf-column-select');
                const inp = this._barEl.querySelector('.rf-text-input');
                if (sel) sel.value = 'all';
                if (inp) inp.value = '';
            }
            if (this._initialized) this._applyToDom();
        }

        /**
         * Remove the filter bar from the DOM. Call on full page reset.
         */
        destroy() {
            if (this._barEl && this._barEl.parentElement) {
                this._barEl.parentElement.removeChild(this._barEl);
            }
            this._barEl       = null;
            this._countEl     = null;
            this._initialized = false;
        }

        // ─── DATA SELECTORS ──────────────────────────────────────────────────

        /** Returns data array filtered by current filter state. */
        getFilteredData() {
            return this._applyToData(this.getData());
        }

        /** Returns only rows that evaluate as pass. */
        getPassData() {
            return this.getData().filter(r => this.isPassFn(r));
        }

        /** Returns only rows that evaluate as fail. */
        getFailData() {
            return this.getData().filter(r => !this.isPassFn(r));
        }

        /**
         * Trigger a download with the given mode.
         * @param {'all'|'filtered'|'pass'|'fail'} mode
         */
        download(mode) {
            const all = this.getData();
            if (!all || all.length === 0) {
                alert('No results to download.');
                return;
            }
            let data, label;
            switch (mode) {
                case 'pass':     data = this.getPassData();    label = 'Passed';   break;
                case 'fail':     data = this.getFailData();    label = 'Failed';   break;
                case 'filtered': data = this.getFilteredData(); label = 'Filtered'; break;
                default:         data = all;                   label = 'All';       break;
            }
            if (!data || data.length === 0) {
                alert(`No ${label.toLowerCase()} rows to download.`);
                return;
            }
            const filename = `${this.getFileName()}_${label}`;
            this.onDownload(data, filename);
        }

        // ─── PRIVATE ─────────────────────────────────────────────────────────

        _buildFilterBar() {
            // Find all column headers dynamically (excluding 'Row' index column)
            const headers = Array.from(this.tableEl.querySelectorAll('thead th'))
                .map(th => th.textContent.trim())
                .filter(txt => txt && txt !== 'Row');

            const bar = document.createElement('div');
            bar.className = 'rf-filter-bar' + (this.darkTheme ? ' rf-dark' : '');

            let optionsHtml = `<option value="all" selected>All Columns</option>`;
            headers.forEach(h => {
                optionsHtml += `<option value="${h}">${h}</option>`;
            });

            bar.innerHTML = `
                <div class="rf-filter-controls">
                    <span class="rf-filter-icon">🔍</span>
                    <select class="rf-column-select" autocomplete="off" aria-label="Filter by column">
                        ${optionsHtml}
                    </select>
                    <input
                        type="text"
                        class="rf-text-input"
                        placeholder="Search column value…"
                        aria-label="Search results text"
                    >
                    <button class="rf-clear-btn" title="Clear all filters" aria-label="Clear filters">✕ Clear</button>
                </div>
                <span class="rf-count-badge" aria-live="polite">—</span>
            `;

            // Column selector dropdown handler
            const sel = bar.querySelector('.rf-column-select');
            sel.value = this._state.column;
            sel.addEventListener('change', () => {
                this._state.column = sel.value;
                this._applyToDom();
            });

            // Text search — debounced 180ms
            const inp = bar.querySelector('.rf-text-input');
            let debounceTimer;
            inp.addEventListener('input', () => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this._state.text = inp.value;
                    this._applyToDom();
                }, 180);
            });

            // Clear button
            bar.querySelector('.rf-clear-btn').addEventListener('click', () => this.reset());

            this._countEl = bar.querySelector('.rf-count-badge');
            this._barEl   = bar;

            // Insert immediately before the table's scroll wrapper
            const scrollWrapper = this.tableEl.closest('[style*="overflow"]') || this.tableEl.parentElement;
            if (scrollWrapper && scrollWrapper.parentElement) {
                scrollWrapper.parentElement.insertBefore(bar, scrollWrapper);
            } else {
                this.tableEl.parentElement.insertBefore(bar, this.tableEl);
            }
        }

        _applyToDom() {
            const tbody = this.tableEl.querySelector('tbody');
            if (!tbody) return;

            const rows    = Array.from(tbody.querySelectorAll('tr'));
            const data    = this.getData();
            const { column, text } = this._state;
            const lowerText = text.toLowerCase().trim();

            const headerCells = Array.from(this.tableEl.querySelectorAll('thead th'));
            let targetColIndex = -1;
            if (column !== 'all') {
                targetColIndex = headerCells.findIndex(th => th.textContent.trim() === column);
            }

            let visible = 0;

            rows.forEach((tr, idx) => {
                const rowData = data[idx];
                if (!rowData) { tr.style.display = ''; visible++; return; }

                let show = true;

                if (lowerText) {
                    if (targetColIndex !== -1) {
                        const cells = tr.querySelectorAll('td');
                        const cell = cells[targetColIndex];
                        const cellText = cell ? cell.textContent.toLowerCase() : '';
                        if (!cellText.includes(lowerText)) show = false;
                    } else {
                        const cells = Array.from(tr.querySelectorAll('td'));
                        const startIdx = (headerCells[0] && headerCells[0].textContent.trim() === 'Row') ? 1 : 0;
                        const cellText = cells.slice(startIdx)
                            .map(td => td.textContent.toLowerCase())
                            .join(' ');
                        if (!cellText.includes(lowerText)) show = false;
                    }
                }

                tr.style.display = show ? '' : 'none';
                if (show) visible++;
            });

            this._updateCount(visible, rows.length);
        }

        _applyToData(data) {
            const { column, text } = this._state;
            const lowerText = text.toLowerCase().trim();

            if (!lowerText) return data;

            return data.filter(row => {
                if (column !== 'all') {
                    const normHeader = column.toLowerCase().replace(/[^a-z0-9]/g, '');
                    const targetKey = Object.keys(row).find(k => k.toLowerCase().replace(/[^a-z0-9]/g, '') === normHeader);
                    if (targetKey) {
                        const val = String(row[targetKey] ?? '').toLowerCase();
                        return val.includes(lowerText);
                    }
                    return false;
                } else {
                    const vals = Object.values(row)
                        .map(v => String(v ?? '').toLowerCase())
                        .join(' ');
                    return vals.includes(lowerText);
                }
            });
        }

        _updateCount(visible, total) {
            if (!this._countEl) return;
            if (visible >= total) {
                this._countEl.textContent = `${total} row${total !== 1 ? 's' : ''}`;
                this._countEl.classList.remove('rf-count--filtered');
            } else {
                this._countEl.textContent = `${visible} of ${total} rows`;
                this._countEl.classList.add('rf-count--filtered');
            }
        }
    }

    // Shared global handler for the new select-based download dropdown
    global.handleDownloadSelect = function (selectEl, pageType) {
        const val = selectEl.value;
        if (!val) return;
        
        if (pageType === 'production') {
            if (global.handleSmartDownload) {
                global.handleSmartDownload(val);
            } else if (global.activeResultsFilter) {
                global.activeResultsFilter.download(val);
            }
        } else {
            if (global.downloadTestOutput) {
                global.downloadTestOutput(val);
            } else if (global.activeOnboardingFilter) {
                global.activeOnboardingFilter.download(val);
            }
        }
        
        // Reset back to placeholder (first option) so same option can be chosen again
        selectEl.value = "";
    };

    // Expose globally
    global.ResultsFilter = ResultsFilter;

})(window);
