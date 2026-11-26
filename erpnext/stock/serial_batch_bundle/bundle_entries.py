from collections import defaultdict

import frappe
from frappe.utils import cstr, escape_html, flt, parse_json

from erpnext.stock.serial_batch_identity import SerialBatchIdentity

# their bundles only reserve stock; a POS Invoice's bundle moves to its Sales Invoice on consolidation
RESERVING_VOUCHER_TYPES = ("Pick List", "POS Invoice")


def get_serial_nos(serial_and_batch_bundle, serial_nos=None):
	if not serial_and_batch_bundle:
		return []

	filters = {"parent": serial_and_batch_bundle, "serial_no": ("is", "set")}
	if isinstance(serial_and_batch_bundle, list):
		filters = {"parent": ("in", serial_and_batch_bundle)}

	if serial_nos:
		filters["serial_no"] = ("in", serial_nos)

	serial_nos = frappe.get_all("Serial and Batch Entry", filters=filters, order_by="idx", pluck="serial_no")

	return serial_nos


def get_serial_nos_from_bundle(serial_and_batch_bundle, serial_nos=None):
	return get_serial_nos(serial_and_batch_bundle, serial_nos=serial_nos)


def get_batches_from_bundle(serial_and_batch_bundle, batches=None):
	if not serial_and_batch_bundle:
		return []

	filters = {"parent": serial_and_batch_bundle, "batch_no": ("is", "set")}
	if isinstance(serial_and_batch_bundle, list):
		filters = {"parent": ("in", serial_and_batch_bundle)}

	if batches:
		filters["batch_no"] = ("in", batches)

	entries = frappe.get_all(
		"Serial and Batch Entry", fields=["batch_no", "qty"], filters=filters, order_by="idx", as_list=1
	)
	if not entries:
		return frappe._dict({})

	return frappe._dict(entries)


def get_batch_nos(serial_and_batch_bundle):
	if not serial_and_batch_bundle:
		return frappe._dict({})

	entries = frappe.get_all(
		"Serial and Batch Entry",
		fields=["batch_no", {"SUM": "qty", "as": "qty"}],
		filters={"parent": serial_and_batch_bundle, "batch_no": ("is", "set")},
		order_by="idx",
		group_by="batch_no",
	)

	if not entries:
		return frappe._dict({})

	return {d.batch_no: d for d in entries}


def get_serial_or_batch_nos(bundle):
	"""Render physical numbers without changing bundle references."""

	bundle_data = frappe.get_cached_value(
		"Serial and Batch Bundle", bundle, ["has_serial_no", "has_batch_no"], as_dict=True
	)

	fields = []
	if bundle_data.has_serial_no:
		fields.append("serial_no")

	if bundle_data.has_batch_no:
		fields.extend(["batch_no", "qty"])

	data = frappe.get_all("Serial and Batch Entry", fields=fields, filters={"parent": bundle}, order_by="idx")
	for fieldname, doctype in (("serial_no", "Serial No"), ("batch_no", "Batch")):
		if fieldname not in fields:
			continue
		numbers = SerialBatchIdentity(doctype).get_number_map(
			[row[fieldname] for row in data if row[fieldname]]
		)
		for row in data:
			if row[fieldname]:
				row[fieldname] = escape_html(numbers.get(row[fieldname], row[fieldname]))

	if bundle_data.has_serial_no and not bundle_data.has_batch_no:
		return ", ".join([d.serial_no for d in data])

	elif bundle_data.has_batch_no:
		html = "<table class= 'table table-borderless' style='margin-top: 0px;margin-bottom: 0px;'>"
		for d in data:
			if d.serial_no:
				html += f"<tr><td>{d.batch_no}</td><td>{d.serial_no}</td><td>{abs(d.qty)}</td></tr>"
			else:
				html += f"<tr><td>{d.batch_no}</td><td>{abs(d.qty)}</td></tr>"

		html += "</table>"

		return html


def get_serial_or_batch_items(items):
	serial_or_batch_items = frappe.get_all(
		"Item",
		filters={"name": ("in", [d.item_code for d in items])},
		or_filters={"has_serial_no": 1, "has_batch_no": 1},
	)

	if not serial_or_batch_items:
		return
	else:
		serial_or_batch_items = [d.name for d in serial_or_batch_items]

	return serial_or_batch_items


def get_serial_nos_batch(serial_nos):
	return frappe._dict(
		frappe.get_all(
			"Serial No",
			fields=["name", "batch_no"],
			filters={"name": ("in", serial_nos)},
			as_list=1,
		)
	)


def get_serial_batch_list_from_item(item):
	serial_list, batch_list = [], []
	if item.get("serial_and_batch_bundle"):
		table = frappe.qb.DocType("Serial and Batch Entry")
		query = (
			frappe.qb.from_(table)
			.select(table.serial_no, table.batch_no)
			.where(table.parent == item.serial_and_batch_bundle)
		)
		result = query.run(as_dict=True)

		for row in result:
			if row.serial_no and row.serial_no not in serial_list:
				serial_list.append(row.serial_no)
			if row.batch_no and row.batch_no not in batch_list:
				batch_list.append(row.batch_no)
	else:
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if item.get("serial_no"):
			serial_list = SerialBatchIdentity("Serial No").resolve(
				item.item_code, get_serial_nos(item.serial_no), ignore_permissions=True
			)
		batch_list = [item.batch_no] if item.get("batch_no") else []

	return serial_list, batch_list


def add_picked_batches(picked_batches, entries):
	for entry in entries:
		if entry.batch_no:
			picked = picked_batches.setdefault(
				(entry.batch_no, entry.warehouse),
				frappe._dict(batch_no=entry.batch_no, warehouse=entry.warehouse, qty=0),
			)
			picked.qty += entry.qty


def parse_serial_nos(serial_no):
	if isinstance(serial_no, list):
		return serial_no

	return [s.strip() for s in cstr(serial_no).strip().replace(",", "\n").split("\n") if s.strip()]


def _get_serial_batch_ledgers(
	item_code: str | None = None,
	docstatus: str | list | int | None = None,
	voucher_no: str | None = None,
	name: str | list | None = None,
	child_row: dict | str | None = None,
):
	fields, filters = _get_bundle_ledger_query(item_code, docstatus, voucher_no, name, child_row)

	return frappe.get_all(
		"Serial and Batch Bundle",
		fields=fields,
		filters=filters,
		order_by="`tabSerial and Batch Entry`.`idx`",
	)


def _get_bundle_ledger_query(item_code, docstatus, voucher_no, name, child_row):
	filters = get_filters_for_bundle(
		item_code=item_code, docstatus=docstatus, voucher_no=voucher_no, name=name, child_row=child_row
	)

	fields = [
		"`tabSerial and Batch Bundle`.`item_code`",
		"`tabSerial and Batch Entry`.`qty`",
		"`tabSerial and Batch Entry`.`warehouse`",
		"`tabSerial and Batch Entry`.`batch_no`",
		"`tabSerial and Batch Entry`.`serial_no`",
		"`tabSerial and Batch Entry`.`name` as `child_row`",
	]

	if not child_row:
		fields.append("`tabSerial and Batch Bundle`.`name`")

	return fields, filters


def get_filters_for_bundle(item_code=None, docstatus=None, voucher_no=None, name=None, child_row=None):
	filters = [
		["Serial and Batch Bundle", "is_cancelled", "=", 0],
	]

	if child_row and isinstance(child_row, str):
		child_row = parse_json(child_row)

	if not name and child_row:
		bundle = get_reference_serial_and_batch_bundle(child_row)
		if bundle:
			voucher_no = None
			filters.append(["Serial and Batch Bundle", "name", "=", bundle])

	if item_code:
		filters.append(["Serial and Batch Bundle", "item_code", "=", item_code])

	if not docstatus:
		docstatus = [0, 1]

	if isinstance(docstatus, list):
		filters.append(["Serial and Batch Bundle", "docstatus", "in", docstatus])
	else:
		filters.append(["Serial and Batch Bundle", "docstatus", "=", docstatus])

	if voucher_no:
		filters.append(["Serial and Batch Bundle", "voucher_no", "=", voucher_no])

	if name:
		if isinstance(name, list):
			filters.append(["Serial and Batch Entry", "parent", "in", name])
		else:
			filters.append(["Serial and Batch Entry", "parent", "=", name])

	return filters


def get_reference_serial_and_batch_bundle(child_row):
	if flt(child_row.get("rejected_qty" if child_row.get("is_rejected") else "qty")) >= 0:
		return

	doctype = child_row.get("doctype")
	field = {
		"Sales Invoice Item": "sales_invoice_item",
		"Delivery Note Item": "dn_detail",
		"Purchase Receipt Item": "purchase_receipt_item",
		"Purchase Invoice Item": "purchase_invoice_item",
		"POS Invoice Item": "pos_invoice_item",
		"Subcontracting Receipt Item": "subcontracting_receipt_item",
	}.get(doctype)

	if field:
		from_rejected = child_row.get("is_rejected") or child_row.get("return_qty_from_rejected_warehouse")
		bundle_field = "rejected_serial_and_batch_bundle" if from_rejected else "serial_and_batch_bundle"
		return frappe.get_cached_value(doctype, child_row.get(field), bundle_field)


# For work order and subcontracting
def get_voucher_wise_serial_batch_from_bundle(**kwargs) -> dict[str, dict]:
	data = get_ledgers_from_serial_batch_bundle(**kwargs)
	if not data:
		return {}

	group_by_voucher = {}

	for row in data:
		key = (row.item_code, row.warehouse, row.voucher_no)
		if kwargs.get("get_subcontracted_item"):
			# get_subcontracted_item = ("doctype", "field_name")
			doctype, field_name = kwargs.get("get_subcontracted_item")

			subcontracted_item_code = frappe.get_cached_value(doctype, row.voucher_detail_no, field_name)
			key = (row.item_code, subcontracted_item_code, row.warehouse, row.voucher_no)

		if key not in group_by_voucher:
			group_by_voucher.setdefault(
				key,
				frappe._dict({"serial_nos": [], "batch_nos": defaultdict(float), "item_row": row}),
			)

		child_row = group_by_voucher[key]
		if row.serial_no:
			child_row["serial_nos"].append(row.serial_no)
			child_row["item_row"].qty = len(child_row["serial_nos"]) * (
				-1 if row.type_of_transaction == "Outward" else 1
			)

		if row.batch_no:
			child_row["batch_nos"][row.batch_no] += row.qty

	return group_by_voucher


def get_ledgers_from_serial_batch_bundle(**kwargs) -> list[frappe._dict]:
	bundle_table = frappe.qb.DocType("Serial and Batch Bundle")
	serial_batch_table = frappe.qb.DocType("Serial and Batch Entry")

	query = (
		frappe.qb.from_(bundle_table)
		.inner_join(serial_batch_table)
		.on(bundle_table.name == serial_batch_table.parent)
		.select(
			serial_batch_table.serial_no,
			bundle_table.warehouse,
			bundle_table.item_code,
			serial_batch_table.batch_no,
			serial_batch_table.qty,
			serial_batch_table.incoming_rate,
			bundle_table.voucher_detail_no,
			bundle_table.voucher_no,
			bundle_table.posting_datetime,
			bundle_table.type_of_transaction,
		)
		.where(
			(bundle_table.docstatus == 1)
			& (bundle_table.is_cancelled == 0)
			& (bundle_table.type_of_transaction.isin(["Inward", "Outward"]))
		)
		.orderby(bundle_table.posting_datetime)
	)

	for key, val in kwargs.items():
		if val is None:
			continue

		if not val and isinstance(val, list):
			return []

		if key == "get_subcontracted_item":
			continue

		if key in ["name", "item_code", "warehouse", "voucher_no", "company", "voucher_detail_no"]:
			if isinstance(val, list):
				query = query.where(bundle_table[key].isin(val))
			else:
				query = query.where(bundle_table[key] == val)
		elif key in ["posting_datetime"]:
			query = query.where(bundle_table[key] >= val)
		else:
			if isinstance(val, list):
				query = query.where(serial_batch_table[key].isin(val))
			else:
				query = query.where(serial_batch_table[key] == val)

	return query.run(as_dict=True)
