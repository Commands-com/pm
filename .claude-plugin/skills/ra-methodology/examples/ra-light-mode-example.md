# RA-Light Mode Workflow Example

**Task**: Implement OAuth2 authentication with Google and GitHub
**Complexity Score**: 7
**RA Mode**: RA-Light
**Estimated Time**: 12 hours

---

## Step 1: Create Task with Comprehensive RA Data

```python
create_task(
    name="Implement OAuth2 authentication with Google and GitHub providers",
    description="Add OAuth2 support for social login with proper token management and security",
    epic_name="Authentication System",
    project_name="Dashboard App",
    ra_mode="ra-light",
    ra_score="7",
    ra_tags='["#COMPLETION_DRIVE_INTEGRATION: OAuth2 flow follows standard redirect pattern", "#SUGGEST_ERROR_HANDLING: Token refresh logic needed", "#PATTERN_MOMENTUM: Using JWT for session management"]',
    ra_metadata='{"complexity_factors": ["OAuth2 protocol", "Multiple providers", "Token security"], "integration_points": ["Google OAuth API", "GitHub OAuth API", "Database", "Frontend"], "estimated_hours": 12, "verification_needed": true}'
)
# Returns task_id: 156
```

---

## Step 2: Research Phase

```python
# Get existing authentication knowledge
get_knowledge(project_id="3", category="authentication")
get_knowledge(project_id="3", category="security")

# Review OAuth2 documentation
# Review existing session management patterns
```

---

## Step 3: Start Work

```python
update_task_status(task_id="156", status="IN_PROGRESS", agent_id="claude")
```

---

## Step 4: Implementation with Extensive RA Tagging

### OAuth2 Flow Implementation

```python
# Backend: OAuth2 handler
@router.get("/auth/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str):
    # Exchange code for token
    # Verify state parameter
    # Create/update user
    # Generate session token
```

**Tag every assumption:**

```python
add_ra_tag(
    task_id="156",
    ra_tag_text="#COMPLETION_DRIVE_IMPL: Using authorization code flow (not implicit flow)",
    agent_id="claude"
)

add_ra_tag(
    task_id="156",
    ra_tag_text="#COMPLETION_DRIVE_INTEGRATION: Google OAuth requires client_secret in token exchange",
    agent_id="claude"
)

add_ra_tag(
    task_id="156",
    ra_tag_text="#CONTEXT_RECONSTRUCT: Assuming HTTPS required for OAuth2 redirects",
    agent_id="claude"
)

add_ra_tag(
    task_id="156",
    ra_tag_text="#SUGGEST_VALIDATION: Verifying state parameter to prevent CSRF attacks",
    agent_id="claude"
)

add_ra_tag(
    task_id="156",
    ra_tag_text="#SUGGEST_ERROR_HANDLING: Handling OAuth provider errors (user denied, expired code)",
    agent_id="claude"
)
```

### Token Management

```python
# JWT token generation
def create_session_token(user_id: int, provider: str) -> str:
    payload = {
        "user_id": user_id,
        "provider": provider,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

**More tags:**

```python
add_ra_tag(
    task_id="156",
    ra_tag_text="#PATTERN_MOMENTUM: Using JWT with HS256 (matches existing API tokens)",
    agent_id="claude"
)

add_ra_tag(
    task_id="156",
    ra_tag_text="#COMPLETION_DRIVE_IMPL: 30-day token expiration (standard for web apps)",
    agent_id="claude"
)

add_ra_tag(
    task_id="156",
    ra_tag_text="#SUGGEST_CLEANUP: Implementing token refresh before expiration",
    agent_id="claude"
)
```

### Database Schema

```sql
-- oauth_accounts table
CREATE TABLE oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    provider VARCHAR(50),
    provider_user_id VARCHAR(255),
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP
);
```

**Schema tags:**

```python
add_ra_tag(
    task_id="156",
    ra_tag_text="#ASSOCIATIVE_GENERATION: Storing refresh_token (feels necessary for OAuth2)",
    agent_id="claude"
)

add_ra_tag(
    task_id="156",
    ra_tag_text="#SUGGEST_DEFENSIVE: Encrypting access_token and refresh_token at rest",
    agent_id="claude"
)

add_ra_tag(
    task_id="156",
    ra_tag_text="#PATTERN_CONFLICT: Uncertain if token encryption is overkill vs prudent",
    agent_id="claude"
)
```

---

## Step 5: Capture Knowledge for Key Decisions

```python
# Decision: Token storage strategy
upsert_knowledge(
    title="OAuth Token Storage Strategy - Encryption Decision",
    content="Decision: Encrypt OAuth tokens at rest using Fernet symmetric encryption. Reasoning: Tokens grant account access if database is compromised. Trade-off: Slight performance cost (negligible). Implementation: Store encrypted tokens in TEXT field, decrypt on retrieval. Key management: Environment variable for encryption key.",
    category="architecture_decisions",
    tags='["oauth", "security", "encryption", "tokens"]',
    task_id="156"
)

# Gotcha encountered
upsert_knowledge(
    title="GitHub OAuth Requires User-Agent Header",
    content="Gotcha: GitHub OAuth API returns 403 if User-Agent header is missing. Tried: 1) Standard OAuth flow without User-Agent (failed with 403), 2) Added custom User-Agent header (success). GitHub docs don't prominently mention this requirement. Required header: User-Agent: YourAppName/1.0",
    category="integration_gotchas",
    tags='["github", "oauth", "http_headers", "403_error"]',
    task_id="156"
)
```

---

## Step 6: Log Progress with Knowledge References

```python
update_task(
    task_id="156",
    agent_id="claude",
    log_entry="OAuth2 backend implementation complete. Created 2 knowledge items: 1) Token encryption strategy decision, 2) GitHub User-Agent requirement gotcha. Frontend integration next. 15 RA tags added so far covering security, token management, and provider-specific requirements."
)
```

---

## Step 7: Flag for Verification

```python
update_task(
    task_id="156",
    agent_id="claude",
    ra_metadata='{"complexity_factors": ["OAuth2 protocol", "Multiple providers", "Token security"], "integration_points": ["Google OAuth API", "GitHub OAuth API", "Database", "Frontend"], "estimated_hours": 12, "verification_needed": true, "security_review_required": true, "assumptions_to_validate": ["Token encryption necessity", "30-day expiration appropriate", "CSRF protection sufficient"]}',
    ra_metadata_mode="merge"
)
```

---

## Step 8: Testing (Comprehensive)

- ✓ Unit tests: Token generation, validation, refresh
- ✓ Integration tests: Full OAuth flow for each provider
- ✓ Security tests: CSRF attack prevention, token tampering
- ✓ Error scenarios: User denial, expired codes, invalid states
- ✓ Manual testing: Complete flow in browser for both providers

---

## Step 9: Mark for Review

```python
update_task_status(task_id="156", status="REVIEW", agent_id="claude")
```

---

## Step 10: Verification Review Process

Reviewer checks ALL RA tags:

1. **#COMPLETION_DRIVE_IMPL: Authorization code flow** → ✓ Correct for web apps
2. **#COMPLETION_DRIVE_INTEGRATION: client_secret required** → ✓ Per OAuth2 spec
3. **#CONTEXT_RECONSTRUCT: HTTPS required** → ✓ OAuth2 security requirement
4. **#SUGGEST_VALIDATION: State parameter verification** → ✓ Essential for CSRF
5. **#PATTERN_MOMENTUM: JWT HS256** → ✓ Matches project standard
6. **#COMPLETION_DRIVE_IMPL: 30-day expiration** → ⚠️ Check security policy (validated: acceptable)
7. **#ASSOCIATIVE_GENERATION: Storing refresh_token** → ✓ Needed for re-authentication
8. **#SUGGEST_DEFENSIVE: Token encryption** → ✓ Prudent given sensitivity
9. **#PATTERN_CONFLICT: Encryption overkill?** → Resolved: Not overkill, good practice

**Review outcome**: 8/9 assumptions validated, 1 required confirmation

---

## Step 11: Capture Validation Results

```python
# Capture assumption validation for audit trail
capture_assumption_validation(
    task_id="156",
    ra_tag_id="ra-tag-30day-exp",
    outcome="validated",
    reason="30-day token expiration aligns with security policy for low-risk applications",
    confidence=95,
    reviewer_agent_id="security-reviewer"
)
```

---

## Step 12: Mark Done

```python
update_task_status(task_id="156", status="DONE", agent_id="reviewer")
```

---

## Complete Statistics

- **RA Tags**: 15 total
- **Knowledge Items**: 2 (decision + gotcha)
- **Tests**: 25 test cases
- **Lines of Code**: ~800
- **Time**: 14 hours (2 hours over estimate)
- **Assumptions Validated**: 9/9 (100%)

---

## RA-Light Mode Requirements

✅ **Must Have:**
- Extensive RA tagging (10-20 tags typical)
- Tag EVERY assumption, don't skip anything
- Knowledge items for all major decisions
- Flag verification_needed in metadata
- Comprehensive testing
- Thorough review of ALL tags

❌ **Don't:**
- Implement SUGGEST_* items without discussion
- Skip tagging "obvious" assumptions
- Go directly to DONE (must use REVIEW)
- Capture routine implementation as knowledge

---

## Difference from Standard Mode

| Aspect | Standard Mode | RA-Light Mode |
|--------|---------------|---------------|
| RA Tags | 5-10 | 10-20 |
| Tagging Requirement | Encouraged | **MANDATORY** |
| Knowledge | Gotchas only | Decisions + gotchas |
| Verification | Self-review | **External verification required** |
| SUGGEST_* handling | Implement if prudent | **Tag but don't implement without approval** |
| Review depth | Assumption validation | **Full assumption audit** |

---

## When RA-Light is Needed

Use RA-Light (complexity 7-8) when:
- Touching 3+ system domains
- Significant security implications
- Multiple integration points
- Many assumptions being made
- High uncertainty about approach
- Critical business logic

RA-Light prevents "confident but wrong" implementations through systematic assumption tracking and verification.
