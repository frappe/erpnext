# Cerbos Authorization for ERPNext

This directory wires [Cerbos](https://cerbos.dev) into ERPNext as an external
Policy Decision Point (PDP). Cerbos owns the **business** authorization rules
(role + attribute checks, multi-company scoping, document lifecycle, portal
access) while Frappe's framework continues to handle session, login, and
DocType existence.

## Layout

```
cerbos/
  policies/                  # Cerbos policy bundle
    _schemas/                # Principal + resource attribute schemas
    derived_roles/           # Shared roles + exported variables
    resource_policies/
      accounts/              # Sales/Purchase Invoice, Payment / Journal Entry
      buying/                # Supplier, Purchase Order, Purchase Receipt
      hr/                    # Employee, Leave, Expense, Timesheet
      projects/              # Project, Task
      selling/               # Customer, Quotation, Sales Order, Delivery Note
      stock/                 # Item, Stock Entry
  config/
    cerbos.yaml              # PDP configuration
  docker-compose.yml         # Local PDP
```

Each `resource_policies/<domain>/` folder ships a policy per resource, a
`*_test.yaml` suite, and a shared `testdata/` fixture set used by every test
in the domain.

## Running the PDP locally

```bash
cd cerbos
docker compose up -d
curl http://localhost:3592/_cerbos/health
```

The PDP exposes:

- HTTP/REST on `:3592`
- gRPC on `:3593` (used by the Python SDK in `erpnext/cerbos_authz/`)

Edit a `.yaml` under `policies/` and the running PDP picks up the change live
(`watchForChanges: true`).

## Validating policies

```bash
docker run --rm -v "$(pwd)/policies:/policies" \
  ghcr.io/cerbos/cerbos:latest compile /policies
```

A green run means schemas resolve, every policy compiles, and every test in
`*_test.yaml` passes.

## How ERPNext talks to the PDP

`erpnext/cerbos_authz/` provides:

- `client.py` — a thread-safe Cerbos client (singleton)
- `principal.py` — builds the Cerbos principal from `frappe.session.user`
- `resources.py` — builds the Cerbos resource from a Frappe `Document`
- `hooks.py` — `has_permission` callbacks registered into ERPNext's
  `hooks.py` for every doctype with a Cerbos resource policy

When Frappe asks "can user X do action Y on doctype Z?", the callback looks up
the doctype, builds the principal + resource, calls Cerbos via gRPC, and
returns a boolean. If the PDP is unreachable the callback fails closed (denies
access) — so a downed PDP locks the system rather than silently allowing
everything.

## Adding a new resource

1. Add an attribute schema at `policies/_schemas/resources/<resource>.json`.
2. Add a policy at `policies/resource_policies/<domain>/<resource>.yaml` and a
   matching `*_test.yaml`.
3. Add fixtures to the domain's `testdata/`.
4. Run `cerbos compile` and confirm exit 0.
5. Add the DocType → resource mapping in
   `erpnext/cerbos_authz/resources.py::DOCTYPE_TO_RESOURCE`.

## Spec summary

- **Principal**: Frappe user. Attributes: `user_type`, default `company`,
  `allowed_companies` (from User Permissions), optional `employee`,
  `customer`, `supplier`, plus `leave_approver_for` / `expense_approver_for`
  lists.
- **Resource**: a Frappe Document. Attributes vary by doctype; common ones
  are `company`, `owner`, `docstatus`, plus party links (`customer`,
  `supplier`, `employee`).
- **Actions**: ERPNext's standard ptypes — `read`, `write`, `create`,
  `delete`, `submit`, `cancel`, `amend`, `print`, `email`, `export`, `share`,
  `report`.
- **Cross-cutting rules**:
  - Submitted documents (`docstatus == 1`) are not writable or deletable.
  - Cancelled documents (`docstatus == 2`) cannot be re-submitted /
    re-cancelled and are the only ones that can be amended.
  - Region locks: deletion of submitted Sales Invoices / Payment Entries is
    blocked when `country == "Nepal"` (mirrors
    `erpnext.regional.check_deletion_permission`).
  - Portal Customer / Supplier users see only their own party's documents.
  - Employees self-service their own HR records via `employee == P.employee`.
