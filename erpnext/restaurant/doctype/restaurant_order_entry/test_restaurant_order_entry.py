# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe, json
import unittest

from erpnext.restaurant.doctype.restaurant_order_entry.restaurant_order_entry \
	import (sync, make_invoice, item_query_restaurant)

class TestRestaurantOrderEntry(unittest.TestCase):
	def setUp(self):
		# save the menus as Price List is deleted before tests...
		frappe.get_doc('Restaurant Menu', 'Test Restaurant 1 Menu 1').save()
		frappe.get_doc('Restaurant Menu', 'Test Restaurant 1 Menu 2').save()

		if not frappe.db.get_value('Restaurant', 'Test Restaurant 1', 'active_menu'):
			restaurant = frappe.get_doc('Restaurant', 'Test Restaurant 1')
			restaurant.active_menu = 'Test Restaurant 1 Menu 1'
			restaurant.save()

	def test_update_order(self):
		table = frappe.db.get_value('Restaurant Table', dict(restaurant = 'Test Restaurant 1'))
		invoice = sync(table,
			json.dumps([dict(item='Food Item 1', qty = 10), dict(item='Food Item 2', qty = 2)]))

		self.assertEquals(invoice.get('restaurant_table'), table)
		self.assertEquals(invoice.get('items')[0].get('item_code'), 'Food Item 1')
		self.assertEquals(invoice.get('items')[1].get('item_code'), 'Food Item 2')
		self.assertEquals(invoice.get('net_total'), 4600)

		return table

	def test_billing(self):
		table = self.test_update_order()
		invoice_name = make_invoice(table, '_Test Customer', 'Cash')

		sales_invoice = frappe.get_doc('Sales Invoice', invoice_name)

		self.assertEquals(sales_invoice.grand_total, 4600)
		self.assertEquals(sales_invoice.items[0].item_code, 'Food Item 1')
		self.assertEquals(sales_invoice.items[1].item_code, 'Food Item 2')
		self.assertEquals(sales_invoice.payments[0].mode_of_payment, 'Cash')
		self.assertEquals(sales_invoice.payments[0].amount, 4600)

	def test_item_query(self):
		table = frappe.db.get_value('Restaurant Table', dict(restaurant = 'Test Restaurant 1'))
		result = item_query_restaurant(filters=dict(table=table))
		items = [d[0] for d in result]
		self.assertTrue('Food Item 1' in items)
		self.assertTrue('_Test Item 1' not in items)
