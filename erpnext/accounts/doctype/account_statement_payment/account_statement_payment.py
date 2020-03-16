# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime, timedelta, date

class AccountStatementPayment(Document):
		
	def on_update(self):
		self.sum_total()
		doc = frappe.get_doc("Patient statement", self.patient_statement)
		doc.cumulative_total = self.total
		doc.save()
	
	def sum_total(self):
		total_price = 0
		price = 0
		account_statement = frappe.get_all("Account Statement Payment Item", ["name", "price", "quantity", "net_pay"], filters = {"parent": self.name})

		for item in account_statement:
			frappe.msgprint("Account Statement: item {}".format(item))
			price = item.net_pay			
			total_price += price	
		
		self.total = total_price			

		frappe.msgprint("Account Statement: total price {} sel.total {}".format(total_price, self.total))
