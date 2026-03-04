#!/usr/bin/env node
/**
 * Diagnostic test for Teamwork v2 time entries API pagination.
 *
 * Tests whether the v2 API uses meta.page.hasMore (v3 style) or
 * X-Page/X-Pages/X-Records response headers for pagination.
 * Fetches ALL time entries for the sprint date range and computes
 * per-user totals for comparison with the Python Excel output.
 *
 * Usage:
 *   TEAMWORK_API_KEY=twp_xxx node test_v2_time_pagination.js
 *
 * Optional env vars:
 *   TEAMWORK_SITE       (default: urimarketing.teamwork.com)
 *   SPRINT_START_DATE   (default: 2026-02-26)
 *   SPRINT_END_DATE     (default: 2026-03-09)
 */

const https = require("https");
const { Buffer } = require("buffer");

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const CONFIG = {
  site: (process.env.TEAMWORK_SITE || "urimarketing.teamwork.com").replace(/^https?:\/\//, "").replace(/\/+$/, ""),
  apiKey: process.env.TEAMWORK_API_KEY || "",
};

const SPRINT_NUMBER = 43;
const START_DATE = process.env.SPRINT_START_DATE || "2026-02-26";
const END_DATE = process.env.SPRINT_END_DATE || "2026-03-09";
const FROM_DATE = START_DATE.replace(/-/g, ""); // YYYYMMDD
const TO_DATE = END_DATE.replace(/-/g, "");

// Known user IDs from api-endpoints.md
const USER_IDS = [384930, 381144, 383404];
const USER_ID_STR = USER_IDS.join(",");

// Will be populated during the test
const USER_NAMES = {};

if (!CONFIG.apiKey) {
  console.error("ERROR: Set TEAMWORK_API_KEY env var.");
  process.exit(1);
}

// ---------------------------------------------------------------------------
// HTTP helper
// ---------------------------------------------------------------------------

function makeRequest(apiVersion, endpoint, params = {}) {
  return new Promise((resolve, reject) => {
    const qs = new URLSearchParams(params).toString().replace(/%2C/g, ",");
    const path = `/projects/api/${apiVersion}${endpoint}${qs ? "?" + qs : ""}`;

    const options = {
      hostname: CONFIG.site,
      path,
      method: "GET",
      headers: {
        Authorization: `Basic ${Buffer.from(`${CONFIG.apiKey}:x`).toString("base64")}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    };

    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            body: JSON.parse(data),
          });
        } catch (e) {
          reject(new Error(`JSON parse error: ${e.message}\nRaw: ${data.slice(0, 500)}`));
        }
      });
    });
    req.on("error", reject);
    req.end();
  });
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ---------------------------------------------------------------------------
// Diagnostic: inspect raw response structure
// ---------------------------------------------------------------------------

async function diagnosePagination() {
  console.log("=== STEP 1: Diagnose v2 Pagination Structure ===\n");
  console.log(`Date range: ${START_DATE} to ${END_DATE}`);
  console.log(`User IDs: ${USER_ID_STR}\n`);

  // Fetch page 1 with small pageSize to force pagination
  // Include all the params Teamwork UI uses to ensure complete results
  const res = await makeRequest("v2", "/time.json", {
    fromDate: FROM_DATE,
    toDate: TO_DATE,
    userId: USER_ID_STR,
    includeArchivedProjects: "true",
    projectStatus: "all",
    includeTentativeProjects: "true",
    invoicedType: "all",
    billableType: "all",
    page: 1,
    pageSize: 50,
  });

  console.log(`HTTP Status: ${res.statusCode}`);
  console.log(`\n--- Response Headers (pagination-related) ---`);

  const paginationHeaders = ["x-page", "x-pages", "x-records", "x-page-size"];
  for (const h of paginationHeaders) {
    const val = res.headers[h];
    console.log(`  ${h}: ${val !== undefined ? val : "(not present)"}`);
  }

  console.log(`\n--- Response Body Keys ---`);
  const bodyKeys = Object.keys(res.body);
  console.log(`  Keys: ${JSON.stringify(bodyKeys)}`);

  // Check for meta.page (v3 style)
  if (res.body.meta) {
    console.log(`  meta: ${JSON.stringify(res.body.meta)}`);
  } else {
    console.log(`  meta: (not present in body)`);
  }

  // Check for STATUS (v1/v2 style)
  if (res.body.STATUS) {
    console.log(`  STATUS: ${res.body.STATUS}`);
  }

  // Determine the result key
  let resultKey = null;
  for (const key of bodyKeys) {
    if (Array.isArray(res.body[key])) {
      resultKey = key;
      break;
    }
  }
  console.log(`  Result key (first array): "${resultKey}"`);
  if (resultKey) {
    console.log(`  Entries on page 1: ${res.body[resultKey].length}`);
  }

  // Show a sample entry
  if (resultKey && res.body[resultKey].length > 0) {
    const sample = res.body[resultKey][0];
    console.log(`\n--- Sample Time Entry (first entry) ---`);
    console.log(`  Keys: ${JSON.stringify(Object.keys(sample))}`);
    // Show key fields
    for (const f of ["id", "taskId", "task-id", "todoItemId", "todo-item-id",
                      "userId", "user-id", "personId", "person-id",
                      "hours", "minutes", "hoursDecimal",
                      "date", "description", "isbillable", "isBillable",
                      "projectId", "project-id", "project-name"]) {
      if (sample[f] !== undefined) {
        console.log(`  ${f}: ${JSON.stringify(sample[f])}`);
      }
    }
  }

  return {
    xPages: res.headers["x-pages"] ? parseInt(res.headers["x-pages"], 10) : null,
    xRecords: res.headers["x-records"] ? parseInt(res.headers["x-records"], 10) : null,
    hasMetaPage: !!(res.body.meta && res.body.meta.page),
    resultKey,
  };
}

// ---------------------------------------------------------------------------
// Fetch ALL time entries using proper pagination
// ---------------------------------------------------------------------------

async function fetchAllTimeEntries(diagnosis) {
  console.log("\n=== STEP 2: Fetch ALL Time Entries ===\n");

  const allEntries = [];
  let page = 1;
  const pageSize = 500; // Use large page to minimize calls

  while (true) {
    await sleep(450); // Rate limit protection

    const res = await makeRequest("v2", "/time.json", {
      fromDate: FROM_DATE,
      toDate: TO_DATE,
      userId: USER_ID_STR,
      includeArchivedProjects: "true",
      projectStatus: "all",
      includeTentativeProjects: "true",
      invoicedType: "all",
      billableType: "all",
      page,
      pageSize,
    });

    const entries = res.body[diagnosis.resultKey] || [];
    allEntries.push(...entries);

    const xPage = res.headers["x-page"] ? parseInt(res.headers["x-page"], 10) : page;
    const xPages = res.headers["x-pages"] ? parseInt(res.headers["x-pages"], 10) : 1;
    const xRecords = res.headers["x-records"] ? parseInt(res.headers["x-records"], 10) : entries.length;

    console.log(`  Page ${xPage}/${xPages}: ${entries.length} entries (${xRecords} total records)`);

    // Check v2 header-based pagination
    if (xPage >= xPages) {
      break;
    }

    // Also check v3-style meta as fallback
    if (res.body.meta && res.body.meta.page && !res.body.meta.page.hasMore) {
      break;
    }

    page++;
  }

  console.log(`\n  Total entries fetched: ${allEntries.length}`);
  return allEntries;
}

// ---------------------------------------------------------------------------
// Compute per-user totals
// ---------------------------------------------------------------------------

function computeTotals(entries) {
  console.log("\n=== STEP 3: Per-User Time Totals ===\n");

  const byUser = {};

  for (const entry of entries) {
    // Handle v2 field name variations
    const uid = entry["userId"] || entry["user-id"] || entry["personId"] || entry["person-id"];
    const firstName = entry["userFirstName"] || entry["user-first-name"] || "";
    const lastName = entry["userLastName"] || entry["user-last-name"] || "";
    const userName = (firstName && lastName) ? `${firstName} ${lastName}` : (entry["userName"] || entry["user-name"] || entry["personName"] || `User ${uid}`);
    const hours = parseFloat(entry["hours"] || 0);
    const minutes = parseFloat(entry["minutes"] || 0);
    const totalMins = hours * 60 + minutes;
    const isBillable = entry["isbillable"] === "1" || entry["isbillable"] === true || entry["isBillable"] === true;

    if (!uid) continue;

    if (!byUser[uid]) {
      byUser[uid] = {
        userId: uid,
        userName,
        totalMinutes: 0,
        billableMinutes: 0,
        nonBillableMinutes: 0,
        entryCount: 0,
      };
    }

    byUser[uid].totalMinutes += totalMins;
    if (isBillable) {
      byUser[uid].billableMinutes += totalMins;
    } else {
      byUser[uid].nonBillableMinutes += totalMins;
    }
    byUser[uid].entryCount++;

    // Track user names
    if (uid && userName) {
      USER_NAMES[uid] = userName;
    }
  }

  // Print summary
  console.log("  User ID    | Name                | Entries | Total Hrs | Billable | Non-Bill");
  console.log("  -----------|---------------------|---------|-----------|----------|----------");

  for (const uid of USER_IDS) {
    const u = byUser[uid];
    if (u) {
      const totalHrs = (u.totalMinutes / 60).toFixed(2);
      const billHrs = (u.billableMinutes / 60).toFixed(2);
      const nonBillHrs = (u.nonBillableMinutes / 60).toFixed(2);
      console.log(
        `  ${String(u.userId).padEnd(11)}| ${u.userName.padEnd(20)}| ${String(u.entryCount).padEnd(8)}| ${totalHrs.padStart(9)} | ${billHrs.padStart(8)} | ${nonBillHrs.padStart(8)}`
      );
    } else {
      console.log(`  ${String(uid).padEnd(11)}| (no entries)        |       0 |      0.00 |     0.00 |     0.00`);
    }
  }

  return byUser;
}

// ---------------------------------------------------------------------------
// Test what Python's fetch_all_pages would return (simulating the bug)
// ---------------------------------------------------------------------------

async function simulatePythonBug(diagnosis) {
  console.log("\n=== STEP 4: Simulate Python fetch_all_pages Bug ===\n");
  console.log("  Fetching page 1 only (pageSize=500) and checking meta.page.hasMore...\n");

  await sleep(450);
  const res = await makeRequest("v2", "/time.json", {
    fromDate: FROM_DATE,
    toDate: TO_DATE,
    userId: USER_ID_STR,
    includeArchivedProjects: "true",
    projectStatus: "all",
    includeTentativeProjects: "true",
    invoicedType: "all",
    billableType: "all",
    page: 1,
    pageSize: 500,
  });

  const entries = res.body[diagnosis.resultKey] || [];
  const meta = (res.body.meta || {}).page || {};
  const hasMore = meta.hasMore || false;

  console.log(`  Entries on page 1: ${entries.length}`);
  console.log(`  meta.page.hasMore: ${JSON.stringify(hasMore)}`);
  console.log(`  X-Pages header: ${res.headers["x-pages"] || "(not present)"}`);
  console.log(`  X-Records header: ${res.headers["x-records"] || "(not present)"}`);

  if (!hasMore) {
    console.log(`\n  ** CONFIRMED: Python would stop after page 1 because meta.page.hasMore is falsy **`);
    const xRecords = res.headers["x-records"] ? parseInt(res.headers["x-records"], 10) : null;
    if (xRecords && xRecords > entries.length) {
      console.log(`  ** ${xRecords - entries.length} entries are being LOST due to missing pagination **`);
    } else if (xRecords === null) {
      console.log(`  ** Cannot determine total records (no X-Records header) **`);
    } else {
      console.log(`  All ${xRecords} entries fit on page 1 — pagination is NOT the issue.`);
    }
  }

  // Compute totals from just page 1 (what Python currently gets)
  const byUser = {};
  for (const entry of entries) {
    const uid = entry["userId"] || entry["user-id"] || entry["personId"] || entry["person-id"];
    const hours = parseFloat(entry["hours"] || 0);
    const minutes = parseFloat(entry["minutes"] || 0);
    const totalMins = hours * 60 + minutes;
    if (!uid) continue;
    if (!byUser[uid]) byUser[uid] = { totalMinutes: 0, entryCount: 0 };
    byUser[uid].totalMinutes += totalMins;
    byUser[uid].entryCount++;
  }

  console.log("\n  --- Page 1 Only Totals (what Python currently returns) ---");
  for (const uid of USER_IDS) {
    const u = byUser[uid];
    const name = USER_NAMES[uid] || `User ${uid}`;
    if (u) {
      console.log(`  ${name}: ${(u.totalMinutes / 60).toFixed(2)} hrs (${u.entryCount} entries)`);
    } else {
      console.log(`  ${name}: 0.00 hrs (0 entries)`);
    }
  }

  return entries.length;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log("╔══════════════════════════════════════════════════════════╗");
  console.log("║  Teamwork v2 Time API Pagination Diagnostic            ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");
  console.log(`Site: ${CONFIG.site}`);
  console.log(`Sprint: #${SPRINT_NUMBER} (${START_DATE} to ${END_DATE})\n`);

  try {
    // Step 1: Diagnose pagination structure
    const diagnosis = await diagnosePagination();

    // Step 2: Fetch all entries with proper pagination
    const allEntries = await fetchAllTimeEntries(diagnosis);

    // Step 3: Compute and display totals
    computeTotals(allEntries);

    // Step 4: Simulate what Python currently does
    await simulatePythonBug(diagnosis);

    console.log("\n=== DONE ===");
  } catch (err) {
    console.error(`\nFATAL ERROR: ${err.message}`);
    if (err.stack) console.error(err.stack);
    process.exit(1);
  }
}

main();
