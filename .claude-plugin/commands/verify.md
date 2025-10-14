---
description: "Deploy verification agent to resolve RA tags and validate implementation assumptions"
allowed-tools: Read, Task, TodoWrite
---

# RA Tag Verification

Deploy specialized verification agent to systematically resolve Response_Awareness tags, validate implementation assumptions, and ensure production-ready code quality.

## Usage
```
/pm:verify <task-file>
```
Example: `/pm:verify 001-user-auth`

## Instructions

You are deploying an RA verification agent to resolve all Response_Awareness tags from implementation and ensure code quality through systematic assumption validation.

## MCP Integration (preferred)
Drive verification via MCP for locking, status updates, logs, and RA metadata.

- Full name: mcp__project-manager-mcp__list_tasks
- Full name: mcp__project-manager-mcp__get_task_details
- Full name: mcp__project-manager-mcp__acquire_task_lock
- Full name: mcp__project-manager-mcp__update_task_status
- Full name: mcp__project-manager-mcp__update_task
- Full name: mcp__project-manager-mcp__release_task_lock

MCP flow:
1) Resolve the task by name → `...__list_tasks` then `...__get_task_details`.
2) Acquire verification lock → `...__acquire_task_lock(task_id, agent_id)` and set status to `REVIEW` or `verifying` via `...__update_task_status`.
3) As tags are inventoried and resolved, append structured entries to `ra_metadata.verification` and `log_entry` via `...__update_task`.
4) On completion, set `DONE` (or project’s final state) and release the lock via `...__release_task_lock`.

### 1. Validate Task Implementation
Prefer MCP:
- Confirm task exists and is ready for verification via `...__get_task_details` (status and RA tags).
- If no RA tags and complexity ≤ 3, you may proceed with Simple verification; otherwise prompt to ensure RA implementation happened.

### 2. Scan for RA Tags

Read implementation files and identify all RA tags:
- `#COMPLETION_DRIVE_IMPL` - Implementation assumptions
- `#COMPLETION_DRIVE_INTEGRATION` - Integration assumptions  
- `#CONTEXT_DEGRADED` - Memory uncertainty
- `#CONTEXT_RECONSTRUCT` - Reconstructed details
- `#CARGO_CULT` - Pattern-driven code
- `#PATTERN_MOMENTUM` - Over-implementation
- `#ASSOCIATIVE_GENERATION` - "Feels right" additions
- `#PATTERN_CONFLICT` - Conflicting approaches
- `#TRAINING_CONTRADICTION` - Training conflicts
- `#PARADIGM_CLASH` - Architecture conflicts
- `#BEST_PRACTICE_TENSION` - Competing practices
- `#SUGGEST_ERROR_HANDLING` - Error handling suggestions
- `#SUGGEST_EDGE_CASE` - Edge case suggestions
- `#SUGGEST_VALIDATION` - Validation suggestions
- `#SUGGEST_CLEANUP` - Cleanup suggestions
- `#SUGGEST_DEFENSIVE` - Defensive programming suggestions

### 3. Create Verification Tracking
Use MCP to track resolution in `ra_metadata.verification` and progress logs:
```yaml
Assumption Tag Resolution:
  - Verify COMPLETION_DRIVE_IMPL assumptions (count: X)
  - Validate COMPLETION_DRIVE_INTEGRATION points (count: X) 
  - Cross-reference CONTEXT_DEGRADED items (count: X)

Pattern Evaluation:
  - Evaluate CARGO_CULT code necessity (count: X)
  - Assess PATTERN_MOMENTUM over-implementation (count: X)
  - Validate ASSOCIATIVE_GENERATION additions (count: X)

Conflict Resolution:
  - Resolve PATTERN_CONFLICT issues (count: X)
  - Address TRAINING_CONTRADICTION items (count: X)
  - Align PARADIGM_CLASH decisions (count: X)

Suggestion Compilation:
  - Collect all SUGGEST_* tags for user review (count: X)
```

### 4. Deploy RA Verification Agent

```yaml
Task:
  description: "Resolve RA tags and verify implementation: $ARGUMENTS"
  subagent_type: "general-purpose"
  prompt: |
    You are an RA verification agent for systematic tag resolution and code quality assurance.
    
    Task File: .pm/tasks/$ARGUMENTS.md
    Implementation Files: {scan results from step 2}
    
    VERIFICATION PROTOCOL:
    
    1. ASSUMPTION TAG RESOLUTION:
    
    For each COMPLETION_DRIVE_IMPL tag:
    - Re-read original task specification
    - Test actual behavior vs assumption
    - ✅ If correct: Replace tag with explanatory comment
    - ❌ If incorrect: Fix implementation, document change
    
    For each COMPLETION_DRIVE_INTEGRATION tag:
    - Test integration point directly
    - Verify API contracts and actual responses
    - ✅ If correct: Document verified interface
    - ❌ If incorrect: Update integration, add error handling
    
    For CONTEXT_DEGRADED/RECONSTRUCT tags:
    - Cross-reference with original specifications
    - Validate naming conventions and architectural decisions
    - ✅ If accurate: Replace with explanatory comment
    - ❌ If inaccurate: Correct to match requirements
    
    2. PATTERN EVALUATION:
    
    For each CARGO_CULT tag:
    - Check task requirements for explicit need
    - If not mentioned → Remove code, document removal rationale
    - If implied/needed → Keep but validate implementation approach
    
    For each PATTERN_MOMENTUM tag:
    - Compare implementation scope vs actual requirements
    - If over-implemented → Simplify to match requirements exactly
    - If appropriate scope → Keep, remove tag, document validation
    
    For ASSOCIATIVE_GENERATION tags:
    - Validate against explicit requirements
    - Remove if purely "feels right" with no requirement basis
    - Keep if genuinely needed, document justification
    
    3. CONFLICT RESOLUTION:
    
    For PATTERN_CONFLICT tags:
    - Analyze existing project patterns and conventions
    - Choose approach most consistent with codebase
    - Document decision rationale in code comments
    
    For TRAINING_CONTRADICTION/PARADIGM_CLASH tags:
    - Prioritize project-specific patterns over general training
    - Align with established project architecture
    - Maintain consistency within the project
    
    4. SUGGESTION COMPILATION:
    
    For ALL SUGGEST_* tags:
    - DO NOT implement the suggestions automatically
    - Collect into structured list for user review
    - Assess impact (high/medium/low) and effort (hours estimate)
    - Prioritize by value vs implementation cost
    
    RESOLUTION DOCUMENTATION:
    For each resolved tag, document:
    - Original assumption/decision
    - Verification action taken
    - Evidence supporting resolution
    - Impact on code functionality
    
    DELIVERABLE: Comprehensive Verification Report with:
    - Tag resolution summary with metrics
    - Code quality improvements made
    - Lines of code simplified/removed
    - User suggestion compilation with priorities
    - Evidence for all verification decisions
    - Zero unresolved critical tags remaining
    
    QUALITY GATES:
    - ✅ All COMPLETION_DRIVE tags resolved with evidence
    - ✅ All pattern tags evaluated (keep/remove with rationale)  
    - ✅ All conflicts resolved consistently with project
    - ✅ All SUGGEST tags compiled for user decision
    - ✅ Code simplified without functionality loss
    - ✅ Implementation matches requirements (not assumptions)
```

### 5. Create Verification Progress File

Create `.pm/tasks/$ARGUMENTS-verification.md`:

```markdown
# RA Verification: $ARGUMENTS

## Verification Started
- **Date**: {current_date}
- **Implementation Agent**: {previous_agent_id}
- **Verification Agent**: RA Verification Agent
- **Tags Identified**: {total_count}

## Tag Resolution Progress
{Verification agent will update with systematic resolution}

## Assumption Validation Results
{Evidence for each assumption verification}

## Pattern Evaluation Decisions
{Rationale for keeping/removing pattern-driven code}

## Code Quality Improvements
{Lines simplified, functionality preserved, consistency achieved}

## User Decision Items
{Compiled SUGGEST tags with impact/effort analysis}

## Verification Complete
{Final quality metrics and readiness confirmation}
```

### 6. Update Task Status

Update task frontmatter:
```yaml
---
status: verifying
verification_started: {current_date}
verification_agent: ra-verification-{timestamp}
verification_file: .pm/tasks/$ARGUMENTS-verification.md
tags_identified: {count}
---
```

### 7. Monitor Verification Progress

```
🔍 RA Verification started: $ARGUMENTS

📊 Verification Tracking:
  ✓ RA tags identified: {count}
  ✓ Verification agent deployed
  ✓ Systematic resolution protocol initiated
  
📁 Files to Monitor:
  .pm/tasks/$ARGUMENTS.md (verification status)
  .pm/tasks/$ARGUMENTS-verification.md (resolution progress)

🎯 Verification Objectives:
  - Validate all implementation assumptions
  - Evaluate pattern-driven vs requirement-driven code
  - Resolve conflicts with project standards
  - Compile suggestions for user review
  - Ensure zero unresolved critical tags

🧹 Quality Outcomes Expected:
  - Production-ready code with validated assumptions
  - Simplified implementation without unnecessary patterns
  - Consistent alignment with project conventions
  - Clear separation of requirements vs suggestions
```

### 8. Verification Completion

When verification agent completes, provide summary:

```markdown
✅ RA Verification Complete: $ARGUMENTS

## Resolution Summary
- **Tags Processed**: {total_count}
- **Assumptions Verified**: {verified_count} correct, {corrected_count} fixed
- **Pattern Code Evaluated**: {pattern_count} - {kept_count} kept, {removed_count} removed
- **Conflicts Resolved**: {conflict_count} aligned with project standards
- **Code Simplified**: {lines_removed} unnecessary lines removed

## User Review Required
**Suggestions Compiled**: {suggestion_count} items need your decision

### High Priority ({count})
- Error handling improvements
- Critical edge case handling
- Security validation enhancements

### Medium Priority ({count})  
- Performance optimizations
- User experience improvements
- Code maintainability

### Low Priority ({count})
- Nice-to-have defensive programming
- Optional cleanup improvements

## Next Steps
1. Review suggestion priorities and approve/reject
2. Run integration tests to verify changes
3. Update documentation with verified assumptions
4. Mark task as production-ready

**Quality Assurance**: Zero unresolved assumptions, all pattern-driven code validated, project consistency maintained.
```

### 9. Integration with PM Workflow

**After Verification**:
- User reviews and decides on suggestion items
- Approved suggestions can be implemented as follow-up tasks
- Task marked as production-ready with verified assumptions
- Lessons learned archived for future template improvements

**Quality Gates Enforced**:
- No task completion without assumption verification
- All pattern-driven code explicitly validated
- Project consistency maintained through conflict resolution
- User retains control over enhancement decisions

Remember: RA verification transforms assumption-laden implementation into conscious, validated, production-ready code through systematic metacognitive analysis.
