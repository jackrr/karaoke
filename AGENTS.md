# Karaoke — Agent Guide

@README.md

## Dev workflow

When asked to make any kind of change to the codebase (feature, bugfix, refactor, etc), you should do the following:

1. Have a subagent use the prompt and the contents of the current project (docs, source code, etc) to research the implementation space
2. Have a subagent create an implementation plan using the research outputs
3. Prompt me for approval of the plan. We may iterate on it together.
4. Once I approve, have a software developer subagent implement the plan. Ensure this agent properly verifies functionality: introduces new tests covering changes, verifies all impacted tests pass.
5. Have a subagent code review the changes. If it finds any non-trivial changes, have a software developer subagent make fixes accordingly. Repeat this step up to 2 times.
6. Open a DRAFT pull request with all the changes made. The PR title and description should be extremely succinct and cover: 1) why these changes are made, 2) the most significant changes.
7. Use sway-msg to send me anotification that you're done. Print out the PR url on github and succinctly summarize all work you and the subagents did so I can begin review.

## Verifying changes

### Frontend

Ensure static analysis checks pass:

```
cd frontend && bun run check
```

Ensure tests pass:

```
cd frontend && bun run test
```

### Backend

Ensure static analysis checks pass:

```
cd backend && uv run ruff
cd backend && uv run ty check
```

Ensure tests pass:

```
cd backend && uv run pytest tests/
```
