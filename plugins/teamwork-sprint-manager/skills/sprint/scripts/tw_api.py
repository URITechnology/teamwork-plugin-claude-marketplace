"""
Teamwork Projects API client library.
Shared utilities used by all sprint manager scripts.
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error
import urllib.parse
import time


# Module-level credential cache so we only prompt once per session
_cached_config = None


def get_config():
    """
    Get Teamwork config, prompting the user if credentials aren't set.
    Credentials are cached in memory for the duration of the session,
    so the user is only asked once.
    """
    global _cached_config
    if _cached_config is not None:
        return _cached_config

    site = os.environ.get("TEAMWORK_SITE", "urimarketing.teamwork.com").strip()
    username = os.environ.get("TEAMWORK_USERNAME", "").strip()
    password = os.environ.get("TEAMWORK_PASSWORD", "").strip()

    # If credentials aren't in env vars, print a message so the calling
    # Claude skill knows to ask the user and set them before retrying.
    if not username or not password:
        print("CREDENTIALS_NEEDED", file=sys.stdout)
        print("Teamwork credentials are not configured for this session.", file=sys.stderr)
        print("Please set them with:", file=sys.stderr)
        print("  export TEAMWORK_USERNAME='your-email@urimarketing.com'", file=sys.stderr)
        print("  export TEAMWORK_PASSWORD='your-password'", file=sys.stderr)
        sys.exit(2)  # Exit code 2 = credentials needed (distinct from other errors)

    # Strip protocol if user included it
    site = site.replace("https://", "").replace("http://", "").rstrip("/")

    _cached_config = {"site": site, "username": username, "password": password}
    return _cached_config


def clear_config_cache():
    """Clear cached credentials (e.g., after an auth failure)."""
    global _cached_config
    _cached_config = None


def make_request(endpoint, params=None, method="GET", body=None, max_retries=3):
    """
    Make an authenticated request to the Teamwork API.

    Args:
        endpoint: API path (e.g., '/tasks.json')
        params: dict of query parameters
        method: HTTP method
        body: dict to send as JSON body (for POST/PUT)
        max_retries: number of retries on rate limit

    Returns:
        Parsed JSON response
    """
    config = get_config()
    base_url = f"https://{config['site']}/projects/api/v3"

    url = f"{base_url}{endpoint}"

    if params:
        query_string = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}?{query_string}"

    # Basic auth: username and password
    credentials = base64.b64encode(f"{config['username']}:{config['password']}".encode()).decode()

    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    data = None
    if body:
        data = json.dumps(body).encode("utf-8")

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as e:
            if e.code == 429:
                # Rate limited — back off
                retry_after = int(e.headers.get("Retry-After", 10))
                print(f"Rate limited. Waiting {retry_after}s before retry {attempt + 1}/{max_retries}...", file=sys.stderr)
                time.sleep(retry_after)
                continue
            elif e.code == 401:
                clear_config_cache()
                print("ERROR: Authentication failed (401). Check your username and password.", file=sys.stderr)
                sys.exit(1)
            elif e.code == 404:
                print(f"ERROR: Not found (404) for endpoint: {endpoint}", file=sys.stderr)
                return None
            else:
                print(f"ERROR: HTTP {e.code} for {url}", file=sys.stderr)
                print(f"Response: {e.read().decode('utf-8', errors='replace')}", file=sys.stderr)
                sys.exit(1)

        except urllib.error.URLError as e:
            print(f"ERROR: Could not connect to {config['site']}: {e.reason}", file=sys.stderr)
            sys.exit(1)

    print("ERROR: Max retries exceeded due to rate limiting.", file=sys.stderr)
    sys.exit(1)


def fetch_all_pages(endpoint, params=None, result_key=None, page_size=250):
    """
    Fetch all pages of a paginated endpoint.

    Args:
        endpoint: API path
        params: query parameters
        result_key: the key in the response that holds the array (e.g., 'tasks', 'tags')
                    If None, tries to auto-detect.
        page_size: items per page (max 500)

    Returns:
        List of all items across all pages
    """
    if params is None:
        params = {}
    params["pageSize"] = page_size
    params["page"] = 1

    all_items = []

    while True:
        response = make_request(endpoint, params)
        if response is None:
            break

        # Auto-detect result key if not specified
        if result_key is None:
            for key in response:
                if isinstance(response[key], list):
                    result_key = key
                    break
            if result_key is None:
                print(f"WARNING: Could not detect result key in response for {endpoint}", file=sys.stderr)
                break

        items = response.get(result_key, [])
        all_items.extend(items)

        # Check for more pages
        meta = response.get("meta", {}).get("page", {})
        if not meta.get("hasMore", False):
            break

        params["page"] += 1

    return all_items


def find_sprint_tags(pattern=None):
    """
    Find tags that look like sprint tags.

    Args:
        pattern: optional string to filter tag names (case-insensitive).
                 If None, looks for common patterns like 'Sprint', 'S-', etc.

    Returns:
        List of tag dicts sorted by name
    """
    tags = fetch_all_pages("/tags.json", result_key="tags")

    sprint_tags = []
    for tag in tags:
        name = tag.get("name", "")
        if pattern:
            if pattern.lower() in name.lower():
                sprint_tags.append(tag)
        else:
            # Common sprint naming patterns
            name_lower = name.lower()
            if any(p in name_lower for p in ["sprint", "s-", "iteration", "iter-"]):
                sprint_tags.append(tag)

    return sorted(sprint_tags, key=lambda t: t.get("name", ""))


def get_tasks_for_tag(tag_id, include_time=True):
    """
    Fetch all tasks with a given tag, optionally including time data.

    Args:
        tag_id: Teamwork tag ID
        include_time: whether to include estimated time info

    Returns:
        List of task dicts
    """
    params = {
        "tagIds": tag_id,
        "include": "tags,assignees",
        "includeEstimatedTime": "true" if include_time else "false",
        "statuses": "all",
    }
    return fetch_all_pages("/tasks.json", params, result_key="tasks")


def get_time_entries_for_task(task_id):
    """Fetch all time entries logged against a task."""
    return fetch_all_pages(f"/tasks/{task_id}/time.json", result_key="timelog")


def get_time_entries_for_tasks(task_ids):
    """
    Fetch time entries for multiple tasks.
    Returns dict mapping task_id -> list of time entries.
    """
    result = {}
    for task_id in task_ids:
        entries = get_time_entries_for_task(task_id)
        result[task_id] = entries
        # Small delay to avoid rate limits on large sprints
        if len(task_ids) > 20:
            time.sleep(0.2)
    return result


def minutes_to_hours(minutes):
    """Convert minutes to hours, rounded to 1 decimal."""
    if minutes is None or minutes == 0:
        return 0.0
    return round(minutes / 60, 1)


def format_duration(minutes):
    """Format minutes as 'Xh Ym' string."""
    if minutes is None or minutes == 0:
        return "0h"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{mins}m"
