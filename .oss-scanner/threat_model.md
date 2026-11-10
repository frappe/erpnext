# Threat model: ERPNext

## What this project does and where untrusted input enters
ERPNext is an ERP (accounting, stock, selling, buying, manufacturing, projects, assets, CRM, point of sale) built as
an app on the Frappe Framework. It runs on the public Internet, often with several companies on one site and many
sites on one bench. ERPNext has no HTTP stack of its own. Input arrives through Frappe into ERPNext code:
- Functions decorated with `@frappe.whitelist()` across `erpnext/`. This is the main surface. Doctype controller
  methods are reached through `run_doc_method`.
- The standard REST, list and report API on ERPNext DocTypes, and script and query reports (`erpnext/*/report/`)
  that build SQL from user filters.
- Controller hooks (`validate`, `on_submit`, `on_cancel` and so on) running on user-supplied document data.
- Portal and website pages for customers and suppliers (`erpnext/templates/`, `erpnext/www/`): orders, invoices,
  quotations, request for quotation, addresses.
- Point of Sale (`erpnext/selling/page/point_of_sale/`), data import, bank statement import and the banking UI
  (`banking/`).
- Integrations that take webhooks or remote data.

## Actors and trust boundaries
From least to most privileged:
1. **Guest**: not logged in.
2. **Website User**: a customer or supplier portal user. They must see only their own party's documents.
3. **System User** with ERPNext roles: Accounts User, Sales User, Purchase User, Stock User, Manufacturing User,
   Projects User and so on. Each role's DocPerm rows are a boundary.
4. **System Manager**, and managers such as Accounts Manager: trusted to configure their area.
5. **Administrator** and anyone with shell access to the bench: fully trusted.

The boundaries that matter:
- **Role**: each role may do only what its DocPerm rows grant.
- **Record**: having permission on the doctype is not permission on every record.
- **Company**: a user limited to one company must not see or change another company's data.
- **User Permission restrictions.**
- **Party, on the portal.**
- **Integrity of submitted documents and the general ledger.**

## Components that matter most
- **Authorization**: whitelisted methods and reports that read or change records without checking that the caller
  may act on that specific record, across roles, companies, User Permission restrictions and portal parties.
- **Injection**: SQL built from request values in reports and utilities.
- **Financial and stock integrity**: changing or cancelling submitted documents without permission, getting past
  approval or credit-limit controls, or posting to another company's accounts.
- **Portal access**, and stored XSS in fields that render in Desk or print formats.

Out of scope: the Frappe Framework itself (enrolled separately as `frappe`), `node_modules/`, generated files, test
fixtures, and demo data.

## What counts as a finding
A report needs all four:
- **Entry point**: the exact reachable function or route.
- **Actor**: Guest, Website User, or a named low-privilege role. Use the least-privileged actor that works.
- **Input**: the request-controlled value and how it reaches the sink.
- **Impact**: what the actor reads, writes or executes that they should not.

Report one finding per root cause and list every entry point it reaches.

## Known non-findings
- Code guarded by `frappe.only_for`, `check_permission`, `has_permission`, or an equivalent check that actually covers
  that actor and that record.
- `ignore_permissions=True` in code reachable only from a scheduled job, patch, install script or test.
- Anything only Administrator, System Manager or the relevant manager role can reach, when the impact does not exceed
  what that role can already do.
- Accounting results that depend on site configuration.
- Behaviour that only exists because of a weakened development setting (`ignore_csrf`, `developer_mode`,
  `allow_tests`, `server_script_enabled`). Say so on the finding if a result depends on one.

## How we rate severity
- **Critical**: a Guest or any logged-in user gets RCE, arbitrary SQL, a full data read, or account takeover.
- **High**: a low-privilege user crosses a trust boundary. They read or write another user's, company's or party's
  data, change or cancel submitted documents they have no right to, or escalate their role. A portal user seeing
  another customer's documents is High.
- **Moderate**: partial disclosure, a bypass that needs an unusual precondition, or a control that fails only in one
  configuration. Getting past an approval or credit-limit control without exposing data also usually lands here.
- **Low**: enumeration, a metadata leak, or missing defence in depth.

## How to exercise it
The image has a bench at `/home/frappe/frappe-bench` on Frappe `develop`, with the checkout at `apps/erpnext` (`/src`
links to it), and a site `test_site` with ERPNext installed. Administrator has completed the setup wizard: company
`Scanner Company` (abbreviation `SC`), country India, currency INR.

ERPNext's own test suite does not run on this site: it creates its own companies and fiscal years
(`erpnext/tests/utils.py`) and fails where the setup wizard already has. Reproduce findings over HTTP instead.
- `frappe-services start` starts MariaDB and Redis, which work offline. `frappe-services stop` stops them.
- Web server: `echo '127.0.0.1 test_site' >> /etc/hosts`, then `su frappe -c "cd ~/frappe-bench && bench serve --port 8000" &`
  and `curl http://test_site:8000/api/method/ping`.
- Log in through `/api/method/login` with `{"usr": ..., "pwd": ...}` and reuse the `sid` cookie. Users:
  `Administrator`/`admin`, and with password `scanner-user-pw`: `website@example.com` (Website User),
  `user@example.com` (plain System User, only the `Desk User` role), `accounts-user@example.com` (Accounts User),
  `sales-user@example.com` (Sales User), `stock-user@example.com` (Stock User), `manager@example.com` (System Manager).
  To show a cross-company or User Permission bypass, create a second company and a User Permission as Administrator
  first.
- `bench --site test_site console` gives a Python shell on the site, for setting up data a reproduction needs.
- MariaDB root password: `root`.

Desk access is not needed to call an API: unless a method checks for a role, `/api/method/...` works for any
logged-in user, so try `website@example.com` before a desk user, and Guest before either.

Prove the impact without maximising it. Read one record you should not be able to read. Do not destroy data. For a
claim that something is refused, run a positive control as the same user in the same run: a 403 can come from a
check unrelated to the one you are testing.

## Reports and patches
Include the HTTP requests that reproduce the issue on `test_site`, the user they ran as, and a minimal patch against
`develop`.
