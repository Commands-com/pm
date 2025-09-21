// Drag and Drop functionality for kanban task movement
import { AppState } from './app.js';
import { showNotification } from './utils.js';

export class DragDropManager {
    constructor() {
        this.draggedTask = null;
        this.draggedElement = null;
        this.dragPlaceholder = null;
        this.initializeDragAndDrop();
    }

    initializeDragAndDrop() {
        // Set up drag and drop event listeners on the board container
        const board = document.querySelector('.board');
        if (board) {
            board.addEventListener('dragstart', this.handleDragStart.bind(this));
            board.addEventListener('dragover', this.handleDragOver.bind(this));
            board.addEventListener('dragenter', this.handleDragEnter.bind(this));
            board.addEventListener('dragleave', this.handleDragLeave.bind(this));
            board.addEventListener('drop', this.handleDrop.bind(this));
            board.addEventListener('dragend', this.handleDragEnd.bind(this));
        }
    }

    // Make task cards draggable when they're created
    makeDraggable(taskElement, task) {
        if (!taskElement || !task) return;

        // Only make draggable if not locked
        const isDraggable = !task.lock_holder;
        taskElement.draggable = isDraggable;

        if (isDraggable) {
            taskElement.setAttribute('data-task-id', task.id);
            taskElement.classList.add('draggable-task');
        } else {
            taskElement.classList.add('locked-task');
            taskElement.title = `Task locked by ${task.lock_holder}`;
        }
    }

    handleDragStart(e) {
        const taskCard = e.target.closest('.task-card');
        if (!taskCard) return;

        const taskId = taskCard.getAttribute('data-task-id');
        if (!taskId) return;

        this.draggedTask = AppState.tasks.get(taskId);
        this.draggedElement = taskCard;

        if (!this.draggedTask) {
            e.preventDefault();
            return;
        }

        // Check if task is locked
        if (this.draggedTask.lock_holder) {
            e.preventDefault();
            showNotification(`Task is locked by ${this.draggedTask.lock_holder}`, 'error');
            return;
        }

        // Set drag effect and data
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', taskId);

        // Add visual feedback
        taskCard.classList.add('dragging');

        // Create drag placeholder
        this.createDragPlaceholder();

        console.log('Drag started for task:', this.draggedTask.name);
    }

    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';

        const column = e.target.closest('.column');
        if (!column) return;

        // Add visual feedback to column
        column.classList.add('drag-over');

        // Update placeholder position
        this.updatePlaceholderPosition(e, column);
    }

    handleDragEnter(e) {
        e.preventDefault();
        const column = e.target.closest('.column');
        if (column) {
            column.classList.add('drag-over');
        }
    }

    handleDragLeave(e) {
        const column = e.target.closest('.column');
        if (column && !column.contains(e.relatedTarget)) {
            column.classList.remove('drag-over');
        }
    }

    async handleDrop(e) {
        e.preventDefault();

        const column = e.target.closest('.column');
        if (!column || !this.draggedTask) {
            this.cleanup();
            return;
        }

        const newStatus = column.getAttribute('data-status');
        const oldStatus = this.draggedTask.status;

        // Remove visual feedback
        column.classList.remove('drag-over');

        // Check if status actually changed
        if (newStatus === oldStatus) {
            this.cleanup();
            return;
        }

        // Validate status transition
        if (!this.isValidStatusTransition(oldStatus, newStatus)) {
            showNotification(`Cannot move task from ${oldStatus} to ${newStatus}`, 'error');
            this.cleanup();
            return;
        }

        try {
            // Show optimistic update
            this.showOptimisticUpdate(newStatus);

            // Update task status via API
            await this.updateTaskStatus(this.draggedTask.id, newStatus);

            showNotification(`Task moved to ${newStatus}`, 'success');

        } catch (error) {
            console.error('Failed to update task status:', error);
            showNotification('Failed to update task status', 'error');

            // Revert optimistic update
            this.revertOptimisticUpdate();
        }

        this.cleanup();
    }

    handleDragEnd(e) {
        this.cleanup();
    }

    createDragPlaceholder() {
        if (this.dragPlaceholder) {
            this.dragPlaceholder.remove();
        }

        this.dragPlaceholder = document.createElement('div');
        this.dragPlaceholder.className = 'drag-placeholder';
        this.dragPlaceholder.innerHTML = `
            <div class="placeholder-content">
                <span class="placeholder-icon">📋</span>
                <span class="placeholder-text">Drop here</span>
            </div>
        `;
    }

    updatePlaceholderPosition(e, column) {
        if (!this.dragPlaceholder) return;

        const tasksContainer = column.querySelector('.tasks');
        if (!tasksContainer) return;

        const taskCards = Array.from(tasksContainer.querySelectorAll('.task-card:not(.dragging)'));
        const dragY = e.clientY;

        let insertBefore = null;

        for (const taskCard of taskCards) {
            const rect = taskCard.getBoundingClientRect();
            const cardCenterY = rect.top + rect.height / 2;

            if (dragY < cardCenterY) {
                insertBefore = taskCard;
                break;
            }
        }

        // Remove placeholder from current position
        if (this.dragPlaceholder.parentNode) {
            this.dragPlaceholder.remove();
        }

        // Insert placeholder at new position
        if (insertBefore) {
            tasksContainer.insertBefore(this.dragPlaceholder, insertBefore);
        } else {
            tasksContainer.appendChild(this.dragPlaceholder);
        }
    }

    isValidStatusTransition(fromStatus, toStatus) {
        // Define valid status transitions
        const validTransitions = {
            'TODO': ['IN_PROGRESS'],
            'BACKLOG': ['TODO', 'IN_PROGRESS'],
            'IN_PROGRESS': ['TODO', 'REVIEW', 'DONE'],
            'REVIEW': ['IN_PROGRESS', 'DONE'],
            'DONE': ['REVIEW'] // Allow moving back for corrections
        };

        const normalizedFrom = fromStatus.toUpperCase().replace(' ', '_');
        const normalizedTo = toStatus.toUpperCase().replace(' ', '_');

        return validTransitions[normalizedFrom]?.includes(normalizedTo) || false;
    }

    showOptimisticUpdate(newStatus) {
        if (!this.draggedTask || !this.draggedElement) return;

        // Update task in AppState
        this.draggedTask.status = newStatus;
        AppState.tasks.set(String(this.draggedTask.id), this.draggedTask);

        // Mark as pending update to prevent WebSocket conflicts
        AppState.pendingUpdates.set(String(this.draggedTask.id), {
            status: newStatus,
            timestamp: Date.now()
        });

        // Move DOM element to new column
        const newColumn = document.querySelector(`[data-status="${newStatus}"] .tasks`);
        if (newColumn) {
            // Remove placeholder and insert task
            if (this.dragPlaceholder && this.dragPlaceholder.parentNode) {
                this.dragPlaceholder.parentNode.replaceChild(this.draggedElement, this.dragPlaceholder);
            } else {
                newColumn.appendChild(this.draggedElement);
            }

            // Update task counts
            this.updateTaskCounts();
        }
    }

    revertOptimisticUpdate() {
        // This would require storing the original state and reverting
        // For now, we'll just reload the board data
        import('./board.js').then(({ loadBoardData }) => {
            loadBoardData();
        });
    }

    async updateTaskStatus(taskId, newStatus) {
        const response = await fetch(`/api/task/${taskId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                status: newStatus,
                agent_id: 'dashboard-ui'
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        // Clear pending update after successful API call
        AppState.pendingUpdates.delete(String(taskId));

        return result;
    }

    updateTaskCounts() {
        const statusCounts = {
            TODO: 0,
            BACKLOG: 0,
            IN_PROGRESS: 0,
            REVIEW: 0,
            DONE: 0
        };

        // Count tasks by status
        for (const task of AppState.tasks.values()) {
            const status = task.status.toUpperCase().replace(' ', '_');
            if (statusCounts.hasOwnProperty(status)) {
                statusCounts[status]++;
            }
        }

        // Update count displays
        Object.entries(statusCounts).forEach(([status, count]) => {
            const countElement = document.getElementById(`${status.toLowerCase().replace('_', '_')}-count`);
            if (countElement) {
                countElement.textContent = `${count} task${count !== 1 ? 's' : ''}`;
            }
        });
    }

    cleanup() {
        // Remove visual feedback
        document.querySelectorAll('.column').forEach(col => {
            col.classList.remove('drag-over');
        });

        if (this.draggedElement) {
            this.draggedElement.classList.remove('dragging');
        }

        // Remove placeholder
        if (this.dragPlaceholder && this.dragPlaceholder.parentNode) {
            this.dragPlaceholder.remove();
        }

        // Reset state
        this.draggedTask = null;
        this.draggedElement = null;
        this.dragPlaceholder = null;
    }

    // Public method to refresh draggable state when tasks are updated
    refreshDraggableState() {
        const taskCards = document.querySelectorAll('.task-card');
        taskCards.forEach(taskCard => {
            const taskId = taskCard.getAttribute('data-task-id');
            if (taskId) {
                const task = AppState.tasks.get(taskId);
                if (task) {
                    this.makeDraggable(taskCard, task);
                }
            }
        });
    }
}

// Create global instance
let dragDropManager = null;

export function initializeDragAndDrop() {
    if (!dragDropManager) {
        dragDropManager = new DragDropManager();
    }
    return dragDropManager;
}

export function getDragDropManager() {
    return dragDropManager;
}