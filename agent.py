"""
=============================================================================
 GITHUB ISSUE TRIAGE AGENT
=============================================================================

 An AI agent that connects to a REAL GitHub repository, reads its actual
 open issues, summarizes and triages them, and can post a comment back.

 Reads AND writes. Runs from the command line so
 anyone can clone this repo and try it themselves.

"""

import os
import json
import requests
from openai import OpenAI


# =============================================================================
# SECTION 1 — CONFIG & CREDENTIALS
# =============================================================================
# Set these in your terminal before running:
#   export OPENAI_API_KEY="your-openai-key"
#   export GITHUB_TOKEN="your-github-token"
#   export GITHUB_REPO="your-username/triage-test-issues"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN")
REPO           = os.environ.get("GITHUB_REPO", "octocat/Hello-World")

if not OPENAI_API_KEY:
    raise SystemExit("Missing OPENAI_API_KEY. Set it in your terminal first.")
if not GITHUB_TOKEN:
    print("WARNING: No GITHUB_TOKEN set. Writes (comments) will fail.")

client = OpenAI(api_key=OPENAI_API_KEY)
MODEL  = "gpt-4o-mini"   # cheap, fast, more than smart enough for triage

GH_API     = "https://api.github.com"
GH_HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}" if GITHUB_TOKEN else "",
}


# =============================================================================
# SECTION 2 — THE TOOLS (real functions that hit the real GitHub API)
# =============================================================================
#
# With OpenAI, tools are described in a JSON schema dict (unlike Gemini which
# reads docstrings). The description fields are how the model decides when to
# call each tool — write them clearly.
#
# TEST EACH TOOL ON ITS OWN before running the full agent (see bottom of file).

def list_issues() -> list:
    url  = f"{GH_API}/repos/{REPO}/issues"
    resp = requests.get(url, headers=GH_HEADERS,
                        params={"state": "open", "per_page": 20}, timeout=15)
    resp.raise_for_status()
    return [
        {"number": i["number"], "title": i["title"], "author": i["user"]["login"]}
        for i in resp.json()
        if "pull_request" not in i   # GitHub mixes PRs into this endpoint
    ]

def get_issue(issue_number: int) -> dict:
    url  = f"{GH_API}/repos/{REPO}/issues/{issue_number}"
    resp = requests.get(url, headers=GH_HEADERS, timeout=15)
    if resp.status_code == 404:
        return {"error": f"No issue #{issue_number} found in {REPO}"}
    resp.raise_for_status()
    i = resp.json()
    return {
        "number": i["number"],
        "title":  i["title"],
        "author": i["user"]["login"],
        "body":   (i.get("body") or "")[:2000],   # trim very long bodies
        "labels": [l["name"] for l in i.get("labels", [])],
    }

def comment_on_issue(issue_number: int, comment: str) -> dict:
    if not GITHUB_TOKEN:
        return {"error": "No GITHUB_TOKEN set, cannot write."}
    url  = f"{GH_API}/repos/{REPO}/issues/{issue_number}/comments"
    resp = requests.post(url, headers=GH_HEADERS,
                         json={"body": comment}, timeout=15)
    resp.raise_for_status()
    return {"posted": True, "url": resp.json().get("html_url")}


# Map tool names to real functions so the loop can call them by name.
TOOL_FUNCTIONS = {
    "list_issues":      list_issues,
    "get_issue":        get_issue,
    "comment_on_issue": comment_on_issue,
}

# OpenAI tool schemas — describe each tool so the model knows when to use it.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_issues",
            "description": "List all open issues in the repository (number, title, author). Use this first to see what issues exist.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_issue",
            "description": "Get the full details of one issue including its body and labels. Use this to read or summarize a specific issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_number": {
                        "type": "integer",
                        "description": "The issue number to fetch (e.g. 3).",
                    }
                },
                "required": ["issue_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "comment_on_issue",
            "description": "Post a comment on a GitHub issue. This WRITES to GitHub — only use when the user explicitly asks to post or comment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_number": {
                        "type": "integer",
                        "description": "The issue number to comment on.",
                    },
                    "comment": {
                        "type": "string",
                        "description": "The comment text to post.",
                    },
                },
                "required": ["issue_number", "comment"],
            },
        },
    },
]


# =============================================================================
# SECTION 3 — THE SYSTEM PROMPT (the agent's job description)
# =============================================================================

SYSTEM_PROMPT = """You are a GitHub issue triage assistant.

You help a maintainer by:
- Summarizing issues into one clear sentence.
- Assigning a priority: P1 (broken/blocking), P2 (important but not blocking), P3 (minor/nice-to-have).
- Suggesting a label and the next action.

Rules:
- Use the tools to read real issue data before judging anything.
- NEVER post a comment unless the user explicitly asks you to post/comment.
- When you do post, keep the comment short, professional, and clearly a triage suggestion.
- You assist a human maintainer; you do not claim to have fixed anything yourself.
- Be concise and practical."""


# =============================================================================
# SECTION 4 — THE AGENT LOOP (the heart of everything)
# =============================================================================
#
# OpenAI's loop is slightly different from Gemini's in structure but the IDEA
# is identical: model responds → if tool call → run it → feed result back → repeat.
#
# Key difference from Gemini: OpenAI uses a flat messages list (dicts) instead
# of typed Content/Part objects. Tool results go in as role="tool" messages.

def run_agent(user_message: str, verbose: bool = True) -> str:
    # MEMORY: flat list of message dicts. Start with the user's question.
    messages = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": user_message},
    ]

    while True:  # the agent loop
        response = client.chat.completions.create(
            model=MODEL,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        msg = response.choices[0].message

        # Save the model's turn to memory.
        messages.append(msg)

        # Did the model ask to call any tools?
        if msg.tool_calls:
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)

                if verbose:
                    print(f"  [tool call: {fn_name}({fn_args})]")

                # Run the real function.
                result = TOOL_FUNCTIONS[fn_name](**fn_args)

                # Feed the result back as a tool message so the model can react.
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      json.dumps(result),
                })
            # Loop — let the model react to the tool results.
        else:
            # No tool calls → this is the final answer.
            return msg.content


# =============================================================================
# SECTION 5 — RUN IT (interactive chat loop in the terminal)
# =============================================================================

def main():
    print(f"GitHub Issue Triage Agent — repo: {REPO}  |  model: {MODEL}")
    print("Type a request (e.g. 'triage all open issues'). Type 'quit' to exit.\n")
    while True:
        try:
            user_message = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye!")
            break
        if user_message.lower() in {"quit", "exit", "q"}:
            print("bye!")
            break
        if not user_message:
            continue
        reply = run_agent(user_message)
        print(f"\nagent > {reply}\n")


if __name__ == "__main__":
    main()


# =============================================================================
# HOW TO TEST EACH TOOL BEFORE RUNNING THE FULL AGENT
# =============================================================================
# Open a Python shell with your env vars set, then:
#
#   from agent import list_issues, get_issue
#   print(list_issues())     # should show your real repo's issues
#   print(get_issue(1))      # should show issue #1's full body
#
# THINGS TO TRY ONCE IT RUNS (watch the [tool call: ...] lines):
#   "triage all the open issues and tell me which to fix first"
#   "summarize issue 3 and suggest a label"
#   "post a triage comment on issue 3 with your suggested priority"   <- WRITE