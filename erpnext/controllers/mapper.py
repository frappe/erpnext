# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import flt


def get_qty_already_mapped(target_doc, ref_field: str, qty_field: str = "qty") -> frappe._dict:
	"""Return a map: {source row name: qty} of rows already mapped into the target document.

	"Get Items From" passes the in-progress (unsaved) document back as `target_doc`. Its rows
	are invisible to the pending-qty queries in the mappers, which only count submitted
	documents -- so without this, selecting the same source document twice maps every row
	again. Rows are keyed by `ref_field` (dn_detail, so_detail, ...), and a row is present in
	the map even when its qty is 0, so mappers without qty tracking can dedupe on presence.
	"""
	if isinstance(target_doc, str):
		target_doc = frappe.parse_json(target_doc)

	qty_map = frappe._dict()
	for row in (target_doc and target_doc.get("items")) or []:
		if ref := row.get(ref_field):
			qty_map[ref] = qty_map.get(ref, 0) + flt(row.get(qty_field))

	return qty_map


def get_ordered_stock_qty(join_field: str, parent_field: str, source_name: str) -> frappe._dict | None:
	"""Return a map: {source row name: stock qty} ordered by submitted Purchase Orders, from their rows'
	unrounded qty * conversion factor. None unless purchase rows round their stock qty: the stored ordered
	qty is then rounded at the total, and the pending qty worked out from it falls a fraction short."""
	if not frappe.get_single_value("Stock Settings", "allow_to_edit_stock_uom_qty_for_purchase"):
		return None

	order = frappe.qb.DocType("Purchase Order")
	order_item = frappe.qb.DocType("Purchase Order Item")
	return frappe._dict(
		frappe.qb.from_(order_item)
		.join(order)
		.on(order.name == order_item.parent)
		.select(order_item[join_field], Sum(order_item.qty * order_item.conversion_factor))
		.where(
			(order_item[parent_field] == source_name) & (order.docstatus == 1) & (order.is_subcontracted == 0)
		)
		.groupby(order_item[join_field])
		.run()
	)


def get_pending_qty(row, ordered_stock_qty: frappe._dict | None, stored_ordered_qty: float) -> float:
	"""Qty of a source row still to order, in its UOM."""
	if ordered_stock_qty is not None and (row.name in ordered_stock_qty or not stored_ordered_qty):
		pending_qty = flt(row.qty) - flt(ordered_stock_qty.get(row.name)) / flt(row.conversion_factor)
	else:
		pending_qty = (flt(row.stock_qty) - flt(stored_ordered_qty)) / (flt(row.conversion_factor) or 1)

	return flt(pending_qty, row.precision("qty"))
