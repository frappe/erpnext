import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import flt


def execute():
	precision = frappe.get_precision("Subcontracting Inward Order Received Item", "returned_qty")
	rows = [row for row in get_returned_rows() if flt(row.qty, precision) != flt(row.returned_qty, precision)]
	frappe.db.bulk_update(
		"Subcontracting Inward Order Received Item",
		{row.name: {"returned_qty": flt(row.qty, precision)} for row in rows},
		update_modified=False,
	)
	for name in {row.parent for row in rows}:
		order = frappe.get_doc("Subcontracting Inward Order", name)
		order.update_status(order.status, update_modified=False)


def get_returned_rows():
	"""Submitted received items with the qty their submitted raw material returns add up to."""
	received_item = frappe.qb.DocType("Subcontracting Inward Order Received Item")
	entry = frappe.qb.DocType("Stock Entry")
	entry_item = frappe.qb.DocType("Stock Entry Detail")

	returned_qty = (
		frappe.qb.from_(entry_item)
		.join(entry)
		.on(entry.name == entry_item.parent)
		.select(Sum(entry_item.transfer_qty))
		.where(
			(entry_item.scio_detail == received_item.name)
			& (entry.docstatus == 1)
			& (entry.purpose == "Return Raw Material to Customer")
			& (entry.subcontracting_inward_order == received_item.parent)
		)
	)
	return (
		frappe.qb.from_(received_item)
		.select(
			received_item.name,
			received_item.parent,
			received_item.returned_qty,
			returned_qty.as_("qty"),
		)
		.where(received_item.docstatus == 1)
		.run(as_dict=True)
	)
