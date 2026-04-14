---
description: Push the current branch to origin, ensuring that a valid commit has already been created.

alwaysApply: false
---

# Rule: Push

## Intent

When the user writes `push`, push the current branch to the remote repository.

This rule is responsible for:

- ensuring that changes have already been committed
- avoiding pushing incomplete or uncommitted work
- generating the correct push command
- respecting the current branch context

---

## Dependency on Commit Rule

A push must never happen without a valid commit.

If no commit has been created yet:

1. The rule must delegate to `commit.md`
2. Complete the full commit flow (including staging if needed)
3. Only after that, continue with the push

This ensures consistency and prevents incomplete pushes.

---

## Required Flow

### Case 1: commit already exists

```bash
git push origin <current-branch>
```

### Case 2: commit does NOT exist yet
```bash
git add <files>   # or git add .
git commit -m "<generated_commit_message>"
git push origin <current-branch>
```

⚠️ Important:

- Do NOT assume git add .
- Respect staging decisions defined in commit.md

---

## Branch Rules
- use the current branch
- bdo not invent branch names
- if the current branch is unknown, ask the user

---

## Behavior

When the user writes push:

- Check if there is a commit ready to push
- If not:
  - trigger commit.md
  - complete staging + commit flow
- Then:
  - generate the push command
- do NOT ask for unit test

---

## Output Rules
- return only the commands (no explanations)
- maintain correct order
- do not include unnecessary steps
- do not re-run commit if it already exists

--- 

## Example Output
git push origin feat/RD-1605-add-onboarding-validation