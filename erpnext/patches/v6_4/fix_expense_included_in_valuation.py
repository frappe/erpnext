# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr

def execute():
	for company in frappe.db.sql("select name, expenses_included_in_valuation from tabCompany", as_dict=1):
		frozen_date = get_frozen_date(company.name, company.expenses_included_in_valuation)

		# Purchase Invoices after frozen date
		# which are not against Receipt, but valuation related tax is there
		pi_list = frappe.db.sql("""
			select distinct pi.name
			from `tabPurchase Invoice` pi, `tabPurchase Invoice Item` pi_item
			where
				pi.name = pi_item.parent
				and pi.company = %s
				and pi.posting_date > %s
				and pi.docstatus = 1
				and pi.is_opening = 'No'
				and (pi_item.item_tax_amount is not null and pi_item.item_tax_amount > 0)
				and (pi_item.purchase_receipt is null or pi_item.purchase_receipt = '')
				and (pi_item.item_code is not null and pi_item.item_code != '')
				and exists(select name from `tabItem` where name=pi_item.item_code and is_stock_item=1)
		""", (company.name, frozen_date), as_dict=1)

		for pi in pi_list:
			# Check whether gle exists for Expenses Included in Valuation account against the PI
			gle_for_expenses_included_in_valuation = frappe.db.sql("""select name from `tabGL Entry`
				where voucher_type='Purchase Invoice' and voucher_no=%s and account=%s""",
				(pi.name, company.expenses_included_in_valuation))

			if gle_for_expenses_included_in_valuation:
				print pi.name

				frappe.db.sql("""delete from `tabGL Entry`
					where voucher_type='Purchase Invoice' and voucher_no=%s""", pi.name)

				purchase_invoice = frappe.get_doc("Purchase Invoice", pi.name)

				# some old entries have missing expense accounts
				if purchase_invoice.against_expense_account:
					expense_account = purchase_invoice.against_expense_account.split(",")
					if len(expense_account) == 1:
						expense_account = expense_account[0]
						for item in purchase_invoice.items:
							if not item.expense_account:
								item.db_set("expense_account", expense_account, update_modified=False)

				purchase_invoice.make_gl_entries()

def get_frozen_date(company, account):
	# Accounting frozen upto
	accounts_frozen_upto = frappe.db.get_single_value("Accounts Settings", "acc_frozen_upto")

	# Last adjustment entry to correct Expenses Included in Valuation account balance
	last_adjustment_entry = frappe.db.sql("""select posting_date from `tabGL Entry`
		where account=%s and company=%s and voucher_type = 'Journal Entry'
		order by posting_date desc limit 1""", (account, company))

	last_adjustment_date = cstr(last_adjustment_entry[0][0]) if last_adjustment_entry else None

	# Last period closing voucher
	last_closing_entry = frappe.db.sql("""select posting_date from `tabGL Entry`
		where company=%s and voucher_type = 'Period Closing Voucher'
		order by posting_date desc limit 1""", company)

	last_closing_date = cstr(last_closing_entry[0][0]) if last_closing_entry else None

	frozen_date = max([accounts_frozen_upto, last_adjustment_date, last_closing_date])

	return frozen_date or '1900-01-01'
