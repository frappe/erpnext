# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe, unittest
from erpnext.setup.utils import get_exchange_rate

test_records = frappe.get_test_records('Currency Exchange')


def save_new_records(test_records):
	for record in test_records:
		kwargs = dict(
			doctype=record.get("doctype"),
			docname=record.get("date") + '-' + record.get("from_currency") + '-' + record.get("to_currency"),
			fieldname="exchange_rate",
			value=record.get("exchange_rate"),
		)

		try:
			frappe.set_value(**kwargs)
		except frappe.DoesNotExistError:
			curr_exchange = frappe.new_doc(record.get("doctype"))
			curr_exchange.date = record["date"]
			curr_exchange.from_currency = record["from_currency"]
			curr_exchange.to_currency = record["to_currency"]
			curr_exchange.exchange_rate = record["exchange_rate"]
			curr_exchange.insert()


class TestCurrencyExchange(unittest.TestCase):
	def clear_cache(self):
		cache = frappe.cache()
		key = "currency_exchange_rate:{0}:{1}".format("USD", "INR")
		cache.delete(key)

	def tearDown(self):
		frappe.db.set_value("Accounts Settings", None, "allow_stale", 1)
		self.clear_cache()

	def test_exchange_rate(self):
		save_new_records(test_records)

		frappe.db.set_value("Accounts Settings", None, "allow_stale", 1)

		# Start with allow_stale is True
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-01")
		self.assertEqual(exchange_rate, 60.0)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-15")
		self.assertEqual(exchange_rate, 65.1)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-30")
		self.assertEqual(exchange_rate, 62.9)
		
		# Exchange rate as on 15th Dec, 2015, should be fetched from fixer.io
		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2015-12-15")
		self.assertFalse(exchange_rate == 60)
		self.assertEqual(exchange_rate, 66.894)

	def test_exchange_rate_strict(self):
		# strict currency settings
		frappe.db.set_value("Accounts Settings", None, "allow_stale", 0)
		frappe.db.set_value("Accounts Settings", None, "stale_days", 1)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-01")
		self.assertEqual(exchange_rate, 60.0)

		# Will fetch from fixer.io
		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-15")
		self.assertEqual(exchange_rate, 67.79)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-30")
		self.assertEqual(exchange_rate, 62.9)

		# Exchange rate as on 15th Dec, 2015, should be fetched from fixer.io
		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2015-12-15")
		self.assertEqual(exchange_rate, 66.894)

		exchange_rate = get_exchange_rate("INR", "NGN", "2016-01-10")
		self.assertEqual(exchange_rate, 65.1)

		# NGN is not available on fixer.io so these should return 0
		exchange_rate = get_exchange_rate("INR", "NGN", "2016-01-09")
		self.assertEqual(exchange_rate, 0)

		exchange_rate = get_exchange_rate("INR", "NGN", "2016-01-11")
		self.assertEqual(exchange_rate, 0)

	def test_exchange_rate_strict_switched(self):
		# Start with allow_stale is True
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-15")
		self.assertEqual(exchange_rate, 65.1)

		frappe.db.set_value("Accounts Settings", None, "allow_stale", 0)
		frappe.db.set_value("Accounts Settings", None, "stale_days", 1)

		# Will fetch from fixer.io
		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-15")
		self.assertEqual(exchange_rate, 67.79)