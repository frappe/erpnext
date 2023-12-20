import frappe


def execute():
	"""Drop unused return_against index"""

	try:
		frappe.db.sql_ddl(
			"ALTER TABLE `tabDelivery Note` DROP INDEX `customer_is_return_return_against_index`"
		)
		frappe.db.sql_ddl(
			"ALTER TABLE `tabPurchase Receipt` DROP INDEX `supplier_is_return_return_against_index`"
		)
	except Exception:
		frappe.log_error("Failed to drop unused index")
