#!/bin/bash
# Show RA methodology reminders after response completion

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
