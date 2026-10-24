from collections import defaultdict

import frappe
from frappe.utils import flt

NAMING_SERIES = "BOM-CRE-.YYYY.-"


def execute():
	if not frappe.db.has_column("BOM Creator Item", "fg_reference_id"):
		return

	rows_by_creator = get_rows_by_creator()
	creator_updates, item_updates = {}, {}
	for creator in get_creators():
		creator_updates[creator.name] = {
			"design_name": creator.design_name or creator.item_name or creator.item_code or creator.name,
			"naming_series": NAMING_SERIES,
			"revision": 1,
		}
		item_updates.update(get_item_updates(creator, rows_by_creator[creator.name]))

	frappe.db.bulk_update("BOM Creator", creator_updates, update_modified=False)
	frappe.db.bulk_update("BOM Creator Item", item_updates, update_modified=False)


def get_creators() -> list:
	creator = frappe.qb.DocType("BOM Creator")
	return (
		frappe.qb.from_(creator)
		.select(creator.name, creator.qty, creator.item_code, creator.item_name, creator.design_name)
		.where(creator.naming_series.isnull() | (creator.naming_series == ""))
		.run(as_dict=True)
	)


def get_rows_by_creator() -> dict:
	item = frappe.qb.DocType("BOM Creator Item")
	rows = (
		frappe.qb.from_(item)
		.select(
			item.name,
			item.parent,
			item.item_code,
			item.item_name,
			item.qty,
			item.rate,
			item.conversion_factor,
			item.fg_reference_id,
		)
		.where(item.parenttype == "BOM Creator")
		.orderby(item.parent)
		.orderby(item.idx)
		.run(as_dict=True)
	)

	rows_by_creator = defaultdict(list)
	for row in rows:
		rows_by_creator[row.parent].append(row)

	return rows_by_creator


def get_item_updates(creator, rows: list) -> dict:
	node_ids = {row.name: node_id for node_id, row in enumerate(rows, start=1)}
	rows_by_name = {row.name: row for row in rows}
	updates = {}
	for row in rows:
		parent = rows_by_name.get(row.fg_reference_id)
		qty = flt(row.qty) / (flt(parent.qty if parent else creator.qty) or 1)
		updates[row.name] = {
			"node_id": node_ids[row.name],
			"parent_node_id": node_ids[parent.name] if parent else 0,
			"part_number": row.item_code,
			"part_name": row.item_name or row.item_code,
			"source": "Manual",
			"qty": qty,
			"stock_qty": qty * (flt(row.conversion_factor) or 1),
			"amount": flt(row.rate) * qty,
		}

	return updates
