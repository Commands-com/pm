/**
 * ModelSelector Component
 * Interactive model selector with filters and preferences for multi-model validation
 *
 * Features:
 * - Enable/disable specific models in comparison view
 * - Filter validations by model provider or confidence level
 * - Save model preferences to local storage
 * - Show model availability status and configuration
 * - Quick preset filters (e.g., "High Confidence Only")
 * - Real-time filter application to multi-model grid
 */

class ModelSelector {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.options = {
            autoLoad: true,
            enableLocalStorage: true,
            showModelCounts: true,
            showPresets: true,
            onFilterChange: null, // Callback when filters change
            storageKey: 'pmDashboard.modelSelectorFilters',
            ...options
        };

        this.data = {
            availableModels: [],
            totalModels: 0,
            enabledModels: 0,
            lastUpdated: null
        };

        this.filters = {
            enabledModels: new Set(), // Set of enabled model IDs
            minConfidence: 0, // Minimum confidence level (0-100)
            providerFilter: null, // null = all, or specific provider
            presetActive: 'all' // 'all', 'high-confidence', 'major-providers'
        };

        this.init();
    }

    init() {
        this.loadFiltersFromStorage();
        this.render();
        this.setupEventListeners();

        if (this.options.autoLoad) {
            this.loadModels();
        }
    }

    render() {
        this.container.innerHTML = `
            <div class="model-selector">
                <div class="selector-header">
                    <h3>Model Filters</h3>
                    <div class="model-counts">
                        <span class="enabled-count">${this.getEnabledModelsCount()}</span>
                        <span class="total-count">of ${this.data.totalModels} models</span>
                    </div>
                </div>

                <!-- Loading state -->
                <div class="selector-loading" style="display: none;">
                    <div class="loading-spinner-small"></div>
                    <span>Loading models...</span>
                </div>

                <!-- Preset filters -->
                ${this.options.showPresets ? this.renderPresets() : ''}

                <!-- Provider filters -->
                <div class="provider-filters">
                    <div class="filter-section-title">Providers</div>
                    <div class="provider-buttons">
                        ${this.renderProviderButtons()}
                    </div>
                </div>

                <!-- Confidence filter -->
                <div class="confidence-filter">
                    <div class="filter-section-title">
                        Minimum Confidence
                        <span class="confidence-value">${this.filters.minConfidence}%</span>
                    </div>
                    <div class="confidence-slider-container">
                        <input type="range"
                               class="confidence-slider"
                               min="0"
                               max="100"
                               step="5"
                               value="${this.filters.minConfidence}"
                               data-filter="confidence">
                        <div class="confidence-markers">
                            <span>0%</span>
                            <span>50%</span>
                            <span>100%</span>
                        </div>
                    </div>
                </div>

                <!-- Individual model selection -->
                <div class="model-list">
                    <div class="filter-section-title">Individual Models</div>
                    <div class="models-container">
                        ${this.renderModelList()}
                    </div>
                </div>

                <!-- Actions -->
                <div class="selector-actions">
                    <button class="action-btn select-all-btn" data-action="select-all">
                        Select All
                    </button>
                    <button class="action-btn select-none-btn" data-action="select-none">
                        Select None
                    </button>
                    <button class="action-btn reset-btn" data-action="reset">
                        Reset Filters
                    </button>
                </div>
            </div>
        `;
    }

    renderPresets() {
        const presets = [
            { id: 'all', label: 'All Models', count: this.data.totalModels },
            { id: 'high-confidence', label: 'High Confidence (80+)', count: this.getHighConfidenceModelCount() },
            { id: 'major-providers', label: 'Major Providers', count: this.getMajorProviderModelCount() }
        ];

        return `
            <div class="preset-filters">
                <div class="filter-section-title">Quick Presets</div>
                <div class="preset-buttons">
                    ${presets.map(preset => `
                        <button class="preset-btn ${this.filters.presetActive === preset.id ? 'active' : ''}"
                                data-preset="${preset.id}">
                            ${preset.label}
                            ${this.options.showModelCounts ? `<span class="preset-count">(${preset.count})</span>` : ''}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
    }

    renderProviderButtons() {
        const providers = this.getUniqueProviders();

        return `
            <button class="provider-btn ${!this.filters.providerFilter ? 'active' : ''}"
                    data-provider="">
                All Providers
                ${this.options.showModelCounts ? `<span class="provider-count">(${this.data.totalModels})</span>` : ''}
            </button>
            ${providers.map(provider => `
                <button class="provider-btn ${this.filters.providerFilter === provider.name ? 'active' : ''}"
                        data-provider="${provider.name}">
                    ${this.capitalizeProvider(provider.name)}
                    ${this.options.showModelCounts ? `<span class="provider-count">(${provider.count})</span>` : ''}
                </button>
            `).join('')}
        `;
    }

    renderModelList() {
        if (!this.data.availableModels.length) {
            return '<div class="models-empty">No models available</div>';
        }

        const filteredModels = this.getFilteredModels();

        return filteredModels.map(model => {
            const isEnabled = this.filters.enabledModels.has(model.id);
            const isVisible = this.isModelVisible(model);

            return `
                <div class="model-item ${!isVisible ? 'hidden' : ''}" data-model-id="${model.id}">
                    <label class="model-checkbox-label">
                        <input type="checkbox"
                               class="model-checkbox"
                               data-model-id="${model.id}"
                               ${isEnabled ? 'checked' : ''}>
                        <div class="checkbox-custom"></div>
                        <div class="model-info">
                            <div class="model-name">${model.display_name}</div>
                            <div class="model-details">
                                <span class="model-provider">${this.capitalizeProvider(model.provider)}</span>
                                <span class="model-weight">Weight: ${model.weight}</span>
                                <span class="model-status ${model.enabled ? 'enabled' : 'disabled'}">
                                    ${model.enabled ? '✓ Enabled' : '✗ Disabled'}
                                </span>
                            </div>
                        </div>
                    </label>
                </div>
            `;
        }).join('');
    }

    setupEventListeners() {
        // Preset button clicks
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('preset-btn')) {
                const preset = e.target.dataset.preset;
                this.applyPreset(preset);
            }

            if (e.target.classList.contains('provider-btn')) {
                const provider = e.target.dataset.provider || null;
                this.setProviderFilter(provider);
            }

            if (e.target.classList.contains('action-btn')) {
                const action = e.target.dataset.action;
                this.handleAction(action);
            }
        });

        // Model checkbox changes
        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('model-checkbox')) {
                const modelId = e.target.dataset.modelId;
                const isChecked = e.target.checked;
                this.toggleModel(modelId, isChecked);
            }

            if (e.target.classList.contains('confidence-slider')) {
                const confidence = parseInt(e.target.value);
                this.setConfidenceFilter(confidence);
            }
        });
    }

    async loadModels() {
        this.showLoading(true);

        try {
            const response = await fetch('/api/assumptions/models');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            this.data = {
                availableModels: data.models || [],
                totalModels: data.total_models || 0,
                enabledModels: data.enabled_models || 0,
                lastUpdated: data.last_updated
            };

            // Initialize enabled models if empty (first load)
            if (this.filters.enabledModels.size === 0) {
                this.data.availableModels.forEach(model => {
                    if (model.enabled) {
                        this.filters.enabledModels.add(model.id);
                    }
                });
            }

            this.render();
            this.notifyFilterChange();

        } catch (error) {
            console.error('Failed to load models:', error);
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    }

    applyPreset(presetId) {
        this.filters.presetActive = presetId;

        switch (presetId) {
            case 'all':
                this.selectAllModels();
                this.filters.minConfidence = 0;
                this.filters.providerFilter = null;
                break;

            case 'high-confidence':
                this.selectAllModels();
                this.filters.minConfidence = 80;
                this.filters.providerFilter = null;
                break;

            case 'major-providers':
                this.selectMajorProviders();
                this.filters.minConfidence = 0;
                this.filters.providerFilter = null;
                break;
        }

        this.render();
        this.saveFiltersToStorage();
        this.notifyFilterChange();
    }

    setProviderFilter(provider) {
        this.filters.providerFilter = provider;
        this.filters.presetActive = null; // Clear preset when manually filtering
        this.render();
        this.saveFiltersToStorage();
        this.notifyFilterChange();
    }

    setConfidenceFilter(confidence) {
        this.filters.minConfidence = confidence;
        this.filters.presetActive = null; // Clear preset when manually filtering

        // Update confidence display
        const confidenceValue = this.container.querySelector('.confidence-value');
        if (confidenceValue) {
            confidenceValue.textContent = `${confidence}%`;
        }

        this.saveFiltersToStorage();
        this.notifyFilterChange();
    }

    toggleModel(modelId, isEnabled) {
        if (isEnabled) {
            this.filters.enabledModels.add(modelId);
        } else {
            this.filters.enabledModels.delete(modelId);
        }

        this.filters.presetActive = null; // Clear preset when manually selecting
        this.updateModelCounts();
        this.saveFiltersToStorage();
        this.notifyFilterChange();
    }

    handleAction(action) {
        switch (action) {
            case 'select-all':
                this.selectAllModels();
                break;
            case 'select-none':
                this.selectNoneModels();
                break;
            case 'reset':
                this.resetFilters();
                break;
        }
    }

    selectAllModels() {
        this.filters.enabledModels.clear();
        this.data.availableModels.forEach(model => {
            if (model.enabled) {
                this.filters.enabledModels.add(model.id);
            }
        });
        this.updateUI();
    }

    selectNoneModels() {
        this.filters.enabledModels.clear();
        this.updateUI();
    }

    selectMajorProviders() {
        const majorProviders = ['anthropic', 'openai', 'google'];
        this.filters.enabledModels.clear();
        this.data.availableModels.forEach(model => {
            if (model.enabled && majorProviders.includes(model.provider)) {
                this.filters.enabledModels.add(model.id);
            }
        });
        this.updateUI();
    }

    resetFilters() {
        this.filters = {
            enabledModels: new Set(),
            minConfidence: 0,
            providerFilter: null,
            presetActive: 'all'
        };

        // Re-enable all available models
        this.selectAllModels();
        this.render();
        this.saveFiltersToStorage();
        this.notifyFilterChange();
    }

    updateUI() {
        this.updateModelCounts();
        this.updateCheckboxes();
        this.saveFiltersToStorage();
        this.notifyFilterChange();
    }

    updateModelCounts() {
        const enabledCount = this.container.querySelector('.enabled-count');
        if (enabledCount) {
            enabledCount.textContent = this.getEnabledModelsCount();
        }
    }

    updateCheckboxes() {
        const checkboxes = this.container.querySelectorAll('.model-checkbox');
        checkboxes.forEach(checkbox => {
            const modelId = checkbox.dataset.modelId;
            checkbox.checked = this.filters.enabledModels.has(modelId);
        });
    }

    getFilteredModels() {
        return this.data.availableModels.filter(model => this.isModelVisible(model));
    }

    isModelVisible(model) {
        // Provider filter
        if (this.filters.providerFilter && model.provider !== this.filters.providerFilter) {
            return false;
        }

        return true;
    }

    getEnabledModelsCount() {
        return this.filters.enabledModels.size;
    }

    getHighConfidenceModelCount() {
        // For now, assume all models can be high confidence
        // This would be refined based on actual validation data
        return this.data.availableModels.filter(model => model.enabled).length;
    }

    getMajorProviderModelCount() {
        const majorProviders = ['anthropic', 'openai', 'google'];
        return this.data.availableModels.filter(model =>
            model.enabled && majorProviders.includes(model.provider)
        ).length;
    }

    getUniqueProviders() {
        const providerCounts = {};
        this.data.availableModels.forEach(model => {
            providerCounts[model.provider] = (providerCounts[model.provider] || 0) + 1;
        });

        return Object.entries(providerCounts).map(([name, count]) => ({ name, count }));
    }

    capitalizeProvider(provider) {
        const providerNames = {
            anthropic: 'Anthropic',
            openai: 'OpenAI',
            google: 'Google',
            meta: 'Meta',
            unknown: 'Unknown'
        };
        return providerNames[provider] || provider.charAt(0).toUpperCase() + provider.slice(1);
    }

    showLoading(show) {
        const loadingEl = this.container.querySelector('.selector-loading');
        if (loadingEl) {
            loadingEl.style.display = show ? 'flex' : 'none';
        }
    }

    showError(message) {
        // Simple error display - could be enhanced with proper error UI
        console.error('ModelSelector error:', message);
    }

    saveFiltersToStorage() {
        if (!this.options.enableLocalStorage) return;

        try {
            const filterData = {
                enabledModels: Array.from(this.filters.enabledModels),
                minConfidence: this.filters.minConfidence,
                providerFilter: this.filters.providerFilter,
                presetActive: this.filters.presetActive,
                timestamp: Date.now()
            };

            localStorage.setItem(this.options.storageKey, JSON.stringify(filterData));
        } catch (error) {
            console.warn('Failed to save model selector filters to localStorage:', error);
        }
    }

    loadFiltersFromStorage() {
        if (!this.options.enableLocalStorage) return;

        try {
            const saved = localStorage.getItem(this.options.storageKey);
            if (saved) {
                const filterData = JSON.parse(saved);

                this.filters.enabledModels = new Set(filterData.enabledModels || []);
                this.filters.minConfidence = filterData.minConfidence || 0;
                this.filters.providerFilter = filterData.providerFilter || null;
                this.filters.presetActive = filterData.presetActive || 'all';
            }
        } catch (error) {
            console.warn('Failed to load model selector filters from localStorage:', error);
        }
    }

    notifyFilterChange() {
        if (typeof this.options.onFilterChange === 'function') {
            const filterState = {
                enabledModels: Array.from(this.filters.enabledModels),
                minConfidence: this.filters.minConfidence,
                providerFilter: this.filters.providerFilter,
                presetActive: this.filters.presetActive,
                totalEnabled: this.filters.enabledModels.size
            };

            this.options.onFilterChange(filterState);
        }
    }

    /**
     * Get current filter state
     */
    getFilterState() {
        return {
            enabledModels: Array.from(this.filters.enabledModels),
            minConfidence: this.filters.minConfidence,
            providerFilter: this.filters.providerFilter,
            presetActive: this.filters.presetActive,
            totalEnabled: this.filters.enabledModels.size
        };
    }

    /**
     * Apply filter state from external source
     */
    setFilterState(filterState) {
        this.filters.enabledModels = new Set(filterState.enabledModels || []);
        this.filters.minConfidence = filterState.minConfidence || 0;
        this.filters.providerFilter = filterState.providerFilter || null;
        this.filters.presetActive = filterState.presetActive || null;

        this.render();
        this.saveFiltersToStorage();
        this.notifyFilterChange();
    }

    /**
     * Refresh models data
     */
    refresh() {
        this.loadModels();
    }

    /**
     * Destroy the component and clean up
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ModelSelector;
}

// Global registration for direct HTML usage
if (typeof window !== 'undefined') {
    window.ModelSelector = ModelSelector;
}