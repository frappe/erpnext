# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe, unittest
test_records = frappe.get_test_records('Currency Exchange')

class TestCurrencyExchange(unittest.TestCase):
	def test_exchnage_rate(self):
		from erpnext.setup.utils import get_exchange_rate
		
		# Exchange rate as on 15th Jan, 2016, should be fetched from Currency Exchange record
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-15")
		self.assertEqual(exchange_rate, 60.0)
		
		# Exchange rate as on 15th Dec, 2015, should be fetched from fixer.io
		exchange_rate = get_exchange_rate("USD", "INR", "2015-12-15")
		self.assertFalse(exchange_rate==60)
		