import frappe


def execute():
	frappe.reload_doc("selling", "doctype", "sales_order_item", force=True)
	frappe.reload_doc("buying", "doctype", "purchase_order_item", force=True)

	for doctype in ("Sales Order Item", "Purchase Order Item"):
		# nosemgrep: frappe-semgrep-rules.rules.security.frappe-sql-format-injection -- formats table or column names, or fixed conditions
		frappe.db.sql(
			f"""
			UPDATE `tab{doctype}`
			SET against_blanket_order = 1
			WHERE ifnull(blanket_order, '') != ''
		"""
		)
