import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "bin")

	bin_ = frappe.qb.DocType("Bin")
	warehouse = frappe.qb.DocType("Warehouse")

	(
		frappe.qb.update(bin_)
		.inner_join(warehouse)
		.on(bin_.warehouse == warehouse.name)
		.set(bin_.company, warehouse.company)
		.where(bin_.company.isnull() | (bin_.company == ""))
	).run()
