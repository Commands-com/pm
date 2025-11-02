---
name: task-locking
description: Atomic task locking patterns to prevent race conditions in multi-agent environments. Use when working with task locks, concurrent operations, acquire_task_lock, update_task_status, or debugging lock conflicts.
allowed-tools: Read, Grep, Glob
---

# Task Lock Coordination

This skill guides proper use of atomic task locking to prevent race conditions in multi-agent workflows.

## Why Atomic Locking Matters

In multi-agent systems, multiple agents can try to work on the same task simultaneously. Without proper locking, you get race conditions:

```
Agent A reads task (unlocked) ─┐
Agent B reads task (unlocked) ─┤ Race condition!
Agent A acquires lock        ─┤ Both think they got it
Agent B acquires lock        ─┘ Data corruption!
```

**Atomic locking** prevents this with a single database operation that's guaranteed to succeed for only ONE agent.

## The Atomic Pattern

```python
# GOOD - Atomic single UPDATE (only ONE agent succeeds)
cursor.execute("""
    UPDATE tasks SET lock_holder = ?, lock_expires_at = ?
    WHERE id = ? AND (lock_holder IS NULL OR lock_expires_at < ?)
""", (agent_id, expires_at, task_id, current_time))

success = cursor.rowcount > 0  # Only 1 agent gets rowcount=1
```

```python
# BAD - Race condition (don't do this!)
if not is_locked(task_id):      # Agent A checks: not locked
    set_lock(task_id, agent_id)  # Agent B can check before A sets!
```

## Tested Under Load

The PM Dashboard locking system has been stress-tested:
- **20+ concurrent agents** trying to lock the same task
- **Exactly 1 agent succeeds** every time
- **19 agents fail gracefully** with clear error messages

This is proven to work under extreme concurrency.

## Two Locking Approaches

### 1. Automatic Locking (Preferred)

Use `update_task_status()` for simple workflows:

```python
# Automatically acquires lock when moving to IN_PROGRESS
update_task_status(
    task_id="42",
    status="IN_PROGRESS",
    agent_id="claude"
)
# Lock acquired automatically!

# Work on task...

# Automatically releases lock when moving to REVIEW or DONE
update_task_status(
    task_id="42",
    status="REVIEW",
    agent_id="claude"
)
# Lock released automatically!
```

**Benefits:**
- ✅ Simple - one call does everything
- ✅ No forgotten unlocks
- ✅ Correct workflow enforcement
- ✅ Perfect for single-agent work

**When to use:** Most of the time!

### 2. Manual Locking (Multi-Agent Coordination)

Use explicit lock/unlock for complex coordination:

```python
# Agent explicitly acquires lock
success = acquire_task_lock(
    task_id="42",
    agent_id="implementation-agent",
    timeout=300  # 5 minutes
)

if success:
    # Do work...

    # Explicitly release when done
    release_task_lock(
        task_id="42",
        agent_id="implementation-agent"
    )
```

**Benefits:**
- ✅ Fine-grained control
- ✅ Custom timeout durations
- ✅ Can hold lock across multiple operations
- ✅ Perfect for multi-agent orchestration

**When to use:** RA-Full mode, multi-agent workflows, complex coordination.

## Lock Lifecycle

```
1. Task created (unlocked)
         ↓
2. update_task_status(IN_PROGRESS) → Auto-acquires lock
         ↓
3. Agent works on task (lock held)
         ↓
4. update_task_status(REVIEW) → Auto-releases lock
         ↓
5. Reviewer validates (can acquire for review)
         ↓
6. update_task_status(DONE) → Fully unlocked
```

## Lock Timeout & Cleanup

**Default timeout:** 300 seconds (5 minutes)

**Auto-cleanup:**
- Expired locks are automatically cleaned up
- System checks for expired locks periodically
- Expired locks are released before new lock attempts

**Custom timeout:**
```python
acquire_task_lock(
    task_id="42",
    agent_id="long-running-agent",
    timeout=1800  # 30 minutes for complex work
)
```

## Handling Lock Failures

### Scenario 1: Task Already Locked

```python
success = acquire_task_lock(task_id="42", agent_id="agent-A")

if not success:
    # Check who has the lock
    lock_status = get_task_lock_status(task_id="42")

    if lock_status["is_locked"]:
        print(f"Task locked by: {lock_status['lock_holder']}")
        print(f"Expires at: {lock_status['lock_expires_at']}")

        # Options:
        # 1. Wait for lock to expire
        # 2. Work on different task
        # 3. Coordinate with lock holder
```

### Scenario 2: Lock Expired While Working

```python
# Lock acquired with 5-minute timeout
acquire_task_lock(task_id="42", agent_id="slow-agent", timeout=300)

# ... work takes 10 minutes (timeout exceeded!) ...

# Try to update status
update_task_status(task_id="42", status="DONE", agent_id="slow-agent")
# ❌ Fails: "Task must be locked by agent to update status"

# Solution: Re-acquire lock before finishing
success = acquire_task_lock(task_id="42", agent_id="slow-agent")
if success:
    update_task_status(task_id="42", status="DONE", agent_id="slow-agent")
```

## Multi-Agent Orchestration Example

**RA-Full mode with multiple agents:**

```python
# Main orchestrator creates task
create_task(name="Complex feature", ra_mode="ra-full", ra_score="9")

# Deploy survey agent
acquire_task_lock(task_id="99", agent_id="survey-agent", timeout=600)
# Survey agent gathers context...
release_task_lock(task_id="99", agent_id="survey-agent")

# Deploy planning agent
acquire_task_lock(task_id="99", agent_id="planning-agent", timeout=600)
# Planning agent creates plan...
release_task_lock(task_id="99", agent_id="planning-agent")

# Deploy implementation agent
acquire_task_lock(task_id="99", agent_id="impl-agent", timeout=1800)
# Implementation agent codes...
release_task_lock(task_id="99", agent_id="impl-agent")

# Deploy verification agent
acquire_task_lock(task_id="99", agent_id="verify-agent", timeout=600)
# Verification agent reviews...
update_task_status(task_id="99", status="DONE", agent_id="verify-agent")
# Auto-releases on DONE
```

## Lock Ownership Validation

**Only the lock holder can:**
- Update task status
- Release the lock
- Modify task data

```python
# Agent A has the lock
acquire_task_lock(task_id="42", agent_id="agent-A")

# Agent B tries to update
update_task_status(task_id="42", status="DONE", agent_id="agent-B")
# ❌ Fails: "Task is locked by agent-A"

# Only Agent A can update
update_task_status(task_id="42", status="DONE", agent_id="agent-A")
# ✅ Success
```

## Best Practices

### ✅ DO

- **Use auto-locking** (`update_task_status`) for simple workflows
- **Set appropriate timeouts** based on work complexity
- **Release locks explicitly** if using manual locking
- **Check lock status** before attempting operations
- **Log lock failures** for debugging

### ❌ DON'T

- **Don't forget to release** manual locks
- **Don't use SELECT then UPDATE** (race condition risk)
- **Don't hold locks longer than necessary**
- **Don't assume lock still held** after long work
- **Don't try to steal locks** from other agents

## Common Patterns

### Pattern 1: Quick Update
```python
# Auto-lock pattern (preferred)
update_task_status(task_id, "IN_PROGRESS", agent_id)
# ... quick work ...
update_task_status(task_id, "DONE", agent_id)
```

### Pattern 2: Long Work Session
```python
# Manual lock with custom timeout
acquire_task_lock(task_id, agent_id, timeout=1800)  # 30 min
try:
    # ... long complex work ...
finally:
    release_task_lock(task_id, agent_id)  # Always release!
```

### Pattern 3: Check Before Acquire
```python
# Check if available first
lock_status = get_task_lock_status(task_id)
if not lock_status["is_locked"]:
    success = acquire_task_lock(task_id, agent_id)
    if success:
        # Do work
        pass
```

## Debugging Lock Issues

### Problem: "Task must be locked"
**Cause:** Lock expired or never acquired
**Solution:** Check timeout, re-acquire if needed

### Problem: "Task is locked by another agent"
**Cause:** Another agent has the lock
**Solution:** Wait for expiration or coordinate

### Problem: Lock never released
**Cause:** Agent crashed or forgot to release
**Solution:** Wait for auto-cleanup (timeout expiration)

## Database Implementation

The atomic locking is implemented with a single UPDATE:

```sql
UPDATE tasks
SET lock_holder = ?, lock_expires_at = ?, updated_at = ?
WHERE id = ?
  AND (lock_holder IS NULL OR lock_expires_at < ?)
```

**Why this works:**
- WHERE clause filters to unlocked or expired locks
- Only ONE concurrent UPDATE can satisfy the WHERE clause
- `rowcount > 0` tells you if YOU got the lock
- Atomic at database level (tested under 20-agent load)

## Summary

**Simple workflows:** Use `update_task_status()` auto-locking

**Complex workflows:** Use `acquire_task_lock()` + `release_task_lock()` manually

**Always:**
- Set appropriate timeouts
- Release locks when done
- Check lock status before operations
- Trust the atomic pattern (it's tested!)

The PM Dashboard locking system is production-ready and proven under concurrent load.
