import frappe

from erpnext.bulk_transaction.doctype.bulk_transaction_logger.test_bulk_transaction_logger import (
	create_company,
	create_customer,
	create_item,
	create_so,
)


@frappe.whitelist()
def create_records():
	create_company()
	create_customer()
	create_item()

	gd = frappe.get_doc("Global Defaults")
	gd.set("default_company", "Test Bulk")
	gd.save()
	frappe.clear_cache()
	create_so()
