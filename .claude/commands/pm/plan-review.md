---
description: "Run a lightweight RA planning review to validate tasks are ready for implementation"
allowed-tools: Read, Write, Task
---

# RA Planning Review

Validate that tasks derived from an epic include the RA Planning block (path decisions, planning uncertainties, and interface contracts) before implementation starts.

## Usage
```
/pm:plan-review <epic-name>
```
Example: `/pm:plan-review user-auth`

## Instructions

You are running a lightweight RA planning review for the epic: **$ARGUMENTS**

## MCP Integration (preferred)
Use MCP to enumerate tasks under the epic and persist review findings.

- Full name: mcp__project-manager-mcp__list_epics — Resolve the epic
- Full name: mcp__project-manager-mcp__list_tasks — List tasks for the epic
- Full name: mcp__project-manager-mcp__get_task_details — Read current planning metadata
- Full name: mcp__project-manager-mcp__update_task — Persist review results and logs

Recommended flow:
1) Resolve epic via `mcp__project-manager-mcp__list_epics`.
2) Fetch tasks for that epic via `mcp__project-manager-mcp__list_tasks(epic_id|epic_name)`.
3) After agent review, write a concise `log_entry` and store findings under `ra_metadata.planning_review` via `...__update_task` for each task.
4) If trivial fixes are auto-applied to local files, reflect that in MCP logs as well.

### 1. Validate Inputs
- Prefer MCP: resolve epic and enumerate tasks using MCP functions above.
- Fallback: check `.pm/epics/$ARGUMENTS.md` and list `.pm/tasks/*$ARGUMENTS*.md`.
- If no tasks found: suggest running `/pm:epic-tasks $ARGUMENTS`.

### 2. Deploy Planning Reviewer Agent

Use the Task tool to deploy the planning-reviewer agent and scan all matching tasks:

```yaml
Task:
  description: "RA planning readiness review for epic $ARGUMENTS"
  subagent_type: "general-purpose"
  prompt: |
    You are the planning-reviewer agent. Validate that every task for epic "$ARGUMENTS" is RA-ready.

    FILES TO REVIEW:
    - Epic: .pm/epics/$ARGUMENTS.md
    - Tasks: .pm/tasks/*$ARGUMENTS*.md

    CHECKLIST:
    1) RA Planning section exists in each task
    2) Path decisions present where applicable:
       - Use `#PATH_DECISION: <topic>`
       - Record a chosen option and a brief decision rationale
    3) Planning uncertainties enumerated:
       - Use `PLAN_UNCERTAINTY: <item>` per uncertainty
       - If none, include explicit `PLAN_UNCERTAINTY: None`
    4) Interface contracts are explicit and testable:
       - Endpoints/APIs listed
       - Request/Response schemas or data types
       - Error cases/versioning notes
    5) No "TBD" placeholders for interfaces

    TAG POLICY:
    - Only use planning tags: `#PATH_DECISION`, `PLAN_UNCERTAINTY`
    - Do NOT add implementation tags (e.g., `#COMPLETION_DRIVE_*`)

    OUTPUTS:
    - Produce a concise "RA Planning Review Summary" with file-by-file READY/REQUIRES_UPDATES status
    - For trivial omissions (e.g., explicit `PLAN_UNCERTAINTY: None`), you may amend task files directly
    - For larger gaps, propose exact edits without implementing them
    - Finish with a single decision line: READY_TO_IMPLEMENT or REQUIRES_UPDATES
```

### 3. Present Summary
When the review completes, present the summary returned by the agent and highlight any files needing updates.

### 4. Next Steps
- If READY_TO_IMPLEMENT: proceed with `/pm:task-start <task>` for the first task
- If REQUIRES_UPDATES: apply the suggested edits, re-run `/pm:plan-review $ARGUMENTS`, then proceed

The goal is to ensure RA signals are present in tasks so implementation can begin immediately and verification can cross-reference planning assumptions.
