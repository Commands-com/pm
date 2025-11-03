#!/bin/bash
set -e

# CRITICAL: Consume stdin (hooks receive JSON via stdin)
hook_data=$(cat)

# Extract session info if needed
session_id=$(echo "$hook_data" | jq -r '.session_id // empty')

# Output reminder to Claude
cat << 'EOF'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 RA AWARENESS SELF-CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Did you implement any code changes?
  ✓ Add RA tags for assumptions made
  ✓ Update task status to REVIEW if RA tags were used
  ✓ Remember: ALL implementations with RA tags → REVIEW before DONE

Use: add_ra_tag(task_id="X", ra_tag_text="#TAG: description", agent_id="claude")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

exit 0
