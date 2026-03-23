# /mpga:plan

Generate an evidence-based implementation plan for the active milestone.

## Steps

1. Read `MPGA/INDEX.md` for active milestone
2. Read the milestone's PLAN.md: `cat MPGA/milestones/<id>/PLAN.md`
3. Read relevant scope documents based on milestone objective
4. Spawn `researcher` agent if `config.agents.researchBeforePlan` is true
5. Break work into bite-sized tasks (2-10 min each):
   - Each task MUST cite exact files to modify (with evidence links)
   - Each task MUST cite expected test file locations
   - Each task MUST have mechanically verifiable acceptance criteria
6. Create task cards on the board:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board add "<title>" --priority <p> --scope <scope> --column todo
   ```
7. Write the plan to `MPGA/milestones/<id>/PLAN.md`
8. Show board: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board show`

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
