/**
 * MultiModelGrid Component
 * Responsive grid for side-by-side model validation comparison
 *
 * Features:
 * - Side-by-side comparison of model validations
 * - Consensus indicator with visual progress bar
 * - Model information cards with confidence scores
 * - Real-time updates via WebSocket integration
 * - Responsive grid layout for mobile and desktop
 * - Performance optimized for 10+ model validations
 */

class MultiModelGrid {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.options = {
            taskId: null,
            raTagId: null,
            showConsensus: true,
            autoRefresh: true,
            enableWebSocket: true,
            columns: {
                mobile: 1,
                tablet: 2,
                desktop: 3
            },
            animationDuration: 300,
            ...options
        };

        this.data = {
            consensus: null,
            validations: [],
            modelCount: 0,
            cached: false,
            generatedAt: null
        };

        this.state = {
            loading: false,
            error: null,
            sortBy: 'created_at', // created_at, confidence, outcome
            sortOrder: 'desc', // asc, desc
            filterByOutcome: null // null, validated, rejected, partial
        };

        this.consensusIndicator = null;
        this.websocketListeners = [];

        this.init();
    }

    init() {
        this.render();
        this.setupEventListeners();

        if (this.options.enableWebSocket) {
            this.setupWebSocketListeners();
        }

        if (this.options.taskId && this.options.raTagId) {
            this.loadData();
        }
    }

    render() {
        this.container.innerHTML = `
            <div class="multi-model-grid" data-loading="${this.state.loading}">
                <!-- Header with consensus and controls -->
                <div class="multi-model-header">
                    ${this.options.showConsensus ? this.renderConsensusSection() : ''}
                    <div class="multi-model-controls">
                        ${this.renderControls()}
                    </div>
                </div>

                <!-- Loading state -->
                <div class="multi-model-loading" style="display: ${this.state.loading ? 'block' : 'none'};">
                    <div class="loading-spinner"></div>
                    <span>Loading model validations...</span>
                </div>

                <!-- Error state -->
                <div class="multi-model-error" style="display: ${this.state.error ? 'block' : 'none'};">
                    <div class="error-icon">⚠️</div>
                    <span class="error-message">${this.state.error || ''}</span>
                    <button class="error-retry-btn" onclick="this.parentElement.parentElement.multiModelGrid.loadData()">
                        Retry
                    </button>
                </div>

                <!-- Validations grid -->
                <div class="multi-model-validations">
                    ${this.renderValidations()}
                </div>

                <!-- Empty state -->
                <div class="multi-model-empty" style="display: ${!this.state.loading && !this.state.error && this.data.validations.length === 0 ? 'block' : 'none'};">
                    <div class="empty-icon">🤖</div>
                    <h3>No Model Validations Yet</h3>
                    <p>This RA tag hasn't been validated by any models yet.</p>
                </div>
            </div>
        `;

        // Store reference for event handlers
        this.container.querySelector('.multi-model-grid').multiModelGrid = this;

        // Initialize consensus indicator if data exists
        if (this.options.showConsensus && this.data.consensus) {
            this.initializeConsensusIndicator();
        }
    }

    renderConsensusSection() {
        return `
            <div class="consensus-section">
                <div class="consensus-indicator-container" id="consensus-${this.options.raTagId}">
                    <!-- ConsensusIndicator will be rendered here -->
                </div>
                <div class="consensus-details">
                    <h3>Multi-Model Consensus</h3>
                    <div class="consensus-stats">
                        <span class="model-count">${this.data.modelCount} models</span>
                        <span class="agreement-level">${this.getAgreementLevelText()}</span>
                    </div>
                </div>
            </div>
        `;
    }

    renderControls() {
        return `
            <div class="grid-controls">
                <div class="sort-controls">
                    <label for="sort-select">Sort by:</label>
                    <select id="sort-select" class="sort-select">
                        <option value="created_at-desc" ${this.state.sortBy === 'created_at' && this.state.sortOrder === 'desc' ? 'selected' : ''}>Newest First</option>
                        <option value="created_at-asc" ${this.state.sortBy === 'created_at' && this.state.sortOrder === 'asc' ? 'selected' : ''}>Oldest First</option>
                        <option value="confidence-desc" ${this.state.sortBy === 'confidence' && this.state.sortOrder === 'desc' ? 'selected' : ''}>Highest Confidence</option>
                        <option value="confidence-asc" ${this.state.sortBy === 'confidence' && this.state.sortOrder === 'asc' ? 'selected' : ''}>Lowest Confidence</option>
                        <option value="outcome-asc" ${this.state.sortBy === 'outcome' && this.state.sortOrder === 'asc' ? 'selected' : ''}>Outcome A-Z</option>
                    </select>
                </div>
                <div class="filter-controls">
                    <label for="outcome-filter">Filter:</label>
                    <select id="outcome-filter" class="outcome-filter">
                        <option value="" ${!this.state.filterByOutcome ? 'selected' : ''}>All Outcomes</option>
                        <option value="validated" ${this.state.filterByOutcome === 'validated' ? 'selected' : ''}>Validated</option>
                        <option value="rejected" ${this.state.filterByOutcome === 'rejected' ? 'selected' : ''}>Rejected</option>
                        <option value="partial" ${this.state.filterByOutcome === 'partial' ? 'selected' : ''}>Partial</option>
                    </select>
                </div>
                <button class="refresh-btn" onclick="this.closest('.multi-model-grid').multiModelGrid.loadData()"
                        title="Refresh validations">
                    🔄
                </button>
            </div>
        `;
    }

    renderValidations() {
        if (!this.data.validations.length) return '';

        const filteredValidations = this.getFilteredValidations();
        const sortedValidations = this.getSortedValidations(filteredValidations);

        return sortedValidations.map(validation => this.renderValidationCard(validation)).join('');
    }

    renderValidationCard(validation) {
        const modelInfo = validation.model_info || {};
        const outcomeClass = `outcome-${validation.outcome}`;
        const confidenceColor = this.getConfidenceColor(validation.confidence);

        return `
            <div class="validation-card ${outcomeClass}" data-validation-id="${validation.validation_id}">
                <div class="validation-header">
                    <div class="model-info">
                        <div class="model-provider-icon">
                            ${this.getProviderIcon(modelInfo.provider)}
                        </div>
                        <div class="model-details">
                            <h4 class="model-name">${modelInfo.display_name || modelInfo.name || 'Unknown Model'}</h4>
                            <span class="model-provider">${modelInfo.provider || 'unknown'}</span>
                        </div>
                    </div>
                    <div class="validation-outcome">
                        <span class="outcome-badge outcome-${validation.outcome}">
                            ${this.getOutcomeIcon(validation.outcome)} ${validation.outcome.toUpperCase()}
                        </span>
                    </div>
                </div>

                <div class="validation-body">
                    <div class="confidence-section">
                        <div class="confidence-label">Confidence</div>
                        <div class="confidence-bar">
                            <div class="confidence-fill"
                                 style="width: ${validation.confidence}%; background-color: ${confidenceColor};">
                            </div>
                            <span class="confidence-value">${validation.confidence}%</span>
                        </div>
                    </div>

                    ${validation.reason ? `
                        <div class="validation-reason">
                            <div class="reason-label">Reasoning</div>
                            <div class="reason-text">${this.escapeHtml(validation.reason)}</div>
                        </div>
                    ` : ''}
                </div>

                <div class="validation-footer">
                    <div class="validation-meta">
                        <span class="validation-time" title="${validation.created_at}">
                            ${this.formatRelativeTime(validation.created_at)}
                        </span>
                        <span class="reviewer-id">${validation.reviewer_agent_id}</span>
                    </div>
                    ${modelInfo.weight ? `
                        <div class="model-weight" title="Consensus weight: ${modelInfo.weight}">
                            Weight: ${modelInfo.weight}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        // Sort control
        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('sort-select')) {
                const [sortBy, sortOrder] = e.target.value.split('-');
                this.state.sortBy = sortBy;
                this.state.sortOrder = sortOrder;
                this.renderValidations();
                this.updateValidationsDisplay();
            }

            if (e.target.classList.contains('outcome-filter')) {
                this.state.filterByOutcome = e.target.value || null;
                this.renderValidations();
                this.updateValidationsDisplay();
            }
        });

        // Responsive layout handling
        this.setupResponsiveLayout();
    }

    setupResponsiveLayout() {
        const handleResize = () => {
            const width = window.innerWidth;
            let columns;

            if (width < 768) {
                columns = this.options.columns.mobile;
            } else if (width < 1024) {
                columns = this.options.columns.tablet;
            } else {
                columns = this.options.columns.desktop;
            }

            const validationsContainer = this.container.querySelector('.multi-model-validations');
            if (validationsContainer) {
                validationsContainer.style.gridTemplateColumns = `repeat(${columns}, 1fr)`;
            }
        };

        window.addEventListener('resize', handleResize);
        handleResize(); // Apply initial layout
    }

    setupWebSocketListeners() {
        // #COMPLETION_DRIVE_INTEGRATION: Using global AppState WebSocket for real-time updates
        if (typeof AppState !== 'undefined' && AppState.socket) {
            const handleMessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    // Handle multi-model specific events
                    if (data.type === 'multi_model.validation_added' ||
                        data.type === 'multi_model.consensus_updated') {
                        // Check if this update is for our task/tag
                        if (data.context &&
                            data.context.task_id == this.options.taskId &&
                            data.context.ra_tag_id === this.options.raTagId) {
                            this.handleMultiModelUpdate(data);
                        }
                    }
                    // Legacy event handling for backward compatibility
                    else if (data.type === 'assumption_validation_captured' ||
                             data.type === 'assumption_validation_updated' ||
                             data.type === 'multi_model_validation') {
                        // Check if this update is for our task/tag
                        if (data.data &&
                            data.data.task_id == this.options.taskId &&
                            data.data.ra_tag_id === this.options.raTagId) {
                            this.loadData(); // Refresh the entire dataset
                        }
                    }
                } catch (error) {
                    console.error('Failed to parse WebSocket message in MultiModelGrid:', error);
                }
            };

            if (AppState.socket.readyState === WebSocket.OPEN) {
                AppState.socket.addEventListener('message', handleMessage);
            }

            this.websocketListeners.push(handleMessage);
        }
    }

    handleMultiModelUpdate(eventData) {
        // #COMPLETION_DRIVE_IMPL: Real-time multi-model event handling with optimized updates
        console.log('Handling multi-model update:', eventData);

        if (eventData.type === 'multi_model.validation_added') {
            // Add new validation to existing data without full reload
            this.handleValidationAdded(eventData.data);
        } else if (eventData.type === 'multi_model.consensus_updated') {
            // Update consensus information
            this.handleConsensusUpdated(eventData.data);
        }

        // Update UI with animation to highlight changes
        this.updateDisplayWithHighlight();
    }

    handleValidationAdded(validationData) {
        if (!this.data || !this.data.validations) {
            // If no data loaded yet, trigger full reload
            this.loadData();
            return;
        }

        // Add the new validation to existing data
        const validation = validationData.validation;
        const model = validationData.model;

        // Create ValidationWithModel object
        const validationWithModel = {
            id: validation.id,
            task_id: validation.task_id,
            ra_tag_id: validation.ra_tag_id,
            outcome: validation.outcome,
            confidence: validation.confidence,
            validator_id: validation.validator_id,
            notes: validation.notes,
            validated_at: validation.validated_at,
            model_name: model.name,
            model_version: model.version,
            model_category: model.category
        };

        // Add to validations array
        this.data.validations.push(validationWithModel);
        this.data.modelCount = Math.max(this.data.modelCount, this.data.validations.length);

        // Recalculate consensus locally (simplified)
        this.recalculateConsensusLocally();
    }

    handleConsensusUpdated(consensusData) {
        if (this.data && this.data.consensus && consensusData.consensus) {
            // Update consensus data
            Object.assign(this.data.consensus, consensusData.consensus);
        }
    }

    recalculateConsensusLocally() {
        if (!this.data || !this.data.validations || this.data.validations.length === 0) {
            return;
        }

        // Simple local consensus calculation
        const validations = this.data.validations;
        const totalValidations = validations.length;

        if (totalValidations === 0) return;

        // Count outcomes
        const outcomes = { validated: 0, rejected: 0, partial: 0 };
        let totalConfidence = 0;

        validations.forEach(validation => {
            outcomes[validation.outcome] = (outcomes[validation.outcome] || 0) + 1;
            totalConfidence += validation.confidence || 50;
        });

        // Calculate percentages and average confidence
        const avgConfidence = totalConfidence / totalValidations;
        const validatedPercent = (outcomes.validated / totalValidations) * 100;
        const rejectedPercent = (outcomes.rejected / totalValidations) * 100;

        // Determine agreement level
        let agreementLevel = 'WEAK';
        if (validatedPercent >= 80 || rejectedPercent >= 80) {
            agreementLevel = 'STRONG';
        } else if (validatedPercent >= 60 || rejectedPercent >= 60) {
            agreementLevel = 'MODERATE';
        }

        // Update consensus data
        if (this.data.consensus) {
            this.data.consensus.overall_score = avgConfidence;
            this.data.consensus.agreement_level = agreementLevel;
            this.data.consensus.validation_count = totalValidations;
        }
    }

    updateDisplayWithHighlight() {
        // Re-render the component with highlight animation
        this.render();

        // Add highlight effect to indicate real-time update
        if (this.container) {
            this.container.style.boxShadow = '0 0 10px rgba(34, 197, 94, 0.5)';
            this.container.style.transition = 'box-shadow 0.3s ease';

            setTimeout(() => {
                this.container.style.boxShadow = '';
            }, 2000);
        }
    }

    async loadData() {
        if (!this.options.taskId || !this.options.raTagId) {
            this.setState({ error: 'Task ID and RA Tag ID are required' });
            return;
        }

        this.setState({ loading: true, error: null });

        try {
            const response = await fetch(`/api/assumptions/multi-model/${this.options.taskId}/${this.options.raTagId}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            this.data = {
                consensus: data.consensus,
                validations: data.validations || [],
                modelCount: data.model_count || 0,
                cached: data.cached || false,
                generatedAt: data.generated_at
            };

            this.setState({ loading: false });
            this.updateDisplay();

        } catch (error) {
            console.error('Failed to load multi-model data:', error);
            this.setState({
                loading: false,
                error: error.message || 'Failed to load validation data'
            });
        }
    }

    setState(newState) {
        Object.assign(this.state, newState);
        this.updateLoadingAndErrorStates();
    }

    updateDisplay() {
        this.updateValidationsDisplay();
        this.updateConsensusDisplay();
        this.updateHeader();
    }

    updateValidationsDisplay() {
        const validationsContainer = this.container.querySelector('.multi-model-validations');
        if (validationsContainer) {
            validationsContainer.innerHTML = this.renderValidations();
        }
    }

    updateConsensusDisplay() {
        if (this.options.showConsensus && this.data.consensus) {
            this.initializeConsensusIndicator();
        }
    }

    updateHeader() {
        const modelCountSpan = this.container.querySelector('.model-count');
        if (modelCountSpan) {
            modelCountSpan.textContent = `${this.data.modelCount} models`;
        }

        const agreementLevelSpan = this.container.querySelector('.agreement-level');
        if (agreementLevelSpan) {
            agreementLevelSpan.textContent = this.getAgreementLevelText();
        }
    }

    updateLoadingAndErrorStates() {
        const grid = this.container.querySelector('.multi-model-grid');
        if (grid) {
            grid.setAttribute('data-loading', this.state.loading);
        }

        const loadingEl = this.container.querySelector('.multi-model-loading');
        if (loadingEl) {
            loadingEl.style.display = this.state.loading ? 'block' : 'none';
        }

        const errorEl = this.container.querySelector('.multi-model-error');
        if (errorEl) {
            errorEl.style.display = this.state.error ? 'block' : 'none';
            const errorMsg = errorEl.querySelector('.error-message');
            if (errorMsg) {
                errorMsg.textContent = this.state.error || '';
            }
        }

        const emptyEl = this.container.querySelector('.multi-model-empty');
        if (emptyEl) {
            const shouldShow = !this.state.loading && !this.state.error && this.data.validations.length === 0;
            emptyEl.style.display = shouldShow ? 'block' : 'none';
        }
    }

    initializeConsensusIndicator() {
        const container = this.container.querySelector(`#consensus-${this.options.raTagId}`);
        if (container && this.data.consensus && typeof ConsensusIndicator !== 'undefined') {
            // Clean up existing indicator
            if (this.consensusIndicator) {
                this.consensusIndicator.destroy();
            }

            // Create new consensus indicator
            this.consensusIndicator = new ConsensusIndicator(container, {
                consensus: this.data.consensus.consensus * 100, // Convert to percentage
                size: 'large',
                showTooltip: true,
                modelBreakdown: this.getModelBreakdown(),
                noData: this.data.consensus.agreement_level === 'no_data'
            });
        }
    }

    getModelBreakdown() {
        if (!this.data.validations.length) return null;

        const breakdown = {
            total: this.data.validations.length,
            validated: 0,
            rejected: 0,
            partial: 0
        };

        this.data.validations.forEach(validation => {
            breakdown[validation.outcome] = (breakdown[validation.outcome] || 0) + 1;
        });

        return breakdown;
    }

    getFilteredValidations() {
        if (!this.state.filterByOutcome) {
            return this.data.validations;
        }
        return this.data.validations.filter(v => v.outcome === this.state.filterByOutcome);
    }

    getSortedValidations(validations) {
        return [...validations].sort((a, b) => {
            let comparison = 0;

            switch (this.state.sortBy) {
                case 'created_at':
                    comparison = new Date(a.created_at) - new Date(b.created_at);
                    break;
                case 'confidence':
                    comparison = a.confidence - b.confidence;
                    break;
                case 'outcome':
                    comparison = a.outcome.localeCompare(b.outcome);
                    break;
            }

            return this.state.sortOrder === 'desc' ? -comparison : comparison;
        });
    }

    getAgreementLevelText() {
        if (!this.data.consensus) return 'No consensus data';

        const level = this.data.consensus.agreement_level;
        const consensus = Math.round(this.data.consensus.consensus * 100);

        const levelTexts = {
            no_data: 'No Data',
            weak: 'Weak Agreement',
            moderate: 'Moderate Agreement',
            strong: 'Strong Agreement',
            unanimous: 'Unanimous Agreement'
        };

        return level === 'no_data'
            ? `${levelTexts[level] || 'No Data'}`
            : `${levelTexts[level] || 'Unknown'} (${consensus}%)`;
    }

    getProviderIcon(provider) {
        const icons = {
            anthropic: '🔮',
            openai: '🤖',
            google: '🧠',
            meta: '🦙',
            unknown: '❓'
        };
        return icons[provider] || icons.unknown;
    }

    getOutcomeIcon(outcome) {
        const icons = {
            validated: '✅',
            rejected: '❌',
            partial: '⚠️'
        };
        return icons[outcome] || '❓';
    }

    getConfidenceColor(confidence) {
        if (confidence >= 80) return '#10b981'; // Green
        if (confidence >= 60) return '#f59e0b'; // Orange
        return '#ef4444'; // Red
    }

    formatRelativeTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMinutes = Math.floor(diffMs / 60000);

        if (diffMinutes < 1) return 'Just now';
        if (diffMinutes < 60) return `${diffMinutes}m ago`;

        const diffHours = Math.floor(diffMinutes / 60);
        if (diffHours < 24) return `${diffHours}h ago`;

        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d ago`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Update data for a specific task and RA tag
     */
    updateTaskAndTag(taskId, raTagId) {
        this.options.taskId = taskId;
        this.options.raTagId = raTagId;
        this.loadData();
    }

    /**
     * Refresh the grid with current data
     */
    refresh() {
        this.loadData();
    }

    /**
     * Destroy the component and clean up
     */
    destroy() {
        // Clean up WebSocket listeners
        this.websocketListeners.forEach(listener => {
            if (typeof AppState !== 'undefined' && AppState.socket) {
                AppState.socket.removeEventListener('message', listener);
            }
        });

        // Clean up consensus indicator
        if (this.consensusIndicator) {
            this.consensusIndicator.destroy();
        }

        // Clean up container
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MultiModelGrid;
}

// Global registration for direct HTML usage
if (typeof window !== 'undefined') {
    window.MultiModelGrid = MultiModelGrid;
}
