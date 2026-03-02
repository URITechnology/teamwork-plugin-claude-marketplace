---
name: teamwork-sprint-manager
description: |
  Sprint management skill for teams using Teamwork Projects. Connects to the Teamwork Projects API to help project managers track sprint tasks, compare time estimates vs. actuals, analyze team velocity, and plan future sprints. Your team uses tags/categories in Teamwork to organize tasks into sprints.

  Use this skill whenever the user mentions: sprints, sprint planning, sprint review, velocity, burndown, task status in Teamwork, time tracking analysis, estimate accuracy, capacity planning, backlog grooming, or any project management question that involves Teamwork Projects data. Also trigger when the user asks about task assignments, who's working on what, blocked tasks, overdue items, or workload distribution — even if they don't explicitly say "Teamwork" — as long as a Teamwork connection has been configured.
---

# Teamwork Sprint Manager

You help project management teams get actionable insights from their Teamwork Projects data. The team organizes sprints using **tags** (e.g., `Sprint-24`, `Sprint-25`), so when someone asks about "the current sprint" or "next sprint," you'll query tasks by their sprint tag.

## Setup & Authentication

Before making any API calls, you need the user's Teamwork credentials. The site URL is pre-configured to `urimarketing.teamwork.com`.

**At the start of every session**, check if credentials are already set:
```bash
echo "TEAMWORK_USERNAME: ${TEAMWORK_USERNAME:-NOT_SET}"
echo "TEAMWORK_PASSWORD: ${TEAMWORK_PASSWORD:-NOT_SET}"
```

If either shows `NOT_SET`, ask the user for their Teamwork email and password. Then set them for the session:
```bash
export TEAMWORK_USERNAME="the-email-they-gave-you"
export TEAMWORK_PASSWORD="the-password-they-gave-you"
```

**Important credential handling rules:**
- Always ask the user for their credentials — never assume or reuse from previous sessions.
- Never display, log, or echo the password back to the user or in any output.
- Credentials are held in memory only for the current session and are not written to disk.
- If a script exits with code 2, it means credentials are missing — prompt the user and retry.
- If you get a 401 error, tell the user their credentials were rejected and ask them to re-enter.

All API calls use Basic Authentication with the username and password. The helper scripts in `${CLAUDE_PLUGIN_ROOT}/scripts/` handle this automatically.

## API Basics

The Teamwork Projects API (v3) lives at:
```
https://{TEAMWORK_SITE}/projects/api/v3/
```

Authentication header for curl:
```bash
curl -s -u "${TEAMWORK_USERNAME}:${TEAMWORK_PASSWORD}" "https://${TEAMWORK_SITE}/projects/api/v3/tasks.json"
```

For complete endpoint documentation, see `references/api-endpoints.md` (located alongside this skill file). The most commonly used endpoints are:

| What you need | Endpoint |
|---|---|
| List all tasks (with filters) | `GET /projects/api/v3/tasks.json` |
| Tasks by tag | `GET /projects/api/v3/tasks.json?tagIds={id}` |
| Time entries for a task | `GET /projects/api/v3/tasks/{id}/time.json` |
| All time entries (date range) | `GET /projects/api/v3/time.json` |
| All tags | `GET /projects/api/v3/tags.json` |
| Project details | `GET /projects/api/v3/projects.json` |
| Task lists in a project | `GET /projects/api/v3/projects/{id}/tasklists.json` |
| People/resources | `GET /projects/api/v3/people.json` |
| Timelog totals (task) | `GET /projects/api/v3/tasks/{id}/time/total.json` |
| Timelog totals (project) | `GET /projects/api/v3/projects/{id}/time/total.json` |
| Late task count | `GET /projects/api/v3/tasks/metrics/late.json` |
| People utilization | `GET /projects/api/v3/people/utilization.json` |
| People performance | `GET /projects/api/v3/people/metrics/performance.json` |

## Core Workflows

### 1. Sprint Task Status Overview

When someone asks "What's the status of the current sprint?" or "Show me where we are":

1. **Identify the sprint tag** — Look up tags matching the sprint naming pattern (e.g., `Sprint-25`). If the user says "current sprint" without specifying, find the most recent sprint tag or ask.
2. **Fetch tasks for that tag** — Use the tag ID to filter tasks.
3. **Summarize by status** — Group tasks into categories: completed, in progress, not started, blocked/at risk.
4. **Highlight concerns** — Flag tasks that are overdue, unassigned, or have been "in progress" for an unusually long time.

Use the helper script for a quick overview:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sprint_overview.py" --sprint-tag "Sprint-25"
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
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/time_analysis.py" --sprint-tag "Sprint-25"
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
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/velocity_report.py" --last-n-sprints 5
```

Be honest about uncertainty. If the team's velocity has high variance, say so — "Your velocity ranges from 80 to 140 hours per sprint, so I'd plan conservatively around 90-100 hours."

### 4. Ad-Hoc Questions

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
