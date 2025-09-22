# AGENTS.md

Guidance for AI agents integrating with this repository. It explains what this repo is, how to interact with it via MCP tools, and how to apply the Response Awareness (RA) methodology while working.

## What This Repo Is

This project is a Python-based project/epic/task manager with a real-time dashboard and an MCP (Model Context Protocol) server so agents can collaborate programmatically.

- Name: project-manager-mcp
- Backend: FastAPI + WebSockets (MCP + updates)
- DB: SQLite (WAL), schema for projects → epics → tasks (+ task logs)
- CLI: `project-manager-mcp` plus `python -m task_manager.cli`
- Dashboard: single-page UI served by the backend
- MCP Tools: create/update/list tasks, acquire/release locks, RA tagging, etc.

See `README.md` for installation, usage, and architecture details.

## MCP: How Agents Integrate

The server exposes a set of MCP tools that agents call to query, plan, execute, and verify work. Common tools include:

- `get_available_tasks`: Find work by status, exclude locked tasks
- `acquire_task_lock`: Atomically lock a task (moves status to IN_PROGRESS)
- `update_task_status`: Single-call status change with auto-locking
- `release_task_lock`: Explicitly release a held lock
- `create_task` / `update_task`: CRUD with full RA metadata support
- `get_task_details`: Full task + logs + dependencies
- `list_projects` / `list_epics` / `list_tasks`: Hierarchical queries
- `add_ra_tag`: Create RA tags with automatic context capture

Transport modes:
- `stdio` (default): for local/CLI integration
- `sse`: HTTP SSE endpoint for network clients

Refer to `README.md` and `docs/` for details and examples.

## Start With A Task (Required)

Before you do any work, you must create or select a task to work on.

- Why: Ensures ownership, locking, logging, RA tags, and status tracking.
- How:
  - MCP: `create_task` with `name`, `description`, and `epic_id`/`project_id` (optionally set `ra_mode`/`ra_score`).
  - Dashboard: Create a task via the UI in the correct project/epic.
  - Scope: If your work spans multiple concerns, split into separate tasks.
- Then: Acquire a lock (`acquire_task_lock`) before making changes, or rely on single-call `update_task_status` for short operations (auto-locking).

## Response Awareness (RA) Methodology

RA is a disciplined way for agents to surface uncertainty and assumptions during work so humans can focus review where it matters. The core artifact is the RA Tag.

### RA Tags

- Format: `#CATEGORY: Description`
- Common categories:
  - `#COMPLETION_DRIVE_IMPL`: Assumption made during implementation
  - `#COMPLETION_DRIVE_INTEGRATION`: Assumption about a dependency/integration
  - `#CONTEXT_RECONSTRUCT`: Filled gaps from incomplete context
  - `#SUGGEST_*` (e.g., `#SUGGEST_ERROR_HANDLING`): Proactive improvement ideas
  - `#PATTERN_MOMENTUM`: Following observed patterns in the codebase

### Zero‑Effort Context Capture

When creating tags via `add_ra_tag`, the system auto-enriches with:
- File path and line number
- Code symbol (function/class) and snippet
- Git branch and commit hash (when available)
- Programming language and environment hints
- Agent ID and timestamp

### Workflow

1. Encounter an uncertainty or make a non-trivial assumption.
2. Create an RA tag describing it (use `add_ra_tag`).
3. The system captures rich context automatically and stores the tag.
4. Reviewers validate or reject assumptions during review.
5. Validation outcomes are recorded for traceability.

### Modes and Scoring

- RA Modes: `simple`, `standard`, `ra-light`, `ra-full`
- Complexity Score: `1–10` (higher = more complex/uncertain)

Agents should adjust thoroughness of tagging and verification steps based on complexity and mode.

## Agent Workflow Best Practices

Use this loop to collaborate safely and effectively:

1. Discover work: `get_available_tasks` (filter by status)
2. Claim exclusive access: `acquire_task_lock` with your `agent_id`
3. Work in small, verifiable increments
4. Add RA tags for any assumptions or uncertainties: `add_ra_tag`
5. Update status as you progress: `update_task_status` (UI or DB vocabulary)
6. Release lock when done: move to `DONE` or call `release_task_lock`
7. For multi-step tasks, keep logs succinct and tag assumptions where validation is needed

Notes:
- Prefer the single-call `update_task_status` for short operations (auto-locking).
- Use explicit `acquire_task_lock` for longer work to prevent conflicts.
- Keep RA tags specific; one assumption per tag is usually best.

## Status Vocabulary

- UI: `TODO`, `IN_PROGRESS`, `REVIEW`, `DONE`
- Database: `pending`, `in_progress`, `review`, `completed`, `blocked`

The system maps between UI and DB vocabularies automatically in the tools.

## Setup Snippets (for Clients)

See `README.md` for full setup. Quick pointers:

- Start server and dashboard (default ports):
  - CLI: `project-manager-mcp`
  - Module: `python -m task_manager.mcp_server`

- Stdio MCP (local):
  - `project-manager-mcp --mcp-transport stdio`

- SSE MCP (network):
  - `project-manager-mcp --mcp-transport sse --port 9000`
  - Connect to `http://localhost:8081/sse` (per README)

- RA Tagging via CLI:
  - `python -m task_manager.cli add-ra-tag "#COMPLETION_DRIVE_IMPL: Assuming input validated upstream" --task-id 123`

## What “Good RA” Looks Like

- Clear: One concrete assumption per tag
- Contextual: Let auto-capture attach file, symbol, and git state
- Actionable: Phrase descriptions so reviewers know what to validate
- Traceable: Use your consistent `agent_id` for attribution

## Quick Reference

- Query: `get_available_tasks`, `list_tasks`
- Locking: `acquire_task_lock`, `release_task_lock`
- Status: `update_task_status`, `update_task`
- CRUD: `create_task`, `update_task`, `get_task_details`
- RA: `add_ra_tag`

If you’re an LLM/agent working in this repo, follow the workflow above and always record assumptions with RA tags. It makes your work safer, review faster, and outcomes more reliable.
