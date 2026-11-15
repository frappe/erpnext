import frappe
from frappe.query_builder import Case
from frappe.query_builder.functions import Sum
from frappe.utils import flt


def execute():
	if not frappe.get_single_value("Stock Settings", "allow_to_edit_stock_uom_qty_for_purchase"):
		return

	precision = frappe.get_precision("Material Request Item", "ordered_qty")
	updates, requests = {}, {}
	for row in get_ordered_rows_of_open_requests():
		ordered_qty = flt(row.qty, precision)
		if ordered_qty != flt(row.ordered_qty):
			updates[row.name] = {"ordered_qty": ordered_qty}
			requests.setdefault(row.parent, []).append(row.name)

	frappe.db.bulk_update("Material Request Item", updates, update_modified=False)
	for name, rows in requests.items():
		request = frappe.get_doc("Material Request", name)
		request.update_per_ordered(update_modified=False)
		request.update_requested_qty(rows)


def get_ordered_rows_of_open_requests():
	"""Rows of Material Requests not stopped, with the qty their submitted Purchase Orders add up to."""
	request = frappe.qb.DocType("Material Request")
	request_item = frappe.qb.DocType("Material Request Item")
	order = frappe.qb.DocType("Purchase Order")
	order_item = frappe.qb.DocType("Purchase Order Item")
	# a subcontracted order adds up its finished good qty, as its status updater does
	ordered_qty = (
		Case()
		.when(order.is_subcontracted == 1, order_item.fg_item_qty)
		.else_(order_item.qty * order_item.conversion_factor)
	)

	return (
		frappe.qb.from_(request_item)
		.join(request)
		.on(request.name == request_item.parent)
		.join(order_item)
		.on(order_item.material_request_item == request_item.name)
		.join(order)
		.on(order.name == order_item.parent)
		.select(
			request_item.name,
			request_item.parent,
			request_item.ordered_qty,
			Sum(ordered_qty).as_("qty"),
		)
		.where((request.docstatus == 1) & (request.status != "Stopped") & (order.docstatus == 1))
		.groupby(request_item.name, request_item.parent, request_item.ordered_qty)
	).run(as_dict=True)
