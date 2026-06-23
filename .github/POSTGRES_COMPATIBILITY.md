# PostgreSQL compatibility — review guide

ERPNext targets **both MariaDB and PostgreSQL from a single codebase**. The full server
test suite passes on both, but the PostgreSQL CI job is **label-gated** (it does not run on
every PR), so until it is required this guide is the always-on guard. Greptile loads it as
review context (`.greptile/config.json`).

When reviewing a PR, flag any **new or changed query** (raw `frappe.db.sql`, `frappe.qb`,
`frappe.get_all/get_list/get_value`, report SQL) that would **error on PostgreSQL** or
**return different results on the two engines**.

## The one rule that governs everything

**MariaDB behaviour must not change; PostgreSQL is brought into line with MariaDB — never the
reverse.** A "fix" that changes the value, row count, or ordering MariaDB produced is a
regression, even if the new behaviour looks more correct. The only accepted MariaDB-output
change is replacing a genuinely *undefined/arbitrary* result with a deterministic one (row
count preserved) — and that should be called out explicitly.

There are two failure modes to watch for:
1. **Hard breaks** — PostgreSQL raises an exception; MariaDB is green. Easy to catch in CI,
   but the gated job may not run.
2. **Silent divergences** — both engines succeed but return *different* results. CI on one
   engine stays green; the bug only shows on a PostgreSQL site. These are the dangerous ones.

---

## 1. Hard breaks — would error on PostgreSQL

Flag a changed query that uses any of these:

- **Loose `GROUP BY`** — selecting/ordering a column that is neither in `GROUP BY` nor wrapped
  in an aggregate. MariaDB tolerates it; PostgreSQL errors (`must appear in the GROUP BY
  clause or be used in an aggregate function`). This **also covers an aggregate (`Sum`/`Count`/…)
  selected alongside bare columns with NO `.groupby()` at all** — MariaDB silently collapses
  every row into one arbitrary-valued row (often a *wrong-output* bug there too), PostgreSQL
  errors. Fix: add the bare column to `GROUP BY` **if it is functionally dependent on the group
  key**, otherwise wrap it in `Max()`/`Min()`. **See §3 — the row-count trap — before suggesting
  "add it to GROUP BY".**
- **MySQL-only functions** — `TIMESTAMP(date,time)`, `TIMEDIFF`, `STR_TO_DATE`, `DATE_FORMAT`,
  `DATE_ADD/SUB`, `GROUP_CONCAT`, `PERIOD_DIFF`, SQL `IF(cond,a,b)`. Use the portable
  `frappe.query_builder.functions` equivalents (`CombineDatetime`, `DateDiff`, `Case`,
  `GroupConcat`, …) or a precomputed column (e.g. `posting_datetime`).
- **`UPDATE … JOIN`** — not valid on PostgreSQL. Rewrite as `UPDATE … WHERE name IN (subquery)`.
- **`HAVING` referencing a `SELECT` alias** — PostgreSQL rejects output-column aliases in
  `HAVING` (regardless of whether the query has a `GROUP BY`; MariaDB allows them). Repeat the
  underlying expression in `HAVING`, or move a non-aggregate predicate into `WHERE`.
- **`SELECT DISTINCT … ORDER BY <expr not in the select list>`** — add the expr to the select.
- **Single-quoted column alias** `AS 'x'` — PostgreSQL reads `'x'` as a string literal. Use an
  unquoted (or double-quoted) alias.
- **`varchar | varchar`** (bitwise OR misused as a coalesce) — errors on PostgreSQL. Use
  `Coalesce(...)`.
- **Capital-cased identifiers** used as column/field names in `get_value(dt, dn, "Status")`,
  `get_all(dt, fields=["Account"])`, and similar — PostgreSQL quotes the identifier and matches
  it case-sensitively; a stored column named `status`/`account` won't match `"Status"`/`"Account"`
  (`column "Account" does not exist`). Use the exact stored (lower-case) fieldname.
- **Boolean passed where an integer column is expected** — `frappe.db.set_value(dt, dn,
  check_field, True)`, `doc.db_set(field, False)`, or `frappe.qb.update(dt).set(check_field, True)`
  emit `SET col = true`, which PostgreSQL rejects on a `smallint`/`Check` column
  (`column is of type smallint but expression is of type boolean`). Pass `1`/`0`.
- **`.like()`/`.ilike()` (or raw `LIKE`) on a NON-text column** — `idx`, `docstatus`, a date, etc.
  frappe maps `.like()` → `ILIKE`, and PostgreSQL has no `bigint ILIKE text` operator (`operator
  does not exist: bigint ~~* unknown`). Cast the column to text first — **`Cast_(col, "varchar")`**,
  not `Cast(col, "char")` (see below). MariaDB coerces the int implicitly, so the cast is a no-op there.
- **`CAST(… AS CHAR)` / `Cast(x, "char")`** — on PostgreSQL bare `CHAR` is `character(1)`, so
  `CAST(12 AS CHAR)` → `'1'` (silently truncates multi-digit values); MariaDB gives the full string.
  Use `VARCHAR` / `Cast_(x, "varchar")`.
- **`.rlike()` / raw `RLIKE`** — frappe rewrites `REGEXP` → `~*` on PostgreSQL but does **not**
  translate `RLIKE` (no such PostgreSQL operator). Use `.regexp()` (or `.like()` for a simple prefix).
- **`IfNull`/`Coalesce` of a typed column with a different-typed literal** — `IfNull(asset.disposal_date, 0)`
  renders `COALESCE("disposal_date", 0)`, coalescing a **DATE** with an **integer**. PostgreSQL requires
  `COALESCE` args to share a type (`DatatypeMismatch: COALESCE types date and integer cannot be matched`);
  MariaDB's `IFNULL` is permissive. The common shape is `IfNull(date_col, 0) != 0 / == 0` as a presence test —
  replace with `date_col.isnotnull()` / `date_col.isnull()` (identical, and valid on both). Otherwise coalesce
  to a **same-type** default (`Coalesce(date_col, '1900-01-01')`, `Coalesce(text_col, '')`).
- **Division by a possibly-zero divisor** — `Sum(a) / Sum(b)`, `x / col`, etc. where the
  divisor can be `0`/empty. MariaDB returns `NULL` for division by zero; PostgreSQL raises
  `division by zero` and aborts the query. Wrap the divisor in `NullIf(divisor, 0)` — that
  yields `NULL` on both engines, matching MariaDB's value. (Only the *literal* `/ 0` is a parse
  constant; the trap is a divisor that is an aggregate or column the data can drive to zero.)

---

## 2. Silent divergences — succeeds on both, returns different results

These don't error, so a one-engine CI stays green. Flag them:

- **Case sensitivity on text equality** — `==`, `.isin()`, `Strpos`/`Locate` on free-text
  columns are case-**sensitive** on PostgreSQL but case-**insensitive** under MariaDB's default
  collation. `Lower()` both sides. *(Not `.like()`/`["like", …]` — those already render as
  `ILIKE` on PostgreSQL; see §4.)*
- **Case sensitivity in a doc-`name` lookup** — lower-casing a value then using it as a
  document name in `get_value`/`get_doc`/`exists` misses on PostgreSQL (names are
  case-sensitive). Keep original case for the identifier; lower-case only comparison operands.
- **Empty string vs NULL** — PostgreSQL stores a blank link/data field as `NULL` on some paths
  while MariaDB keeps `''`; `Concat`/`Concat_ws` then diverge. Prefer the stored full value, or
  `Coalesce(col, '')` per argument.
- **NULL ordering** — MariaDB sorts `NULL` first, PostgreSQL sorts it last. For
  `ORDER BY … LIMIT 1`/`[0]` on a nullable column, guard with `Coalesce`/`isnotnull()`.
- **`ORDER BY … LIMIT 1` with no unique tiebreaker** — when rows tie on the ordered column the
  two engines may pick different rows. Add a `creation`/`name` tiebreaker **only if it does not
  change MariaDB's current pick** (see §4).
- **Integer division** — `int / int` truncates on PostgreSQL but is decimal on MariaDB, e.g.
  `COUNT(...) / COUNT(...) * 100` → `0`, or `manufacturing_time_in_mins / 1440` flooring a
  lead-time to whole days. Force float: multiply by `100.0`, or make a literal a float
  (`/ 1440` → `/ 1440.0`), or cast an operand. (Only SQL-level `/` on integer **columns/literals**
  — Python `/` is already float.)
- **`DISTINCT` list ordering** — `frappe.get_all(distinct=True, order_by=…)` /
  `SELECT DISTINCT … ORDER BY`: frappe's `db_query` **silently drops `ORDER BY` for distinct
  queries on PostgreSQL**, so the result is unordered there. Sort in Python instead — and use
  `key=str.casefold`, because bare `sorted()` is case-sensitive (ASCII) while MariaDB's
  collation is case-insensitive, so a plain sort reorders MariaDB's output.
- **Engine-specific function rewrites** — e.g. a PostgreSQL `regexp_replace` branch
  reimplementing MariaDB's `CAST(SUBSTRING_INDEX(name,' ',-1) AS UNSIGNED)` (leading digits of
  the last whitespace token). Verify the rewrite matches MariaDB on edge cases (`"X - 3a"→3`,
  `"X - 1.5"→1`) by diffing both engines on literal rows.
- **`UnixTimestamp(date)` / date→epoch** is timezone-dependent (midnight in the DB session TZ),
  so a strict `epoch <= now` bound is flaky on PostgreSQL.

---

## 3. The `GROUP BY` row-count trap (the single most important rule)

When making a loose `GROUP BY` PostgreSQL-valid, **do not add a non-functionally-dependent
column to the `GROUP BY` just to satisfy PostgreSQL** — that turns one group row into N and
**changes the MariaDB row count** (a regression). The classic traps are adding the **child/row
primary key** or an **editable per-row field**. Instead **`Max()`/`Min()`-wrap** the offending
column: the row count is preserved and the value goes from arbitrary (MariaDB's old loose pick)
to deterministic.

**Judge functional dependence by the source table, not the column name:**
- A column from a **master joined on the group key** (`t3.x` where `t1.key = t3.name`) is FD →
  safe to keep in `GROUP BY`.
- A descriptive field on the **transaction** table (`t1.supplier_name`, `t1.territory`,
  `t1.item_name` — fetched/editable, can differ across historical rows for the same key) is
  **not** FD even though it looks master-derived → `Max()`-wrap it.

Conversely, do **not** suggest changing a `Max()`/`Min()`-wrapped column to `Sum()` (or vice
versa) to make a number "more correct" — that changes the MariaDB value. The wrap reproduces
MariaDB's prior one-value-per-group output; a different aggregate is a product change, out of
scope for a portability fix.

---

## 4. False positives — do NOT flag these

These are auto-handled by the framework and are **not** breaks:

- **`.like()` / `["like", …]`** already renders as `ILIKE` on PostgreSQL — not a
  case-sensitivity bug. *(Exception: `.like()` on a **non-text** column — `idx`, `docstatus` —
  is a hard break, `bigint ILIKE`; see §1.)*
- **Raw `ifnull(...)`** inside `frappe.db.sql()` is rewritten to `coalesce(...)` on all engines.
- **Backticks**, **`LOCATE`**, **`REGEXP`** / **`.regexp()`** in raw SQL are auto-translated on
  PostgreSQL (`REGEXP` → `~*`). **But `RLIKE` / `.rlike()` is NOT translated** — that one is a
  hard break (see §1).
- **An `ORDER BY … LIMIT 1` tie where the two engines already agree**, or where adding a
  tiebreaker would *change* MariaDB's current pick — leave it; "fixing" it would either change
  MariaDB or has no observable effect.

---

## 5. Transaction / runtime (not query-shape, still PostgreSQL-only)

- **Catch-and-continue inserts** — on PostgreSQL a failed `insert()` aborts the **whole
  transaction**, so code that swallows a duplicate and keeps going dies on the next statement
  with `InFailedSqlTransaction` (frappe dropped its blanket per-statement savepoint in
  frappe#40075). Such a handler must wrap the fallible insert in `frappe.db.savepoint(name)` +
  `rollback(save_point=name)` — unless it re-`throw`s with no DB call before the throw, or the
  insert uses `ignore_if_duplicate=True` / `autoname="hash"` (→ `ON CONFLICT DO NOTHING`).

---

## How to review

For every changed query: does it (a) use a construct from §1 (would error on PostgreSQL), or
(b) match a divergence in §2/§3 (different result across engines)? If so, comment with the
portable fix and confirm it leaves **MariaDB output unchanged**. Skip the §4 false positives.
Prefer a comment that names the rule (e.g. "loose GROUP BY — Max()-wrap, don't add to GROUP BY:
splits the row count") so the fix is unambiguous.

The static pre-commit checker (`.github/helper/postgres_compat.py`) catches the *mechanical*
§1 breaks; the **semantic** §2/§3 divergences are exactly what a reviewer (and this guide) must
cover, because no static check can see them.
