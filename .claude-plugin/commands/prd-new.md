---
description: "Launch guided brainstorming to create a comprehensive Product Requirements Document"
allowed-tools: Bash, Write, Read
---

# Create New PRD

Launch guided brainstorming to create a comprehensive Product Requirements Document.

## Usage
```
/pm:prd-new <feature-name>
```

## Instructions

You are creating a PRD for: **$ARGUMENTS**

## MCP Integration (optional)
Optionally seed an MCP epic/project mapping for this PRD to streamline later commands.

- Full name: mcp__project-manager-mcp__create_task — Upserts project/epic via a seed task
- Full name: mcp__project-manager-mcp__update_task — Attach PRD link/metadata to the seed

Suggested flow:
1) Create a seed tracking task: `mcp__project-manager-mcp__create_task(name="PRD: $ARGUMENTS", project_name="{YourProject}", epic_name="$ARGUMENTS", ra_mode="standard", ra_score="4")`.
2) Update task with `ra_metadata.prd_path = ".pm/prds/$ARGUMENTS.md"` and a `log_entry` once the PRD is created.

### 1. Validate Feature Name
- Must be kebab-case (lowercase letters, numbers, hyphens only)
- Examples: `user-authentication`, `payment-processing`, `notification-system`
- If invalid format, ask user to provide valid name

### 2. Check for Existing PRD
- Check if `.pm/prds/$ARGUMENTS.md` already exists
- If exists, ask: "PRD already exists. Overwrite? (yes/no)"
- Only proceed with explicit 'yes'

### 3. Guided Discovery Process

**Start with open-ended questions to understand the feature deeply:**

#### Problem Discovery
- "What specific problem does $ARGUMENTS solve?"
- "Who experiences this problem and how often?"
- "What happens if this problem isn't solved?"
- "How are users currently working around this problem?"

#### User Journey Exploration
- "Walk me through the ideal user experience for $ARGUMENTS"
- "What would success look like from the user's perspective?"
- "What are the key moments in this user journey?"
- "Where might users get confused or frustrated?"

#### Technical Constraints
- "Are there any technical limitations we need to consider?"
- "What existing systems does this need to integrate with?"
- "What performance requirements are critical?"
- "Are there security or compliance considerations?"

#### Success Metrics
- "How will we measure if $ARGUMENTS is successful?"
- "What metrics would indicate users are getting value?"
- "What would make this feature a failure?"

### 4. Create Comprehensive PRD

Use the template from `.pm/templates/prd-standard.md` and populate with discovered information.

**Key Requirements for PRD Quality:**
- **Specific User Stories**: Not "users want to login" but "new users can create account with email/password in under 60 seconds"
- **Measurable Success Criteria**: Not "improve user experience" but "increase task completion rate from 60% to 85%"
- **Technical Details**: Include architecture considerations based on project type
- **Edge Cases**: Address error conditions and boundary scenarios
- **Dependencies**: Clear internal and external dependencies

### 5. PRD Validation

Before saving, validate the PRD contains:
- [ ] Clear problem statement with user impact
- [ ] Specific user stories with acceptance criteria  
- [ ] Measurable success metrics
- [ ] Technical considerations for the project type
- [ ] Explicit scope boundaries (what's included/excluded)
- [ ] Dependencies and assumptions
- [ ] Risk assessment

### 6. Save PRD

Save to `.pm/prds/$ARGUMENTS.md` using the template structure with current date/time.

### 7. Next Steps

After successful creation:
```
✅ PRD created: .pm/prds/$ARGUMENTS.md

📋 What's Next:
  1. Review and refine the PRD
  2. Get stakeholder approval
  3. Create technical epic: /pm:prd-to-epic $ARGUMENTS
  4. Share PRD with team for feedback

💡 Pro tip: The better the PRD, the easier the implementation planning will be!
```

## Quality Checklist

A good PRD should:
- [ ] Clearly articulate the problem and user need
- [ ] Define specific, measurable success criteria
- [ ] Include detailed user stories with edge cases
- [ ] Address technical feasibility for your tech stack
- [ ] Have explicit scope boundaries
- [ ] Consider integration points and dependencies
- [ ] Include risk assessment and mitigation strategies

The PRD is the foundation for all implementation work - invest time to make it comprehensive and clear!
