# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import unittest
from erpnext.non_profit.doctype.member.member import create_member
from erpnext.stock.doctype.item.test_item import create_item

class TestMembership(unittest.TestCase):
	def setUp(self):
		# Get default company
		company = frappe.get_doc("Company", erpnext.get_default_company())
		
		# update membership settings
		settings = frappe.get_doc("Membership Settings")
		# Enable razorpay
		settings.enable_razorpay = 1
		settings.billing_cycle = "Monthly"
		settings.billing_frequency = 24
		# Enable invoicing
		settings.enable_invoicing = 1
		settings.make_payment_entry = 1
		settings.company = company.name
		settings.payment_to = company.default_cash_account
		settings.debit_account = company.default_receivable_account
		settings.save()

		# make test plan
		plan = frappe.new_doc("Membership Type")
		plan.amount = 100
		plan.razorpay_plan_id = "_rzpy_test_milythm"
		plan.linked_item = create_item("_Test Item for Non Profit Membership")
		plan.insert()

		# make test member
		self.member_doc = create_member(frappe._dict({
				'fullname': "_Test_Member",
				'email': "_test_member_erpnext@example.com",
				'plan_id': plan.name
		}))

	def test_auto_generate_invoice_and_payment_entry(self):
		pass

	def test_renew within_30_days(self):
		pass

	def test_from_to_dates(self):
		pass

	def test_razorpay_webook(self):
		pass
