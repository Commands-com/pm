"""
RA instructions MCP tool.

Provides tool for retrieving RA methodology instructions with knowledge
context injection for agent guidance.
"""

import json
import logging
from typing import Optional

from .base import BaseTool
from ..ra_instructions import ra_instructions_manager

# Configure logging for instructions tool operations
logger = logging.getLogger(__name__)

class GetInstructionsTool(BaseTool):
    """
    MCP tool to retrieve RA methodology instructions text for clients with knowledge context injection.

    Provides either the full or concise instruction set along with version and
    last updated metadata. Automatically injects project/epic knowledge context
    when task context parameters are provided.
    """

    async def apply(
        self, 
        format: str = "concise", 
        project_id: Optional[str] = None,
        epic_id: Optional[str] = None,
        include_knowledge_context: Optional[str] = "true"
    ) -> str:
        """
        Get RA methodology instructions with optional knowledge context injection.

        Args:
            format: "full" or "concise" (default: "concise")
            project_id: Project ID for knowledge context (optional)
            epic_id: Epic ID for knowledge context (optional)
            include_knowledge_context: Whether to inject knowledge context (default: "true")

        Returns:
            JSON string including instructions text, metadata, and knowledge context
        """
        try:
            fmt = (format or "concise").strip().lower()
            if fmt not in ("full", "concise"):
                return self._format_error_response(
                    "Invalid format. Use 'full' or 'concise'",
                    valid_formats=["full", "concise"]
                )

            # Get base instructions
            if fmt == "full":
                instructions = ra_instructions_manager.get_full_instructions()
            else:
                instructions = ra_instructions_manager.get_concise_instructions()

            # Inject knowledge context if requested and project context is available
            knowledge_context = ""
            if include_knowledge_context and include_knowledge_context.lower() == "true":
                if project_id:
                    try:
                        parsed_project_id = int(project_id)
                        parsed_epic_id = None
                        if epic_id:
                            parsed_epic_id = int(epic_id)

                        knowledge_context = await get_task_knowledge_context(
                            self.db, 
                            project_id=parsed_project_id, 
                            epic_id=parsed_epic_id
                        )

                        if knowledge_context and "No knowledge" not in knowledge_context:
                            # Prepend knowledge context to instructions
                            instructions = f"{knowledge_context}\n\n---\n\n{instructions}"

                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid project/epic ID for knowledge context: {e}")

            return self._format_success_response(
                "Instructions retrieved" + (" with knowledge context" if knowledge_context else ""),
                instructions=instructions,
                format=fmt,
                version=ra_instructions_manager.version,
                last_updated=ra_instructions_manager.last_updated,
                knowledge_context_included=bool(knowledge_context and "No knowledge" not in knowledge_context),
                context_source={
                    "project_id": project_id,
                    "epic_id": epic_id
                } if project_id else None
            )
        except Exception as e:
            logger.error(f"Failed to get instructions: {e}")
            return self._format_error_response(
                "Failed to get instructions",
                error_details=str(e)
            )



async def get_task_knowledge_context(
    database: 'TaskDatabase', 
    project_id: Optional[int] = None, 
    epic_id: Optional[int] = None,
    max_words: int = 500
) -> str:
    """
    Retrieve and format knowledge context for agent task instructions.
    
    Args:
        database: TaskDatabase instance
        project_id: Project ID for project-level knowledge
        epic_id: Epic ID for epic-level knowledge 
        max_words: Maximum word count for context (default: 500)
        
    Returns:
        Formatted knowledge context string for agent instructions
    """
    try:
        if not project_id:
            return "No knowledge context available - missing project information."
        
        # Get project-level knowledge
        project_knowledge = database.get_knowledge(
            project_id=project_id,
            limit=10,
            include_inactive=False
        )
        
        # Get epic-level knowledge if epic_id is provided
        epic_knowledge = []
        if epic_id:
            epic_knowledge = database.get_knowledge(
                project_id=project_id,
                epic_id=epic_id,
                limit=10,
                include_inactive=False
            )
        
        # Format knowledge into structured context
        context_parts = []
        
        if project_knowledge or epic_knowledge:
            context_parts.append("## Project Knowledge Context")
            
            # Format project-level knowledge
            if project_knowledge:
                context_parts.append("### Project-Level Knowledge:")
                for item in project_knowledge[:3]:  # Limit to top 3 items
                    title = item.get('title', 'Untitled')
                    content = item.get('content', '')
                    # Truncate content to prevent bloat
                    if len(content) > 100:
                        content = content[:97] + "..."
                    context_parts.append(f"• **{title}**: {content}")
            
            # Format epic-level knowledge
            if epic_knowledge:
                context_parts.append("\n### Epic-Level Knowledge:")
                for item in epic_knowledge[:2]:  # Limit to top 2 items
                    title = item.get('title', 'Untitled')
                    content = item.get('content', '')
                    # Truncate content to prevent bloat
                    if len(content) > 100:
                        content = content[:97] + "..."
                    context_parts.append(f"• **{title}**: {content}")
            
            # Add key decisions and gotchas if available
            decisions = []
            gotchas = []
            
            all_knowledge = project_knowledge + epic_knowledge
            for item in all_knowledge:
                category = item.get('category', '').lower()
                if 'decision' in category:
                    decisions.append(item.get('title', ''))
                elif 'gotcha' in category or 'warning' in category:
                    gotchas.append(item.get('title', ''))
            
            if decisions:
                context_parts.append("\n### Key Decisions:")
                for decision in decisions[:3]:
                    context_parts.append(f"• {decision}")
            
            if gotchas:
                context_parts.append("\n### Important Gotchas:")
                for gotcha in gotchas[:3]:
                    context_parts.append(f"• {gotcha}")
            
            context = "\n".join(context_parts)
            
            # Enforce word limit
            words = context.split()
            if len(words) > max_words:
                truncated = " ".join(words[:max_words])
                context = truncated + f"\n\n[Context truncated at {max_words} words]"
            
            return context
        else:
            return "No knowledge available for this project/epic context."
            
    except Exception as e:
        logger.error(f"Failed to get task knowledge context: {e}")
