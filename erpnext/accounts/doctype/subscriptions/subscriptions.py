# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import now, nowdate, getdate, cint, add_days, date_diff, get_last_day, get_first_day
from frappe import _


SUBSCRIPTION_SETTINGS = frappe.get_single('Subscription Settings')


class Subscriptions(Document):
	def before_insert(self):
		# update start just before the subscription doc is created
		self.update_subscription_period()

	def update_subscription_period(self):
		self.set_current_invoice_start()
		self.set_current_invoice_end()

	def set_current_invoice_start(self, date=None):
		if not date:
			self.current_invoice_start = nowdate()

	def set_current_invoice_end(self):
		self.current_invoice_end = get_last_day(self.current_invoice_start)
