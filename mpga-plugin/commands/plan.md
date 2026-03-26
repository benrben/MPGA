# /mpga:plan

Generate an evidence-based implementation plan for the active milestone. Evidence First — no fake docs. Build the wall between modules!

## Steps

1. Start the live board in the browser: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board live --serve --open`
2. Read `MPGA/INDEX.md` for active milestone
3. Read the milestone's PLAN.md: `cat MPGA/milestones/<id>/PLAN.md`
4. Read relevant scope documents based on milestone objective
5. Spawn `researcher` plus any needed read-only `scout` agents in parallel if `config.agents.researchBeforePlan` is true
6. Break work into bite-sized tasks (2-10 min each):
   - Each task MUST cite exact files to modify (with evidence links)
   - Each task MUST cite expected test file locations
   - Each task MUST have mechanically verifiable acceptance criteria
   - Each task should declare its scope so independent scopes can run in parallel
   - One write lane per scope
7. Create task cards on the board:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board add "<title>" --priority <p> --scope <scope> --column todo
   ```
8. Write the plan to `MPGA/milestones/<id>/PLAN.md`
9. Show board: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board show`

## Usage
```
/mpga:plan
/mpga:plan M001-auth-system
```

## Plan quality criteria
- [ ] Each task references specific files with evidence links
- [ ] Acceptance criteria are checkboxes, not prose
- [ ] No task is more than 10 minutes of work
- [ ] Dependencies between tasks are explicit
- [ ] Evidence links expected for each task are listed
- [ ] Parallel-safe tasks are separated from same-scope write conflicts — Lock her up! (the race condition!)
