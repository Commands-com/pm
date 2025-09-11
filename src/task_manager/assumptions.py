"""
Assumption Intelligence REST API Endpoints

Provides three endpoints for assumption validation analytics:
- /api/assumptions/insights - Dashboard analytics with success rates and trends
- /api/assumptions/recent - Recent validation activities with pagination
- /api/assumptions/tag-types - Available RA tag types for filtering

Features performance optimization with caching, indexed database queries,
and integration with RA tag normalization utilities.
"""

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from .database import TaskDatabase
from .ra_tag_utils import normalize_ra_tag, parse_ra_tag_list, get_category_stats
from .models import (
    InsightsSummary,
    RecentValidationsResponse,
    TagTypesResponse,
    ValidationExample,
    RecentValidation,
    TagTypeInfo,
    create_error_response,
)

# Router for assumption intelligence endpoints
router = APIRouter(prefix="/api/assumptions", tags=["assumptions"])

# Simple in-memory cache with 5-minute TTL as specified in requirements
# #COMPLETION_DRIVE_IMPL: Using simple dict-based cache for MVP, Redis alternative available if scaling needed
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def get_database() -> TaskDatabase:
    """Dependency injection for database instance."""
    # Import the main dependency function to ensure consistency
    from .api import get_database as api_get_database
    return api_get_database()


def _get_cache_key(endpoint: str, **params) -> str:
    """Generate cache key from endpoint and parameters."""
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
    return f"{endpoint}?{param_str}" if param_str else endpoint


def _get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached response if still valid."""
    if cache_key in _cache:
        cached = _cache[cache_key]
        if time.time() - cached["timestamp"] < CACHE_TTL_SECONDS:
            return cached["data"]
        else:
            # Remove expired cache entry
            del _cache[cache_key]
    return None


def _cache_response(cache_key: str, data: Dict[str, Any]) -> None:
    """Cache response data with timestamp."""
    _cache[cache_key] = {"data": data, "timestamp": time.time()}


def _calculate_success_rate(outcome_counts: Dict[str, int]) -> float:
    """Calculate success rate with partial validations weighted at 0.5."""
    validated = outcome_counts.get("validated", 0)
    rejected = outcome_counts.get("rejected", 0)
    partial = outcome_counts.get("partial", 0)

    total = validated + rejected + partial
    if total == 0:
        return 0.0

    # Success rate: validated + (partial * 0.5) / total
    # #COMPLETION_DRIVE_IMPL: Partial validations weighted at 0.5 per task requirements
    success_score = validated + (partial * 0.5)
    return round(success_score / total, 3)


@router.get("/insights", response_model=InsightsSummary)
async def get_assumption_insights(
    db: TaskDatabase = Depends(get_database),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    epic_id: Optional[int] = Query(None, description="Filter by epic ID"),
    ra_tag_type: Optional[str] = Query(None, description="Filter by normalized RA tag type"),
    since: Optional[str] = Query(
        None, description="ISO timestamp - only validations after this time"
    ),
    limit: int = Query(10, ge=1, le=100, description="Number of recent examples to include"),
) -> InsightsSummary:
    """
    Get assumption validation insights with success rates, breakdowns, and recent examples.

    Returns aggregated statistics including:
    - Total validation count and success rate (with partial validations at 0.5 weight)
    - Breakdown by outcome (validated/rejected/partial)
    - Breakdown by normalized RA tag type using RA utilities
    - Recent validation examples with task context
    - Cached for 5 minutes for performance optimization
    """
    try:
        # Check cache first for performance
        cache_key = _get_cache_key(
            "insights",
            project_id=project_id,
            epic_id=epic_id,
            ra_tag_type=ra_tag_type,
            since=since,
            limit=limit,
        )
        cached_response = _get_cached_response(cache_key)
        if cached_response:
            return InsightsSummary(**cached_response)

        # Build query with performance-optimized indexes
        base_query = """
            SELECT av.id, av.task_id, av.ra_tag_id, av.outcome, av.confidence, 
                   av.validator_id, av.validated_at, av.notes, av.project_id, av.epic_id,
                   t.name as task_name, t.ra_tags
            FROM assumption_validations av
            JOIN tasks t ON av.task_id = t.id
        """

        conditions = []
        params = []

        # Only filter by project_id if it's a positive integer (not 0 or negative)
        if project_id is not None and project_id > 0:
            conditions.append("av.project_id = ?")
            params.append(project_id)

        # Only filter by epic_id if it's a positive integer (not 0 or negative)
        if epic_id is not None and epic_id > 0:
            conditions.append("av.epic_id = ?")
            params.append(epic_id)

        if since:
            conditions.append("av.validated_at >= ?")
            params.append(since)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        order_clause = " ORDER BY av.validated_at DESC"

        query = base_query + where_clause + order_clause

        # Execute optimized query using database indexes
        with db._connection_lock:
            cursor = db._connection.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        if not rows:
            # Return empty insights response
            empty_insights = InsightsSummary(
                total_validations=0,
                success_rate=0.0,
                outcome_breakdown={},
                tag_type_breakdown={},
                recent_examples=[],
                cache_timestamp=datetime.now(timezone.utc).isoformat(),
            )
            _cache_response(cache_key, empty_insights.model_dump())
            return empty_insights

        # Process results with RA tag normalization
        outcome_counts = defaultdict(int)
        tag_type_counts = defaultdict(int)
        all_validations = []

        for row in rows:
            # Extract RA tag details from task's ra_tags JSON
            ra_tag_id = row[2]
            ra_tags_json = row[11]  # t.ra_tags
            extracted_ra_tag_type = "UNKNOWN"
            ra_tag_text = "Unknown tag"
            
            if ra_tags_json:
                try:
                    ra_tags = json.loads(ra_tags_json)
                    for tag in ra_tags:
                        if tag.get('id') == ra_tag_id:
                            extracted_ra_tag_type = tag.get('type', 'UNKNOWN')
                            ra_tag_text = tag.get('text', 'Unknown tag')
                            break
                except (json.JSONDecodeError, TypeError):
                    pass
            
            validation_data = {
                "id": row[0],
                "task_id": row[1],
                "ra_tag_id": ra_tag_id,
                "ra_tag": extracted_ra_tag_type,
                "ra_tag_text": ra_tag_text,
                "outcome": row[3],
                "confidence": row[4],
                "validator_id": row[5],
                "validated_at": row[6],
                "notes": row[7],
                "task_name": row[10],
            }
            all_validations.append(validation_data)

            # Count outcomes
            outcome_counts[row[3]] += 1

            # Use the actual RA tag type instead of normalized for better display
            tag_type_counts[extracted_ra_tag_type] += 1

        # Filter by normalized tag type if specified
        if ra_tag_type:
            filtered_validations = []
            for validation in all_validations:
                normalized_type, _ = normalize_ra_tag(validation["ra_tag"])
                if normalized_type == ra_tag_type:
                    filtered_validations.append(validation)

            # Recalculate counts for filtered results
            if filtered_validations:
                outcome_counts = defaultdict(int)
                for validation in filtered_validations:
                    outcome_counts[validation["outcome"]] += 1
                all_validations = filtered_validations
            else:
                all_validations = []
                outcome_counts = defaultdict(int)

        # Calculate success rate with partial weighting
        success_rate = _calculate_success_rate(dict(outcome_counts))

        # Prepare recent examples (limited as requested)
        recent_examples = []
        for validation in all_validations[:limit]:
            recent_examples.append(
                ValidationExample(
                    id=validation["id"],
                    task_id=validation["task_id"],
                    task_name=validation["task_name"],
                    ra_tag=validation["ra_tag"],
                    outcome=validation["outcome"],
                    confidence=validation["confidence"],
                    validator_id=validation["validator_id"],
                    validated_at=validation["validated_at"],
                    notes=validation["notes"],
                )
            )

        # Build response
        insights = InsightsSummary(
            total_validations=len(all_validations),
            success_rate=success_rate,
            outcome_breakdown=dict(outcome_counts),
            tag_type_breakdown=dict(tag_type_counts),
            recent_examples=recent_examples,
            cache_timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Cache the response for 5 minutes
        _cache_response(cache_key, insights.model_dump())

        return insights

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve assumption insights: {str(e)}"
        )


@router.get("/recent", response_model=RecentValidationsResponse)
async def get_recent_validations(
    db: TaskDatabase = Depends(get_database),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    epic_id: Optional[int] = Query(None, description="Filter by epic ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of recent validations to return"),
    before_id: Optional[int] = Query(
        None, description="Cursor for pagination - get validations before this ID"
    ),
) -> RecentValidationsResponse:
    """
    Get recent assumption validation activities with task context and pagination.

    Returns recent validations with:
    - Task, project, and epic context information
    - Normalized RA tag types using RA utilities
    - Cursor-based pagination for efficient browsing
    - Validation details including confidence and reviewer info
    """
    try:
        # Build query with joins for context information
        # #COMPLETION_DRIVE_INTEGRATION: Using LEFT JOINs to handle cases where project/epic might be null
        query = """
            SELECT av.id, av.task_id, av.ra_tag_id, av.outcome, av.confidence,
                   av.validator_id, av.validated_at, av.notes, av.context_snapshot,
                   t.name as task_name, t.ra_tags,
                   p.name as project_name,
                   e.name as epic_name
            FROM assumption_validations av
            JOIN tasks t ON av.task_id = t.id
            LEFT JOIN projects p ON av.project_id = p.id
            LEFT JOIN epics e ON av.epic_id = e.id
        """

        conditions = []
        params = []

        # Only filter by project_id if it's a positive integer (not 0 or negative)
        if project_id is not None and project_id > 0:
            conditions.append("av.project_id = ?")
            params.append(project_id)

        # Only filter by epic_id if it's a positive integer (not 0 or negative)
        if epic_id is not None and epic_id > 0:
            conditions.append("av.epic_id = ?")
            params.append(epic_id)

        if before_id is not None:
            conditions.append("av.id < ?")
            params.append(before_id)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        # Order by ID DESC for cursor-based pagination
        order_clause = " ORDER BY av.id DESC"
        limit_clause = f" LIMIT {limit + 1}"  # Get one extra to check for more results

        full_query = query + where_clause + order_clause + limit_clause

        # Execute query with performance indexes
        with db._connection_lock:
            cursor = db._connection.cursor()
            cursor.execute(full_query, params)
            rows = cursor.fetchall()

        # Check if there are more results
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]  # Remove the extra row

        # Process results with RA tag normalization
        validations = []
        for row in rows:
            # Extract RA tag details from task's ra_tags JSON
            ra_tag_id = row[2]
            ra_tags_json = row[10]  # t.ra_tags
            extracted_ra_tag_type = "UNKNOWN"
            ra_tag_text = "Unknown tag"
            
            if ra_tags_json:
                try:
                    ra_tags = json.loads(ra_tags_json)
                    for tag in ra_tags:
                        if tag.get('id') == ra_tag_id:
                            extracted_ra_tag_type = tag.get('type', 'UNKNOWN')
                            ra_tag_text = tag.get('text', 'Unknown tag')
                            break
                except (json.JSONDecodeError, TypeError):
                    pass

            # Normalize RA tag using utilities from Task 14
            normalized_type, _ = normalize_ra_tag(extracted_ra_tag_type)

            validation = RecentValidation(
                id=row[0],
                task_id=row[1],
                ra_tag_id=ra_tag_id,
                task_name=row[9],
                project_name=row[11],
                epic_name=row[12],
                ra_tag=extracted_ra_tag_type,
                ra_tag_type=normalized_type,
                outcome=row[3],
                confidence=row[4],
                validator_id=row[5],
                validated_at=row[6],
                notes=row[7],
                context_snapshot=row[8],
            )
            validations.append(validation)

        # Calculate total count (approximate for pagination)
        # #COMPLETION_DRIVE_IMPL: Using simple count for MVP, full count queries available if needed
        total_query = """
            SELECT COUNT(*) FROM assumption_validations av
        """ + (
            where_clause.replace("av.id < ?", "") if before_id else where_clause
        )

        count_params = [p for p in params if p != before_id] if before_id else params

        with db._connection_lock:
            cursor = db._connection.cursor()
            cursor.execute(total_query, count_params)
            total_count = cursor.fetchone()[0]

        # Determine next cursor
        next_cursor = validations[-1].id if validations and has_more else None

        return RecentValidationsResponse(
            validations=validations,
            total_count=total_count,
            has_more=has_more,
            next_cursor=next_cursor,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve recent validations: {str(e)}"
        )


@router.get("/tag-types", response_model=TagTypesResponse)
async def get_tag_types(
    db: TaskDatabase = Depends(get_database),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    epic_id: Optional[int] = Query(None, description="Filter by epic ID"),
) -> TagTypesResponse:
    """
    Get available RA tag types for filter dropdown population.

    Returns:
    - Distinct normalized RA tag types using RA utilities
    - Category and subcategory breakdowns
    - Usage counts and example original tags
    - Cached for 5 minutes for performance
    """
    try:
        # Check cache first
        cache_key = _get_cache_key("tag-types", project_id=project_id, epic_id=epic_id)
        cached_response = _get_cached_response(cache_key)
        if cached_response:
            return TagTypesResponse(**cached_response)

        # Query for distinct RA tags with counts
        query = """
            SELECT av.ra_tag_id, t.ra_tags, COUNT(*) as count
            FROM assumption_validations av
            JOIN tasks t ON av.task_id = t.id
        """

        conditions = []
        params = []

        # Only filter by project_id if it's a positive integer (not 0 or negative)
        if project_id is not None and project_id > 0:
            conditions.append("av.project_id = ?")
            params.append(project_id)

        # Only filter by epic_id if it's a positive integer (not 0 or negative)
        if epic_id is not None and epic_id > 0:
            conditions.append("av.epic_id = ?")
            params.append(epic_id)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        group_clause = " GROUP BY av.ra_tag_id, t.ra_tags ORDER BY count DESC"

        full_query = query + where_clause + group_clause

        with db._connection_lock:
            cursor = db._connection.cursor()
            cursor.execute(full_query, params)
            rows = cursor.fetchall()

        # Process with RA tag normalization and grouping
        tag_type_data = defaultdict(
            lambda: {"count": 0, "examples": [], "category": "", "subcategory": ""}
        )

        for ra_tag_id, ra_tags_json, count in rows:
            # Extract RA tag details from task's ra_tags JSON
            extracted_ra_tag_type = "UNKNOWN"
            ra_tag_text = "Unknown tag"
            
            if ra_tags_json:
                try:
                    ra_tags = json.loads(ra_tags_json)
                    for tag in ra_tags:
                        if tag.get('id') == ra_tag_id:
                            extracted_ra_tag_type = tag.get('type', 'UNKNOWN')
                            ra_tag_text = tag.get('text', 'Unknown tag')
                            break
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Normalize using RA utilities from Task 14
            normalized_type, original_text = normalize_ra_tag(extracted_ra_tag_type)

            # Accumulate data for this normalized type
            type_info = tag_type_data[normalized_type]
            type_info["count"] += count

            # Keep up to 3 examples of original tags
            if len(type_info["examples"]) < 3:
                type_info["examples"].append(ra_tag_text)

            # Extract category and subcategory
            if not type_info["category"]:
                parts = normalized_type.split(":")
                type_info["category"] = parts[0]
                type_info["subcategory"] = parts[1] if len(parts) > 1 else "other"

        # Convert to response format
        tag_types = []
        for normalized_type, data in tag_type_data.items():
            tag_info = TagTypeInfo(
                normalized_type=normalized_type,
                category=data["category"],
                subcategory=data["subcategory"],
                count=data["count"],
                example_tags=data["examples"],
            )
            tag_types.append(tag_info)

        # Sort by count descending
        tag_types.sort(key=lambda x: x.count, reverse=True)

        response = TagTypesResponse(
            tag_types=tag_types,
            total_types=len(tag_types),
            cache_timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Cache the response
        _cache_response(cache_key, response.model_dump())

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tag types: {str(e)}")


@router.get("/tag-details")
async def get_tag_details(
    tag_type: str = Query(..., description="The RA tag type to get details for"),
    db: TaskDatabase = Depends(get_database),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    epic_id: Optional[int] = Query(None, description="Filter by epic ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of validations to return"),
) -> Dict[str, Any]:
    """
    Get detailed validation information for a specific RA tag type.
    
    Returns:
    - All validations for the specified tag type
    - Success rate breakdown
    - Recent validation examples with full context
    """
    try:
        # Build query to get all validations for this tag type
        query = """
            SELECT av.id, av.task_id, av.ra_tag_id, av.outcome, av.confidence,
                   av.validator_id, av.validated_at, av.notes, av.context_snapshot,
                   t.name as task_name, t.ra_tags,
                   p.name as project_name,
                   e.name as epic_name
            FROM assumption_validations av
            JOIN tasks t ON av.task_id = t.id
            LEFT JOIN projects p ON av.project_id = p.id
            LEFT JOIN epics e ON av.epic_id = e.id
        """

        conditions = []
        params = []

        # Filter by project_id if specified
        if project_id is not None and project_id > 0:
            conditions.append("av.project_id = ?")
            params.append(project_id)

        # Filter by epic_id if specified
        if epic_id is not None and epic_id > 0:
            conditions.append("av.epic_id = ?")
            params.append(epic_id)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        order_clause = " ORDER BY av.validated_at DESC"
        limit_clause = f" LIMIT {limit}"

        full_query = query + where_clause + order_clause + limit_clause

        with db._connection_lock:
            cursor = db._connection.cursor()
            cursor.execute(full_query, params)
            rows = cursor.fetchall()

        # Filter and process results for the specific tag type
        matching_validations = []
        outcome_counts = {"validated": 0, "rejected": 0, "partial": 0}

        for row in rows:
            # Extract RA tag details from task's ra_tags JSON
            ra_tag_id = row[2]
            ra_tags_json = row[10]  # t.ra_tags
            extracted_ra_tag_type = "UNKNOWN"
            
            if ra_tags_json:
                try:
                    ra_tags = json.loads(ra_tags_json)
                    for tag in ra_tags:
                        if tag.get('id') == ra_tag_id:
                            extracted_ra_tag_type = tag.get('type', 'UNKNOWN')
                            break
                except (json.JSONDecodeError, TypeError):
                    pass

            # Only include validations that match the requested tag type
            if extracted_ra_tag_type == tag_type:
                validation = {
                    "id": row[0],
                    "task_id": row[1],
                    "ra_tag_id": ra_tag_id,
                    "task_name": row[9],
                    "project_name": row[11],
                    "epic_name": row[12],
                    "ra_tag": extracted_ra_tag_type,
                    "outcome": row[3],
                    "confidence": row[4],
                    "validator_id": row[5],
                    "validated_at": row[6],
                    "notes": row[7],
                    "context_snapshot": row[8],
                }
                matching_validations.append(validation)
                outcome_counts[row[3]] = outcome_counts.get(row[3], 0) + 1

        # Calculate success rate
        total_validations = len(matching_validations)
        success_rate = _calculate_success_rate(outcome_counts) if total_validations > 0 else 0.0

        return {
            "success": True,
            "tag_type": tag_type,
            "total_validations": total_validations,
            "success_rate": success_rate,
            "outcome_breakdown": outcome_counts,
            "validations": matching_validations,
            # Add frontend-expected fields
            "successful_count": outcome_counts.get("validated", 0),
            "partial_count": outcome_counts.get("partial", 0), 
            "rejected_count": outcome_counts.get("rejected", 0),
            "recent_validations": matching_validations,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tag details: {str(e)}")
