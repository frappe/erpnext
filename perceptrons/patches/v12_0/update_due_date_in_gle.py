import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "gl_entry")

	for doctype in ["Sales Invoice", "Purchase Invoice", "Journal Entry"]:
		frappe.reload_doc("accounts", "doctype", frappe.scrub(doctype))

		frappe.db.sql(
			f""" UPDATE `tabGL Entry`, `tab{doctype}`
            SET
                `tabGL Entry`.due_date = `tab{doctype}`.due_date
            WHERE
                `tabGL Entry`.voucher_no = `tab{doctype}`.name and `tabGL Entry`.party is not null
                and `tabGL Entry`.voucher_type in ('Sales Invoice', 'Purchase Invoice', 'Journal Entry')
                and `tabGL Entry`.account in (select name from `tabAccount` where account_type in ('Receivable', 'Payable'))"""
		)
