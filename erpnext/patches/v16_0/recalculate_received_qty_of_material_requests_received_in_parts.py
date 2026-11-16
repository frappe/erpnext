import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import flt

from erpnext.controllers.buying_controller import rounds_stock_qty


def execute():
	rows, received_qty = {}, {}
	for row in get_received_rows("Purchase Receipt") + get_received_rows("Purchase Invoice"):
		rows[row.name] = row
		received_qty[row.name] = received_qty.get(row.name, 0) + row.qty

	precision = frappe.get_precision("Material Request Item", "received_qty")
	updates, requests = {}, set()
	for name, row in rows.items():
		qty = flt(received_qty[name])
		if rounds_stock_qty(row):
			qty = flt(qty, precision)

		if qty != flt(row.received_qty):
			updates[name] = {"received_qty": qty}
			requests.add(row.parent)

	frappe.db.bulk_update("Material Request Item", updates, update_modified=False)
	for name in requests:
		update_per_received(name)


def get_received_rows(receipt_doctype):
	"""Rows of partly received Material Requests not stopped, with the qty their submitted receipts add up to."""
	request = frappe.qb.DocType("Material Request")
	request_item = frappe.qb.DocType("Material Request Item")
	receipt = frappe.qb.DocType(receipt_doctype)
	receipt_item = frappe.qb.DocType(f"{receipt_doctype} Item")

	query = (
		frappe.qb.from_(request_item)
		.join(request)
		.on(request.name == request_item.parent)
		.join(receipt_item)
		.on(receipt_item.material_request_item == request_item.name)
		.join(receipt)
		.on(receipt.name == receipt_item.parent)
		.select(
			request_item.name,
			request_item.parent,
			request_item.stock_uom,
			request_item.received_qty,
			Sum(receipt_item.qty * receipt_item.conversion_factor).as_("qty"),
		)
		.where(
			(request.docstatus == 1)
			& (request.status != "Stopped")
			& (request.per_received < 100)
			& (receipt.docstatus == 1)
		)
		.groupby(request_item.name, request_item.parent, request_item.stock_uom, request_item.received_qty)
	)
	if receipt_doctype == "Purchase Invoice":
		query = query.where(receipt.update_stock == 1)

	return query.run(as_dict=True)


def update_per_received(request):
	frappe.get_doc("Material Request", request)._update_percent_field(
		{
			"target_dt": "Material Request Item",
			"target_parent_dt": "Material Request",
			"target_parent_field": "per_received",
			"target_ref_field": "stock_qty",
			"target_field": "received_qty",
			"name": request,
		},
		update_modified=False,
	)
