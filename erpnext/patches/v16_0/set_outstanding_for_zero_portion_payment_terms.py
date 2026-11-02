import frappe
from frappe.query_builder import DocType


def execute():
	ps = DocType("Payment Schedule")
	settled = ps.paid_amount + ps.discounted_amount
	outstanding = ps.payment_amount - settled

	for parenttype in ("Sales Invoice", "Purchase Invoice", "Sales Order", "Purchase Order"):
		parent = DocType(parenttype)
		conversion_rate = (
			frappe.qb.from_(parent).select(parent.conversion_rate).where(parent.name == ps.parent)
		)
		submitted = frappe.qb.from_(parent).select(parent.name).where(parent.docstatus == 1)

		(
			frappe.qb.update(ps)
			.set(ps.outstanding, outstanding)
			.set(ps.base_payment_amount, ps.payment_amount * conversion_rate)
			.set(ps.base_outstanding, outstanding * conversion_rate)
			.where(
				(ps.parenttype == parenttype)
				& ps.parent.isin(submitted)
				& (ps.invoice_portion == 0)
				& (ps.outstanding == 0)
				& (settled < ps.payment_amount)
			)
		).run()
