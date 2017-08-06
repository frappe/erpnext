# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from frappe.utils import cint


class TestPaymentDueDate(unittest.TestCase):
	def test_create_pdd_quick(self):
		pyt_due_date = frappe.get_doc(
			{"code": "_COD", "description": "_Cash On Delivery", "doctype": "Payment Due Date"}
		)
		pyt_due_date.insert()
		self.assertEqual(pyt_due_date.code, '_COD')
		self.assertEqual(pyt_due_date.description, '_Cash On Delivery')

		saved_pyt_due_date = frappe.get_doc('Payment Due Date', '_COD')
		self.assertEqual(saved_pyt_due_date.code, '_COD')
		self.assertEqual(saved_pyt_due_date.description, '_Cash On Delivery')

		saved_pyt_due_date.delete()

	def test_create_pyt_due_date_full(self):
		pyt_due_date = frappe.get_doc(
			{
				"doctype": "Payment Due Date", "term_days": 30, "count_from_month_end": 0,
				"with_discount": 1, "code": "_2/10 N30",
				"description": "_2% Cash Discount Within 10 days; Net 30 days",
				"discount": 2, "discount_days": 10
			}
		)
		pyt_due_date.insert()
		self.assertEqual(pyt_due_date.code, '_2/10 N30')
		self.assertEqual(pyt_due_date.description, '_2% Cash Discount Within 10 days; Net 30 days')
		self.assertEqual(cint(pyt_due_date.term_days), 30)
		self.assertEqual(cint(pyt_due_date.with_discount), 1)
		self.assertEqual(cint(pyt_due_date.discount), 2)
		self.assertEqual(cint(pyt_due_date.discount_days), 10)

		saved_pyt_due_date = frappe.get_doc('Payment Due Date', '_2/10 N30')
		self.assertEqual(saved_pyt_due_date.code, '_2/10 N30')
		self.assertEqual(saved_pyt_due_date.description, '_2% Cash Discount Within 10 days; Net 30 days')
		self.assertEqual(cint(saved_pyt_due_date.term_days), 30)
		self.assertEqual(cint(saved_pyt_due_date.with_discount), 1)
		self.assertEqual(cint(saved_pyt_due_date.discount), 2)
		self.assertEqual(cint(saved_pyt_due_date.discount_days), 10)

		saved_pyt_due_date.delete()

	def test_pay_due_date_numerical_field_validation(self):
		pyt_due_date = frappe.get_doc(
			{"code": "_COD", "description": "_Cash On Delivery", "doctype": "Payment Due Date"}
		)
		pyt_due_date.term_days = -30
		self.assertRaises(frappe.ValidationError, pyt_due_date.insert)
		pyt_due_date.term_days = 0
		pyt_due_date.with_discount = 1
		self.assertRaises(frappe.ValidationError, pyt_due_date.insert)
		pyt_due_date.discount = -10
		self.assertRaises(frappe.ValidationError, pyt_due_date.insert)
		pyt_due_date.discount = 0
		pyt_due_date.discount_days = -30
		self.assertRaises(frappe.ValidationError, pyt_due_date.insert)
		pyt_due_date.term_days = -30
		pyt_due_date.discount = -2
		pyt_due_date.discount_days = -30
		self.assertRaises(frappe.ValidationError, pyt_due_date.insert)

	def test_pay_due_date_discount_validation(self):
		pyt_due_date = frappe.get_doc(
			{
				"doctype": "Payment Due Date", "term_days": 0, "count_from_month_end": 0,
				"with_discount": 1, "code": "_2/10 N30",
				"description": "_2% Cash Discount Within 10 days; Net 30 days",
				"discount": 0, "discount_days": 10
			}
		)
		self.assertRaises(frappe.ValidationError, pyt_due_date.insert)
		pyt_due_date.discount = 2
		pyt_due_date.discount_days = 0
		self.assertRaises(frappe.ValidationError, pyt_due_date.insert)