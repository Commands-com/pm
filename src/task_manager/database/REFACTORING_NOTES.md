# Database Refactoring Notes

## Status
- ✅ connection.py (574 lines) - Schema and connection management
- ✅ locks.py (209 lines) - Lock operations
- ✅ sessions.py (184 lines) - Session and event management  
- ✅ projects.py (615 lines) - Project and epic operations
- 🔄 tasks.py - IN PROGRESS - Task operations (largest module)
- ⏳ knowledge.py - PENDING - Knowledge management
- ⏳ __init__.py - PENDING - TaskDatabase wrapper

## Tasks.py Methods Needed (23 total)
1. create_task
2. get_task_details
3. get_task_by_id
4. get_available_tasks
5. get_all_tasks
6. list_tasks_filtered
7. update_task_status
8. update_task_ra_fields
9. add_task_log
10. get_task_logs
11. get_latest_task_log
12. _process_ra_tags_with_ids
13. _extract_tag_type
14. create_task_with_ra_metadata
15. add_task_log_entry
16. get_task_details_with_relations
17. get_task_logs_paginated
18. resolve_task_dependencies
19. update_task_atomic
20. list_tasks_with_context_dashboard
21. create_task_with_project_context
22. delete_task
23. cleanup_orphaned_tasks

## Knowledge.py Methods Needed (4 total)
1. get_knowledge
2. upsert_knowledge
3. append_knowledge_log
4. get_knowledge_logs
5. delete_knowledge_item

## Approach
Given the size (1500+ lines for tasks.py), we're creating a comprehensive
import wrapper in __init__.py that maintains full backward compatibility.
