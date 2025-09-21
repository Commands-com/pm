// Assumption Insights Modal - Analytics Dashboard for RA Tag Validation
import { showNotification } from './utils.js';

export class AssumptionInsightsModal {
    constructor() {
        this.modal = document.getElementById('assumptionInsightsModal');
        this.drawer = document.getElementById('assumption-detail-drawer');
        this.isLoading = false;
        this.cache = {
            projects: null,
            epics: null,
            insights: null,
            recent: null
        };
        this.filters = {
            project_id: null,
            epic_id: null,
            tag_type: null,
            outcome: null,
            start_date: null,
            end_date: null
        };

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Close modal handlers
        const closeBtn = document.getElementById('assumptionModalCloseBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        // Modal backdrop click
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) {
                    this.close();
                }
            });
        }

        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal && this.modal.style.display === 'flex') {
                this.close();
            }
        });

        // Setup filter change handlers
        this.setupFilterHandlers();

        // Setup drawer close
        const drawerCloseBtn = document.querySelector('.drawer-close-btn');
        if (drawerCloseBtn) {
            drawerCloseBtn.addEventListener('click', () => this.closeDrawer());
        }

        // Event delegation for modal body
        const modalBody = this.modal.querySelector('.assumption-modal-body');
        if (modalBody) {
            modalBody.addEventListener('click', (e) => {
                const row = e.target.closest('.table-row-clickable');
                const taskLink = e.target.closest('.task-link');
                const retryBtn = e.target.closest('.retry-btn');

                if (row) {
                    const tagType = row.dataset.tagType;
                    const validationId = row.dataset.validationId;
                    if (tagType) {
                        this.openTagDetails(tagType);
                    } else if (validationId) {
                        this.openValidationDetails(validationId);
                    }
                } else if (taskLink) {
                    e.preventDefault();
                    const taskId = taskLink.dataset.taskId;
                    const taskName = taskLink.dataset.taskName;
                    if (taskId && taskName && window.openTaskDetailModal) {
                        window.openTaskDetailModal({ id: taskId, name: taskName });
                    }
                } else if (retryBtn) {
                    this.open();
                }
            });
        }
    }

    setupFilterHandlers() {
        const filterIds = [
            'assumption-project-select',
            'assumption-epic-select',
            'assumption-tag-type-select',
            'assumption-outcome-select',
            'assumption-start-date',
            'assumption-end-date'
        ];

        filterIds.forEach(filterId => {
            const element = document.getElementById(filterId);
            if (element) {
                element.addEventListener('change', () => this.applyFilters());
            }
        });
    }

    async open() {
        try {
            this.showGlobalLoading();

            if (this.modal) {
                this.modal.style.display = 'flex';
            }

            // Load all data in parallel
            await Promise.all([
                this.loadProjects(),
                this.loadEpics(),
                this.loadInsights(),
                this.loadRecentValidations()
            ]);

            // Render the base UI structure, then populate content
            this.renderContent();
            this.populateFilters();
            // Re-bind filter handlers to newly rendered elements
            this.setupFilterHandlers();
            this.renderKPICards();
            this.renderDataTables();

            this.hideGlobalLoading();

        } catch (error) {
            console.error('Error opening assumption insights modal:', error);
            this.showError('Failed to load assumption insights. Please try again.');
            this.hideGlobalLoading();
        }
    }

    close() {
        if (this.modal) {
            this.modal.style.display = 'none';
        }
        this.closeDrawer();
    }

    showGlobalLoading() {
        // Non-destructive: add or update a loading overlay without removing base structure
        const body = document.querySelector('.assumption-modal-body');
        if (body) {
            const existing = body.querySelector('.assumption-loading');
            const overlay = existing || document.createElement('div');
            overlay.className = 'assumption-loading';
            overlay.innerHTML = `
                <div class="spinner"></div>
                <span>Loading assumption insights...</span>
            `;
            if (!existing) body.appendChild(overlay);
        }
        this.isLoading = true;
    }

    hideGlobalLoading() {
        this.isLoading = false;
        const body = document.querySelector('.assumption-modal-body');
        const loading = body?.querySelector('.assumption-loading');
        if (loading) loading.remove();
    }

    showError(message) {
        const body = document.querySelector('.assumption-modal-body');
        if (body) {
            body.innerHTML = `
                <div class="assumption-empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <h3 class="empty-state-title">Error Loading Data</h3>
                    <p class="empty-state-message">${message}</p>
                    <button class="retry-btn">Retry</button>
                </div>
            `;
        }
    }

    async loadProjects() {
        if (this.cache.projects) return this.cache.projects;

        try {
            const response = await fetch('/api/projects');
            if (!response.ok) throw new Error(`Projects API error: ${response.status}`);

            const result = await response.json();
            this.cache.projects = Array.isArray(result) ? result : (result.projects || []);
            return this.cache.projects;
        } catch (error) {
            console.error('Error loading projects:', error);
            this.cache.projects = [];
            return [];
        }
    }

    async loadEpics() {
        if (this.cache.epics) return this.cache.epics;

        try {
            const response = await fetch('/api/epics');
            if (!response.ok) throw new Error(`Epics API error: ${response.status}`);

            const result = await response.json();
            this.cache.epics = Array.isArray(result) ? result : (result.epics || []);
            return this.cache.epics;
        } catch (error) {
            console.error('Error loading epics:', error);
            this.cache.epics = [];
            return [];
        }
    }

    async loadInsights() {
        try {
            // Build query params from current filters
            const params = new URLSearchParams();
            if (this.filters.project_id) params.append('project_id', this.filters.project_id);
            if (this.filters.epic_id) params.append('epic_id', this.filters.epic_id);
            if (this.filters.start_date) params.append('start_date', this.filters.start_date);
            if (this.filters.end_date) params.append('end_date', this.filters.end_date);

            // Note: This API endpoint may not exist yet - would need to be implemented
            const response = await fetch(`/api/assumptions/insights?${params.toString()}`);
            if (!response.ok) {
                // If API doesn't exist, create mock data
                this.cache.insights = this.generateMockInsights();
                return this.cache.insights;
            }

            const result = await response.json();
            this.cache.insights = result;
            return this.cache.insights;
        } catch (error) {
            console.error('Error loading insights:', error);
            // Generate mock data for demo purposes
            this.cache.insights = this.generateMockInsights();
            return this.cache.insights;
        }
    }

    async loadRecentValidations() {
        try {
            // Build query params from current filters
            const params = new URLSearchParams();
            params.append('limit', '50'); // Recent 50 validations
            if (this.filters.project_id) params.append('project_id', this.filters.project_id);
            if (this.filters.epic_id) params.append('epic_id', this.filters.epic_id);

            // Use the correct working endpoint from the original implementation
            const response = await fetch(`/api/assumptions/recent?${params.toString()}`);
            if (!response.ok) {
                this.cache.recent = this.generateMockRecentValidations();
                return this.cache.recent;
            }

            const result = await response.json();
            this.cache.recent = result.validations || [];
            return this.cache.recent;
        } catch (error) {
            console.error('Error loading recent validations:', error);
            this.cache.recent = this.generateMockRecentValidations();
            return this.cache.recent;
        }
    }

    generateMockInsights() {
        return {
            summary: {
                total_tags: 156,
                validated: 89,
                rejected: 23,
                partial: 44,
                success_rate: 68.3
            },
            by_type: [
                { tag_type: 'COMPLETION_DRIVE_IMPL', total: 45, validated: 32, rejected: 8, partial: 5, success_rate: 82.2 },
                { tag_type: 'SUGGEST_ERROR_HANDLING', total: 34, validated: 19, rejected: 6, partial: 9, success_rate: 82.4 },
                { tag_type: 'PATTERN_MOMENTUM', total: 28, validated: 15, rejected: 4, partial: 9, success_rate: 85.7 },
                { tag_type: 'CONTEXT_DEGRADED', total: 22, validated: 12, rejected: 3, partial: 7, success_rate: 86.4 },
                { tag_type: 'SUGGEST_VALIDATION', total: 18, validated: 8, rejected: 2, partial: 8, success_rate: 88.9 },
                { tag_type: 'CARGO_CULT', total: 9, validated: 3, rejected: 0, partial: 6, success_rate: 100.0 }
            ],
            trends: {
                weekly_validations: [12, 18, 15, 22, 19, 25, 28],
                weekly_success_rates: [65.2, 70.1, 68.9, 75.3, 72.8, 78.2, 82.1]
            }
        };
    }

    generateMockRecentValidations() {
        const outcomes = ['validated', 'rejected', 'partial'];
        const tagTypes = ['COMPLETION_DRIVE_IMPL', 'SUGGEST_ERROR_HANDLING', 'PATTERN_MOMENTUM', 'CONTEXT_DEGRADED'];
        const reasons = [
            'Implementation matched requirements exactly',
            'Edge case not properly handled',
            'Pattern applied correctly but incomplete',
            'Assumption proved incorrect during testing',
            'Validation successful with minor adjustments'
        ];

        return Array.from({ length: 25 }, (_, i) => ({
            id: i + 1,
            task_id: Math.floor(Math.random() * 50) + 1,
            task_name: `Task ${Math.floor(Math.random() * 50) + 1}`,
            ra_tag_id: `ra_tag_${Math.random().toString(36).substr(2, 9)}`,
            ra_tag_text: `#${tagTypes[Math.floor(Math.random() * tagTypes.length)]}: Mock assumption ${i + 1}`,
            outcome: outcomes[Math.floor(Math.random() * outcomes.length)],
            reason: reasons[Math.floor(Math.random() * reasons.length)],
            confidence: Math.floor(Math.random() * 30) + 70,
            created_at: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
            reviewer_agent_id: 'claude'
        }));
    }

    populateFilters() {
        // Populate project filter
        const projectSelect = document.getElementById('assumption-project-select');
        if (projectSelect && this.cache.projects) {
            projectSelect.innerHTML = '<option value="">All Projects</option>';
            this.cache.projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.id;
                option.textContent = project.name;
                projectSelect.appendChild(option);
            });
        }

        // Populate epic filter
        const epicSelect = document.getElementById('assumption-epic-select');
        if (epicSelect && this.cache.epics) {
            epicSelect.innerHTML = '<option value="">All Epics</option>';
            this.cache.epics.forEach(epic => {
                const option = document.createElement('option');
                option.value = epic.id;
                option.textContent = epic.name;
                epicSelect.appendChild(option);
            });
        }

        // Set default date range (last 30 days)
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - 30);

        const startDateInput = document.getElementById('assumption-start-date');
        const endDateInput = document.getElementById('assumption-end-date');

        if (startDateInput) {
            startDateInput.value = startDate.toISOString().split('T')[0];
        }
        if (endDateInput) {
            endDateInput.value = endDate.toISOString().split('T')[0];
        }
    }

    renderContent() {
        const body = document.querySelector('.assumption-modal-body');
        if (!body) return;

        body.innerHTML = `
            <div class="assumption-filters-section">
                ${this.renderFilters()}
            </div>
            <div class="assumption-kpi-cards">
                ${this.renderKPICards()}
            </div>
            <div class="assumption-data-section">
                ${this.renderDataTables()}
            </div>
        `;
    }

    renderFilters() {
        return `
            <div class="assumption-filter-group">
                <label for="assumption-project-select" class="assumption-filter-label">Project</label>
                <select id="assumption-project-select" class="assumption-filter-select">
                    <option value="">All Projects</option>
                </select>
            </div>
            <div class="assumption-filter-group">
                <label for="assumption-epic-select" class="assumption-filter-label">Epic</label>
                <select id="assumption-epic-select" class="assumption-filter-select">
                    <option value="">All Epics</option>
                </select>
            </div>
            <div class="assumption-filter-group">
                <label for="assumption-tag-type-select" class="assumption-filter-label">Tag Type</label>
                <select id="assumption-tag-type-select" class="assumption-filter-select">
                    <option value="">All Types</option>
                    <option value="COMPLETION_DRIVE_IMPL">Implementation</option>
                    <option value="SUGGEST_ERROR_HANDLING">Error Handling</option>
                    <option value="PATTERN_MOMENTUM">Patterns</option>
                    <option value="CONTEXT_DEGRADED">Context Issues</option>
                </select>
            </div>
            <div class="assumption-filter-group">
                <label for="assumption-outcome-select" class="assumption-filter-label">Outcome</label>
                <select id="assumption-outcome-select" class="assumption-filter-select">
                    <option value="">All Outcomes</option>
                    <option value="validated">Validated</option>
                    <option value="rejected">Rejected</option>
                    <option value="partial">Partial</option>
                </select>
            </div>
            <div class="assumption-filter-group">
                <label class="assumption-filter-label">Date Range</label>
                <div class="date-range-inputs">
                    <input type="date" id="assumption-start-date" class="date-input">
                    <input type="date" id="assumption-end-date" class="date-input">
                </div>
            </div>
        `;
    }

    renderKPICards() {
        if (!this.cache.insights) return '';

        const insights = this.cache.insights;
        const total = insights.total_validations || 0;
        const validated = (insights.outcome_breakdown && insights.outcome_breakdown.validated) || 0;
        const partial = (insights.outcome_breakdown && insights.outcome_breakdown.partial) || 0;
        const successRatePct = ((insights.success_rate || 0) * 100).toFixed(1);

        const kpiContainer = document.querySelector('.assumption-kpi-cards');
        if (kpiContainer) {
            kpiContainer.innerHTML = `
                <div class="assumption-kpi-card">
                    <div class="kpi-card-header">
                        <div class="kpi-card-icon total">📊</div>
                        <h3 class="kpi-card-title">Total Validations</h3>
                    </div>
                    <div class="kpi-card-value">${total}</div>
                    <div class="kpi-card-subtitle">Across selected scope</div>
                </div>
                <div class="assumption-kpi-card">
                    <div class="kpi-card-header">
                        <div class="kpi-card-icon success">✅</div>
                        <h3 class="kpi-card-title">Validated</h3>
                    </div>
                    <div class="kpi-card-value">${validated}</div>
                    <div class="kpi-card-subtitle">${total ? ((validated / total) * 100).toFixed(1) : '0.0'}% of total</div>
                </div>
                <div class="assumption-kpi-card">
                    <div class="kpi-card-header">
                        <div class="kpi-card-icon partial">⚠️</div>
                        <h3 class="kpi-card-title">Partially Valid</h3>
                    </div>
                    <div class="kpi-card-value">${partial}</div>
                    <div class="kpi-card-subtitle">${total ? ((partial / total) * 100).toFixed(1) : '0.0'}% of total</div>
                </div>
                <div class="assumption-kpi-card">
                    <div class="kpi-card-header">
                        <div class="kpi-card-icon success">📈</div>
                        <h3 class="kpi-card-title">Success Rate</h3>
                    </div>
                    <div class="kpi-card-value">${successRatePct}%</div>
                    <div class="kpi-card-subtitle">Validated + 0.5 * Partial</div>
                </div>
            `;
        }
    }

    renderDataTables() {
        const dataContainer = document.querySelector('.assumption-data-section');
        if (!dataContainer) return;

        dataContainer.innerHTML = `
            <div class="data-section-header">
                <h3 class="data-section-title">Tag Type Analysis</h3>
            </div>
            <table class="assumption-data-table" id="tag-types-table">
                <thead>
                    <tr>
                        <th>Tag Type</th>
                        <th>Total</th>
                        <th>Success Rate</th>
                        <th>Validation Results</th>
                    </tr>
                </thead>
                <tbody>
                    ${this.renderTagTypeRows()}
                </tbody>
            </table>

            <div class="data-section-header" style="margin-top: 2rem;">
                <h3 class="data-section-title">Recent Validations</h3>
            </div>
            <table class="assumption-data-table" id="recent-validations-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Task</th>
                        <th>RA Tag</th>
                        <th>Outcome</th>
                        <th>Confidence</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody>
                    ${this.renderRecentValidationRows()}
                </tbody>
            </table>
        `;
    }

    renderTagTypeRows() {
        if (!this.cache.insights || !this.cache.insights.tag_type_breakdown) return '';

        const rows = [];
        for (const [type, count] of Object.entries(this.cache.insights.tag_type_breakdown)) {
            rows.push(`
                <tr class="table-row-clickable" data-tag-type="${type}">
                    <td class="tag-type-cell">${type}</td>
                    <td>${count}</td>
                    <td class="success-rate-cell">
                        <span class="success-rate-badge">N/A</span>
                    </td>
                    <td>
                        <div class="validation-counts">
                            <span class="count-badge validated">—</span>
                            <span class="count-badge partial">—</span>
                            <span class="count-badge rejected">—</span>
                        </div>
                    </td>
                </tr>
            `);
        }
        return rows.join('');
    }

    renderRecentValidationRows() {
        if (!this.cache.recent) return '';

        return this.cache.recent.slice(0, 10).map(validation => `
            <tr class="table-row-clickable" data-validation-id="${validation.id}">
                <td class="timestamp-cell">${this.formatTimestamp(validation.validated_at)}</td>
                <td>
                    ${validation.task_name ? `<a href="#" data-task-id="${validation.task_id}" data-task-name="${validation.task_name.replace(/'/g, "\\'")}" class="task-link">${validation.task_name}</a>` : 'N/A'}
                </td>
                <td class="tag-type-cell">${validation.ra_tag || validation.ra_tag_type || 'UNKNOWN'}</td>
                <td>
                    <span class="outcome-badge ${validation.outcome}">${validation.outcome}</span>
                </td>
                <td>${validation.confidence}%</td>
                <td class="reason-preview">${validation.notes || ''}</td>
            </tr>
        `).join('');
    }

    getSuccessRateClass(rate) {
        if (rate >= 80) return 'high';
        if (rate >= 60) return 'medium';
        return 'low';
    }

    extractTagType(tagText) {
        const match = tagText.match(/#([A-Z_]+):/);
        return match ? match[1] : 'UNKNOWN';
    }

    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        try {
            const date = new Date(timestamp);
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return 'Invalid Date';
        }
    }

    async applyFilters() {
        // Update filters from form
        this.filters.project_id = document.getElementById('assumption-project-select')?.value || null;
        this.filters.epic_id = document.getElementById('assumption-epic-select')?.value || null;
        this.filters.tag_type = document.getElementById('assumption-tag-type-select')?.value || null;
        this.filters.outcome = document.getElementById('assumption-outcome-select')?.value || null;
        this.filters.start_date = document.getElementById('assumption-start-date')?.value || null;
        this.filters.end_date = document.getElementById('assumption-end-date')?.value || null;

        // Clear cache and reload data
        this.cache.insights = null;
        this.cache.recent = null;

        // Reload with filters
        await Promise.all([
            this.loadInsights(),
            this.loadRecentValidations()
        ]);

        this.renderKPICards();
        this.renderDataTables();
    }

    async openTagDetails(tagType) {
        try {
            this.showDrawerLoading();
            this.openDrawer(tagType);

            // Load tag-specific data
            const params = new URLSearchParams();
            params.append('tag_type', tagType);
            if (this.filters.project_id) params.append('project_id', this.filters.project_id);
            if (this.filters.epic_id) params.append('epic_id', this.filters.epic_id);
            if (this.filters.start_date) params.append('start_date', this.filters.start_date);
            if (this.filters.end_date) params.append('end_date', this.filters.end_date);

            const response = await fetch(`/api/assumptions/tag-details?${params.toString()}`);
            if (!response.ok) throw new Error(`Tag details API error: ${response.status}`);

            const data = await response.json();
            this.updateDrawerContent(tagType, data);
            this.hideDrawerLoading();
        } catch (error) {
            console.error('Error loading tag details:', error);
            this.showDrawerError('Failed to load tag details.');
            this.hideDrawerLoading();
        }
    }

    openValidationDetails(validationId) {
        console.log('Opening validation details for:', validationId);
        // Could open a drawer with full validation details
        showNotification(`Validation details for ID ${validationId} - feature coming soon`, 'info');
    }

    openDrawer(tagType) {
        const title = document.getElementById('drawer-tag-title');
        const subtitle = document.getElementById('drawer-tag-subtitle');

        if (title) title.textContent = tagType;
        if (subtitle) subtitle.textContent = 'Loading validation data...';

        if (this.drawer) {
            this.drawer.classList.add('open');
        }
    }

    closeDrawer() {
        if (this.drawer) {
            this.drawer.classList.remove('open');
        }
    }

    showDrawerLoading() {
        const metricsContent = document.getElementById('drawer-metrics-content');
        const historyContent = document.getElementById('drawer-history-content');
        const reasonsContent = document.getElementById('drawer-reasons-content');

        if (metricsContent) metricsContent.innerHTML = '<div class="drawer-loading">Loading metrics...</div>';
        if (historyContent) historyContent.innerHTML = '<div class="drawer-loading">Loading history...</div>';
        if (reasonsContent) reasonsContent.innerHTML = '<div class="drawer-loading">Loading reasons...</div>';
    }

    hideDrawerLoading() {
        // Loading is hidden when content is updated
    }

    showDrawerError(message) {
        const metricsContent = document.getElementById('drawer-metrics-content');
        const historyContent = document.getElementById('drawer-history-content');
        const reasonsContent = document.getElementById('drawer-reasons-content');

        const errorHtml = `<div class="drawer-error">${message}</div>`;
        if (metricsContent) metricsContent.innerHTML = errorHtml;
        if (historyContent) historyContent.innerHTML = errorHtml;
        if (reasonsContent) reasonsContent.innerHTML = errorHtml;
    }

    updateDrawerContent(tagType, data) {
        const subtitle = document.getElementById('drawer-tag-subtitle');
        if (subtitle) {
            subtitle.textContent = `${data.validations?.length || 0} validations found`;
        }

        this.updateDrawerMetrics(data);
        this.updateDrawerHistory(data);
        this.updateDrawerReasons(data);
    }

    updateDrawerMetrics(data) {
        const metricsContent = document.getElementById('drawer-metrics-content');
        if (!metricsContent) return;

        const metrics = data.metrics || {};
        const successRate = ((metrics.success_rate || 0) * 100).toFixed(1);
        const total = metrics.total_validations || 0;
        const validated = metrics.validated_count || 0;
        const rejected = metrics.rejected_count || 0;
        const partial = metrics.partial_count || 0;

        metricsContent.innerHTML = `
            <div class="drawer-metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">${successRate}%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${total}</div>
                    <div class="metric-label">Total Validations</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${validated}</div>
                    <div class="metric-label">Validated</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${rejected}</div>
                    <div class="metric-label">Rejected</div>
                </div>
            </div>
        `;
    }

    updateDrawerHistory(data) {
        const historyContent = document.getElementById('drawer-history-content');
        if (!historyContent) return;

        const validations = data.validations || [];
        if (validations.length === 0) {
            historyContent.innerHTML = '<div class="drawer-empty">No validation history found.</div>';
            return;
        }

        const historyHtml = validations.slice(0, 10).map(validation => `
            <div class="validation-history-item">
                <div class="validation-history-header">
                    <span class="outcome-badge ${validation.outcome}">${validation.outcome}</span>
                    <span class="validation-date">${this.formatTimestamp(validation.created_at)}</span>
                </div>
                <div class="validation-reason">${validation.reason || 'No reason provided'}</div>
                ${validation.task_name ? `<div class="validation-task">Task: ${validation.task_name}</div>` : ''}
            </div>
        `).join('');

        historyContent.innerHTML = historyHtml;
    }

    updateDrawerReasons(data) {
        const reasonsContent = document.getElementById('drawer-reasons-content');
        if (!reasonsContent) return;

        const reasons = data.common_reasons || [];
        if (reasons.length === 0) {
            reasonsContent.innerHTML = '<div class="drawer-empty">No common reasons found.</div>';
            return;
        }

        const reasonsHtml = reasons.map(reason => `
            <div class="common-reason-item">
                <div class="reason-text">${reason.reason}</div>
                <div class="reason-count">${reason.count} time${reason.count !== 1 ? 's' : ''}</div>
            </div>
        `).join('');

        reasonsContent.innerHTML = reasonsHtml;
    }
}
