// Board rendering and task management functions
import { AppState } from './state.js';
import { showNotification, escapeHtml, getFilteredTasks, openDeleteModal } from './utils.js';
import { initializeDragAndDrop, getDragDropManager } from './drag-drop.js';

// Load board data from API
export async function loadBoardData() {
    try {
        const response = await fetch('/api/board/state');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update AppState with loaded data
        AppState.tasks.clear();
        AppState.projects.clear();
        AppState.epics.clear();

        // Populate tasks
        if (data.tasks) {
            data.tasks.forEach(task => {
                AppState.tasks.set(String(task.id), task);
            });
        }

        // Populate projects
        if (data.projects) {
            data.projects.forEach(project => {
                AppState.projects.set(String(project.id), project);
            });
        }

        // Populate epics
        if (data.epics) {
            data.epics.forEach(epic => {
                AppState.epics.set(String(epic.id), epic);
            });
        }

        // Initialize drag and drop functionality before rendering so cards get wired correctly
        initializeDragAndDrop();

        // Render the board
        renderAllTasks();
        updateTaskCounts();

    } catch (error) {
        console.error('Failed to load board data:', error);
        showNotification('Failed to load board data', 'error');
    }
}

// Alias for backward compatibility
export const loadBoardState = loadBoardData;

// Render all tasks on the board
export function renderAllTasks() {
    // Clear all columns
    const columns = ['TODO', 'IN_PROGRESS', 'REVIEW', 'DONE'];
    columns.forEach(status => {
        const container = document.getElementById(`${status.toLowerCase()}-tasks`);
        if (container) {
            container.innerHTML = '';
        }
    });

    // Render filtered tasks
    const filteredTasks = getFilteredTasks();
    filteredTasks.forEach(task => {
        renderTask(task);
    });
}

// Render a single task card
export function renderTask(task) {
    const taskElement = createTaskElement(task);
    const statusColumn = getStatusColumn(task.status);

    if (statusColumn) {
        // Remove existing task element if it exists
        const existingElement = document.getElementById(`task-${task.id}`);
        if (existingElement) {
            existingElement.remove();
        }

        statusColumn.appendChild(taskElement);
    }
}

// Create task DOM element
function createTaskElement(task) {
    const taskDiv = document.createElement('div');
    taskDiv.className = `task-card${task.lock_holder ? ' locked' : ''}`;
    taskDiv.id = `task-${task.id}`;
    taskDiv.draggable = !task.lock_holder;
    // Ensure drag manager has access to task id even if not initialized yet
    taskDiv.setAttribute('data-task-id', String(task.id));
    if (!task.lock_holder) {
        taskDiv.classList.add('draggable-task');
    } else {
        taskDiv.classList.add('locked-task');
        taskDiv.title = `Task locked by ${task.lock_holder}`;
    }

    // Add click event to open modal
    taskDiv.addEventListener('click', (e) => {
        // Don't trigger modal on action button clicks
        if (!e.target.closest('.task-action-btn')) {
            openTaskModal(task);
        }
    });

    const projectBreadcrumb = buildProjectBreadcrumb(task);
    const taskIndicators = buildTaskIndicators(task);
    const taskMeta = buildTaskMeta(task);

    taskDiv.innerHTML = `
        ${projectBreadcrumb}
        <div class="task-title">${escapeHtml(task.name)}</div>
        ${taskIndicators}
        ${taskMeta}
        <div class="task-actions">
            <button class="task-action-btn move-task-btn" title="Move task">
                ↔
            </button>
            <button class="task-action-btn delete-task-btn" title="Delete task">
                ×
            </button>
        </div>
    `;

    // Add event listeners for action buttons
    const moveBtn = taskDiv.querySelector('.move-task-btn');
    if (moveBtn) {
        moveBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleMoveTask(task);
        });
    }

    const deleteBtn = taskDiv.querySelector('.delete-task-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleDeleteTask(task);
        });
    }

    // Set up drag and drop functionality
    const dragDropManager = getDragDropManager();
    if (dragDropManager) {
        dragDropManager.makeDraggable(taskDiv, task);
    }

    return taskDiv;
}

// Get status column element
function getStatusColumn(status) {
    const statusMap = {
        'TODO': 'todo-tasks',
        'BACKLOG': 'todo-tasks',
        'IN_PROGRESS': 'in_progress-tasks',
        'REVIEW': 'review-tasks',
        'DONE': 'done-tasks'
    };

    const columnId = statusMap[status] || 'todo-tasks';
    return document.getElementById(columnId);
}

// Build task indicators (complexity, mode, dependencies, etc.)
function buildTaskIndicators(task) {
    const indicators = [];

    // Complexity score with color coding
    if (task.complexity_score || task.ra_score) {
        const score = task.complexity_score || task.ra_score;
        const scoreClass = getScoreClass(score);
        indicators.push(`<span class="complexity-badge ${scoreClass}">${score}</span>`);
    }

    // RA Mode
    if (task.mode_used || task.ra_mode) {
        const mode = (task.mode_used || task.ra_mode).toLowerCase().replace('_', '-');
        indicators.push(`<span class="mode-badge ${mode}">${task.ra_mode || task.mode_used}</span>`);
    }

    // Dependencies count
    if (task.dependencies_count && task.dependencies_count > 0) {
        indicators.push(`<span class="dependencies-count">⚡ ${task.dependencies_count} deps</span>`);
    }

    // Verification status
    if (task.verification_status) {
        const status = task.verification_status.toLowerCase();
        indicators.push(`<span class="verification-status ${status}">${task.verification_status}</span>`);
    }

    // RA tags summary
    if (task.ra_tags && task.ra_tags.length > 0) {
        const tagSummary = buildRATagsSummary(task.ra_tags);
        indicators.push(`<div class="ra-tags-summary">${tagSummary}</div>`);
    }

    // Adaptive scoring (predicted vs actual)
    if (task.predicted_complexity && task.complexity_score &&
        task.predicted_complexity !== task.complexity_score) {
        const adaptiveScore = `
            <div class="adaptive-scoring">
                <span class="score-comparison">
                    Predicted: ${task.predicted_complexity}
                    <span class="score-arrow">→</span>
                    Actual: ${task.complexity_score}
                </span>
            </div>
        `;
        indicators.push(adaptiveScore);
    }

    return indicators.length > 0 ? `<div class="task-indicators">${indicators.join('')}</div>` : '';
}

// Get CSS class for complexity score
function getScoreClass(score) {
    const numScore = parseInt(score);
    if (numScore >= 1 && numScore <= 3) return 'score-1-3';
    if (numScore >= 4 && numScore <= 6) return 'score-4-6';
    if (numScore >= 7 && numScore <= 8) return 'score-7-8';
    if (numScore >= 9 && numScore <= 10) return 'score-9-10';
    return 'score-1-3'; // default
}

// #COMPLETION_DRIVE_RA: Build RA tags summary with category breakdown
// Assumption: RA tags are objects with 'category' and 'count' or simple array of tag objects
function buildRATagsSummary(raTags) {
    if (!raTags || raTags.length === 0) return '';

    // Count tags by category (simplified approach for now)
    let totalTags = Array.isArray(raTags) ? raTags.length : 0;
    let implTags = 0;
    let suggestTags = 0;

    // If tags have category information, count them
    if (Array.isArray(raTags)) {
        raTags.forEach(tag => {
            if (typeof tag === 'object' && tag.category) {
                if (tag.category.includes('IMPL') || tag.category.includes('COMPLETION_DRIVE')) {
                    implTags++;
                } else if (tag.category.includes('SUGGEST')) {
                    suggestTags++;
                }
            }
        });
    }

    let summary = `<span class="ra-tag-count">${totalTags} tags</span>`;

    if (implTags > 0 || suggestTags > 0) {
        const breakdown = [];
        if (implTags > 0) breakdown.push(`${implTags} impl`);
        if (suggestTags > 0) breakdown.push(`${suggestTags} suggest`);
        summary += ` <span style="font-size: 0.65rem;">(${breakdown.join(', ')})</span>`;
    }

    return summary;
}

// #COMPLETION_DRIVE_UX: Build project breadcrumb navigation context
// Assumption: Task object may contain project_name and epic_name fields
function buildProjectBreadcrumb(task) {
    // Show breadcrumbs in these cases:
    // 1. No project selected (All Projects) - show Project → Epic
    // 2. Project selected but no epic (All Epics in Project) - show Epic only
    const noProjectSelected = !AppState.selectedProjectId;
    const projectSelectedNoEpic = AppState.selectedProjectId && !AppState.selectedEpicId;
    const showBreadcrumb = noProjectSelected || projectSelectedNoEpic;

    if (!showBreadcrumb) return '';

    const parts = [];

    // Look up project and epic names from IDs if not directly available
    let projectName = task.project_name;
    let epicName = task.epic_name;

    // If we have epic_id but no epic_name, look it up
    if (task.epic_id && !epicName) {
        const epic = AppState.epics.get(String(task.epic_id));
        if (epic) {
            epicName = epic.name;
            // Also get project name from epic if not available on task
            if (epic.project_id && !projectName) {
                const project = AppState.projects.get(String(epic.project_id));
                if (project) {
                    projectName = project.name;
                }
            }
        }
    }

    // Determine what to show based on current filter state
    if (noProjectSelected) {
        // All Projects view - show Project → Epic
        if (projectName) parts.push(escapeHtml(projectName));
        if (epicName) parts.push(escapeHtml(epicName));
    } else if (projectSelectedNoEpic) {
        // Project selected, All Epics in Project view - show Epic only
        if (epicName) parts.push(escapeHtml(epicName));
    }

    if (parts.length === 0) return '';

    return `
        <div class="project-breadcrumb">
            ${parts.join('<span class="breadcrumb-separator">→</span>')}
        </div>
    `;
}

// #COMPLETION_DRIVE_UX: Build task metadata section with existing agent/lock info
// Pattern: Maintain existing functionality while adding RA context
function buildTaskMeta(task) {
    const lockInfo = task.lock_holder ?
        `<span class="task-locked-info">🔒 ${task.lock_holder}</span>` : '';

    const agentInfo = task.agent_id ?
        `<span class="task-agent">${task.agent_id}</span>` : '';

    return `
        <div class="task-meta">
            <span>${agentInfo}</span>
            <span>${lockInfo}</span>
        </div>
    `;
}

// Update task counts in column headers
export function updateTaskCounts() {
    const columns = ['TODO', 'IN_PROGRESS', 'REVIEW', 'DONE'];
    const filteredTasks = getFilteredTasks();

    columns.forEach(status => {
        const count = filteredTasks.filter(task => {
            if (status === 'TODO') {
                return task.status === 'TODO' || task.status === 'BACKLOG';
            }
            return task.status === status;
        }).length;

        const countElement = document.getElementById(`${status.toLowerCase()}-count`);
        if (countElement) {
            countElement.textContent = `${count} tasks`;
        }
    });
}

// Apply current filters to get filtered task list
export function applyFilters() {
    renderAllTasks();
    updateTaskCounts();
}


function openTaskModal(task) {
    // Implementation for opening task modal
    if (window.taskDetailModal) {
        window.taskDetailModal.open(task);
    }
}

function handleMoveTask(task) {
    if (!task) return;

    // Toggle between TODO and BACKLOG status
    const newStatus = (task.status === 'TODO' || task.status === 'todo') ? 'BACKLOG' : 'TODO';

    // Optimistic update: immediately update local state and UI
    const previousStatus = task.status;
    task.status = newStatus;
    AppState.tasks.set(String(task.id), task);

    // Add task to pending updates to avoid conflicts with WebSocket updates
    AppState.pendingUpdates.set(String(task.id), true);

    // Re-render the board immediately to show the change
    renderAllTasks();
    updateTaskCounts();

    // Use drag-drop manager for backend status updates
    const dragDropManager = getDragDropManager();
    if (dragDropManager) {
        dragDropManager.updateTaskStatus(task.id, newStatus)
            .then(() => {
                // Remove from pending updates on success
                AppState.pendingUpdates.delete(String(task.id));
                showNotification(`Task moved to ${newStatus}`, 'success');
            })
            .catch(error => {
                // Revert optimistic update on failure
                task.status = previousStatus;
                AppState.tasks.set(String(task.id), task);
                AppState.pendingUpdates.delete(String(task.id));
                renderAllTasks();
                updateTaskCounts();
                console.error('Failed to move task:', error);
                showNotification('Failed to move task', 'error');
            });
    }
}

export async function deleteTask(taskId) {
    // Implementation for deleting tasks
    console.log('Delete task:', taskId);
    // TODO: Implement actual deletion via API
    const task = AppState.tasks.get(String(taskId));
    if (task) {
        AppState.tasks.delete(String(taskId));
        renderAllTasks();
        updateTaskCounts();
        showNotification(`Task "${task.name}" deleted locally.`, 'info');
    }
}

function handleDeleteTask(task) {
    if (!task) {
        return;
    }

    openDeleteModal('task', task.id, task.name);
}

