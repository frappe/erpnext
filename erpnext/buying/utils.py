# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, getdate

from erpnext.stock.doctype.item.item import get_last_purchase_details, validate_end_of_life


def update_last_purchase_rate(doc, is_submit) -> None:
	"""updates last_purchase_rate in item table for each item"""

	if doc.get("is_internal_supplier"):
		return

	this_purchase_date = getdate(doc.get("posting_date") or doc.get("transaction_date"))

	for d in doc.get("items"):
		# get last purchase details
		last_purchase_details = get_last_purchase_details(d.item_code, doc.name)

		# compare last purchase date and this transaction's date
		last_purchase_rate = None
		if last_purchase_details and (
			doc.get("docstatus") == 2 or last_purchase_details.purchase_date > this_purchase_date
		):
			last_purchase_rate = last_purchase_details["base_net_rate"]
		elif is_submit == 1:
			# even if this transaction is the latest one, it should be submitted
			# for it to be considered for latest purchase rate
			if flt(d.conversion_factor):
				last_purchase_rate = flt(d.base_net_rate) / flt(d.conversion_factor)
			# Check if item code is present
			# Conversion factor should not be mandatory for non itemized items
			elif d.item_code:
				frappe.throw(_("UOM Conversion factor is required in row {0}").format(d.idx))

		# update last purchsae rate
		frappe.db.set_value("Item", d.item_code, "last_purchase_rate", flt(last_purchase_rate))


def validate_for_items(doc) -> None:
	items = []
	for d in doc.get("items"):
		set_stock_levels(row=d)  # update with latest quantities
		item = validate_item_and_get_basic_data(row=d)
		validate_stock_item_warehouse(row=d, item=item)
		validate_end_of_life(d.item_code, item.end_of_life, item.disabled)

		items.append(cstr(d.item_code))

	if (
		items
		and len(items) != len(set(items))
		and not cint(frappe.db.get_single_value("Buying Settings", "allow_multiple_items") or 0)
	):
		frappe.throw(_("Same item cannot be entered multiple times."))


def set_stock_levels(row) -> None:
	projected_qty = frappe.db.get_value(
		"Bin",
		{
			"item_code": row.item_code,
			"warehouse": row.warehouse,
		},
		"projected_qty",
	)

	qty_data = {
		"projected_qty": flt(projected_qty),
		"ordered_qty": 0,
		"received_qty": 0,
	}
	if row.doctype in ("Purchase Receipt Item", "Purchase Invoice Item"):
		qty_data.pop("received_qty")

	for field in qty_data:
		if row.meta.get_field(field):
			row.set(field, qty_data[field])


def validate_item_and_get_basic_data(row) -> dict:
	item = frappe.db.get_values(
		"Item",
		filters={"name": row.item_code},
		fieldname=["is_stock_item", "is_sub_contracted_item", "end_of_life", "disabled"],
		as_dict=1,
	)
	if not item:
		frappe.throw(_("Row #{0}: Item {1} does not exist").format(row.idx, frappe.bold(row.item_code)))

	return item[0]


def validate_stock_item_warehouse(row, item) -> None:
	if item.is_stock_item == 1 and row.qty and not row.warehouse and not row.get("delivered_by_supplier"):
		frappe.throw(
			_("Row #{1}: Warehouse is mandatory for stock Item {0}").format(
				frappe.bold(row.item_code), row.idx
			)
		)


def check_on_hold_or_closed_status(doctype, docname) -> None:
	status = frappe.db.get_value(doctype, docname, "status")

	if status in ("Closed", "On Hold"):
		frappe.throw(_("{0} {1} status is {2}").format(doctype, docname, status), frappe.InvalidStatusError)


@frappe.whitelist()
def get_linked_material_requests(items):
	items = json.loads(items)
	mr_list = []
	for item in items:
		material_request = frappe.db.sql(
			"""SELECT distinct mr.name AS mr_name,
				(mr_item.qty - mr_item.ordered_qty) AS qty,
				mr_item.item_code AS item_code,
				mr_item.name AS mr_item
			FROM `tabMaterial Request` mr, `tabMaterial Request Item` mr_item
			WHERE mr.name = mr_item.parent
				AND mr_item.item_code = %(item)s
				AND mr.material_request_type = 'Purchase'
				AND mr.per_ordered < 99.99
				AND mr.docstatus = 1
				AND mr.status != 'Stopped'
                        ORDER BY mr_item.item_code ASC""",
			{"item": item},
			as_dict=1,
		)
		if material_request:
			mr_list.append(material_request)

	return mr_list
