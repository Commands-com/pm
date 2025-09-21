// Global application state
// #COMPLETION_DRIVE_ARCHITECTURE: Centralized state management to avoid circular dependencies
// Extracted from app.js to break circular import between app.js and websocket.js

export const AppState = {
    socket: null,
    reconnectDelay: 1000,
    maxReconnectDelay: 30000,
    connectionAttempts: 0,
    maxConnectionAttempts: 10,
    tasks: new Map(),
    projects: new Map(),
    epics: new Map(),
    selectedProjectId: null,
    selectedEpicId: null,
    pendingUpdates: new Map(),
    isOnline: navigator.onLine,
    pollingInterval: null,
    pollingDelay: 5000,
    todoViewMode: 'TODO' // 'TODO' or 'BACKLOG'
};