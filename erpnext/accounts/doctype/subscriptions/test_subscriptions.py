# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils.data import nowdate, add_days, get_last_day


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

		subscription.delete()

	def test_create_subscription_without_trial_with_correct_period(self):
		subscription = frappe.new_doc('Subscriptions')
		subscription.subscriber = '_Test Customer'
		subscription.append('plans', {'plan': '_Test Plan Name'})
		subscription.save()

		self.assertEqual(subscription.trial_period_start, None)
		self.assertEqual(subscription.trial_period_end, None)
		self.assertEqual(subscription.current_invoice_start, nowdate())
		self.assertEqual(subscription.current_invoice_end, get_last_day(nowdate()))
		self.assertEqual(len(subscription.invoices), 1)

		subscription.delete()