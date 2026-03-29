# /mpga:wireframe

Generate a visual checkpoint before implementation. We do NOT jump into UI code blind.

## Steps

1. Run `mpga wireframe "<description>" --screens <n>`
2. Detect the best renderer available
3. Use the `designer` agent to create one wireframe per screen
4. Save the artifacts under `MPGA/milestones/<id>/design/wireframes/`
5. Require approval before escalating to a prototype

## Usage
```
/mpga:wireframe Login dashboard
/mpga:wireframe Checkout flow --screens 3
```
