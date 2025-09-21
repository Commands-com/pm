// Real-time event handlers for WebSocket updates
import { AppState } from './app.js';
import { renderTask, updateTaskCounts, renderAllTasks } from './board.js';
import { populateProjectSelector, populateEpicSelector } from './filters.js';
import { showNotification } from './utils.js';
import { saveSelectionState, getFilteredTasks, updateDeleteButtonVisibility } from './utils.js';

export function handleTaskStatusUpdate(data) {
    const task = AppState.tasks.get(String(data.task_id));
    if (task) {
        // #COMPLETION_DRIVE_CONFLICT: Skip update if user has pending operation
        // Assumption: User's optimistic update takes precedence over remote updates
        if (AppState.pendingUpdates.has(String(data.task_id))) {
            console.log('Skipping remote update due to pending local update');
            return;
        }

        task.status = data.status;
        task.agent_id = data.agent_id;
        AppState.tasks.set(String(data.task_id), task);
        renderTask(task);
        updateTaskCounts();
    } else {
        // If task not found locally (stale state), resync board
        console.log('Task not found in state for status update; reloading board state');
        import('./board.js').then(({ loadBoardState }) => loadBoardState());
    }
}

export function handleTaskLocked(data) {
    const task = AppState.tasks.get(String(data.task_id));
    if (task) {
        task.lock_holder = data.agent_id;
        AppState.tasks.set(String(data.task_id), task);
        renderTask(task);
    } else {
        console.log('Task not found in state for lock; reloading board state');
        import('./board.js').then(({ loadBoardState }) => loadBoardState());
    }
}

export function handleTaskUnlocked(data) {
    const task = AppState.tasks.get(String(data.task_id));
    if (task) {
        task.lock_holder = null;
        AppState.tasks.set(String(data.task_id), task);
        renderTask(task);
    } else {
        console.log('Task not found in state for unlock; reloading board state');
        import('./board.js').then(({ loadBoardState }) => loadBoardState());
    }
}

// #COMPLETION_DRIVE_IMPL: Enhanced event handlers for enriched WebSocket payloads
// New event types support auto-switch functionality and comprehensive real-time updates

export function handleTaskCreated(data) {
    console.log('Task created event received:', data);

    // #COMPLETION_DRIVE_INTEGRATION: Extract enriched task data from event payload
    const enrichedData = data.data || data;
    const taskData = enrichedData.task;
    const projectData = enrichedData.project;
    const epicData = enrichedData.epic;
    const flags = enrichedData.flags || {};
    const initiator = enrichedData.initiator;

    if (taskData) {
        // Create task object compatible with existing UI structure
        const task = {
            id: taskData.id,
            name: taskData.name,
            description: taskData.description,
            status: taskData.status || 'TODO',
            epic_id: taskData.epic_id,
            project_id: projectData ? projectData.id : null,
            ra_score: taskData.ra_score,
            ra_mode: taskData.ra_mode,
            complexity_score: taskData.ra_score || taskData.complexity_score, // Alias for UI compatibility
            mode_used: taskData.ra_mode || taskData.mode_used, // Alias for UI compatibility
            estimated_hours: taskData.ra_metadata?.estimated_hours || 'N/A', // Extract from ra_metadata
            created_at: taskData.created_at,
            updated_at: taskData.updated_at,
            project_name: projectData ? projectData.name : null,
            epic_name: epicData ? epicData.name : null
        };

        // Add task to state
        AppState.tasks.set(String(task.id), task);

        // Update projects and epics data if provided
        if (projectData) {
            AppState.projects.set(String(projectData.id), projectData);
        }
        if (epicData) {
            AppState.epics.set(String(epicData.id), epicData);
        }

        // Re-populate selectors if new project/epic was created
        if (flags.project_created) {
            populateProjectSelector();
        }
        if (flags.epic_created) {
            populateEpicSelector();
        }

        // Only render and update counts if task matches current filter
        const filteredTasks = getFilteredTasks();
        if (filteredTasks.some(t => t.id === task.id)) {
            renderTask(task);
            updateTaskCounts();
        } else {
            // Task exists but doesn't match filter - still update counts
            updateTaskCounts();
        }

        // #COMPLETION_DRIVE_INTEGRATION: Auto-switch logic for dashboard clients
        // Check if this event should trigger auto-switch behavior
        if (enrichedData.auto_switch_recommended && initiator) {
            // #SUGGEST_EDGE_CASE: Implement session-based auto-switch logic
            // For now, show notification about new task creation
            let switchMessage = `New task created: ${task.name}`;

            if (flags.project_created) {
                switchMessage += ` (new project: ${projectData?.name})`;
            }
            if (flags.epic_created) {
                switchMessage += ` (new epic: ${epicData?.name})`;
            }

            showNotification(switchMessage, 'success', 5000);
        }
    }
}

export function handleTaskUpdated(data) {
    console.log('Task updated event received:', data);

    // #COMPLETION_DRIVE_INTEGRATION: Extract enriched update data from event payload
    const enrichedData = data.data || data;
    const taskData = enrichedData.task;
    const changedFields = enrichedData.changed_fields || [];
    const fieldChanges = enrichedData.field_changes || {};

    if (taskData && taskData.id) {
        const taskId = String(taskData.id);

        // Skip update if user has pending operation to avoid conflicts
        if (AppState.pendingUpdates.has(taskId)) {
            console.log('Skipping remote task update due to pending local update');
            return;
        }

        // Get existing task or create new one
        let task = AppState.tasks.get(taskId) || {};

        // Update task with enriched data
        Object.assign(task, {
            id: taskData.id,
            name: taskData.name,
            description: taskData.description,
            status: taskData.status,
            epic_id: taskData.epic_id,
            ra_score: taskData.ra_score,
            ra_mode: taskData.ra_mode,
            complexity_score: taskData.ra_score || taskData.complexity_score, // UI compatibility
            mode_used: taskData.ra_mode || taskData.mode_used, // UI compatibility
            estimated_hours: taskData.ra_metadata?.estimated_hours || 'N/A', // Extract from ra_metadata
            created_at: taskData.created_at,
            updated_at: taskData.updated_at,
            project_name: enrichedData.project ? enrichedData.project.name : task.project_name,
            epic_name: enrichedData.epic ? enrichedData.epic.name : task.epic_name
        });

        // Update state
        AppState.tasks.set(taskId, task);

        // Check if task should be visible in current filter
        const wasVisible = document.getElementById(`task-${task.id}`) !== null;
        const shouldBeVisible = getFilteredTasks().some(t => t.id === task.id);

        if (shouldBeVisible) {
            renderTask(task);
        } else if (wasVisible) {
            // Task was visible but no longer matches filter - remove it
            const taskElement = document.getElementById(`task-${task.id}`);
            if (taskElement) {
                taskElement.remove();
            }
        }

        updateTaskCounts();

        // Show notification about significant changes
        if (changedFields.includes('status')) {
            const statusChange = fieldChanges.status;
            if (statusChange) {
                showNotification(`Task "${task.name}" moved to ${statusChange.new}`, 'info');
            }
        }

        // Update task detail modal if it's currently showing this task
        if (window.taskDetailModal && window.taskDetailModal.currentTask &&
            window.taskDetailModal.currentTask.id == taskData.id) {
            // #SUGGEST_EDGE_CASE: Consider refreshing modal data for real-time updates
            console.log('Task detail modal is open for updated task - consider refreshing');
        }
    }
}

export function handleTaskLogsAppended(data) {
    console.log('Task logs appended event received:', data);

    // #COMPLETION_DRIVE_IMPL: Handle real-time log updates for task detail modal
    const logsData = data.data || data;
    const taskId = logsData.task_id;
    const logEntries = logsData.log_entries || [];

    // If task detail modal is open for this task, update the logs
    if (window.taskDetailModal && window.taskDetailModal.currentTask &&
        window.taskDetailModal.currentTask.id == taskId &&
        window.taskDetailModal.activeTab === 'execution-log') {

        // #SUGGEST_IMPLEMENTATION: Real-time log appending in modal
        // For now, show notification about new log entries
        showNotification(`${logEntries.length} new log entr${logEntries.length === 1 ? 'y' : 'ies'} added`, 'info');

        // Optional: Auto-refresh logs in modal
        setTimeout(() => {
            if (window.taskDetailModal.currentTask && window.taskDetailModal.currentTask.id == taskId) {
                window.taskDetailModal.refreshExecutionLogs();
            }
        }, 500);
    }
}

export function handleProjectDeleted(data) {
    console.log('Project deleted event received:', data);

    const projectId = String(data.project_id);

    // Remove project from AppState
    if (AppState.projects.has(projectId)) {
        AppState.projects.delete(projectId);
    }

    // Remove all epics belonging to this project
    AppState.epics.forEach((epic, epicId) => {
        if (epic.project_id == data.project_id) {
            AppState.epics.delete(epicId);
        }
    });

    // Remove all tasks belonging to this project
    AppState.tasks.forEach((task, taskId) => {
        if (task.project_id == data.project_id) {
            AppState.tasks.delete(taskId);
        }
    });

    // Reset selections if deleted project was selected
    if (AppState.selectedProjectId == data.project_id) {
        AppState.selectedProjectId = null;
        AppState.selectedEpicId = null;
        saveSelectionState();
    }

    // Update UI
    populateProjectSelector();
    populateEpicSelector();
    updateDeleteButtonVisibility();
    renderAllTasks();
    updateTaskCounts();

    // Show notification
    showNotification(`Project "${data.project_name}" deleted successfully`, 'success');
}

export function handleEpicDeleted(data) {
    console.log('Epic deleted event received:', data);

    const epicId = String(data.epic_id);

    // Remove epic from AppState
    if (AppState.epics.has(epicId)) {
        AppState.epics.delete(epicId);
    }

    // Remove all tasks belonging to this epic
    AppState.tasks.forEach((task, taskId) => {
        if (task.epic_id == data.epic_id) {
            AppState.tasks.delete(taskId);
        }
    });

    // Reset epic selection if deleted epic was selected
    if (AppState.selectedEpicId == data.epic_id) {
        AppState.selectedEpicId = null;
        saveSelectionState();
    }

    // Update UI
    populateEpicSelector();
    updateDeleteButtonVisibility();
    renderAllTasks();
    updateTaskCounts();

    // Show notification
    showNotification(`Epic "${data.epic_name}" deleted successfully`, 'success');
}

export function handleKnowledgeUpserted(data) {
    console.log('Knowledge upserted event received:', data);

    // If the knowledge modal is open, refresh its data
    if (window.knowledgeModal && window.knowledgeModal.isOpen) {
        window.knowledgeModal.loadKnowledgeData();
    }

    // Show notification for knowledge updates
    const operation = data.operation || 'updated';
    const knowledgeItem = data.knowledge_item || {};
    const title = knowledgeItem.title || 'Knowledge item';

    showNotification(`${title} ${operation} successfully`, 'success');
}

export function handleKnowledgeQuery(data) {
    console.log('Knowledge query event received:', data);

    // This appears to be a query result event, could be used for search results
    // or knowledge retrieval operations. Currently just logging for visibility.
    const resultCount = data.result_count || 0;
    console.log(`Knowledge query returned ${resultCount} results`);
}

export function handleKnowledgeDeleted(data) {
    console.log('Knowledge deleted event received:', data);

    // If the knowledge modal is open, refresh its data to remove deleted item
    if (window.knowledgeModal && window.knowledgeModal.isOpen) {
        window.knowledgeModal.loadKnowledgeData();
    }

    // Show notification for knowledge deletion
    showNotification(`Knowledge item deleted successfully`, 'success');
}

export function handleKnowledgeLog(data) {
    console.log('Knowledge log event received:', data);

    // If the knowledge modal is open and showing the item that was logged,
    // refresh the log display in real-time
    const knowledgeId = data.knowledge_id;
    const action = data.action_type || 'activity';

    showNotification(`Knowledge item ${action} logged`, 'info');
}