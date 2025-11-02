# Simple Mode Workflow Example

**Task**: Fix button alignment on settings page
**Complexity Score**: 2
**RA Mode**: Simple
**Estimated Time**: 30 minutes

---

## Step 1: Create Task

```python
create_task(
    name="Fix button alignment on settings page",
    description="Align save/cancel buttons to the right of the form",
    epic_name="UI Polish",
    project_name="Dashboard App",
    ra_mode="simple",
    ra_score="2"
)
# Returns task_id: 42
```

---

## Step 2: Start Work

```python
update_task_status(
    task_id="42",
    status="IN_PROGRESS",
    agent_id="claude"
)
# Auto-acquires lock
```

---

## Step 3: Implement with RA Tags

```typescript
// Edit settings.tsx
// Changed:
<div className="form-actions">
  <button>Save</button>
  <button>Cancel</button>
</div>

// To:
<div className="form-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
  <button>Cancel</button>
  <button>Save</button>
</div>
```

**Add RA tag for the assumption:**
```python
add_ra_tag(
    task_id="42",
    ra_tag_text="#PATTERN_MOMENTUM: Using flexbox for alignment (standard pattern in this codebase)",
    agent_id="claude"
)
```

---

## Step 4: Test

Test manually in browser:
- ✓ Buttons aligned to right
- ✓ Proper spacing between buttons
- ✓ Cancel before Save (standard pattern)
- ✓ Mobile responsive

No issues encountered - worked immediately.

---

## Step 5: Knowledge Capture Decision

**Question**: Should I capture knowledge?

**Answer**: NO - This was straightforward. Flexbox worked immediately, no gotchas encountered.

**Knowledge capture is ONLY for**:
- ❌ Routine implementations → NO
- ✅ Multi-attempt solutions → YES
- ✅ Non-obvious gotchas → YES

---

## Step 6: Mark for Review

Even simple tasks with RA tags must go through REVIEW:

```python
update_task_status(
    task_id="42",
    status="REVIEW",
    agent_id="claude"
)
# Releases lock for reviewer
```

**Why REVIEW?** The #PATTERN_MOMENTUM tag indicates an assumption (using flexbox). Reviewer should verify this is the correct approach.

---

## Step 7: Review Process

Reviewer checks:
- ✓ Flexbox is indeed the standard pattern in codebase
- ✓ Button order (Cancel before Save) matches other forms
- ✓ Spacing (8px gap) matches design system
- ✓ Works in all supported browsers

**Review outcome**: Assumption validated ✓

---

## Step 8: Mark Done

```python
update_task_status(
    task_id="42",
    status="DONE",
    agent_id="reviewer"
)
# Auto-releases lock
```

---

## Complete Timeline

1. **Create task** → 2 min
2. **Start work (IN_PROGRESS)** → Instant
3. **Implement + tag assumption** → 15 min
4. **Test** → 5 min
5. **Mark REVIEW** → Instant
6. **Review & validate** → 5 min
7. **Mark DONE** → Instant

**Total**: ~27 minutes

---

## Key Takeaways for Simple Mode

✅ **DO**:
- Create task BEFORE implementing
- Use RA tags for assumptions (even if it feels obvious)
- Send to REVIEW status if RA tags were used
- Test thoroughly before marking complete

❌ **DON'T**:
- Skip task creation ("it's too small")
- Skip RA tags ("it's obvious")
- Go directly to DONE if you used RA tags
- Capture knowledge for routine work

---

## What If Something Went Wrong?

### Scenario: Flexbox Failed in Safari

If you encountered a browser-specific issue that took multiple attempts to fix:

```python
# After fixing Safari issue
upsert_knowledge(
    title="Button Alignment Safari Quirk",
    content="Problem: Flexbox justify-content worked in Chrome/Firefox but failed in Safari 14. Tried: 1) Regular flexbox (failed), 2) Finally needed -webkit-flex prefix for Safari 14. Standard flexbox works in Safari 15+.",
    category="css_gotchas",
    tags='["css", "flexbox", "safari", "browser_compatibility"]',
    task_id="42"
)
```

**Then**: Log it in task before marking REVIEW:
```python
update_task(
    task_id="42",
    agent_id="claude",
    log_entry="Encountered Safari 14 compatibility issue with flexbox. Created knowledge item with workaround."
)
```

This transforms a simple task into a learning moment for the team!

---

## Anti-Pattern Examples

### ❌ Bad: No RA Tag
```python
# Just implemented without tagging the flexbox assumption
# Reviewer has no idea you made a choice
```

### ❌ Bad: Generic Tag
```python
add_ra_tag(
    task_id="42",
    ra_tag_text="#PATTERN_MOMENTUM: Using CSS",  # Too vague!
    agent_id="claude"
)
```

### ❌ Bad: Skipped REVIEW
```python
# Went straight from IN_PROGRESS to DONE
# Assumption never validated
```

### ✅ Good: Specific Tag + REVIEW
```python
add_ra_tag(
    task_id="42",
    ra_tag_text="#PATTERN_MOMENTUM: Using flexbox for alignment (standard pattern in this codebase)",
    agent_id="claude"
)

update_task_status(task_id="42", status="REVIEW", agent_id="claude")
```
