# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe


class TestPromotionalScheme(unittest.TestCase):
	def test_promotional_scheme(self):
		ps = make_promotional_scheme()
		price_rules = frappe.get_all('Pricing Rule', fields = ["promotional_scheme_id", "name", "creation"],
			filters = {'promotional_scheme': ps.name})
		self.assertTrue(len(price_rules),1)
		price_doc_details = frappe.db.get_value('Pricing Rule', price_rules[0].name, ['customer', 'min_qty', 'discount_percentage'], as_dict = 1)
		self.assertTrue(price_doc_details.customer, '_Test Customer')
		self.assertTrue(price_doc_details.min_qty, 4)
		self.assertTrue(price_doc_details.discount_percentage, 20)

		ps.price_discount_slabs[0].min_qty = 6
		ps.append('customer', {
			'customer': "_Test Customer 2"})
		ps.save()
		price_rules = frappe.get_all('Pricing Rule', fields = ["promotional_scheme_id", "name"],
			filters = {'promotional_scheme': ps.name})
		self.assertTrue(len(price_rules), 2)

		price_doc_details = frappe.db.get_value('Pricing Rule', price_rules[1].name, ['customer', 'min_qty', 'discount_percentage'], as_dict = 1)
		self.assertTrue(price_doc_details.customer, '_Test Customer 2')
		self.assertTrue(price_doc_details.min_qty, 6)
		self.assertTrue(price_doc_details.discount_percentage, 20)

		price_doc_details = frappe.db.get_value('Pricing Rule', price_rules[0].name, ['customer', 'min_qty', 'discount_percentage'], as_dict = 1)
		self.assertTrue(price_doc_details.customer, '_Test Customer')
		self.assertTrue(price_doc_details.min_qty, 6)

		frappe.delete_doc('Promotional Scheme', ps.name)
		price_rules = frappe.get_all('Pricing Rule', fields = ["promotional_scheme_id", "name"],
			filters = {'promotional_scheme': ps.name})
		self.assertEqual(price_rules, [])

def make_promotional_scheme():
	ps = frappe.new_doc('Promotional Scheme')
	ps.name = '_Test Scheme'
	ps.append('items',{
		'item_code': '_Test Item'
	})
	ps.selling = 1
	ps.append('price_discount_slabs',{
		'min_qty': 4,
		'discount_percentage': 20,
		'rule_description': 'Test'
	})
	ps.applicable_for = 'Customer'
	ps.append('customer',{
		'customer': "_Test Customer"
	})
	ps.save()

	return ps
