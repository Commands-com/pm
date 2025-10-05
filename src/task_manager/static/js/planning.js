// Planning Mode JavaScript
// Handles file tree navigation, markdown rendering, and live updates

class PlanningApp {
    constructor() {
        this.socket = null;
        this.currentFile = null;
        this.files = { prds: [], epics: [] };

        this.init();
    }

    async init() {
        console.log('Initializing Planning Mode');

        // Setup event listeners
        this.setupEventListeners();

        // Initialize WebSocket connection
        this.initializeWebSocket();

        // Load initial file list
        await this.loadFileList();
    }

    setupEventListeners() {
        // Back to dashboard button
        const backBtn = document.getElementById('backToDashboard');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                window.location.href = '/';
            });
        }

        // Refresh files button
        const refreshBtn = document.getElementById('refreshFiles');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshFiles();
            });
        }

        // Open in editor button
        const openEditorBtn = document.getElementById('openInEditor');
        if (openEditorBtn) {
            openEditorBtn.addEventListener('click', () => {
                if (this.currentFile) {
                    this.openInExternalEditor(this.currentFile.path);
                } else {
                    this.showToast('error', 'No File Selected', 'Please select a file first');
                }
            });
        } else {
            console.error('Open in editor button not found');
        }

        // Archive section toggle
        const archiveHeader = document.getElementById('archive-header');
        if (archiveHeader) {
            archiveHeader.addEventListener('click', () => {
                this.toggleArchiveSection();
            });
        }

        // Tasks section toggle
        const tasksHeader = document.getElementById('tasks-header');
        if (tasksHeader) {
            tasksHeader.addEventListener('click', () => {
                this.toggleTasksSection();
            });
        }
    }

    initializeWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/planning`;

            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                console.log('Planning WebSocket connected');
                this.updateConnectionStatus('connected');
            };

            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };

            this.socket.onclose = () => {
                console.log('Planning WebSocket disconnected');
                this.updateConnectionStatus('disconnected');

                // Attempt to reconnect after 3 seconds
                setTimeout(() => {
                    this.initializeWebSocket();
                }, 3000);
            };

            this.socket.onerror = (error) => {
                console.error('Planning WebSocket error:', error);
                this.updateConnectionStatus('disconnected');
            };

        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
            this.updateConnectionStatus('disconnected');
        }
    }

    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connectionStatus');
        if (statusElement) {
            statusElement.className = `connection-status ${status}`;
            switch (status) {
                case 'connected':
                    statusElement.textContent = 'Connected';
                    break;
                case 'connecting':
                    statusElement.textContent = 'Connecting...';
                    break;
                case 'disconnected':
                    statusElement.textContent = 'Disconnected';
                    break;
            }
        }
    }

    handleWebSocketMessage(data) {
        console.log('Planning WebSocket message:', data);

        switch (data.event_type) {
            case 'file_updated':
                this.handleFileUpdate(data);
                break;
            case 'file_deleted':
                this.handleFileDelete(data);
                break;
            case 'file_created':
                this.handleFileCreate(data);
                break;
        }
    }

    // Determine if an incoming event refers to the currently open file.
    isEventForCurrentFile(data) {
        if (!this.currentFile) return false;

        try {
            // Primary: match by filename + type (more robust across path formats)
            const byNameAndType = (
                data.filename === this.currentFile.filename &&
                (data.file_type === this.currentFile.type ||
                 // File watcher sends singular, frontend stores plural; handle both
                 (data.file_type === 'prd' && this.currentFile.type === 'prds') ||
                 (data.file_type === 'epic' && this.currentFile.type === 'epics'))
            );

            if (byNameAndType) return true;

            // Fallback: compare paths allowing absolute vs relative differences
            if (data.file_path && this.currentFile.path) {
                const a = String(data.file_path);
                const b = String(this.currentFile.path);
                if (a === b || a.endsWith(b) || b.endsWith(a)) return true;
            }
        } catch (e) {
            console.warn('Failed to compare event to current file:', e);
        }

        return false;
    }

    async handleFileUpdate(data) {
        // If the currently displayed file was updated, reload its content (robust matching)
        if (this.isEventForCurrentFile(data)) {
            await this.loadFile(this.currentFile.type, this.currentFile.filename);
        }

        // Refresh the file list to update modification times
        await this.loadFileList();
    }

    async handleFileDelete(data) {
        // If the currently displayed file was deleted, show welcome view
        if (this.currentFile && data.file_path === this.currentFile.path) {
            this.showWelcomeView();
            this.currentFile = null;
        }

        // Refresh the file list
        await this.loadFileList();
    }

    async handleFileCreate(data) {
        // Refresh the file list to show new files
        await this.loadFileList();
    }

    async loadFileList() {
        try {
            const [activeResponse, archiveResponse] = await Promise.all([
                fetch('/api/planning/files'),
                fetch('/api/planning/archive/files')
            ]);

            const activeData = await activeResponse.json();
            const archiveData = await archiveResponse.json();

            if (activeData.success) {
                this.files = {
                    prds: activeData.prds || [],
                    epics: activeData.epics || [],
                    tasks: activeData.tasks || []
                };

                this.renderFileTree();
            } else {
                console.error('Failed to load file list:', activeData.error);
                this.showError('Failed to load planning files');
            }

            if (archiveData.success) {
                this.archivedFiles = {
                    prds: archiveData.prds || [],
                    epics: archiveData.epics || [],
                    tasks: archiveData.tasks || []
                };

                this.renderArchiveTree();
            }
        } catch (error) {
            console.error('Error loading file list:', error);
            this.showError('Failed to connect to server');
        }
    }

    renderFileTree() {
        this.renderFileSection('prd-files', this.files.prds, 'prds');
        this.renderFileSection('epic-files', this.files.epics, 'epics');
        this.renderFileSection('task-files', this.files.tasks, 'tasks');
    }

    renderFileSection(containerId, files, fileType, isArchived = false) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (files.length === 0) {
            container.innerHTML = '<div class="no-files">No files found</div>';
            return;
        }

        const fileElements = files.map(file => {
            const isActive = this.currentFile &&
                            this.currentFile.filename === file.filename &&
                            this.currentFile.type === fileType;

            const archiveAction = isArchived ? 'unarchive' : 'archive';
            const archiveIcon = isArchived
                ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3h18v18H3z"/><path d="M12 8v8"/><path d="M8 12h8"/></svg>`
                : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/></svg>`;

            return `
                <div class="file-item ${isActive ? 'active' : ''}"
                     data-type="${fileType}"
                     data-filename="${file.filename}"
                     data-archived="${isArchived}"
                     title="${file.name}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14,2 14,8 20,8"></polyline>
                    </svg>
                    <span class="file-name">${file.name}</span>
                    <button class="archive-btn" data-action="${archiveAction}" title="${archiveAction === 'archive' ? 'Archive' : 'Unarchive'}" onclick="event.stopPropagation()">
                        ${archiveIcon}
                    </button>
                </div>
            `;
        }).join('');

        container.innerHTML = fileElements;

        // Add click event listeners for files
        container.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', () => {
                const fileType = item.dataset.type;
                const filename = item.dataset.filename;
                this.loadFile(fileType, filename);
            });

            // Add archive/unarchive button listener
            const archiveBtn = item.querySelector('.archive-btn');
            if (archiveBtn) {
                archiveBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const action = archiveBtn.dataset.action;
                    const fileType = item.dataset.type;
                    const filename = item.dataset.filename;

                    if (action === 'archive') {
                        await this.archiveFile(fileType, filename);
                    } else {
                        await this.unarchiveFile(fileType, filename);
                    }
                });
            }
        });
    }

    async loadFile(fileType, filename) {
        try {
            // Show loading state
            this.showLoading();

            const response = await fetch(`/api/planning/file/${fileType}/${filename}`);
            const data = await response.json();

            if (data.success) {
                this.currentFile = {
                    type: fileType,
                    filename: data.filename,
                    path: data.path,
                    content: data.content,
                    modified: data.modified,
                    size: data.size
                };

                this.renderDocument(data);
                this.updateActiveFile();
            } else {
                console.error('Failed to load file:', data.error);
                this.showError(`Failed to load ${filename}`);
            }
        } catch (error) {
            console.error('Error loading file:', error);
            this.showError('Failed to load file');
        }
    }

    renderDocument(fileData) {
        // Hide welcome view and show document view
        document.getElementById('welcome-view').style.display = 'none';
        document.getElementById('document-view').style.display = 'flex';

        // Update document header
        document.getElementById('document-title').textContent = fileData.filename.replace('.md', '');

        const typeElement = document.getElementById('document-type');
        typeElement.textContent = fileData.type.toUpperCase();
        typeElement.className = `document-type ${fileData.type}`;

        const modifiedDate = new Date(fileData.modified).toLocaleString();
        document.getElementById('last-modified').textContent = `Last modified: ${modifiedDate}`;

        // Render markdown content
        const contentElement = document.getElementById('document-content');
        try {
            const html = marked.parse(fileData.content);
            contentElement.innerHTML = html;
        } catch (error) {
            console.error('Error rendering markdown:', error);
            contentElement.innerHTML = `<pre>${fileData.content}</pre>`;
        }

        // Scroll to top
        contentElement.scrollTop = 0;
    }

    updateActiveFile() {
        // Remove active class from all file items
        document.querySelectorAll('.file-item').forEach(item => {
            item.classList.remove('active');
        });

        // Add active class to current file
        if (this.currentFile) {
            const activeItem = document.querySelector(
                `.file-item[data-type="${this.currentFile.type}"][data-filename="${this.currentFile.filename}"]`
            );
            if (activeItem) {
                activeItem.classList.add('active');
            }
        }
    }

    showWelcomeView() {
        document.getElementById('welcome-view').style.display = 'flex';
        document.getElementById('document-view').style.display = 'none';
        this.currentFile = null;
        this.updateActiveFile();
    }

    showLoading() {
        const contentElement = document.getElementById('document-content');
        if (contentElement) {
            contentElement.innerHTML = `
                <div class="loading" style="justify-content: center; padding: 2rem;">
                    <span class="spinner"></span>
                    Loading document...
                </div>
            `;
        }
    }

    showError(message) {
        const contentElement = document.getElementById('document-content');
        if (contentElement) {
            contentElement.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: #dc2626;">
                    <p>Error: ${message}</p>
                    <button onclick="window.location.reload()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #dc2626; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        Reload Page
                    </button>
                </div>
            `;
        }
    }

    renderArchiveTree() {
        if (!this.archivedFiles) {
            this.archivedFiles = { prds: [], epics: [], tasks: [] };
        }
        this.renderFileSection('archived-prd-files', this.archivedFiles.prds, 'prds', true);
        this.renderFileSection('archived-epic-files', this.archivedFiles.epics, 'epics', true);
        this.renderFileSection('archived-task-files', this.archivedFiles.tasks || [], 'tasks', true);
    }

    toggleArchiveSection() {
        const archiveContent = document.getElementById('archive-content');
        const archiveHeader = document.getElementById('archive-header');

        if (archiveContent && archiveHeader) {
            const isCollapsed = archiveContent.style.display === 'none';
            archiveContent.style.display = isCollapsed ? 'block' : 'none';
            archiveHeader.classList.toggle('collapsed', !isCollapsed);
        }
    }

    toggleTasksSection() {
        const tasksContent = document.getElementById('tasks-content');
        const tasksHeader = document.getElementById('tasks-header');

        if (tasksContent && tasksHeader) {
            const isCollapsed = tasksContent.style.display === 'none';
            tasksContent.style.display = isCollapsed ? 'block' : 'none';
            tasksHeader.classList.toggle('collapsed', !isCollapsed);
        }
    }

    async archiveFile(fileType, filename) {
        try {
            // Remove 's' from fileType to get singular form (prds -> prd, epics -> epic)
            const singularFileType = fileType.endsWith('s') ? fileType.slice(0, -1) : fileType;

            const response = await fetch('/api/planning/archive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_type: singularFileType,
                    filename: filename
                })
            });

            const data = await response.json();

            if (data.success) {
                const archivedCount = data.archived_files?.length || 1;
                const fileList = data.archived_files?.map(f => f.filename).join(', ') || filename;

                if (archivedCount > 1) {
                    this.showToast('success', 'Files Archived',
                        `Archived ${archivedCount} file(s): ${fileList}`);
                } else {
                    this.showToast('success', 'File Archived', `${filename} has been archived`);
                }

                // If currently viewing any of the archived files, show welcome view
                if (this.currentFile && data.archived_files?.some(f => f.filename === this.currentFile.filename)) {
                    this.showWelcomeView();
                }

                // Refresh file lists
                await this.loadFileList();
            } else {
                this.showToast('error', 'Archive Failed', data.error || 'Failed to archive file');
            }
        } catch (error) {
            console.error('Error archiving file:', error);
            this.showToast('error', 'Archive Failed', 'An error occurred');
        }
    }

    async unarchiveFile(fileType, filename) {
        try {
            // Remove 's' from fileType to get singular form
            const singularFileType = fileType.endsWith('s') ? fileType.slice(0, -1) : fileType;

            const response = await fetch('/api/planning/unarchive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_type: singularFileType,
                    filename: filename
                })
            });

            const data = await response.json();

            if (data.success) {
                const unarchivedCount = data.unarchived_files?.length || 1;
                const fileList = data.unarchived_files?.map(f => f.filename).join(', ') || filename;
                const conflicts = data.conflicts?.length || 0;

                let message = '';
                if (unarchivedCount > 1) {
                    message = `Unarchived ${unarchivedCount} file(s): ${fileList}`;
                    if (conflicts > 0) {
                        message += ` (${conflicts} skipped - already exists)`;
                    }
                } else {
                    message = `${filename} has been restored`;
                }

                this.showToast('success', 'Files Unarchived', message);

                // Refresh file lists
                await this.loadFileList();
            } else {
                this.showToast('error', 'Unarchive Failed', data.error || 'Failed to unarchive file');
            }
        } catch (error) {
            console.error('Error unarchiving file:', error);
            this.showToast('error', 'Unarchive Failed', 'An error occurred');
        }
    }

    refreshFiles() {
        const refreshBtn = document.getElementById('refreshFiles');
        const svg = refreshBtn?.querySelector('svg');

        // Add spinning animation
        if (svg) {
            svg.style.animation = 'spin 0.5s linear';
        }

        // Show toast notification
        this.showToast('info', 'Refreshing Files', 'Loading latest file list...');

        // Load file list and handle completion
        this.loadFileList().then(() => {
            this.showToast('success', 'Files Refreshed', 'File list updated successfully');
        }).catch((error) => {
            console.error('Error refreshing files:', error);
            this.showToast('error', 'Refresh Failed', 'Unable to refresh file list');
        }).finally(() => {
            // Remove animation after completion
            if (svg) {
                setTimeout(() => {
                    svg.style.animation = '';
                }, 100);
            }
        });
    }

    openInExternalEditor(filePath) {
        // Validate file path
        if (!filePath) {
            this.showToast('error', 'Copy Failed', 'No file path available');
            return;
        }

        // Copy the path to clipboard with modern toast notification
        if (navigator.clipboard) {
            navigator.clipboard.writeText(filePath).then(() => {
                this.showToast('success', 'Copied to Clipboard', filePath);
            }).catch((err) => {
                console.error('Clipboard copy failed:', err);
                this.showToast('error', 'Copy Failed', 'Unable to copy to clipboard');
            });
        } else {
            // Fallback for browsers without clipboard API
            console.log('Clipboard API not available, showing file path');
            this.showToast('info', 'File Path', filePath);
        }
    }

    showToast(type, title, message, duration = 4000) {
        const container = document.getElementById('toast-container');
        if (!container) {
            console.error('Toast container not found');
            return;
        }

        const toastId = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.id = toastId;

        // Icon based on type
        let iconSvg = '';
        switch (type) {
            case 'success':
                iconSvg = `
                    <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M9 12l2 2 4-4"/>
                        <circle cx="12" cy="12" r="10"/>
                    </svg>
                `;
                break;
            case 'error':
                iconSvg = `
                    <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="15" y1="9" x2="9" y2="15"/>
                        <line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                `;
                break;
            case 'info':
            default:
                iconSvg = `
                    <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="16" x2="12" y2="12"/>
                        <line x1="12" y1="8" x2="12.01" y2="8"/>
                    </svg>
                `;
                break;
        }

        toast.innerHTML = `
            ${iconSvg}
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="window.planningApp.dismissToast('${toastId}')" aria-label="Close">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
        `;

        container.appendChild(toast);

        // Trigger the show animation
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // Auto-dismiss after duration
        setTimeout(() => {
            this.dismissToast(toastId);
        }, duration);
    }

    dismissToast(toastId) {
        const toast = document.getElementById(toastId);
        if (!toast) return;

        toast.classList.remove('show');

        // Remove from DOM after animation
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }
}

// Initialize the planning app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.planningApp = new PlanningApp();
});

// Export for potential use by other modules
window.PlanningApp = PlanningApp;
