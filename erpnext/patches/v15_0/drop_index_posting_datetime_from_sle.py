import click
import frappe


def execute():
	table = "tabStock Ledger Entry"
	index = "posting_datetime_creation_index"

	if not frappe.db.has_index(table, index):
		return

	try:
		frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP INDEX `{index}`")
		click.echo(f"✓ dropped {index} index from {table}")
	except Exception:
		frappe.log_error("Failed to drop index")
