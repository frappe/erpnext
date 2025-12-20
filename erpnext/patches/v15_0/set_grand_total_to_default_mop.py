import frappe


def execute():
	if frappe.db.has_column("POS Profile", "disable_grand_total_to_default_mop"):
		POSProfile = frappe.qb.DocType("POS Profile")

		frappe.qb.update(POSProfile).set(POSProfile.set_grand_total_to_default_mop, 1).where(
			POSProfile.disable_grand_total_to_default_mop == 0
		).run()
