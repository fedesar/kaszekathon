---
description: Execute a one-shot flow that stages everything, auto-generates a Conventional Commit message, and pushes the current branch without asking for confirmations or showing commands.

alwaysApply: false
---

# Rule: Flow (one-shot add + commit + push)

## Intent

When the user writes `flow` (or `fast push` / `fast commit` / `fast`), stage everything, generate the commit message using the same conventions as `commit.md`, and push the current branch to origin without follow-up questions or command prompts.

## Behavior

- do not ask for staging choices or confirmations; always run `git add .` (include untracked)
- auto-generate the commit message from the staged diff using Conventional Commits style (type + concise imperative description, optional body); reuse only the message-quality expectations from `commit.md`, not its staging/review/push flow
- never fall back to a generic or short placeholder message; keep it meaningful and conventional
- use the current branch; if the branch cannot be determined, ask the user instead of inventing one
- skip pre-commit review and tests; this is an intentionally fast path
- execute the flow directly; do not print the command. Only emit a brief success/failure summary (e.g., `flow ready`) and any errors if they occur.

## Command Format
Executed internally (not printed):
```bash
git add . && git commit -m "<generated_commit_message>" && git push origin <current-branch>
```

## Examples
### With message
Input: `flow`

Result:
```
flow ready (pushed to <current-branch>)
```
