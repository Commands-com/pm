---
description: Comprehensive guide to the PM Adaptive Workflow commands and intelligent complexity management
allowed-tools: Read
---

# PM Adaptive Workflow Help

Comprehensive guide to the PM Adaptive Workflow - an intelligent task management system that automatically adjusts complexity handling based on task requirements.

## Usage
```
/pm:help [command]
```

## PM Adaptive Workflow Overview

The PM Adaptive Workflow transforms software development from one-size-fits-all to intelligent complexity scaling:

**PRD → Epic → Tasks → Adaptive Execution → Quality-Matched Verification → Shipping**

### Core Philosophy
1. **Intelligent Scaling**: Automatically match workflow rigor to task complexity
2. **No Wasted Effort**: Simple tasks get simple treatment, complex tasks get thorough handling
3. **Assumption Awareness**: Track and validate uncertainties in complex work
4. **Learning System**: Get smarter over time through pattern recognition
5. **Quality Assurance**: Appropriate verification for each complexity level

## Adaptive Modes

The system automatically selects from four workflow modes:

### Simple Mode (Complexity 1-3)
**For**: Bug fixes, simple UI changes, single-file modifications
**Process**: Direct implementation → Basic testing → Done
**Duration**: < 4 hours
**Overhead**: Minimal

### Standard Mode (Complexity 4-6)  
**For**: Multi-file features, basic integrations, moderate complexity
**Process**: Plan → Implement → Test → Verify → Done
**Duration**: 4-8 hours  
**Overhead**: Structured approach

### RA-Light Mode (Complexity 7-8)
**For**: Cross-domain work, API integrations, significant refactoring
**Process**: Assess → Plan → Tagged Implementation → Assumption Verification → Done
**Duration**: 8-16 hours
**Overhead**: Response Awareness tags and verification

### RA-Full Mode (Complexity 9-10)
**For**: Architecture changes, complex integrations, mission-critical features
**Process**: Survey → Multi-agent Planning → Synthesis → Orchestrated Implementation → Full Verification → Done
**Duration**: > 16 hours
**Overhead**: Complete Response Awareness orchestration

## Command Reference

### 🚀 Getting Started
- **`/pm:init`** - Initialize adaptive workflow with intelligent templates
- **`/pm:help`** - Show this help (or `/pm:help <command>` for details)

### 📋 Planning Phase
- **`/pm:prd-new <name>`** - Create PRD with complexity indicators
- **`/pm:prd-to-epic <name>`** - Convert PRD to technical plan with mode awareness
- **`/pm:epic-tasks <name>`** - Break epic into adaptive tasks

### 🎯 Intelligence Layer (NEW)
- **`/pm:assess <task>`** - Standalone complexity assessment and mode recommendation
- **`/pm:start <task>`** - Intelligent task execution with auto-assessment and adaptive workflow
- **`/pm:plan-review <epic>`** - Lightweight RA planning readiness review for tasks

### 🔍 Verification
- **`/pm:verify <task>`** - Adaptive verification scaled to complexity level

### ⚡ Traditional Execution  
- **`/pm:task-sync <task>`** - Sync progress to GitHub issues
- **`/pm:next`** - Get intelligent next task recommendation

### 📊 Monitoring
- **`/pm:status`** - Comprehensive dashboard with complexity metrics

## MCP Functions Reference
These MCP functions back the PM commands. Use the full names when invoking:

- Full name: mcp__project-manager-mcp__list_projects — List projects
- Full name: mcp__project-manager-mcp__list_epics — List epics (optionally by project)
- Full name: mcp__project-manager-mcp__list_tasks — List tasks (filter by project/epic/status)
- Full name: mcp__project-manager-mcp__get_available_tasks — Next available tasks and metadata
- Full name: mcp__project-manager-mcp__get_task_details — Full details and logs for a task
- Full name: mcp__project-manager-mcp__acquire_task_lock — Atomically lock a task and set IN_PROGRESS
- Full name: mcp__project-manager-mcp__update_task_status — Update task status (TODO/IN_PROGRESS/REVIEW/DONE)
- Full name: mcp__project-manager-mcp__update_task — Update name/description/RA fields and append logs
- Full name: mcp__project-manager-mcp__create_task — Create a task (with epic/project upsert)
- Full name: mcp__project-manager-mcp__release_task_lock — Explicitly release a lock you own

## Typical Adaptive Workflow

### 1. Project Setup
```bash
/pm:init                    # Set up adaptive structure
```

### 2. Requirements & Planning
```bash
/pm:prd-new user-auth       # Create PRD with complexity factors
/pm:prd-to-epic user-auth   # Convert to technical plan with mode awareness
/pm:epic-tasks user-auth    # Create adaptive tasks
```

### 3. Intelligent Execution (NEW)
```bash
/pm:assess login-endpoint   # Preview complexity assessment
/pm:start login-endpoint    # Auto-assess and execute with appropriate mode
/pm:plan-review user-auth   # Check tasks include RA Planning blocks before coding
```

MCP usage during execution:
- Lookup tasks: `mcp__project-manager-mcp__list_tasks`, details: `...__get_task_details`
- Start work: `...__acquire_task_lock`, `...__update_task_status(IN_PROGRESS)`
- Log progress: `...__update_task(log_entry=...)`, update RA fields: `ra_mode`, `ra_score`, `ra_metadata`
- Complete: `...__update_task_status(REVIEW|DONE)`, `...__release_task_lock`

### 4. Verification & Shipping
```bash
/pm:verify login-endpoint   # Adaptive verification based on mode used
/pm:task-sync login-endpoint # Update GitHub with results
```

### 5. Continuous Monitoring
```bash
/pm:status                  # View all tasks with complexity scores
/pm:next                    # Get intelligent next recommendation
```

## Complexity Assessment

### Automatic Assessment
The system evaluates:
- **Task type**: Bug fix (1) → Architecture change (5)
- **Integration points**: APIs, databases, external services (+2-3 each)
- **Risk factors**: Security, payments, breaking changes (+2-3 each)
- **Scope**: Files affected, domains crossed, hours estimated
- **Keywords**: "refactor", "integrate", "migrate" trigger increases

### Assessment Example
```
Task: "Refactor authentication to support OAuth"
- Base: Refactoring (4 points)
- Keyword: "refactor" (+3 points) 
- Security: Authentication (+2 points)
- External: OAuth integration (+2 points)
Total: 11 → RA-Full Mode (capped at 10)
```

## Mode Selection Intelligence

### Automatic Selection
```yaml
Score 1-3: Simple Mode
  - Single files, clear requirements
  - No assumptions, minimal risk
  - Direct implementation

Score 4-6: Standard Mode  
  - Multi-file changes, some complexity
  - Document key assumptions
  - Structured verification

Score 7-8: RA-Light Mode
  - Cross-domain, external dependencies
  - Track assumptions with RA tags
  - Assumption verification required

Score 9-10: RA-Full Mode
  - Major changes, high uncertainty
  - Multi-agent orchestration
  - Complete Response Awareness protocol
```

### Manual Override
```bash
/pm:start <task> --mode=simple      # Force simpler approach
/pm:start <task> --mode=ra-full     # Force maximum rigor
```

## Response Awareness (RA) Features

For complex tasks (RA-Light and RA-Full modes), the system uses metacognitive awareness:

### RA Tags (Automatic)
```yaml
Assumption Tags:
  #COMPLETION_DRIVE_IMPL: Implementation assumptions
  #COMPLETION_DRIVE_INTEGRATION: Integration assumptions
  
Pattern Tags:
  #CARGO_CULT: Pattern-driven code without requirements
  #PATTERN_MOMENTUM: Over-implementation from habits
  
Suggestion Tags:
  #SUGGEST_ERROR_HANDLING: Error handling recommendations
  #SUGGEST_VALIDATION: Input validation suggestions
```

### Verification Process
1. **Tag Resolution**: Validate all tagged assumptions
2. **Pattern Evaluation**: Keep necessary code, remove cargo-cult patterns
3. **Suggestion Compilation**: Present user decisions for enhancements
4. **Quality Assurance**: Ensure production readiness

## File Structure (Enhanced)

After initialization:
```
.pm/
├── prds/                  # Product Requirements with complexity markers
├── epics/                 # Technical plans with mode recommendations  
├── tasks/                 # Adaptive tasks with auto-assessment
│   ├── 001-feature.md     # Task with complexity score
│   └── 001-progress.md    # Progress with mode tracking
├── patterns/              # Learning system data
│   ├── assessments.json   # Complexity prediction accuracy
│   └── mode_effectiveness.json # Which modes work best
├── templates/             # Adaptive templates (embedded in /pm:init)
└── config.json           # Adaptive configuration
```

## Learning System

### Pattern Recognition
- **Assessment Accuracy**: Track predicted vs actual complexity
- **Mode Effectiveness**: Monitor which modes work best for task types
- **Common Patterns**: Learn project-specific complexity indicators
- **Team Velocity**: Adjust estimates based on team performance

### Continuous Improvement
- Assessment thresholds adjust based on accuracy
- Mode recommendations improve with experience
- Project-specific patterns emerge over time
- Template optimization based on successful patterns

## Advanced Features

### Intelligent Recommendations
```bash
# System learns your patterns
/pm:next
# "Based on your recent authentication work, 
#  recommend 003-oauth-integration (RA-Light mode, 
#  similar to previous successful tasks)"
```

### Parallel Execution Optimization
```bash
# System identifies compatible parallel tasks
/pm:status
# Shows: "Tasks 003, 005, 007 can run in parallel 
#        (different domains, no file conflicts)"
```

### Adaptive Templates
Templates automatically adjust based on complexity:
- Simple tasks: Minimal template
- Standard tasks: Structured template  
- RA tasks: Full template with assumption tracking

## Best Practices

### 1. Trust the Assessment
- Use `/pm:assess` to preview complexity before starting
- Let the system choose the appropriate mode
- Override only when you have specific reasons

### 2. Learn from Patterns
- Review assessment accuracy after task completion
- Note which mode recommendations work best
- Update task descriptions based on learning

### 3. Use the Right Level
- Don't over-engineer simple tasks
- Don't under-estimate complex tasks
- Let verification scale with complexity

### 4. Embrace Assumption Tracking
- For RA modes, mark uncertainties with tags
- Don't try to be perfect - mark assumptions
- Use verification to validate and clean up

## Troubleshooting

### "Assessment seems wrong"
```bash
/pm:assess <task>          # Get detailed breakdown
# Review scoring factors and override if needed
/pm:start <task> --mode=<override>
```

### "Mode feels too heavy/light"
- Let the task complete and review effectiveness
- The system learns from mode effectiveness over time
- Consider if task description needs more/less detail

### "RA tags seem overwhelming"  
- RA tags only appear for complex tasks (7+ complexity)
- They prevent issues by making assumptions explicit
- Verification resolves tags automatically - just mark uncertainties

### "Want to see progress"
```bash
/pm:status                 # Dashboard with complexity metrics
# Shows mode effectiveness, assessment accuracy, progress
```

## Integration with Development Workflow

### Git Integration
- Works with any branching strategy
- Task completion can trigger automated testing
- Progress updates feed into project dashboards

### Team Collaboration
- Multiple developers see same complexity assessments
- Shared learning across team members
- Consistent quality levels regardless of developer

### CI/CD Pipeline
- Task complexity can trigger different test suites
- Quality gates based on mode used
- Automated deployment for verified tasks

## Getting Specific Help

```bash
/pm:help init             # Adaptive initialization help
/pm:help assess           # Complexity assessment details
/pm:help start            # Intelligent execution help
/pm:help verify           # Adaptive verification guide
/pm:help plan-review      # RA planning readiness review help
```

## What Makes This "Adaptive"

### Traditional Approach
- Same process for every task
- Over-engineer simple work OR under-engineer complex work
- Manual decision-making about rigor level

### PM Adaptive Approach  
- **Intelligent Assessment**: Automatically evaluate complexity
- **Scaled Rigor**: Match process overhead to task needs
- **Learning System**: Get smarter over time
- **Quality Assurance**: Appropriate verification for risk level

### Result
- ⚡ **Faster simple tasks**: No unnecessary overhead
- 🛡️ **Safer complex tasks**: Proper assumption tracking and verification
- 📈 **Continuous improvement**: System learns your patterns
- 🎯 **Optimal resource allocation**: Right effort for each task

The PM Adaptive Workflow eliminates the choice between "fast and risky" vs "slow and safe" - instead, it's **adaptive and optimal** for every task.
