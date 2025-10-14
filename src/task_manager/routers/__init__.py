"""
FastAPI Routers for Project Manager API

Organized router modules for better API structure and maintainability.
"""

from .health import router as health_router
from .board import router as board_router
from .tasks import router as tasks_router
from .projects import router as projects_router
from .epics import router as epics_router
from .knowledge import router as knowledge_router
from .planning import router as planning_router

__all__ = [
    'health_router',
    'board_router',
    'tasks_router',
    'projects_router',
    'epics_router',
    'knowledge_router',
    'planning_router',
]
