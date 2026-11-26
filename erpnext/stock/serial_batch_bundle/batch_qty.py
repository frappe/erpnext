import frappe
from frappe import _, bold
from frappe.utils import flt, get_link_to_form

from erpnext.stock.serial_batch_identity import SerialBatchIdentity


def update_batch_qty(voucher_type, voucher_no, docstatus, via_landed_cost_voucher=False):
	batches = get_batchwise_qty(voucher_type, voucher_no)
	if not batches:
		return

	precision = frappe.get_precision("Batch", "batch_qty")
	for batch, qty in sorted(batches.items()):
		current_qty = get_batch_current_qty(batch)
		current_qty += flt(qty, precision) * (-1 if docstatus == 2 else 1)

		if not via_landed_cost_voucher and current_qty < 0:
			throw_negative_batch_validation(batch, current_qty)

		frappe.db.set_value("Batch", batch, "batch_qty", current_qty)


def get_batch_current_qty(batch):
	doctype = frappe.qb.DocType("Batch")
	query = frappe.qb.from_(doctype).select(doctype.batch_qty).where(doctype.name == batch).for_update()
	batch_qty = query.run()

	return flt(batch_qty[0][0]) if batch_qty else 0.0


def throw_negative_batch_validation(batch_no, qty):
	# This validation is important for backdated stock transactions with batch items
	frappe.throw(
		_(
			"The Batch {0} has negative batch quantity {1}. To fix this, go to the batch and click on Recalculate Batch Qty. If the issue still persists, create an inward entry."
		).format(
			bold(get_link_to_form("Batch", batch_no, SerialBatchIdentity("Batch").get_label(batch_no))),
			bold(qty),
		),
		title=_("Negative Stock Error"),
	)


def get_batchwise_qty(voucher_type, voucher_no):
	bundles = frappe.get_all(
		"Serial and Batch Bundle",
		filters={"voucher_no": voucher_no, "voucher_type": voucher_type, "docstatus": (">", 0)},
		pluck="name",
	)
	if not bundles:
		return

	batches = frappe.get_all(
		"Serial and Batch Entry",
		filters={"parent": ("in", bundles), "batch_no": ("is", "set")},
		fields=["batch_no", {"SUM": "qty", "as": "qty"}],
		group_by="batch_no",
		as_list=1,
	)

	if not batches:
		return frappe._dict({})

	return frappe._dict(batches)


def get_empty_batches_based_work_order(work_order, item_code):
	batches = get_batches_from_work_order(work_order, item_code)
	if not batches:
		return batches

	entries = get_batches_from_stock_entries(work_order, item_code)
	if not entries:
		return batches

	ids = [d.serial_and_batch_bundle for d in entries if d.serial_and_batch_bundle]
	if ids:
		set_batch_details_from_package(ids, batches)

	# Will be deprecated in v16
	for d in entries:
		if not d.batch_no:
			continue

		batches[d.batch_no] -= d.qty

	return batches


def get_batches_from_work_order(work_order, item_code):
	return frappe._dict(
		frappe.get_all(
			"Batch",
			fields=["name", "qty_to_produce"],
			filters={"reference_name": work_order, "item": item_code},
			as_list=1,
		)
	)


def get_batches_from_stock_entries(work_order, item_code):
	entries = frappe.get_all(
		"Stock Entry",
		filters={"work_order": work_order, "docstatus": 1, "purpose": "Manufacture"},
		fields=["name"],
	)

	return frappe.get_all(
		"Stock Entry Detail",
		fields=["batch_no", "qty", "serial_and_batch_bundle"],
		filters={
			"parent": ("in", [d.name for d in entries]),
			"is_finished_item": 1,
			"item_code": item_code,
		},
	)


def set_batch_details_from_package(ids, batches):
	entries = frappe.get_all(
		"Serial and Batch Entry",
		filters={"parent": ("in", ids), "is_outward": 0},
		fields=["batch_no", "qty"],
	)

	for d in entries:
		batches[d.batch_no] -= d.qty
