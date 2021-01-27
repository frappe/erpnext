# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import unittest
import frappe
import erpnext
from erpnext.non_profit.doctype.member.member import create_member
from frappe.utils import nowdate, add_months

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
		settings.payment_account = company.default_cash_account
		settings.debit_account = company.default_receivable_account
		settings.save()

		# make test plan
		if not frappe.db.exists("Membership Type", "_rzpy_test_milythm"):
			plan = frappe.new_doc("Membership Type")
			plan.membership_type = "_rzpy_test_milythm"
			plan.amount = 100
			plan.razorpay_plan_id = "_rzpy_test_milythm"
			plan.linked_item = create_item("_Test Item for Non Profit Membership").name
			plan.insert()
		else:
			plan = frappe.get_doc("Membership Type", "_rzpy_test_milythm")

		# make test member
		self.member_doc = create_member(frappe._dict({
				'fullname': "_Test_Member",
				'email': "_test_member_erpnext@example.com",
				'plan_id': plan.name
		}))
		self.member_doc.make_customer_and_link()
		self.member = self.member_doc.name

	def test_auto_generate_invoice_and_payment_entry(self):
		entry = make_membership(self.member)

		# Naive test to see if at all invoice was generated and attached to member
		# In any case if details were missing, the invoicing would throw an error
		invoice = entry.generate_invoice(save=True)
		self.assertEqual(invoice.name, entry.invoice)

	def test_renew_within_30_days(self):
		# create a membership for two months
		# Should work fine
		make_membership(self.member, { "from_date": nowdate() })
		make_membership(self.member, { "from_date": add_months(nowdate(), 1) })

		from frappe.utils.user import add_role
		add_role("test@example.com", "Non Profit Manager")
		frappe.set_user("test@example.com")

		# create next membership with expiry not within 30 days
		self.assertRaises(frappe.ValidationError, make_membership, self.member, {
			"from_date": add_months(nowdate(), 2),
		})

		frappe.set_user("Administrator")
		# create the same membership but as administrator
		make_membership(self.member, {
			"from_date": add_months(nowdate(), 2),
			"to_date": add_months(nowdate(), 3),
		})

def set_config(key, value):
	frappe.db.set_value("Membership Settings", None, key, value)

def make_membership(member, payload={}):
	data = {
		"doctype": "Membership",
		"member": member,
		"membership_status": "Current",
		"membership_type": "_rzpy_test_milythm",
		"currency": "INR",
		"paid": 1,
		"from_date": nowdate(),
		"amount": 100
	}
	data.update(payload)
	membership = frappe.get_doc(data)
	membership.insert(ignore_permissions=True, ignore_if_duplicate=True)
	return membership

def create_item(item_code):
	if not frappe.db.exists("Item", item_code):
		item = frappe.new_doc("Item")
		item.item_code = item_code
		item.item_name = item_code
		item.stock_uom = "Nos"
		item.description = item_code
		item.item_group = "All Item Groups"
		item.is_stock_item = 0
		item.save()
	else:
		item = frappe.get_doc("Item", item_code)
	return item
