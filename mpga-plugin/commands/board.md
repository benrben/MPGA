# /mpga:board

Show and manage the task board.

## Steps

1. Run `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board show` and display the current board
2. Display stats: progress, in-flight, blocked, evidence coverage
3. Offer actions based on board state:
   - If todo tasks exist: suggest `/mpga:execute`
   - If in-progress tasks: show what's being worked on
   - If blocked tasks: highlight and ask for help
   - If board is empty: suggest `/mpga:plan`

## Board operations
```
/mpga:board                      (show board)
/mpga:board add "Task title"     (create task)
/mpga:board move T001 done       (move task)
/mpga:board claim T001           (claim task)
/mpga:board block T001 "reason"  (mark blocked)
```

## Usage
```
/mpga:board
```
