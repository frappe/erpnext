import frappe
from frappe.query_builder import DocType


def execute():
	ps = DocType("Payment Schedule")
	for parenttype in ("Sales Invoice", "Purchase Invoice", "Sales Order", "Purchase Order"):
		parent = DocType(parenttype)
		settled = ps.paid_amount + ps.discounted_amount
		outstanding = ps.payment_amount - settled

		(
			frappe.qb.update(ps)
			.join(parent)
			.on(ps.parent == parent.name)
			.set(ps.outstanding, outstanding)
			.set(ps.base_payment_amount, ps.payment_amount * parent.conversion_rate)
			.set(ps.base_outstanding, outstanding * parent.conversion_rate)
			.where(
				(ps.parenttype == parenttype)
				& (parent.docstatus == 1)
				& (ps.invoice_portion == 0)
				& (ps.outstanding == 0)
				& (settled < ps.payment_amount)
			)
		).run()
