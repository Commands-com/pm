/**
 * UserPromptSubmit Hook - Pre-Execution Skill Activation
 *
 * Analyzes user prompts BEFORE Claude sees them and injects skill activation
 * reminders based on keyword matching, intent patterns, and file context.
 *
 * This ensures Claude automatically loads relevant skills instead of requiring
 * manual skill invocation every time.
 */

import * as fs from 'fs';
import * as path from 'path';

interface SkillRule {
  type: string;
  enforcement: string;
  priority: string;
  promptTriggers?: {
    keywords?: string[];
    intentPatterns?: string[];
  };
  fileTriggers?: {
    pathPatterns?: string[];
    contentPatterns?: string[];
  };
}

interface SkillRules {
  [skillName: string]: SkillRule;
}

/**
 * Load skill rules from configuration file
 */
function loadSkillRules(): SkillRules {
  try {
    const rulesPath = path.join(__dirname, 'skill-rules.json');
    const rulesContent = fs.readFileSync(rulesPath, 'utf-8');
    return JSON.parse(rulesContent);
  } catch (error) {
    console.error('Failed to load skill rules:', error);
    return {};
  }
}

/**
 * Check if prompt matches skill keywords
 */
function matchesKeywords(prompt: string, keywords: string[]): boolean {
  const lowerPrompt = prompt.toLowerCase();
  return keywords.some(keyword => lowerPrompt.includes(keyword.toLowerCase()));
}

/**
 * Check if prompt matches intent patterns (regex)
 */
function matchesIntentPatterns(prompt: string, patterns: string[]): boolean {
  return patterns.some(pattern => {
    try {
      const regex = new RegExp(pattern, 'i');
      return regex.test(prompt);
    } catch {
      return false;
    }
  });
}

/**
 * Analyze which skills should activate based on the prompt
 */
function analyzePromptForSkills(prompt: string, rules: SkillRules): string[] {
  const matchedSkills: string[] = [];

  for (const [skillName, rule] of Object.entries(rules)) {
    const triggers = rule.promptTriggers;
    if (!triggers) continue;

    // Check keywords
    if (triggers.keywords && matchesKeywords(prompt, triggers.keywords)) {
      matchedSkills.push(skillName);
      continue;
    }

    // Check intent patterns
    if (triggers.intentPatterns && matchesIntentPatterns(prompt, triggers.intentPatterns)) {
      matchedSkills.push(skillName);
    }
  }

  return matchedSkills;
}

/**
 * Format skill activation reminder for injection
 */
function formatSkillReminder(skills: string[], rules: SkillRules): string {
  if (skills.length === 0) return '';

  const lines = [
    '',
    '🎯 SKILL ACTIVATION CHECK',
    '━'.repeat(50),
    'Recommended Skills:'
  ];

  for (const skillName of skills) {
    const rule = rules[skillName];
    const priority = rule.priority === 'high' ? 'High Priority' : 'Medium Priority';
    lines.push(`  • ${skillName} (${priority})`);
  }

  lines.push('━'.repeat(50));
  lines.push('');

  return lines.join('\n');
}

/**
 * Main hook function - modifies the prompt before Claude sees it
 */
export default async function userPromptSubmitHook(params: {
  prompt: string;
}): Promise<{ prompt: string }> {
  const { prompt } = params;

  // Load skill rules
  const rules = loadSkillRules();
  if (Object.keys(rules).length === 0) {
    // No rules loaded, return original prompt
    return { prompt };
  }

  // Analyze prompt for skill matches
  const matchedSkills = analyzePromptForSkills(prompt, rules);

  if (matchedSkills.length === 0) {
    // No skills matched, return original prompt
    return { prompt };
  }

  // Format reminder and inject into prompt
  const reminder = formatSkillReminder(matchedSkills, rules);
  const modifiedPrompt = reminder + prompt;

  return { prompt: modifiedPrompt };
}
