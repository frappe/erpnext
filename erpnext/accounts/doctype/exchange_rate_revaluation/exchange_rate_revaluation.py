# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import nowdate
from frappe.model.document import Document
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.doctype.account.account import get_account_currency
from erpnext.accounts.doctype.journal_entry.journal_entry import get_average_exchange_rate,get_balance_on

class ExchangeRateRevaluation(Document):
	def get_accounts_data(self, account=None):
		child_table = []
		if self.company:
			if account:
				accounts = [account]
			else:	
				accounts = self.get_accounts()
			for i in accounts:
				balance = get_balance_on(i, in_account_currency=False)
				company_currency = erpnext.get_company_currency(self.company)
				account_currency = get_account_currency(i)
				new_exchange_rate = get_exchange_rate(account_currency, company_currency, self.posting_date)
				new_balance_in_base_currency = get_balance_on(i) * new_exchange_rate
				if balance:
					child_table.append({
							"account":i,
							"balance_in_base_currency": balance,
							"balance_in_alternate_currency": get_balance_on(i),
							"current_exchange_rate": get_average_exchange_rate(i),
							"new_exchange_rate": new_exchange_rate,
							"new_balance_in_base_currency": new_balance_in_base_currency,
							"difference": (new_balance_in_base_currency - balance)
						})
			return child_table
		else :
			return frappe.msgprint("Company is not selected")


	def get_accounts(self):
		company_currency = erpnext.get_company_currency(self.company)
		accounts = frappe.db.sql_list("""
			select name from tabAccount
			where is_group=0 and report_type='Balance Sheet' and root_type in ('Asset','Liability') and company=%s
			and not account_currency=%s order by name""",(self.company,company_currency))
		return accounts