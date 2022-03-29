# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest

import frappe
from frappe.utils import cint, flt

from erpnext.setup.utils import get_exchange_rate

test_records = frappe.get_test_records("Currency Exchange")


def save_new_records(test_records):
	for record in test_records:
		# If both selling and buying enabled
		purpose = "Selling-Buying"

		if cint(record.get("for_buying")) == 0 and cint(record.get("for_selling")) == 1:
			purpose = "Selling"
		if cint(record.get("for_buying")) == 1 and cint(record.get("for_selling")) == 0:
			purpose = "Buying"
		kwargs = dict(
			doctype=record.get("doctype"),
			docname=record.get("date")
			+ "-"
			+ record.get("from_currency")
			+ "-"
			+ record.get("to_currency")
			+ "-"
			+ purpose,
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
			curr_exchange.for_buying = record["for_buying"]
			curr_exchange.for_selling = record["for_selling"]
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
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-01", "for_buying")
		self.assertEqual(flt(exchange_rate, 3), 60.0)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-15", "for_buying")
		self.assertEqual(exchange_rate, 65.1)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-30", "for_selling")
		self.assertEqual(exchange_rate, 62.9)

		# Exchange rate as on 15th Dec, 2015
		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2015-12-15", "for_selling")
		self.assertFalse(exchange_rate == 60)
		self.assertEqual(flt(exchange_rate, 3), 66.999)

	def test_exchange_rate_strict(self):
		# strict currency settings
		frappe.db.set_value("Accounts Settings", None, "allow_stale", 0)
		frappe.db.set_value("Accounts Settings", None, "stale_days", 1)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-01", "for_buying")
		self.assertEqual(exchange_rate, 60.0)

		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-15", "for_buying")
		self.assertEqual(flt(exchange_rate, 3), 67.235)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-30", "for_selling")
		self.assertEqual(exchange_rate, 62.9)

		# Exchange rate as on 15th Dec, 2015
		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2015-12-15", "for_buying")
		self.assertEqual(flt(exchange_rate, 3), 66.999)

	def test_exchange_rate_strict_switched(self):
		# Start with allow_stale is True
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-15", "for_buying")
		self.assertEqual(exchange_rate, 65.1)

		frappe.db.set_value("Accounts Settings", None, "allow_stale", 0)
		frappe.db.set_value("Accounts Settings", None, "stale_days", 1)

		# Will fetch from fixer.io
		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-15", "for_buying")
		self.assertEqual(flt(exchange_rate, 3), 67.235)
