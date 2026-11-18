import frappe
from frappe.query_builder.functions import Count, IfNull, Sum
from frappe.utils import flt

RECEIVED_ITEM = "Subcontracting Inward Order Received Item"
entry = frappe.qb.DocType("Stock Entry")
entry_item = frappe.qb.DocType("Stock Entry Detail")
work_order = frappe.qb.DocType("Work Order")


def execute():
	for inward_order, fg_row in get_affected_inward_order_rows():
		rows = merge_duplicate_rows(get_own_material_rows(inward_order, fg_row))
		set_consumed_qty(rows, get_consumed_qty(inward_order, fg_row))


def get_affected_inward_order_rows():
	"""Finished good rows with own material on two rows of one Manufacture entry, or with duplicate extra rows."""
	from_entries = (
		get_own_material_query()
		.select(entry.subcontracting_inward_order, work_order.subcontracting_inward_order_item)
		.where(entry.docstatus > 0)
		.groupby(
			entry.name,
			entry.subcontracting_inward_order,
			work_order.subcontracting_inward_order_item,
			entry_item.item_code,
			entry_item.s_warehouse,
		)
		.having(Count("*") > 1)
	).run()

	row = frappe.qb.DocType(RECEIVED_ITEM)
	duplicated = (
		frappe.qb.from_(row)
		.select(row.parent, row.reference_name)
		.where((row.docstatus == 1) & (row.is_additional_item == 1) & (row.is_customer_provided_item == 0))
		.groupby(row.parent, row.reference_name, row.rm_item_code, row.warehouse)
		.having(Count("*") > 1)
	).run()

	return set(from_entries) | set(duplicated)


def get_own_material_query():
	"""Own material rows of inward Manufacture entries."""
	item = frappe.qb.DocType("Item")
	return (
		frappe.qb.from_(entry_item)
		.join(entry)
		.on(entry.name == entry_item.parent)
		.join(work_order)
		.on(work_order.name == entry.work_order)
		.join(item)
		.on(item.name == entry_item.item_code)
		.where(
			(entry.purpose == "Manufacture")
			& (IfNull(entry.subcontracting_inward_order, "") != "")
			& (entry_item.is_finished_item == 0)
			& (IfNull(entry_item.secondary_item_type, "") == "")
			& (IfNull(entry_item.valuation_type, "") == "")
			& (item.is_customer_provided_item == 0)
		)
	)


def get_own_material_rows(inward_order, fg_row):
	return frappe.get_all(
		RECEIVED_ITEM,
		filters={
			"parent": inward_order,
			"reference_name": fg_row,
			"docstatus": 1,
			"is_customer_provided_item": 0,
		},
		fields=["name", "rm_item_code", "warehouse", "is_additional_item", "billed_qty", "returned_qty"],
		order_by="idx",
	)


def merge_duplicate_rows(rows):
	"""Fold each extra row into the first one of its item and warehouse; returns the rows left."""
	kept, first_rows = [], {}
	for row in rows:
		key = (row.rm_item_code, row.warehouse)
		if row.is_additional_item and key in first_rows:
			merge_row(first_rows[key], row)
			continue

		if row.is_additional_item:
			first_rows[key] = row
		kept.append(row)

	return kept


def merge_row(target, row):
	target.billed_qty = flt(target.billed_qty + row.billed_qty, get_precision("billed_qty"))
	target.returned_qty = flt(target.returned_qty + row.returned_qty, get_precision("returned_qty"))
	frappe.db.set_value(
		RECEIVED_ITEM,
		target.name,
		{"billed_qty": target.billed_qty, "returned_qty": target.returned_qty},
		update_modified=False,
	)
	for doctype in ("Sales Invoice Item", "Stock Entry Detail"):
		frappe.db.set_value(
			doctype, {"scio_detail": row.name}, "scio_detail", target.name, update_modified=False
		)
	frappe.db.delete(RECEIVED_ITEM, row.name)


def get_consumed_qty(inward_order, fg_row):
	"""Qty of each own material and warehouse consumed by the submitted Manufacture entries of a finished good row."""
	data = (
		get_own_material_query()
		.select(entry_item.item_code, entry_item.s_warehouse, Sum(entry_item.transfer_qty))
		.where(
			(entry.docstatus == 1)
			& (entry.subcontracting_inward_order == inward_order)
			& (work_order.subcontracting_inward_order_item == fg_row)
		)
		.groupby(entry_item.item_code, entry_item.s_warehouse)
	).run()
	return {(item_code, warehouse): qty for item_code, warehouse, qty in data}


def set_consumed_qty(rows, consumed_qty):
	"""Extra rows take the qty of their own warehouse, BOM rows (no warehouse) the rest of their item."""
	updates = {}
	for row in rows:
		if row.is_additional_item:
			updates[row.name] = consumed_qty.pop((row.rm_item_code, row.warehouse), 0)

	for row in rows:
		if not row.is_additional_item:
			keys = [key for key in consumed_qty if key[0] == row.rm_item_code]
			updates[row.name] = sum(consumed_qty.pop(key) for key in keys)

	precision = get_precision("consumed_qty")
	frappe.db.bulk_update(
		RECEIVED_ITEM,
		{name: {"consumed_qty": flt(qty, precision)} for name, qty in updates.items()},
		update_modified=False,
	)


def get_precision(fieldname):
	return frappe.get_precision(RECEIVED_ITEM, fieldname)
