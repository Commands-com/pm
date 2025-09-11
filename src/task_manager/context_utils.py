"""
Context Detection Utilities for RA Tag Creation

Provides automatic detection of file, git, and development context for RA tag creation
with zero additional effort from developers. Handles errors gracefully and provides
fallback mechanisms when detection fails.

Key Features:
- File path and line number detection from development environment
- Git branch and commit extraction with error handling
- Programming language detection from file extensions
- Symbol context extraction using regex patterns
- Performance optimized with <200ms execution times
"""

import os
import subprocess
import re
import logging
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Language detection mapping
LANGUAGE_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript', 
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.jsx': 'javascript',
    '.java': 'java',
    '.cpp': 'cpp',
    '.c': 'c',
    '.h': 'c',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.go': 'go',
    '.rs': 'rust',
    '.php': 'php',
    '.rb': 'ruby',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.r': 'r',
    '.sql': 'sql',
    '.sh': 'bash',
    '.ps1': 'powershell',
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.less': 'less',
    '.json': 'json',
    '.xml': 'xml',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.md': 'markdown',
    '.dockerfile': 'dockerfile'
}

# Symbol extraction patterns for common languages
SYMBOL_PATTERNS = {
    'python': [
        r'^\s*def\s+(\w+)\s*\(',  # functions
        r'^\s*class\s+(\w+)\s*[\(:]',  # classes
        r'^\s*async\s+def\s+(\w+)\s*\('  # async functions
    ],
    'javascript': [
        r'function\s+(\w+)\s*\(',  # function declarations
        r'const\s+(\w+)\s*=\s*\(',  # const functions
        r'let\s+(\w+)\s*=\s*\(',   # let functions
        r'var\s+(\w+)\s*=\s*\(',   # var functions
        r'(\w+)\s*:\s*function',    # object methods
        r'(\w+)\s*\(\s*.*?\s*\)\s*=>',  # arrow functions
    ],
    'typescript': [
        r'function\s+(\w+)\s*\(',
        r'const\s+(\w+)\s*=\s*\(',
        r'let\s+(\w+)\s*=\s*\(',
        r'(\w+)\s*:\s*function',
        r'(\w+)\s*\(\s*.*?\s*\)\s*=>',
        r'export\s+function\s+(\w+)',
        r'public\s+(\w+)\s*\(',  # class methods
        r'private\s+(\w+)\s*\(',
    ],
    'java': [
        r'public\s+\w+\s+(\w+)\s*\(',  # public methods
        r'private\s+\w+\s+(\w+)\s*\(',  # private methods
        r'protected\s+\w+\s+(\w+)\s*\(',  # protected methods
        r'class\s+(\w+)\s*[{<]',  # classes
    ],
    'go': [
        r'func\s+(\w+)\s*\(',  # functions
        r'func\s+\(\w+\s+\*?\w+\)\s+(\w+)\s*\(',  # methods
    ]
}


def detect_file_context(file_path: Optional[str] = None, line_number: Optional[int] = None) -> Dict[str, Any]:
    """
    Detect and validate file context information.
    
    Args:
        file_path: Optional file path, will attempt auto-detection if None
        line_number: Optional line number for context
        
    Returns:
        Dict with file context information, empty dict on errors
    """
    context = {}
    
    try:
        # Use provided file path or attempt detection
        resolved_path = file_path
        
        if not resolved_path:
            # Try to detect from environment variables or current directory
            resolved_path = _detect_current_file()
        
        if resolved_path:
            # Convert to relative path from project root if possible
            context['file_path'] = _get_relative_path(resolved_path)
            
            # Detect programming language
            language = detect_language(resolved_path)
            if language:
                context['language'] = language
        
        # Include line number if provided
        if line_number is not None and isinstance(line_number, int) and line_number > 0:
            context['line_number'] = line_number
            
            # Extract symbol context if we have both file and line
            if resolved_path and os.path.exists(resolved_path):
                symbol = extract_symbol_context(resolved_path, line_number)
                if symbol:
                    context['symbol_context'] = symbol
    
    except Exception as e:
        logger.warning(f"File context detection failed: {e}")
    
    return context


def get_git_context() -> Dict[str, Optional[str]]:
    """
    Extract git branch and commit from current working directory.
    
    Returns:
        Dict with git_branch and git_commit, None values on errors
    """
    context = {'git_branch': None, 'git_commit': None}
    
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return context
        
        # Get current branch
        try:
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if branch_result.returncode == 0 and branch_result.stdout.strip():
                context['git_branch'] = branch_result.stdout.strip()
        except Exception as e:
            logger.debug(f"Git branch detection failed: {e}")
        
        # Get current commit hash (short form)
        try:
            commit_result = subprocess.run(
                ['git', 'rev-parse', '--short=8', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if commit_result.returncode == 0 and commit_result.stdout.strip():
                context['git_commit'] = commit_result.stdout.strip()
        except Exception as e:
            logger.debug(f"Git commit detection failed: {e}")
    
    except Exception as e:
        logger.warning(f"Git context detection failed: {e}")
    
    return context


def detect_language(file_path: str) -> Optional[str]:
    """
    Detect programming language from file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Language name or None if not recognized
    """
    if not file_path:
        return None
    
    try:
        # Get file extension
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # Check for special cases
        if path.name.lower() == 'dockerfile':
            return 'dockerfile'
        
        return LANGUAGE_EXTENSIONS.get(extension)
    
    except Exception as e:
        logger.debug(f"Language detection failed for {file_path}: {e}")
        return None


def extract_symbol_context(file_path: str, line_number: int) -> Optional[str]:
    """
    Extract function/method name from file at specific line using regex patterns.
    
    Args:
        file_path: Path to the source file
        line_number: Line number to search around
        
    Returns:
        Symbol name (function/method/class) or None if not found
    """
    if not file_path or not os.path.exists(file_path) or line_number <= 0:
        return None
    
    try:
        language = detect_language(file_path)
        if not language or language not in SYMBOL_PATTERNS:
            return None
        
        patterns = SYMBOL_PATTERNS[language]
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if line_number > len(lines):
            return None
        
        # Search backwards from the target line to find the containing symbol
        search_start = max(0, line_number - 20)  # Search up to 20 lines back
        search_lines = lines[search_start:line_number]
        
        # Reverse search to find the most recent symbol definition
        for i in range(len(search_lines) - 1, -1, -1):
            line = search_lines[i]
            
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    return match.group(1)
    
    except Exception as e:
        logger.debug(f"Symbol extraction failed for {file_path}:{line_number}: {e}")
    
    return None


def validate_context(context_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize context information.
    
    Args:
        context_dict: Raw context dictionary
        
    Returns:
        Validated and sanitized context dictionary
    """
    validated = {}
    
    # Validate file_path
    if 'file_path' in context_dict:
        file_path = context_dict['file_path']
        if isinstance(file_path, str) and file_path.strip():
            validated['file_path'] = file_path.strip()
    
    # Validate line_number
    if 'line_number' in context_dict:
        line_num = context_dict['line_number']
        if isinstance(line_num, int) and line_num > 0:
            validated['line_number'] = line_num
    
    # Validate git context
    for git_field in ['git_branch', 'git_commit']:
        if git_field in context_dict:
            value = context_dict[git_field]
            if isinstance(value, str) and value.strip():
                validated[git_field] = value.strip()
    
    # Validate language
    if 'language' in context_dict:
        language = context_dict['language']
        if isinstance(language, str) and language.strip():
            validated['language'] = language.strip().lower()
    
    # Validate symbol_context
    if 'symbol_context' in context_dict:
        symbol = context_dict['symbol_context']
        if isinstance(symbol, str) and symbol.strip():
            validated['symbol_context'] = symbol.strip()
    
    # Validate code_snippet
    if 'code_snippet' in context_dict:
        snippet = context_dict['code_snippet']
        if isinstance(snippet, str) and snippet.strip():
            validated['code_snippet'] = snippet.strip()
    
    return validated


def _detect_current_file() -> Optional[str]:
    """
    Attempt to detect current file from environment variables.
    
    Returns:
        File path if detected, None otherwise
    """
    # Check common environment variables used by editors/IDEs
    env_vars = ['EDITOR_FILE', 'CURRENT_FILE', 'VIM_FILE', 'VS_FILE']
    
    for var in env_vars:
        file_path = os.environ.get(var)
        if file_path and os.path.exists(file_path):
            return file_path
    
    return None


def _get_relative_path(file_path: str) -> str:
    """
    Convert absolute path to relative path from git root or current directory.
    
    Args:
        file_path: Absolute or relative file path
        
    Returns:
        Relative path string
    """
    try:
        path = Path(file_path)
        
        # If it's already relative, return as-is
        if not path.is_absolute():
            return str(path)
        
        # Try to get relative path from git root
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                git_root = Path(result.stdout.strip())
                try:
                    return str(path.relative_to(git_root))
                except ValueError:
                    pass  # Path is not under git root
        except Exception:
            pass  # Git command failed
        
        # Fall back to relative path from current directory
        try:
            return str(path.relative_to(Path.cwd()))
        except ValueError:
            # If not under current directory, return just the filename
            return path.name
    
    except Exception:
        return str(file_path)


def create_enriched_context(
    file_path: Optional[str] = None,
    line_number: Optional[int] = None,
    code_snippet: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a complete context dictionary with all available information.
    
    Args:
        file_path: Optional file path
        line_number: Optional line number
        code_snippet: Optional code snippet
        
    Returns:
        Complete context dictionary with all detected information
    """
    # Detect file context
    file_context = detect_file_context(file_path, line_number)
    
    # Detect git context
    git_context = get_git_context()
    
    # Combine all context
    complete_context = {}
    complete_context.update(file_context)
    complete_context.update(git_context)
    
    # Add code snippet if provided
    if code_snippet:
        complete_context['code_snippet'] = code_snippet
    
    # Validate and return
    return validate_context(complete_context)