/**
 * Post-Tool-Use Hook - File Edit Tracking
 *
 * Runs after every Edit/Write/MultiEdit operation to track which files
 * were modified. This builds a list for the Stop hook to process with
 * build checks and quality gates.
 *
 * Implements the "#NoMessLeftBehind" philosophy by ensuring all edits
 * are tracked for later verification.
 */

import * as fs from 'fs';
import * as path from 'path';

interface EditLogEntry {
  timestamp: string;
  file: string;
  module: string;
  operation: string;
}

interface EditLog {
  entries: EditLogEntry[];
}

const EDIT_LOG_PATH = path.join(process.cwd(), 'hooks', '.edit-log.json');

/**
 * Load existing edit log
 */
function loadEditLog(): EditLog {
  try {
    if (fs.existsSync(EDIT_LOG_PATH)) {
      const content = fs.readFileSync(EDIT_LOG_PATH, 'utf-8');
      return JSON.parse(content);
    }
  } catch (error) {
    console.error('Failed to load edit log:', error);
  }
  return { entries: [] };
}

/**
 * Save edit log to disk
 */
function saveEditLog(log: EditLog): void {
  try {
    fs.writeFileSync(EDIT_LOG_PATH, JSON.stringify(log, null, 2));
  } catch (error) {
    console.error('Failed to save edit log:', error);
  }
}

/**
 * Determine which module a file belongs to
 */
function getModuleName(filePath: string): string {
  if (filePath.includes('src/task_manager/')) {
    if (filePath.includes('database/')) return 'database';
    if (filePath.includes('tools_lib/')) return 'tools_lib';
    if (filePath.includes('routers/')) return 'routers';
    if (filePath.includes('static/')) return 'frontend';
    return 'task_manager';
  }
  if (filePath.includes('test/')) return 'tests';
  if (filePath.includes('skills/')) return 'skills';
  if (filePath.includes('hooks/')) return 'hooks';
  return 'other';
}

/**
 * Main hook function - logs file edits
 */
export default async function postToolUseHook(params: {
  tool: string;
  args: any;
  result: any;
}): Promise<void> {
  const { tool, args } = params;

  // Only track Edit, Write, and MultiEdit operations
  if (!['Edit', 'Write', 'MultiEdit'].includes(tool)) {
    return;
  }

  // Extract file path from args
  let filePath: string | undefined;
  if (tool === 'Edit' || tool === 'Write') {
    filePath = args.file_path;
  } else if (tool === 'MultiEdit' && args.edits && args.edits.length > 0) {
    // For MultiEdit, log all files
    const log = loadEditLog();
    for (const edit of args.edits) {
      const entry: EditLogEntry = {
        timestamp: new Date().toISOString(),
        file: edit.file_path,
        module: getModuleName(edit.file_path),
        operation: 'multi-edit'
      };
      log.entries.push(entry);
    }
    saveEditLog(log);
    return;
  }

  if (!filePath) {
    return;
  }

  // Load existing log
  const log = loadEditLog();

  // Add new entry
  const entry: EditLogEntry = {
    timestamp: new Date().toISOString(),
    file: filePath,
    module: getModuleName(filePath),
    operation: tool.toLowerCase()
  };

  log.entries.push(entry);

  // Save updated log
  saveEditLog(log);
}
