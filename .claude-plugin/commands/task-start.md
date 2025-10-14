---
description: Intelligent task execution with automatic complexity assessment and adaptive workflow selection
allowed-tools: Task, TodoWrite, Read, Write, Bash
---

# Adaptive Task Start

Intelligent task execution with automatic complexity assessment and adaptive workflow selection.

## Usage
```
/pm:task-start <task-name>
```
Example: `/pm:start user-authentication`

## Instructions

You are launching the PM Adaptive workflow - an intelligent system that automatically assesses task complexity and selects the optimal execution mode.

## MCP Integration (preferred)
Use MCP for task lookup, locking, status changes, and progress logging.

- Full name: mcp__project-manager-mcp__list_tasks
- Full name: mcp__project-manager-mcp__get_task_details
- Full name: mcp__project-manager-mcp__acquire_task_lock
- Full name: mcp__project-manager-mcp__update_task_status
- Full name: mcp__project-manager-mcp__update_task
- Full name: mcp__project-manager-mcp__release_task_lock
- Full name: mcp__project-manager-mcp__create_task (if creating tasks on the fly)

MCP flow:
1) Resolve the task by name: `mcp__project-manager-mcp__list_tasks` with a filter, then `...__get_task_details`.
2) Validate dependencies from `get_task_details` (use `ra_metadata`/`dependencies` fields if present).
3) Acquire a lock: `mcp__project-manager-mcp__acquire_task_lock(task_id, agent_id)`.
4) Mark IN_PROGRESS: `mcp__project-manager-mcp__update_task_status(task_id, IN_PROGRESS, agent_id)`.
5) Persist assessment results and selected mode: `mcp__project-manager-mcp__update_task(ra_score, ra_mode, log_entry, ra_metadata)`.
6) Log execution milestones via repeated `...__update_task(log_entry=...)` calls.
7) On completion, move to REVIEW or DONE using `...__update_task_status` and release the lock with `...__release_task_lock`.

### 1. Task Validation
- Prefer MCP: lookup task by name using `mcp__project-manager-mcp__list_tasks` and confirm via `...__get_task_details`.
- Fallback: check `.pm/tasks/$ARGUMENTS.md` exists.
- If task is already completed, prompt for override.

### 2. Dependency Check
Verify dependencies:
- Prefer MCP: read `dependencies` or `ra_metadata.depends_on` via `...__get_task_details` and ensure each dependent task is completed.
- Fallback: parse `.pm/tasks/$ARGUMENTS.md` frontmatter.
- If unmet: block start and list missing dependencies.

### 3. Deploy Adaptive Assessor
Use the Task tool to deploy the adaptive-assessor agent:

```yaml
Task:
  description: "Assess complexity and recommend mode for $ARGUMENTS"
  subagent_type: "general-purpose"
  prompt: |
    You are the adaptive complexity assessor for the PM Adaptive workflow.
    
    ASSESSMENT TASK: Analyze complexity and recommend workflow mode
    
    Task File: .pm/tasks/$ARGUMENTS.md
    
    ASSESSMENT METHODOLOGY:
    
    1. Read the task file completely
    2. Apply complexity scoring rules:
       - Base score for task type (1-5)
       - Modifiers for external APIs (+2)
       - Modifiers for database changes (+3)
       - Modifiers for breaking changes (+3)
       - Modifiers for multi-domain impact (+1 per domain)
       - Modifiers for >8 hour estimate (+2)
       - Keyword analysis (refactor +3, integrate +2, etc.)
    
    3. Analyze codebase context:
       - Scan affected files and directories
       - Count integration points
       - Assess risk factors
       - Identify uncertainty areas
    
    4. Calculate final complexity score (1-10)
    
    5. Recommend mode:
       - Simple (1-3): Direct implementation
       - Standard (4-6): Structured with verification  
       - RA-Light (7-8): Assumption tracking
       - RA-Full (9-10): Complete orchestration
    
    DELIVERABLE: Structured assessment with:
    - Complexity breakdown and rationale
    - Final score and mode recommendation
    - Confidence level and assumptions made
    - Potential escalation triggers
    
    Use the assessment format from your agent instructions.
```

### 4. Process Assessment Results
When assessor completes:
- Extract complexity score and recommended mode
- Persist via MCP using `mcp__project-manager-mcp__update_task(ra_score, ra_mode, ra_metadata.assessment, log_entry)`
- Display assessment summary to user

### 5. Mode-Based Task Execution

#### Simple Mode (Score 1-3)
Deploy task-runner-adaptive directly:
```yaml  
Task:
  description: "Execute simple task: $ARGUMENTS"
  subagent_type: "general-purpose"
  prompt: |
    You are executing a SIMPLE MODE task with the adaptive task runner.
    
    CONFIGURATION:
    - Mode: Simple
    - Complexity Score: {score}
    - Expected Duration: < 4 hours
    - Rigor Level: Minimal overhead
    
    EXECUTION APPROACH:
    - Read task requirements and implement directly
    - No assumption tracking or RA tags needed
    - Focus on speed and clean implementation
    - Basic error handling and testing
    - Standard project conventions
    
    Task File: .pm/tasks/$ARGUMENTS.md
    
    Follow the Simple Mode protocol from your agent instructions.
    
    DELIVERABLE: Clean, working implementation with progress report

MCP calls during execution:
- Append progress: `mcp__project-manager-mcp__update_task(log_entry=...)`
- Update status on finish: `mcp__project-manager-mcp__update_task_status(..., REVIEW|DONE, agent_id)`
```

#### Standard Mode (Score 4-6)  
Deploy task-runner-adaptive with standard configuration:
```yaml
Task:
  description: "Execute standard task: $ARGUMENTS"  
  subagent_type: "general-purpose"
  prompt: |
    You are executing a STANDARD MODE task with the adaptive task runner.
    
    CONFIGURATION:
    - Mode: Standard
    - Complexity Score: {score}
    - Expected Duration: 4-8 hours
    - Rigor Level: Structured with verification
    
    EXECUTION APPROACH:
    - Plan implementation approach
    - Document key assumptions in comments
    - Implement with comprehensive error handling
    - Full testing (unit + integration)
    - Self-verify against acceptance criteria
    
    Task File: .pm/tasks/$ARGUMENTS.md
    
    Follow the Standard Mode protocol from your agent instructions.
    
    DELIVERABLE: Well-structured implementation with documented assumptions
```

#### RA-Light Mode (Score 7-8)
Deploy task-runner-adaptive with RA configuration:
```yaml
Task:
  description: "Execute RA-Light task: $ARGUMENTS"
  subagent_type: "general-purpose"  
  prompt: |
    You are executing an RA-LIGHT MODE task with the adaptive task runner.
    
    CONFIGURATION:
    - Mode: RA-Light
    - Complexity Score: {score}
    - Expected Duration: 8-16 hours
    - Rigor Level: Assumption tracking required
    
    EXECUTION APPROACH:
    - Brief planning with uncertainty identification
    - Use Response Awareness tags throughout implementation:
      * #COMPLETION_DRIVE_IMPL for implementation assumptions
      * #COMPLETION_DRIVE_INTEGRATION for integration assumptions
      * #SUGGEST_* tags for user decision items
    - Comprehensive error handling and testing
    - Flag for verification upon completion
    
    Task File: .pm/tasks/$ARGUMENTS.md
    
    Follow the RA-Light Mode protocol from your agent instructions.
    
    DELIVERABLE: Tagged implementation ready for assumption verification
```

#### RA-Full Mode (Score 9-10)
Deploy complete RA orchestration:
```yaml
Task:
  description: "Execute RA-Full orchestration: $ARGUMENTS"
  subagent_type: "general-purpose"
  prompt: |
    You are orchestrating a FULL RA MODE task - the most complex workflow.
    
    CONFIGURATION:
    - Mode: RA-Full  
    - Complexity Score: {score}
    - Expected Duration: > 16 hours
    - Rigor Level: Complete Response Awareness protocol
    
    ORCHESTRATION PROTOCOL:
    This requires the complete 5-phase RA workflow:
    
    Phase 0: Deploy survey agent for codebase analysis
    Phase 1: Deploy domain-specific planning agents in parallel
    Phase 2: Deploy synthesis agent for plan integration
    Phase 3: Deploy implementation agents with full RA tagging
    Phase 4: Deploy verification agents for assumption validation
    Phase 5: Synthesize final report
    
    Task File: .pm/tasks/$ARGUMENTS.md
    
    DO NOT implement directly. Coordinate the multi-agent workflow.
    Follow the RA-Full orchestration protocol.
    
    DELIVERABLE: Complete orchestration with validated implementation
```

### 6. Create Progress Tracking

Create `.pm/tasks/$ARGUMENTS-progress.md`:
```markdown
# Adaptive Progress: $ARGUMENTS

## Assessment Results
- **Complexity Score**: {score}/10
- **Mode Selected**: {mode}
- **Confidence**: {confidence_level}
- **Assessment Time**: {timestamp}

## Mode Configuration
- **Expected Duration**: {time_estimate}
- **Rigor Level**: {description}
- **Verification Required**: {yes/no}
- **RA Tags Expected**: {yes/no}

## Execution Log
{Agent will update with detailed progress}

## Adaptive Learning
- **Predicted Complexity**: {initial_score}
- **Actual Complexity**: {to_be_filled_during_execution}
- **Mode Effectiveness**: {to_be_assessed}
- **Lessons Learned**: {patterns_for_future}

## Files Modified
{Agent will track all changes}

## Quality Metrics
{Mode-appropriate quality measures}

## Completion Status
{Agent will update when finished}
```

### 7. Update Task Status

Update task frontmatter:
```yaml
---
status: in_progress
complexity_assessed: {score}
mode_selected: {mode}
assessment_confidence: {level}
started: {timestamp}
agent_deployed: adaptive-task-runner
progress_file: .pm/tasks/$ARGUMENTS-progress.md
---
```

### 8. Monitor and Report

Provide execution summary:
```
🚀 Adaptive Task Execution Started: $ARGUMENTS

📊 Assessment Results:
  🎯 Complexity Score: {score}/10
  ⚙️ Mode Selected: {mode}
  ⏱️ Estimated Duration: {time}
  🔍 Verification Required: {yes/no}

📁 Tracking Files:
  • .pm/tasks/$ARGUMENTS.md (task status)
  • .pm/tasks/$ARGUMENTS-progress.md (detailed progress)

🎛️ Mode Configuration:
  {mode_specific_description}

💡 What's Happening:
  • Complexity automatically assessed
  • Optimal workflow mode selected  
  • Agent deployed with appropriate rigor level
  • Progress tracking enabled
  
⏭️ Next Steps:
  • Monitor progress file for updates
  • {mode_specific_next_steps}
  
🧠 Adaptive Learning:
  • Assessment accuracy will be tracked
  • Mode effectiveness will be measured
  • Patterns will be learned for future tasks
```

### 9. Auto-Verification Triggering

For RA-Light and RA-Full modes:
- Monitor task completion
- When implementation finishes, automatically suggest verification:
  ```
  ✅ Implementation Complete - Verification Required
  
  🔍 RA Tags Created: {count} tags requiring resolution
  
  Next Command: /pm:verify $ARGUMENTS
  
  The verification will:
  • Validate all tagged assumptions
  • Resolve pattern-driven code
  • Compile user suggestions
  • Ensure production readiness
  ```

### 10. Learning Integration

After task completion:
- Compare predicted vs actual complexity
- Assess mode effectiveness
- Update complexity assessment patterns
- Store lessons learned in `.pm/patterns/`

### 11. Error Recovery

If any step fails:
- Provide clear error message
- Suggest manual override options
- Offer fallback approaches
- Update assessment accuracy

## Advanced Features

### Mode Override
Allow manual mode selection:
```
/pm:start <task> --mode=<simple|standard|ra-light|ra-full>
```

### Parallel Execution
For tasks marked `parallel: true`, provide guidance on compatible parallel tasks.

### Complexity Debugging
If assessment seems wrong:
```
/pm:assess <task>  # Get detailed complexity breakdown
```

The Adaptive Task Start system ensures every task gets exactly the right level of rigor - no more, no less!
