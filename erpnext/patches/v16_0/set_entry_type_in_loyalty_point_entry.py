import frappe


def execute():
	"""Label existing points rows with their type.

	Redemption rows stored the invoice's grand total as `purchase_amount`, so they counted as
	tier spend. Set it to 0. `loyalty_points` does not change, so no balance changes.
	"""
	lpe = frappe.qb.DocType("Loyalty Point Entry")
	unlabelled = (lpe.entry_type.isnull()) | (lpe.entry_type == "")

	(
		frappe.qb.update(lpe)
		.set(lpe.entry_type, "Redeem")
		.set(lpe.purchase_amount, 0)
		.where(unlabelled & lpe.redeem_against.isnotnull() & (lpe.redeem_against != ""))
	).run()

	(
		frappe.qb.update(lpe)
		.set(lpe.entry_type, "Earn")
		.where(unlabelled & lpe.invoice.isnotnull() & (lpe.invoice != ""))
	).run()

	(frappe.qb.update(lpe).set(lpe.entry_type, "Adjustment").where(unlabelled)).run()
