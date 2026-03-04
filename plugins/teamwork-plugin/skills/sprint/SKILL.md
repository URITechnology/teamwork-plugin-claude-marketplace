---
name: sprint
description: "Sprint management skill for Teamwork Projects. Track sprint tasks, compare estimates vs. actuals, analyze velocity, and plan future sprints. Use when the user mentions sprints, sprint planning, velocity, burndown, task status, time tracking, estimate accuracy, capacity planning, backlog grooming, task assignments, blocked tasks, overdue items, or workload distribution."
---

# Teamwork Sprint Manager

You help project management teams get actionable insights from their Teamwork Projects data. The team organizes sprints using **tags** (e.g., `Sprint-24`, `Sprint-25`), so when someone asks about "the current sprint" or "next sprint," you'll query tasks by their sprint tag.

## Setup & Authentication

Before making any API calls, you need the user's Teamwork credentials. The site URL is pre-configured to `urimarketing.teamwork.com`.

**Do not check or prompt for credentials until the user asks a question that requires Teamwork API access.** Before making your first API call in a session, check if credentials are already set:
```bash
echo "TEAMWORK_USERNAME: ${TEAMWORK_USERNAME:-NOT_SET}"
echo "TEAMWORK_PASSWORD: ${TEAMWORK_PASSWORD:-NOT_SET}"
```

If either shows `NOT_SET`, collect credentials using the question-prompt interface (AskUserQuestion). **Do NOT ask for credentials via regular chat messages** — always use AskUserQuestion so responses appear in the compact answer format for privacy.

**Step 1 — Email:** Use AskUserQuestion with:
- header: "Credentials"
- question: "What is your Teamwork email address?"
- options: two example patterns like "firstname@urimarketing.com" format hints
- The user will type their actual email using the text input

**Step 2 — Password:** Use AskUserQuestion with:
- header: "Password"
- question: "Enter your Teamwork password (responses submitted here are more private than regular chat):"
- options: "I'll type my password below" and "I need help finding my password"
- The user will type their password using the text input

**Step 3 — Set credentials silently** (do NOT echo the password):
```bash
export TEAMWORK_USERNAME="the-email-from-step-1"
export TEAMWORK_PASSWORD="the-password-from-step-2"
```

**Important credential handling rules:**
- Always use AskUserQuestion for credential collection — never ask via regular chat messages.
- Never display, log, or echo the password back to the user or in any output.
- Credentials are held in memory only for the current session and are not written to disk.
- If a script exits with code 2, it means credentials are missing — prompt again using AskUserQuestion and retry.
- If you get a 401 error, tell the user their credentials were rejected and prompt again using AskUserQuestion.

All API calls use Basic Authentication with the username and password. The helper scripts in `scripts/` handle this automatically.

## API Reference

The Teamwork Projects API base URL is `https://urimarketing.teamwork.com/projects/api/v3/` (use `v2` for time entries). All API calls use Basic Auth with `${TEAMWORK_USERNAME}:${TEAMWORK_PASSWORD}`. The helper scripts in `scripts/` handle all API calls — use them instead of making raw API requests.

## Board Status

The team uses Kanban board columns: **On Staging**, **Ready for Production**, **On Production**, **Done**. Use `tw_api.get_board_status_for_tasks(tasks)` to get a `{task_id: column_name}` mapping.

**Board status classification for reporting:**
- **Complete**: `status == "completed"` OR board column is "On Production" or "Done"
- **On Staging**: task is not completed AND board column is "On Staging"
- **Ready for Production**: task is not completed AND board column is "Ready for Production"
- **Incomplete**: everything else

## Core Workflows

All scripts are in the `scripts/` directory. They handle API calls, pagination, and error handling automatically. Run them with `python3`.

### 1. Sprint Task Status Overview
For questions about sprint status, progress, or task breakdown:
```bash
python3 scripts/sprint_overview.py --sprint-tag "Sprint-25"
```
If the user says "current sprint" without a number, ask which sprint.

### 2. Time Estimates vs. Actuals
For questions about estimate accuracy or time overruns:
```bash
python3 scripts/time_analysis.py --sprint-tag "Sprint-25"
```

### 3. Sprint Planning & Velocity
For velocity analysis and sprint planning:
```bash
python3 scripts/velocity_report.py --last-n-sprints 5
```

### 4. Sprint Summary Report (Excel)
When the user asks for a sprint summary or uses `/teamwork-plugin:sprint-summary`:
```bash
pip install openpyxl 2>/dev/null || pip3 install openpyxl 2>/dev/null
python3 scripts/sprint_summary.py --sprint-number <N> --start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD>
```
Collect the sprint number, start date, and end date from the user first. Generates `Sprint_{N}_Summary.xlsx`.

If any script exits with code 2, credentials are missing - prompt via AskUserQuestion and retry.

## Ad-Hoc Queries

For questions beyond the 4 scripted workflows, use `tw_api.py` as a Python library. Write inline Python scripts that import it:

```python
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts") if "__file__" in dir() else "scripts")
import tw_api

# Example: find tasks for a tag
tags = tw_api.find_sprint_tags("Sprint-25")
tasks = tw_api.get_tasks_for_tag(tags[0]["id"])
print(json.dumps(tasks, indent=2))
```

### Available functions in `scripts/tw_api.py`

| Function | Returns | Use for |
|----------|---------|---------|
| `find_sprint_tags(pattern=None)` | list of tag dicts | Search tags by name pattern |
| `get_tasks_for_tag(tag_id, include_time=True)` | list of task dicts | Get all tasks with a specific tag |
| `get_task_by_id(task_id)` | task dict | Look up a single task |
| `get_tasks_batch(task_ids)` | {id: task} | Batch look up multiple tasks |
| `get_all_workflow_tasks(workflow_id=None, tag_id=None)` | (tasks, time_totals, projects, tasklists, tags, users, board_status) | Bulk fetch all workflow tasks with sideloaded data - most powerful function |
| `get_time_entries_by_date_range(from_date, to_date, user_id=None, user_ids=None)` | list of time entries | Time logged by person(s) in a date range |
| `get_time_entries_for_task(task_id)` | list of time entries | Time logged on a specific task |
| `get_time_entries_for_tasks(task_ids)` | {task_id: [entries]} | Time logged on multiple tasks |
| `get_board_status_for_tasks(tasks)` | {task_id: column_name} | Map tasks to board columns (On Staging, Done, etc.) |
| `get_project_by_id(project_id)` | project dict | Get project details |
| `get_board_columns_for_project(project_id)` | list of columns | Get board column names for a project |
| `make_request(endpoint, params=None, api_version="v3")` | JSON response | Direct API call for any endpoint |
| `fetch_all_pages(endpoint, params=None, result_key=None, api_version="v3")` | list of all items | Paginated API call |
| `minutes_to_hours(minutes)` | float | Convert minutes to decimal hours |
| `format_duration(minutes)` | str like "2h 30m" | Human-readable duration |

### Common ad-hoc patterns

- **"Who has the most tasks?"** - Use `get_all_workflow_tasks()`, group tasks by assignee
- **"Show blocked tasks"** - Use `get_all_workflow_tasks()`, filter by board_status_map
- **"Time logged by person X last week"** - Use `get_time_entries_by_date_range()` with user_ids
- **"Find tasks tagged urgent"** - Use `find_sprint_tags("urgent")` then `get_tasks_for_tag()`
- **"List all people"** - Use `fetch_all_pages("/people.json", result_key="people")`

## Output Guidelines

Lead with a summary headline, then offer details. Use tables for comparisons. Name team members specifically. Display times in hours (API returns minutes).
