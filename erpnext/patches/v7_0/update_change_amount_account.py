from __future__ import unicode_literals
import frappe
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

def execute():
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice')

	for company in frappe.db.sql("""select company from `tabSales Invoice` 
		where change_amount <> 0 and account_for_change_amount is null group by company""", as_list = 1):
		cash_account = get_default_bank_cash_account(company[0], 'Cash').get('account')
		if not cash_account:
			bank_account = get_default_bank_cash_account(company[0], 'Bank').get('account')
			cash_account = bank_account

		if cash_account:
			frappe.db.sql("""update `tabSales Invoice` 
				set account_for_change_amount = %(cash_account)s where change_amount <> 0 
				and company = %(company)s and account_for_change_amount is null""",
				{'cash_account': cash_account, 'company': company[0]})
