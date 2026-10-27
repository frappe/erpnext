import click
import frappe

BATCH_SIZE = 10000


def execute():
	last_name = ""
	while names := get_bundle_names(last_name):
		set_posting_datetime(names)
		last_name = names[-1]

	drop_indexes()


def get_bundle_names(last_name):
	sabb = frappe.qb.DocType("Serial and Batch Bundle")

	return (
		frappe.qb.from_(sabb)
		.select(sabb.name)
		.where(sabb.name > last_name)
		.orderby(sabb.name)
		.limit(BATCH_SIZE)
	).run(pluck=True)


def set_posting_datetime(names):
	sabb = frappe.qb.DocType("Serial and Batch Bundle").as_("sabb")
	sle = frappe.qb.DocType("Stock Ledger Entry")

	(
		frappe.qb.update(sabb)
		.join(sle)
		.on(sabb.name == sle.serial_and_batch_bundle)
		.set(sabb.posting_datetime, sle.posting_datetime)
		.where((sle.is_cancelled == 0) & sabb.name.isin(names))
	).run()


def drop_indexes():
	table = "tabSerial and Batch Bundle"
	index_list = ["voucher_no_index", "item_code_index", "warehouse_index", "company_index"]

	for index in index_list:
		if not frappe.db.has_index(table, index):
			continue

		try:
			frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP INDEX `{index}`")
			click.echo(f"✓ dropped {index} index from {table}")
		except Exception:
			frappe.log_error("Failed to drop index")
