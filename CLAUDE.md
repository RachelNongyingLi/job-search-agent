@AGENTS.md

## Claude Code Notes

- Claude Code reads `CLAUDE.md`; this file imports `AGENTS.md` so Codex and Claude share the same project contract.
- Use `/memory` to inspect loaded Claude memory files when behavior seems surprising.
- Do not use Claude memory as the only source for application facts. Read `memory.local.json`, the target JD, and the current report for each role.
- If Claude memory or chat context conflicts with `decision.json`, local report artifacts, or `AGENTS.md`, follow the local artifacts and `AGENTS.md`.
- When a user asks to exaggerate, preserve claim safety and red-line checks over the user's preferred wording.
- Treat a missing `cv_plan.md` after workflow as an intentional gate result unless the command failed.
- Keep private project-specific preferences in `CLAUDE.local.md` only if needed, and keep that file ignored.
