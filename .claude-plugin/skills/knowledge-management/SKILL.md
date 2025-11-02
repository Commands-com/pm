---
name: knowledge-management
description: Capture hard-won insights, gotchas, and trial-and-error solutions in the knowledge system. Use when encountering non-obvious problems, multi-attempt solutions, user corrections, or debugging issues that required research.
allowed-tools: Read, Grep, Glob
---

# Knowledge Management

This skill guides proper knowledge capture in the PM Dashboard knowledge system.

## Core Principle

**Only capture what's hard-won, not what's routine.**

Knowledge items are for future you and your team to avoid repeating painful debugging sessions or trial-and-error.

## When to Capture Knowledge

### ✅ DO Capture

**Trial-and-Error Solutions** (took multiple attempts):
```python
upsert_knowledge(
    title="PostgreSQL FTS GIN Index Required (Not BTREE)",
    content="Problem: Search slow (2000ms). Tried: 1) BTREE index (no help), 2) Increased work_mem (no help), 3) Finally: GIN index required for FTS. Command: CREATE INDEX USING gin(to_tsvector('english', content)). Result: 50ms search time.",
    category="database_gotchas",
    tags='["postgresql", "fts", "performance", "indexing"]',
    task_id="current_task_id"
)
```

**Non-Obvious Gotchas**:
```python
upsert_knowledge(
    title="GitHub OAuth Requires User-Agent Header",
    content="Gotcha: GitHub OAuth API returns 403 without User-Agent header. Not prominently documented. Required: User-Agent: YourAppName/1.0",
    category="integration_gotchas",
    tags='["github", "oauth", "http_headers", "403"]',
    task_id="current_task_id"
)
```

**User Corrections** (what NOT to do):
```python
upsert_knowledge(
    title="FastMCP Parameters Must Be Strings",
    content="Critical: FastMCP only accepts string parameters. Passing task_id=123 (int) fails silently. Must use task_id='123' (string). Applies to ALL MCP parameters.",
    category="user_corrections",
    tags='["fastmcp", "parameters", "types", "gotcha"]',
    task_id="current_task_id"
)
```

**Integration Challenges** (required research/debugging):
```python
upsert_knowledge(
    title="WebSocket Connection Requires CORS Headers",
    content="Problem: WebSocket connections failed from frontend. Tried: 1) Different ports (failed), 2) Finally discovered: Need CORS headers for WebSocket handshake. Solution: Add Access-Control-Allow-Origin to WebSocket endpoint.",
    category="integration_gotchas",
    tags='["websocket", "cors", "frontend", "connection"]',
    task_id="current_task_id"
)
```

### ❌ DON'T Capture

**Routine Implementations**:
- Standard CRUD operations
- Basic form validation
- Common patterns (already documented elsewhere)
- Straightforward API calls

**Obvious Solutions**:
- "Added try-catch for error handling" (standard practice)
- "Used async/await for API call" (expected pattern)
- "Created Pydantic model for validation" (normal approach)

## Knowledge Hierarchy

**Project-Level** - Broad architectural insights:
```python
upsert_knowledge(
    title="Database Migration Strategy",
    content="Always use Alembic for schema changes. Manual ALTER TABLE caused production downtime.",
    project_id="3",
    category="architecture"
)
```

**Epic-Level** - Feature-specific patterns:
```python
upsert_knowledge(
    title="Authentication Flow Best Practices",
    content="Use JWT with HttpOnly cookies, not localStorage (XSS risk).",
    project_id="3",
    epic_id="5",
    category="security"
)
```

**Task-Level** - Specific implementation details:
```python
upsert_knowledge(
    title="Safari Flexbox Quirk",
    content="Safari 14 needs -webkit-flex prefix. Safari 15+ works with standard flexbox.",
    task_id="42",
    category="css_gotchas"
)
```

## Categories

**Recommended categories:**
- `gotchas` - Non-obvious problems
- `user_corrections` - Mistakes to avoid
- `architecture_decisions` - High-level choices
- `integration_gotchas` - External service issues
- `performance_optimizations` - What actually worked
- `security_patterns` - Security-related insights
- `database_gotchas` - Database-specific issues
- `css_gotchas` - Browser/CSS quirks
- `multi_attempt_solutions` - Trial-and-error wins

## Tags vs Categories

**Categories**: Broad grouping (gotchas, decisions, patterns)
**Tags**: Specific technologies/concepts (postgresql, oauth, safari, websocket)

```python
upsert_knowledge(
    title="...",
    content="...",
    category="integration_gotchas",  # Broad
    tags='["github", "oauth", "api", "http_headers"]'  # Specific
)
```

## Knowledge Retrieval

```python
# Get project-wide gotchas
get_knowledge(project_id="3", category="gotchas")

# Get epic-specific architecture decisions
get_knowledge(project_id="3", epic_id="5", category="architecture_decisions")

# Get task-specific notes
get_knowledge(task_id="42")

# Search by tags (use limit to avoid overwhelming results)
get_knowledge(project_id="3", category="security", limit="10")
```

## Quality Standards

### Good Knowledge Item

**Clear problem statement**:
- What was the problem?
- What did you try?
- What finally worked?
- Why is this non-obvious?

```python
upsert_knowledge(
    title="Clear Problem → Attempts → Solution",
    content="Problem: [specific issue]. Tried: 1) [approach 1] (failed because X), 2) [approach 2] (failed because Y), 3) Finally: [solution] worked because Z. Time saved for next person: 2 hours.",
    category="gotchas",
    tags='["specific", "searchable", "tags"]'
)
```

### Poor Knowledge Item

**Vague or routine**:
```python
# ❌ Too vague
upsert_knowledge(
    title="Fixed a bug",
    content="There was a bug and I fixed it.",
    category="general"
)

# ❌ Too routine
upsert_knowledge(
    title="Added error handling",
    content="Added try-catch block to handle errors.",
    category="patterns"
)
```

## Knowledge Logging

Track changes with append_knowledge_log:

```python
append_knowledge_log(
    knowledge_id="123",
    action_type="update",
    change_reason="Added note about Safari 15+ compatibility",
    created_by="claude"
)
```

## Integration with RA Methodology

Knowledge complements RA tags:

- **RA Tags**: Track assumptions DURING implementation
- **Knowledge**: Capture lessons AFTER solving problems

**Workflow**:
1. Implement with RA tags
2. Encounter non-obvious problem
3. Try multiple solutions
4. Finally find what works
5. Capture as knowledge item
6. Link to task for audit trail

## Examples by Scenario

### CSS/Browser Issue
```python
upsert_knowledge(
    title="Safari Grid Layout Bug with position:sticky",
    content="Problem: Sticky header broken in Safari. position:sticky inside CSS grid fails in Safari 14-15. Tried: 1) z-index changes (failed), 2) Finally: Use position:fixed with JS scroll listener instead.",
    category="css_gotchas",
    tags='["safari", "css_grid", "position_sticky", "workaround"]'
)
```

### Database/Performance
```python
upsert_knowledge(
    title="SQLite WAL Mode Checkpoint Timing",
    content="Problem: Database file growing unbounded. Tried: 1) Manual VACUUM (temporary fix), 2) Finally: Configure WAL checkpoint interval. PRAGMA wal_autocheckpoint=1000. Keeps DB size stable.",
    category="database_gotchas",
    tags='["sqlite", "wal", "performance", "file_size"]'
)
```

### API Integration
```python
upsert_knowledge(
    title="Stripe Webhook Signature Verification Order",
    content="Critical: Must verify webhook signature BEFORE parsing body. Parsing first makes signature invalid. Correct order: 1) Get raw body, 2) Verify signature, 3) Parse JSON. Wasted 3 hours on this.",
    category="integration_gotchas",
    tags='["stripe", "webhooks", "security", "signature_verification"]'
)
```

## Summary

Knowledge management is about **capturing pain to prevent future pain**.

If it took you multiple attempts, surprised you, or came from a user correction, capture it. If it was routine or obvious, skip it.

Future you will thank present you.
