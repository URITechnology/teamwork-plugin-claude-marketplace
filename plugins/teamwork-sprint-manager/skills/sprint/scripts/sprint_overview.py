#!/usr/bin/env python3
"""
Sprint Overview — Shows task status breakdown for a given sprint tag.

Usage:
    python3 sprint_overview.py --sprint-tag "Sprint-25"
    python3 sprint_overview.py --sprint-tag "Sprint-25" --project-id 12345
    python3 sprint_overview.py --list-sprints

Requires: TEAMWORK_SITE and TEAMWORK_API_KEY environment variables.
"""

import argparse
import json
import sys
import os

# Add parent directory so we can import tw_api
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tw_api


def list_sprint_tags():
    """Print all sprint-like tags."""
    tags = tw_api.find_sprint_tags()
    if not tags:
        print("No sprint tags found. Tags matching 'Sprint', 'S-', or 'Iteration' patterns are detected.")
        print("\nAll tags in your Teamwork instance:")
        all_tags = tw_api.fetch_all_pages("/tags.json", result_key="tags")
        for tag in sorted(all_tags, key=lambda t: t.get("name", "")):
            print(f"  - {tag['name']} (ID: {tag['id']})")
        return

    print("Sprint tags found:")
    for tag in tags:
        print(f"  - {tag['name']} (ID: {tag['id']})")


def sprint_overview(sprint_tag_name, project_id=None):
    """Generate a sprint status overview."""

    # Find the tag
    tags = tw_api.find_sprint_tags(sprint_tag_name)
    if not tags:
        print(f"ERROR: No tag matching '{sprint_tag_name}' found.", file=sys.stderr)
        print("Use --list-sprints to see available sprint tags.", file=sys.stderr)
        sys.exit(1)

    # Use exact match if available, otherwise first partial match
    tag = None
    for t in tags:
        if t["name"].lower() == sprint_tag_name.lower():
            tag = t
            break
    if tag is None:
        tag = tags[0]
        print(f"Note: Using closest match '{tag['name']}' for '{sprint_tag_name}'", file=sys.stderr)

    print(f"\n{'='*60}")
    print(f"  SPRINT OVERVIEW: {tag['name']}")
    print(f"{'='*60}\n")

    # Fetch tasks for this sprint tag
    tasks = tw_api.get_tasks_for_tag(tag["id"])

    if project_id:
        tasks = [t for t in tasks if str(t.get("projectId")) == str(project_id)]

    if not tasks:
        print("No tasks found for this sprint tag.")
        return

    # Categorize tasks
    completed = []
    in_progress = []
    not_started = []
    other = []

    for task in tasks:
        status = task.get("status", "").lower()
        progress = task.get("progress", 0)

        if status == "completed" or progress == 100:
            completed.append(task)
        elif progress > 0 or status in ("active", "in progress"):
            in_progress.append(task)
        elif status in ("new", "") or progress == 0:
            not_started.append(task)
        else:
            other.append(task)

    total = len(tasks)
    pct_complete = round(len(completed) / total * 100) if total > 0 else 0

    # Summary
    print(f"Total tasks: {total}")
    print(f"Completed:   {len(completed)} ({pct_complete}%)")
    print(f"In Progress: {len(in_progress)}")
    print(f"Not Started: {len(not_started)}")
    if other:
        print(f"Other:       {len(other)}")

    # Estimated time summary
    total_estimated = sum(t.get("estimatedMinutes", 0) or 0 for t in tasks)
    completed_estimated = sum(t.get("estimatedMinutes", 0) or 0 for t in completed)
    print(f"\nEstimated hours (total):     {tw_api.minutes_to_hours(total_estimated)}h")
    print(f"Estimated hours (completed): {tw_api.minutes_to_hours(completed_estimated)}h")

    # Assignee breakdown
    print(f"\n--- Assignee Breakdown ---")
    assignee_tasks = {}
    for task in tasks:
        assignees = task.get("assignees", [])
        if not assignees:
            assignee_tasks.setdefault("Unassigned", []).append(task)
        else:
            for a in assignees:
                name = f"{a.get('firstName', '')} {a.get('lastName', '')}".strip() or f"User {a.get('id')}"
                assignee_tasks.setdefault(name, []).append(task)

    for name, atasks in sorted(assignee_tasks.items()):
        done = sum(1 for t in atasks if t in completed)
        total_a = len(atasks)
        print(f"  {name}: {done}/{total_a} complete")

    # At-risk tasks (in progress or not started with past due dates)
    print(f"\n--- At-Risk Tasks ---")
    at_risk = []
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    for task in in_progress + not_started:
        due = task.get("dueDate")
        if due:
            try:
                due_date = datetime.fromisoformat(due.replace("Z", "+00:00"))
                if due_date < now:
                    at_risk.append(task)
            except (ValueError, TypeError):
                pass

    if at_risk:
        for task in at_risk:
            assignees = task.get("assignees", [])
            assignee_names = ", ".join(
                f"{a.get('firstName', '')} {a.get('lastName', '')}".strip()
                for a in assignees
            ) or "Unassigned"
            print(f"  OVERDUE: {task['name']}")
            print(f"           Due: {task.get('dueDate', 'N/A')} | Assigned: {assignee_names}")
    else:
        print("  No overdue tasks found.")

    # Unassigned tasks
    unassigned = [t for t in tasks if not t.get("assignees")]
    if unassigned:
        print(f"\n--- Unassigned Tasks ({len(unassigned)}) ---")
        for task in unassigned:
            print(f"  - {task['name']}")

    # Output raw data as JSON for further processing
    output = {
        "sprint_tag": tag["name"],
        "total_tasks": total,
        "completed": len(completed),
        "in_progress": len(in_progress),
        "not_started": len(not_started),
        "percent_complete": pct_complete,
        "total_estimated_hours": tw_api.minutes_to_hours(total_estimated),
        "at_risk_count": len(at_risk),
        "unassigned_count": len(unassigned),
    }
    print(f"\n--- JSON Summary ---")
    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Sprint task overview from Teamwork Projects")
    parser.add_argument("--sprint-tag", help="Sprint tag name (e.g., 'Sprint-25')")
    parser.add_argument("--project-id", help="Optional: filter to a specific project ID")
    parser.add_argument("--list-sprints", action="store_true", help="List all sprint-like tags")
    args = parser.parse_args()

    if args.list_sprints:
        list_sprint_tags()
    elif args.sprint_tag:
        sprint_overview(args.sprint_tag, args.project_id)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
