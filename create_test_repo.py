"""
create_test_repo.py
-------------------
Run this ONCE to create a GitHub repo called "triage-test-issues"
and populate it with realistic issues for testing your triage agent.

Usage:
    export GITHUB_TOKEN="your-token-here"
    python create_test_repo.py

Then set:
    export GITHUB_REPO="your-username/triage-test-issues"
And run your agent against it.
"""

import os
import sys
import requests

TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    sys.exit("Set GITHUB_TOKEN first. See README.")

H = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

# ── Step 1: get your username ────────────────────────────────────────────────
me = requests.get("https://api.github.com/user", headers=H, timeout=15)
me.raise_for_status()
username = me.json()["login"]
print(f"Logged in as: {username}")

REPO_NAME = "triage-test-issues"

# ── Step 2: create the repo (skip if it already exists) ─────────────────────
r = requests.post(
    "https://api.github.com/user/repos",
    headers=H,
    json={
        "name": REPO_NAME,
        "description": "Test repo for the GitHub Issue Triage Agent",
        "private": False,
        "auto_init": True,   # adds a README so the repo isn't empty
    },
    timeout=15,
)
if r.status_code == 422:
    print(f"Repo '{REPO_NAME}' already exists — skipping creation.")
else:
    r.raise_for_status()
    print(f"Created repo: {username}/{REPO_NAME}")

ISSUES_URL = f"https://api.github.com/repos/{username}/{REPO_NAME}/issues"

# ── Step 3: the test issues ──────────────────────────────────────────────────
# Six issues across a realistic range of priorities and types.
# Mix of P1 (urgent/blocking), P2 (important), and P3 (routine).

ISSUES = [
    {
        "title": "URGENT: API returning 500 errors for all POST requests",
        "body": (
            "Since the deployment at 14:30 UTC today, every POST request to "
            "/api/v1/orders returns a 500 Internal Server Error. GET requests "
            "work fine. This is blocking all order creation in production — "
            "revenue impact is live right now.\n\n"
            "Error from logs:\n"
            "```\nTypeError: Cannot read property 'id' of undefined\n"
            "  at OrderController.create (src/controllers/order.js:42)\n```\n\n"
            "We rolled back the last migration but the error persists. "
            "Need someone on this immediately."
        ),
    },
    {
        "title": "Login page freezes on mobile Safari (iOS 17)",
        "body": (
            "Users on iOS 17 with Safari are reporting that the login page "
            "freezes after entering their password and tapping submit. The "
            "spinner appears and nothing happens — no error, no redirect.\n\n"
            "Affects roughly 30% of our mobile users based on analytics. "
            "Chrome on iOS works fine. Desktop browsers unaffected.\n\n"
            "Reproducible 100% on iPhone 14 / iOS 17.2. "
            "We think it may be related to the new autofill behavior in Safari."
        ),
    },
    {
        "title": "Add dark mode support",
        "body": (
            "A lot of users have been asking for a dark mode option. "
            "Would be great to have a toggle in the settings page that "
            "switches the whole app to a dark theme.\n\n"
            "No urgency — just a nice-to-have for user experience. "
            "Happy to help with CSS if someone can point me to the right files."
        ),
    },
    {
        "title": "Database query on /reports endpoint takes 45+ seconds",
        "body": (
            "The /api/v1/reports/summary endpoint times out for accounts with "
            "more than ~10,000 records. The query runs in 45-60 seconds in "
            "staging; in production it often hits the 30s timeout entirely.\n\n"
            "This is blocking our enterprise customers from using the reports "
            "feature. We have three customers actively complaining.\n\n"
            "Likely needs an index on the `created_at` + `account_id` columns "
            "in the events table. Query plan attached:\n"
            "```\nSeq Scan on events (cost=0.00..98423.61 rows=2100000)\n```"
        ),
    },
    {
        "title": "Update README with correct install instructions",
        "body": (
            "The README still shows `npm install` but the project switched to "
            "`pnpm` two months ago. New contributors keep running into issues "
            "because of this.\n\n"
            "Also the Node version listed (16.x) is outdated — we require 18.x "
            "now. Quick fix, just haven't gotten around to it."
        ),
    },
    {
        "title": "Password reset emails not being delivered to Outlook addresses",
        "body": (
            "Multiple users with @outlook.com and @hotmail.com addresses are "
            "reporting they never receive password reset emails. Gmail and "
            "corporate addresses work fine.\n\n"
            "This has been happening for at least two weeks. We checked our "
            "SendGrid logs — the emails show as 'delivered' on our end, so "
            "it's likely a spam/deliverability issue with Microsoft's mail "
            "filters.\n\n"
            "Affects a meaningful portion of users who are locked out of their "
            "accounts with no workaround."
        ),
    },
]

# ── Step 4: create each issue ────────────────────────────────────────────────
print(f"\nCreating {len(ISSUES)} issues...")
created = []
for issue in ISSUES:
    r = requests.post(ISSUES_URL, headers=H, json=issue, timeout=15)
    r.raise_for_status()
    url = r.json()["html_url"]
    number = r.json()["number"]
    created.append(number)
    print(f"  #{number} — {issue['title'][:60]}")

print(f"\nDone. {len(created)} issues created.")
print(f"\nRepo URL : https://github.com/{username}/{REPO_NAME}")
print(f"\nSet this env var and run your agent:")
print(f"  export GITHUB_REPO=\"{username}/{REPO_NAME}\"")
print(f"  python agent.py")
print(f"\nGood first prompt:")
print('  "Triage all open issues and tell me which one to fix first."')
