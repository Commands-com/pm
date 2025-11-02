# RA Complexity Scoring Guide

Detailed criteria for assessing task complexity on a 1-10 scale.

## Scoring Factors

Consider these dimensions when assessing complexity:

1. **Code Size**: Lines of code that will be affected
2. **Domains Affected**: Number of system domains touched
3. **Integration Points**: External systems or services involved
4. **Uncertainty Level**: How much is unknown or assumed
5. **Testing Complexity**: Difficulty of verification

## Complexity Levels

### Simple (1-3)

**Characteristics:**
- Single file or small set of related files
- Well-defined requirements
- Minimal integration with other systems
- Straightforward testing
- Low uncertainty

**Examples:**
- Fix button alignment (complexity: 2)
- Add validation to existing form field (complexity: 2)
- Update text labels or UI copy (complexity: 1)
- Simple data transformation function (complexity: 3)

**Typical Effort:** < 2 hours

---

### Standard (4-6)

**Characteristics:**
- Multiple files across 2-3 modules
- Some integration with existing systems
- Moderate testing requirements
- Some architectural decisions needed
- Medium uncertainty

**Examples:**
- Implement user search feature (complexity: 5)
- Add new API endpoint with validation (complexity: 5)
- Create data export functionality (complexity: 6)
- Refactor component to use new pattern (complexity: 4)

**Typical Effort:** 2-8 hours

---

### RA-Light (7-8)

**Characteristics:**
- Touches 3+ modules or domains
- Significant integration complexity
- Multiple assumptions being made
- Complex testing scenarios
- Architectural decisions with trade-offs

**Examples:**
- Implement OAuth2 authentication (complexity: 7)
- Build notification system (complexity: 8)
- Create real-time collaboration feature (complexity: 8)
- Database migration with data transformation (complexity: 7)

**Typical Effort:** 8-16 hours

**Special Requirements:**
- Extensive RA tagging throughout
- Knowledge documentation for all decisions
- Flag for verification review

---

### RA-Full (9-10)

**Characteristics:**
- System-wide changes affecting many modules
- Multiple integration points and external services
- High uncertainty and many assumptions
- Complex coordinated testing
- Requires multi-agent orchestration

**Examples:**
- Complete system architecture redesign (complexity: 10)
- Multi-channel notification system with templating (complexity: 9)
- Real-time synchronization across distributed systems (complexity: 10)
- Full application security overhaul (complexity: 9)

**Typical Effort:** 16+ hours

**Special Requirements:**
- DO NOT implement directly
- Deploy specialized agents (survey, planning, implementation, verification)
- Coordinate with atomic task locking
- Full verification phase required

## Adjustment Factors

Start with base complexity, then adjust:

### Increase Score (+1 each if applicable)
- **Unfamiliar technology**: First time using library/framework
- **Unclear requirements**: Requirements are vague or changing
- **Critical system**: Changes affect core business logic
- **Performance sensitive**: Requires optimization/profiling
- **Security implications**: Handling sensitive data/authentication

### Decrease Score (-1 each if applicable)
- **Well-documented patterns**: Clear examples exist in codebase
- **Isolated changes**: Minimal impact on other systems
- **Comprehensive tests exist**: Can rely on existing test coverage
- **Recent similar work**: Just completed similar feature

## Quick Decision Tree

```
Start here:
│
├─ Single file, < 2 hours? → Simple (1-3)
│
├─ 2-3 modules, some integration? → Standard (4-6)
│
├─ 3+ modules, many assumptions? → RA-Light (7-8)
│
└─ System-wide, high uncertainty? → RA-Full (9-10)
```

## Examples by Domain

### Frontend
- Add CSS class: 1
- New component with props: 3
- Form with validation: 5
- Complex data grid: 7
- Complete UI redesign: 9

### Backend
- Add log statement: 1
- New database query: 3
- REST API endpoint: 5
- Authentication system: 7
- Microservice architecture: 9

### Database
- Add column: 2
- Create index: 3
- Data migration: 6
- Schema redesign: 8
- Distributed transactions: 10

### Infrastructure
- Update config: 1
- Add environment variable: 2
- CI/CD pipeline change: 5
- Deployment automation: 7
- Multi-region setup: 9

## When in Doubt

**If uncertain between two scores, choose the higher one.** It's better to be over-prepared with more RA tagging than to under-estimate and miss critical assumptions.

**Rule of thumb:** If you're making assumptions about how things work, add +1 to your initial score.
