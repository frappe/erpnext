import frappe
from frappe.utils import (
	escape_html,
)

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
