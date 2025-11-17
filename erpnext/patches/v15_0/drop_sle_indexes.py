import click
import frappe


def execute():
	table = "tabStock Ledger Entry"
	index_list = ["posting_datetime_creation_index", "item_warehouse"]

	for index in index_list:
		if not frappe.db.has_index(table, index):
			continue

		try:
			if frappe.db.db_type == "postgres":
				frappe.db.sql_ddl(f'DROP INDEX IF EXISTS "{index}"')
			else:
				frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP INDEX `{index}`")

			click.echo(f"✓ dropped {index} index from {table}")
		except Exception as e:
			frappe.log_error(f"Failed to drop index {index}: {e}")
