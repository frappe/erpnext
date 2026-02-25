import frappe
from frappe.query_builder.functions import Sum


def execute():
	sre = frappe.qb.DocType("Stock Reservation Entry")
	query = (
		frappe.qb.from_(sre)
		.select(
			sre.item_code,
			sre.warehouse,
			Sum(sre.reserved_qty - sre.delivered_qty).as_("reserved_stock"),
		)
		.where((sre.docstatus == 1) & (sre.status.notin(["Delivered", "Cancelled"])))
		.groupby(sre.item_code, sre.warehouse)
	)

	for d in query.run(as_dict=True):
		frappe.db.set_value(
			"Bin",
			{"item_code": d.item_code, "warehouse": d.warehouse},
			"reserved_stock",
			d.reserved_stock,
		)
