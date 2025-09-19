---
description: Standalone complexity assessment and mode recommendation for tasks
allowed-tools: Task, Read, Write
---

# Task Complexity Assessment

Analyze task complexity and provide detailed mode recommendations without executing the task.

## Usage
```
/pm:assess <task-name>
```
Example: `/pm:assess user-authentication`

## Instructions

You are providing standalone complexity assessment for the PM Adaptive workflow, allowing users to understand task complexity and mode recommendations before execution.

## MCP Integration (preferred)
Use MCP to resolve tasks and persist assessment results.

- Full name: mcp__project-manager-mcp__list_tasks
- Full name: mcp__project-manager-mcp__get_task_details
- Full name: mcp__project-manager-mcp__update_task
- Full name: mcp__project-manager-mcp__create_task (if the task does not yet exist)

Recommended flow:
1) Lookup task by name via `mcp__project-manager-mcp__list_tasks`; if not found, create using `...__create_task(name, project_name?, epic_name?, ra_mode?, ra_score?)`.
2) Fetch details via `mcp__project-manager-mcp__get_task_details` for context and prior RA metadata.
3) After assessment, persist: `mcp__project-manager-mcp__update_task(ra_score, ra_mode, ra_metadata.assessment, log_entry)`.
4) Do not change status; leave execution to `/pm:task-start`.

### 1. Task Validation
- Prefer MCP: resolve by name using `mcp__project-manager-mcp__list_tasks`; if missing and appropriate, create with `...__create_task`.
- Fallback: check if `.pm/tasks/$ARGUMENTS.md` exists.
- If task definition is incomplete, prompt for missing details.

### 2. Deploy Assessment Agent

Use the Task tool to deploy the adaptive-assessor agent:

```yaml
Task:
  description: "Detailed complexity assessment for $ARGUMENTS"
  subagent_type: "general-purpose"
  prompt: |
    You are the adaptive complexity assessor providing detailed standalone analysis.
    
    ASSESSMENT TASK: Comprehensive complexity analysis and mode recommendation
    
    Task File: .pm/tasks/$ARGUMENTS.md
    
    DETAILED ASSESSMENT PROTOCOL:
    
    1. TASK ANALYSIS
       - Read complete task specification
       - Extract estimated hours, domains, integration points
       - Identify risk factors and unknowns
       - Parse acceptance criteria complexity
    
    2. COMPLEXITY SCORING
       Apply detailed scoring matrix:
       
       Base Scores (choose highest applicable):
       - Simple file change: 1 point
       - Multi-file change: 2 points
       - New feature: 3 points
       - Refactoring: 4 points
       - Architecture change: 5 points
       
       Modifiers (cumulative):
       - External API integration: +2
       - Database schema changes: +3
       - Breaking changes: +3
       - Security-critical: +2
       - Performance-critical: +2
       - Multi-domain (per additional domain): +1
       - Estimated >8 hours: +2
       - Estimated >16 hours: +3
       
       Keyword Analysis:
       - "refactor": +3
       - "integrate" / "integration": +2
       - "migrate" / "migration": +3
       - "architect" / "architecture": +4
       - "optimize" / "performance": +2
       - "authentication" / "security": +2
       - "payment" / "billing": +3
       - "real-time" / "websocket": +2
    
    3. CODEBASE CONTEXT
       - Scan mentioned files and directories
       - Identify affected system boundaries
       - Count integration points
       - Assess existing code complexity
       - Evaluate testing requirements
    
    4. RISK ASSESSMENT
       - Identify assumptions that may be wrong
       - Flag potential integration issues
       - Note areas with high uncertainty
       - Assess impact of potential mistakes
    
    5. MODE RECOMMENDATION
       Based on final score:
       - 1-3: Simple Mode
       - 4-6: Standard Mode
       - 7-8: RA-Light Mode
       - 9-10: RA-Full Mode
    
    DELIVERABLE FORMAT:
    Provide comprehensive assessment using this structure:
    
    # COMPLEXITY ASSESSMENT: $ARGUMENTS
    
    ## Quick Summary
    **Score**: X/10 | **Mode**: [Recommended] | **Confidence**: [High/Medium/Low]
    
    ## Detailed Breakdown
    
    ### Base Complexity Analysis
    **Primary Task Type**: [classification] → X points
    **Rationale**: [why this classification]
    
    ### Complexity Modifiers Applied
    - [Modifier 1]: +X points - [specific reason]
    - [Modifier 2]: +X points - [specific reason]
    [list all applicable modifiers]
    
    ### Keyword Impact
    **Keywords Detected**: [list relevant keywords]
    **Keyword Score**: +X points total
    
    ### Codebase Context
    **Files Likely Affected**: ~X files
    **Domains Involved**: [list domains]
    **Integration Points**: [list external systems/APIs]
    **System Boundaries Crossed**: X boundaries
    
    ### Risk Factors
    **High Risk Areas**:
    - [Risk 1]: [description and impact]
    - [Risk 2]: [description and impact]
    
    **Uncertainty Areas**:
    - [Unknown 1]: [what's unclear]
    - [Unknown 2]: [what's unclear]
    
    ### Final Calculation
    **Base Score**: X
    **Modifiers**: +X
    **Keyword Bonus**: +X
    **Context Adjustment**: +/-X
    **Total Score**: X/10
    
    ## Mode Recommendation: [MODE NAME]
    
    ### Why This Mode?
    [Detailed rationale for mode selection]
    
    ### What This Mode Provides:
    [Description of workflow, rigor level, verification]
    
    ### Expected Workflow:
    [Step-by-step process description]
    
    ### Estimated Timeline:
    - **Assessment**: X minutes
    - **Planning**: X minutes  
    - **Implementation**: X hours
    - **Verification**: X minutes/hours
    - **Total**: X hours
    
    ## Alternative Considerations
    
    ### If Score Were Higher/Lower:
    - **One mode up**: [when to consider escalating]
    - **One mode down**: [when simpler might work]
    
    ### Override Scenarios:
    **Consider Simple Mode if**:
    - [conditions that might reduce complexity]
    
    **Consider RA-Full if**:
    - [conditions that might increase risk]
    
    ## Pre-Implementation Checklist
    
    ### Before Starting:
    - [ ] [Preparation item 1]
    - [ ] [Preparation item 2]
    
    ### Red Flags to Watch:
    - [Warning sign 1]: Escalate to higher mode
    - [Warning sign 2]: Stop and reassess
    
    ## Learning Notes
    **Assessment Confidence**: [High/Medium/Low]
    **Key Uncertainty**: [biggest unknown factor]
    **Track This**: [what to measure for future learning]
    
    ---
    
    Ready to execute with: `/pm:start $ARGUMENTS`
    Override mode with: `/pm:start $ARGUMENTS --mode=[mode]`
```

### 3. Present Assessment Results

When the assessor completes, format and present the results:

```
📊 COMPLEXITY ASSESSMENT COMPLETE: $ARGUMENTS

{paste the full assessment from the agent}

💡 NEXT STEPS:

🚀 Ready to Execute:
   /pm:start $ARGUMENTS

🔧 Mode Override Options:
   /pm:start $ARGUMENTS --mode=simple     # If you want minimal overhead
   /pm:start $ARGUMENTS --mode=standard   # If you want structured approach  
   /pm:start $ARGUMENTS --mode=ra-light   # If you want assumption tracking
   /pm:start $ARGUMENTS --mode=ra-full    # If you want complete orchestration

📈 Assessment Tracking:
   This assessment will be stored for learning and accuracy tracking.
   After task completion, we'll compare predicted vs actual complexity.

❓ Questions About This Assessment:
   • Disagree with the score? The assessment factors are shown above
   • Want a second opinion? Run assessment again or ask for human review
   • Need more detail? Check the risk factors and uncertainty areas
```

### 4. Store Assessment Results

Create `.pm/tasks/$ARGUMENTS-assessment.md`:
```markdown
# Complexity Assessment: $ARGUMENTS

## Assessment Details
- **Date**: {timestamp}
- **Assessor**: adaptive-assessor
- **Score**: {score}/10
- **Recommended Mode**: {mode}
- **Confidence**: {level}

## Full Assessment
{complete_assessment_from_agent}

## Assessment Metadata
- **Base Score**: {base}
- **Modifiers**: {list}
- **Context Factors**: {factors}
- **Risk Level**: {assessment}

## Prediction Tracking
- **Predicted Complexity**: {score}
- **Predicted Duration**: {estimate}
- **Predicted Mode**: {mode}
- **Confidence Level**: {confidence}

## For Future Learning
{assessment_accuracy_will_be_tracked_here}
```

### 5. Update Project Patterns

If `.pm/patterns/assessments.json` exists, append assessment data:
```json
{
  "task_name": "$ARGUMENTS",
  "predicted_score": {score},
  "predicted_mode": "{mode}",
  "confidence": "{level}",
  "assessment_date": "{timestamp}",
  "key_factors": [list],
  "actual_score": null,
  "actual_mode": null,
  "accuracy": null
}
```

### 6. Provide Assessment Insights

Based on assessment results:

#### For Simple Tasks (1-3):
```
✨ SIMPLE TASK DETECTED

This looks straightforward:
• Direct implementation recommended
• Minimal planning overhead
• Basic testing sufficient
• Quick turnaround expected

Perfect for: Small fixes, simple features, single-file changes
```

#### For Standard Tasks (4-6):
```
⚙️ STANDARD COMPLEXITY TASK

This needs structured approach:
• Plan before implementing
• Document key assumptions  
• Comprehensive testing required
• Moderate verification needed

Good for: Multi-file features, integration work, moderate complexity
```

#### For RA-Light Tasks (7-8):
```
🔍 RA-LIGHT COMPLEXITY TASK

This has significant unknowns:
• Assumption tracking required
• Pattern decisions need documentation
• Verification phase essential
• Some uncertainty expected

Best for: Cross-domain work, API integration, refactoring
```

#### For RA-Full Tasks (9-10):
```
🎛️ RA-FULL ORCHESTRATION REQUIRED

This is highly complex:
• Multi-agent coordination needed
• Complete assumption validation
• Systematic verification required
• High risk of issues without proper process

Required for: Architecture changes, complex integrations, mission-critical features
```

### 7. Assessment Comparison

If previous assessments exist, provide comparison:
```
📊 Assessment History for Similar Tasks:
• Last similar task: [name] scored {score} (actual: {actual})
• Pattern accuracy: {percentage}% for this task type
• Typical mode effectiveness: {data}
```

### 8. Expert Override Guidance

Provide guidance on when to override:
```
🧠 When to Override Assessment:

⬆️ Consider Higher Mode If:
• Team is unfamiliar with this domain
• Timeline is tight (less room for error)
• Task is business-critical
• Integration dependencies are unclear

⬇️ Consider Lower Mode If:
• Very similar task done recently
• Excellent test coverage exists
• Clear, detailed specifications
• Low business impact if issues occur
```

The assessment command provides complete transparency into complexity evaluation, helping users make informed decisions about task execution approach.
