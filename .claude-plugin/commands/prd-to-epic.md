---
description: "Transform a Product Requirements Document into a detailed technical implementation plan"
allowed-tools: Read, Write
---

# Convert PRD to Epic

Transform a Product Requirements Document into a detailed technical implementation plan.

## Usage
```
/pm:prd-to-epic <feature-name>
```

## Instructions

You are creating a technical epic for: **$ARGUMENTS**

## MCP Integration (preferred)
Ensure the epic exists in MCP and prime it for upcoming tasks.

- Full name: mcp__project-manager-mcp__list_epics — Check for existing epic
- Full name: mcp__project-manager-mcp__create_task — Upsert epic/project via a seed task
- Full name: mcp__project-manager-mcp__update_task — Record epic planning metadata/logs

Recommended flow:
1) If the epic is not found via `...__list_epics`, create a seed task with `epic_name=$ARGUMENTS` to upsert the epic.
2) Persist epic-level RA planning metadata (architecture decisions, risks) into `ra_metadata.epic_plan` attached to the seed task using `...__update_task`.
3) Proceed to `/pm:epic-tasks $ARGUMENTS` to generate granular tasks backed by MCP.

### 1. Validate PRD Exists
- Check if `.pm/prds/$ARGUMENTS.md` exists
- If not found: "❌ PRD not found. Create it first with: /pm:prd-new $ARGUMENTS"
- Read and analyze the PRD content

### 2. Technical Analysis

Based on the PRD, analyze:

#### Architecture Requirements
- What new database tables/models are needed?
- What API endpoints need to be created/modified?
- What UI components are required?
- How does this integrate with existing systems?

#### Data Flow Design
- How does data move through the system?
- What are the key data transformations?
- Where is data stored and how is it accessed?
- What are the performance implications?

#### Integration Points
- What external services are involved?
- How does this interact with authentication?
- What existing APIs need to be modified?
- Are there third-party integrations required?

### 3. Technology-Specific Planning

Read `.pm/config.json` to get the project type, then create architecture decisions specific to the tech stack:

#### For TypeScript Projects:
- React/Vue component architecture
- State management approach (Context, Redux, Zustand)
- API client structure
- TypeScript interfaces and types
- Build and bundling considerations

#### For Python Projects:
- Django/FastAPI endpoint structure
- Database models and migrations
- Background job requirements
- API serialization approach
- Deployment and scaling strategy

#### For Other Project Types:
- Framework-specific patterns
- Language-specific best practices
- Testing strategies
- Performance optimizations

### 4. Create Technical Epic

Use the template from `.pm/templates/epic-standard.md` and populate with:

**Architecture Decisions**
- Specific technology choices with rationale
- Database schema with relationships
- API design with endpoints and data models
- Component hierarchy and data flow

**Implementation Strategy**
- High-level implementation approach
- Key technical challenges and solutions
- Performance and scalability considerations
- Security and compliance requirements

**Task Breakdown Preview**
- Rough outline of major implementation tasks
- Dependencies between different work streams
- Parallel execution opportunities
- Risk areas that need special attention

### 5. Epic Quality Validation

Ensure the epic includes:
- [ ] Clear technical architecture decisions
- [ ] Specific database schema (if applicable)
- [ ] API design with request/response formats
- [ ] Component/service breakdown
- [ ] Integration strategy with existing systems
- [ ] Performance and scalability considerations
- [ ] Security and error handling approach
- [ ] Testing strategy
- [ ] Deployment and monitoring plan

### 6. Save Epic

Save to `.pm/epics/$ARGUMENTS.md` using the epic template with current date/time.

### 7. Next Steps

After successful creation:
```
✅ Technical epic created: .pm/epics/$ARGUMENTS.md

🏗️ Implementation Plan Ready:
  ✓ Architecture decisions documented
  ✓ Technical approach defined
  ✓ Integration strategy planned
  ✓ Risk areas identified

📋 What's Next:
  1. Review technical decisions with team
  2. Break into specific tasks: /pm:epic-tasks $ARGUMENTS
  3. Validate technical feasibility
  4. Plan development timeline

💡 The epic serves as the technical blueprint - all tasks will reference this plan!
```

## Technical Epic Checklist

A good technical epic should:
- [ ] Make specific technology choices with rationale
- [ ] Define clear data architecture and API contracts
- [ ] Identify all integration points and dependencies
- [ ] Address scalability and performance requirements
- [ ] Include comprehensive error handling strategy
- [ ] Plan testing approach for all components
- [ ] Consider deployment and monitoring needs
- [ ] Identify potential technical risks and mitigation

The epic bridges product requirements and implementation tasks - it should be detailed enough that any developer can understand the technical approach!
