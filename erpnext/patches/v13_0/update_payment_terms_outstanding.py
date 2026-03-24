# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "Payment Schedule")
	if frappe.db.count("Payment Schedule"):
		payment_schedule = frappe.qb.DocType("Payment Schedule")
		(
			frappe.qb.update(payment_schedule).set(
				payment_schedule.outstanding, payment_schedule.payment_amount - payment_schedule.paid_amount
			)
		).run()
