# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils.data import nowdate, add_days, get_last_day, cint, getdate, add_to_date


class TestSubscriptions(unittest.TestCase):
	def create_plan(self):
		if not frappe.db.exists('Subscription Plan', '_Test Plan Name'):
			plan = frappe.new_doc('Subscription Plan')
			plan.plan_name = '_Test Plan Name'
			plan.item = '_Test Non Stock Item'
			plan.cost = 999.99
			plan.billing_interval = 'Month'
			plan.billing_interval_count = 1
			plan.insert()

		if not frappe.db.exists('Subscription Plan', '_Test Plan Name 2'):
			plan = frappe.new_doc('Subscription Plan')
			plan.plan_name = '_Test Plan Name 2'
			plan.item = '_Test Non Stock Item'
			plan.cost = 1999.99
			plan.billing_interval = 'Month'
			plan.billing_interval_count = 1
			plan.insert()

		if not frappe.db.exists('Subscription Plan', '_Test Plan Name 3'):
			plan = frappe.new_doc('Subscription Plan')
			plan.plan_name = '_Test Plan Name 3'
			plan.item = '_Test Non Stock Item'
			plan.cost = 1999.99
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

	def test_create_subscription_multi_with_different_billing_fails(self):
		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.trial_period_end = nowdate()
		subscription.trial_period_start = add_days(nowdate(), 30)
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.append('plans', {'plan': '_Test Plan Name 3'})

		self.assertRaises(frappe.ValidationError, subscription.save)

	# def test_subscription_invoice_days_until_due(self):
	# 	subscription = frappe.new_doc('Subscriptions')
	# 	subscription.subscriber = '_Test Customer'
	# 	subscription.append('plans', {'plan': '_Test Plan Name'})
	# 	subscription.save()

	# 	generated_invoice_name = subscription.invoices[-1].invoice
	# 	invoice = frappe.get_doc('Sales Invoice', generated_invoice_name)

	# 	self.assertEqual(
	# 		invoice.due_date, 
	# 		add_days(subscription.current_invoice_end, cint(subscription.days_until_due))
	# 	)

	# 	subscription.delete()

	def test_subscription_creation_with_multiple_plans(self):
		pass
