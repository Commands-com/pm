// Filter management for projects and epics
import { AppState } from './app.js';
import { saveSelectionState, loadSelectionState, updateDeleteButtonVisibility, showNotification } from './utils.js';

// Populate project selector dropdown
export function populateProjectSelector() {
    const projectSelect = document.getElementById('projectSelect');
    if (!projectSelect) return;

    // Clear existing options
    projectSelect.innerHTML = '<option value="">All Projects</option>';

    // Add projects from AppState
    const projects = Array.from(AppState.projects.values());
    projects.sort((a, b) => a.name.localeCompare(b.name));

    projects.forEach(project => {
        const option = document.createElement('option');
        option.value = project.id;
        option.textContent = project.name;
        if (AppState.selectedProjectId == project.id) {
            option.selected = true;
        }
        projectSelect.appendChild(option);
    });
}

// Populate epic selector dropdown based on selected project
export function populateEpicSelector() {
    const epicSelect = document.getElementById('epicSelect');
    if (!epicSelect) return;

    // Clear existing options
    epicSelect.innerHTML = '<option value="">All Epics</option>';

    // If no project selected, show all epics
    let epics = Array.from(AppState.epics.values());

    // Filter epics by selected project
    if (AppState.selectedProjectId) {
        epics = epics.filter(epic => epic.project_id == AppState.selectedProjectId);
    }

    // Sort epics by name
    epics.sort((a, b) => a.name.localeCompare(b.name));

    epics.forEach(epic => {
        const option = document.createElement('option');
        option.value = epic.id;
        option.textContent = epic.name;
        if (AppState.selectedEpicId == epic.id) {
            option.selected = true;
        }
        epicSelect.appendChild(option);
    });

    // Update epic selector state
    if (AppState.selectedProjectId && !epics.some(e => e.id == AppState.selectedEpicId)) {
        // Selected epic is not valid for current project filter
        AppState.selectedEpicId = null;
        saveSelectionState();
    }
}

// Initialize filters on page load
export function initializeFilters() {
    // Load saved selection state
    loadSelectionState();

    // Setup event listeners
    setupFilterEventListeners();

    // Update initial state
    updateDeleteButtonVisibility();
    // Ensure TODO/BACKLOG column title reflects current view mode
    updateTodoColumnTitle();
}

// Setup additional filter event listeners (main ones are in utils.js)
function setupFilterEventListeners() {

    // Todo view mode toggle (if exists)
    const todoToggle = document.querySelector('[data-mode="TODO"]');
    const backlogToggle = document.querySelector('[data-mode="BACKLOG"]');
    const singleToggle = document.getElementById('todo-backlog-toggle');

    if (todoToggle) {
        todoToggle.addEventListener('click', () => {
            AppState.todoViewMode = 'TODO';
            saveSelectionState();
            updateViewModeButtons();
            // Apply filters dynamically to avoid circular import
            import('./board.js').then(({ applyFilters }) => applyFilters());
        });
    }

    if (backlogToggle) {
        backlogToggle.addEventListener('click', () => {
            AppState.todoViewMode = 'BACKLOG';
            saveSelectionState();
            updateViewModeButtons();
            // Apply filters dynamically to avoid circular import
            import('./board.js').then(({ applyFilters }) => applyFilters());
        });
    }

    // Support original single toggle button behavior
    if (singleToggle) {
        singleToggle.addEventListener('click', () => {
            AppState.todoViewMode = (AppState.todoViewMode === 'TODO') ? 'BACKLOG' : 'TODO';
            saveSelectionState();
            updateViewModeButtons();
            updateTodoColumnTitle();
            // Apply filters dynamically to avoid circular import
            import('./board.js').then(({ applyFilters }) => applyFilters());
        });
    }
}

// Update view mode button states
function updateViewModeButtons() {
    const todoToggle = document.querySelector('[data-mode="TODO"]');
    const backlogToggle = document.querySelector('[data-mode="BACKLOG"]');

    if (todoToggle && backlogToggle) {
        todoToggle.classList.toggle('active', AppState.todoViewMode === 'TODO');
        backlogToggle.classList.toggle('active', AppState.todoViewMode === 'BACKLOG');
    }
}

// Update the TODO/BACKLOG column header title to reflect current view mode
function updateTodoColumnTitle() {
    const titleEl = document.getElementById('todo-column-title');
    if (titleEl) {
        titleEl.textContent = AppState.todoViewMode || 'TODO';
    }
}

// Delete project with confirmation
async function deleteProject(projectId) {
    const project = AppState.projects.get(String(projectId));
    if (!project) return;

    const confirmed = confirm(`Are you sure you want to delete project "${project.name}"? This will also delete all its epics and tasks.`);
    if (!confirmed) return;

    try {
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // The WebSocket event handler will update the UI
        console.log('Project deletion request sent');

    } catch (error) {
        console.error('Failed to delete project:', error);
        showNotification('Failed to delete project', 'error');
    }
}

// Delete epic with confirmation
async function deleteEpic(epicId) {
    const epic = AppState.epics.get(String(epicId));
    if (!epic) return;

    const confirmed = confirm(`Are you sure you want to delete epic "${epic.name}"? This will also delete all its tasks.`);
    if (!confirmed) return;

    try {
        const response = await fetch(`/api/epics/${epicId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // The WebSocket event handler will update the UI
        console.log('Epic deletion request sent');

    } catch (error) {
        console.error('Failed to delete epic:', error);
        showNotification('Failed to delete epic', 'error');
    }
}

// Reset all filters
export function resetFilters() {
    AppState.selectedProjectId = null;
    AppState.selectedEpicId = null;
    AppState.todoViewMode = 'TODO';
    saveSelectionState();

    populateProjectSelector();
    populateEpicSelector();
    updateDeleteButtonVisibility();
    updateViewModeButtons();
    // Apply filters dynamically to avoid circular import
    import('./board.js').then(({ applyFilters }) => applyFilters());
}
