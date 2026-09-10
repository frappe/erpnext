# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import cstr, flt
from pypika import analytics as an

from erpnext.stock.serial_batch_bundle import get_serial_no_status


def execute(filters=None):
	validate_warehouse(filters)
	columns = get_columns()
	data = get_data(filters.warehouse, filters.show_disabled_items)
	return columns, data


def validate_warehouse(filters):
	company = filters.company
	warehouse = filters.warehouse
	if not frappe.db.exists("Warehouse", {"name": warehouse, "company": company}):
		frappe.throw(_("Warehouse: {0} does not belong to {1}").format(warehouse, company))


def get_columns():
	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 200,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Serial No Count"), "fieldname": "total", "fieldtype": "Float", "width": 150},
		{"label": _("Stock Qty"), "fieldname": "stock_qty", "fieldtype": "Float", "width": 150},
		{"label": _("Difference"), "fieldname": "difference", "fieldtype": "Float", "width": 150},
	]

	return columns


def get_warehouses(warehouse):
	if frappe.db.get_value("Warehouse", warehouse, "is_group"):
		from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses

		return get_child_warehouses(warehouse)

	return [warehouse]


def get_data(warehouse, show_disabled_items):
	# A group (parent) warehouse holds no stock itself; stock lives in its child
	# warehouses. Expand it to all its descendants so the report aggregates them.
	warehouses = get_warehouses(warehouse)

	filters = {"has_serial_no": True}
	if not show_disabled_items:
		filters["disabled"] = False
	serial_item_list = frappe.get_all(
		"Item",
		filters=filters,
		fields=["item_code", "item_name"],
	)

	status_list = ["Active", "Expired"]
	data = []
	for item in serial_item_list:
		total_serial_no = frappe.db.count(
			"Serial No",
			filters={
				"item_code": item.item_code,
				"status": ("in", status_list),
				"warehouse": ("in", warehouses),
			},
		)

		bin_table = frappe.qb.DocType("Bin")
		bin_qty = (
			frappe.qb.from_(bin_table)
			.select(Sum(bin_table.actual_qty))
			.where(bin_table.item_code == item.item_code)
			.where(bin_table.warehouse.isin(warehouses))
		).run()

		# Sum is null when no Bin record exists for the item in these warehouses.
		actual_qty = flt(bin_qty[0][0]) if bin_qty else 0

		difference = total_serial_no - actual_qty

		row = {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"total": total_serial_no,
			"stock_qty": actual_qty,
			"difference": difference,
		}

		data.append(row)

	return data


SYNC_CHUNK_SIZE = 1000


@frappe.whitelist(methods=["POST"])
def sync_serial_no_status(warehouse: str, item_code: str | None = None):
	if not frappe.has_permission("Serial No", "write"):
		frappe.throw(_("Not permitted to update Serial No"), frappe.PermissionError)

	warehouse = cstr(warehouse)
	item_code = cstr(item_code) if item_code else None
	if not frappe.db.exists("Warehouse", warehouse):
		frappe.throw(_("Warehouse {0} does not exist").format(warehouse))

	if item_code and not frappe.db.exists("Item", item_code):
		frappe.throw(_("Item {0} does not exist").format(item_code))

	frappe.enqueue(
		sync_serial_no_status_for_warehouse,
		queue="long",
		warehouse=warehouse,
		item_code=item_code,
	)
	frappe.msgprint(
		_("Serial No status sync has been queued. Reload the report after a few minutes."),
		alert=True,
	)


def sync_serial_no_status_for_warehouse(warehouse, item_code=None):
	filters = {"has_serial_no": 1}
	if item_code:
		filters["name"] = item_code

	for item in frappe.get_all("Item", filters=filters, pluck="name"):
		sync_serial_no_status_for_item(item, warehouse)


def sync_serial_no_status_for_item(item_code, warehouse):
	"""Correct Serial No records this report counts in the warehouse but whose last
	stock ledger movement says the stock left it. Reposting rebuilds qty and valuation
	from the ledger but never rewrites Serial No warehouse/status, so records orphaned
	by cancelled or amended vouchers keep inflating the serial count."""
	serial_nos = frappe.get_all(
		"Serial No",
		filters={"item_code": item_code, "warehouse": warehouse, "status": ("in", ["Active", "Expired"])},
		pluck="name",
	)
	if not serial_nos:
		return

	last_moves = get_last_ledger_moves(item_code, serial_nos)
	for serial_no in serial_nos:
		row = last_moves.get(serial_no)
		if row and flt(row.qty) > 0 and row.warehouse == warehouse:
			continue

		set_serial_no_state_from_ledger(serial_no, row)


def set_serial_no_state_from_ledger(serial_no, row):
	if not row:
		frappe.db.set_value(
			"Serial No", serial_no, {"warehouse": None, "status": "Inactive"}, update_modified=False
		)
		return

	status = get_serial_no_status(
		frappe._dict(
			actual_qty=flt(row.qty),
			warehouse=row.warehouse,
			voucher_type=row.voucher_type,
			voucher_no=row.voucher_no,
			is_cancelled=0,
		)
	)
	warehouse = row.warehouse if status == "Active" else None
	frappe.db.set_value(
		"Serial No", serial_no, {"warehouse": warehouse, "status": status}, update_modified=False
	)


def get_last_ledger_moves(item_code, serial_nos):
	last_moves = get_last_bundle_moves(item_code, serial_nos)
	if missing := [serial_no for serial_no in serial_nos if serial_no not in last_moves]:
		set_legacy_last_moves(item_code, missing, last_moves)

	return last_moves


def get_last_bundle_moves(item_code, serial_nos):
	last_moves = {}
	for start in range(0, len(serial_nos), SYNC_CHUNK_SIZE):
		for row in get_last_bundle_moves_chunk(item_code, serial_nos[start : start + SYNC_CHUNK_SIZE]):
			last_moves[row.serial_no] = row

	return last_moves


def get_last_bundle_moves_chunk(item_code, serial_nos):
	"""A bundle can be created much before its Stock Ledger Entry, so same-posting-datetime
	ties are broken on the creation of the bundle's own SLE. The SLE join also keeps only
	real stock movements - reservation bundles (Pick List) carry no SLE."""
	entry = frappe.qb.DocType("Serial and Batch Entry")
	bundle = frappe.qb.DocType("Serial and Batch Bundle")
	sle = frappe.qb.DocType("Stock Ledger Entry")

	row_number = (
		an.RowNumber()
		.over(entry.serial_no)
		.orderby(Coalesce(entry.posting_datetime, bundle.posting_datetime), order=Order.desc)
		.orderby(sle.creation, order=Order.desc)
	)

	ranked = (
		frappe.qb.from_(entry)
		.inner_join(bundle)
		.on(entry.parent == bundle.name)
		.inner_join(sle)
		.on(sle.serial_and_batch_bundle == bundle.name)
		.select(
			entry.serial_no,
			entry.qty,
			Coalesce(entry.warehouse, bundle.warehouse).as_("warehouse"),
			bundle.voucher_type,
			bundle.voucher_no,
			row_number.as_("row_no"),
		)
		.where(
			(bundle.docstatus == 1)
			& (Coalesce(bundle.is_cancelled, 0) == 0)
			& (sle.is_cancelled == 0)
			& (bundle.item_code == item_code)
			& (entry.serial_no.isin(serial_nos))
		)
	).as_("ranked")

	return (
		frappe.qb.from_(ranked)
		.select(ranked.serial_no, ranked.qty, ranked.warehouse, ranked.voucher_type, ranked.voucher_no)
		.where(ranked.row_no == 1)
		.run(as_dict=True)
	)


def set_legacy_last_moves(item_code, serial_nos, last_moves):
	"""Movements posted before Serial and Batch Bundle exist only as newline-separated
	text on Stock Ledger Entry."""
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	pending = set(serial_nos)
	rows = frappe.get_all(
		"Stock Ledger Entry",
		filters={"item_code": item_code, "is_cancelled": 0, "serial_no": ("is", "set")},
		fields=["serial_no", "actual_qty", "warehouse", "voucher_type", "voucher_no"],
		order_by="posting_datetime asc, creation asc",
	)

	for row in rows:
		qty = 1 if flt(row.actual_qty) > 0 else -1
		for serial_no in get_serial_nos(row.serial_no):
			if serial_no in pending:
				last_moves[serial_no] = frappe._dict(
					qty=qty,
					warehouse=row.warehouse,
					voucher_type=row.voucher_type,
					voucher_no=row.voucher_no,
				)
