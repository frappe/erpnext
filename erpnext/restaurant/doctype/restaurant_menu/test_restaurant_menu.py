# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_records = [
	dict(doctype='Item', item_code='Food Item 1',
		item_group='Products', is_stock_item=0),
	dict(doctype='Item', item_code='Food Item 2',
		item_group='Products', is_stock_item=0),
	dict(doctype='Item', item_code='Food Item 3',
		item_group='Products', is_stock_item=0),
	dict(doctype='Item', item_code='Food Item 4',
		item_group='Products', is_stock_item=0),
	dict(doctype='Restaurant Menu', restaurant='Test Restaurant 1', name='Test Restaurant 1 Menu 1',
		items = [
			dict(item='Food Item 1', rate=400),
			dict(item='Food Item 2', rate=300),
			dict(item='Food Item 3', rate=200),
			dict(item='Food Item 4', rate=100),
		]),
	dict(doctype='Restaurant Menu', restaurant='Test Restaurant 1', name='Test Restaurant 1 Menu 2',
		items = [
			dict(item='Food Item 1', rate=450),
			dict(item='Food Item 2', rate=350),
		])
]

class TestRestaurantMenu(unittest.TestCase):
	def test_price_list_creation_and_editing(self):
		menu1 = frappe.get_doc('Restaurant Menu', 'Test Restaurant 1 Menu 1')
		menu1.save()

		menu2 = frappe.get_doc('Restaurant Menu', 'Test Restaurant 1 Menu 2')
		menu2.save()

		self.assertTrue(frappe.db.get_value('Price List', 'Test Restaurant 1 Menu 1'))
		self.assertEquals(frappe.db.get_value('Item Price',
			dict(price_list = 'Test Restaurant 1 Menu 1', item_code='Food Item 1'), 'price_list_rate'), 400)
		self.assertEquals(frappe.db.get_value('Item Price',
			dict(price_list = 'Test Restaurant 1 Menu 2', item_code='Food Item 1'), 'price_list_rate'), 450)

		menu1.items[0].rate = 401
		menu1.save()

		self.assertEquals(frappe.db.get_value('Item Price',
			dict(price_list = 'Test Restaurant 1 Menu 1', item_code='Food Item 1'), 'price_list_rate'), 401)

		menu1.items[0].rate = 400
		menu1.save()
