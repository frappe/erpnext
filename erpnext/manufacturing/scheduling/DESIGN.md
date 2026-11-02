# Production Scheduling Engine - Design

Status: **Phases 1–2 implemented**, plus the Work Order/Job Card date-sync slice of
Phase 3. `plan_adapter.py` builds the plan task graph and backs the "Schedule Items"
button with a what-if preview dialog on Production Plan; dates are written and
Production Plan Schedule entries created only when the user applies the proposal.

## 1. Problem

Production Plan today carries dates (`po_items.planned_start_date`,
`sub_assembly_items.schedule_date`) but nothing computes them - users type them in.
The only real scheduling in ERPNext happens at the very end of the chain: when a Work
Order is submitted, Job Cards are placed one at a time (first-fit, forward-only) against
workstation working hours and existing bookings. Consequences:

- A plan gives no answer to "when will this be done?" or "can we promise this date?"
- MRP/MPS computes release dates from a static `Item Lead Time` number, blind to shop load.
- There is no backward ("we must ship on X, when must we start?") scheduling anywhere.
- Rescheduling after a disruption means resubmitting work orders one by one.

## 2. Reference model - Epicor Kinetic

Concepts worth adopting, and their fate in this design:

| Epicor concept | What it does | This design |
|---|---|---|
| Capacity / Load / Scheduling Blocks | Resource supply vs demand; operations placed as time blocks on resources | Core model: `Resource` (calendar + capacity), load intervals, `Assignment.blocks` |
| Finite vs Infinite scheduling | Finite respects load and never overloads; infinite ignores load to show demand vs capacity | `mode = FINITE / INFINITE` per run |
| Forward / Backward scheduling | Earliest-completion from a start date, or latest-start from a due date (JIT), with forward fallback when backward lands in the past | `direction = FORWARD / BACKWARD`, automatic per-task forward fallback |
| What-if scheduling | Propose a schedule without committing it | Engine is **dry-run by default**: it returns a proposal, callers persist |
| Global scheduling | Batch re-schedule everything by priority after disruptions | Same engine fed with *all* open tasks; priority is a first-class task field |
| Capability-based scheduling | Operation demands a capability, engine picks a concrete resource | `Task.resource_type` (maps to existing `workstation_type`), engine picks the earliest-available machine |
| Resource Groups & calendars | Shifts, holidays per resource | `ResourceCalendar` built from Workstation working hours + holiday list |
| Scheduling boards | Gantt UIs for jobs/resources | Phase 5 (UI reads engine output; not part of the core) |
| Setup / queue / move times | Per-operation overheads | Partially: inter-task gap (mins between operations) now; explicit setup/queue fields are a Phase 5 schema addition |

Not adopted (out of scope): sequence-optimization to minimize changeovers, multi-plant
transfer scheduling, capable-to-promise quoting. Epicor itself ships those only in the
APS add-on.

## 3. ERPNext today - inventory and gaps

What exists and is reused as-is:

- **Workstation**: `working_hours` (daily shift slots), `holiday_list`,
  `production_capacity` (parallel jobs), `workstation_type` (capability),
  `plant_floor`, status. → becomes the engine's `Resource`.
- **BOM Operation**: `time_in_mins`, `fixed_time`, `batch_size`, `sequence_id`
  (parallel groups), `workstation` / `workstation_type`. → becomes `Task`s.
- **Job Card**: `Job Card Scheduled Time` + `Job Card Time Log` rows are the booked
  load; `schedule_time_logs` is today's first-fit placer. → load source; later a client.
- **Manufacturing Settings**: `mins_between_operations`, `allow_overtime`,
  `allow_production_on_holidays`, `capacity_planning_for_days`,
  `disable_capacity_planning`. → engine options.
- **Item Lead Time**: per-item `capacity_per_day`, `daily_yield`, shift/workstation
  counts, `purchase_time`, `buffer_time`. → duration source for rows *without* BOM
  operations, and for purchased/subcontracted tasks.
- **MPS / MRP**: `Master Production Schedule`, `MPS Planned Order`, MRP report with
  `cumulative_lead_time` and `release_date = delivery_date - lead_time`. → Phase 4 client.

Gaps this design closes:

| Gap | Today | Target |
|---|---|---|
| Plan-level scheduling | none (manual dates) | engine schedules the whole BOM-level task graph |
| Backward scheduling | none | `BACKWARD` direction with forward fallback |
| Infinite mode (RCCP) | none | `INFINITE` mode + overload report from the same output |
| What-if | none | dry-run result object, persisted only on demand |
| Cross-document view | job cards placed one WO at a time | one run can hold every open task; earlier placements constrain later ones |
| MRP dates | static lead-time arithmetic | same engine, same calendars, load-aware |
| Priority | none | `Task.priority` orders placement under contention |

## 4. Architecture

**Pure core, thin adapters.** The engine (`engine.py`, `models.py`, `calendars.py`)
imports nothing from Frappe - it consumes plain tasks/resources/intervals and returns a
proposal. All DB access lives in `loaders.py` (build inputs from doctypes) and, later,
in per-document adapters (persist outputs). This is what makes the engine reusable by
Production Plan, Work Order, and MRP alike, and testable without a site.

```
                 ┌────────────────────────────────────────────┐
                 │              scheduling engine             │
   loaders.py ─▶ │  tasks + resources + load ─▶ assignments   │ ─▶ adapters persist
  (Workstation,  │  direction: FORWARD | BACKWARD             │    (Phase ≥ 2)
   Job Cards,    │  mode:      FINITE  | INFINITE             │
   BOM, ILT)     │  dry-run: always                           │
                 └────────────────────────────────────────────┘
       clients: Production Plan ─ Work Order/Job Card ─ MRP/MPS ─ boards/reports
```

### Core model (`models.py`)

- `Interval(start, end)` - half-open time block.
- `Resource(name, capacity, calendar)` - a workstation or any capacity-bearing thing
  (a supplier lane, a subcontractor) with a `ResourceCalendar`.
- `ResourceCalendar(daily_windows, holidays)` - daily shift windows (empty = 24×7,
  i.e. overtime allowed or no working hours maintained) plus holiday dates.
- `Task(key, duration_mins, resource, resource_type, depends_on, earliest_start,
  due_date, priority)` - one operation, or one whole row when no operations exist
  (duration then comes from Item Lead Time).
- `Assignment(task_key, resource, blocks)` - where a task landed; `blocks` are the
  scheduling blocks (a task may split across shifts/days).
- `ScheduleResult(assignments, unscheduled)` - the proposal; `unscheduled` carries a
  reason (no resource, beyond horizon) instead of throwing.

### Algorithm (`engine.py`)

Forward, finite (the default):

1. Topologically sort tasks by `depends_on`; `priority` breaks ties, so under
   contention the important job grabs the slot first (Epicor's global-scheduling
   priority behavior).
2. A task's ready time = max(anchor, its `earliest_start`, dependency ends + gap).
3. Resolve the resource: explicit `resource` wins; otherwise every resource matching
   `resource_type` is tried and the one giving the earliest finish wins
   (capability-based scheduling).
4. Walk the resource's calendar windows from the ready time; in FINITE mode a
   sub-window only counts when concurrent load < capacity (segment sweep over interval
   boundaries). Consume windows into blocks until the duration is exhausted.
5. Placed blocks join the in-run load immediately, so later tasks - same plan or
   another document in the same run - see them. This is what fixed the "two plans
   scheduled back-to-back don't see each other" caveat of the earlier prototype.

Backward: reverse topological order; latest end = min(due date, successor starts − gap);
blocks are consumed walking the calendar backward. If the computed start lands before
the anchor (today), the task - and transitively its successors - are re-placed forward
from the anchor: Epicor's "backward with forward fallback", so an impossible due date
degrades into "earliest possible" rather than an error.

Infinite mode: identical walks, but existing load is ignored; only calendars constrain.
Comparing FINITE vs INFINITE end dates for the same tasks *is* the overload report.

### Task-graph construction (`loaders.py`)

- `build_bom_operation_tasks(bom_no, qty, prefix)` - one task per BOM Operation,
  time scaled `time_in_mins × qty / bom.quantity` (`fixed_time` unscaled). Operations
  sharing a `sequence_id` become parallel siblings; each sequence group depends on the
  previous group - same semantics Work Order applies today.
- Production Plan graph (Phase 2): per FG row, each sub-assembly row expands to its BOM
  operation chain (or a single lead-time task when the BOM has no operations /
  subcontracted); FG tasks depend on the terminal tasks of its sub-assemblies. This
  replaces the level-wave approximation of the earlier prototype with true
  per-parent dependency edges.
- `get_workstation_resources(...)` - Resource per Workstation; 24×7 calendar when
  `allow_overtime` is on or no working hours are maintained; holidays dropped when
  `allow_production_on_holidays` is on.
- `get_booked_load(resources, from_date)` - intervals from open Job Cards
  (Scheduled Time rows of untouched drafts + Time Logs), the same sources today's
  overlap checks read.

## 5. Phases

| Phase | Deliverable | Persists to |
|---|---|---|
| **1 (this package)** | Engine core + loaders + unit tests. Dry-run only, nothing wired. | - |
| **2 (built)** | Production Plan adapter (`plan_adapter.py`): "Schedule Items" runs the engine over the plan's task graph; what-if preview dialog shows the proposal, and only Apply writes `schedule_date`/`schedule_end_date` + `planned_start_date`/`planned_end_date` and materializes **Production Plan Schedule** rows (new non-submittable doctype, one row per scheduling block) - viewed shift-wise through Frappe's Calendar view with plan/workstation/item filters. Rows without BOM operations use Item Lead Time durations, scalable by the new `no_of_shifts` field on Production Plan. "Use Item Wise Start Dates" anchors each assembly item's chain to its own row `planned_start_date` (dialog date = global floor); in that mode row start dates are inputs and stay as entered, only end dates are written. Backward-from-delivery-date remains pending | plan child rows + Production Plan Schedule |
| 3 | Work Order / Job Card unification: WO submission asks the engine for placement instead of the recursive first-fit in `schedule_time_logs`; job cards become the persisted form of engine blocks. Global reschedule = one engine run over all open job cards. **First slice built:** when a WO originates from a scheduled plan row, its auto-created Job Cards are seeded from the Production Plan Schedule blocks (same times, same workstation, one scheduled row per block) instead of re-running first-fit - plan calendar and job cards match exactly. Fallback to first-fit when no schedule exists, qty is batch-split, or an operation repeats in the routing | Job Card Scheduled Time |
| 4 | MRP/MPS integration: planned-order release/due dates come from a backward engine run (load-aware when finite is chosen) instead of `delivery_date − cumulative_lead_time`; purchased items keep Item Lead Time durations on infinite supplier lanes | MPS Planned Order |
| 5 | Boards & schema extras: resource Gantt board (drag = pin `earliest_start`), overload report (finite vs infinite), per-operation setup/queue time fields, `priority` field on Production Plan / Work Order | UI + new fields |

Phase 2 is the sign-off gate for everything downstream; 3 and 4 are independent of each
other once 1–2 land.

## 6. Decisions taken (flag disagreement before Phase 2)

1. **Dry-run by default, callers persist.** What-if and global re-scheduling fall out
   for free; no hidden writes from the engine.
2. **Pure-python core, Frappe only in loaders/adapters.** Unit-testable without a site;
   reusable verbatim for MRP.
3. **Duration hierarchy:** BOM Operations when present → Item Lead Time capacity/time
   fields → 1-day floor. Purchased/subcontracted rows always use Item Lead Time
   (`purchase_time + buffer_time`) on an infinite lane.
4. **Backward falls back forward per-task** instead of failing the run.
5. **No changeover/sequence optimization.** First-fit by priority order, like Kinetic's
   base scheduler; APS-class optimization is explicitly out of scope.
6. **Job Cards stay the persistence format for shop-floor bookings** (Phase 3 replaces
   their placement logic, not their role).

## 7. Open questions

- Should FINITE be the default for Production Plan scheduling, with INFINITE only in
  reports? (Epicor defaults resources to finite; proposal: yes.)
- Material-constrained scheduling (don't start before raw material PO arrival) - Phase 4
  via MRP pegging, or earlier as a simple `earliest_start` from Material Request dates?
- Multi-company/multi-plant: scope resources per company now (proposal) or add a
  plant dimension to `Resource` immediately?
