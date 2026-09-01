import frappe
from frappe.utils import cint


def execute():
	bom_names, children_by_bom = _get_boms_with_operation_items_and_ancestors()
	_rebuild_bom_explosions(bom_names, children_by_bom)
	_backfill_work_order_operation_rows()


def _rebuild_bom_explosions(bom_names, children_by_bom):
	rebuilt = set()
	rebuilding = set()

	def rebuild(bom_no):
		if bom_no in rebuilt or bom_no in rebuilding:
			return

		rebuilding.add(bom_no)
		for child_bom in children_by_bom.get(bom_no, ()):
			if child_bom in bom_names:
				rebuild(child_bom)

		frappe.get_doc("BOM", bom_no).update_exploded_items()
		rebuilding.remove(bom_no)
		rebuilt.add(bom_no)

	for bom_no in bom_names:
		rebuild(bom_no)


def _get_boms_with_operation_items_and_ancestors():
	bom_names = set(
		frappe.get_all(
			"BOM Item",
			filters={"docstatus": 1, "operation_row_id": [">", 0]},
			pluck="parent",
			order_by=None,
			limit=0,
		)
	)
	children_by_bom = {}
	for row in frappe.get_all(
		"BOM Item",
		filters={"docstatus": 1, "bom_no": ["is", "set"]},
		fields=["parent", "bom_no"],
		limit=0,
	):
		children_by_bom.setdefault(row.parent, set()).add(row.bom_no)

	while True:
		parents = {
			parent for parent, child_boms in children_by_bom.items() if child_boms.intersection(bom_names)
		}
		new_parents = parents - bom_names
		if not new_parents:
			break
		bom_names.update(new_parents)

	return bom_names, children_by_bom


def _backfill_work_order_operation_rows():
	rows = frappe.get_all(
		"Work Order Operation",
		filters={"bom": ["is", "set"], "bom_operation_row_id": 0},
		fields=["name", "parent", "bom"],
		order_by="parent, idx",
		limit=0,
	)
	if not rows:
		return

	bom_operations = frappe.get_all(
		"BOM Operation",
		filters={"parent": ["in", list({row.bom for row in rows})]},
		fields=["parent", "idx"],
		order_by="parent, idx",
		limit=0,
	)
	row_ids_by_bom = {}
	for row in bom_operations:
		row_ids_by_bom.setdefault(row.parent, []).append(cint(row.idx))

	operation_occurrences = {}
	updates = {}
	for row in rows:
		key = (row.parent, row.bom)
		row_ids = row_ids_by_bom.get(row.bom, ())
		if not row_ids:
			continue

		occurrence = operation_occurrences.get(key, 0)
		updates[row.name] = {"bom_operation_row_id": row_ids[occurrence % len(row_ids)]}
		operation_occurrences[key] = occurrence + 1

	if updates:
		frappe.db.bulk_update("Work Order Operation", updates, update_modified=False)
