from collections import Counter, defaultdict

import frappe
import frappe.query_builder
from frappe import _, _dict, bold
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import cint

from erpnext.stock.serial_batch_bundle.bundle_entries import _get_serial_batch_ledgers, parse_serial_nos
from erpnext.stock.serial_batch_identity import SerialBatchIdentity


def get_reserved_voucher_details(kwargs):
	reserved_voucher_details = []

	field_mapper = {
		"Delivery Note": [["Delivery Note Item", "so_detail"]],
		"Sales Invoice": [["Sales Invoice Item", "so_detail"]],
		"Stock Entry": [["Stock Entry", "work_order"], ["Stock Entry", "subcontracting_inward_order"]],
		"Work Order": [["Work Order", "production_plan"], ["Work Order", "subcontracting_inward_order"]],
		"Pick List": [["Pick List", "work_order"]],
	}.get(kwargs.get("sabb_voucher_type"))

	if not field_mapper or not kwargs.get("sabb_voucher_no"):
		return reserved_voucher_details

	voucher_item_filters = {
		"name": kwargs.get("sabb_voucher_detail_no"),
		"parent": kwargs.get("sabb_voucher_no"),
		"docstatus": ("<", 2),
	}
	voucher_based_filters = {
		"Delivery Note": voucher_item_filters,
		"Sales Invoice": voucher_item_filters,
		"Stock Entry": {
			"name": kwargs.get("sabb_voucher_no"),
			"docstatus": ("<", 2),
		},
		"Work Order": {
			"name": kwargs.get("sabb_voucher_no"),
			"docstatus": ("<", 2),
		},
		"Pick List": {
			"name": kwargs.get("sabb_voucher_no"),
			"docstatus": ("<", 2),
		},
	}.get(kwargs.get("sabb_voucher_type"))

	reserved_voucher_details = []
	for row in field_mapper:
		reserved_voucher_details.extend(
			frappe.get_all(
				row[0],
				pluck=row[1],
				filters=voucher_based_filters,
			)
		)

	if kwargs.get("sabb_voucher_type") in ("Delivery Note", "Sales Invoice") and any(
		reserved_voucher_details
	):
		# bundle components are reserved against the Sales Order's packed item rows
		reserved_voucher_details.extend(
			frappe.get_all(
				"Packed Item",
				filters={
					"parenttype": "Sales Order",
					"parent_detail_docname": ("in", reserved_voucher_details),
					"item_code": kwargs.get("item_code"),
				},
				pluck="name",
			)
		)

	return reserved_voucher_details


def get_reserved_serial_nos_for_voucher(kwargs, reserved_entries, reserved_voucher_details):
	serial_nos = []
	if not kwargs.get("pick_reserved_items"):
		return serial_nos

	for entry in reserved_entries:
		if is_reserved_for_voucher(entry, reserved_voucher_details):
			serial_nos.append(entry.serial_no)
			continue

		if kwargs.get("serial_nos") and entry.serial_no in kwargs.get("serial_nos"):
			frappe.throw(
				_(
					"The Serial No {0} is reserved against the {1} {2} and cannot be used for any other transaction."
				).format(
					bold(SerialBatchIdentity("Serial No").get_label(entry.serial_no)),
					entry.voucher_type,
					bold(entry.voucher_no),
				),
				title=_("Serial No Reserved"),
			)

	return serial_nos


def get_other_doc_reserved_serials(kwargs, reserved_entries, reserved_voucher_details):
	serial_nos = []
	for entry in reserved_entries:
		if is_reserved_for_voucher(entry, reserved_voucher_details):
			continue

		serial_nos.append(entry.serial_no)

	return serial_nos


def is_reserved_for_voucher(entry, reserved_voucher_details) -> bool:
	"""Sales vouchers match the reserved Sales Order row, other vouchers the reserved voucher."""
	return entry.voucher_no in reserved_voucher_details or entry.voucher_detail_no in reserved_voucher_details


def get_reserved_serial_nos_for_sre(kwargs) -> list:
	"""Returns a list of `Serial No` reserved in Stock Reservation Entry."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	sb_entry = frappe.qb.DocType("Serial and Batch Entry")
	query = (
		frappe.qb.from_(sre)
		.inner_join(sb_entry)
		.on(sre.name == sb_entry.parent)
		.select(
			sb_entry.serial_no,
			sre.voucher_no,
			sre.voucher_type,
			sre.voucher_detail_no,
		)
		.where(
			(sre.docstatus == 1)
			& (sre.item_code == kwargs.item_code)
			& (sre.status != "Closed")
			& (sre.delivered_qty < sre.reserved_qty)
			& (sb_entry.delivered_qty < sb_entry.qty)
			& (sre.reservation_based_on == "Serial and Batch")
		)
		.orderby(sb_entry.idx)
	)

	if isinstance(kwargs.warehouse, list):
		query = query.where(sre.warehouse.isin(kwargs.warehouse))
	elif kwargs.warehouse:
		query = query.where(sre.warehouse == kwargs.warehouse)

	if kwargs.ignore_voucher_nos:
		query = query.where(sre.name.notin(kwargs.ignore_voucher_nos))

	return query.run(as_dict=True)


def get_serial_no_reservation(item_code: str, serial_no: str, warehouse: str) -> _dict | None:
	"""Returns the Stock Reservation Entry that has reserved the given serial number, if any."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	sb_entry = frappe.qb.DocType("Serial and Batch Entry")
	result = (
		frappe.qb.from_(sre)
		.inner_join(sb_entry)
		.on(sre.name == sb_entry.parent)
		.select(sre.name, sre.voucher_type, sre.voucher_no)
		.where(
			(sre.docstatus == 1)
			& (sre.item_code == item_code)
			& (sre.warehouse == warehouse)
			& (sre.status.notin(["Delivered", "Cancelled", "Closed"]))
			& (sre.reservation_based_on == "Serial and Batch")
			& (sb_entry.serial_no == serial_no)
			& (sb_entry.qty != sb_entry.delivered_qty)
		)
		.limit(1)
		.run(as_dict=True)
	)

	return result[0] if result else None


def get_serial_nos_from_sre(kwargs):
	table = frappe.qb.DocType("Stock Reservation Entry")
	child_table = frappe.qb.DocType("Serial and Batch Entry")
	query = (
		frappe.qb.from_(table)
		.join(child_table)
		.on(table.name == child_table.parent)
		.select(child_table.serial_no, child_table.batch_no, child_table.warehouse)
		.where(
			(table.docstatus == 1)
			& (table.voucher_detail_no == kwargs.scio_detail)
			& (child_table.qty != child_table.delivered_qty)
		)
		.limit(cint(kwargs.qty) or 10000000)
	)
	if kwargs.based_on == "LIFO":
		query = query.orderby(child_table.creation, order=frappe.query_builder.Order.desc)
	else:
		query = query.orderby(child_table.creation)
	return query.run(as_dict=True)


def get_reserved_serial_nos_for_pos(kwargs):
	pos_invoices = get_unconsolidated_pos_invoice_items(kwargs)
	if not pos_invoices:
		return []

	serial_nos_by_row = get_pos_serial_nos_by_row(kwargs.item_code, pos_invoices)
	if kwargs.get("check_serial_nos") and kwargs.get("serial_nos"):
		serial_nos_by_row = filter_rows_by_serial_nos(serial_nos_by_row, kwargs.get("serial_nos"))
		pos_invoices = [row for row in pos_invoices if row.child_docname in serial_nos_by_row]

	reserved_serial_nos = Counter(
		sn for row_serial_nos in serial_nos_by_row.values() for sn in row_serial_nos
	)
	returned_serial_nos = Counter(get_pos_returned_serial_nos(pos_invoices, kwargs))

	return list(reserved_serial_nos - returned_serial_nos)


def get_unconsolidated_pos_invoice_items(kwargs):
	return frappe.get_all(
		"POS Invoice",
		fields=[
			"`tabPOS Invoice Item`.serial_no",
			"`tabPOS Invoice Item`.name as child_docname",
			"`tabPOS Invoice`.name as parent_docname",
			"`tabPOS Invoice Item`.serial_and_batch_bundle",
		],
		filters=[
			["POS Invoice", "consolidated_invoice", "is", "not set"],
			["POS Invoice", "docstatus", "=", 1],
			["POS Invoice", "is_return", "=", 0],
			["POS Invoice Item", "item_code", "=", kwargs.item_code],
			["POS Invoice", "name", "not in", kwargs.ignore_voucher_nos],
		],
	)


def get_pos_serial_nos_by_row(item_code, pos_invoices):
	serial_nos_by_row = defaultdict(list)
	rows_by_bundle = defaultdict(list)
	for row in pos_invoices:
		if row.serial_and_batch_bundle:
			rows_by_bundle[row.serial_and_batch_bundle].append(row.child_docname)

	if rows_by_bundle:
		for d in _get_serial_batch_ledgers(item_code, docstatus=1, name=list(rows_by_bundle)):
			if d.serial_no:
				for child_docname in rows_by_bundle[d.name]:
					serial_nos_by_row[child_docname].append(d.serial_no)

	legacy_rows = [row for row in pos_invoices if row.serial_no and not row.serial_and_batch_bundle]
	row_numbers = [parse_serial_nos(row.serial_no) for row in legacy_rows]
	numbers = [number for row_number_list in row_numbers for number in row_number_list]
	if numbers:
		names = iter(SerialBatchIdentity("Serial No").resolve(item_code, numbers, ignore_permissions=True))
		for row, row_number_list in zip(legacy_rows, row_numbers, strict=True):
			serial_nos_by_row[row.child_docname].extend(next(names) for _number in row_number_list)

	return serial_nos_by_row


def filter_rows_by_serial_nos(serial_nos_by_row, serial_nos):
	serial_nos = set(serial_nos)
	filtered_rows = {}
	for child_docname, row_serial_nos in serial_nos_by_row.items():
		if matched := [sn for sn in row_serial_nos if sn in serial_nos]:
			filtered_rows[child_docname] = matched

	return filtered_rows


def get_pos_returned_serial_nos(pos_invoices, kwargs):
	from erpnext.controllers.sales_and_purchase_return import get_returned_serial_nos

	returned_serial_nos = []
	for row in pos_invoices:
		returned_serial_nos.extend(
			get_returned_serial_nos(
				_dict({"doctype": "POS Invoice Item", "name": row.child_docname}),
				_dict({"doctype": "POS Invoice", "name": row.parent_docname}),
				ignore_voucher_detail_no=kwargs.get("ignore_voucher_detail_no"),
			)
		)

	return returned_serial_nos


def get_reserved_batches_for_pos(kwargs) -> dict:
	"""Returns a dict of `Batch No` followed by the `Qty` reserved in POS Invoices."""

	pos_batches = frappe._dict()
	POS_Invoice = frappe.qb.DocType("POS Invoice")
	POS_Invoice_Item = frappe.qb.DocType("POS Invoice Item")

	pos_invoices = (
		frappe.qb.from_(POS_Invoice)
		.inner_join(POS_Invoice_Item)
		.on(POS_Invoice.name == POS_Invoice_Item.parent)
		.select(
			POS_Invoice_Item.batch_no,
			POS_Invoice_Item.qty,
			POS_Invoice.is_return,
			POS_Invoice_Item.warehouse,
			POS_Invoice_Item.name.as_("child_docname"),
			POS_Invoice.name.as_("parent_docname"),
			POS_Invoice_Item.use_serial_batch_fields,
			POS_Invoice_Item.serial_and_batch_bundle,
		)
		.where(
			(Coalesce(POS_Invoice.consolidated_invoice, "") == "")
			& (POS_Invoice.docstatus == 1)
			& (POS_Invoice_Item.item_code == kwargs.item_code)
		)
	)

	if kwargs.get("company"):
		pos_invoices = pos_invoices.where(POS_Invoice.company == kwargs.get("company"))

	if kwargs.get("ignore_voucher_nos"):
		pos_invoices = pos_invoices.where(POS_Invoice.name.notin(kwargs.get("ignore_voucher_nos")))

	if kwargs.get("warehouse"):
		warehouses = kwargs.warehouse if isinstance(kwargs.warehouse, list) else [kwargs.warehouse]
		pos_invoices = pos_invoices.where(POS_Invoice_Item.warehouse.isin(warehouses))

	pos_invoices = pos_invoices.run(as_dict=True)

	batch_nos = kwargs.get("batch_no") or []
	if isinstance(batch_nos, str):
		batch_nos = [batch_nos]

	ids = [
		pos_invoice.serial_and_batch_bundle
		for pos_invoice in pos_invoices
		if pos_invoice.serial_and_batch_bundle and not pos_invoice.use_serial_batch_fields
	]

	if ids:
		for d in _get_serial_batch_ledgers(kwargs.item_code, docstatus=1, name=ids):
			if batch_nos and d.batch_no not in batch_nos:
				continue

			key = (d.batch_no, d.warehouse)
			if key not in pos_batches:
				pos_batches[key] = frappe._dict(
					{
						"qty": d.qty,
						"warehouse": d.warehouse,
					}
				)
			else:
				pos_batches[key].qty += d.qty

	# POS invoices having batch without bundle (to handle old POS invoices)
	for row in pos_invoices:
		if not row.batch_no or row.serial_and_batch_bundle in ids:
			continue

		if batch_nos and row.batch_no not in batch_nos:
			continue

		key = (row.batch_no, row.warehouse)
		if key in pos_batches:
			pos_batches[key]["qty"] += row.qty * -1
		else:
			pos_batches[key] = frappe._dict(
				{
					"qty": row.qty * -1,
					"warehouse": row.warehouse,
				}
			)

	return pos_batches


def get_reserved_batches_for_sre(kwargs) -> dict:
	"""Returns a dict of `Batch No` followed by the `Qty` reserved in Stock Reservation Entry."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	sb_entry = frappe.qb.DocType("Serial and Batch Entry")
	query = (
		frappe.qb.from_(sre)
		.inner_join(sb_entry)
		.on(sre.name == sb_entry.parent)
		.select(
			sb_entry.batch_no, sre.warehouse, (-1 * Sum(sb_entry.qty - sb_entry.delivered_qty)).as_("qty")
		)
		.where(
			(sre.docstatus == 1)
			& (sre.item_code == kwargs.item_code)
			& (sre.delivered_qty < sre.reserved_qty)
			& (sre.reservation_based_on == "Serial and Batch")
		)
		.groupby(sb_entry.batch_no, sre.warehouse)
	)

	if kwargs.get("company"):
		query = query.where(sre.company == kwargs.get("company"))

	if kwargs.batch_no:
		if isinstance(kwargs.batch_no, list):
			query = query.where(sb_entry.batch_no.isin(kwargs.batch_no))
		else:
			query = query.where(sb_entry.batch_no == kwargs.batch_no)

	if kwargs.warehouse:
		if isinstance(kwargs.warehouse, list):
			query = query.where(sre.warehouse.isin(kwargs.warehouse))
		else:
			query = query.where(sre.warehouse == kwargs.warehouse)

	if kwargs.ignore_voucher_nos:
		query = query.where(sre.name.notin(kwargs.ignore_voucher_nos))

	data = query.run(as_dict=True)

	reserved_batches_details = frappe._dict()
	if data:
		reserved_batches_details = frappe._dict(
			{(d.batch_no, d.warehouse): frappe._dict({"warehouse": d.warehouse, "qty": d.qty}) for d in data}
		)

	return reserved_batches_details


def get_cross_warehouse_sre_details(kwargs):
	sre = frappe.qb.DocType("Stock Reservation Entry")
	sb_entry = frappe.qb.DocType("Serial and Batch Entry")
	query = (
		frappe.qb.from_(sre)
		.inner_join(sb_entry)
		.on(sre.name == sb_entry.parent)
		.select(
			sb_entry.batch_no,
			sre.warehouse,
			Sum(sb_entry.qty - sb_entry.delivered_qty).as_("outstanding_qty"),
		)
		.where(
			(sre.docstatus == 1)
			& (sre.item_code == kwargs.item_code)
			& (sre.delivered_qty < sre.reserved_qty)
			& (sre.reservation_based_on == "Serial and Batch")
			& (sb_entry.batch_no.isnotnull())
		)
		.groupby(sb_entry.batch_no, sre.warehouse)
	)

	if kwargs.get("company"):
		query = query.where(sre.company == kwargs.get("company"))

	if kwargs.warehouse:
		warehouses = kwargs.warehouse if isinstance(kwargs.warehouse, list) else [kwargs.warehouse]
		query = query.where(sre.warehouse.notin(warehouses))

	return query.run(as_dict=True)


def get_batches_to_be_considered(sales_order_name):
	parent = frappe.qb.DocType("Stock Reservation Entry")
	child = frappe.qb.DocType("Serial and Batch Entry")

	query = (
		frappe.qb.from_(parent)
		.join(child)
		.on(parent.name == child.parent)
		.select(child.batch_no, child.warehouse)
		.distinct()
		.where(
			(parent.docstatus == 1)
			& (parent.voucher_no == sales_order_name)
			& (child.delivered_qty < child.qty)
		)
	)
	return query.run(as_dict=True)
