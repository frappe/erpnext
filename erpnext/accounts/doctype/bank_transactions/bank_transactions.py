# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from os import truncate
from tkinter.messagebox import NO
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

			if self.created_by == None:
				self.created_by = frappe.session.user

		if self.docstatus == 1:
			self.docstatus = 3
			self.status = "Transit"
			self.calculate_diferred_account()

		if self.check and self.no_bank_check == None:
			self.no_bank_check = self.insert_numeration_for_check()

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

		if self.transaction_data == "Bank Check" or self.transaction_data== "Debit Note":
			doc.deferred_debits += self.amount_data
		else:
			doc.deferred_credits += self.amount_data
		
		doc.current_balance = doc.deferred_credits - doc.deferred_debits
		
		doc.save()

	def calculate_diferred_account_cancel(self):
		doc = frappe.get_doc("Bank Account", self.bank_account)

		if self.transaction_data == "Bank Check" or self.transaction_data== "Debit Note":
			doc.deferred_debits -= self.amount_data
		else:
			doc.deferred_credits -= self.amount_data
		
		doc.current_balance = doc.deferred_credits - doc.deferred_debits
		
		doc.save()
	
	def on_cancel(self):
		self.calculate_diferred_account_cancel()
	
	def insert_numeration_for_check(self):
		correlative = frappe.get_doc("Correlative Of Bank Checks", self.bank_account)

		if correlative == None:
			frappe.throw(_("This bank account does not have a check correlative assigned."))

		actual = correlative.current_numbering + 1

		actual_string = str(actual)

		actual_len = len(actual_string)

		cont = correlative.number_of_digits - actual_len

		actual_correlative = ""

		for number in range(cont):
			actual_correlative += "0"
		
		actual_correlative += actual_string

		correlative.current_numbering = actual
		correlative.save()

		return actual_correlative