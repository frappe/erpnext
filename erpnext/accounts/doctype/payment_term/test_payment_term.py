# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from frappe.utils import cint


class TestPaymentTerm(unittest.TestCase):
	def test_create_pdd_quick(self):
		pyt_term = frappe.get_doc(
			{"code": "_COD", "description": "_Cash On Delivery", "doctype": "Payment Term"}
		)
		pyt_term.insert()
		self.assertEqual(pyt_term.code, '_COD')
		self.assertEqual(pyt_term.description, '_Cash On Delivery')

		saved_pyt_term = frappe.get_doc('Payment Term', '_COD')
		self.assertEqual(saved_pyt_term.code, '_COD')
		self.assertEqual(saved_pyt_term.description, '_Cash On Delivery')

		saved_pyt_term.delete()

	def test_create_pyt_term_full(self):
		pyt_term = frappe.get_doc(
			{
				"doctype": "Payment Term", "term_days": 30, "count_from_month_end": 0,
				"with_discount": 1, "code": "_2/10 N30",
				"description": "_2% Cash Discount Within 10 days; Net 30 days",
				"discount": 2, "discount_days": 10
			}
		)
		pyt_term.insert()
		self.assertEqual(pyt_term.code, '_2/10 N30')
		self.assertEqual(pyt_term.description, '_2% Cash Discount Within 10 days; Net 30 days')
		self.assertEqual(cint(pyt_term.term_days), 30)
		self.assertEqual(cint(pyt_term.with_discount), 1)
		self.assertEqual(cint(pyt_term.discount), 2)
		self.assertEqual(cint(pyt_term.discount_days), 10)

		saved_pyt_term = frappe.get_doc('Payment Term', '_2/10 N30')
		self.assertEqual(saved_pyt_term.code, '_2/10 N30')
		self.assertEqual(saved_pyt_term.description, '_2% Cash Discount Within 10 days; Net 30 days')
		self.assertEqual(cint(saved_pyt_term.term_days), 30)
		self.assertEqual(cint(saved_pyt_term.with_discount), 1)
		self.assertEqual(cint(saved_pyt_term.discount), 2)
		self.assertEqual(cint(saved_pyt_term.discount_days), 10)

		saved_pyt_term.delete()

	def test_pay_due_date_numerical_field_validation(self):
		pyt_term = frappe.get_doc(
			{"code": "_COD", "description": "_Cash On Delivery", "doctype": "Payment Term"}
		)
		pyt_term.term_days = -30
		self.assertRaises(frappe.ValidationError, pyt_term.insert)
		pyt_term.term_days = 0
		pyt_term.with_discount = 1
		self.assertRaises(frappe.ValidationError, pyt_term.insert)
		pyt_term.discount = -10
		self.assertRaises(frappe.ValidationError, pyt_term.insert)
		pyt_term.discount = 0
		pyt_term.discount_days = -30
		self.assertRaises(frappe.ValidationError, pyt_term.insert)
		pyt_term.term_days = -30
		pyt_term.discount = -2
		pyt_term.discount_days = -30
		self.assertRaises(frappe.ValidationError, pyt_term.insert)

	def test_pay_due_date_discount_validation(self):
		pyt_term = frappe.get_doc(
			{
				"doctype": "Payment Term", "term_days": 0, "count_from_month_end": 0,
				"with_discount": 1, "code": "_2/10 N30",
				"description": "_2% Cash Discount Within 10 days; Net 30 days",
				"discount": 0, "discount_days": 10
			}
		)
		self.assertRaises(frappe.ValidationError, pyt_term.insert)
		pyt_term.discount = 2
		pyt_term.discount_days = 0
		self.assertRaises(frappe.ValidationError, pyt_term.insert)