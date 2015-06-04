# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe

class TestShoppingCart(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		enable_shopping_cart()

	def tearDown(self):
		frappe.set_user("Administrator")
		disable_shopping_cart()

def enable_shopping_cart():
	pass

def disable_shopping_cart():
	pass

