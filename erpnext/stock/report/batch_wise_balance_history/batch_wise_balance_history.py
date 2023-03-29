# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import cint, flt, getdate
from pypika import functions as fn

from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter


def execute(filters=None):
	if not filters:
		filters = {}

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_batch_map(filters, float_precision)

	data = []
	for item in sorted(iwb_map):
		if not filters.get("item") or filters.get("item") == item:
			for wh in sorted(iwb_map[item]):
				for batch in sorted(iwb_map[item][wh]):
					qty_dict = iwb_map[item][wh][batch]
					if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
						data.append(
							[
								item,
								item_map[item]["item_name"],
								item_map[item]["description"],
								wh,
								batch,
								flt(qty_dict.opening_qty, float_precision),
								flt(qty_dict.in_qty, float_precision),
								flt(qty_dict.out_qty, float_precision),
								flt(qty_dict.bal_qty, float_precision),
								item_map[item]["stock_uom"],
							]
						)

	return columns, data


def get_columns(filters):
	"""return columns based on filters"""

	columns = (
		[_("Item") + ":Link/Item:100"]
		+ [_("Item Name") + "::150"]
		+ [_("Description") + "::150"]
		+ [_("Warehouse") + ":Link/Warehouse:100"]
		+ [_("Batch") + ":Link/Batch:100"]
		+ [_("Opening Qty") + ":Float:90"]
		+ [_("In Qty") + ":Float:80"]
		+ [_("Out Qty") + ":Float:80"]
		+ [_("Balance Qty") + ":Float:90"]
		+ [_("UOM") + "::90"]
	)

	return columns


# get all details
def get_stock_ledger_entries(filters):
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))
	if not filters.get("to_date"):
		frappe.throw(_("'To Date' is required"))

	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = (
		frappe.qb.from_(sle)
		.select(
			sle.item_code,
			sle.warehouse,
			sle.batch_no,
			sle.posting_date,
			fn.Sum(sle.actual_qty).as_("actual_qty"),
		)
		.where(
			(sle.docstatus < 2)
			& (sle.is_cancelled == 0)
			& (fn.IfNull(sle.batch_no, "") != "")
			& (sle.posting_date <= filters["to_date"])
		)
		.groupby(sle.voucher_no, sle.batch_no, sle.item_code, sle.warehouse)
		.orderby(sle.item_code, sle.warehouse)
	)

	query = apply_warehouse_filter(query, sle, filters)
	for field in ["item_code", "batch_no", "company"]:
		if filters.get(field):
			query = query.where(sle[field] == filters.get(field))

	return query.run(as_dict=True)


def get_item_warehouse_batch_map(filters, float_precision):
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	for d in sle:
		iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {}).setdefault(
			d.batch_no, frappe._dict({"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0})
		)
		qty_dict = iwb_map[d.item_code][d.warehouse][d.batch_no]
		if d.posting_date < from_date:
			qty_dict.opening_qty = flt(qty_dict.opening_qty, float_precision) + flt(
				d.actual_qty, float_precision
			)
		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty = flt(qty_dict.in_qty, float_precision) + flt(d.actual_qty, float_precision)
			else:
				qty_dict.out_qty = flt(qty_dict.out_qty, float_precision) + abs(
					flt(d.actual_qty, float_precision)
				)

		qty_dict.bal_qty = flt(qty_dict.bal_qty, float_precision) + flt(d.actual_qty, float_precision)

	return iwb_map


def get_item_details(filters):
	item_map = {}
	for d in (frappe.qb.from_("Item").select("name", "item_name", "description", "stock_uom")).run(
		as_dict=1
	):
		item_map.setdefault(d.name, d)

	return item_map
