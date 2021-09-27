# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class BankTransactionAccountingEntry(Document):
	def validate(self):
		if self.docstatus == 1:
			self.check_transaction()
			self.calculate_totals()
			self.verificate_totals()
	
	def on_cancel(self):
		self.uncheck_transaction()
	
	def on_trash(self):
		self.uncheck_transaction()

	def on_update(self):
		detailamount = frappe.get_all("Bank Transactions Detail", ["name"], filters = {"parent": self.name})
		if len(detailamount) == 0:
			self.create_register()
		
		if self.docstatus == 0:
			self.calculate_totals()
	
	def create_register(self):
		transaction = frappe.get_all("Bank Transactions", ["name","bank_account", "transaction_data", "amount_data"], filters = {"name": self.bank_transaction})

		account = frappe.get_all("Bank Account", ["account"], filters = {"name": transaction[0].bank_account})

		# doc = frappe.get_doc("Bank Transaction Accounting Entry")
		row = self.append("detail", {})
		row.account = account[0].account

		if transaction[0].transaction_data == "Bank Check" or transaction[0].transaction_data == "Credit Note":
			row.credit = transaction[0].amount_data
			row.debit = 0
		else:
			row.debit = transaction[0].amount_data
			row.credit = 0
		self.save()
		# doc.save()
	
	def check_transaction(self):
		transaction = frappe.get_all("Bank Transactions", ["name"], filters = {"name": self.bank_transaction})
		doc_tran = frappe.get_doc("Bank Transactions", transaction[0].name)
		doc_tran.accounting_seat = 1
		doc_tran.save()
	
	def uncheck_transaction(self):
		transaction = frappe.get_all("Bank Transactions", ["name"], filters = {"name": self.bank_transaction})
		doc_tran = frappe.get_doc("Bank Transactions", transaction[0].name)
		doc_tran.accounting_seat = 0
		doc_tran.save()
	
	def calculate_totals(self):
		detailamount = frappe.get_all("Bank Transactions Detail", ["debit", "credit"], filters = {"parent": self.name})

		total_debit = 0
		total_credit = 0

		for detail in detailamount:
			total_debit += detail.debit
			total_credit += detail.credit
		
		self.db_set('total_debit', total_debit, update_modified=False)
		self.db_set('total_credit', total_credit, update_modified=False)
	
	def verificate_totals(self):
		difference_totals = self.total_debit - self.total_credit

		if difference_totals != 0:
			frappe.throw(_("Difference amount must be 0"))