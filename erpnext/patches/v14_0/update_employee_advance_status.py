import frappe


def execute():
	frappe.reload_doc("hr", "doctype", "employee_advance")

	advance = frappe.qb.DocType("Employee Advance")
	(
		frappe.qb.update(advance)
		.set(advance.status, "Returned")
		.where(
			(advance.docstatus == 1)
			& ((advance.return_amount) & (advance.paid_amount == advance.return_amount))
			& (advance.status == "Paid")
		)
	).run()

	(
		frappe.qb.update(advance)
		.set(advance.status, "Partly Claimed and Returned")
		.where(
			(advance.docstatus == 1)
			& (
				(advance.claimed_amount & advance.return_amount)
				& (advance.paid_amount == (advance.return_amount + advance.claimed_amount))
			)
			& (advance.status == "Paid")
		)
	).run()
