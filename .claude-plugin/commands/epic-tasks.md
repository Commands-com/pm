---
description: "Transform a technical epic into specific, actionable tasks with detailed implementation plans"
allowed-tools: Read, Write, Task
---

# Break Epic into Granular Tasks

Transform a technical epic into specific, actionable tasks with detailed implementation plans.

## Usage
```
/pm:epic-tasks <feature-name>
```

## Instructions

You are breaking down the epic for: **$ARGUMENTS**

## MCP Integration (preferred)
Use MCP to validate epic context and create tasks with structured metadata.

- Full name: mcp__project-manager-mcp__list_epics
- Full name: mcp__project-manager-mcp__list_tasks
- Full name: mcp__project-manager-mcp__create_task
- Full name: mcp__project-manager-mcp__update_task

Recommended flow:
1) Validate epic exists by name via `mcp__project-manager-mcp__list_epics` (or by id if known).
2) For each granular task, create it with `mcp__project-manager-mcp__create_task` using `epic_name=$ARGUMENTS` and initial `ra_metadata` (acceptance criteria, file list, dependencies) plus parallel execution fields: `parallel_group`, `conflicts_with`, and `parallel_eligible`.
3) For RA planning blocks, persist planning details in `ra_metadata.planning` via `mcp__project-manager-mcp__update_task`.
4) **CRITICAL**: Include proper `dependencies` field (task ID array) and parallel execution metadata to enable agent coordination.
5) Optionally mirror task files into `.pm/tasks/` for local context; MCP remains the source of truth.

### 1. Validate Epic Exists
- Prefer MCP: verify via `mcp__project-manager-mcp__list_epics` by name; error if not found.
- Optionally read `.pm/epics/$ARGUMENTS.md` for additional context.

### 2. Task Breakdown Philosophy

**CRITICAL: No Vague Tasks Allowed**

Every task must be:
- **2-8 hours maximum** (no exceptions)
- **Concrete and specific** (exact files, functions, components to build)
- **Independently executable** (minimal dependencies)
- **Clearly testable** (specific success criteria)
- **One logical unit of work** (single feature/component/endpoint)

**Bad Task Examples (DON'T DO THIS):**
- ❌ "Implement user management"
- ❌ "Add authentication"
- ❌ "Create API endpoints"
- ❌ "Build frontend"

**Good Task Examples:**
- ✅ "Create UserProfile React component with avatar, name, email fields and edit modal"
- ✅ "Implement POST /api/users/:id/profile endpoint with validation and error handling"
- ✅ "Add getUserById function to UserService with caching and error handling"
- ✅ "Write 8 unit tests for password validation function covering edge cases"

### 3. Analyze Epic for Task Categories

Read the epic and identify these categories:

#### Setup Tasks (0.5-2 hours each)
- Database migrations/schema changes
- Environment configuration
- Dependency installations
- Test framework setup
- CI/CD pipeline updates

#### Core Implementation Tasks (2-6 hours each)
- Individual API endpoints with full CRUD
- Single UI components with props and state
- Service functions with business logic
- Database models with relationships
- Integration with external services

#### Testing Tasks (1-4 hours each)
- Unit test suites for specific modules
- Integration tests for API endpoints
- Component tests for UI elements
- End-to-end test scenarios
- Performance testing for critical paths

#### Polish Tasks (1-3 hours each)
- Error handling improvements
- Performance optimizations
- Documentation updates
- Accessibility enhancements
- Security hardening

### 4. Create Granular Task List

For the project type, create extremely specific tasks:

#### For TypeScript Projects:
```
✅ Example Breakdown:
- "Create UserProfileForm.tsx with name/email/avatar fields, validation hooks, and submit handler"
- "Add useUserProfile custom hook with loading/error states and optimistic updates"
- "Implement PUT /api/users/:id/profile endpoint with Joi validation and error responses"
- "Write 6 unit tests for UserProfileForm covering validation, submission, and error states"
- "Add user profile route to React Router with authentication guard"
```

#### For Python Projects:
```
✅ Example Breakdown:
- "Create UserProfile SQLAlchemy model with bio, avatar_url, preferences JSONB fields"
- "Implement UserProfileService.update_profile() with validation and audit logging"
- "Add GET/PUT /users/{user_id}/profile FastAPI endpoints with Pydantic schemas"
- "Write 8 pytest tests for UserProfileService covering success/validation/error cases"
- "Create UserProfileSchema Pydantic model with custom validators"
```

### 5. Task Dependencies and Parallel Execution

For each task, use MCP parallel execution fields:

#### Required MCP Fields:
- **`dependencies`**: JSON string array of task IDs that MUST be completed first (e.g., '["1", "2"]')
- **`parallel_group`**: Group name for coordinated execution (e.g., "backend", "frontend", "integration")  
- **`conflicts_with`**: JSON string array of task IDs that cannot run simultaneously (e.g., '["3", "4"]')
- **`parallel_eligible`**: Boolean whether task supports parallel execution (default: true)

#### Parallel Group Strategy:
- **"backend"**: Database, API, service layer tasks
- **"frontend"**: UI components, pages, client-side logic  
- **"integration"**: Tasks requiring both backend and frontend complete
- **"testing"**: Test suites that can run after implementation
- **"setup"**: Infrastructure, configuration, schema changes

#### Example Task Creation with Parallel Fields:
```json
{
  "name": "Create UserProfile API endpoint",
  "epic_name": "user-management",
  "dependencies": '["1"]',  // depends on database schema task
  "parallel_group": "backend",
  "conflicts_with": '["5"]',  // conflicts with UserService refactoring
  "parallel_eligible": true
}
```

### 6. Use Task Agent for Large Epics

If the epic is complex (>10 tasks), use the Task tool to break it down in parallel:

```yaml
Task:
  description: "Break down epic into granular implementation tasks"
  subagent_type: "general-purpose"
  prompt: |
    Break down the epic: $ARGUMENTS into specific, actionable tasks.
    
    Epic content: [epic content here]
    
    Create 8-15 granular tasks following these rules:
    - Each task is 2-8 hours maximum
    - Specific files/functions/components to build
    - Concrete acceptance criteria
    - Clear testing requirements
    - No vague descriptions allowed
    
    For each task, provide:
    1. Specific implementation details
    2. Exact files to create/modify
    3. Testing checklist
    4. Dependencies on other tasks
    5. Size estimate (S/M/L)
    
    Use the task template from .pm/templates/task-standard.md
    
    Return: List of task files created with brief summary
```

### 7. Create Task Files

Create numbered task files in `.pm/tasks/`:
- `001-$ARGUMENTS.md` - First task
- `002-$ARGUMENTS.md` - Second task
- etc.

Each task file must use the template from `.pm/templates/task-standard.md` with:

**Required Sections:**
- **What Exactly Gets Built**: Specific implementation details
- **File Changes**: Exact files with line count estimates
- **Acceptance Criteria**: Specific, testable requirements
- **Testing Checklist**: Comprehensive test requirements
- **Dependencies**: Clear task dependencies

#### RA Planning Block (add to every task file)
Include a short RA Planning section so implementation can start with tags and verification can cross‑reference planning assumptions:

```
## RA Planning

### Path Decisions
- #PATH_DECISION: [topic]
  - Options: A) ..., B) ...
  - Chosen: [A/B/other] — Decision rationale: [one line]

### Planning Uncertainties
- PLAN_UNCERTAINTY: [unknown/assumption to confirm]
- PLAN_UNCERTAINTY: [if none, write "None"]

### Interface Contracts
- Endpoints/APIs: [list]
- Schemas: [request/response or types]
- Errors/versioning: [expected error cases, compat notes]
```

### 8. Task Quality Validation

Review each task to ensure:
- [ ] Implementation is concrete and specific
- [ ] File changes are listed with estimates
- [ ] Acceptance criteria are testable
- [ ] Testing approach is comprehensive
- [ ] Dependencies are clearly identified
- [ ] Size is appropriate (2-8 hours)
- [ ] No vague language used
- [ ] RA Planning section present with at least one `PLAN_UNCERTAINTY` (or explicitly "None")
- [ ] Any `#PATH_DECISION` includes a chosen option and decision rationale
- [ ] Interface contracts are explicit (no TBD)

### 9. Create Task Summary and MCP Task Tracking

Generate a summary file: `.pm/tasks/$ARGUMENTS-summary.md`

```markdown
# Task Summary: $ARGUMENTS

## Overview
- **Total Tasks**: X
- **Estimated Hours**: X-Y hours total
- **Parallel Groups**: X independent streams for Y hours, then sequential integration
- **Critical Path**: X hours minimum

## Task Categories
- **Setup**: X tasks (X hours) - Database schema
- **Implementation**: X tasks (X hours) - MCP tools, UI, API endpoints
- **Integration**: X tasks (X hours) - Agent context injection
- **Testing**: X tasks (X hours) - E2E testing and polish

## Parallel Execution Plan

### Stream 1: Backend Development (X hours)
**Tasks XXX → XXX → XXX**
- Task XXX: Create Database Schema (1h) 
- Task XXX: Implement get_knowledge MCP Tool (2h)
- Task XXX: Implement upsert_knowledge MCP Tool (2h) 

### Stream 2: Frontend Development (X hours)
**Tasks XXX → XXX**
- Task XXX: Add Book Icon and Modal HTML (2h)
- Task XXX: Implement Modal JavaScript Logic (3h)

### Stream 3: Integration & Testing (X hours - Sequential)
**Tasks XXX → XXX → XXX**
- Task XXX: Create API Endpoints (2h) - *Requires Stream 1 complete*
- Task XXX: Add MCP Context Injection (2h) - *Requires Tasks XXX, XXX, XXX*
- Task XXX: End-to-End Testing & Polish (2h) - *Requires all previous tasks*

## Critical Dependencies

### Hard Dependencies
- **Task XXX** depends on **Task XXX** (database schema needed)
- **Task XXX** depends on **Tasks XXX, XXX** (schema + sanitization utility)

### Soft Dependencies  
- Task XXX benefits from Task XXX (sanitization patterns)

## Optimal Execution Timeline

### Week 1: Parallel Development (Day 1-2)
**Stream 1 Developer**: Tasks XXX → XXX → XXX (X hours)
**Stream 2 Developer**: Tasks XXX → XXX (X hours)

### Week 1: Integration (Day 3)  
**Either Developer**: Tasks XXX → XXX (X hours)

**Total Timeline**: X-Y days with 2 developers, X-Y hours with 1 developer

## MCP Task Tracking

All tasks created in MCP system:
- **Task X**: Database Schema (Task XXX)
- **Task Y**: get_knowledge MCP Tool (Task XXX) 
- **Task Z**: upsert_knowledge MCP Tool (Task XXX)
[List all MCP task IDs with their .md file references]

## Implementation Notes

### Quality Standards
- Every task includes specific acceptance criteria
- All backend tasks include comprehensive unit tests
- Frontend tasks include manual testing checklists
- Integration tasks include performance verification

### File Organization
- Backend changes primarily in `src/task_manager/`
- Frontend changes in `src/task_manager/static/`
- Tests in `test/project_manager/`
- Migration scripts for database changes

### Testing Strategy
- Unit tests for all MCP tools (Tasks XXX-XXX)
- Integration tests for API endpoints (Task XXX)
- End-to-end workflow testing (Task XXX)
- Manual cross-browser testing (Task XXX)

---

**Ready to Start**: Task XXX (Database Schema) and Task XXX (Book Icon HTML)
**Next Command**: `/pm:task-start XXX-epic-name` or `/pm:task-start XXX-epic-name`
```

### 10. CRITICAL: MCP Task Creation Requirements

When creating MCP tasks, you MUST avoid these critical mistakes:

#### ❌ Common Mistakes (DO NOT DO):
- Creating MCP tasks without proper `dependencies` field
- Missing `.md` file references in task names or descriptions  
- Losing parallel execution information from task analysis
- Using only ra_metadata for dependencies instead of actual MCP `dependencies` field

#### ✅ Required MCP Task Creation:
```json
mcp__project-manager-mcp__create_task(
  name="Implement OAuth2 authentication with Google and GitHub providers",
  description="Add OAuth2 authentication support - see .pm/tasks/002-knowledge-management-system-mvp.md",
  epic_name="Knowledge Management System MVP",
  dependencies='["1"]',  // CRITICAL: Actual MCP dependencies field, not just ra_metadata
  parallel_group="backend",
  conflicts_with='["5", "7"]',
  parallel_eligible=true,
  ra_metadata='{"file_reference": ".pm/tasks/002-knowledge-management-system-mvp.md", "estimated_hours": 3, "complexity_factors": ["OAuth2 integration", "Multi-provider support"]}'
)
```

#### ✅ Verification Checklist:
- [ ] **Dependencies**: Used actual `dependencies` field with task ID array  
- [ ] **File References**: Included `.md` file path in description or ra_metadata
- [ ] **Parallel Execution**: Set parallel_group, conflicts_with, parallel_eligible
- [ ] **Task Mapping**: Created MCP task for every .md file with proper numbering
- [ ] **Cross-Reference**: MCP task names match .md file task names

### 11. Success Message

```
✅ Epic broken down into X granular tasks!

📊 Task Breakdown:
  ✓ X tasks created (avg Y hours each)
  ✓ X parallel execution streams identified  
  ✓ All tasks have specific implementation details
  ✓ Comprehensive testing requirements included

🔗 MCP Integration:
  ✓ X MCP tasks created with proper dependencies field
  ✓ Parallel execution metadata: parallel_group, conflicts_with, parallel_eligible
  ✓ All .md file references included in task descriptions
  ✓ Ready for multi-agent coordination and parallel execution

📁 Files Created:
  .pm/tasks/001-$ARGUMENTS.md through 0XX-$ARGUMENTS.md
  .pm/tasks/$ARGUMENTS-summary.md

🚀 Next Steps:
  1. Review tasks for accuracy and completeness
  2. Verify MCP tasks have correct dependencies and parallel execution fields
  3. Start first task: /pm:task-start 001-$ARGUMENTS
  4. Launch parallel streams for faster delivery  
  5. Track progress: /pm:status

💡 Each task is designed for 2-8 hours with agent coordination via MCP parallel execution fields!
```

## Task Breakdown Quality Standards

Every task must have:
- [ ] **Concrete Implementation**: Exact code/components to build
- [ ] **File-Level Detail**: Specific files to create/modify with line estimates
- [ ] **Testing Requirements**: Unit/integration/manual test checklists
- [ ] **Clear Dependencies**: What must be done first
- [ ] **Success Criteria**: How to know when it's complete
- [ ] **Time Estimate**: Realistic 2-8 hour range

Remember: The goal is to eliminate ambiguity and make every task immediately actionable by any developer on the team!

### 11. Optional RA Planning Review

If the epic is complex or spans multiple domains, run a lightweight planning review to confirm RA readiness before implementation:

```yaml
Task:
  description: "RA planning review for tasks in epic $ARGUMENTS"
  subagent_type: "general-purpose"
  prompt: |
    You are the planning-reviewer agent. Validate that every task generated from epic "$ARGUMENTS" is RA-ready.

    SCOPE:
    - Read all `.pm/tasks/*$ARGUMENTS*.md` created by this command
    - Check RA Planning section presence and completeness
    - Ensure each `#PATH_DECISION` has a chosen option with a brief decision rationale
    - Ensure `PLAN_UNCERTAINTY` items are listed (or explicitly "None")
    - Ensure interface contracts (endpoints/schemas/errors) are explicit and testable

    OUTPUTS:
    - A concise report listing any tasks needing fixes (missing RA Planning, missing rationale, unspecified interfaces)
    - If trivial omissions (e.g., explicit "None"), you may amend the task files to add the missing line; otherwise, suggest exact edits
    - A readiness summary with counts: tasks ready vs needs changes

    TAG POLICY:
    - Use `PLAN_UNCERTAINTY` and `#PATH_DECISION` only in planning docs
    - Do NOT add implementation tags (e.g., COMPLETION_DRIVE) at this stage

    DELIVERABLE:
    - "RA Planning Review Summary" with file-by-file status and a final "READY TO IMPLEMENT" or "REQUIRES UPDATES" decision.
```
