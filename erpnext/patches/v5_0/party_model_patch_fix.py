from __future__ import unicode_literals
import frappe

def execute():
	for organization in frappe.get_all("organization",
			["name", "default_receivable_account", "default_payable_account"]):

		if organization.default_receivable_account:
			frappe.db.sql("""update `tabSales Invoice` invoice set `debit_to`=%(account)s
				where organization=%(organization)s
				and not exists (select name from `tabAccount` account where account.name=invoice.debit_to)""",
				{"organization": organization.name, "account": organization.default_receivable_account})

		if organization.default_payable_account:
			frappe.db.sql("""update `tabPurchase Invoice` invoice set `credit_to`=%(account)s
				where organization=%(organization)s
				and not exists (select name from `tabAccount` account where account.name=invoice.credit_to)""",
				{"organization": organization.name, "account": organization.default_payable_account})
