# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import now, nowdate, getdate, cint, add_days, date_diff, get_last_day, get_first_day, add_to_date
from frappe import _


SUBSCRIPTION_SETTINGS = frappe.get_single('Subscription Settings')


class Subscriptions(Document):
	def before_save(self):
		self.set_status()

	def before_insert(self):
		# update start just before the subscription doc is created
		self.update_subscription_period()

	def update_subscription_period(self):
		self.set_current_invoice_start()
		self.set_current_invoice_end()

	def set_current_invoice_start(self, date=None):
		if self.trial_period_start and self.is_trialling():
			self.current_invoice_start = self.trial_period_start
		elif not date:
			self.current_invoice_start = nowdate()

	def set_current_invoice_end(self):
		if self.is_trialling():
			self.current_invoice_end = self.trial_period_end
		else:
			billing_cycle_info = self.get_billing_cycle()
			if billing_cycle_info:
				self.current_invoice_end = add_to_date(self.current_invoice_start, **billing_cycle_info)
			else:
				self.current_invoice_end = get_last_day(self.current_invoice_start)

	def get_billing_cycle(self):
		return self.get_billing_cycle_data()

	def validate_plans_billing_cycle(self, billing_cycle_data):
		if billing_cycle_data and len(billing_cycle_data) != 1:
			frappe.throw(_('You can only have Plans with the same billing cycle in a Subscription'))

	def get_billing_cycle_and_interval(self):
		plan_names = [plan.plan for plan in self.plans]
		billing_info = frappe.db.sql(
			'select distinct `billing_interval`, `billing_interval_count` '
			'from `tabSubscription Plan` '
			'where name in %s',
			(plan_names,), as_dict=1
		)

		return billing_info

	def get_billing_cycle_data(self):
		billing_info = self.get_billing_cycle_and_interval()

		self.validate_plans_billing_cycle(billing_info)

		if billing_info:
			data = dict()
			interval = billing_info[0]['billing_interval']
			interval_count = billing_info[0]['billing_interval_count']
			if interval not in ['Day', 'Week']:
				data['days'] = -1
			if interval == 'Day':
				data['days'] = interval_count - 1
			elif interval == 'Month':
				data['months'] = interval_count
			elif interval == 'Year':
				data['years'] == interval_count
			# todo: test week
			elif interval == 'Week':
				data['days'] = interval_count * 7 - 1

			return data

	def set_status(self):
		if self.is_trialling():
			self.status = 'Trialling'
		elif self.status == 'Past Due' and self.is_past_grace_period():
			self.status = 'Canceled' if cint(SUBSCRIPTION_SETTINGS.cancel_after_grace) else 'Unpaid'
		elif self.status == 'Past Due' and not self.has_outstanding_invoice():
			self.status = 'Active'
		elif self.current_invoice_is_past_due():
			self.status = 'Past Due'
		elif self.is_new_subscription():
			self.status = 'Active'
			# todo: then generate new invoice

	def is_trialling(self):
		return not self.period_has_passed(self.trial_period_end) and self.is_new_subscription()

	def period_has_passed(self, end_date):
		# todo: test for illegal time
		if not end_date:
			return True

		end_date = getdate(end_date)
		return getdate(nowdate()) > getdate(end_date)

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
			return getdate(nowdate()) > getdate(current_invoice.due_date)

	def get_current_invoice(self):
		if len(self.invoices):
			current = self.invoices[-1]
			doc = frappe.get_doc('Sales Invoice', current.invoice)
			return doc

	def is_new_subscription(self):
		return len(self.invoices) == 0

	def validate(self):
		self.validate_trial_period()
		self.validate_plans_billing_cycle(self.get_billing_cycle_and_interval())

	def validate_trial_period(self):
		if self.trial_period_start and self.trial_period_end:
			if getdate(self.trial_period_end) < getdate(self.trial_period_start):
				frappe.throw(_('Trial Period End Date Cannot be before Trial Period Start Date'))

		elif self.trial_period_start or self.trial_period_end:
			frappe.throw(_('Both Trial Period Start Date and Trial Period End Date must be set'))

	def after_insert(self):
		# todo: deal with users who collect prepayments. Maybe a new Subscription Invoice doctype?
		pass

	def generate_invoice(self):
		invoice = self.create_invoice()
		self.append('invoices', {'invoice': invoice.name})
		self.save()	# Validates all over again but we don't mind
		self.subscription_updated(invoice)

		return invoice

	def create_invoice(self):
		invoice = frappe.new_doc('Sales Invoice')
		invoice.customer = self.get_customer(self.subscriber)

		# Subscription is better suited for service items. I won't update `update_stock`
		# for that reason
		items_list = self.get_items_from_plans(self.plans)
		for item in items_list:
			item['qty'] = self.quantity
			invoice.append('items',	item)

		# Taxes
		# todo: tax template does not populate tax table
		if self.tax_template:
			invoice.taxes_and_charges = self.tax_template

		# Due date
		invoice.append(
			'payment_schedule', 
			{
				'due_date': add_days(self.current_invoice_end, cint(self.days_until_due)),
				'invoice_portion': 100
			}
		)

		# Discounts
		if self.apply_additional_discount:
			invoice.apply_discount_on = self.apply_additional_discount

		if self.additional_discount_percentage:
			invoice.additional_discount_percentage = self.additional_discount_percentage

		if self.additional_discount_amount:
			invoice.additional_discount_amount = self.additional_discount_amount

		invoice.save()
		invoice.submit()

		return invoice

	def get_customer(self, subscriber_name):
		return frappe.get_value('Subscriber', subscriber_name)

	def get_items_from_plans(self, plans):
		plan_items = [plan.plan for plan in plans]

		if plan_items:
			item_names = frappe.db.sql(
				'select item as item_code, cost as rate from `tabSubscription Plan` where name in %s',
				(plan_items,), as_dict=1
			)
			return item_names

	def subscription_updated(self, invoice):
		self.update_subscription_period()

	def process(self):
		"""
		To be called by task periodically. It checks the subscription and takes appropriate action
		as need be. It calls these methods in this order:
		1. `process_for_active`
		2. `process_for_past_due`
		3. 
		"""
		if self.status == 'Active':
			self.process_for_active()
		elif self.status == 'Past Due':
			self.process_for_past_due_date()
		# process_for_unpaid()

	def process_for_active(self):
		print 'processing for active'
		if nowdate() > self.current_invoice_end and not self.has_outstanding_invoice():
			print 'generating invoice'
			self.generate_invoice()
			print 'invoice generated'

		if self.current_invoice_is_past_due():
			print 'current invoice is past due'
			self.status = 'Past Due'

	def process_for_past_due_date(self):
		if not self.has_outstanding_invoice():
			self.status = 'Active'
			self.update_subscription_period()
		else:
			self.set_status()

	def has_outstanding_invoice(self):
		current_invoice = self.get_current_invoice()
		return current_invoice.posting_date != self.current_invoice_start
