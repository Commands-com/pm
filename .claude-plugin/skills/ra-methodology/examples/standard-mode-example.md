# Standard Mode Workflow Example

**Task**: Implement user search with filters
**Complexity Score**: 5
**RA Mode**: Standard
**Estimated Time**: 4 hours

---

## Complete Workflow

### 1. Create Task
```python
create_task(
    name="Implement user search with filters",
    description="Add search functionality with filters for role, status, department",
    epic_name="User Management",
    project_name="Dashboard App",
    ra_mode="standard",
    ra_score="5"
)
# Returns task_id: 87
```

### 2. Start Work
```python
update_task_status(task_id="87", status="IN_PROGRESS", agent_id="claude")
```

### 3. Review Existing Knowledge
```python
get_knowledge(project_id="3", category="search")
# Found: "PostgreSQL Full-Text Search Best Practices"
# Learned: Use GIN index for ts_vector columns
```

### 4. Implement with RA Tags

**Backend API:**
```python
# Added search endpoint
@router.get("/api/users/search")
async def search_users(
    query: str,
    role: Optional[str] = None,
    status: Optional[str] = None
):
    # PostgreSQL FTS implementation
```

**Tag assumptions:**
```python
add_ra_tag(
    task_id="87",
    ra_tag_text="#COMPLETION_DRIVE_IMPL: Using PostgreSQL full-text search with ts_vector",
    agent_id="claude"
)

add_ra_tag(
    task_id="87",
    ra_tag_text="#SUGGEST_VALIDATION: Sanitizing search input to prevent SQL injection",
    agent_id="claude"
)

add_ra_tag(
    task_id="87",
    ra_tag_text="#PATTERN_MOMENTUM: Adding pagination with default limit 20",
    agent_id="claude"
)
```

### 5. Encountered Problem (Multi-Attempt Solution)

**Tried:**
1. BTREE index → Search slow (2000ms) ❌
2. Increased work_mem → No improvement ❌
3. GIN index → Success! (50ms) ✓

**Capture knowledge:**
```python
upsert_knowledge(
    title="PostgreSQL FTS Requires GIN Index Not BTREE",
    content="Problem: Search was slow (2000ms). Tried: 1) BTREE index (no improvement), 2) Increasing work_mem (no improvement), 3) Finally discovered: FTS needs GIN index, not BTREE. Command: CREATE INDEX USING gin(to_tsvector('english', content)). Reduced search time to 50ms.",
    category="database_gotchas",
    tags='["postgresql", "fts", "gin_index", "performance"]',
    task_id="87"
)
```

### 6. Log Progress
```python
update_task(
    task_id="87",
    agent_id="claude",
    log_entry="Backend search API completed with GIN index optimization. Added knowledge item about index type requirement. Frontend filters next."
)
```

### 7. Complete Implementation

**Frontend:**
```typescript
// Search component with filters
<SearchBar onSearch={handleSearch} />
<FilterPanel filters={{ role, status, department }} />
<ResultsTable results={searchResults} />
```

**Add more tags:**
```python
add_ra_tag(
    task_id="87",
    ra_tag_text="#SUGGEST_EDGE_CASE: Empty search query returns all results with pagination",
    agent_id="claude"
)

add_ra_tag(
    task_id="87",
    ra_tag_text="#COMPLETION_DRIVE_INTEGRATION: Debouncing search input at 300ms",
    agent_id="claude"
)
```

### 8. Testing
- ✓ Unit tests for search query builder
- ✓ Integration tests for API endpoint
- ✓ Frontend tests for user interactions
- ✓ Performance test (< 100ms response time)

### 9. Mark for Review
```python
update_task_status(task_id="87", status="REVIEW", agent_id="claude")
```

### 10. Review Process

Reviewer validates:
- ✓ GIN index approach confirmed (found in knowledge base)
- ✓ Input sanitization prevents SQL injection
- ✓ Pagination default (20) matches design spec
- ✓ Debounce timing (300ms) is standard for this project
- ✓ Empty query behavior is acceptable

### 11. Mark Done
```python
update_task_status(task_id="87", status="DONE", agent_id="reviewer")
```

---

## Timeline

- Create task: 5 min
- Review existing knowledge: 10 min
- Implement backend: 1.5 hours
- Debug index performance: 1 hour (trial-and-error)
- Capture knowledge: 5 min
- Implement frontend: 1 hour
- Testing: 45 min
- Review: 15 min

**Total**: ~4 hours 20 min

---

## Key Differences from Simple Mode

| Aspect | Simple Mode | Standard Mode |
|--------|-------------|---------------|
| RA Tags | 1-3 tags | 5-10 tags |
| Knowledge | Rarely | When encountering gotchas |
| Testing | Basic | Comprehensive |
| Documentation | Minimal | Assumptions in code comments + RA tags |
| Review Depth | Quick validation | Thorough assumption check |

---

## Standard Mode Checklist

Before marking REVIEW:
- ✓ All major decisions tagged with RA tags
- ✓ Hard-won insights captured as knowledge
- ✓ Unit + integration tests passing
- ✓ Code comments explain key assumptions
- ✓ Acceptance criteria met
- ✓ No TODO comments left in code
