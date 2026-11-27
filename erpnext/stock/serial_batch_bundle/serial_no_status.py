import frappe
from frappe.query_builder import Case
from frappe.utils import add_days, cint, getdate
from pypika import Order

CONSUMED_SERIAL_NO_STOCK_ENTRY_PURPOSES = (
	"Manufacture",
	"Material Issue",
	"Repack",
	"Material Consumption for Manufacture",
)


INACTIVE_SERIAL_NO_STOCK_ENTRY_PURPOSES = ("Disassemble", "Material Receipt")


def get_serial_no_status(sle):
	warehouse = sle.warehouse if sle.actual_qty > 0 else None
	if warehouse:
		return "Active"

	status = get_status_for_serial_nos(sle)
	if sle.voucher_type == "Stock Entry" and sle.actual_qty < 0:
		purpose = frappe.get_cached_value("Stock Entry", sle.voucher_no, "purpose")
		if purpose in INACTIVE_SERIAL_NO_STOCK_ENTRY_PURPOSES:
			status = "Inactive"

	return status


def get_status_for_serial_nos(sle):
	status = "Inactive"
	if sle.actual_qty < 0 and sle.voucher_type not in ["Purchase Invoice", "Purchase Receipt"]:
		status = "Delivered"
		if sle.voucher_type == "Stock Entry":
			purpose = frappe.get_cached_value("Stock Entry", sle.voucher_no, "purpose")
			if purpose in CONSUMED_SERIAL_NO_STOCK_ENTRY_PURPOSES:
				status = "Consumed"

		if sle.is_cancelled == 1 and (
			sle.voucher_type in ["Purchase Invoice", "Purchase Receipt", "Stock Reconciliation"]
			or status == "Consumed"
		):
			status = "Inactive"

	return status


def get_serial_no_status_term(sn_table, sle, warehouse, status):
	if warehouse:
		return "Active"

	if not sle.is_cancelled:
		return status

	return Case().when(sn_table.reference_name == sle.voucher_no, "Inactive").else_(status)


def update_serial_no_status(sle, serial_nos):
	warehouse = sle.warehouse if sle.actual_qty > 0 else None

	if isinstance(serial_nos, str):
		serial_nos = [serial_nos]

	status = get_serial_no_status(sle)

	customer = None
	if sle.voucher_type in ["Sales Invoice", "Delivery Note"] and sle.actual_qty < 0:
		customer = frappe.get_cached_value(sle.voucher_type, sle.voucher_no, "customer")

	sn_table = frappe.qb.DocType("Serial No")

	query = (
		frappe.qb.update(sn_table)
		.set(sn_table.warehouse, warehouse)
		.set(sn_table.status, get_serial_no_status_term(sn_table, sle, warehouse, status))
		.set(sn_table.company, sle.company)
		.set(sn_table.customer, customer)
		.where(sn_table.name.isin(serial_nos))
	)

	if status == "Delivered":
		warranty_period = frappe.get_cached_value("Item", sle.item_code, "warranty_period")
		if warranty_period:
			warranty_expiry_date = add_days(getdate(sle.posting_datetime), cint(warranty_period))
			query = query.set(sn_table.warranty_expiry_date, warranty_expiry_date)
			query = query.set(sn_table.warranty_period, warranty_period)
	else:
		query = query.set(sn_table.warranty_expiry_date, None)
		query = query.set(sn_table.warranty_period, 0)

	query.run()


def update_serial_no_status_for_stock_reco(serial_nos):
	for serial_no in serial_nos:
		sle_doctype = frappe.qb.DocType("Stock Ledger Entry")
		sn_table = frappe.qb.DocType("Serial and Batch Entry")

		query = (
			frappe.qb.from_(sle_doctype)
			.inner_join(sn_table)
			.on(sle_doctype.serial_and_batch_bundle == sn_table.parent)
			.select(
				sle_doctype.warehouse,
				sle_doctype.actual_qty,
				sle_doctype.voucher_type,
				sle_doctype.voucher_no,
				sle_doctype.is_cancelled,
				sle_doctype.item_code,
				sle_doctype.posting_datetime,
				sle_doctype.company,
			)
			.where(
				(sn_table.serial_no == serial_no)
				& (sle_doctype.is_cancelled == 0)
				& (sn_table.docstatus == 1)
			)
			.orderby(sle_doctype.posting_datetime, order=Order.desc)
			.orderby(sle_doctype.creation, order=Order.desc)
			.limit(1)
		)

		sle = query.run(as_dict=1)
		if sle:
			update_serial_no_status(sle[0], serial_no)


def set_batch_no_in_serial_nos(serial_and_batch_bundle):
	entries = frappe.get_all(
		"Serial and Batch Entry",
		fields=["serial_no", "batch_no"],
		filters={"parent": serial_and_batch_bundle},
	)

	batch_serial_nos = {}
	for ledger in entries:
		batch_serial_nos.setdefault(ledger.batch_no, []).append(ledger.serial_no)

	for batch_no, serial_nos in batch_serial_nos.items():
		sn_table = frappe.qb.DocType("Serial No")
		(
			frappe.qb.update(sn_table).set(sn_table.batch_no, batch_no).where(sn_table.name.isin(serial_nos))
		).run()
