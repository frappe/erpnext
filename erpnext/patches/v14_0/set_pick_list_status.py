# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE


import frappe
from pypika.terms import ExistsCriterion


def execute():
	pl = frappe.qb.DocType("Pick List")
	se = frappe.qb.DocType("Stock Entry")
	dn = frappe.qb.DocType("Delivery Note")

	(
		frappe.qb.update(pl).set(
			pl.status,
			(
				frappe.qb.terms.Case()
				.when(pl.docstatus == 0, "Draft")
				.when(pl.docstatus == 2, "Cancelled")
				.else_("Completed")
			),
		)
	).run()

	(
		frappe.qb.update(pl)
		.set(pl.status, "Open")
		.where(
			(
				ExistsCriterion(
					frappe.qb.from_(se).select(se.name).where((se.docstatus == 1) & (se.pick_list == pl.name))
				)
				| ExistsCriterion(
					frappe.qb.from_(dn).select(dn.name).where((dn.docstatus == 1) & (dn.pick_list == pl.name))
				)
			).negate()
			& (pl.docstatus == 1)
		)
	).run()
