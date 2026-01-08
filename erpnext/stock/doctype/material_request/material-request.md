### Problem
Once a Purchase Material Request is partially ordered, users cannot update the
remaining quantity, UOM, warehouse, or schedule date. This forces cancellation
and recreation of Material Requests, breaking workflow continuity.

### Solution
Introduces a controlled **Update Items** action for submitted Purchase Material
Requests that are not fully ordered.

### Key Features
- Allows updating qty, UOM, rate, warehouse, and schedule date
- Prevents reducing quantity below completed (ordered) quantity
- Disallows deletion of rows with completed quantity
- Enforces permission and document state checks
- Updates Bin → Indented Qty to keep inventory consistent

### Scope
- Material Request (Purchase)
- Client-side dialog for controlled updates
- Server-side validation and persistence
- Unit tests added
- Documentation added

### Backward Compatibility
No impact on existing workflows. Feature is opt-in via UI action.
