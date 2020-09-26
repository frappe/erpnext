from __future__ import unicode_literals
import frappe
from six import iteritems

def execute():
	frappe.reload_doctype('Stock Entry Taxes and Charges')

	company_account_map = frappe._dict(frappe.db.sql("""
		SELECT name, expenses_included_in_valuation from `tabCompany`
	"""))

	for company, account in iteritems(company_account_map):
		frappe.db.sql("""
			UPDATE
				`tabStock Entry Taxes and Charges` t, `tabStock Entry` s
			SET
				t.expense_account = %s
			WHERE
				s.docstatus = 1
				AND s.company = %s
				AND t.parent = s.name
		""", (account, company))
