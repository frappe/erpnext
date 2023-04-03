import frappe


def execute():
	if not frappe.get_meta("Company").has_field("enable_perpetual_inventory_for_non_stock_items"):
		return

	frappe.reload_doc("setup", "doctype", "company")

	company = frappe.qb.DocType("Company")

	frappe.qb.update(company).set(
		company.enable_provisional_accounting_for_non_stock_items,
		company.enable_perpetual_inventory_for_non_stock_items,
	).set(company.default_provisional_account, company.service_received_but_not_billed).where(
		company.enable_perpetual_inventory_for_non_stock_items == 1
	).where(
		company.service_received_but_not_billed.isnotnull()
	).run()
