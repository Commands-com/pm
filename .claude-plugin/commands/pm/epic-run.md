---
description: Execute entire epic with maximum parallelization using MCP orchestration
allowed-tools: Task, TodoWrite, Read, Write, mcp__project-manager-mcp__list_tasks, mcp__project-manager-mcp__get_task_details, mcp__project-manager-mcp__acquire_task_lock, mcp__project-manager-mcp__update_task_status, mcp__project-manager-mcp__update_task, mcp__project-manager-mcp__release_task_lock, mcp__project-manager-mcp__list_epics
---

# Epic Execution with Maximum Parallelization

Execute an entire epic with intelligent dependency resolution and maximum parallel task execution using MCP orchestration.

## Usage
```
/pm:epic-run <epic-name>
```
Example: `/pm:epic-run knowledge-management-system`

## Instructions

You are launching the PM Epic Orchestrator - an intelligent system that executes entire epics with maximum parallelization while respecting task dependencies.

## MCP Integration (Required)

Primary MCP tools for epic orchestration:

- `mcp__project-manager-mcp__list_epics` - Find epic by name
- `mcp__project-manager-mcp__list_tasks` - Get all tasks in epic
- `mcp__project-manager-mcp__get_task_details` - Analyze dependencies and parallel groups
- `mcp__project-manager-mcp__acquire_task_lock` - Atomic task locking
- `mcp__project-manager-mcp__update_task_status` - Status management
- `mcp__project-manager-mcp__update_task` - Progress logging and metadata updates
- `mcp__project-manager-mcp__release_task_lock` - Lock management

## Epic Orchestration Protocol

### 1. Epic Discovery and Validation

```yaml
Step 1: Resolve epic by name
- Use mcp__project-manager-mcp__list_epics to find epic
- If not found, suggest similar epic names
- Validate epic contains tasks ready for execution

Step 2: Task inventory
- Use mcp__project-manager-mcp__list_tasks(epic_id=...) to get all tasks
- Filter out completed tasks
- Identify blocked or in-progress tasks
- Build complete task dependency graph
```

### 2. Dependency Analysis and Parallelization Planning

```yaml
Dependency Graph Construction:
- For each task: mcp__project-manager-mcp__get_task_details(task_id)
- Extract dependencies from ra_metadata.dependencies or dependencies field
- Build directed acyclic graph (DAG) of task dependencies
- Identify parallel groups from parallel_group field
- Detect conflicts from conflicts_with field

Parallelization Strategy:
- Group tasks by dependency level (0=no deps, 1=depends on level 0, etc.)
- Within each level, identify parallel-safe task groups
- Respect parallel_group constraints (tasks in same group can run together)
- Honor conflicts_with restrictions (conflicting tasks cannot run simultaneously)
- Calculate maximum parallel execution streams
```

### 3. Complexity Assessment for Epic

```yaml
Epic-Level Assessment:
- Sum individual task complexity scores
- Factor in inter-task dependencies
- Account for integration complexity
- Assess parallel execution overhead
- Determine overall epic complexity (1-10 scale)

Mode Selection:
- Simple (1-3): Sequential execution, minimal coordination
- Standard (4-6): Moderate parallelization, standard monitoring  
- RA-Light (7-8): Full parallelization with assumption tracking
- RA-Full (9-10): Advanced orchestration with verification phases
```

### 4. Direct Parallel Execution by Main Agent

The main agent (you) orchestrates maximum parallelization directly:

```yaml
Main Agent Orchestration Protocol:

Phase 1: Dependency Resolution
- Build complete task dependency graph using MCP tools
- Identify execution levels (0, 1, 2, ...) 
- Map parallel groups and conflict constraints
- Calculate optimal execution order

Phase 2: Stream Allocation  
- Assign tasks to parallel execution streams
- Balance workload across available streams
- Respect dependency and conflict constraints
- Queue tasks by execution level

Phase 3: Direct Parallel Task Execution
For each execution level:
- Launch task-runner-adaptive agents directly for each parallel stream
- Use single message with multiple Task tool calls for maximum parallelism
- CRITICAL: Instruct each subagent to use MCP for task status updates
- Monitor task completion and dependency satisfaction
- Advance to next level when current level completes
- Handle failures with graceful degradation

Phase 4: Progress Coordination
- Track progress across all parallel streams using MCP tools
- Log epic-level milestones
- Handle inter-task communication
- Coordinate shared resource access

Phase 5: Completion Synthesis
- Verify all tasks completed successfully using MCP
- Run epic-level integration tests if defined
- Generate completion report with metrics

Direct Parallel Launch Pattern:
- Use single response with multiple Task tool calls
- Launch all parallel streams simultaneously
- Each task-runner gets specific stream configuration
- Monitor completion through MCP status updates

MCP INTEGRATION (MANDATORY):
- Use mcp__project-manager-mcp__acquire_task_lock for atomic task claiming
- Update progress: mcp__project-manager-mcp__update_task(log_entry=...)
- Status transitions: mcp__project-manager-mcp__update_task_status
- Coordinate through task metadata and parallel_group fields
- CRITICAL: Every subagent MUST use MCP tools to update task status - never use TodoWrite
```

### 5. Stream-Specific Task Execution

For each parallel stream, deploy adaptive task runners:

```yaml
Stream Execution Agent:
  description: "Execute task stream {stream_id} for epic $ARGUMENTS"
  subagent_type: "task-runner-adaptive"
  prompt: |
    You are executing PARALLEL STREAM {stream_id} for epic $ARGUMENTS.
    
    STREAM CONFIGURATION:
    - Stream ID: {stream_id}
    - Assigned Tasks: {task_list}
    - Execution Mode: {mode_per_task}
    - Dependencies: {stream_dependencies}
    
    EXECUTION PROTOCOL:
    1. Process tasks in dependency order within stream
    2. Acquire locks atomically before starting each task using mcp__project-manager-mcp__acquire_task_lock
    3. UPDATE TASK STATUS TO IN_PROGRESS using mcp__project-manager-mcp__update_task_status immediately after acquiring lock
    4. Execute with appropriate complexity mode
    5. Log progress using mcp__project-manager-mcp__update_task(log_entry=...) and coordinate with other streams
    6. UPDATE TASK STATUS TO DONE using mcp__project-manager-mcp__update_task_status when task completes
    7. Handle failures with stream-level recovery
    
    COORDINATION:
    - Respect inter-stream dependencies
    - Communicate completion status using MCP tools only
    - Share resources safely
    - Maintain epic-level consistency
    - NEVER use TodoWrite or other task management tools - only MCP project-manager tools
    
    TASK QUEUE: {stream_task_queue}
    
    Execute efficiently while maintaining quality standards.
```

### 6. Real-Time Progress Monitoring

Create epic-level progress tracking:

```markdown
# Epic Execution Progress: $ARGUMENTS

## Epic Overview
- **Epic Name**: {epic_name}
- **Total Tasks**: {total_count}
- **Parallel Streams**: {stream_count}
- **Execution Mode**: {epic_mode}
- **Started**: {timestamp}

## Dependency Graph
{visual_dependency_representation}

## Parallel Stream Status
### Stream 1: {stream_1_name}
- **Tasks**: {stream_1_tasks}
- **Status**: {stream_1_status}
- **Progress**: {stream_1_progress}

### Stream 2: {stream_2_name}  
- **Tasks**: {stream_2_tasks}
- **Status**: {stream_2_status}
- **Progress**: {stream_2_progress}

{additional_streams}

## Execution Levels
### Level 0 (No Dependencies)
- ✅ Task A (completed)
- 🔄 Task B (in progress)
- ⏳ Task C (queued)

### Level 1 (Depends on Level 0)
- ⏳ Task D (waiting)
- ⏳ Task E (waiting)

{additional_levels}

## Performance Metrics
- **Parallelization Efficiency**: {parallel_efficiency}%
- **Dependency Wait Time**: {wait_time}
- **Average Task Duration**: {avg_duration}
- **Critical Path Length**: {critical_path}

## Epic-Level Logs
{real_time_epic_logs}

## Integration Status
{inter_task_integration_status}

## Completion Forecast
- **Estimated Completion**: {eta}
- **Critical Path Tasks**: {critical_tasks}
- **Risk Factors**: {risk_assessment}
```

### 7. Advanced Parallel Features

#### Dynamic Load Balancing
```yaml
Load Balancing Protocol:
- Monitor stream performance in real-time
- Redistribute queued tasks from slower streams
- Account for varying task complexity
- Maintain dependency constraints during redistribution
```

#### Failure Recovery
```yaml
Stream Failure Recovery:
- Isolate failed tasks without blocking other streams
- Redistribute dependent tasks to available streams
- Maintain epic-level progress despite failures
- Log failure analysis for future optimization
```

#### Resource Contention Management
```yaml
Shared Resource Coordination:
- Identify tasks that modify shared files/systems
- Serialize access to contended resources
- Queue resource-dependent tasks appropriately
- Prevent race conditions and conflicts
```

### 8. Epic Completion and Integration

```yaml
Epic Integration Protocol:
1. Verify all tasks completed successfully
2. Run epic-level integration tests
3. Validate inter-task dependencies and interfaces
4. Generate epic completion report with metrics
5. Update epic status and archive execution logs

Integration Validation:
- Cross-task interface compatibility
- Epic-level acceptance criteria verification
- Performance and quality metrics aggregation
- Documentation and deployment readiness
```

### 9. Execution Summary Report

```
🚀 Epic Parallel Execution Complete: $ARGUMENTS

📊 Performance Metrics:
  🎯 Tasks Completed: {completed}/{total}
  ⚡ Parallelization Efficiency: {efficiency}%
  ⏱️ Total Execution Time: {duration}
  🔀 Parallel Streams Used: {streams}
  🛤️ Critical Path Duration: {critical_path}

📈 Efficiency Analysis:
  • Sequential Estimate: {sequential_time}
  • Parallel Actual: {parallel_time}  
  • Time Saved: {time_saved} ({percentage}%)
  • Bottlenecks Identified: {bottlenecks}

🔗 Dependency Management:
  • Dependencies Resolved: {dep_resolved}
  • Dependency Wait Time: {dep_wait}
  • Parallel Groups Utilized: {parallel_groups}
  • Conflicts Avoided: {conflicts}

✅ Quality Metrics:
  • Integration Tests: {integration_status}
  • Code Quality Checks: {quality_status}
  • Epic Acceptance Criteria: {acceptance_status}

🧠 Learning Insights:
  • Parallelization Patterns: {patterns_learned}
  • Optimization Opportunities: {optimizations}
  • Future Epic Recommendations: {recommendations}
```

### 10. Advanced Epic Features

#### Epic Modes Override
```
/pm:epic-run <epic-name> --mode=<simple|standard|ra-light|ra-full>
```

#### Stream Count Control
```
/pm:epic-run <epic-name> --streams=<number>
```

#### Dependency Debugging
```
/pm:epic-deps <epic-name>  # Visualize dependency graph
```

#### Epic Progress Monitoring
```
/pm:epic-status <epic-name>  # Real-time progress dashboard
```

The Epic Orchestrator maximizes development velocity through intelligent parallelization while maintaining code quality and dependency safety!