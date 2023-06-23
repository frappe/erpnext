# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "Process Statement of Accounts", force=True)
	process_soa = frappe.qb.DocType("Process Statement of Accounts")
	q = frappe.qb.update(process_soa).set(process_soa.report, "General Ledger")
	q.run()
