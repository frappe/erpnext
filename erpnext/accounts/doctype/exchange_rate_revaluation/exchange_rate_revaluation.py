# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document
from erpnext.accounts.doctype.journal_entry.journal_entry import get_average_exchange_rate,get_balance_on
class ExchangeRateRevaluation(Document):
	def get_accounts_data(self):
		if self.company:
			accounts = self.get_accounts()
			self.exchange_rate_revaluation_account = []
			for i in accounts:
				self.append("exchange_rate_revaluation_account",{
					"account":i,
					"balance_in_base_currency":get_average_exchange_rate(i) * get_balance_on(i),
					"balance_in_alternate_currency":get_balance_on(i),
					"current_exchange_rate":get_average_exchange_rate(i),
					"difference":-(get_average_exchange_rate(i) * get_balance_on(i))
					})					
		else :
			frappe.msgprint("Company is not selected")


	def get_accounts(self):
		company_currency = erpnext.get_company_currency(self.company)
		accounts = frappe.db.sql_list("""
			select name from tabAccount 
			where is_group=0 and report_type='Balance Sheet' and company=%s
			and not account_currency=%s order by name""",(self.company,company_currency))
		return accounts