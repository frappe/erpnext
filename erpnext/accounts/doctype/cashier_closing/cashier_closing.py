# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, cstr
from frappe import _, msgprint, throw

class CashierClosing(Document):
	def validate(self):
		self.validate_time()

	def before_save(self):
		self.calculate_cash()
		self.get_outstanding()
		self.make_calculations()
	
	def calculate_cash(self):
		entry = frappe.db.sql("""
			select sum(amount)
			from `tabCash Entry`
			where date=%s and hour>=%s and hour<=%s and user=%s and docstatus=1
		""", (self.date, self.from_time, self.time, self.user))

		self.cash_entry_amount = flt(entry[0][0] if entry else 0)

		withdrawal = frappe.db.sql("""
			select sum(amount)
			from `tabCash Withdrawal`
			where date=%s and hour>=%s and hour<=%s and user=%s and docstatus=1
		""", (self.date, self.from_time, self.time, self.user))

		self.cash_withdrawal_amount = flt(withdrawal[0][0] if withdrawal else 0)

	def get_outstanding(self):
		values = frappe.db.sql("""
			select sum(outstanding_amount)
			from `tabSales Invoice`
			where posting_date=%s and posting_time>=%s and posting_time<=%s and owner=%s
		""", (self.date, self.from_time, self.time, self.user))
		self.outstanding_amount = flt(values[0][0] if values else 0)
			
	def make_calculations(self):
		total = 0.00
		for i in self.payments:
			total += flt(i.amount)

		self.net_amount = total + self.outstanding_amount + self.expense - self.custody + self.returns + self.cash_entry_amount - self.cash_withdrawal_amount

	def validate_time(self):
		if self.from_time >= self.time:
			frappe.throw(_("From Time Should Be Less Than To Time"))