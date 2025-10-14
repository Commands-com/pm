---
description: "Intelligently recommend the next highest-priority task to work on based on dependencies and project status"
allowed-tools: Read
---

# Get Next Priority Task

Intelligently recommend the next highest-priority task to work on based on dependencies, parallel opportunities, and project status.

## Usage
```
/pm:next
```

## Instructions

Analyze the current project state to recommend the optimal next task for execution.

## MCP Integration (preferred)
Use MCP to identify available tasks and compute a recommendation.

- Full name: mcp__project-manager-mcp__get_available_tasks — Primary list of ready tasks
- Full name: mcp__project-manager-mcp__list_tasks — For additional filtering or scoring
- Full name: mcp__project-manager-mcp__get_task_details — Deep context for top candidates

Recommended flow:
1) Call `mcp__project-manager-mcp__get_available_tasks` (e.g., status=TODO, include_locked=false) to fetch candidates.
2) Score by: dependency readiness, RA score (complexity), epic priority, estimated hours, and recent activity.
3) For the top 3 tasks, fetch `...__get_task_details` and present concise rationales.
4) Provide a “start now” suggestion that points to `/pm:task-start <task>` which will handle locking and status via MCP.

### 1. Scan Task Status
Read all tasks in `.pm/tasks/` and categorize by status:
- **Open**: Available for execution
- **In Progress**: Currently being worked on
- **Blocked**: Waiting for dependencies
- **Completed**: Finished tasks

### 2. Dependency Analysis
For each open task:
- Check `depends_on` field for prerequisite tasks
- Verify all dependencies are completed
- Identify tasks with no remaining dependencies (ready to start)
- Calculate dependency chain length for prioritization

### 3. Parallel Execution Opportunities
Identify tasks that can run simultaneously:
- Check `parallel: true` flag
- Review `conflicts_with` field to avoid conflicts
- Group compatible tasks for parallel execution
- Consider current in-progress tasks for conflict avoidance

### 4. Priority Scoring Algorithm
Score each available task based on:

#### Critical Path Impact (Weight: 40%)
- Tasks on critical path get highest priority
- Tasks blocking other tasks get bonus points
- Tasks with many dependents score higher

#### Effort vs. Value (Weight: 30%)
- Smaller tasks (S/M) get priority for quick wins
- Tasks completing user-facing features get bonus
- Tasks unblocking parallel streams score higher

#### Resource Availability (Weight: 20%)
- Match task requirements to available skills/resources
- Prefer tasks that can utilize currently idle resources
- Consider context-switching overhead

#### Risk Factors (Weight: 10%)
- Penalize tasks with external dependencies
- Boost tasks that reduce technical risk
- Consider tasks that validate critical assumptions

### 5. Generate Recommendations

#### Single Task Recommendation
```markdown
# 🎯 Next Recommended Task

## Priority Task: {task_name}
**File**: `.pm/tasks/{task_file}.md`
**Estimated Time**: {hours} hours
**Priority Score**: {score}/100

### Why This Task?
- ✅ All dependencies completed
- 🚀 On critical path - blocks {dependent_count} other tasks
- ⚡ Can be completed in parallel with {parallel_tasks}
- 💡 High business value: {value_description}

### Quick Start
```bash
/pm:task-start {task_file}
```

### Context
{brief_description_of_task}
```

#### Multiple Task Options
```markdown
# 🎯 Recommended Next Tasks

## Top Priority: {task1_name} (Score: {score1})
**Why**: {reasoning1}
**Time**: {hours1}h | **Start**: `/pm:task-start {task1_file}`

## Alternative Options:
### Option 2: {task2_name} (Score: {score2})
**Why**: {reasoning2}
**Time**: {hours2}h | **Start**: `/pm:task-start {task2_file}`

### Option 3: {task3_name} (Score: {score3})
**Why**: {reasoning3}
**Time**: {hours3}h | **Start**: `/pm:task-start {task3_file}`

## Parallel Execution Opportunity
🔄 Tasks {task1_name} and {task4_name} can run simultaneously
**Launch Parallel**: 
```bash
/pm:task-start {task1_file}
/pm:task-start {task4_file}
```
```

### 6. Special Situations

#### No Tasks Available
```markdown
# 🚫 No Tasks Ready for Execution

## Current Blockers:
- {blocked_task1}: Waiting for {dependency1}
- {blocked_task2}: Waiting for {dependency2}

## Recommended Actions:
1. Check dependency status: /pm:status
2. Complete blocking tasks first
3. Consider breaking down large dependencies
4. Review if dependencies are actually required

## Alternative Actions:
- Create new PRD: /pm:prd-new {feature}
- Break down existing epic: /pm:epic-tasks {epic}
- Review and update documentation
```

#### All Tasks In Progress
```markdown
# ⚡ Maximum Parallel Execution Active

## Currently Running:
- {task1}: {hours_remaining}h remaining
- {task2}: {hours_remaining}h remaining

## Recommended Actions:
1. Monitor progress: /pm:status
2. Prepare for next wave of tasks
3. Review upcoming dependencies
4. Plan integration testing

## Next Tasks Ready When Current Complete:
- {next_task1}: Will be unblocked by {current_task}
- {next_task2}: Can start independently
```

### 7. Context-Aware Suggestions

#### Early Project Phase
- Prioritize foundation tasks (database, auth, core APIs)
- Focus on tasks that unblock the most dependent work
- Suggest parallel setup tasks

#### Mid-Project Phase
- Balance new features with technical debt
- Prioritize integration and testing tasks
- Focus on user-visible functionality

#### Late Project Phase
- Prioritize bug fixes and polish tasks
- Focus on performance and security
- Emphasize documentation and deployment tasks

### 8. Smart Notifications

#### Dependency Completion
```markdown
# 🎉 New Tasks Available!

Task {dependency_task} just completed, unblocking:
- {unblocked_task1} (Priority: High)
- {unblocked_task2} (Priority: Medium)

Recommended: Start {unblocked_task1} immediately
```

#### Parallel Opportunity
```markdown
# ⚡ Parallel Execution Opportunity

With {current_task} running, you can also start:
- {compatible_task1} (No conflicts, {hours}h)
- {compatible_task2} (Different files, {hours}h)

This could complete both streams {time_savings}h faster!
```

### 9. Advanced Features

#### Team Coordination
If multiple developers are working:
- Suggest task assignment based on expertise
- Avoid conflicts between team members
- Balance workload across the team

#### Time-Based Prioritization
Consider available time slots:
- Quick tasks (<2h) for small time windows
- Complex tasks (4-8h) for dedicated work sessions
- Background tasks for low-energy periods

### 10. Success Metrics
Track recommendation effectiveness:
- Task completion rate after recommendation
- Time from recommendation to task start
- Accuracy of effort estimates
- User satisfaction with suggestions

The `/pm:next` command transforms task prioritization from guesswork into data-driven decision making, ensuring developers always work on the highest-value tasks while maximizing parallel execution opportunities!
