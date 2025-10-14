---
description: "Display comprehensive overview of all PRDs, epics, and tasks with progress tracking"
allowed-tools: Read, Bash
---

# Project Status Dashboard

Display comprehensive overview of all PRDs, epics, and tasks with progress tracking.

## Usage
```
/pm:status
```

## Instructions

Generate a comprehensive project status dashboard.

## MCP Integration (preferred)
Use MCP to fetch canonical project/epic/task data instead of filesystem scans.

- Full name: mcp__project-manager-mcp__list_projects
- Full name: mcp__project-manager-mcp__list_epics
- Full name: mcp__project-manager-mcp__list_tasks
- Full name: mcp__project-manager-mcp__get_available_tasks
- Full name: mcp__project-manager-mcp__get_task_details

Recommended flow:
1) Fetch projects: list recent N via `mcp__project-manager-mcp__list_projects`.
2) Fetch epics: `mcp__project-manager-mcp__list_epics` (optionally per project) and compute epic counts by status.
3) Fetch tasks: `mcp__project-manager-mcp__list_tasks` (optionally filter by project/epic/status) to compute counts and hours, and to build progress metrics.
4) Optionally use `mcp__project-manager-mcp__get_available_tasks` to highlight next available work and parallel opportunities.
5) For spotlighted tasks, call `mcp__project-manager-mcp__get_task_details` to surface RA metadata (mode, score, dependencies) and recent log entries.

If MCP is unavailable, fall back to filesystem-based scanning below.

### 1. Scan PM Directories
First, use `find` command or direct path access to locate the `.pm` directory:
```bash
find . -name ".pm" -type d
# Or use absolute path if needed
ls -la .pm/
```

Check for existence and content of:
- `.pm/prds/` - Product Requirements Documents
- `.pm/epics/` - Technical implementation plans
- `.pm/tasks/` - Individual task files
- `.pm/config.json` - Project configuration

IMPORTANT: The `.pm` directory may be hidden. Use `ls -la` or `find` commands to locate it properly.
If directories don't exist: "⚠️ PM workflow not initialized. Run: /pm:init"

### 2. Collect PRD Status
For each file in `.pm/prds/`:
- Read frontmatter for status, created date, description
- Count total PRDs by status (backlog, in-progress, completed)
- Identify most recent PRD activity

### 3. Collect Epic Status  
For each file in `.pm/epics/`:
- Read frontmatter for status, progress percentage, task count
- Calculate overall epic completion
- Identify epics in various states

### 4. Collect Task Status
For each file in `.pm/tasks/`:
- Read frontmatter for status, size estimate, dependencies
- Count tasks by status (open, in-progress, blocked, completed)
- Calculate total estimated vs. completed hours
- Identify parallel execution opportunities
- Find blocked or overdue tasks

### 5. Generate Status Dashboard

```markdown
# 📊 PM Workflow Status Dashboard

## 🎯 Overview
- **Project Type**: {project_type from config}
- **Last Updated**: {current_timestamp}
- **Workflow Version**: {version from config}

## 📋 Product Requirements (PRDs)
- **Total PRDs**: {total_count}
  - 📝 Backlog: {backlog_count}
  - 🔄 In Progress: {in_progress_count}
  - ✅ Completed: {completed_count}

### Recent PRD Activity
{list recent PRDs with status and dates}

## 🏗️ Technical Epics
- **Total Epics**: {total_count}
  - 📋 Planning: {planning_count}
  - 🔄 In Progress: {in_progress_count} ({avg_completion}% avg completion)
  - ✅ Completed: {completed_count}

### Epic Progress Summary
{list epics with progress bars and task counts}

## ⚡ Task Execution
- **Total Tasks**: {total_count}
  - ⏳ Open: {open_count}
  - 🔄 In Progress: {in_progress_count}
  - 🚫 Blocked: {blocked_count}
  - ✅ Completed: {completed_count}

### Effort Tracking
- **Total Estimated**: {total_hours} hours
- **Completed Work**: {completed_hours} hours ({percentage}%)
- **Remaining Work**: {remaining_hours} hours
- **Average Task Size**: {avg_hours} hours

### Parallel Execution Opportunities
{list tasks that can run in parallel}

### ⚠️ Attention Needed
{list blocked, overdue, or problematic tasks}

## 🚀 Active Work Streams
{group in-progress tasks by parallel execution streams}

## 📈 Velocity Metrics
- **Tasks Completed This Week**: {weekly_completed}
- **Average Completion Time**: {avg_completion_time}
- **Success Rate**: {completion_percentage}%

## 🎯 Next Recommended Actions
{intelligent suggestions based on current state}
```

### 6. Analyze Bottlenecks
Identify potential issues:
- Tasks blocked for >48 hours
- Epics with no recent progress
- PRDs stuck in backlog
- Dependency chain problems
- Resource allocation conflicts

### 7. Generate Recommendations
Based on current state, suggest next actions:

#### If many tasks are open but none in progress:
- "🚀 Ready to start development! Consider: /pm:task-start {next_priority_task}"

#### If tasks are blocked:
- "🚫 {blocked_count} tasks blocked. Review dependencies and resolve blockers first."

#### If parallel opportunities exist:
- "⚡ {parallel_count} tasks can run in parallel. Consider launching multiple work streams."

#### If epics need task breakdown:
- "📋 Epic '{epic_name}' ready for task breakdown: /pm:epic-tasks {epic_name}"

### 8. Performance Analysis
Calculate key metrics:
- **Throughput**: Tasks completed per week
- **Lead Time**: Average time from task creation to completion
- **Cycle Time**: Average time from task start to completion
- **Success Rate**: Percentage of tasks completed without rework

### 9. Resource Planning
Analyze workload:
- Total remaining effort by category
- Critical path analysis
- Parallel execution capacity
- Resource allocation suggestions

### 10. Export Options
Offer additional views:
```
📊 Additional Views Available:
  /pm:status --detailed     # Detailed task-by-task breakdown
  /pm:status --timeline     # Gantt chart view of tasks
  /pm:status --velocity     # Performance analytics
  /pm:status --export       # Export to CSV/JSON for external tools
```

### 11. Integration Status
If GitHub integration is enabled, show:
- Sync status with GitHub issues
- Last sync timestamps
- Any sync failures or warnings

### 12. Health Checks
Validate workflow health:
- ✅ All tasks have proper acceptance criteria
- ⚠️ Tasks missing size estimates: {count}
- ❌ Circular dependencies detected: {issues}
- 📋 PRDs without corresponding epics: {count}

The status dashboard provides a comprehensive, actionable view of the entire project management workflow, helping teams make informed decisions about priorities and resource allocation!
