import frappe
from frappe.query_builder.functions import IfNull


def execute():
	sre = frappe.qb.DocType("Stock Reservation Entry")
	(
		frappe.qb.update(sre)
		.set(sre.from_voucher_type, "Pick List")
		.set(sre.from_voucher_no, sre.against_pick_list)
		.set(sre.from_voucher_detail_no, sre.against_pick_list_item)
		.where(
			(IfNull(sre.against_pick_list, "") != "") & (IfNull(sre.against_pick_list_item, "") != "")
		)
	).run()
