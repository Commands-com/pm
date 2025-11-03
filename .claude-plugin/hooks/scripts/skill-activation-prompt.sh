#!/bin/bash
set -e

# CRITICAL: Consume stdin (hooks receive JSON via stdin)
hook_data=$(cat)

# Debug: Log that hook was called
echo "$(date): UserPromptSubmit hook called" >> /tmp/skill-activation-debug.log

# Extract user prompt
user_prompt=$(echo "$hook_data" | jq -r '.user_prompt // empty')

# Debug: Log the prompt
echo "$(date): User prompt: $user_prompt" >> /tmp/skill-activation-debug.log

# If no prompt, exit silently
if [[ -z "$user_prompt" ]]; then
    exit 0
fi

# Load skill rules
RULES_FILE="${CLAUDE_PLUGIN_ROOT}/hooks/skill-rules.json"
if [[ ! -f "$RULES_FILE" ]]; then
    exit 0
fi

# Simple keyword matching for skill activation
activate_skills=""

# Check ra-methodology triggers
if echo "$user_prompt" | grep -qiE "(task|epic|project|complexity|RA tag|assumption|create task|update task)"; then
    activate_skills="${activate_skills}ra-methodology "
fi

# Check pm-dashboard-dev triggers
if echo "$user_prompt" | grep -qiE "(MCP tool|FastAPI|endpoint|route|database|API|test|pytest)"; then
    activate_skills="${activate_skills}pm-dashboard-dev "
fi

# Check knowledge-management triggers
if echo "$user_prompt" | grep -qiE "(error|gotcha|took multiple|finally worked|trial and error|struggled)"; then
    activate_skills="${activate_skills}knowledge-management "
fi

# Check task-locking triggers
if echo "$user_prompt" | grep -qiE "(lock|atomic|race condition|concurrent|acquire lock|release lock)"; then
    activate_skills="${activate_skills}task-locking "
fi

# If skills should be activated, output suggestion
if [[ -n "$activate_skills" ]]; then
    cat << EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 SUGGESTED SKILLS FOR THIS REQUEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Detected relevant skills: $activate_skills

Consider using: /skill ${activate_skills%% }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF
fi

exit 0
