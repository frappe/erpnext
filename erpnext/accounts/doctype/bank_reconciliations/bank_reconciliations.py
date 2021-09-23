# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class Bankreconciliations(Document):
	def validate(self):
		if self.docstatus == 1:
			self.verificate_defference_amount()
			self.conciliation_transactions()
			self.create_reconciled_balance()

	def on_update(self):
		self.update_amount()
	
	def update_amount(self):
		details = frappe.get_all("Bank reconciliations Detail", ["amount"], filters = {"parent": self.name})

		self.transaction_amount = 0
		for detail in details:
			self.transaction_amount += detail.amount
		
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
		doc = frappe.new_doc("Reconciled balances")
		doc.reconciled_date = self.date
		doc.reconciled_balance = self.transaction_amount
		doc.insert()
	
	def on_cancel(self):
		frappe.throw(_("Bank reconciliation cannot be canceled"))