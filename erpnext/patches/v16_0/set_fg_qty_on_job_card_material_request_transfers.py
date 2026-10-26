import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import flt


def execute():
	precision = frappe.get_precision("Stock Entry", "fg_completed_qty")
	for entry in get_zero_qty_transfers():
		qty = flt(get_untransferred_qty(entry.job_card), precision)
		if qty <= 0:
			continue

		frappe.db.set_value("Stock Entry", entry.name, "fg_completed_qty", qty, update_modified=False)
		frappe.get_doc("Job Card", entry.job_card).set_transferred_qty(update_status=True)


def get_zero_qty_transfers():
	"""Job Card transfers made from a Material Request that lost their finished good qty."""
	stock_entry = frappe.qb.DocType("Stock Entry")
	stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")
	from_material_request = (
		frappe.qb.from_(stock_entry_detail)
		.select(stock_entry_detail.parent)
		.where(stock_entry_detail.material_request.isnotnull() & (stock_entry_detail.material_request != ""))
	)

	return (
		frappe.qb.from_(stock_entry)
		.select(stock_entry.name, stock_entry.job_card)
		.where(
			(stock_entry.docstatus == 1)
			& (stock_entry.purpose == "Material Transfer for Manufacture")
			& stock_entry.job_card.isnotnull()
			& (stock_entry.job_card != "")
			& (stock_entry.fg_completed_qty == 0)
			& (stock_entry.is_return == 0)
			& stock_entry.name.isin(from_material_request)
		)
		.orderby(stock_entry.posting_date, stock_entry.posting_time, stock_entry.creation)
	).run(as_dict=True)


def get_untransferred_qty(job_card):
	stock_entry = frappe.qb.DocType("Stock Entry")
	transferred_qty = (
		frappe.qb.from_(stock_entry)
		.select(Sum(stock_entry.fg_completed_qty))
		.where(
			(stock_entry.job_card == job_card)
			& (stock_entry.docstatus == 1)
			& (stock_entry.purpose == "Material Transfer for Manufacture")
		)
	).run()[0][0]

	return flt(frappe.db.get_value("Job Card", job_card, "for_quantity")) - flt(transferred_qty)
