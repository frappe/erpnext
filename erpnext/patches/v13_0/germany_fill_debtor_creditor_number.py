# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	"""Move account number into the new custom field debtor_creditor_number.

	German companies used to use a dedicated payable/receivable account for
	every party to mimick party accounts in the external accounting software
	"DATEV". This is no longer necessary. The reference ID for DATEV will be
	stored in a new custom field "debtor_creditor_number".
	"""
	company_list = frappe.get_all("Company", filters={"country": "Germany"})

	for company in company_list:
		party_account_list = frappe.get_all(
			"Party Account",
			filters={"company": company.name},
			fields=["name", "account", "debtor_creditor_number"],
		)
		for party_account in party_account_list:
			if (not party_account.account) or party_account.debtor_creditor_number:
				# account empty or debtor_creditor_number already filled
				continue

			account_number = frappe.db.get_value("Account", party_account.account, "account_number")
			if not account_number:
				continue

			frappe.db.set_value(
				"Party Account", party_account.name, "debtor_creditor_number", account_number
			)
			frappe.db.set_value("Party Account", party_account.name, "account", "")
