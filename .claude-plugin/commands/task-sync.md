---
description: "Update GitHub issues with detailed progress from local task execution"
allowed-tools: Read, Write, Bash
---

# Sync Task Progress to GitHub

Update GitHub issues with detailed progress from local task execution.

## Usage
```
/pm:task-sync <task-file>
```
Example: `/pm:task-sync 001-user-auth`

## Instructions

You are syncing progress for task: **$ARGUMENTS**

## MCP Integration (preferred)
Reflect sync activity in MCP so task history remains canonical.

- Full name: mcp__project-manager-mcp__list_tasks — Resolve task by name
- Full name: mcp__project-manager-mcp__get_task_details — Retrieve current status/metadata
- Full name: mcp__project-manager-mcp__update_task — Append sync logs and GitHub issue linkage

Recommended flow:
1) Resolve the task via `...__list_tasks` and confirm with `...__get_task_details`.
2) After posting to GitHub, call `...__update_task(log_entry="Synced progress to GH issue #<n>", ra_metadata.github.issue_number, ra_metadata.github.url)` to record the linkage in MCP.
3) Optionally reflect local progress percentages into `ra_metadata.progress`.

### 1. Validate Task and Progress
- Check if `.pm/tasks/$ARGUMENTS.md` exists
- Check if `.pm/tasks/$ARGUMENTS-progress.md` exists
- Read current task status and progress details
- If no progress file: "⚠️ No progress tracked. Start task first: /pm:task-start $ARGUMENTS"

### 2. Gather Progress Information
From the task and progress files, collect:
- Current completion percentage
- Files created/modified
- Acceptance criteria status
- Test results
- Any issues or blockers encountered
- Time spent vs. estimated

### 3. Check GitHub Integration
Determine how to sync to GitHub:

#### Option A: GitHub CLI Available
```bash
# Check if gh CLI is available
if command -v gh &> /dev/null; then
  echo "✅ GitHub CLI available"
else
  echo "❌ GitHub CLI not found"
fi
```

#### Option B: Manual Issue Template
If no GitHub CLI, generate issue update template for manual posting.

### 4. Find or Create GitHub Issue
If using GitHub CLI:
```bash
# Look for existing issue with task title
gh issue list --search "in:title $ARGUMENTS" --json number,title,state

# If no issue exists, create one
if [ $? -ne 0 ]; then
  gh issue create --title "Task: $ARGUMENTS" --body "$(cat issue_template)"
fi
```

### 5. Format Progress Update
Create comprehensive progress update:

```markdown
## 🔄 Progress Update - {current_date}

### ⏱️ Timeline
- **Started**: {start_date}
- **Last Update**: {current_date}
- **Estimated Completion**: {completion_estimate}

### ✅ Completed Work
{list completed items from acceptance criteria}

### 🔄 In Progress
{current work items from progress log}

### 📁 Files Modified
{list of files created/modified with brief description}

### 🧪 Testing Status
- **Unit Tests**: {pass_count}/{total_count} passing
- **Manual Testing**: {status}
- **Integration Tests**: {status}

### 📊 Acceptance Criteria Status
- ✅ {completed_criterion_1}
- 🔄 {in_progress_criterion_2}
- ⏸️ {blocked_criterion_3}
- ⏳ {pending_criterion_4}

### 🚀 Next Steps
{planned next actions from progress log}

### ⚠️ Issues & Blockers
{any current blockers or technical issues}

### 💻 Recent Changes
{git commit summaries or file change descriptions}

---
*Progress: {completion_percentage}% | Synced from .pm/tasks/$ARGUMENTS-progress.md*
```

### 6. Post Update to GitHub
#### Via GitHub CLI:
```bash
# Post as comment to existing issue
gh issue comment {issue_number} --body-file update_content.md

# Update issue labels based on status
case "$status" in
  "in_progress") gh issue edit {issue_number} --add-label "in-progress" ;;
  "blocked") gh issue edit {issue_number} --add-label "blocked" ;;
  "completed") gh issue edit {issue_number} --add-label "completed" --state closed ;;
esac
```

#### Manual Template:
If no GitHub CLI, provide formatted update for manual posting:
```
📋 Manual GitHub Update:
  
Copy the following content to GitHub issue #{issue_number}:

{formatted_progress_update}

Suggested labels: {status_labels}
```

### 7. Update Local Tracking
Update the progress file with sync information:
```yaml
---
last_sync: {current_date}
github_issue: {issue_number}
sync_status: success
---
```

### 8. Handle Task Completion
If task status is "completed":

```markdown
## ✅ Task Completed - {completion_date}

### 🎯 All Acceptance Criteria Met
- ✅ {criterion_1}
- ✅ {criterion_2}
- ✅ {criterion_3}

### 📦 Deliverables
- {deliverable_1} ({file_location})
- {deliverable_2} ({file_location})

### 🧪 Testing Summary
- **Unit Tests**: All {count} tests passing
- **Integration Tests**: All scenarios verified
- **Manual Testing**: Complete checklist validated

### 📚 Documentation
- Code documentation: Updated
- README updates: Complete
- API documentation: Current

### 🔗 Related Files
{list all files created/modified with descriptions}

This task is ready for review and integration.

---
*Task completed: 100% | Final sync at {timestamp}*
```

Close the GitHub issue and update labels to "completed".

### 9. Success Confirmation
```
✅ Task progress synced to GitHub!

📊 Sync Summary:
  ✓ Progress updated in GitHub issue #{issue_number}
  ✓ {completion_percentage}% completion reported
  ✓ {files_count} files documented
  ✓ Current status: {status}

🔗 GitHub Issue: {github_url}

📁 Local Files Updated:
  .pm/tasks/$ARGUMENTS-progress.md (sync timestamp)
  
🚀 Next Steps:
  - Continue task work if not complete
  - Review GitHub issue for team feedback
  - Sync again after significant progress: /pm:task-sync $ARGUMENTS
```

### 10. Error Handling
Handle common issues:
- GitHub authentication problems
- Network connectivity issues
- Issue not found or access denied
- Rate limiting

Provide fallback manual sync options when automated sync fails.

This command ensures transparent progress tracking and team visibility into detailed task execution!
