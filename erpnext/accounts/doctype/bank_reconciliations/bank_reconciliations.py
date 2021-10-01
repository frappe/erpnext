# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class Bankreconciliations(Document):
	def validate(self):
		if self.docstatus == 0:
			self.verificate_bank_account()

		if self.docstatus == 1:
			self.verificate_defference_amount()
			self.conciliation_transactions()
			self.create_reconciled_balance()
			self.modified_total_reconcilitiation_account()

	def on_update(self):
		self.update_amount()
	
	def update_amount(self):
		details = frappe.get_all("Bank reconciliations Detail", ["amount"], filters = {"parent": self.name})

		self.transaction_amount = 0
		for detail in details:
			self.transaction_amount += detail.amount
		if self.bank_amount == None:
			self.bank_amount = 0
			
		self.defference_amount = self.transaction_amount - self.bank_amount

	def verificate_defference_amount(self):
		if self.defference_amount != 0:
			frappe.throw(_("Difference amount must be 0"))
	
	def conciliation_transactions(self):
		details = frappe.get_all("Bank reconciliations Detail", ["bank_trasaction"], filters = {"parent": self.name})

		for detail in details:
			doc = frappe.get_doc("Bank Transactions", detail.bank_trasaction)
			doc.docstatus = 5
			doc.status = "Reconciled"
			doc.save()
	
	def create_reconciled_balance(self):
		details = frappe.get_all("Bank reconciliations Detail", ["bank_trasaction", "amount"], filters = {"parent": self.name})

		transaction = frappe.get_all("Bank Transactions", ["bank_account", "transaction_data"], filters = {"name": details[0].bank_trasaction})

		doc = frappe.new_doc("Reconciled balances")
		doc.reconciled_date = self.date
		doc.reconciled_balance = self.transaction_amount
		doc.docstatus = 1
		doc.bank_account = transaction[0].bank_account
		doc.insert()
	
	def on_cancel(self):
		frappe.throw(_("Bank reconciliation cannot be canceled"))
	
	def modified_total_reconcilitiation_account(self):
		details = frappe.get_all("Bank reconciliations Detail", ["bank_trasaction", "amount"], filters = {"parent": self.name})

		transaction = frappe.get_all("Bank Transactions", ["bank_account", "transaction_data"], filters = {"name": details[0].bank_trasaction})

		doc = frappe.get_doc("Bank Account", transaction[0].bank_account)
		doc.reconciliation_date = self.date
		doc.total_reconciliation = self.transaction_amount

		for detail in details:
			transac = frappe.get_all("Bank Transactions", ["bank_account", "transaction_data"], filters = {"name": detail.bank_trasaction})
			if transac[0].transaction_data == "Bank Check" or transac[0].transaction_data== "Credit Note":
				doc.deferred_debits -= self.amount_data
			else:
				doc.deferred_credits -= self.amount_data
		
		doc.current_balance = doc.deferred_credits - doc.deferred_debits

		doc.save()
	
	def verificate_bank_account(self):
		details = frappe.get_all("Bank reconciliations Detail", ["bank_trasaction", "amount"], filters = {"parent": self.name})

		for detail in details:
			transaction = frappe.get_all("Bank Transactions", ["bank_account", "transaction_data"], filters = {"name": detail.bank_trasaction})

			if transaction[0].bank_account != self.bank_account:
				frappe.throw(_("Bank transaction {} has a different bank account {} than the one selected".format(detail.bank_trasaction, transaction[0].bank_account)))
