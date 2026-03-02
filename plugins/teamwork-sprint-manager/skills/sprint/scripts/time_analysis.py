#!/usr/bin/env python3
"""
Time Analysis — Compare estimated vs. actual time for sprint tasks.

Usage:
    python3 time_analysis.py --sprint-tag "Sprint-25"
    python3 time_analysis.py --sprint-tag "Sprint-25" --format json

Requires: TEAMWORK_SITE and TEAMWORK_API_KEY environment variables.
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tw_api


def time_analysis(sprint_tag_name, output_format="text"):
    """Analyze estimated vs. actual time for a sprint."""

    # Find the tag
    tags = tw_api.find_sprint_tags(sprint_tag_name)
    if not tags:
        print(f"ERROR: No tag matching '{sprint_tag_name}' found.", file=sys.stderr)
        sys.exit(1)

    tag = None
    for t in tags:
        if t["name"].lower() == sprint_tag_name.lower():
            tag = t
            break
    if tag is None:
        tag = tags[0]

    print(f"Fetching tasks for '{tag['name']}'...", file=sys.stderr)

    # Fetch tasks
    tasks = tw_api.get_tasks_for_tag(tag["id"])
    if not tasks:
        print("No tasks found for this sprint tag.")
        return

    # Fetch time entries for all tasks
    task_ids = [t["id"] for t in tasks]
    print(f"Fetching time entries for {len(task_ids)} tasks...", file=sys.stderr)
    time_entries_map = tw_api.get_time_entries_for_tasks(task_ids)

    # Build analysis
    results = []
    total_estimated = 0
    total_actual = 0
    tasks_with_estimates = 0
    tasks_without_estimates = 0
    tasks_over = 0
    tasks_under = 0
    tasks_no_time = 0

    for task in tasks:
        task_id = task["id"]
        estimated_mins = task.get("estimatedMinutes", 0) or 0
        entries = time_entries_map.get(task_id, [])
        actual_mins = sum(e.get("minutes", 0) or 0 for e in entries)

        variance_mins = actual_mins - estimated_mins if estimated_mins > 0 else None
        variance_pct = round(variance_mins / estimated_mins * 100, 1) if estimated_mins > 0 and variance_mins is not None else None

        if estimated_mins > 0:
            tasks_with_estimates += 1
            total_estimated += estimated_mins
            total_actual += actual_mins
            if actual_mins > estimated_mins:
                tasks_over += 1
            elif actual_mins < estimated_mins:
                tasks_under += 1
        else:
            tasks_without_estimates += 1

        if actual_mins == 0:
            tasks_no_time += 1

        assignees = task.get("assignees", [])
        assignee_names = ", ".join(
            f"{a.get('firstName', '')} {a.get('lastName', '')}".strip()
            for a in assignees
        ) or "Unassigned"

        results.append({
            "task_id": task_id,
            "task_name": task.get("name", ""),
            "assignee": assignee_names,
            "status": task.get("status", ""),
            "estimated_mins": estimated_mins,
            "estimated_hours": tw_api.minutes_to_hours(estimated_mins),
            "actual_mins": actual_mins,
            "actual_hours": tw_api.minutes_to_hours(actual_mins),
            "variance_mins": variance_mins,
            "variance_pct": variance_pct,
        })

    # Sort by variance (worst overruns first)
    results_with_variance = [r for r in results if r["variance_pct"] is not None]
    results_with_variance.sort(key=lambda r: r["variance_pct"] or 0, reverse=True)
    results_without = [r for r in results if r["variance_pct"] is None]

    if output_format == "json":
        output = {
            "sprint_tag": tag["name"],
            "summary": {
                "total_tasks": len(tasks),
                "tasks_with_estimates": tasks_with_estimates,
                "tasks_without_estimates": tasks_without_estimates,
                "tasks_no_time_logged": tasks_no_time,
                "total_estimated_hours": tw_api.minutes_to_hours(total_estimated),
                "total_actual_hours": tw_api.minutes_to_hours(total_actual),
                "overall_variance_pct": round((total_actual - total_estimated) / total_estimated * 100, 1) if total_estimated > 0 else None,
                "tasks_over_estimate": tasks_over,
                "tasks_under_estimate": tasks_under,
            },
            "tasks": results_with_variance + results_without,
        }
        print(json.dumps(output, indent=2))
        return

    # Text output
    print(f"\n{'='*70}")
    print(f"  TIME ANALYSIS: {tag['name']}")
    print(f"{'='*70}\n")

    print(f"Tasks with estimates:    {tasks_with_estimates}")
    print(f"Tasks without estimates: {tasks_without_estimates}")
    print(f"Tasks with no time log:  {tasks_no_time}")
    print()

    if total_estimated > 0:
        overall_var = round((total_actual - total_estimated) / total_estimated * 100, 1)
        direction = "over" if overall_var > 0 else "under"
        print(f"Total estimated: {tw_api.format_duration(total_estimated)}")
        print(f"Total actual:    {tw_api.format_duration(total_actual)}")
        print(f"Overall:         {abs(overall_var)}% {direction} estimate")
    print()

    # Table of tasks with estimates
    if results_with_variance:
        print(f"{'Task':<40} {'Est':>7} {'Act':>7} {'Var %':>7}")
        print(f"{'-'*40} {'-'*7} {'-'*7} {'-'*7}")
        for r in results_with_variance:
            name = r["task_name"][:39]
            est = tw_api.format_duration(r["estimated_mins"])
            act = tw_api.format_duration(r["actual_mins"])
            var = f"{r['variance_pct']:+.0f}%" if r["variance_pct"] is not None else "N/A"
            flag = " ⚠" if r["variance_pct"] is not None and r["variance_pct"] > 50 else ""
            print(f"{name:<40} {est:>7} {act:>7} {var:>7}{flag}")

    # Assignee accuracy breakdown
    print(f"\n--- Estimate Accuracy by Assignee ---")
    assignee_data = {}
    for r in results_with_variance:
        name = r["assignee"]
        if name not in assignee_data:
            assignee_data[name] = {"estimated": 0, "actual": 0, "count": 0}
        assignee_data[name]["estimated"] += r["estimated_mins"]
        assignee_data[name]["actual"] += r["actual_mins"]
        assignee_data[name]["count"] += 1

    for name, data in sorted(assignee_data.items()):
        if data["estimated"] > 0:
            var = round((data["actual"] - data["estimated"]) / data["estimated"] * 100, 1)
            direction = "over" if var > 0 else "under"
            print(f"  {name}: {abs(var)}% {direction} across {data['count']} tasks")

    # Tasks without estimates (process gap warning)
    if results_without:
        print(f"\n--- Tasks Missing Estimates ({len(results_without)}) ---")
        for r in results_without:
            actual = tw_api.format_duration(r["actual_mins"]) if r["actual_mins"] > 0 else "no time logged"
            print(f"  - {r['task_name']} ({actual})")


def main():
    parser = argparse.ArgumentParser(description="Estimate vs. actual time analysis")
    parser.add_argument("--sprint-tag", required=True, help="Sprint tag name")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    time_analysis(args.sprint_tag, args.format)


if __name__ == "__main__":
    main()
