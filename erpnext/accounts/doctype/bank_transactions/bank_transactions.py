# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from os import truncate
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils.data import money_in_words

class BankTransactions(Document):
	def validate(self):
		if self.check:
			self.amount_of = money_in_words(self.amount)
			self.amount_data = self.amount
		
		if self.debit_note:
			self.amount_of_nd = money_in_words(self.amount_nd)
			self.amount_data = self.amount_nd
		
		if self.credit_note:
			self.amount_of_nc = money_in_words(self.amount_nc)
			self.amount_data = self.amount_nc
		
		if self.bank_deposit:
			self.amount_data = 0
			self.amount_data = self.amount_bd
		
		if self.docstatus == 0:
			self.set_transaction_data()

		if self.docstatus == 1:
			self.docstatus = 3
			self.status = "Transit"
			self.calculate_diferred_account()

	def verified_check(self, arg=None):		
		if self.debit_note:
			self.check = False
			frappe.throw(_("You have already marked the debit note option"))
		
		if self.credit_note:
			self.check = False
			frappe.throw(_("You have already marked the credit note option"))
		
		if self.bank_deposit:
			self.check = False
			frappe.throw(_("You have already marked the bank deposit option"))

	def verified_check2(self, arg=None):
		if self.check:
			self.debit_note = False
			frappe.throw(_("You have already marked the bank check option"))
		
		if self.credit_note:
			self.debit_note = False
			frappe.throw(_("You have already marked the credit note option"))
		
		if self.bank_deposit:
			self.debit_note = False
			frappe.throw(_("You have already marked the bank deposit option"))
	
	def verified_check3(self, arg=None):
		if self.check:
			self.credit_note = False
			frappe.throw(_("You have already marked the bank check option"))
		
		if self.debit_note:
			self.credit_note = False
			frappe.throw(_("You have already marked the debit note option"))
		
		if self.bank_deposit:
			self.credit_note = False
			frappe.throw(_("You have already marked the bank deposit option"))
	
	def verified_check4(self, arg=None):
		if self.check:
			self.bank_deposit = False
			frappe.throw(_("You have already marked the bank check option"))
		
		if self.debit_note:
			self.bank_deposit = False
			frappe.throw(_("You have already marked the debit note option"))
		
		if self.credit_note:
			self.bank_deposit = False
			frappe.throw(_("You have already marked the credit note option"))
	
	def prereconciled(self):
		self.set_transaction_data()
		self.db_set('docstatus', 4, update_modified=False)
		self.db_set('status', "Pre-reconciled", update_modified=False)
		self.reload()
	
	def set_transaction_data(self):
		if self.check:
			self.db_set('transaction_data', "Bank Check", update_modified=False)
			self.db_set('date_data', self.check_date, update_modified=False)
		
		if self.debit_note:
			self.db_set('transaction_data', "Debit Note", update_modified=False)
			self.db_set('date_data', self.check_date_nd, update_modified=False)
		
		if self.credit_note:
			self.db_set('transaction_data', "Credit Note", update_modified=False)
			self.db_set('date_data', self.check_date_nc, update_modified=False)
		
		if self.bank_deposit:
			self.db_set('transaction_data', "Bank deposit", update_modified=False)
			self.db_set('date_data', self.deposit_date, update_modified=False)
	
	def calculate_diferred_account(self):
		doc = frappe.get_doc("Bank Account", self.bank_account)

		if self.transaction_data == "Bank Check" or self.transaction_data== "Credit Note":
			doc.deferred_credits += self.amount_data
		else:
			doc.deferred_debits += self.amount_data
		
		doc.save()