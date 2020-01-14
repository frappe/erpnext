# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	# Reload doctype
	for dt in ("Account", "GL Entry", "Journal Entry",
		"Journal Entry Account", "Sales Invoice", "Purchase Invoice", "Customer", "Supplier"):
			frappe.reload_doctype(dt)

	company_list = frappe.get_all("Company", fields=["name", "default_currency", "default_receivable_account"])
	for company in company_list:

		# update currency in account and gl entry as per company currency
		frappe.db.sql("""update `tabAccount` set account_currency = %s
			where ifnull(account_currency, '') = '' and company=%s""", (company.default_currency, company.name))

		# update newly introduced field's value in sales / purchase invoice
		frappe.db.sql("""
			update
				`tabSales Invoice`
			set
				base_paid_amount=paid_amount,
				base_write_off_amount=write_off_amount,
				party_account_currency=%s
			where company=%s
		""", (company.default_currency, company.name))

		frappe.db.sql("""
			update
				`tabPurchase Invoice`
			set
				base_write_off_amount=write_off_amount,
				party_account_currency=%s
			where company=%s
		""", (company.default_currency, company.name))

		# update exchange rate, debit/credit in account currency in Journal Entry
		frappe.db.sql("""
			update `tabJournal Entry Account` jea
			set exchange_rate=1,
				debit_in_account_currency=debit,
				credit_in_account_currency=credit,
				account_type=(select account_type from `tabAccount` where name=jea.account)
		""")

		frappe.db.sql("""
			update `tabJournal Entry Account` jea, `tabJournal Entry` je
			set account_currency=%s
			where jea.parent = je.name and je.company=%s
		""", (company.default_currency, company.name))

		# update debit/credit in account currency in GL Entry
		frappe.db.sql("""
			update
				`tabGL Entry`
			set
				debit_in_account_currency=debit,
				credit_in_account_currency=credit,
				account_currency=%s
			where
				company=%s
		""", (company.default_currency, company.name))
