#!/bin/bash

DB_FILE="project_manager.db"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <epic_id>"
    echo "Clears all assumption validations for tasks in the specified epic"
    echo ""
    echo "Available epics:"
    sqlite3 "$DB_FILE" "SELECT e.id, e.name, p.name as project_name FROM epics e JOIN projects p ON e.project_id = p.id ORDER BY e.id" -header -column
    exit 1
fi

EPIC_ID=$1

if [ ! -f "$DB_FILE" ]; then
    echo "Error: Database file $DB_FILE not found"
    exit 1
fi

# Show what will be deleted
echo "Tasks in epic $EPIC_ID with validations:"
sqlite3 "$DB_FILE" "SELECT t.id, t.name FROM tasks t WHERE t.epic_id = $EPIC_ID AND t.id IN (SELECT DISTINCT task_id FROM assumption_validations)"

# Count validations to be deleted
COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM assumption_validations WHERE task_id IN (SELECT id FROM tasks WHERE epic_id = $EPIC_ID)")

if [ "$COUNT" -eq 0 ]; then
    echo "No validations found for epic $EPIC_ID"
    exit 0
fi

echo "About to delete $COUNT validation(s). Continue? (y/N)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    sqlite3 "$DB_FILE" "DELETE FROM assumption_validations WHERE task_id IN (SELECT id FROM tasks WHERE epic_id = $EPIC_ID)"
    echo "Deleted $COUNT validation(s) for epic $EPIC_ID"
else
    echo "Cancelled"
fi