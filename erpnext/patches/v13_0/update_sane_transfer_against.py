import frappe


def execute():
	bom = frappe.qb.DocType("BOM")

	(
		frappe.qb.update(bom)
		.set(bom.transfer_material_against, "Work Order")
		.where(bom.with_operations == 0)
	).run()
