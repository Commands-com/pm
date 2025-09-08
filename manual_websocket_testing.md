# Manual WebSocket Testing Guide

This guide provides manual testing procedures for the enhanced WebSocket events implementation.

## Prerequisites

1. Start the FastAPI server:
   ```bash
   cd /Users/dtannen/Code/pm
   python -m uvicorn src.task_manager.api:app --reload --host 0.0.0.0 --port 8000
   ```

2. Open browser to: http://localhost:8000

3. Open Browser Developer Tools (F12) and go to Network or Console tab

## Test Cases

### 1. WebSocket Connection

**Expected Behavior:**
- Connection status in header shows "Connected" (green)
- Console shows: "WebSocket connected successfully"

**Manual Steps:**
1. Refresh the page
2. Check connection status indicator
3. Check browser console for connection messages

### 2. Task Creation Events (task.created)

**Test Scenario:** Create a task via MCP and verify enriched event

**Expected Enriched Payload Structure:**
```javascript
{
  "type": "task.created",
  "timestamp": "2025-01-08T10:30:00Z",
  "data": {
    "task": {
      "id": 123,
      "name": "Task Name", 
      "status": "pending",
      "ra_score": 8,
      "ra_mode": "ra-light",
      "description": "Task description"
    },
    "epic": {
      "id": 45,
      "name": "Epic Name",
      "project_id": 12
    },
    "project": {
      "id": 12,
      "name": "Project Name"
    },
    "flags": {
      "project_created": true,
      "epic_created": false
    },
    "initiator": "session_abc123"
  }
}
```

**Manual Steps:**
1. Use MCP client to create task with `client_session_id` parameter
2. Check browser console for "Task created event received" message
3. Verify new task appears in TODO column
4. Check notification shows creation details with project/epic context

### 3. Task Update Events (task.updated)

**Test Scenario:** Update a task via MCP and verify enriched event

**Expected Features:**
- Complete task context (project/epic names)
- Changed fields tracking
- Real-time UI updates

**Manual Steps:**
1. Use MCP client to update an existing task (change status, description, etc.)
2. Check browser console for "Task updated event received" message
3. Verify task moves to correct column if status changed
4. Check notification shows update details

### 4. Task Logs Appended Events (task.logs.appended)

**Test Scenario:** Add log entries to a task and verify real-time log updates

**Expected Behavior:**
- Real-time log updates in task detail modal
- Proper sequence tracking
- Auto-refresh functionality

**Manual Steps:**
1. Open task detail modal for a task
2. Switch to "Execution Log" tab
3. Use MCP client to update task with log_entry parameter
4. Check console for "Task logs appended event received" message
5. Verify log notification appears
6. Check logs auto-refresh after 500ms delay

### 5. Session Tracking and Auto-Switch

**Test Scenario:** Verify session-based event targeting

**Expected Behavior:**
- Events include initiator/session ID when provided
- Auto-switch recommendations work correctly
- Session-specific notifications

**Manual Steps:**
1. Create task with `client_session_id: "test_session_123"`
2. Verify event payload includes `"initiator": "test_session_123"`
3. Check for auto-switch notification messages
4. Verify project/epic creation flags work correctly

## Browser Developer Tools Inspection

### Network Tab
1. Filter by "WS" (WebSocket)
2. Click on WebSocket connection
3. Go to "Messages" tab
4. Watch for enriched event payloads

### Console Tab
Look for these message patterns:
- `WebSocket connected successfully`
- `Processing real-time update: {event_data}`
- `Task created event received: {enriched_data}`
- `Task updated event received: {enriched_data}`
- `Task logs appended event received: {logs_data}`

### Application Tab
1. Go to Storage → Local Storage
2. Check AppState.tasks Map contents
3. Verify task data includes project/epic context

## Performance Testing

### Event Payload Size
1. Create tasks with large descriptions (~5KB)
2. Check WebSocket message size in Network tab
3. Verify payloads stay under 10KB limit

### Connection Resilience
1. Disable network connection
2. Verify "Disconnected" status appears
3. Re-enable network
4. Check automatic reconnection works

### Rapid Updates
1. Create multiple tasks quickly via MCP
2. Verify all events are received and processed
3. Check for event flooding protection

## Expected Results

✅ **Task Created Events:**
- New tasks appear immediately in UI
- Full project/epic context included
- Auto-switch notifications work
- Session targeting functions correctly

✅ **Task Updated Events:**
- Real-time status changes reflected
- Field change tracking works
- Task detail modal updates appropriately
- Change notifications appear

✅ **Task Logs Appended:**
- Real-time log updates in modal
- Proper sequence tracking
- Auto-refresh functionality
- Notification system works

✅ **Performance:**
- Payload sizes under 10KB
- No event flooding
- Connection resilience
- Fast event processing

## Troubleshooting

**WebSocket not connecting:**
- Check server is running on port 8000
- Check firewall settings
- Try hard refresh (Ctrl+F5)

**Events not received:**
- Check MCP tools include correct session ID
- Verify server logs for broadcasting errors
- Check browser console for JavaScript errors

**UI not updating:**
- Check AppState.tasks Map in dev tools
- Verify renderTask() function calls
- Check for JavaScript errors in console

**Modal not refreshing:**
- Verify taskDetailModal instance exists
- Check activeTab matches 'execution-log'
- Confirm task ID matching logic works