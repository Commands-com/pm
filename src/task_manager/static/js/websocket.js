// WebSocket connection management with auto-reconnection and fallback
import { AppState } from './state.js';
// loadBoardState will be imported dynamically to avoid circular dependencies
import {
    handleTaskStatusUpdate,
    handleTaskLocked,
    handleTaskUnlocked,
    handleTaskCreated,
    handleTaskUpdated,
    handleTaskLogsAppended,
    handleProjectDeleted,
    handleEpicDeleted,
    handleKnowledgeUpserted,
    handleKnowledgeQuery,
    handleKnowledgeDeleted,
    handleKnowledgeLog
} from './event-handlers.js';

// #COMPLETION_DRIVE_WEBSOCKET: WebSocket connection with exponential backoff
// Pattern: Auto-reconnection with increasing delays prevents server overload
export function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/updates`;

    try {
        AppState.socket = new WebSocket(wsUrl);

        AppState.socket.onopen = function(event) {
            AppState.reconnectDelay = 1000; // Reset backoff
            AppState.connectionAttempts = 0;
            updateConnectionStatus('connected');

            // Stop polling fallback if active
            if (AppState.pollingInterval) {
                clearInterval(AppState.pollingInterval);
                AppState.pollingInterval = null;
            }
        };

        AppState.socket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                handleRealtimeUpdate(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        AppState.socket.onclose = function(event) {
            AppState.socket = null;
            updateConnectionStatus('disconnected');

            // #COMPLETION_DRIVE_FALLBACK: Implement polling fallback for poor connections
            // Assumption: Fallback ensures functionality when WebSocket is unreliable
            startPollingFallback();

            // Attempt reconnection with exponential backoff
            if (AppState.connectionAttempts < AppState.maxConnectionAttempts) {
                AppState.connectionAttempts++;
                setTimeout(() => {
                    if (!AppState.socket || AppState.socket.readyState === WebSocket.CLOSED) {
                        initializeWebSocket();
                    }
                }, AppState.reconnectDelay);

                AppState.reconnectDelay = Math.min(
                    AppState.reconnectDelay * 2,
                    AppState.maxReconnectDelay
                );
            }
        };

        AppState.socket.onerror = function(error) {
            console.error('WebSocket error:', error);
            updateConnectionStatus('disconnected');
        };

    } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        updateConnectionStatus('disconnected');
        startPollingFallback();
    }
}

// #COMPLETION_DRIVE_RESILIENCE: Polling fallback for network issues
// Pattern: Ensures dashboard remains functional when WebSocket fails
function startPollingFallback() {
    if (AppState.pollingInterval) return; // Already polling

    AppState.pollingInterval = setInterval(async () => {
        try {
            const { loadBoardState } = await import('./board.js');
            await loadBoardState();
        } catch (error) {
            console.error('Polling fallback failed:', error);
        }
    }, AppState.pollingDelay);
}

export function updateConnectionStatus(status) {
    const statusElement = document.getElementById('connectionStatus');
    if (!statusElement) return;

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

// #COMPLETION_DRIVE_REALTIME: Handle real-time updates from WebSocket with enriched payloads
// Pattern: Event-driven updates maintain UI consistency across clients with enhanced payload support
function handleRealtimeUpdate(data) {
    switch (data.type) {
        case 'task.status_changed':
            handleTaskStatusUpdate(data);
            break;
        case 'task.locked':
            handleTaskLocked(data);
            break;
        case 'task.unlocked':
            handleTaskUnlocked(data);
            break;
        case 'task.created':
            handleTaskCreated(data);
            break;
        case 'task.updated':
            handleTaskUpdated(data);
            break;
        case 'task.logs.appended':
            handleTaskLogsAppended(data);
            break;
        case 'project_deleted':
            handleProjectDeleted(data);
            break;
        case 'epic_deleted':
            handleEpicDeleted(data);
            break;
        case 'knowledge_upserted':
            handleKnowledgeUpserted(data);
            break;
        case 'knowledge_query':
            handleKnowledgeQuery(data);
            break;
        case 'knowledge_deleted':
            handleKnowledgeDeleted(data);
            break;
        case 'knowledge_log':
            handleKnowledgeLog(data);
            break;
        default:
            // Unknown event type - silently ignore
            break;
    }
}