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

	# Set party account if default currency of party other than company's default currency
	for dt in ("Customer", "Supplier"):
		parties = frappe.get_all(dt, filters={"docstatus": 0})
		for p in parties:
			party = frappe.get_doc(dt, p.name)
			party_accounts = []

			for company in company_list:
				# Get party GL Entries
				party_gle = frappe.db.get_value("GL Entry", {"party_type": dt, "party": p.name,
					"company": company.name}, ["account", "account_currency", "name"], as_dict=True)

				# set party account currency
				if party_gle:
					party.party_account_currency = party_gle.account_currency
				elif not party.party_account_currency:
					party.party_account_currency = company.default_currency

				# Add default receivable /payable account if not exists
				# and currency is other than company currency
				if party.party_account_currency and party.party_account_currency != company.default_currency:
					party_account_exists_for_company = False
					for d in party.get("accounts"):
						if d.company == company.name:
							account_currency = frappe.db.get_value("Account", d.account, "account_currency")
							if account_currency == party.party_account_currency:
								party_accounts.append({
									"company": d.company,
									"account": d.account
								})
								party_account_exists_for_company = True
								break

					if not party_account_exists_for_company:
						party_account = None
						if party_gle:
							party_account = party_gle.account
						else:
							default_receivable_account_currency = frappe.db.get_value("Account",
								company.default_receivable_account, "account_currency")
							if default_receivable_account_currency != company.default_currency:
								party_account = company.default_receivable_account

						if party_account:
							party_accounts.append({
								"company": company.name,
								"account": party_account
							})

			party.set("accounts", party_accounts)
			party.flags.ignore_mandatory = True
			party.save()
