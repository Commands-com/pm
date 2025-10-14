---
description: Initialize PM Adaptive Workflow with embedded templates and intelligent mode selection
allowed-tools: Write, Read, Bash, TodoWrite
---

# Initialize PM Adaptive Workflow

Initialize the PM Adaptive Workflow system with intelligent complexity assessment and mode selection.

## Usage
```
/pm:init
```

## Instructions

You are initializing the PM Adaptive Workflow - a intelligent system that automatically scales complexity handling based on task needs.

## MCP Integration (optional)
Optionally seed an MCP project/epic context for tracking initialization work and future tasks.

- Full name: mcp__project-manager-mcp__create_task — Seed a project/epic by creating a setup task
- Full name: mcp__project-manager-mcp__update_task — Append logs and RA metadata
- Full name: mcp__project-manager-mcp__get_instructions — Retrieve methodology text for RA references

Suggested flow:
1) Create a setup task: `mcp__project-manager-mcp__create_task(name="Initialize PM Adaptive Workflow", project_name="{YourProject}", epic_name="Project Setup", ra_mode="standard", ra_score="4")`.
2) Attach initialization outputs (paths created, templates written) to `ra_metadata.init` via `mcp__project-manager-mcp__update_task` with a `log_entry`.
3) Store RA methodology reference snippet from `mcp__project-manager-mcp__get_instructions` (optional) in `ra_metadata.references`.

### 1. Create Project Structure

Create the following directories:
```
.pm/
├── prds/           # Product Requirements Documents
├── epics/          # Technical implementation plans
├── tasks/          # Granular task breakdowns
├── patterns/       # Learned patterns and assessments
└── config.json     # Adaptive configuration
```

### 2. Create Configuration File

Create `.pm/config.json`:
```json
{
  "workflow_mode": "adaptive",
  "auto_assess": true,
  "complexity_thresholds": {
    "simple": 3,
    "standard": 6,
    "ra_light": 8,
    "ra_full": 10
  },
  "mode_overrides": {},
  "learning_enabled": true,
  "parallel_execution": true,
  "github_sync": true,
  "project_started": "{timestamp}",
  "metrics": {
    "tasks_completed": 0,
    "average_complexity": 0,
    "assumption_accuracy": null
  }
}
```

### 3. Embedded Templates

#### PRD Template with Complexity Indicators
Create `.pm/templates/prd-adaptive.md`:
```markdown
# PRD: {name}

## Complexity Assessment Indicators
- **Estimated Hours**: {hours}
- **Domains Affected**: {list_domains}
- **Integration Points**: {external_apis_services}  
- **Data Migration**: {yes/no}
- **Breaking Changes**: {yes/no}
- **Security Considerations**: {list}
- **Performance Requirements**: {specific_metrics}

## Product Vision
{What are we building and why?}

## Target Users
{Who will use this feature?}

## User Stories
### Primary User Story
As a {user_type}, I want to {action} so that {benefit}.

**Acceptance Criteria:**
- [ ] {specific_measurable_criteria}
- [ ] {edge_case_handling}
- [ ] {performance_requirement}

### Edge Cases
- {edge_case_1_description}
- {edge_case_2_description}

## Success Metrics
- {measurable_outcome_1}
- {measurable_outcome_2}

## Technical Considerations
### Complexity Factors
- **Architecture Impact**: {low/medium/high}
- **Database Changes**: {none/schema/migration}
- **API Changes**: {none/backward-compatible/breaking}
- **Third-party Dependencies**: {list}
- **Testing Complexity**: {simple/integration/e2e}

## Dependencies
- {dependency_1}
- {dependency_2}

## Out of Scope
- {what_we_are_not_building}

## Adaptive Mode Recommendation
Based on complexity factors, recommended workflow mode: **{auto-calculated}**
```

#### Epic Template with Mode Awareness
Create `.pm/templates/epic-adaptive.md`:
```markdown
# Epic: {name}

## Workflow Mode
**Assessed Complexity**: {score}/10
**Selected Mode**: {simple/standard/ra-light/ra-full}
**Rationale**: {why_this_mode}

## Overview
{high_level_technical_plan}

## Architecture Decisions
### Approach
{technical_approach}

### Technology Choices
- **Framework/Library**: {choice} - {rationale}
- **Data Storage**: {choice} - {complexity_impact}
- **Integration Method**: {choice} - {risk_assessment}

## Implementation Phases
### Phase 1: {phase_name} (Complexity: {score})
- {deliverable_1}
- {deliverable_2}
- **Mode**: {recommended_mode_for_phase}

### Phase 2: {phase_name} (Complexity: {score})
- {deliverable_1}
- {deliverable_2}
- **Mode**: {recommended_mode_for_phase}

## Task Breakdown Strategy
### Parallel Execution Opportunities
- {tasks_that_can_run_simultaneously}

### Sequential Dependencies
- {tasks_that_must_run_in_order}

## Risk Assessment
### Technical Risks
- **Risk**: {description}
  - **Likelihood**: {low/medium/high}
  - **Impact**: {low/medium/high}
  - **Mitigation**: {strategy}
  - **Triggers RA Mode**: {yes/no}

## Testing Strategy
### Based on Complexity
- **Simple Mode**: Unit tests only
- **Standard Mode**: Unit + integration tests
- **RA-Light Mode**: Unit + integration + assumption validation
- **RA-Full Mode**: Comprehensive + performance + security

## Success Criteria
- [ ] All phases completed
- [ ] Tests passing at appropriate level
- [ ] Assumptions validated (if RA mode)
- [ ] Performance metrics met
```

#### Task Template with Adaptive Markers
Create `.pm/templates/task-adaptive.md`:
```markdown
---
task_number: {number}
task_name: {name}
estimated_hours: {hours}
complexity_score: {auto_calculated}
recommended_mode: {simple/standard/ra-light/ra-full}
status: pending
parallel: {true/false}
conflicts_with: []
depends_on: []
domains_affected: []
integration_points: []
---

# Task {number}: {name}

## Complexity Analysis
**Auto-Assessment Score**: {score}/10
**Factors**:
- Hours estimate: {hours} → +{points}
- Domains affected: {count} → +{points}
- Integration points: {count} → +{points}
- Special factors: {list} → +{points}
**Total**: {score}/10
**Recommended Mode**: {mode}

## What Exactly Gets Built
{specific_deliverables}

## Implementation Approach
### Mode: {mode}
{mode_specific_instructions}

#### If Simple Mode (1-3)
- Direct implementation
- No assumption tracking
- Basic testing

#### If Standard Mode (4-6)
- Implementation with notes
- Document key assumptions
- Comprehensive testing

#### If RA-Light Mode (7-8)
- Use COMPLETION_DRIVE tags for assumptions
- Track pattern decisions
- Require verification pass

#### If RA-Full Mode (9-10)
- Full Response_Awareness orchestration
- Multi-agent coordination
- Complete tag taxonomy
- Systematic verification

## File Changes
### Files to Create
- `{file_path}` ({estimated_lines} lines)
  - {what_this_file_does}
  - Complexity factors: {any_special_considerations}

### Files to Modify
- `{file_path}` (~{estimated_changes} lines)
  - {what_changes}
  - Risk level: {low/medium/high}

## Acceptance Criteria
- [ ] {specific_measurable_criteria}
- [ ] {based_on_mode_requirements}

## Testing Requirements
### Always Required
- [ ] Unit tests for new functions
- [ ] Manual testing checklist completed

### If Standard+ Mode
- [ ] Integration tests
- [ ] Error handling validation

### If RA Mode
- [ ] Assumption validation tests
- [ ] Pattern necessity verification
- [ ] Cross-domain integration tests

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

## Adaptive Tracking
**Initial Complexity**: {score}
**Actual Complexity**: {filled_after_completion}
**Mode Used**: {mode}
**Mode Appropriate**: {yes/no/should_have_been_x}
**Lessons Learned**: {what_to_remember}
```

#### Task Standard Template
Create `.pm/templates/task-standard.md` with the same content as `.pm/templates/task-adaptive.md` above (including the RA Planning section).

### 4. Complexity Scoring Matrix

Embed in configuration understanding:

```markdown
COMPLEXITY_SCORING_RULES = {
  "base_scores": {
    "single_file_change": 1,
    "multi_file_change": 2,
    "new_feature": 3,
    "refactoring": 4,
    "architecture_change": 5
  },
  "modifiers": {
    "external_api": +2,
    "database_change": +3,
    "breaking_change": +3,
    "security_critical": +2,
    "performance_critical": +2,
    "multi_domain": +1 per domain beyond first,
    "over_8_hours": +2
  },
  "keywords": {
    "refactor": +3,
    "integrate": +2,
    "migrate": +3,
    "architect": +4,
    "optimize": +2
  }
}
```

### 5. Mode Selection Logic

Embed this decision tree:

```markdown
MODE_SELECTION = {
  "simple": {
    "score_range": [1, 3],
    "characteristics": [
      "Single file or component",
      "No external dependencies",
      "Well-defined requirements",
      "< 4 hours work"
    ],
    "workflow": "Direct implementation → Basic testing → Done"
  },
  "standard": {
    "score_range": [4, 6],
    "characteristics": [
      "Multiple files",
      "Some integration",
      "4-8 hours work",
      "Clear requirements"
    ],
    "workflow": "Plan → Implement → Test → Verify → Done"
  },
  "ra_light": {
    "score_range": [7, 8],
    "characteristics": [
      "Cross-domain",
      "External APIs",
      "Some unknowns",
      "8-16 hours work"
    ],
    "workflow": "Assess → Plan → Implement with tags → Verify assumptions → Done"
  },
  "ra_full": {
    "score_range": [9, 10],
    "characteristics": [
      "Major refactoring",
      "Multiple systems",
      "High risk",
      "> 16 hours work"
    ],
    "workflow": "Survey → Multi-agent planning → Synthesis → Implementation → Verification → Done"
  }
}
```

### 6. Create Patterns Directory

Create `.pm/patterns/` with initial learning structure:
```
patterns/
├── successful_assessments.json    # Track prediction accuracy
├── common_patterns.json           # Repeated task types
└── mode_effectiveness.json        # Which modes work best
```

Initialize with:
```json
{
  "successful_assessments": [],
  "assessment_accuracy": {
    "total": 0,
    "accurate": 0,
    "overestimated": 0,
    "underestimated": 0
  }
}
```

### 7. Create README

Create `.pm/README.md`:
```markdown
# PM Adaptive Workflow

This project uses the PM Adaptive Workflow - an intelligent task management system that automatically adjusts complexity handling based on task requirements.

## Quick Start
- `/pm:start <task>` - Intelligent task execution with auto-assessment
- `/pm:assess <task>` - Preview complexity assessment
- `/pm:status` - View all tasks with complexity scores

## Workflow Modes
- **Simple (1-3)**: Direct implementation
- **Standard (4-6)**: Structured with verification
- **RA-Light (7-8)**: Assumption tracking
- **RA-Full (9-10)**: Complete orchestration

## Current Configuration
Mode: {workflow_mode}
Auto-assess: {auto_assess}
Learning: {learning_enabled}

Generated: {timestamp}
```

### 8. Success Confirmation

```
✅ PM Adaptive Workflow initialized successfully!

📁 Created structure:
  .pm/
  ├── prds/
  ├── epics/
  ├── tasks/
  ├── patterns/
  ├── templates/
  │   ├── prd-adaptive.md
  │   ├── epic-adaptive.md
  │   ├── task-adaptive.md
  │   └── task-standard.md
  ├── config.json
  └── README.md

🎯 Adaptive Features Enabled:
  ✓ Automatic complexity assessment
  ✓ Intelligent mode selection
  ✓ Pattern learning system
  ✓ Progressive enhancement
  ✓ Multi-mode templates

🚀 Next Steps:
  1. Create a PRD: /pm:prd-new <feature>
  2. Start a task: /pm:start <task>
  3. Check assessment: /pm:assess <task>
  
💡 The system will automatically:
  - Assess task complexity
  - Select appropriate workflow
  - Scale verification as needed
  - Learn from patterns over time

Type /pm:help for comprehensive guide.
```

The PM Adaptive Workflow is ready - it intelligently scales from simple to complex tasks automatically!
