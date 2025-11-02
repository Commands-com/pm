# RA Tags Catalog

Complete reference for all Response Awareness tags with examples and usage guidelines.

## Tag Format

All RA tags follow this format:
```
#TAG_NAME: Specific description of the assumption or suggestion
```

**Critical**: Tags must include a colon (`:`) followed by a specific description. Generic tags without descriptions are not useful.

---

## Implementation Tags

These tags identify assumptions made during implementation based on patterns or incomplete information.

### #COMPLETION_DRIVE_IMPL
**When to use**: Implementation details assumed based on typical patterns

**Examples:**
```python
#COMPLETION_DRIVE_IMPL: Assuming database connection pooling is configured
#COMPLETION_DRIVE_IMPL: Using standard password hashing (bcrypt with salt)
#COMPLETION_DRIVE_IMPL: Implementing pagination with default limit of 20 items
#COMPLETION_DRIVE_IMPL: Error responses follow REST API standard format
```

**Why it matters**: These are educated guesses based on common patterns. They need verification to ensure they match actual requirements.

---

### #COMPLETION_DRIVE_INTEGRATION
**When to use**: Assumptions about how systems integrate or communicate

**Examples:**
```python
#COMPLETION_DRIVE_INTEGRATION: Email service expects JSON payload with 'to', 'subject', 'body'
#COMPLETION_DRIVE_INTEGRATION: WebSocket broadcasts go to all connected clients
#COMPLETION_DRIVE_INTEGRATION: Database transactions auto-commit on success
#COMPLETION_DRIVE_INTEGRATION: Auth tokens passed via Authorization header
```

**Why it matters**: Integration assumptions are high-risk. If wrong, they can cause cascading failures.

---

### #CONTEXT_DEGRADED
**When to use**: Memory is fuzzy, making educated guess

**Examples:**
```python
#CONTEXT_DEGRADED: Vague memory of user preferences table structure
#CONTEXT_DEGRADED: Uncertain if validation happens client-side or server-side
#CONTEXT_DEGRADED: Fuzzy on exact error codes used in this codebase
#CONTEXT_DEGRADED: Not sure if this service uses async/await or promises
```

**Why it matters**: Flags areas where you're operating with incomplete certainty. Reviewer should double-check these.

---

### #CONTEXT_RECONSTRUCT
**When to use**: Actively filling in details that seem like they should exist

**Examples:**
```python
#CONTEXT_RECONSTRUCT: Adding user role check (feels like it should be here)
#CONTEXT_RECONSTRUCT: Assuming rate limiting middleware is in place
#CONTEXT_RECONSTRUCT: Reconstructing expected database schema from usage
#CONTEXT_RECONSTRUCT: Inferring API contract from client-side code
```

**Why it matters**: You're building a mental model based on partial information. These need validation.

---

## Pattern Detection Tags

These tags identify code added from pattern recognition rather than explicit requirements.

### #CARGO_CULT
**When to use**: Code copied from pattern association, not requirement

**Examples:**
```python
#CARGO_CULT: Added try-catch because other controllers have it
#CARGO_CULT: Including logging statements like similar functions
#CARGO_CULT: Adding .gitkeep file because I saw it in other folders
#CARGO_CULT: Using same validation pattern as nearby code
```

**Why it matters**: Copying patterns blindly can add unnecessary code or miss context-specific needs.

---

### #PATTERN_MOMENTUM
**When to use**: Methods/features added because they feel like natural completions

**Examples:**
```python
#PATTERN_MOMENTUM: Added update() method since create() and delete() exist
#PATTERN_MOMENTUM: Including archive() alongside delete() for soft deletes
#PATTERN_MOMENTUM: Adding batch operations since single operations exist
#PATTERN_MOMENTUM: Created getUserById() to match other getXById() methods
```

**Why it matters**: Features that "feel right" may not be needed yet. Avoid over-engineering.

---

### #ASSOCIATIVE_GENERATION
**When to use**: Features that feel like they should exist in this context

**Examples:**
```python
#ASSOCIATIVE_GENERATION: Adding sort/filter options (feels standard for lists)
#ASSOCIATIVE_GENERATION: Including created_at/updated_at timestamps
#ASSOCIATIVE_GENERATION: Adding description field alongside name field
#ASSOCIATIVE_GENERATION: Including user_id foreign key (seems necessary)
```

**Why it matters**: Common features aren't always needed. Verify requirements first.

---

## Conflict Tags

These tags identify situations where multiple approaches seem equally valid.

### #PATTERN_CONFLICT
**When to use**: Multiple contradictory patterns feel valid

**Examples:**
```python
#PATTERN_CONFLICT: Could use REST or GraphQL - both seen in codebase
#PATTERN_CONFLICT: Uncertain between class-based or functional components
#PATTERN_CONFLICT: SQL joins vs. multiple queries - both patterns exist
#PATTERN_CONFLICT: Sync vs async processing - see examples of both
```

**Why it matters**: Conflicts indicate architectural inconsistency. Need guidance on preferred approach.

---

### #TRAINING_CONTRADICTION
**When to use**: Different training contexts suggest opposing approaches

**Examples:**
```python
#TRAINING_CONTRADICTION: Some sources say validate client-side, others server-side
#TRAINING_CONTRADICTION: Conflicting best practices for error handling in async code
#TRAINING_CONTRADICTION: Uncertainty about when to use transactions
#TRAINING_CONTRADICTION: Different authentication patterns in various frameworks
```

**Why it matters**: Framework-specific or context-specific choices need clarification.

---

## Suggestion Tags

These tags identify defensive programming or robustness improvements that seem prudent but weren't explicitly required.

### #SUGGEST_ERROR_HANDLING
**When to use**: Error handling that feels needed but wasn't specified

**Examples:**
```python
#SUGGEST_ERROR_HANDLING: Added try-catch for database connection failure
#SUGGEST_ERROR_HANDLING: Network timeout handling for API calls
#SUGGEST_ERROR_HANDLING: Null check before accessing nested property
#SUGGEST_ERROR_HANDLING: Graceful degradation if external service fails
```

**Best practice**: Always include error handling, but tag it to indicate it wasn't explicitly required.

---

### #SUGGEST_EDGE_CASE
**When to use**: Edge cases that should probably be handled

**Examples:**
```python
#SUGGEST_EDGE_CASE: Empty array handling in map function
#SUGGEST_EDGE_CASE: Division by zero check in calculation
#SUGGEST_EDGE_CASE: Handling simultaneous updates to same record
#SUGGEST_EDGE_CASE: UTF-8 characters in user input
```

**Best practice**: Edge cases prevent bugs, but verify which ones are actually priorities.

---

### #SUGGEST_VALIDATION
**When to use**: Input validation that seems important

**Examples:**
```python
#SUGGEST_VALIDATION: Email format validation before sending
#SUGGEST_VALIDATION: Password strength requirements (min 8 chars)
#SUGGEST_VALIDATION: File size limit check before upload
#SUGGEST_VALIDATION: SQL injection prevention in query params
```

**Best practice**: Validation is critical for security, but specific rules should be confirmed.

---

### #SUGGEST_CLEANUP
**When to use**: Resource cleanup that feels necessary

**Examples:**
```python
#SUGGEST_CLEANUP: Closing database connection in finally block
#SUGGEST_CLEANUP: Clearing interval timers on component unmount
#SUGGEST_CLEANUP: Deleting temporary files after processing
#SUGGEST_CLEANUP: Removing event listeners when no longer needed
```

**Best practice**: Cleanup prevents memory leaks and resource exhaustion.

---

### #SUGGEST_DEFENSIVE
**When to use**: Defensive programming that seems prudent

**Examples:**
```python
#SUGGEST_DEFENSIVE: Deep copy object to avoid mutation
#SUGGEST_DEFENSIVE: Type checking before method calls
#SUGGEST_DEFENSIVE: Bounds checking on array access
#SUGGEST_DEFENSIVE: Default fallback value if config missing
```

**Best practice**: Defensive code improves reliability, but verify it's not over-engineering.

---

## How to Choose the Right Tag

### Decision Tree

1. **Is it about how you're implementing something?**
   → Use #COMPLETION_DRIVE_IMPL or #COMPLETION_DRIVE_INTEGRATION

2. **Are you uncertain about the details?**
   → Use #CONTEXT_DEGRADED or #CONTEXT_RECONSTRUCT

3. **Did you copy a pattern from similar code?**
   → Use #CARGO_CULT, #PATTERN_MOMENTUM, or #ASSOCIATIVE_GENERATION

4. **Are there multiple valid approaches?**
   → Use #PATTERN_CONFLICT or #TRAINING_CONTRADICTION

5. **Is it defensive/robustness code you're adding?**
   → Use appropriate #SUGGEST_* tag

---

## Tag Examples by Scenario

### Scenario: Building a New API Endpoint

```python
# Creating task
create_task(
    name="Add user profile update endpoint",
    ra_mode="standard",
    ra_score="5"
)

# During implementation, add tags:
add_ra_tag(
    task_id="current_task_id",
    ra_tag_text="#COMPLETION_DRIVE_IMPL: Using PUT method for updates (REST convention)",
    agent_id="claude"
)

add_ra_tag(
    task_id="current_task_id",
    ra_tag_text="#SUGGEST_VALIDATION: Email format validation added",
    agent_id="claude"
)

add_ra_tag(
    task_id="current_task_id",
    ra_tag_text="#SUGGEST_ERROR_HANDLING: 404 if user not found, 400 for invalid data",
    agent_id="claude"
)
```

### Scenario: Integrating External Service

```python
add_ra_tag(
    task_id="current_task_id",
    ra_tag_text="#COMPLETION_DRIVE_INTEGRATION: Assuming API returns JSON with 'data' and 'error' fields",
    agent_id="claude"
)

add_ra_tag(
    task_id="current_task_id",
    ra_tag_text="#CONTEXT_RECONSTRUCT: Inferring authentication header format from examples",
    agent_id="claude"
)

add_ra_tag(
    task_id="current_task_id",
    ra_tag_text="#SUGGEST_ERROR_HANDLING: Retry logic for network failures (exponential backoff)",
    agent_id="claude"
)
```

---

## Common Mistakes

### ❌ Too Generic
```python
#COMPLETION_DRIVE_IMPL: Making an assumption
```
**Problem**: Doesn't say what the assumption is.

### ✅ Specific
```python
#COMPLETION_DRIVE_IMPL: Assuming user sessions expire after 24 hours of inactivity
```
**Better**: Clear, actionable assumption that can be verified.

---

### ❌ Missing Context
```python
#SUGGEST_VALIDATION: Added validation
```
**Problem**: What kind of validation?

### ✅ Specific
```python
#SUGGEST_VALIDATION: Email format regex validation before database insert
```
**Better**: Reviewer knows exactly what to verify.

---

## Tag Frequency Guidelines

- **Simple Mode (1-3)**: 2-5 tags typical
- **Standard Mode (4-6)**: 5-10 tags typical
- **RA-Light Mode (7-8)**: 10-20 tags typical
- **RA-Full Mode (9-10)**: 20+ tags typical

**If you have zero tags, you're probably missing assumptions!**

---

## Summary

RA tags are your self-awareness system. They help you recognize when you're:
- Making assumptions (COMPLETION_DRIVE)
- Operating with fuzzy memory (CONTEXT_DEGRADED)
- Following patterns without requirements (CARGO_CULT, PATTERN_MOMENTUM)
- Facing design conflicts (PATTERN_CONFLICT)
- Adding defensive code (SUGGEST_*)

Tag early, tag often. Better to over-tag than under-tag.
