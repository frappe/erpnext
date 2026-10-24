"""Merge duplicate component rows in existing Product Bundles (issue #368).

A bundle could previously list the same component Item on several rows; the new
duplicate check rejects that, so such bundles would become unsaveable after upgrade.
Merge the duplicates into one row per item (qty summed into the earliest row, the
rest deleted) and resequence idx. Idempotent — a second run finds no duplicates.
"""

import frappe
from frappe.query_builder.functions import Count
from frappe.utils import flt

from erpnext.stock.get_item_details import get_conversion_factor


def execute():
	pbi = frappe.qb.DocType("Product Bundle Item")
	duplicates = (
		frappe.qb.from_(pbi)
		.select(pbi.parent, pbi.item_code)
		.groupby(pbi.parent, pbi.item_code)
		.having(Count(pbi.name) > 1)
	).run(as_dict=True)

	affected_parents = set()
	for dupe in duplicates:
		rows = frappe.get_all(
			"Product Bundle Item",
			filters={"parent": dupe.parent, "item_code": dupe.item_code},
			fields=["name", "qty", "uom"],
			order_by="idx asc",
		)
		# rows may use different UOMs, so sum in stock units and keep the surviving row in
		# the stock UOM (packing converts the row's UOM, so this preserves the packed qty)
		stock_uom = frappe.db.get_value("Item", dupe.item_code, "stock_uom")
		total_stock_qty = sum(
			flt(row.qty) * flt(get_conversion_factor(dupe.item_code, row.uom).get("conversion_factor"))
			for row in rows
		)
		keeper, extras = rows[0], rows[1:]
		frappe.db.set_value(
			"Product Bundle Item",
			keeper.name,
			{"qty": total_stock_qty, "uom": stock_uom},
			update_modified=False,
		)
		for extra in extras:
			frappe.db.delete("Product Bundle Item", {"name": extra.name})
		affected_parents.add(dupe.parent)

	for parent in affected_parents:
		names = frappe.get_all(
			"Product Bundle Item", filters={"parent": parent}, pluck="name", order_by="idx asc"
		)
		for idx, name in enumerate(names, start=1):
			frappe.db.set_value("Product Bundle Item", name, "idx", idx, update_modified=False)
