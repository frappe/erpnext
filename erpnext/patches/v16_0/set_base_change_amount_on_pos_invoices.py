import frappe
from frappe.query_builder.functions import Round


def execute():
	pos_invoice = frappe.qb.DocType("POS Invoice")
	precision = frappe.get_precision("POS Invoice", "base_change_amount")

	(
		frappe.qb.update(pos_invoice)
		.set(
			pos_invoice.base_change_amount,
			Round(pos_invoice.change_amount * pos_invoice.conversion_rate, precision),
		)
		.where(pos_invoice.docstatus == 1)
		.where(pos_invoice.change_amount > 0)
		.where(pos_invoice.base_change_amount == 0)
	).run()
