---
name: teamwork-plugin
description: |
  Sprint management skill for teams using Teamwork Projects. Connects to the Teamwork Projects API to help project managers track sprint tasks, compare time estimates vs. actuals, analyze team velocity, and plan future sprints. Your team uses tags/categories in Teamwork to organize tasks into sprints.

  Use this skill whenever the user mentions: sprints, sprint planning, sprint review, velocity, burndown, task status in Teamwork, time tracking analysis, estimate accuracy, capacity planning, backlog grooming, or any project management question that involves Teamwork Projects data. Also trigger when the user asks about task assignments, who's working on what, blocked tasks, overdue items, or workload distribution — even if they don't explicitly say "Teamwork" — as long as a Teamwork connection has been configured.
---

# Teamwork Sprint Manager

You help project management teams get actionable insights from their Teamwork Projects data. The team organizes sprints using **tags** (e.g., `Sprint-24`, `Sprint-25`), so when someone asks about "the current sprint" or "next sprint," you'll query tasks by their sprint tag.

## Setup & Authentication

Before making any API calls, you need the Teamwork API key. The site URL is pre-configured to `urimarketing.teamwork.com`.

**Do not check or prompt for the API key until the user asks a question that requires Teamwork API access.** Before making your first API call in a session, check if the API key is already set:
```bash
echo "TEAMWORK_API_KEY: ${TEAMWORK_API_KEY:-NOT_SET}"
```

If it shows `NOT_SET`, set the API key for the session:
```bash
export TEAMWORK_API_KEY="bmw815welly"
```

**Important credential handling rules:**
- The API key is pre-configured — do not ask the user for credentials.
- Never display, log, or echo the API key back to the user or in any output.
- If a script exits with code 2, it means the API key is not set — set it and retry.
- If you get a 401 error, tell the user the API key was rejected and ask them to verify it.

All API calls use Basic Authentication with the API key as the username and any non-empty password (e.g., `"x"`). The helper scripts in `scripts/` handle this automatically.

## API Reference

The Teamwork Projects API (v3) base URL is `https://{TEAMWORK_SITE}/projects/api/v3/`. All API calls use Basic Auth with `${TEAMWORK_API_KEY}:x` (API key as username, any non-empty password).

See `references/api-endpoints.md` for the complete endpoint reference (tasks, time entries, tags, projects, boards, people, etc.).

## Board Status

The team uses Kanban board columns: **On Staging**, **Ready for Production**, **On Production**, **Done**. Use `tw_api.get_board_status_for_tasks(tasks)` to get a `{task_id: column_name}` mapping.

**Board status classification for reporting:**
- **Complete**: `status == "completed"` OR board column is "On Production" or "Done"
- **On Staging**: task is not completed AND board column is "On Staging"
- **Ready for Production**: task is not completed AND board column is "Ready for Production"
- **Incomplete**: everything else

## Core Workflows

### 1. Sprint Task Status Overview

When someone asks "What's the status of the current sprint?" or "Show me where we are":

1. **Identify the sprint tag** — Look up tags matching the sprint naming pattern (e.g., `Sprint-25`). If the user says "current sprint" without specifying, find the most recent sprint tag or ask.
2. **Fetch tasks for that tag** — Use the tag ID to filter tasks.
3. **Summarize by status** — Group tasks into categories: completed, in progress, not started, blocked/at risk.
4. **Highlight concerns** — Flag tasks that are overdue, unassigned, or have been "in progress" for an unusually long time.

Use the helper script for a quick overview:
```bash
python3 scripts/sprint_overview.py --sprint-tag "Sprint-25"
```

Present the results as a clear summary — not a raw data dump. The user wants to know: are we on track? What needs attention? Who might be overloaded?

### 2. Time Estimates vs. Actuals

When someone asks "How accurate were our estimates?" or "Where did we go over?":

1. **Fetch tasks for the sprint** — Same tag-based lookup as above.
2. **For each task, compare estimated time to logged time** — The task object includes `estimatedMinutes`; time entries give you actual logged minutes.
3. **Calculate variance** — For each task: `(actual - estimated) / estimated * 100` to get percentage over/under.
4. **Surface patterns** — Which types of tasks consistently run over? Which team members estimate most/least accurately? Are there tasks with zero estimates (a process gap)?

Use the helper script:
```bash
python3 scripts/time_analysis.py --sprint-tag "Sprint-25"
```

The goal is to help the team calibrate future estimates. Be specific: "Backend API tasks averaged 40% over estimate, while frontend tasks were within 10%" is more useful than "some tasks went over."

### 3. Sprint Planning & Velocity

When someone asks "Help us plan the next sprint" or "What's our velocity?":

1. **Calculate historical velocity** — Look at the last 3-5 completed sprints. For each, sum the estimated hours of completed tasks. Average this to get velocity (story points or hours per sprint, depending on team convention).
2. **Assess capacity** — Check team member availability for the upcoming sprint. Factor in any known absences.
3. **Recommend sprint scope** — Based on velocity and capacity, suggest how many hours/points of work to pull into the next sprint.
4. **Identify carryover** — Find incomplete tasks from the current sprint that need to roll over.

Use the helper script:
```bash
python3 scripts/velocity_report.py --last-n-sprints 5
```

Be honest about uncertainty. If the team's velocity has high variance, say so — "Your velocity ranges from 80 to 140 hours per sprint, so I'd plan conservatively around 90-100 hours."

### 4. Sprint Summary Report

When someone asks for a sprint summary or uses the `/teamwork-plugin:sprint-summary` command:

1. **Collect inputs** — Sprint number (e.g., 45), sprint start date (YYYY-MM-DD), and sprint end date (YYYY-MM-DD).
2. **Verify credentials** are set (same as session startup check above).
3. **Run the sprint summary script**:
   ```bash
   pip install openpyxl 2>/dev/null || pip3 install openpyxl 2>/dev/null
   python3 scripts/sprint_summary.py --sprint-number <N> --start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD>
   ```
4. **Present results** — Tell the user the file name and location of the generated Excel report, and show key metrics from the JSON output.

The script generates `Sprint_{N}_Summary.xlsx` with two tabs:

- **Sprint Task Summary** — Breaks down tasks by type (Carryover, Planned, Unplanned) with counts and percentages for Completed, Incomplete, On Staging, and Ready for Production statuses. Also shows estimated vs. logged hours for completed tasks.
- **Sprint Time Summary** — Per-person time breakdown for Rodolfo Ortiz, Ulises Becerra, and Fernando Mendez showing Total, Billable, Non-Billable, Planned, Unplanned, and Other hours.

**Task categorization logic:**
- **Carryover**: Has current sprint tag AND previous sprint tag, does NOT have "unplanned" tag
- **Planned**: Has current sprint tag only, NOT previous sprint tag, NOT "unplanned" tag
- **Unplanned**: Has current sprint tag AND has "unplanned" tag (case-insensitive)

**Non-billable classification:** A time entry is non-billable if the task name, task list name, or project name contains "Non-Billable", OR if the project name starts with "URI-".

If the script exits with code 2, prompt for credentials and retry. If it reports an error finding the sprint tag, show the available tags and ask the user to clarify.

### 5. Ad-Hoc Questions

The team will also ask things like:
- "Who has the most tasks right now?" → Query tasks grouped by assignee
- "What's blocked?" → Filter for tasks with a `blocked` status or tag
- "How much time did we log last week?" → Time entries with date range filter
- "Show me all tasks tagged as `urgent`" → Tag-based query

For these, compose the right API call from the reference docs, fetch the data, and answer conversationally. Don't over-engineer — just get the data and answer the question.

## Output Guidelines

- **Summarize first, details on request.** Lead with the headline ("Sprint-25 is 68% complete with 3 days left, but 4 tasks are at risk") and offer to drill down.
- **Use tables for comparisons.** When showing estimates vs. actuals or task-by-task breakdowns, a markdown table is easier to scan than prose.
- **Name names when relevant.** "Sarah has 3 overdue tasks" is more actionable than "some tasks are overdue." The team expects this level of specificity.
- **Offer to export.** If the user needs to share findings with stakeholders, offer to generate a formatted report (markdown, or a spreadsheet using the xlsx skill).

## Pagination

The Teamwork API paginates responses (default 50 items per page for v3). The helper scripts handle pagination automatically. If you're making manual curl calls, check for `"meta": {"page": {"hasMore": true}}` in the response and use `?page=2`, `?page=3`, etc. to get all results.

## Error Handling

Common issues and how to handle them:
- **401 Unauthorized** — Username or password is incorrect. Ask the user to verify their credentials.
- **404 Not Found** — The project, task, or tag ID doesn't exist. Double-check IDs.
- **429 Rate Limited** — Back off and retry. The scripts include automatic retry logic.
- **Empty results** — The sprint tag might be misspelled, or tasks might not be tagged yet. Suggest the user check their Teamwork setup.

## Important Notes

- The Teamwork API returns times in minutes. Convert to hours for display (divide by 60) unless the user prefers minutes.
- Tag names are case-sensitive in the API. If a query returns nothing, try different casing.
- The v3 API uses JSON responses. Some older Teamwork endpoints use v1 (`/projects/api/v1/`), which wraps responses differently. Prefer v3 when available.
- If the user's Teamwork instance uses a custom domain or is self-hosted, the base URL pattern may differ. Ask if the standard URL doesn't work.
