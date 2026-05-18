import click
import frappe
from frappe.query_builder.functions import Count


def execute():
	"""Copy legacy `source` values into `utm_source` on Lead and Opportunity where missing."""
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
	"""Backfill `utm_source` for one doctype and report conflicts."""
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
