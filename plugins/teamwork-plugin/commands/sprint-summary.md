---
description: Generate a sprint summary Excel report with task breakdown and time analysis
---

# Sprint Summary Report

Generate a comprehensive Excel sprint summary with task status breakdown and team time analysis.

## When invoked

1. **Prompt the user** for the following information:
   - **Sprint number** (e.g., 45)
   - **Sprint start date** in YYYY-MM-DD format (e.g., 2026-02-24)
   - **Sprint end date** in YYYY-MM-DD format (e.g., 2026-03-07)

2. **Verify credentials** are set before running the script:
   ```bash
   echo "TEAMWORK_USERNAME: ${TEAMWORK_USERNAME:-NOT_SET}"
   echo "TEAMWORK_PASSWORD: ${TEAMWORK_PASSWORD:-NOT_SET}"
   ```
   If either shows `NOT_SET`, collect credentials using the question-prompt interface (AskUserQuestion) — **do NOT ask via regular chat messages**:
   - Use AskUserQuestion to ask for their Teamwork email address (header: "Credentials")
   - Use AskUserQuestion to ask for their password (header: "Password")
   - Then silently export them (never echo the password):
   ```bash
   export TEAMWORK_USERNAME="their-email"
   export TEAMWORK_PASSWORD="their-password"
   ```

3. **Ensure openpyxl is installed**:
   ```bash
   pip install openpyxl 2>/dev/null || pip3 install openpyxl 2>/dev/null
   ```

4. **Run the sprint summary script** with the user's inputs:
   ```bash
   python3 scripts/sprint_summary.py --sprint-number <N> --start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD>
   ```

5. **Present the results** to the user:
   - Tell them the file name and location of the generated Excel report
   - Show a brief text summary of the key metrics from the JSON output
   - If the script exits with code 2, prompt for credentials and retry
   - If the script reports an error finding the sprint tag, show the available tags and ask the user to clarify

## Output

The script generates an Excel file named `Sprint_{N}_Summary.xlsx` with two tabs:

- **Sprint Task Summary** — Breaks down tasks by type (Carryover, Planned, Unplanned) with completion, staging, and production status counts and percentages, plus estimated vs. logged hours for completed tasks.
- **Sprint Time Summary** — Per-person time breakdown for Rodolfo Ortiz, Ulises Becerra, and Fernando Mendez showing total, billable, non-billable, planned, unplanned, and other hours.
