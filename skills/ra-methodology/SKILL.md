---
name: ra-methodology
description: Response Awareness methodology for AI-assisted development with complexity scoring (1-10), assumption tagging, and knowledge capture. Use when creating tasks, managing projects, tracking assumptions, adding RA tags, or discussing complexity assessment.
allowed-tools: Read, Grep, Glob
---

# Response Awareness (RA) Methodology

This skill guides you through the Response Awareness methodology for creating and managing tasks with proper assumption tracking across all programming and development work.

## Critical Requirements

⚠️ **MANDATORY: CREATE A TASK BEFORE DOING ANY WORK**
- NO code changes without a task
- NO file edits without a task
- NO implementations without a task
- Create task BEFORE reading code, writing code, or making changes

## Quick Workflow

```
1. CREATE TASK FIRST → 2. Assess complexity (1-10) → 3. Set RA mode →
4. Implement with RA tags → 5. Log progress → 6. Status: REVIEW → 7. Validate → 8. DONE
```

## Complexity Assessment (1-10 Scale)

Score based on: code size, domains affected, integration points, uncertainty level

- **1-3: Simple Mode** - Direct implementation, basic testing
- **4-6: Standard Mode** - Document assumptions, comprehensive testing
- **7-8: RA-Light Mode** - Extensive RA tagging, verification needed
- **9-10: RA-Full Mode** - Multi-agent orchestration required

For detailed scoring criteria, see [COMPLEXITY_SCORING.md](reference/COMPLEXITY_SCORING.md).

## RA Modes Explained

### Simple Mode (1-3)
- Direct implementation with **MANDATORY RA awareness**
- **RA tags REQUIRED for ALL assumptions**
- Basic error handling and testing
- Knowledge capture: ONLY for problems/gotchas
- Completion: MUST go to REVIEW for assumption validation

### Standard Mode (4-6)
- Structured implementation with **MANDATORY RA awareness**
- **RA tags REQUIRED for ALL decisions and uncertainties**
- Document assumptions in code comments AND RA tags
- Comprehensive error handling and testing
- Knowledge capture: ONLY for problems/gotchas encountered
- Completion: MUST go to REVIEW for assumption validation

### RA-Light Mode (7-8)
- Extensive RA tagging required throughout
- Every assumption must be tagged with specific content
- Don't implement SUGGEST_* items - just tag them
- Comprehensive knowledge documentation
- Flag for verification: `update_task(ra_metadata={"verification_needed": True})`
- Completion: ALWAYS goes to REVIEW

### RA-Full Mode (9-10)
- DO NOT implement directly - requires orchestration
- Deploy multiple specialized agents
- Coordinate with atomic task locking
- Full verification phase required
- Comprehensive knowledge management

## RA Tags - Track Your Assumptions

🚨 **CRITICAL**: You MUST use the `add_ra_tag` MCP tool to record assumptions as you implement.

### Implementation Tags
- `#COMPLETION_DRIVE_IMPL:` Specific implementation assumption
- `#COMPLETION_DRIVE_INTEGRATION:` System integration assumption
- `#CONTEXT_DEGRADED:` Fuzzy memory, making educated guess
- `#CONTEXT_RECONSTRUCT:` Actively filling in missing details

### Pattern Detection Tags
- `#CARGO_CULT:` Code from pattern association, not requirement
- `#PATTERN_MOMENTUM:` Methods/features from completion drive
- `#ASSOCIATIVE_GENERATION:` Features that feel like they should exist

### Conflict Tags
- `#PATTERN_CONFLICT:` Multiple contradictory patterns feel valid
- `#TRAINING_CONTRADICTION:` Different contexts suggest opposing approaches

### Suggestion Tags
- `#SUGGEST_ERROR_HANDLING:` Error handling that feels needed
- `#SUGGEST_EDGE_CASE:` Edge cases should probably be handled
- `#SUGGEST_VALIDATION:` Input validation seems important
- `#SUGGEST_CLEANUP:` Resource cleanup feels necessary
- `#SUGGEST_DEFENSIVE:` Defensive programming seems prudent

For complete tag catalog with examples, see [RA_TAGS_CATALOG.md](reference/RA_TAGS_CATALOG.md).

## How to Add RA Tags

**During implementation**, use the MCP tool:

```python
add_ra_tag(
    task_id="current_task_id",
    ra_tag_text="#COMPLETION_DRIVE_IMPL: Assuming database connection pooling",
    agent_id="claude"
)
```

⛔ **DO NOT** just think about assumptions
✅ **DO** record every assumption using the tool

## Task Creation

Always create tasks first:

```python
create_task(
    name="Implement user authentication",
    description="Add OAuth2 authentication support",
    epic_name="Authentication System",
    project_name="My Project",
    ra_mode="standard",
    ra_score="5"
)
```

## Task Status Workflow

```
TODO → IN_PROGRESS → REVIEW → DONE
```

### Status Transitions

**Start work:**
```python
update_task_status(task_id, "IN_PROGRESS", agent_id)  # Auto-acquires lock
```

**Ready for review:**
```python
update_task_status(task_id, "REVIEW", agent_id)  # Releases lock for reviewer
```

**Mark complete:**
```python
update_task_status(task_id, "DONE", agent_id)  # Auto-releases lock
```

**CRITICAL**: If RA tags were used during implementation, task MUST go to REVIEW status, not directly to DONE. RA tags indicate assumptions that require validation.

## Knowledge Capture Guidelines

Capture knowledge ONLY for:
- ✅ Trial-and-error solutions (took multiple attempts)
- ✅ Non-obvious gotchas discovered
- ✅ User corrections (what NOT to do)
- ✅ Integration challenges that required research

Do NOT capture:
- ❌ Routine implementation details
- ❌ Standard patterns
- ❌ Obvious solutions

Example:
```python
upsert_knowledge(
    title="PostgreSQL FTS GIN Index Gotcha",
    content="Problem: Search was slow (2000ms). Tried: 1) BTREE index (no improvement), 2) Increasing work_mem (no improvement), 3) Finally discovered: FTS needs GIN index, not BTREE. Command: CREATE INDEX USING gin(to_tsvector('english', content)). Reduced search time to 50ms.",
    category="database_gotchas",
    tags='["postgresql", "fts", "gin_index", "performance"]',
    task_id="current_task_id"
)
```

## MCP Tools Reference

### Task Management
- `create_task()` - Create new task with RA metadata
- `update_task()` - Update task fields, RA tags, logs
- `update_task_status()` - Change status with auto-locking
- `get_task_details()` - Retrieve complete task info
- `add_ra_tag()` - Add assumption tags during implementation

### Knowledge Management
- `get_knowledge()` - Retrieve knowledge items
- `upsert_knowledge()` - Create/update knowledge
- `append_knowledge_log()` - Track knowledge changes

### Task Locking
- `acquire_task_lock()` - Manual lock (multi-agent only)
- `release_task_lock()` - Manual unlock
- **Preferred**: Use `update_task_status()` for automatic lock management

## Workflow Examples

See the examples directory for complete workflows:
- [Simple Mode Example](examples/simple-mode-example.md)
- [Standard Mode Example](examples/standard-mode-example.md)
- [RA-Light Mode Example](examples/ra-light-mode-example.md)

## Quality Standards

ALL MODES:
- Production-ready code with proper error handling
- Follow project conventions and patterns
- No TODO comments left in final code
- All acceptance criteria met

RA MODES ADDITIONAL:
- All assumptions explicitly tagged
- Integration points validated
- Pattern decisions documented
- Ready for verification phase

## Common Pitfalls

### Parameter Format Errors
RA tags must be JSON string arrays:
- ✓ Correct: `ra_tags='["#TAG: description"]'`
- ✗ Wrong: `ra_tags=["#TAG: description"]`

### Skipping REVIEW Status
If you used RA tags, the task MUST go through REVIEW before DONE.

### Forgetting to Add Tags
Don't just think about assumptions - use `add_ra_tag()` to record them.

### Over-capturing Knowledge
Only capture hard-won insights, not routine implementations.

## Version
RA Methodology v3.0.0 - Comprehensive assumption tracking across all complexity levels
