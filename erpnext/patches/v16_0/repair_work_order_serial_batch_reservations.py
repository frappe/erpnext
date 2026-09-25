import frappe
from frappe.utils import flt

from erpnext.manufacturing.doctype.work_order.services.reservation import get_row_wise_serial_batch

FINISHED_WORK_ORDER_STATUSES = ("Completed", "Closed", "Stopped")


def execute():
	for name, work_order in get_used_serial_batch_reservations():
		sre = frappe.get_doc("Stock Reservation Entry", name)
		purpose = "Material Transfer for Manufacture" if sre.transferred_qty else "Manufacture"
		sre.consume_serial_batch_for_material_transfer(get_row_wise_serial_batch(work_order, purpose))
		if sre.matched_serial_batch_qty >= flt(sre.transferred_qty) + flt(sre.consumed_qty):
			continue

		if frappe.db.get_value("Work Order", work_order, "status") in FINISHED_WORK_ORDER_STATUSES:
			release_rows(sre)
		else:
			reopen(sre)


def get_used_serial_batch_reservations():
	return frappe.get_all(
		"Stock Reservation Entry",
		filters={"docstatus": 1, "voucher_type": "Work Order", "reservation_based_on": "Serial and Batch"},
		or_filters={"transferred_qty": (">", 0), "consumed_qty": (">", 0)},
		fields=["name", "voucher_no"],
		as_list=True,
	)


def release_rows(sre):
	for entry in sre.sb_entries:
		entry.db_set("delivered_qty", entry.qty, update_modified=False)


def reopen(sre):
	fieldname = "transferred_qty" if sre.transferred_qty else "consumed_qty"
	sre.db_set(fieldname, sre.matched_serial_batch_qty, update_modified=False)
	sre.update_status()
	sre.update_reserved_stock_in_bin()
