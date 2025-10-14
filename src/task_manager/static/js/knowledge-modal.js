// Enhanced Interactive Knowledge Management Modal
// Full-featured modal with Add/Edit/Delete functionality, form validation, and API integration
import { showNotification } from './utils.js';
import { AppState } from './state.js';

export class KnowledgeManagementModal {
    constructor() {
        this.modal = document.getElementById('knowledgeModal');
        this.isOpen = false;
        this.isEditing = false;
        this.currentEditingItem = null;
        this.originalData = {};
        this.currentTags = [];
        this.hasUnsavedChanges = false;
        this.knowledgeItems = [];
        this.sessionProject = null;
        this.currentInlineEditItem = null;
        this.sessionEpic = null;

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Core modal functionality
        this.setupCloseHandlers();

        // Interactive action buttons
        this.setupActionButtons();

        // Form functionality
        this.setupFormHandlers();

        // Search and filtering
        this.setupSearchAndFiltering();

        // Event delegation for dynamic content
        const contentElement = document.getElementById('knowledgeContent');
        if (contentElement) {
            contentElement.addEventListener('click', (e) => {
                const target = e.target;
                const itemAction = target.closest('.item-action-btn');
                const emptyStateAddBtn = target.closest('.add-first-btn');

                if (itemAction) {
                    const knowledgeItem = itemAction.closest('.knowledge-item');
                    const knowledgeId = knowledgeItem?.dataset.id;
                    if (!knowledgeId) return;

                    if (itemAction.classList.contains('edit-btn')) {
                        this.startEditing(knowledgeId);
                    } else if (itemAction.classList.contains('delete-btn')) {
                        this.deleteKnowledgeItem(knowledgeId);
                    }
                } else if (emptyStateAddBtn) {
                    this.startAddingNew();
                }
            });
        }

        const tagsContainer = document.getElementById('tagsContainer');
        if (tagsContainer) {
            tagsContainer.addEventListener('click', (e) => {
                if (e.target.classList.contains('tag-remove')) {
                    const tag = e.target.dataset.tag;
                    if (tag) {
                        this.removeTag(tag);
                    }
                }
            });
        }
    }

    setupCloseHandlers() {
        const closeBtn = document.getElementById('knowledgeModalCloseBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.handleClose());
        }

        this.modal?.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.handleClose();
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.handleClose();
            }
        });
    }

    setupActionButtons() {
        // Add New button
        document.getElementById('addKnowledgeBtn')?.addEventListener('click', () => {
            this.startAddingNew();
        });

        // Save button
        document.getElementById('saveKnowledgeBtn')?.addEventListener('click', () => {
            this.saveKnowledgeItem();
        });

        // Cancel button
        document.getElementById('cancelKnowledgeBtn')?.addEventListener('click', () => {
            this.cancelEditing();
        });
    }

    setupFormHandlers() {
        // Character counter for content textarea
        const contentTextarea = document.getElementById('itemContent');
        if (contentTextarea) {
            contentTextarea.addEventListener('input', (e) => {
                const counter = document.getElementById('contentCharCounter');
                if (counter) {
                    counter.textContent = `${e.target.value.length}/2000`;
                }
                this.hasUnsavedChanges = true;
            });
        }

        // Track changes on all form fields
        ['itemTitle', 'itemCategory', 'itemPriority'].forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.addEventListener('input', () => {
                    this.hasUnsavedChanges = true;
                });
            }
        });

        // Tag input handling
        const tagInput = document.getElementById('tagInput');
        if (tagInput) {
            tagInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.addTag();
                }
            });
        }

        const addTagBtn = document.getElementById('addTagBtn');
        if (addTagBtn) {
            addTagBtn.addEventListener('click', () => this.addTag());
        }
    }

    setupSearchAndFiltering() {
        const searchInput = document.getElementById('knowledgeSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterKnowledgeItems(e.target.value);
            });
        }

        const categoryFilter = document.getElementById('knowledgeCategoryFilter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => {
                this.filterByCategory(e.target.value);
            });
        }

        const clearSearchBtn = document.getElementById('clearSearchBtn');
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => {
                searchInput.value = '';
                categoryFilter.value = '';
                this.loadKnowledgeData();
                clearSearchBtn.style.display = 'none';
            });
        }
    }

    async open() {
        try {
            if (this.modal) {
                this.modal.style.display = 'flex';
                this.isOpen = true;

                // Set focus management for accessibility
                const firstFocusable = this.modal.querySelector('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
                if (firstFocusable) {
                    setTimeout(() => firstFocusable.focus(), 100);
                }

                document.body.style.overflow = 'hidden';
                await this.loadKnowledgeData();
            }
        } catch (error) {
            console.error('Error opening knowledge modal:', error);
            showNotification('Error opening Knowledge Management', 'error');
        }
    }

    async handleClose() {
        if (this.hasUnsavedChanges) {
            const confirmClose = confirm('You have unsaved changes. Are you sure you want to close?');
            if (!confirmClose) {
                return;
            }
        }

        if (this.modal) {
            this.modal.style.display = 'none';
            this.isOpen = false;
            this.hasUnsavedChanges = false;
            this.cancelEditing();
            document.body.style.overflow = '';
        }
    }

    startAddingNew() {
        this.isEditing = true;
        this.currentEditingItem = null;
        this.originalData = {};
        this.currentTags = [];
        this.showEditForm(true);
        this.clearForm();

        document.getElementById('formTitle').textContent = 'Add New Knowledge Item';
        document.getElementById('itemTitle').focus();
    }

    startEditing(knowledgeId) {
        const item = this.findKnowledgeItemById(knowledgeId);
        if (!item) return;

        this.isEditing = true;
        this.currentEditingItem = item;
        this.originalData = { ...item };
        this.showEditForm(true);
        this.populateForm(item);

        document.getElementById('formTitle').textContent = 'Edit Knowledge Item';
    }

    populateForm(item) {
        document.getElementById('itemTitle').value = item.title || '';
        document.getElementById('itemCategory').value = item.category || '';
        document.getElementById('itemContent').value = item.content || '';
        document.getElementById('itemPriority').value = item.priority || 2;

        // Handle tags
        this.currentTags = Array.isArray(item.tags) ? [...item.tags] : [];
        this.renderTags();

        // Update character counter
        const content = item.content || '';
        const counter = document.getElementById('contentCharCounter');
        if (counter) {
            counter.textContent = `${content.length}/2000`;
        }
    }

    clearForm() {
        document.getElementById('itemTitle').value = '';
        document.getElementById('itemCategory').value = '';
        document.getElementById('itemContent').value = '';
        document.getElementById('itemPriority').value = 2;
        this.currentTags = [];
        this.renderTags();

        const counter = document.getElementById('contentCharCounter');
        if (counter) {
            counter.textContent = '0/2000';
        }
    }

    showEditForm(show) {
        const form = document.getElementById('knowledgeEditForm');
        const saveBtn = document.getElementById('saveKnowledgeBtn');
        const cancelBtn = document.getElementById('cancelKnowledgeBtn');

        if (show) {
            if (form) form.style.display = 'block';
            if (saveBtn) saveBtn.style.display = 'inline-flex';
            if (cancelBtn) cancelBtn.style.display = 'inline-flex';
        } else {
            if (form) form.style.display = 'none';
            if (saveBtn) saveBtn.style.display = 'none';
            if (cancelBtn) cancelBtn.style.display = 'none';
        }
    }

    cancelEditing() {
        this.isEditing = false;
        this.currentEditingItem = null;
        this.originalData = {};
        this.currentTags = [];
        this.hasUnsavedChanges = false;
        this.showEditForm(false);
        this.clearForm();
    }

    addTag() {
        const tagInput = document.getElementById('tagInput');
        if (!tagInput) return;

        const tag = tagInput.value.trim();
        if (tag && !this.currentTags.includes(tag)) {
            this.currentTags.push(tag);
            this.renderTags();
            tagInput.value = '';
            this.hasUnsavedChanges = true;
        }
    }

    removeTag(tag) {
        this.currentTags = this.currentTags.filter(t => t !== tag);
        this.renderTags();
        this.hasUnsavedChanges = true;
    }

    renderTags() {
        const tagsContainer = document.getElementById('tagsContainer');
        if (!tagsContainer) return;

        tagsContainer.innerHTML = this.currentTags.map(tag => `
            <div class="knowledge-tag">
                <span class="tag-text">${this.escapeHtml(tag)}</span>
                <button class="tag-remove" data-tag="${this.escapeHtml(tag)}" type="button">×</button>
            </div>
        `).join('');
    }

    async saveKnowledgeItem() {
        if (!this.validateForm()) {
            return;
        }

        const formData = this.getFormData();

        try {
            const response = await fetch('/api/knowledge', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (result.success) {
                showNotification('Knowledge item saved successfully!', 'success');
                this.hasUnsavedChanges = false;
                this.cancelEditing();
                await this.loadKnowledgeData(); // Refresh the list
            } else {
                showNotification(result.message || 'Failed to save knowledge item', 'error');
            }
        } catch (error) {
            console.error('Error saving knowledge item:', error);
            showNotification('Error saving knowledge item', 'error');
        }
    }

    getFormData() {
        const projectSelector = document.getElementById('projectSelect');
        const epicSelector = document.getElementById('epicSelect');

        // Ensure project_id is always provided (required by database schema)
        // Priority: selector value → AppState selection → session project → fallback to 1
        let projectId = projectSelector?.value || AppState.selectedProjectId || this.sessionProject;

        // Validate that the project exists before using it
        if (projectId && !AppState.projects.has(String(projectId))) {
            projectId = null;
        }

        // Only fall back to 1 as last resort, and validate it exists
        if (!projectId) {
            if (AppState.projects.has('1')) {
                projectId = 1;
            } else {
                // Use the first available project if project 1 doesn't exist
                const firstProject = Array.from(AppState.projects.values())[0];
                projectId = firstProject ? firstProject.id : 1;
            }
        }

        const epicId = epicSelector?.value || AppState.selectedEpicId || this.sessionEpic || null;

        return {
            knowledge_id: this.currentEditingItem?.id || null,
            title: document.getElementById('itemTitle').value.trim(),
            content: document.getElementById('itemContent').value.trim(),
            category: document.getElementById('itemCategory').value,
            tags: this.currentTags,
            priority: parseInt(document.getElementById('itemPriority').value),
            project_id: parseInt(projectId),
            epic_id: epicId ? parseInt(epicId) : null,
            is_active: true
        };
    }

    validateForm() {
        const title = document.getElementById('itemTitle').value.trim();
        const content = document.getElementById('itemContent').value.trim();

        if (!title) {
            showNotification('Title is required', 'error');
            document.getElementById('itemTitle').focus();
            return false;
        }

        if (!content) {
            showNotification('Content is required', 'error');
            document.getElementById('itemContent').focus();
            return false;
        }

        if (content.length > 2000) {
            showNotification('Content must be 2000 characters or less', 'error');
            document.getElementById('itemContent').focus();
            return false;
        }

        return true;
    }

    async loadKnowledgeData(forceProjectId = null, forceEpicId = null) {
        const contentElement = document.getElementById('knowledgeContent');
        if (!contentElement) return;

        try {
            contentElement.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div>Loading knowledge items...</div>';

            // Determine context from current selectors or provided overrides
            const projectSelector = document.getElementById('projectSelect');
            const epicSelector = document.getElementById('epicSelect');

            // Priority: forced values → selector values → AppState → session → fallback
            let currentProject = forceProjectId || projectSelector?.value || AppState.selectedProjectId || this.sessionProject;
            let currentEpic = forceEpicId || epicSelector?.value || AppState.selectedEpicId || this.sessionEpic;

            // Validate project exists
            if (currentProject && !AppState.projects.has(String(currentProject))) {
                currentProject = null;
            }

            // Only fall back to 1 as last resort if it exists
            if (!currentProject) {
                if (AppState.projects.has('1')) {
                    currentProject = 1;
                } else {
                    const firstProject = Array.from(AppState.projects.values())[0];
                    currentProject = firstProject ? firstProject.id : 1;
                }
            }

            // Persist session context for subsequent actions
            this.sessionProject = currentProject;
            this.sessionEpic = currentEpic;

            // Build backend endpoint compatible with API
            let apiUrl;
            if (currentEpic && currentProject) {
                apiUrl = `/api/knowledge/project/${currentProject}/epic/${currentEpic}`;
            } else if (currentProject) {
                apiUrl = `/api/knowledge/project/${currentProject}`;
            } else {
                apiUrl = `/api/knowledge/project/1`;
            }

            const response = await fetch(apiUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            this.knowledgeItems = result.knowledge_items || [];
            this.renderKnowledgeItems();

        } catch (error) {
            console.error('Error loading knowledge data:', error);
            contentElement.innerHTML = '<div class="error-state">Error loading knowledge items</div>';
            showNotification('Error loading knowledge items', 'error');
        }
    }

    renderKnowledgeItems() {
        const contentElement = document.getElementById('knowledgeContent');
        if (!contentElement) return;

        if (this.knowledgeItems.length === 0) {
            contentElement.innerHTML = `
                <div class="empty-state">
                    <h3>No Knowledge Items Found</h3>
                    <p>Start building your knowledge base by adding your first item.</p>
                    <button class="add-first-btn">Add First Item</button>
                </div>
            `;
            return;
        }

        const groupedItems = this.groupItemsByCategory();
        let html = '';

        for (const [category, items] of Object.entries(groupedItems)) {
            html += `
                <div class="knowledge-category">
                    <div class="category-header">
                        <h3 class="category-title">${this.escapeHtml(category || 'Uncategorized')}</h3>
                        <span class="category-count">${items.length} item${items.length !== 1 ? 's' : ''}</span>
                    </div>
                    <div class="category-items">
                        ${items.map(item => this.renderKnowledgeItem(item)).join('')}
                    </div>
                </div>
            `;
        }

        contentElement.innerHTML = html;
    }

    renderKnowledgeItem(item) {
        const tags = Array.isArray(item.tags) ? item.tags : [];
        const priority = item.priority || 1;
        const priorityClass = `priority-${priority}`;

        return `
            <div class="knowledge-item" data-id="${item.id}">
                <div class="item-header">
                    <div class="item-title-section">
                        <h4 class="item-title">${this.escapeHtml(item.title)}</h4>
                        <div class="item-meta">
                            <span class="item-priority ${priorityClass}">Priority ${priority}</span>
                            <span class="item-date">Updated ${this.formatTimestamp(item.updated_at)}</span>
                        </div>
                    </div>
                    <div class="item-actions">
                        <button class="item-action-btn edit-btn" title="Edit Item">
                            <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708L4.707 15.001H1v-3.707L12.146.146zM11.207 1.207L13.707 3.707 14.5 3l-2.5-2.5L11.207 1.207z"/>
                            </svg>
                        </button>
                        <button class="item-action-btn delete-btn" title="Delete Item">
                            <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
                                <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4L4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="item-content">
                    <p class="item-description">${this.escapeHtml(item.content).substring(0, 200)}${item.content.length > 200 ? '...' : ''}</p>
                    ${tags.length > 0 ? `
                        <div class="item-tags">
                            ${tags.map(tag => `<span class="knowledge-tag">${this.escapeHtml(tag)}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    groupItemsByCategory() {
        const groups = {};
        this.knowledgeItems.forEach(item => {
            const category = item.category || 'Uncategorized';
            if (!groups[category]) {
                groups[category] = [];
            }
            groups[category].push(item);
        });

        // Sort items within each category by priority and update date
        Object.values(groups).forEach(items => {
            items.sort((a, b) => {
                const priorityDiff = (b.priority || 1) - (a.priority || 1);
                if (priorityDiff !== 0) return priorityDiff;
                return new Date(b.updated_at) - new Date(a.updated_at);
            });
        });

        return groups;
    }

    async deleteKnowledgeItem(itemId) {
        const item = this.findKnowledgeItemById(itemId);
        if (!item) return;

        // Use the reusable delete confirmation modal
        const { openDeleteModal } = await import('./utils.js');
        openDeleteModal('knowledge', itemId, item.title);
    }

    // This function is called by the confirmation modal after user confirms
    async deleteKnowledgeItemConfirmed(itemId) {
        try {
            const response = await fetch(`/api/knowledge/${itemId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                showNotification('Knowledge item deleted successfully!', 'success');
                await this.loadKnowledgeData();
            } else {
                const result = await response.json();
                showNotification(result.message || 'Failed to delete knowledge item', 'error');
            }
        } catch (error) {
            console.error('Error deleting knowledge item:', error);
            showNotification('Error deleting knowledge item', 'error');
        }
    }

    findKnowledgeItemById(id) {
        return this.knowledgeItems.find(item => item.id === parseInt(id));
    }

    filterKnowledgeItems(searchTerm) {
        const items = document.querySelectorAll('.knowledge-item');
        const clearBtn = document.getElementById('clearSearchBtn');

        if (searchTerm.trim()) {
            clearBtn.style.display = 'block';
        } else {
            clearBtn.style.display = 'none';
        }

        items.forEach(item => {
            const title = item.querySelector('.item-title').textContent.toLowerCase();
            const content = item.querySelector('.item-description').textContent.toLowerCase();
            const searchLower = searchTerm.toLowerCase();

            if (title.includes(searchLower) || content.includes(searchLower)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    }

    filterByCategory(category) {
        const categories = document.querySelectorAll('.knowledge-category');

        categories.forEach(categoryElement => {
            const categoryTitle = categoryElement.querySelector('.category-title').textContent.toLowerCase();

            if (!category || categoryTitle.includes(category.toLowerCase())) {
                categoryElement.style.display = 'block';
            } else {
                categoryElement.style.display = 'none';
            }
        });
    }

    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';

        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) {
                return 'Invalid Date';
            }

            return date.toLocaleString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            console.error('Error formatting timestamp:', timestamp, error);
            return 'Invalid Date';
        }
    }

    escapeHtml(text) {
        if (typeof text !== 'string') return '';

        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Inline editing methods from original implementation
    startInlineEditing(knowledgeId) {
        // Cancel any existing inline edit
        if (this.currentInlineEditItem) {
            this.cancelInlineEditing();
        }

        const item = this.knowledgeItems.find(item => item.id === knowledgeId);
        if (!item) {
            showNotification('Knowledge item not found', 'error');
            return;
        }

        this.currentInlineEditItem = { ...item };
        // Re-render the items to show the inline edit form
        this.renderKnowledgeData();
    }

    renderInlineEditForm(item) {
        return `
            <div class="knowledge-item inline-edit-item" data-knowledge-id="${item.id}">
                <div class="inline-edit-form">
                    <input type="text" class="inline-edit-title" value="${this.escapeHtml(item.title)}" placeholder="Enter title">
                    <textarea class="inline-edit-content" placeholder="Enter content">${this.escapeHtml(item.content)}</textarea>
                    <input type="text" class="inline-edit-category" value="${this.escapeHtml(item.category || '')}" placeholder="Category">
                    <input type="text" class="inline-edit-tags" value="${item.tags ? item.tags.join(', ') : ''}" placeholder="Tags (comma-separated)">
                    <div class="inline-edit-actions">
                        <button class="inline-action-btn save-btn" title="Save Changes" onclick="knowledgeModal.saveInlineEdit(${item.id})">
                            Save
                        </button>
                        <button class="inline-action-btn cancel-btn" title="Cancel Changes" onclick="knowledgeModal.cancelInlineEditing()">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    async saveInlineEdit(knowledgeId) {
        const form = document.querySelector(`.inline-edit-item[data-knowledge-id="${knowledgeId}"]`);
        if (!form) return;

        const title = form.querySelector('.inline-edit-title')?.value?.trim();
        const content = form.querySelector('.inline-edit-content')?.value?.trim();
        const category = form.querySelector('.inline-edit-category')?.value?.trim();
        const tagsValue = form.querySelector('.inline-edit-tags')?.value?.trim();

        if (!title || !content) {
            showNotification('Title and content are required', 'error');
            return;
        }

        try {
            const tags = tagsValue ? tagsValue.split(',').map(tag => tag.trim()).filter(tag => tag) : [];

            const response = await fetch('/api/knowledge', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    knowledge_id: knowledgeId.toString(),
                    title,
                    content,
                    category,
                    tags: JSON.stringify(tags)
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            showNotification('Knowledge item updated successfully', 'success');
            this.currentInlineEditItem = null;
            this.loadKnowledgeData();
        } catch (error) {
            console.error('Error saving inline edit:', error);
            showNotification('Failed to save changes', 'error');
        }
    }

    cancelInlineEditing() {
        this.currentInlineEditItem = null;
        this.renderKnowledgeData();
    }

    // Render all knowledge data (method was missing)
    renderKnowledgeData() {
        this.renderKnowledgeItems();
    }

    // Knowledge logs toggle functionality from original
    async toggleKnowledgeLogs(knowledgeId) {
        const toggleBtn = document.querySelector(`[onclick="knowledgeModal.toggleKnowledgeLogs(${knowledgeId})"]`);
        if (!toggleBtn) return;

        const logsSection = document.querySelector(`#knowledge-logs-${knowledgeId}`);
        if (!logsSection) {
            // Logs section doesn't exist, create and load it
            try {
                const response = await fetch(`/api/knowledge/${knowledgeId}/logs`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const logs = await response.json();
                this.displayKnowledgeLogs(knowledgeId, logs, toggleBtn);
            } catch (error) {
                console.error('Failed to load knowledge logs:', error);
                showNotification('Failed to load logs', 'error');
            }
        } else {
            // Toggle existing logs section
            const isVisible = logsSection.style.display !== 'none';
            logsSection.style.display = isVisible ? 'none' : 'block';
            toggleBtn.textContent = isVisible ? 'Show Logs' : 'Hide Logs';
        }
    }

    displayKnowledgeLogs(knowledgeId, logs, toggleBtn) {
        const knowledgeItem = document.querySelector(`[data-id="${knowledgeId}"]`);
        if (!knowledgeItem) return;

        const logsHtml = `
            <div id="knowledge-logs-${knowledgeId}" class="knowledge-logs">
                <h4>Knowledge Item History</h4>
                ${logs.length === 0 ? '<p>No logs found</p>' :
                    logs.map(log => `
                        <div class="log-entry">
                            <div class="log-meta">
                                <span class="log-date">${this.formatTimestamp(log.created_at)}</span>
                                <span class="log-type">${log.action_type}</span>
                            </div>
                            <div class="log-message">${this.escapeHtml(log.change_reason || 'No reason provided')}</div>
                        </div>
                    `).join('')
                }
            </div>
        `;

        knowledgeItem.insertAdjacentHTML('beforeend', logsHtml);
        toggleBtn.textContent = 'Hide Logs';
    }
}

// Export the delete function for use by the confirmation modal
export async function deleteKnowledgeItemConfirmed(itemId) {
    // Get the knowledge modal instance
    const modal = window.knowledgeModal;
    if (modal && modal.deleteKnowledgeItemConfirmed) {
        await modal.deleteKnowledgeItemConfirmed(itemId);
    } else {
        console.error('Knowledge modal not available for deletion');
    }
}
