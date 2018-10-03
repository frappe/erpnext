# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import nowdate, getdate, cint, add_days, date_diff, get_last_day, add_to_date, flt
from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate


class Subscription(Document):
	def before_insert(self):
		# update start just before the subscription doc is created
		self.update_subscription_period(self.start)

	def update_subscription_period(self, date=None):
		"""
		Subscription period is the period to be billed. This method updates the
		beginning of the billing period and end of the billing period.

		The beginning of the billing period is represented in the doctype as
		`current_invoice_start` and the end of the billing period is represented
		as `current_invoice_end`.
		"""
		self.set_current_invoice_start(date)
		self.set_current_invoice_end()

	def set_current_invoice_start(self, date=None):
		"""
		This sets the date of the beginning of the current billing period.
		If the `date` parameter is not given , it will be automatically set as today's
		date.
		"""
		if self.trial_period_start and self.is_trialling():
			self.current_invoice_start = self.trial_period_start
		elif date:
			self.current_invoice_start = date
		else:
			self.current_invoice_start = nowdate()

	def set_current_invoice_end(self):
		"""
		This sets the date of the end of the current billing period.

		If the subscription is in trial period, it will be set as the end of the
		trial period.

		If is not in a trial period, it will be `x` days from the beginning of the
		current billing period where `x` is the billing interval from the
		`Subscription Plan` in the `Subscription`.
		"""
		if self.is_trialling():
			self.current_invoice_end = self.trial_period_end
		else:
			billing_cycle_info = self.get_billing_cycle_data()
			if billing_cycle_info:
				self.current_invoice_end = add_to_date(self.current_invoice_start, **billing_cycle_info)
			else:
				self.current_invoice_end = get_last_day(self.current_invoice_start)

	@staticmethod
	def validate_plans_billing_cycle(billing_cycle_data):
		"""
		Makes sure that all `Subscription Plan` in the `Subscription` have the
		same billing interval
		"""
		if billing_cycle_data and len(billing_cycle_data) != 1:
			frappe.throw(_('You can only have Plans with the same billing cycle in a Subscription'))

	def get_billing_cycle_and_interval(self):
		"""
		Returns a dict representing the billing interval and cycle for this `Subscription`.

		You shouldn't need to call this directly. Use `get_billing_cycle` instead.
		"""
		plan_names = [plan.plan for plan in self.plans]
		billing_info = frappe.db.sql(
			'select distinct `billing_interval`, `billing_interval_count` '
			'from `tabSubscription Plan` '
			'where name in %s',
			(plan_names,), as_dict=1
		)

		return billing_info

	def get_billing_cycle_data(self):
		"""
		Returns dict contain the billing cycle data.

		You shouldn't need to call this directly. Use `get_billing_cycle` instead.
		"""
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
				data['years'] = interval_count
			# todo: test week
			elif interval == 'Week':
				data['days'] = interval_count * 7 - 1

			return data

	def set_status_grace_period(self):
		"""
		Sets the `Subscription` `status` based on the preference set in `Subscription Settings`.

		Used when the `Subscription` needs to decide what to do after the current generated
		invoice is past it's due date and grace period.
		"""
		subscription_settings = frappe.get_single('Subscription Settings')
		if self.status == 'Past Due Date' and self.is_past_grace_period():
			self.status = 'Cancelled' if cint(subscription_settings.cancel_after_grace) else 'Unpaid'

	def set_subscription_status(self):
		"""
		Sets the status of the `Subscription`
		"""
		if self.is_trialling():
			self.status = 'Trialling'
		elif self.status == 'Past Due Date' and self.is_past_grace_period():
			subscription_settings = frappe.get_single('Subscription Settings')
			self.status = 'Cancelled' if cint(subscription_settings.cancel_after_grace) else 'Unpaid'
		elif self.status == 'Past Due Date' and not self.has_outstanding_invoice():
			self.status = 'Active'
		elif self.current_invoice_is_past_due():
			self.status = 'Past Due Date'
		elif self.is_new_subscription():
			self.status = 'Active'
			# todo: then generate new invoice
		self.save()

	def is_trialling(self):
		"""
		Returns `True` if the `Subscription` is trial period.
		"""
		return not self.period_has_passed(self.trial_period_end) and self.is_new_subscription()

	@staticmethod
	def period_has_passed(end_date):
		"""
		Returns true if the given `end_date` has passed
		"""
		# todo: test for illegal time
		if not end_date:
			return True

		end_date = getdate(end_date)
		return getdate(nowdate()) > getdate(end_date)

	def is_past_grace_period(self):
		"""
		Returns `True` if the grace period for the `Subscription` has passed
		"""
		current_invoice = self.get_current_invoice()
		if self.current_invoice_is_past_due(current_invoice):
			subscription_settings = frappe.get_single('Subscription Settings')
			grace_period = cint(subscription_settings.grace_period)

			return getdate(nowdate()) > add_days(current_invoice.due_date, grace_period)

	def current_invoice_is_past_due(self, current_invoice=None):
		"""
		Returns `True` if the current generated invoice is overdue
		"""
		if not current_invoice:
			current_invoice = self.get_current_invoice()

		if not current_invoice:
			return False
		else:
			return getdate(nowdate()) > getdate(current_invoice.due_date)

	def get_current_invoice(self):
		"""
		Returns the most recent generated invoice.
		"""
		if len(self.invoices):
			current = self.invoices[-1]
			if frappe.db.exists('Sales Invoice', current.invoice):
				doc = frappe.get_doc('Sales Invoice', current.invoice)
				return doc
			else:
				frappe.throw(_('Invoice {0} no longer exists'.format(current.invoice)))

	def is_new_subscription(self):
		"""
		Returns `True` if `Subscription` has never generated an invoice
		"""
		return len(self.invoices) == 0

	def validate(self):
		self.validate_trial_period()
		self.validate_plans_billing_cycle(self.get_billing_cycle_and_interval())

	def validate_trial_period(self):
		"""
		Runs sanity checks on trial period dates for the `Subscription`
		"""
		if self.trial_period_start and self.trial_period_end:
			if getdate(self.trial_period_end) < getdate(self.trial_period_start):
				frappe.throw(_('Trial Period End Date Cannot be before Trial Period Start Date'))

		elif self.trial_period_start or self.trial_period_end:
			frappe.throw(_('Both Trial Period Start Date and Trial Period End Date must be set'))

	def after_insert(self):
		# todo: deal with users who collect prepayments. Maybe a new Subscription Invoice doctype?
		self.set_subscription_status()

	def generate_invoice(self, prorate=0):
		"""
		Creates a `Sales Invoice` for the `Subscription`, updates `self.invoices` and
		saves the `Subscription`.
		"""
		invoice = self.create_invoice(prorate)
		self.append('invoices', {'invoice': invoice.name})
		self.save()

		return invoice

	def create_invoice(self, prorate):
		"""
		Creates a `Sales Invoice`, submits it and returns it
		"""
		invoice = frappe.new_doc('Sales Invoice')
		invoice.set_posting_time = 1
		invoice.posting_date = self.current_invoice_start
		invoice.customer = self.get_customer(self.subscriber)

		# Subscription is better suited for service items. I won't update `update_stock`
		# for that reason
		items_list = self.get_items_from_plans(self.plans, prorate)
		for item in items_list:
			invoice.append('items',	item)

		# Taxes
		if self.tax_template:
			invoice.taxes_and_charges = self.tax_template
			invoice.set_taxes()

		# Due date
		invoice.append(
			'payment_schedule',
			{
				'due_date': add_days(self.current_invoice_end, cint(self.days_until_due)),
				'invoice_portion': 100
			}
		)

		# Discounts
		if self.additional_discount_percentage:
			invoice.additional_discount_percentage = self.additional_discount_percentage

		if self.additional_discount_amount:
			invoice.discount_amount = self.additional_discount_amount

		if self.additional_discount_percentage or self.additional_discount_amount:
			discount_on = self.apply_additional_discount
			invoice.apply_additional_discount = discount_on if discount_on else 'Grand Total'

		# Subscription period
		invoice.from_date = self.current_invoice_start
		invoice.to_date = self.current_invoice_end

		invoice.flags.ignore_mandatory = True
		invoice.save()
		invoice.submit()

		return invoice

	@staticmethod
	def get_customer(subscriber_name):
		"""
		Returns the `Customer` linked to the `Subscriber`
		"""
		return frappe.db.get_value('Subscriber', subscriber_name, 'customer')

	def get_items_from_plans(self, plans, prorate=0):
		"""
		Returns the `Item`s linked to `Subscription Plan`
		"""
		if prorate:
			prorate_factor = get_prorata_factor(self.current_invoice_end, self.current_invoice_start)

		items = []
		customer = self.get_customer(self.subscriber)
		for plan in plans:
			item_code = frappe.db.get_value("Subscription Plan", plan.plan, "item")
			if not prorate:
				items.append({'item_code': item_code, 'qty': plan.qty, 'rate': get_plan_rate(plan.plan, plan.qty, customer)})
			else:
				items.append({'item_code': item_code, 'qty': plan.qty, 'rate': (get_plan_rate(plan.plan, plan.qty, customer) * prorate_factor)})

		return items

	def process(self):
		"""
		To be called by task periodically. It checks the subscription and takes appropriate action
		as need be. It calls either of these methods depending the `Subscription` status:
		1. `process_for_active`
		2. `process_for_past_due`
		"""
		if self.status == 'Active':
			self.process_for_active()
		elif self.status in ['Past Due Date', 'Unpaid']:
			self.process_for_past_due_date()

		self.save()

	@property
	def is_postpaid_to_invoice(self):
		return getdate(nowdate()) > getdate(self.current_invoice_end) or \
			(getdate(nowdate()) >= getdate(self.current_invoice_end) and getdate(self.current_invoice_end) == getdate(self.current_invoice_start)) and \
			not self.has_outstanding_invoice()

	@property
	def is_prepaid_to_invoice(self):
		if not self.generate_invoice_at_period_start:
			return False

		if self.is_new_subscription():
			return True

		# Check invoice dates and make sure it doesn't have outstanding invoices
		return getdate(nowdate()) >= getdate(self.current_invoice_start) and not self.has_outstanding_invoice()

	def process_for_active(self):
		"""
		Called by `process` if the status of the `Subscription` is 'Active'.

		The possible outcomes of this method are:
		1. Generate a new invoice
		2. Change the `Subscription` status to 'Past Due Date'
		3. Change the `Subscription` status to 'Cancelled'
		"""
		if self.is_postpaid_to_invoice or self.is_prepaid_to_invoice:
			self.generate_invoice()
			if self.current_invoice_is_past_due():
				self.status = 'Past Due Date'

		if self.current_invoice_is_past_due() and getdate(nowdate()) > getdate(self.current_invoice_end):
			self.status = 'Past Due Date'

		if self.cancel_at_period_end and getdate(nowdate()) > getdate(self.current_invoice_end):
			self.cancel_subscription_at_period_end()

	def cancel_subscription_at_period_end(self):
		"""
		Called when `Subscription.cancel_at_period_end` is truthy
		"""
		self.status = 'Cancelled'
		if not self.cancelation_date:
			self.cancelation_date = nowdate()

	def process_for_past_due_date(self):
		"""
		Called by `process` if the status of the `Subscription` is 'Past Due Date'.

		The possible outcomes of this method are:
		1. Change the `Subscription` status to 'Active'
		2. Change the `Subscription` status to 'Cancelled'
		3. Change the `Subscription` status to 'Unpaid'
		"""
		current_invoice = self.get_current_invoice()
		if not current_invoice:
			frappe.throw(_('Current invoice {0} is missing'.format(current_invoice.invoice)))
		else:
			if self.is_not_outstanding(current_invoice):
				self.status = 'Active'
				self.update_subscription_period(add_days(self.current_invoice_end, 1))
			else:
				self.set_status_grace_period()

	@staticmethod
	def is_not_outstanding(invoice):
		"""
		Return `True` if the given invoice is paid
		"""
		return invoice.status == 'Paid'

	def has_outstanding_invoice(self):
		"""
		Returns `True` if the most recent invoice for the `Subscription` is not paid
		"""
		current_invoice = self.get_current_invoice()
		if not current_invoice:
			return False
		else:
			return not self.is_not_outstanding(current_invoice)

	def cancel_subscription(self):
		"""
		This sets the subscription as cancelled. It will stop invoices from being generated
		but it will not affect already created invoices.
		"""
		if self.status != 'Cancelled':
			to_generate_invoice = True if self.status == 'Active' else False
			to_prorate = frappe.db.get_single_value('Subscription Settings', 'prorate')
			self.status = 'Cancelled'
			self.cancelation_date = nowdate()
			if to_generate_invoice:
				self.generate_invoice(prorate=to_prorate)
			self.save()

	def restart_subscription(self):
		"""
		This sets the subscription as active. The subscription will be made to be like a new
		subscription and the `Subscription` will lose all the history of generated invoices
		it has.
		"""
		if self.status == 'Cancelled':
			self.status = 'Active'
			self.db_set('start', nowdate())
			self.update_subscription_period(nowdate())
			self.invoices = []
			self.save()
		else:
			frappe.throw(_('You cannot restart a Subscription that is not cancelled.'))

	def get_precision(self):
		invoice = self.get_current_invoice()
		if invoice:
			return invoice.precision('grand_total')


def get_prorata_factor(period_end, period_start):
	diff = flt(date_diff(nowdate(), period_start) + 1)
	plan_days = flt(date_diff(period_end, period_start) + 1)
	prorate_factor = diff / plan_days

	return prorate_factor


def process_all():
	"""
	Task to updates the status of all `Subscription` apart from those that are cancelled
	"""
	subscriptions = get_all_subscriptions()
	for subscription in subscriptions:
		process(subscription)


def get_all_subscriptions():
	"""
	Returns all `Subscription` documents
	"""
	return frappe.db.sql(
		'select name from `tabSubscription` where status != "Cancelled"',
		as_dict=1
	)


def process(data):
	"""
	Checks a `Subscription` and updates it status as necessary
	"""
	if data:
		try:
			subscription = frappe.get_doc('Subscription', data['name'])
			subscription.process()
			frappe.db.commit()
		except frappe.ValidationError:
			frappe.db.rollback()
			frappe.db.begin()
			frappe.log_error(frappe.get_traceback())
			frappe.db.commit()


@frappe.whitelist()
def cancel_subscription(name):
	"""
	Cancels a `Subscription`. This will stop the `Subscription` from further invoicing the
	`Subscriber` but all already outstanding invoices will not be affected.
	"""
	subscription = frappe.get_doc('Subscription', name)
	subscription.cancel_subscription()


@frappe.whitelist()
def restart_subscription(name):
	"""
	Restarts a cancelled `Subscription`. The `Subscription` will 'forget' the history of
	all invoices it has generated
	"""
	subscription = frappe.get_doc('Subscription', name)
	subscription.restart_subscription()


@frappe.whitelist()
def get_subscription_updates(name):
	"""
	Use this to get the latest state of the given `Subscription`
	"""
	subscription = frappe.get_doc('Subscription', name)
	subscription.process()
