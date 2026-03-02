#!/usr/bin/env python3
"""
Velocity Report — Calculate team velocity and help plan future sprints.

Usage:
    python3 velocity_report.py --last-n-sprints 5
    python3 velocity_report.py --last-n-sprints 5 --format json

Requires: TEAMWORK_SITE and TEAMWORK_API_KEY environment variables.
"""

import argparse
import json
import sys
import os
import statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tw_api


def velocity_report(last_n=5, output_format="text"):
    """Generate a velocity report across recent sprints."""

    # Find all sprint tags
    sprint_tags = tw_api.find_sprint_tags()
    if not sprint_tags:
        print("No sprint tags found. Make sure your sprint tags contain 'Sprint', 'S-', or 'Iteration'.")
        print("Use sprint_overview.py --list-sprints to see all available tags.")
        return

    # Sort sprint tags — attempt numeric sort by extracting numbers from names
    def extract_sprint_number(tag):
        import re
        numbers = re.findall(r'\d+', tag.get("name", ""))
        return int(numbers[-1]) if numbers else 0

    sprint_tags.sort(key=extract_sprint_number)

    # Take the last N sprints
    recent_sprints = sprint_tags[-last_n:] if len(sprint_tags) >= last_n else sprint_tags

    print(f"Analyzing {len(recent_sprints)} sprint(s)...", file=sys.stderr)

    sprint_data = []

    for tag in recent_sprints:
        print(f"  Fetching data for {tag['name']}...", file=sys.stderr)
        tasks = tw_api.get_tasks_for_tag(tag["id"])

        total_tasks = len(tasks)
        completed_tasks = [t for t in tasks if t.get("status", "").lower() == "completed" or t.get("progress", 0) == 100]
        incomplete_tasks = [t for t in tasks if t not in completed_tasks]

        # Estimated hours for completed work (this is velocity)
        completed_estimated_mins = sum(t.get("estimatedMinutes", 0) or 0 for t in completed_tasks)
        total_estimated_mins = sum(t.get("estimatedMinutes", 0) or 0 for t in tasks)
        incomplete_estimated_mins = sum(t.get("estimatedMinutes", 0) or 0 for t in incomplete_tasks)

        completion_rate = round(len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0

        sprint_info = {
            "sprint_tag": tag["name"],
            "tag_id": tag["id"],
            "total_tasks": total_tasks,
            "completed_tasks": len(completed_tasks),
            "incomplete_tasks": len(incomplete_tasks),
            "completion_rate_pct": completion_rate,
            "velocity_hours": tw_api.minutes_to_hours(completed_estimated_mins),
            "velocity_mins": completed_estimated_mins,
            "total_estimated_hours": tw_api.minutes_to_hours(total_estimated_mins),
            "carryover_hours": tw_api.minutes_to_hours(incomplete_estimated_mins),
            "carryover_tasks": [
                {
                    "name": t.get("name", ""),
                    "estimated_hours": tw_api.minutes_to_hours(t.get("estimatedMinutes", 0) or 0),
                    "assignee": ", ".join(
                        f"{a.get('firstName', '')} {a.get('lastName', '')}".strip()
                        for a in t.get("assignees", [])
                    ) or "Unassigned",
                }
                for t in incomplete_tasks
            ],
        }
        sprint_data.append(sprint_info)

    # Calculate velocity statistics
    velocities = [s["velocity_hours"] for s in sprint_data if s["velocity_hours"] > 0]
    if velocities:
        avg_velocity = round(statistics.mean(velocities), 1)
        velocity_stddev = round(statistics.stdev(velocities), 1) if len(velocities) > 1 else 0
        min_velocity = min(velocities)
        max_velocity = max(velocities)
    else:
        avg_velocity = 0
        velocity_stddev = 0
        min_velocity = 0
        max_velocity = 0

    completion_rates = [s["completion_rate_pct"] for s in sprint_data]
    avg_completion = round(statistics.mean(completion_rates), 1) if completion_rates else 0

    # Planning recommendation
    # Conservative: avg - 1 stddev (rounded down)
    conservative_capacity = round(max(avg_velocity - velocity_stddev, min_velocity), 1)
    moderate_capacity = avg_velocity
    aggressive_capacity = round(min(avg_velocity + velocity_stddev * 0.5, max_velocity), 1)

    # Most recent sprint's carryover
    latest = sprint_data[-1] if sprint_data else None
    carryover_hours = latest["carryover_hours"] if latest else 0

    summary = {
        "sprints_analyzed": len(sprint_data),
        "velocity": {
            "average_hours": avg_velocity,
            "stddev_hours": velocity_stddev,
            "min_hours": min_velocity,
            "max_hours": max_velocity,
        },
        "avg_completion_rate_pct": avg_completion,
        "planning_recommendation": {
            "conservative_hours": conservative_capacity,
            "moderate_hours": moderate_capacity,
            "aggressive_hours": aggressive_capacity,
            "carryover_from_current_hours": carryover_hours,
            "new_work_conservative_hours": round(max(conservative_capacity - carryover_hours, 0), 1),
            "new_work_moderate_hours": round(max(moderate_capacity - carryover_hours, 0), 1),
        },
    }

    if output_format == "json":
        output = {
            "summary": summary,
            "sprints": sprint_data,
        }
        print(json.dumps(output, indent=2))
        return

    # Text output
    print(f"\n{'='*60}")
    print(f"  VELOCITY REPORT ({len(sprint_data)} sprints)")
    print(f"{'='*60}\n")

    # Per-sprint breakdown
    print(f"{'Sprint':<20} {'Tasks':>7} {'Done':>7} {'Rate':>7} {'Velocity':>10}")
    print(f"{'-'*20} {'-'*7} {'-'*7} {'-'*7} {'-'*10}")
    for s in sprint_data:
        print(f"{s['sprint_tag']:<20} {s['total_tasks']:>7} {s['completed_tasks']:>7} {s['completion_rate_pct']:>6}% {s['velocity_hours']:>9}h")

    print(f"\n--- Velocity Statistics ---")
    print(f"Average velocity:  {avg_velocity}h per sprint")
    print(f"Std deviation:     {velocity_stddev}h")
    print(f"Range:             {min_velocity}h – {max_velocity}h")
    print(f"Avg completion:    {avg_completion}%")

    if velocity_stddev > avg_velocity * 0.3:
        print(f"\n⚠  High velocity variance detected ({velocity_stddev}h stddev on {avg_velocity}h avg).")
        print(f"   This suggests sprint scope or team capacity varies significantly.")
        print(f"   Consider planning conservatively until velocity stabilizes.")

    print(f"\n--- Next Sprint Planning ---")
    print(f"Recommended capacity (hours of estimated work to commit to):")
    print(f"  Conservative: {conservative_capacity}h  (high confidence)")
    print(f"  Moderate:     {moderate_capacity}h  (based on average)")
    print(f"  Aggressive:   {aggressive_capacity}h  (stretch goal)")

    if carryover_hours > 0 and latest:
        print(f"\nCarryover from {latest['sprint_tag']}: {carryover_hours}h ({len(latest['carryover_tasks'])} tasks)")
        print(f"  Room for new work (conservative): {summary['planning_recommendation']['new_work_conservative_hours']}h")
        print(f"  Room for new work (moderate):     {summary['planning_recommendation']['new_work_moderate_hours']}h")
        print(f"\n  Carryover tasks:")
        for ct in latest["carryover_tasks"]:
            est = f"{ct['estimated_hours']}h" if ct["estimated_hours"] > 0 else "no est."
            print(f"    - {ct['name']} ({est}, {ct['assignee']})")


def main():
    parser = argparse.ArgumentParser(description="Sprint velocity and planning report")
    parser.add_argument("--last-n-sprints", type=int, default=5, help="Number of recent sprints to analyze")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    velocity_report(args.last_n_sprints, args.format)


if __name__ == "__main__":
    main()
