# GitHub Issue Triage Agent

An AI agent that connects to a **real GitHub repository**, reads its open
issues, summarizes and triages them (priority + suggested label + next action),
and can **post a triage comment back** to an issue.

It works against live GitHub issues. Runs from the command line,
so anyone can clone it and try it on their own repo.

## What this demonstrates

This is a working example of an **AI agent**: a language model running in a
loop, with **tools** it can call and **memory** of the conversation. The model
decides which tool to use; the code runs it and feeds the result back; the
loop continues until the model has an answer.

Tools the agent has:
- `list_issues` — list open issues in the repo
- `get_issue` — read one issue's full text and labels
- `comment_on_issue` — post a comment (a real write action; only when asked)

## How it works (the agent loop)

```
you ask  ->  model decides: answer or call a tool
                     |
              calls a tool  ->  code runs it  ->  result back to model
                     |                                   |
                     +-----------------<-----------------+
                     |
              no tool needed  ->  final answer
```

The model does the reasoning (summarizing, prioritizing). The tools only fetch
data and take actions. That separation is the core idea of an agent.

## Setup

### 1. Install dependencies

pip install -r requirements.txt


### 2. Get your credentials (all free)

- **OpenAI API key** — from platform.openai.com .
- **GitHub personal access token** — GitHub → Settings → Developer settings →
  Personal access tokens → Classic Token. Give it access to the repo you
  want, with **Issues: Read and write** permission.

### 3. Set environment variables
```bash
export GEMINI_API_KEY="your-gemini-key"
export GITHUB_TOKEN="your-github-token"
export GITHUB_REPO="your-username/your-test-repo"
```

(See `.env.example`. Never commit your real keys.)

### 4. Run it
```bash
python agent.py
```

Then try:
```
you > triage all the open issues and tell me which to fix first
you > summarize issue 1 and suggest a label
you > post a triage comment on issue 1
```

## A note on safety

The agent will **not** post comments unless you explicitly ask it to. Write
actions stay under human control by design. Point `GITHUB_REPO` at a test
repo you own so you're never writing to someone else's project.

## What I learned building this

- The agent loop: model → tool call → result → repeat → answer
- Tool use and why clear tool descriptions matter
- Integrating a real external API (GitHub) with authentication
- The difference between an agent that only reads and one that takes actions
- Keeping write actions human-controlled (responsible-AI design)
