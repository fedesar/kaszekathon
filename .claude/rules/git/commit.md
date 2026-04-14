---
description: Generate a Conventional Commit message in English using only the staged diff and the current branch name. If staging has not been done yet, first ask the user whether they want to stage all modified files or only some of them.

alwaysApply: false
---

# Rule: Commit

## Intent

When the user writes `commit`, guide the user through the correct commit flow and generate a high-quality Conventional Commit message in English.

This rule is responsible for:

- checking whether staging is still needed
- asking the user how they want to stage files when necessary
- using only the staged diff as the source of truth for the commit message
- generating an informative commit message
- returning the commands in the correct order

---

## Sources of Truth

Use only:

1. the staged diff
2. the current branch name

Do not use:

- unstaged changes as the basis for the final commit message
- untracked files unless the user explicitly chooses to stage them
- assumptions based on unrelated repository context
- the full diff if it differs from the staged diff

If nothing is staged yet, do not generate the final commit message from all modified files.
First resolve staging.

---

## Required Staging Behavior

If staging has not been done yet:

1. Show the list of modified files

2. Ask the user whether they want to:
   - stage all modified files
   - stage only some of them

If the user chooses to stage only some files:
- show the full list of currently modified files
- let the user choose exactly which files to stage from that list
- only then generate the corresponding `git add <selected-files>` command

3. Only after that, continue with the commit flow

Use this staging order:

- first decide what to stage
- then stage the selected files
- then generate the commit message from the staged diff
- then return the commit command

Do not assume `git add .` by default without asking first.

Prefer:
- `git add <specific-files>` when the user wants only selected files
- `git add .` only when the user explicitly wants all relevant current changes staged

---

## Pre-Commit Review Dependency

Before generating the final commit message, you MUST perform a pre-commit review.

This review must be based only on the staged diff.

### Flow

1. Load `pre-commit-review.md`
2. Review the staged changes
3. If issues are found:
   - show findings clearly
   - recommend fixing them before committing
   - STOP the commit flow until the user confirms or fixes them
4. If no relevant issues are found:
   - approve the changes
   - continue with the commit flow

Do NOT skip this step.

The commit must not be generated before the review is completed.

---

## Required Commit Flow

The correct order is:

```bash```
git add <files>   # or git add .
git commit -m "<generated_commit_message>"

---

The commit message must follow the Conventional Commits format:

<type>: <short description>

<body explaining what changed and why>

Refs: RD-XXXX

---

## Types

Use the most accurate type:

- feat: new functionality
- fix: bug fix
- refactor: code restructuring without behavior change
- style: formatting changes without logic changes
- chore: maintenance, tooling, or configuration
- docs: documentation only
- test: adding or updating tests

---

## Why the body matters

The body is important because it helps reviewers understand:
- what changed
- where it changed
- why it changed

This avoids the need to open every modified file during code review.

---

## Description Rules

The description must:

- be written in English
- use imperative mood
- be concise but specific
- reflect the main intent of the staged changes

Avoid vague descriptions such as:

- update stuff
- fixes
- improvements
- changes

---

## Modified Files

When useful for clarity, include key modified files:

- update onboarding validation in src/services/onboardingService.ts
- modify parser logic in src/utils/parser.ts

Rules:

- include only relevant files
- do not list every minor change
- keep paths concise

---

### Footer Rules

If the branch contains an issue key (e.g. RD-1605), include:

Refs: <ISSUE-KEY>

Rules:

- preserve uppercase
- do not invent issue keys
- do not include footer if none exists

---

## Example

feat: add validation for onboarding payload

- validate required fields before processing
- add fallback handling for optional attributes
- improve error messages for invalid inputs
- update validation logic in src/services/onboardingService.ts
- modify parser behavior in src/utils/parser.ts

Refs: RD-1605

---

## Post-Commit Behavior

After generating the commit:

Ask the user:

"Do you want to push this commit?"

If the user answers yes:
- load `push.md`
- execute push flow

If the user answers no:
- stop after commit