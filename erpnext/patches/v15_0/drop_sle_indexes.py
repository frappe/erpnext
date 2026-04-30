import click
import frappe


def execute():
	table = "tabStock Ledger Entry"
	index_list = ["posting_datetime_creation_index", "item_warehouse", "batch_no_item_code_warehouse_index"]

	for index in index_list:
		if not frappe.db.has_index(table, index):
			continue

		try:
			frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP INDEX `{index}`")
			click.echo(f"✓ dropped {index} index from {table}")
		except Exception:
			frappe.log_error("Failed to drop index")
