// Main application state and initialization
// #COMPLETION_DRIVE_ARCHITECTURE: Global state management for WebSocket and UI
// Assumption: Single global state object simplifies state management in single-page context

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

// Import modules
import { initializeWebSocket, updateConnectionStatus } from './websocket.js';
import { loadBoardData, applyFilters } from './board.js';
import { setupEventListeners } from './utils.js';
import { initializeModals } from './modal.js';
import { initializeFilters, populateProjectSelector, populateEpicSelector } from './filters.js';

// Initialize application
export function initializeApp() {
    console.log('Initializing PM Dashboard Application');

    // Initialize filters and modals first
    initializeFilters();
    initializeModals();

    // Setup event listeners
    setupEventListeners();

    // Initialize WebSocket connection
    initializeWebSocket();

    // Load initial data
    loadBoardData();

    // Populate selectors after data is loaded
    setTimeout(() => {
        populateProjectSelector();
        populateEpicSelector();
    }, 100);

    // Setup network status monitoring
    window.addEventListener('online', () => {
        console.log('Network connection restored');
        AppState.isOnline = true;
        if (!AppState.socket || AppState.socket.readyState !== WebSocket.OPEN) {
            initializeWebSocket();
        }
    });

    window.addEventListener('offline', () => {
        console.log('Network connection lost');
        AppState.isOnline = false;
        updateConnectionStatus('disconnected');
    });

    // Apply initial filters
    applyFilters();
}

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}