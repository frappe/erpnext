"""Backfill `utm_source` from the legacy `source` column on Lead and Opportunity.

The v15 patch `erpnext.patches.v15_0.migrate_to_utm_analytics` migrated
the `Lead Source` lookup doctype's rows into `UTM Source`, then renamed
the per-row `source` field on Lead/Opportunity to `utm_source` via the
`oldfieldname` schema hint.

That hint is documentation-only in Frappe — the only code path that
actually issues a `RENAME COLUMN` is the desk-driven Custom Field rename
flow. Standard DocField schema-sync only adds new columns and modifies
existing ones; it never renames or drops based on JSON changes. So on
every site that ran this patch, `utm_source` was added empty alongside
the legacy `source` column, and every row's source value was orphaned
on the now-meta-less `source` column.

This patch promotes those values: where `utm_source` is empty and the
legacy `source` column still exists with a value, copy it forward. Rows
where both columns are set to *different* values are left untouched and
surfaced as a count for the operator to triage. Idempotent re-run is a
no-op.
"""

import click
import frappe
from frappe.query_builder.functions import Count


def execute():
	for doctype in ("Lead", "Opportunity"):
		if not frappe.db.exists("DocType", doctype):
			continue
		columns = frappe.db.get_table_columns(doctype)
		if "source" not in columns or "utm_source" not in columns:
			# Either the legacy column was already dropped (clean rename
			# completed) or the new column never landed — nothing to do.
			continue

		_backfill_one(doctype)


def _backfill_one(doctype: str) -> None:
	table = frappe.qb.DocType(doctype)

	empty_utm = table.utm_source.isnull() | (table.utm_source == "")
	utm_set = table.utm_source.isnotnull() & (table.utm_source != "")
	source_set = table.source.isnotnull() & (table.source != "")

	to_fill = (frappe.qb.from_(table).select(Count("*")).where(empty_utm & source_set).run())[0][0]
	conflicts = (
		frappe.qb.from_(table)
		.select(Count("*"))
		.where(utm_set & source_set & (table.utm_source != table.source))
		.run()
	)[0][0]

	if to_fill:
		frappe.qb.update(table).set(table.utm_source, table.source).where(empty_utm & source_set).run()
		click.secho(
			f"  {doctype}: copied legacy `source` → `utm_source` on {to_fill} rows",
			fg="green",
		)

	if conflicts:
		click.secho(
			f"  {doctype}: {conflicts} rows have both `source` and `utm_source` populated "
			f"with DIFFERENT values; left untouched — review manually",
			fg="yellow",
		)
