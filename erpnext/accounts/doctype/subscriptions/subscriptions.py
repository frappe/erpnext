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

	def before_save(self):
		self.set_status()

	def set_status(self):
		if self.is_trialling():
			self.status = 'Trialling'
		elif self.status == 'Past Due' and self.is_past_grace_period():
			self.status = 'Canceled' if cint(SUBSCRIPTION_SETTINGS.cancel_after_grace) else 'Unpaid'
		elif self.current_invoice_is_past_due():
			self.status = 'Past Due'
		elif self.is_new_subscription():
			self.status = 'Active'
			# todo: then generate new invoice

	def is_past_grace_period(self):
		current_invoice = self.get_current_invoice()
		if self.current_invoice_is_past_due(current_invoice):
			grace_period = cint(SUBSCRIPTION_SETTINGS.grace_period)

			return nowdate() > add_days(current_invoice.due_date, grace_period)

	def current_invoice_is_past_due(self, current_invoice=None):
		if not current_invoice:
			current_invoice = self.get_current_invoice()

		if not current_invoice:
			return False
		else:
			return nowdate() > current_invoice.due_date

	def is_new_subscription(self):
		return len(self.invoices) == 0

	def validate(self):
		self.validate_trial_period()

	def validate_trial_period(self):
		if self.trial_period_start and self.trial_period_end:
			if getdate(self.trial_period_end) > getdate(self.trial_period_start):
				frappe.throw(_('Trial Period End Date Cannot be before Trial Period Start Date'))

		elif self.trial_period_start or self.trial_period_end:
			frappe.throw(_('Both Trial Period Start Date and Trial Period End Date must be set'))

