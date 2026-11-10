from collections import defaultdict

import frappe
from frappe.query_builder.functions import IfNull


def execute():
	for (plan, plan_row), receipt_rows in get_plan_rows_of_receipt_reservations().items():
		relink_reservations(plan, plan_row, receipt_rows)
		recount_plan_row(plan_row)


def get_plan_rows_of_receipt_reservations() -> dict:
	sre = frappe.qb.DocType("Stock Reservation Entry")
	receipt_item = frappe.qb.DocType("Purchase Receipt Item")
	mr_item = frappe.qb.DocType("Material Request Item")
	rows = (
		frappe.qb.from_(sre)
		.inner_join(receipt_item)
		.on(receipt_item.name == sre.voucher_detail_no)
		.inner_join(mr_item)
		.on(mr_item.name == receipt_item.material_request_item)
		.select(sre.voucher_no, mr_item.material_request_plan_item, receipt_item.name)
		.distinct()
		.where(
			(sre.voucher_type == "Production Plan")
			& (sre.from_voucher_type == "Purchase Receipt")
			& (IfNull(mr_item.material_request_plan_item, "") != "")
		)
	).run()

	plan_rows = defaultdict(list)
	for plan, plan_row, receipt_row in rows:
		plan_rows[(plan, plan_row)].append(receipt_row)

	return plan_rows


def relink_reservations(plan: str, plan_row: str, receipt_rows: list) -> None:
	sre = frappe.qb.DocType("Stock Reservation Entry")
	(
		frappe.qb.update(sre)
		.set(sre.voucher_detail_no, plan_row)
		.where(
			(sre.voucher_type == "Production Plan")
			& (sre.voucher_no == plan)
			& sre.voucher_detail_no.isin(receipt_rows)
		)
	).run()
	(
		frappe.qb.update(sre)
		.set(sre.from_voucher_detail_no, plan_row)
		.where(
			(sre.from_voucher_type == "Production Plan")
			& (sre.from_voucher_no == plan)
			& sre.from_voucher_detail_no.isin(receipt_rows)
		)
	).run()


def recount_plan_row(plan_row: str) -> None:
	if sre_name := frappe.db.get_value(
		"Stock Reservation Entry",
		{"voucher_type": "Production Plan", "voucher_detail_no": plan_row, "docstatus": 1},
	):
		frappe.get_doc("Stock Reservation Entry", sre_name).update_reserved_qty_in_voucher(
			update_modified=False
		)
