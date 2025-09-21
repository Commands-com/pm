// Utility functions and common helpers
import { AppState } from './state.js';

// Escape HTML to prevent XSS
export function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show notification to user
export function showNotification(message, type = 'info', duration = 3000) {
    // Remove existing notification
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    // Add to page
    document.body.appendChild(notification);

    // Show with animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);

    // Auto-hide after duration
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, duration);
}

// Save selection state to localStorage
export function saveSelectionState() {
    const state = {
        selectedProjectId: AppState.selectedProjectId,
        selectedEpicId: AppState.selectedEpicId,
        todoViewMode: AppState.todoViewMode
    };
    localStorage.setItem('pm-dashboard-selection', JSON.stringify(state));
}

// Load selection state from localStorage
export function loadSelectionState() {
    try {
        const saved = localStorage.getItem('pm-dashboard-selection');
        if (saved) {
            const state = JSON.parse(saved);
            AppState.selectedProjectId = state.selectedProjectId;
            AppState.selectedEpicId = state.selectedEpicId;
            AppState.todoViewMode = state.todoViewMode || 'TODO';
        }
    } catch (error) {
        console.error('Failed to load selection state:', error);
    }
}

// Update delete button visibility based on selections
export function updateDeleteButtonVisibility() {
    const deleteBtn = document.getElementById('deleteFilterBtn');
    if (!deleteBtn) return;

    const hasSelection = AppState.selectedProjectId || AppState.selectedEpicId;
    deleteBtn.style.display = hasSelection ? 'flex' : 'none';
}

// Get filtered tasks based on current selections
export function getFilteredTasks() {
    const allTasks = Array.from(AppState.tasks.values());

    return allTasks.filter(task => {
        // Project filter
        if (AppState.selectedProjectId && task.project_id != AppState.selectedProjectId) {
            return false;
        }

        // Epic filter
        if (AppState.selectedEpicId && task.epic_id != AppState.selectedEpicId) {
            return false;
        }

        // Todo view mode filter
        if (AppState.todoViewMode === 'TODO') {
            return task.status !== 'BACKLOG';
        }

        return true;
    });
}

// Format date for display
export function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    } catch (error) {
        return dateString;
    }
}

// Format relative time (e.g., "2 hours ago")
export function formatRelativeTime(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    } catch (error) {
        return dateString;
    }
}

// Debounce function to limit API calls
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Deep clone object
export function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime());
    if (obj instanceof Array) return obj.map(item => deepClone(item));
    if (typeof obj === 'object') {
        const clonedObj = {};
        Object.keys(obj).forEach(key => {
            clonedObj[key] = deepClone(obj[key]);
        });
        return clonedObj;
    }
}

export function setupEventListeners() {
    // Project selector change
    const projectSelect = document.getElementById('projectSelect');
    if (projectSelect) {
        projectSelect.addEventListener('change', async (e) => {
            AppState.selectedProjectId = e.target.value || null;
            AppState.selectedEpicId = null; // Reset epic selection
            saveSelectionState();
            const { populateEpicSelector } = await import('./filters.js');
            populateEpicSelector();
            updateDeleteButtonVisibility();
            const { applyFilters } = await import('./board.js');
            applyFilters();
        });
    }

    // Epic selector change
    const epicSelect = document.getElementById('epicSelect');
    if (epicSelect) {
        epicSelect.addEventListener('change', async (e) => {
            AppState.selectedEpicId = e.target.value || null;
            saveSelectionState();
            updateDeleteButtonVisibility();
            const { applyFilters } = await import('./board.js');
            applyFilters();
        });
    }

    // Delete filter button
    const deleteBtn = document.getElementById('deleteFilterBtn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', () => {
            if (AppState.selectedEpicId) {
                openDeleteModal('epic', AppState.selectedEpicId);
            } else if (AppState.selectedProjectId) {
                openDeleteModal('project', AppState.selectedProjectId);
            }
        });
    }

    // Knowledge button
    const knowledgeBtn = document.getElementById('knowledgeBtn');
    if (knowledgeBtn) {
        knowledgeBtn.addEventListener('click', () => {
            if (window.knowledgeModal) {
                window.knowledgeModal.open();
            }
        });
    }

    // Assumption Insights button
    const assumptionInsightsBtn = document.getElementById('assumptionInsightsBtn');
    if (assumptionInsightsBtn) {
        assumptionInsightsBtn.addEventListener('click', async () => {
            if (window.assumptionInsightsModal) {
                await window.assumptionInsightsModal.open();
            }
        });
    }

    initializeDeleteModal();
}

// API helper functions
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

async function deleteProject(projectId) {
    try {
        await apiRequest(`/api/projects/${projectId}`, { method: 'DELETE' });
        showNotification('Project deleted successfully', 'success');
    } catch (error) {
        showNotification('Failed to delete project', 'error');
    }
}

async function deleteEpic(epicId) {
    try {
        await apiRequest(`/api/epics/${epicId}`, { method: 'DELETE' });
        showNotification('Epic deleted successfully', 'success');
    } catch (error) {
        showNotification('Failed to delete epic', 'error');
    }
}

export function openDeleteModal(type, id, name) {
    const deleteModal = document.getElementById('deleteConfirmModal');
    const message = document.getElementById('deleteModalMessage');
    if (deleteModal && message) {
        deleteModal.dataset.deleteType = type;
        deleteModal.dataset.deleteId = id;

        // Derive name if not provided
        if (!name) {
            if (type === 'project') {
                const project = AppState.projects.get(String(id));
                name = project ? project.name : 'Unknown Project';
            } else if (type === 'epic') {
                const epic = AppState.epics.get(String(id));
                name = epic ? epic.name : 'Unknown Epic';
            } else if (type === 'task') {
                const task = AppState.tasks.get(String(id));
                name = task ? task.name : 'Unknown Task';
            }
        }

        message.textContent = `Are you sure you want to delete this ${type}: "${name}"?`;
        deleteModal.style.display = 'flex';
    }
}

function closeDeleteModal() {
    const deleteModal = document.getElementById('deleteConfirmModal');
    if (deleteModal) {
        deleteModal.style.display = 'none';
    }
}

async function confirmDelete() {
    const deleteModal = document.getElementById('deleteConfirmModal');
    const deleteType = deleteModal?.dataset?.deleteType;
    const deleteId = deleteModal?.dataset?.deleteId;

    if (!deleteType || !deleteId) {
        console.error('Missing delete type or ID');
        return;
    }

    try {
        if (deleteType === 'project') {
            await deleteProject(deleteId);
        } else if (deleteType === 'epic') {
            await deleteEpic(deleteId);
        } else if (deleteType === 'task') {
            const { deleteTask } = await import('./board.js');
            await deleteTask(deleteId);
        }

        closeDeleteModal();
    } catch (error) {
        console.error('Delete confirmation failed:', error);
        showNotification('Delete operation failed', 'error');
    }
}

function initializeDeleteModal() {
    const deleteModal = document.getElementById('deleteConfirmModal');
    if (deleteModal) {
        const closeBtn = deleteModal.querySelector('.modal-close-btn');
        const cancelBtn = deleteModal.querySelector('.modal-btn-cancel');
        const confirmBtn = document.getElementById('confirmDeleteBtn');

        if (closeBtn) {
            closeBtn.addEventListener('click', closeDeleteModal);
        }
        if (cancelBtn) {
            cancelBtn.addEventListener('click', closeDeleteModal);
        }
        if (confirmBtn) {
            confirmBtn.addEventListener('click', confirmDelete);
        }
    }
}