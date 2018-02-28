# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils.data import nowdate, add_days, get_last_day, cint, getdate, add_to_date, get_datetime_str
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry


class TestSubscriptions(unittest.TestCase):
	def create_plan(self):
		if not frappe.db.exists('Subscription Plan', '_Test Plan Name'):
			plan = frappe.new_doc('Subscription Plan')
			plan.plan_name = '_Test Plan Name'
			plan.item = '_Test Non Stock Item'
			plan.cost = 900
			plan.billing_interval = 'Month'
			plan.billing_interval_count = 1
			plan.insert()

		if not frappe.db.exists('Subscription Plan', '_Test Plan Name 2'):
			plan = frappe.new_doc('Subscription Plan')
			plan.plan_name = '_Test Plan Name 2'
			plan.item = '_Test Non Stock Item'
			plan.cost = 1999
			plan.billing_interval = 'Month'
			plan.billing_interval_count = 1
			plan.insert()

		if not frappe.db.exists('Subscription Plan', '_Test Plan Name 3'):
			plan = frappe.new_doc('Subscription Plan')
			plan.plan_name = '_Test Plan Name 3'
			plan.item = '_Test Non Stock Item'
			plan.cost = 1999
			plan.billing_interval = 'Day'
			plan.billing_interval_count = 14
			plan.insert()

	def create_subscriber(self):
		if not frappe.db.exists('Subscriber', '_Test Customer'):
			subscriber = frappe.new_doc('Subscriber')
			subscriber.subscriber_name = '_Test Customer'
			subscriber.customer = '_Test Customer'
			subscriber.insert()

	def setUp(self):
		self.create_plan()
		self.create_subscriber()

	def test_create_subscription_with_trial_with_correct_period(self):
		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.trial_period_start = nowdate()
		subscription.trial_period_end = add_days(nowdate(), 30)
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.save()

		self.assertEqual(subscription.trial_period_start, nowdate())
		self.assertEqual(subscription.trial_period_end, add_days(nowdate(), 30))
		self.assertEqual(subscription.trial_period_start, subscription.current_invoice_start)
		self.assertEqual(subscription.trial_period_end, subscription.current_invoice_end)
		self.assertEqual(subscription.invoices, [])
		self.assertEqual(subscription.status, 'Trialling')

		subscription.delete()

	def test_create_subscription_without_trial_with_correct_period(self):
		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.save()

		self.assertEqual(subscription.trial_period_start, None)
		self.assertEqual(subscription.trial_period_end, None)
		self.assertEqual(subscription.current_invoice_start, nowdate())
		self.assertEqual(subscription.current_invoice_end, add_to_date(nowdate(), months=1, days=-1))
		# No invoice is created
		self.assertEqual(len(subscription.invoices), 0)
		self.assertEqual(subscription.status, 'Active')

		subscription.delete()

	def test_create_subscription_trial_with_wrong_dates(self):
		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.trial_period_end = nowdate()
		subscription.trial_period_start = add_days(nowdate(), 30)
		subscription.append('plans', {'plan': '_Test Plan Name'})

		self.assertRaises(frappe.ValidationError, subscription.save)
		subscription.delete()

	def test_create_subscription_multi_with_different_billing_fails(self):
		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.trial_period_end = nowdate()
		subscription.trial_period_start = add_days(nowdate(), 30)
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.append('plans', {'plan': '_Test Plan Name 3'})

		self.assertRaises(frappe.ValidationError, subscription.save)
		subscription.delete()

	def test_invoice_is_generated_at_end_of_billing_period(self):
		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.insert()

		self.assertEqual(subscription.status, 'Active')

		subscription.set_current_invoice_start('2018-01-01')
		subscription.set_current_invoice_end()

		self.assertEqual(subscription.current_invoice_start, '2018-01-01')
		self.assertEqual(subscription.current_invoice_end, '2018-01-31')
		subscription.process()

		self.assertEqual(len(subscription.invoices), 1)
		self.assertEqual(subscription.current_invoice_start, nowdate())
		self.assertEqual(subscription.status, 'Past Due Date')
		subscription.delete()

	def test_status_goes_back_to_active_after_invoice_is_paid(self):
		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.insert()
		subscription.set_current_invoice_start('2018-01-01')
		subscription.set_current_invoice_end()
		subscription.process()	# generate first invoice
		self.assertEqual(len(subscription.invoices), 1)
		self.assertEqual(subscription.status, 'Past Due Date')

		subscription.get_current_invoice()
		current_invoice = subscription.get_current_invoice()

		self.assertIsNotNone(current_invoice)

		current_invoice.db_set('outstanding_amount', 0)
		current_invoice.db_set('status', 'Paid')
		subscription.process()

		self.assertEqual(subscription.status, 'Active')
		self.assertEqual(subscription.current_invoice_start, nowdate())
		self.assertEqual(len(subscription.invoices), 1)

		subscription.delete()

	def test_subscription_cancel_after_grace_period(self):
		settings = frappe.get_single('Subscription Settings')
		default_grace_period_action = settings.cancel_after_grace
		settings.cancel_after_grace = 1
		settings.save()

		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.insert()
		subscription.set_current_invoice_start('2018-01-01')
		subscription.set_current_invoice_end()
		subscription.process()	# generate first invoice

		self.assertEqual(subscription.status, 'Past Due Date')

		subscription.process()	
		# This should change status to Canceled since grace period is 0
		self.assertEqual(subscription.status, 'Canceled')

		settings.cancel_after_grace = default_grace_period_action
		settings.save()
		subscription.delete()

	def test_subscription_unpaid_after_grace_period(self):
		settings = frappe.get_single('Subscription Settings')
		default_grace_period_action = settings.cancel_after_grace
		settings.cancel_after_grace = 0
		settings.save()

		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.insert()
		subscription.set_current_invoice_start('2018-01-01')
		subscription.set_current_invoice_end()
		subscription.process()	# generate first invoice

		self.assertEqual(subscription.status, 'Past Due Date')

		subscription.process()	
		# This should change status to Canceled since grace period is 0
		self.assertEqual(subscription.status, 'Unpaid')

		settings.cancel_after_grace = default_grace_period_action
		settings.save()
		subscription.delete()

	def test_subscription_invoice_days_until_due(self):
		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.days_until_due = 10
		subscription.insert()
		subscription.set_current_invoice_start(get_datetime_str(add_to_date(nowdate(), months=-1)))
		subscription.set_current_invoice_end()
		subscription.process()	# generate first invoice
		self.assertEqual(len(subscription.invoices), 1)
		self.assertEqual(subscription.status, 'Active')

		subscription.delete()

	def test_subcription_is_past_due_doesnt_change_within_grace_period(self):
		settings = frappe.get_single('Subscription Settings')
		grace_period = settings.grace_period
		settings.grace_period = 1000
		settings.save()

		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.insert()
		subscription.set_current_invoice_start('2018-01-01')
		subscription.set_current_invoice_end()
		subscription.process()	# generate first invoice

		self.assertEqual(subscription.status, 'Past Due Date')

		subscription.process()	
		# Grace period is 1000 days so status should remain as Past Due Date
		self.assertEqual(subscription.status, 'Past Due Date')

		subscription.process()
		self.assertEqual(subscription.status, 'Past Due Date')

		subscription.process()
		self.assertEqual(subscription.status, 'Past Due Date')

		settings.grace_period = grace_period
		settings.save()
		subscription.delete()

	def test_subscription_remains_active_during_invoice_period(self):
		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.save()
		subscription.process()	# no changes expected

		self.assertEqual(subscription.status, 'Active')
		self.assertEqual(subscription.current_invoice_start, nowdate())
		self.assertEqual(subscription.current_invoice_end, add_to_date(nowdate(), months=1, days=-1))
		self.assertEqual(len(subscription.invoices), 0)
		
		subscription.process()	# no changes expected still
		self.assertEqual(subscription.status, 'Active')
		self.assertEqual(subscription.current_invoice_start, nowdate())
		self.assertEqual(subscription.current_invoice_end, add_to_date(nowdate(), months=1, days=-1))
		self.assertEqual(len(subscription.invoices), 0)

		subscription.process()	# no changes expected yet still
		self.assertEqual(subscription.status, 'Active')
		self.assertEqual(subscription.current_invoice_start, nowdate())
		self.assertEqual(subscription.current_invoice_end, add_to_date(nowdate(), months=1, days=-1))
		self.assertEqual(len(subscription.invoices), 0)

		subscription.delete()

	def test_subscription_creation_with_multiple_plans(self):
		pass
