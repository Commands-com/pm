// Basic modal management for task details and other modals
import { AppState } from './state.js';
import { KnowledgeManagementModal } from './knowledge-modal.js';
import { AssumptionInsightsModal } from './assumption-insights-modal.js';
import { escapeHtml } from './utils.js';

export class TaskDetailModal {
    constructor() {
        this.modal = document.getElementById('taskDetailModal');
        this.currentTask = null;
        this.currentTaskData = null;
        this.raValidations = [];
        this.activeTab = 'overview';
        this.logCursor = null;
        this.filteredLogs = [];
        this.isLoading = false;
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        const closeBtn = document.getElementById('modalCloseBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        // Backdrop click closes modal
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) {
                    this.close();
                }
            });
        }

        // Escape key closes modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal && this.modal.style.display === 'flex') {
                this.close();
            }
        });

        // Tab navigation
        const tabs = document.querySelectorAll('.modal-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Log refresh button
        const logRefreshBtn = document.getElementById('logRefreshBtn');
        if (logRefreshBtn) {
            logRefreshBtn.addEventListener('click', () => {
                this.refreshExecutionLogs();
            });
        }

        // Log type filter
        const logTypeFilter = document.getElementById('logTypeFilter');
        if (logTypeFilter) {
            logTypeFilter.addEventListener('change', (e) => {
                this.filterLogs(e.target.value);
            });
        }

        // Copy prompt button
        const promptCopyBtn = document.getElementById('promptCopyBtn');
        if (promptCopyBtn) {
            promptCopyBtn.addEventListener('click', () => {
                this.copySystemPrompt();
            });
        }
    }

    formatTimestampValue(val) {
        if (!val) return '';
        try {
            let s = String(val).trim();
            s = s.replace(' ', 'T');
            s = s.replace(/(\.\d{3})\d+/, '$1');
            s = s.replace(/([+-]\d{2}:\d{2})Z$/, 'Z');
            let d = new Date(s);
            if (!isNaN(d.getTime())) return d.toLocaleString();
            if (s.endsWith('Z')) {
                d = new Date(s.slice(0, -1));
                if (!isNaN(d.getTime())) return d.toLocaleString();
            }
            return String(val);
        } catch {
            return String(val);
        }
    }

    open(task) {
        this.currentTask = task;
        if (this.modal) {
            this.modal.style.display = 'flex';
            this.loadTaskData(task);
        }
    }

    close() {
        if (this.modal) {
            this.modal.style.display = 'none';
        }
        this.currentTask = null;
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.modal-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });

        this.activeTab = tabName;
    }

    async loadTaskData(task) {
        // Update modal title
        const titleElement = document.getElementById('modalTaskTitle');
        if (titleElement) {
            titleElement.textContent = task.name;
        }

        // Load basic task info in overview tab
        this.loadOverviewTab(task);

        // Fetch detailed task data and RA validations in parallel
        try {
            this.showLoading();

            const [taskResponse, validationsResponse] = await Promise.all([
                fetch('/api/task/details', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        task_id: task.id.toString(),
                        log_limit: 100
                    })
                }),
                // Try to load RA validations (may not exist)
                fetch('/api/assumptions/validations').catch(() => null)
            ]);

            if (taskResponse.ok) {
                const apiResponse = await taskResponse.json();
                this.currentTaskData = JSON.parse(apiResponse.result);

                // Load RA validations if available and filter for this task
                this.raValidations = [];
                if (validationsResponse && validationsResponse.ok) {
                    const validationsResult = await validationsResponse.json();
                    const allValidations = validationsResult.validations || [];
                    this.raValidations = allValidations.filter(v => v.task_id === parseInt(task.id));
                }

                this.populateTaskDetails(this.currentTaskData);
                this.hideLoading();
            } else {
                console.error('Failed to load task details:', taskResponse.statusText);
                this.showErrorInTabs('Failed to load task details');
                this.hideLoading();
            }
        } catch (error) {
            console.error('Error loading task details:', error);
            this.showErrorInTabs('Network error loading task details');
            this.hideLoading();
        }
    }

    loadOverviewTab(task) {
        const descriptionElement = document.getElementById('taskDescription');
        if (descriptionElement) {
            descriptionElement.textContent = task.description || 'No description available';
        }

        // Add basic metrics - note that task here is just the basic task object from card click
        // The detailed metrics will be updated when full task details are fetched
        const metricsElement = document.getElementById('taskMetrics');
        if (metricsElement) {
            metricsElement.innerHTML = `
                <div class="metric-card">
                    <div class="metric-label">Status</div>
                    <div class="metric-value">${task.status}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Complexity</div>
                    <div class="metric-value">${task.ra_score || task.complexity_score || 'N/A'}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Mode</div>
                    <div class="metric-value">${task.ra_mode || task.mode_used || 'N/A'}</div>
                </div>
            `;
        }
    }

    populateTaskDetails(taskDetails) {
        // taskDetails structure: {task, project, epic, dependencies, logs, pagination}
        const task = taskDetails.task || {};

        // Populate RA tags tab
        this.loadRATags(task.ra_tags || []);

        // Populate execution logs tab
        this.loadExecutionLogs(taskDetails.logs || []);

        // Populate system prompt tab
        this.loadSystemPrompt(task.prompt_snapshot || '');

        // Populate dependencies tab
        this.loadDependencies(taskDetails.dependencies || []);

        // Update overview with additional details
        this.updateOverviewDetails(taskDetails);
    }

    async loadRATags(raTags) {
        const container = document.getElementById('raTagsContainer');
        if (!container) return;

        if (raTags.length === 0) {
            container.innerHTML = '<div class="empty-state">No RA tags found for this task.</div>';
            return;
        }

        // Load validation data for this task
        this.raValidations = [];
        try {
            const validationsResponse = await fetch(`/api/assumptions/recent?limit=50`);
            if (validationsResponse.ok) {
                const validationsResult = await validationsResponse.json();
                const allValidations = validationsResult.validations || [];
                // Filter to only include validations for this specific task
                this.raValidations = allValidations.filter(v => v.task_id === parseInt(this.currentTask?.id));
            }
        } catch (error) {
            console.warn('Failed to load validation data:', error);
            this.raValidations = [];
        }

        this.displayRATagsWithValidations(raTags);
    }

    displayRATagsWithValidations(tags) {
        const container = document.getElementById('raTagsContainer');
        if (!container) return;

        // Process tags with validation information
        const processedTags = tags.map(tag => {
            const tagId = tag.id;
            const validation = tagId ? this.findValidationForTag(tagId) : null;

            return {
                ...tag,
                validation: validation,
                status: validation ? validation.outcome : 'pending'
            };
        });

        // Group by validation status
        const statusGroups = {
            validated: processedTags.filter(t => t.status === 'validated'),
            partial: processedTags.filter(t => t.status === 'partial'),
            rejected: processedTags.filter(t => t.status === 'rejected'),
            pending: processedTags.filter(t => t.status === 'pending')
        };

        container.innerHTML = `
            <div class="ra-validation-summary">
                <h4>Validation Summary</h4>
                <div class="validation-counts">
                    <span class="count-item validated">✓ ${statusGroups.validated.length}</span>
                    <span class="count-item partial">△ ${statusGroups.partial.length}</span>
                    <span class="count-item rejected">✗ ${statusGroups.rejected.length}</span>
                    <span class="count-item pending">○ ${statusGroups.pending.length}</span>
                </div>
            </div>
            ${Object.entries(statusGroups).map(([status, statusTags]) =>
                statusTags.length > 0 ? `
                    <div class="ra-tag-status-group">
                        <h5 class="status-group-header ${status}">${status.toUpperCase()} (${statusTags.length})</h5>
                        ${statusTags.map(tagData => this.renderRATagWithValidation(tagData)).join('')}
                    </div>
                ` : ''
            ).join('')}
        `;
    }

    findValidationForTag(tagId) {
        if (!this.raValidations || this.raValidations.length === 0) return null;

        // Find validation that matches this exact tag ID
        return this.raValidations.find(validation =>
            validation.ra_tag_id === tagId
        );
    }

    renderRATagWithValidation(tagData) {
        const validation = tagData.validation;
        const tagType = tagData.type || tagData.ra_tag_type || 'UNKNOWN';
        const tagText = tagData.text || tagData.ra_tag_text || '';
        const ts = tagData.created_at ? this.formatTimestampValue(tagData.created_at) : '';

        const statusClass = validation ? validation.outcome : 'pending';

        return `
            <div class="ra-tag-item">
                <div class="ra-tag-header">
                    <div class="ra-tag-name">${escapeHtml(tagType)}</div>
                    <span class="validation-status-badge ${statusClass}">
                        ${validation ? validation.outcome : 'pending'}
                    </span>
                </div>
                <div class="ra-tag-description">${escapeHtml(tagText)}</div>
                ${ts ? `<div class="ra-tag-timestamp" style="color:#64748b;font-size:0.75rem;margin-top:0.25rem;">${ts}</div>` : ''}

                ${validation ? `
                    <div class="validation-details">
                        <div class="validation-summary">
                            <div class="validation-row">
                                <span class="validation-label">Confidence:</span>
                                <span class="confidence-badge">${validation.confidence}%</span>
                            </div>
                            <div class="validation-row">
                                <span class="validation-label">Reviewed by:</span>
                                <span class="validator-name">${validation.validator_id.replace('mcp-reviewer-agent', 'MCP Reviewer').replace('-', ' ')}</span>
                            </div>
                            <div class="validation-row">
                                <span class="validation-label">Date:</span>
                                <span class="validation-date">${this.formatTimestampValue(validation.validated_at)}</span>
                            </div>
                        </div>
                        <div class="validation-reasoning">
                            <div class="reason-label">Validation Notes:</div>
                            <div class="reason-text">${escapeHtml(validation.notes || 'No reason provided')}</div>
                        </div>
                    </div>
                ` : `
                    <div class="validation-details pending">
                        <div class="validation-reasoning">
                            <div class="reason-text">
                                <em>No validation performed yet</em>
                            </div>
                        </div>
                    </div>
                `}
            </div>
        `;
    }

    loadExecutionLogs(logs) {
        if (!logs) {
            logs = [];
        }

        // Initialize filtered logs with all logs
        this.filteredLogs = [...logs];

        // Apply current filter if any
        const logTypeFilter = document.getElementById('logTypeFilter');
        if (logTypeFilter && logTypeFilter.value && logTypeFilter.value !== 'all') {
            this.filterLogs(logTypeFilter.value);
        } else {
            this.displayFilteredLogs();
        }
    }

    loadSystemPrompt(promptSnapshot) {
        const container = document.getElementById('systemPromptContent');
        if (!container) return;

        if (!promptSnapshot) {
            container.textContent = 'No system prompt snapshot available.';
            return;
        }

        container.textContent = promptSnapshot;
    }

    loadDependencies(dependencies) {
        const container = document.getElementById('dependenciesContainer');
        const totalCount = document.getElementById('totalDepsCount');
        const completedCount = document.getElementById('completedDepsCount');
        const pendingCount = document.getElementById('pendingDepsCount');

        if (!container) return;

        // Update counters
        const completed = dependencies.filter(dep => dep.status === 'completed' || dep.status === 'DONE').length;
        const pending = dependencies.length - completed;

        if (totalCount) totalCount.textContent = dependencies.length;
        if (completedCount) completedCount.textContent = completed;
        if (pendingCount) pendingCount.textContent = pending;

        if (dependencies.length === 0) {
            container.innerHTML = '<div class="empty-state">No dependencies for this task.</div>';
            return;
        }

        container.innerHTML = dependencies.map(dep => `
            <div class="dependency-item">
                <div class="dependency-header">
                    <span class="dependency-name">${dep.name}</span>
                    <span class="dependency-status status-${dep.status.toLowerCase()}">${dep.status}</span>
                </div>
                <div class="dependency-id">Task ID: ${dep.id}</div>
            </div>
        `).join('');
    }

    updateOverviewDetails(taskDetails) {
        const task = taskDetails.task || {};
        const project = taskDetails.project || {};
        const epic = taskDetails.epic || {};

        const formatTS = (val) => this.formatTimestampValue(val) || 'N/A';

        // Update breadcrumb
        const breadcrumbElement = document.getElementById('taskBreadcrumb');
        if (breadcrumbElement && project.name && epic.name) {
            breadcrumbElement.innerHTML = `
                <span class="breadcrumb-project">${project.name}</span>
                <span class="breadcrumb-separator">→</span>
                <span class="breadcrumb-epic">${epic.name}</span>
            `;
        }

        // Update timestamps
        const timestampsElement = document.getElementById('taskTimestamps');
        if (timestampsElement) {
            timestampsElement.innerHTML = `
                <div class="timestamp-item">
                    <span class="timestamp-label">Created:</span>
                    <span class="timestamp-value">${formatTS(task.created_at)}</span>
                </div>
                <div class="timestamp-item">
                    <span class="timestamp-label">Updated:</span>
                    <span class="timestamp-value">${formatTS(task.updated_at)}</span>
                </div>
            `;
        }

        // Update status info
        const statusElement = document.getElementById('taskStatusInfo');
        if (statusElement) {
            statusElement.innerHTML = `
                <div class="status-item">
                    <span class="status-label">Lock Status:</span>
                    <span class="status-value">${task.lock_holder ? 'Locked' : 'Unlocked'}</span>
                </div>
                ${task.lock_holder ? `
                <div class="status-item">
                    <span class="status-label">Locked By:</span>
                    <span class="status-value">${task.lock_holder}</span>
                </div>
                ` : ''}
            `;
        }

        // Update metrics with detailed task data
        const metricsElement = document.getElementById('taskMetrics');
        if (metricsElement && task) {
            metricsElement.innerHTML = `
                <div class="metric-card">
                    <div class="metric-label">Status</div>
                    <div class="metric-value">${task.status}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Complexity</div>
                    <div class="metric-value">${task.ra_score || 'N/A'}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Mode</div>
                    <div class="metric-value">${task.ra_mode || 'N/A'}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">RA Tags</div>
                    <div class="metric-value">${task.ra_tags ? task.ra_tags.length : 0}</div>
                </div>
            `;
        }
    }

    showErrorInTabs(errorMessage) {
        // Show error in all loading tabs
        const containers = [
            'raTagsContainer',
            'executionLogContainer',
            'dependenciesContainer'
        ];

        containers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = `<div class="error-state">Error: ${errorMessage}</div>`;
            }
        });

        const promptContainer = document.getElementById('systemPromptContent');
        if (promptContainer) {
            promptContainer.textContent = `Error: ${errorMessage}`;
        }
    }

    async refreshExecutionLogs() {
        if (!this.currentTask) return;

        try {
            this.showLoading();
            await this.loadTaskData(this.currentTask);
        } catch (error) {
            console.error('Failed to refresh logs:', error);
            this.showErrorInTabs('Failed to refresh execution logs');
        }
    }

    filterLogs(filterValue) {
        if (!this.currentTaskData || !this.currentTaskData.logs) return;

        const logs = this.currentTaskData.logs;

        if (filterValue === '' || filterValue === 'all') {
            this.filteredLogs = [...logs];
        } else {
            this.filteredLogs = logs.filter(log => {
                const logType = log.kind || log.type || 'update';
                return logType === filterValue;
            });
        }

        this.displayFilteredLogs();
    }

    displayFilteredLogs() {
        const container = document.getElementById('executionLogContainer');
        if (!container) return;

        if (this.filteredLogs.length === 0) {
            container.innerHTML = '<div class="empty-state">No execution logs match the current filter.</div>';
            return;
        }

        container.innerHTML = this.filteredLogs.map(log => {
            const logType = log.kind || log.type || 'update';
            const timestamp = this.formatTimestampValue(log.ts || log.timestamp || log.created_at);

            // Build content from payload or fallback fields
            let content = '';
            const payload = log.payload;
            if (payload) {
                if (typeof payload === 'string') {
                    content = payload;
                } else if (typeof payload === 'object') {
                    if (payload.agent_action) {
                        content = `Action: ${payload.agent_action}`;
                        const p = payload.original_parameters || {};
                        if (p.name) content += ` - Task: ${p.name}`;
                        if (p.ra_mode) content += ` (${p.ra_mode})`;
                        if (p.ra_score) content += ` [Score: ${p.ra_score}]`;
                    } else if (payload.prompt_snapshot) {
                        content = 'System prompt snapshot captured';
                    } else if (payload.log_entry) {
                        content = payload.log_entry;
                    } else if (payload.message) {
                        content = payload.message;
                    } else {
                        try { content = JSON.stringify(payload, null, 2); } catch { content = String(payload); }
                    }
                }
            }
            if (!content) {
                content = log.content || log.message || log.log_entry || 'No content';
            }

            return `
                <div class="log-entry ${logType}">
                    <div class="log-entry-header">
                        <span class="log-entry-type ${logType}">${logType}</span>
                        <span class="log-entry-timestamp">${timestamp}</span>
                    </div>
                    <div class="log-entry-content">${escapeHtml(content)}</div>
                </div>
            `;
        }).join('');
    }

    copySystemPrompt() {
        const contentElement = document.getElementById('systemPromptContent');
        if (contentElement && contentElement.textContent.trim()) {
            navigator.clipboard.writeText(contentElement.textContent).then(() => {
                this.showNotification('System prompt copied to clipboard', 'success');
            }).catch((error) => {
                console.error('Failed to copy prompt:', error);
                this.showNotification('Failed to copy prompt', 'error');
            });
        } else {
            this.showNotification('No prompt to copy', 'info');
        }
    }

    showLoading() {
        const loadingElement = document.getElementById('modalLoading');
        if (loadingElement) {
            loadingElement.style.display = 'flex';
        }
        this.isLoading = true;
    }

    hideLoading() {
        const loadingElement = document.getElementById('modalLoading');
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
        this.isLoading = false;
    }

    showNotification(message, type = 'info') {
        // Simple notification - could be enhanced with a proper notification system
        console.log(`[${type.toUpperCase()}] ${message}`);

        // Try to use global notification function if available
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type);
        }
    }

    // Missing methods from original implementation
    loadMoreLogs() {
        if (!this.currentTask) return;

        try {
            // Increment log limit and reload task data
            this.logCursor = this.currentTaskData?.logs?.length || 0;
            this.loadTaskData(this.currentTask);
        } catch (error) {
            console.error('Failed to load more logs:', error);
            this.showNotification('Failed to load more logs', 'error');
        }
    }

    openDependencyTask(depId) {
        if (!depId) return;

        // Find the dependency task and open its modal
        const dependencyTask = AppState.tasks.get(String(depId));
        if (dependencyTask) {
            this.open(dependencyTask);
        } else {
            this.showNotification('Dependency task not found', 'error');
        }
    }
}

// Use the full KnowledgeManagementModal implementation
export { KnowledgeManagementModal as KnowledgeModal };

// Initialize modals when DOM is ready
export function initializeModals() {
    window.taskDetailModal = new TaskDetailModal();
    window.knowledgeModal = new KnowledgeManagementModal();
    window.assumptionInsightsModal = new AssumptionInsightsModal();
    // Helper for modules that reference a global opener (parity with original)
    window.openTaskDetailModal = function(task) {
        if (window.taskDetailModal && task) {
            window.taskDetailModal.open(task);
        }
    };
}
