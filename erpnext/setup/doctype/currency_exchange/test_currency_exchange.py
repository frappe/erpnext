# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest
from unittest import mock

import frappe
from frappe.utils import cint, flt

from erpnext.setup.utils import get_exchange_rate

test_records = frappe.get_test_records('Currency Exchange')

def save_new_records(test_records):
	for record in test_records:
		# If both selling and buying enabled
		purpose = "Selling-Buying"

		if cint(record.get("for_buying"))==0 and cint(record.get("for_selling"))==1:
			purpose = "Selling"
		if cint(record.get("for_buying"))==1 and cint(record.get("for_selling"))==0:
			purpose = "Buying"
		kwargs = dict(
			doctype=record.get("doctype"),
			docname=record.get("date") + '-' + record.get("from_currency") + '-' + record.get("to_currency") + '-' + purpose,
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

test_exchange_values = {
	'2015-12-15': '66.999',
	'2016-01-15': '65.1'
}

# Removing API call from get_exchange_rate
def patched_requests_get(*args, **kwargs):
	class PatchResponse:
		def __init__(self, json_data, status_code):
			self.json_data = json_data
			self.status_code = status_code

		def raise_for_status(self):
			if self.status_code != 200:
				raise frappe.DoesNotExistError

		def json(self):
			return self.json_data

	if args[0] == "https://api.exchangerate.host/convert" and kwargs.get('params'):
		if kwargs['params'].get('date') and kwargs['params'].get('from') and kwargs['params'].get('to'):
			if test_exchange_values.get(kwargs['params']['date']):
				return PatchResponse({'result': test_exchange_values[kwargs['params']['date']]}, 200)

	return PatchResponse({'result': None}, 404)

@mock.patch('requests.get', side_effect=patched_requests_get)
class TestCurrencyExchange(unittest.TestCase):
	def clear_cache(self):
		cache = frappe.cache()
		for date in test_exchange_values.keys():
			key = "currency_exchange_rate_{0}:{1}:{2}".format(date, "USD", "INR")
			cache.delete(key)

	def tearDown(self):
		frappe.db.set_value("Accounts Settings", None, "allow_stale", 1)
		self.clear_cache()

	def test_exchange_rate(self, mock_get):
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

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-20", "for_buying")
		self.assertFalse(exchange_rate == 60)
		self.assertEqual(flt(exchange_rate, 3), 65.1)

	def test_exchange_rate_strict(self, mock_get):
		# strict currency settings
		frappe.db.set_value("Accounts Settings", None, "allow_stale", 0)
		frappe.db.set_value("Accounts Settings", None, "stale_days", 1)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-01", "for_buying")
		self.assertEqual(exchange_rate, 60.0)

		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-15", "for_buying")
		self.assertEqual(flt(exchange_rate, 3), 65.100)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-30", "for_selling")
		self.assertEqual(exchange_rate, 62.9)

		# Exchange rate as on 15th Dec, 2015
		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2015-12-15", "for_buying")
		self.assertEqual(flt(exchange_rate, 3), 66.999)

	def test_exchange_rate_strict_switched(self, mock_get):
		# Start with allow_stale is True
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-15", "for_buying")
		self.assertEqual(exchange_rate, 65.1)

		frappe.db.set_value("Accounts Settings", None, "allow_stale", 0)
		frappe.db.set_value("Accounts Settings", None, "stale_days", 1)

		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-30", "for_buying")
		self.assertFalse(exchange_rate == 65)
		self.assertEqual(flt(exchange_rate, 3), 62.9)
