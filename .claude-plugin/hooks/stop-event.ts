/**
 * Stop Event Hook - Post-Execution Quality Gates
 *
 * Runs after Claude finishes responding to perform automatic quality checks:
 * 1. Build Checker - Runs mypy, black, pytest on modified files
 * 2. RA Tag Reminder - Reminds about RA tagging for task implementations
 * 3. Knowledge Capture Reminder - Suggests capturing trial-and-error solutions
 *
 * Implements "#NoMessLeftBehind" - catches errors immediately instead of
 * letting them accumulate.
 */

import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

interface EditLog {
  entries: Array<{
    timestamp: string;
    file: string;
    module: string;
    operation: string;
  }>;
}

const EDIT_LOG_PATH = path.join(__dirname, '.edit-log.json');

/**
 * Load and clear edit log
 */
function loadAndClearEditLog(): EditLog {
  try {
    if (fs.existsSync(EDIT_LOG_PATH)) {
      const content = fs.readFileSync(EDIT_LOG_PATH, 'utf-8');
      const log: EditLog = JSON.parse(content);

      // Clear the log for next session
      fs.writeFileSync(EDIT_LOG_PATH, JSON.stringify({ entries: [] }, null, 2));

      return log;
    }
  } catch (error) {
    console.error('Failed to load edit log:', error);
  }
  return { entries: [] };
}

/**
 * Get unique modules that were modified
 */
function getModifiedModules(log: EditLog): Set<string> {
  const modules = new Set<string>();
  for (const entry of log.entries) {
    modules.add(entry.module);
  }
  return modules;
}

/**
 * Run build checks for Python files
 */
function runPythonChecks(): { errors: number; output: string } {
  let errors = 0;
  let output = '';

  try {
    // Run mypy type checking
    const mypyOutput = execSync('mypy src/', { encoding: 'utf-8', cwd: process.cwd() });
    output += `\n📊 Type Checking (mypy):\n${mypyOutput}`;
  } catch (error: any) {
    errors++;
    output += `\n❌ Type Checking Errors:\n${error.stdout || error.message}`;
  }

  try {
    // Run black formatting check
    const blackOutput = execSync('black --check .', { encoding: 'utf-8', cwd: process.cwd() });
    output += `\n✅ Code Formatting (black): OK`;
  } catch (error: any) {
    errors++;
    output += `\n⚠️  Code Formatting Issues:\n${error.stdout || error.message}`;
  }

  return { errors, output };
}

/**
 * Check if task-related files were modified
 */
function taskRelatedFilesModified(log: EditLog): boolean {
  const taskRelatedPatterns = [
    'tools_lib/tasks.py',
    'tools_lib/projects.py',
    'database/tasks.py',
    'mcp_server.py'
  ];

  return log.entries.some(entry =>
    taskRelatedPatterns.some(pattern => entry.file.includes(pattern))
  );
}

/**
 * Format RA tag reminder
 */
function formatRATagReminder(): string {
  return `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 RA AWARENESS SELF-CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  Task Implementation Detected

   ❓ Did you add RA tags for assumptions made?
   ❓ Did you update task status to REVIEW if RA tags were used?

   💡 Remember: ALL implementations with RA tags → REVIEW before DONE

   Use: add_ra_tag(task_id="X", ra_tag_text="#TAG: description", agent_id="claude")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
}

/**
 * Format knowledge capture reminder
 */
function formatKnowledgeReminder(): string {
  return `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 KNOWLEDGE CAPTURE CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This solution may have been non-obvious. Consider capturing:
  • What didn't work and why
  • What finally worked
  • Non-obvious gotchas discovered

Use: upsert_knowledge(title="...", content="...", category="gotchas", task_id="X")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
}

/**
 * Main hook function - runs quality checks
 */
export default async function stopEventHook(): Promise<void> {
  // Load edit log
  const log = loadAndClearEditLog();

  if (log.entries.length === 0) {
    // No files were edited, nothing to check
    return;
  }

  const modules = getModifiedModules(log);
  let output = '';

  // Build Checker
  if (modules.has('task_manager') || modules.has('database') || modules.has('tools_lib') || modules.has('routers')) {
    console.log('\n🔍 Running build checks on modified Python files...\n');

    const { errors, output: checkOutput } = runPythonChecks();

    output += checkOutput;

    if (errors > 0) {
      if (errors < 5) {
        console.log(output);
        console.log(`\n⚠️  Found ${errors} issue(s). Please review and fix.`);
      } else {
        const scriptsPath = path.join(__dirname, '..', 'skills', 'pm-dashboard-dev', 'scripts', 'run-full-tests.sh');
        console.log(`\n❌ Found ${errors} issues. Consider running: bash ${scriptsPath}`);
      }
    } else {
      console.log('✅ All build checks passed!');
    }
  }

  // RA Tag Reminder
  if (taskRelatedFilesModified(log)) {
    console.log(formatRATagReminder());
  }

  // Knowledge Capture Reminder (heuristic - show occasionally)
  // In a more sophisticated version, this would analyze conversation history
  // for trial-and-error patterns. For now, show for any significant edits.
  if (log.entries.length >= 3 && modules.size >= 2) {
    console.log(formatKnowledgeReminder());
  }
}
