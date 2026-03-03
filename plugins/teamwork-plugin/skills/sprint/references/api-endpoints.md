# Teamwork Projects API v3 — Endpoint Reference

Base URL: `https://{TEAMWORK_SITE}/projects/api/v3` (default site: `urimarketing.teamwork.com`)

Authentication: Basic Auth — username is the user's Teamwork email, password is their Teamwork password.

```
Authorization: Basic base64({USERNAME}:{PASSWORD})
```

All responses return JSON. Pagination uses `?page=N&pageSize=50` (default 50 items).

---

## Table of Contents

1. [Projects](#projects)
2. [Tasks](#tasks)
3. [Task Lists](#task-lists)
4. [Tags](#tags)
5. [Time Entries](#time-entries)
6. [People](#people)
7. [Milestones](#milestones)
8. [Boards](#boards)
9. [Common Query Parameters](#common-query-parameters)

---

## Projects

### List all projects
```
GET /projects.json
```
Returns: `{ "projects": [...] }`

Key fields per project: `id`, `name`, `description`, `status`, `startDate`, `endDate`, `company`

### Get a single project
```
GET /projects/{id}.json
```

### Get project stats
```
GET /projects/{id}/stats.json
```
Returns task counts by status, time totals, milestone progress.

### Project metrics (from Postman collection)
```
GET /projects/metrics/active.json    — Count of active projects
GET /projects/metrics/healths.json   — Health summary across all projects
GET /projects/metrics/billable.json  — Total billable time per project
GET /projects/metrics/owners.json    — Owned and unassigned project counts
```

### Export project data
```
GET /projects.csv    — CSV export
GET /projects.xlsx   — Excel export
GET /projects.html   — HTML report
GET /projects.pdf    — PDF report
```

### People on a project
```
GET /projects/{projectId}/people.json
```

---

## Tasks

### List all tasks
```
GET /tasks.json
```

### List tasks with filters
```
GET /tasks.json?tagIds={tagId}&assignedToUserIds={userId}&statuses=active&includeEstimatedTime=true
```

**Key query parameters:**

| Parameter | Description | Example |
|---|---|---|
| `tagIds` | Filter by tag ID (comma-separated for multiple) | `tagIds=12345` |
| `assignedToUserIds` | Filter by assignee | `assignedToUserIds=67890` |
| `projectIds` | Filter by project | `projectIds=111` |
| `statuses` | Filter by status: `active`, `completed`, `all` | `statuses=active` |
| `includeEstimatedTime` | Include time estimates | `includeEstimatedTime=true` |
| `include` | Sideload related data | `include=tags,assignees` |
| `startDate` | Tasks starting after this date | `startDate=2026-01-01` |
| `endDate` | Tasks due before this date | `endDate=2026-01-31` |
| `orderBy` | Sort field | `orderBy=dueDate` |
| `pageSize` | Items per page (max 500) | `pageSize=250` |

### Get a single task
```
GET /tasks/{id}.json
```

Key fields per task:
- `id`, `name`, `description`
- `status` — "new", "active", "completed", etc.
- `priority` — "none", "low", "medium", "high"
- `progress` — 0-100 integer
- `estimatedMinutes` — estimated time in minutes
- `dueDate` — ISO date string or null
- `assignees` — array of user objects (when using `include=assignees`)
- `tags` — array of tag objects (when using `include=tags`)
- `parentTaskId` — for subtasks
- `taskListId` — which task list this belongs to
- `createdAt`, `updatedAt`

### Get subtasks
```
GET /tasks/{id}/subtasks.json
```

### Task metrics (from Postman collection)
```
GET /tasks/metrics/complete.json   — Total count of completed tasks
GET /tasks/metrics/late.json       — Total count of late/overdue tasks
```

These are useful for quick dashboard-style summaries without fetching all task details.

### Update a task
```
PUT /tasks/{id}.json
Content-Type: application/json

{
  "task": {
    "status": "completed",
    "progress": 100
  }
}
```

---

## Task Lists

### List task lists in a project
```
GET /projects/{projectId}/tasklists.json
```

### Get tasks within a task list
```
GET /tasklists/{tasklistId}/tasks.json
```

---

## Tags

### List all tags
```
GET /tags.json
```

Returns: `{ "tags": [{ "id": 123, "name": "Sprint-25", "color": "#ff0000" }, ...] }`

### Get tasks by tag
Use the tasks endpoint with `tagIds` filter:
```
GET /tasks.json?tagIds={tagId}&include=tags,assignees&includeEstimatedTime=true
```

### Finding sprint tags
Sprint tags typically follow a naming pattern like `Sprint-25`, `Sprint 25`, or `S25`. To find them:
1. Fetch all tags: `GET /tags.json`
2. Filter by name pattern (e.g., names starting with "Sprint")
3. Use the tag ID to fetch associated tasks

---

## Time Entries

### List time entries for a task
```
GET /tasks/{taskId}/time.json
```

### List all time entries (with date range)
```
GET /time.json?fromDate=2026-01-01&toDate=2026-01-31
```

### List time entries for a project
```
GET /projects/{projectId}/time.json
```

**Key query parameters:**

| Parameter | Description | Example |
|---|---|---|
| `fromDate` | Start of date range (YYYYMMDD) | `fromDate=20260101` |
| `toDate` | End of date range (YYYYMMDD) | `toDate=20260131` |
| `userId` | Filter by person (comma-separated for multiple) | `userId=384930,381144,383404` |
| `projectId` | Filter by project | `projectId=111` |
| `taskId` | Filter by task | `taskId=222` |

Key fields per time entry:
- `id`
- `taskId`
- `userId`, `userName`
- `minutes` — logged time in minutes
- `hours`, `minutes` — alternative breakdown
- `date` — the date the work was done
- `description` — what was done
- `isBillable` — boolean

### Timelog totals (aggregated — from Postman collection)
These return pre-aggregated totals, so you don't need to sum individual entries:
```
GET /time/total.json                    — All timelog totals
GET /projects/{id}/time/total.json      — Timelog totals for a project
GET /tasks/{id}/time/total.json         — Timelog totals for a specific task
```

### Time entries for an allocation
```
GET /allocations/{allocationId}/time.json
```

### Running timers
```
GET /me/timers.json          — Your own running timers
GET /timers.json             — All running timers
GET /timers/{timerId}.json   — A specific timer
```

### Calculate actual time for a task
Sum the `minutes` field across all time entries for that task, or use the totals endpoint `/tasks/{id}/time/total.json` for a pre-aggregated value. Compare with the task's `estimatedMinutes` for variance analysis.

---

## People

### List all people
```
GET /people.json
```

Key fields: `id`, `firstName`, `lastName`, `email`, `company`, `isAdmin`

### Get a person's tasks
```
GET /tasks.json?assignedToUserIds={userId}&statuses=active
```

### People metrics (from Postman collection)
```
GET /people/metrics/performance.json   — Users completing the most tasks
GET /people/utilization.json           — User utilization data
```

These are very useful for sprint planning — utilization shows who has capacity, and performance data helps calibrate assignments.

---

## Milestones

### List milestones
```
GET /projects/{projectId}/milestones.json
```

### Get a milestone
```
GET /milestones/{id}.json
```

Key fields: `id`, `title`, `deadline`, `completed`, `responsiblePartyIds`

### Milestone metrics (from Postman collection)
```
GET /milestones/metrics/deadlines.json   — Milestones by due date in a time range
```

### Export milestones
```
GET /milestones.csv
GET /milestones.xlsx
GET /milestones.html
GET /milestones.pdf
```

---

## Task Lists

### Get all task lists
```
GET /tasklists
```

### Get task lists in a project
```
GET /projects/{projectId}/tasklists
```

### Export task lists
```
GET /projects/{projectId}/tasklists.csv
GET /projects/{projectId}/tasklists.xlsx
```

---

## Risks

### Get all risks
```
GET /risks.json
```

### Get risks for a project
```
GET /projects/{projectId}/risks
```

---

## Activity & Updates

### Latest activity (all projects)
```
GET /latestactivity
```

### Latest activity for a project
```
GET /projects/{projectId}/latestactivity
```

### Project updates
```
GET /projects/updates.json              — All project updates
GET /projects/{projectId}/updates.json  — Updates for a specific project
```

---

## Workload

The API includes a Workload section for capacity planning. Check available endpoints at your Teamwork instance.

---

## Workflows

Workflows provide a cross-project Kanban-style view for tasks organized into stages. The workflows endpoint is highly efficient because it supports **sideloading** related data (projects, tasklists, tags, users, timeTotals) in a single response.

### Get workflow details
```
GET /workflows/{workflowId}.json
```
Returns workflow metadata including stages.

### List tasks in a workflow stage
```
GET /workflows/{workflowId}/stages/{stageId}/tasks.json
```

**Key query parameters:**

| Parameter | Description | Example |
|---|---|---|
| `tagIds` | Filter by tag ID | `tagIds=138509` |
| `status` | Task status filter | `status=all` |
| `includeCompletedTasks` | Include completed tasks | `includeCompletedTasks=true` |
| `include` | Sideload related data | `include=users,timeTotals,projects,tasklists,tags,parentTasks,subtaskStats` |
| `fields[projects]` | Sparse fieldset for projects | `fields[projects]=id,name,companyId,status,type` |
| `fields[tasklists]` | Sparse fieldset for tasklists | `fields[tasklists]=id,projectId,name` |
| `pageSize` | Items per page (max 500) | `pageSize=500` |

**Response format:**

The response includes a `tasks` array and an `included` section with sideloaded data:

```json
{
  "tasks": [
    {
      "id": 42774623,
      "name": "Task Name",
      "status": "new",
      "estimateMinutes": 270,
      "tagIds": [136610, 138509],
      "tags": [{"id": 136610, "type": "tags"}, ...],
      "assigneeUserIds": [381144],
      "tasklistId": 3272209,
      "parentTaskId": 42508880,
      "workflowStages": [{"workflowId": 78859, "stageId": 452716, "stageTaskDisplayOrder": 1924.25}]
    }
  ],
  "included": {
    "timeTotals": {
      "42774623": {"loggedMinutes": 645, "billedloggedMinutes": 345, "billableLoggedMinutes": 645}
    },
    "projects": {"740934": {"id": 740934, "name": "Project Name", ...}},
    "tasklists": {"3272209": {"id": 3272209, "name": "Tasklist Name", "projectId": 740934}},
    "tags": {"136610": {"id": 136610, "name": "PMD", "color": "#2f8de4"}},
    "users": {"381144": {"id": 381144, "firstName": "Rodolfo", "lastName": "Ortiz", ...}}
  }
}
```

**Key notes:**
- `tagIds` on tasks is a flat `[int]` array; `tags` are type references (`{"id": N, "type": "tags"}`)
- Full tag data (with names) is in `included.tags`
- `timeTotals` is keyed by task ID string: `{"42774623": {"loggedMinutes": 645, ...}}`
- `estimateMinutes` (not `estimatedMinutes`) is the field name in workflow responses
- `workflowStages` on each task identifies which stage (board column) it belongs to
- This endpoint is used by the sprint summary script to replace multiple individual API calls

---

## Boards

Boards provide a Kanban-style workflow view for tasks. Each project can have board columns representing workflow stages (e.g., "To Do", "In Progress", "On Staging", "Ready for Production", "On Production", "Done"). Tasks appear as cards within columns.

### List board columns for a project
```
GET /projects/{projectId}/boards/columns.json
```

**Query parameters:**

| Parameter | Description | Example |
|---|---|---|
| `page` | Page number (1-based) | `page=1` |
| `pageSize` | Items per page | `pageSize=50` |
| `getStats` | Include card count stats per column | `getStats=true` |

Returns: `{ "columns": [...] }`

Key fields per column:
- `id` — Column ID
- `name` — Column display name (e.g., "On Staging", "Done")
- `color` — Hex color string
- `displayOrder` — Sort order (integer)
- `projectId` — Parent project ID
- `stats` — Object with `total` card count (when `getStats=true`)

### Get a single board column
```
GET /boards/columns/{columnId}.json
```

### List cards in a column
```
GET /boards/columns/{columnId}/cards.json
```

Returns: `{ "cards": [...] }`

Key fields per card:
- `id` — Card ID
- `taskId` — The Teamwork task ID this card represents
- `columnId` — Which column the card is in
- `name` — Card/task name
- `status` — Card status
- `taskStatus` — The underlying task's status
- `displayOrder` — Sort order within the column

### Move a card between columns
```
PUT /boards/columns/cards/{cardId}/move.json
Content-Type: application/json

{
  "card": {
    "columnId": {targetColumnId}
  }
}
```

### Determining a task's board status

To find which board column a task is in:
1. Identify the task's `projectId`
2. Fetch columns: `GET /projects/{projectId}/boards/columns.json?getStats=true`
3. For each column with cards (`stats.total > 0`), fetch cards: `GET /boards/columns/{columnId}/cards.json`
4. Match `card.taskId` to your task's `id`

The helper function `tw_api.get_board_status_for_tasks(tasks)` automates this pattern — it groups tasks by project, fetches columns and cards, and returns a `{task_id: column_name}` mapping.

---

## Common Query Parameters

These work across most list endpoints:

| Parameter | Description |
|---|---|
| `page` | Page number (1-based) |
| `pageSize` | Items per page (default 50, max 500) |
| `orderBy` | Sort field name |
| `orderMode` | `asc` or `desc` |
| `updatedAfter` | ISO datetime — only items updated after this |
| `fields[tasks]` | Sparse fieldset — only return specified fields |
| `include` | Sideload related resources (comma-separated) |

## Pagination Handling

Check for more pages in the response metadata:
```json
{
  "meta": {
    "page": {
      "pageOffset": 0,
      "pageSize": 50,
      "count": 50,
      "hasMore": true
    }
  }
}
```

When `hasMore` is `true`, increment the page number and fetch again until all results are collected.

---

## Rate Limits

Teamwork enforces rate limits (typically 150 requests per minute). If you receive a `429` response:
1. Check the `Retry-After` header for wait time
2. Back off and retry after that duration
3. For bulk operations, add small delays between requests

## Notes

- All times are in **minutes** unless otherwise specified. Divide by 60 for hours.
- Dates use **ISO 8601** format (YYYY-MM-DD or full datetime).
- Tag names are **case-sensitive** in filters.
- The `include` parameter is powerful — use it to avoid N+1 request patterns. For example, `include=tags,assignees` on a tasks query returns all tag and assignee data inline.
- Some older Teamwork instances may still use v1 endpoints (`/projects/api/v1/`). The v1 response format wraps data differently (e.g., `"todo-items"` instead of `"tasks"`). Prefer v3 when available.
