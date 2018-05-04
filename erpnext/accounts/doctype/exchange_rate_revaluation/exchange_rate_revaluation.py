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

	def make_jv_entry(self, accounts, total_gain_loss):
		exchange_gain_loss = frappe.get_doc("Company",self.company).unrealized_exchange_gain_loss_account
		if exchange_gain_loss:
			journal_entry = frappe.new_doc('Journal Entry')
			journal_entry.voucher_type = 'Exchange Rate Revaluation'
			journal_entry.company = self.company
			journal_entry.posting_date = nowdate()
			journal_entry.multi_currency = 1

			account_amt_list = []

			for acc in accounts:
				account_amt_list.append({
					"account": acc.get("account"),
					"balance":get_balance_on(acc.get("account")),
					"debit_in_account_currency": acc.get("balance_in_alternate_currency"),
					"exchange_rate":acc.get("new_exchange_rate"),
					"reference_type": "Exchange Rate Revaluation",
					"reference_name": self.name,
					})
				account_amt_list.append({
					"account": acc.get("account"),
					"balance":get_balance_on(acc.get("account")),
					"credit_in_account_currency": acc.get("balance_in_alternate_currency"),
					"exchange_rate":acc.get("current_exchange_rate"),
					"reference_type": "Exchange Rate Revaluation",
					"reference_name": self.name,
					})
			if total_gain_loss != 0:
				account_amt_list.append({
					"account": exchange_gain_loss,
					"balance":get_balance_on(exchange_gain_loss),
					"debit_in_account_currency": total_gain_loss if total_gain_loss < 0 else 0,
					"credit_in_account_currency": total_gain_loss if total_gain_loss > 0 else 0,
					"reference_type": "Exchange Rate Revaluation",
					"reference_name": self.name,
					})
			journal_entry.set("accounts", account_amt_list)
			return journal_entry.as_dict()
		else:
			frappe.msgprint("Set the Unrealized Exchange / Gain Loss Account field in Company DocType")