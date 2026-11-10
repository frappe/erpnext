# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from unittest import mock

import frappe
from frappe.utils import cint, flt
from frappe.utils.password import remove_encrypted_password

from erpnext.patches.v16_0 import encrypt_currency_exchange_access_key
from erpnext.setup.utils import get_exchange_rate
from erpnext.tests.utils import ERPNextTestSuite


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


test_exchange_values = {"2015-12-15": "66.999", "2016-01-15": "65.1"}


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

	if args[0] == "https://api.exchangerate.host/convert" and kwargs.get("params"):
		if kwargs["params"].get("date") and kwargs["params"].get("from") and kwargs["params"].get("to"):
			if test_exchange_values.get(kwargs["params"]["date"]):
				return PatchResponse({"result": test_exchange_values[kwargs["params"]["date"]]}, 200)
	elif args[0].startswith("https://api.frankfurter.dev/v1") and kwargs.get("params"):
		if kwargs["params"].get("base") and kwargs["params"].get("symbols"):
			date = args[0].replace("https://api.frankfurter.dev/v1/", "")
			if test_exchange_values.get(date):
				return PatchResponse(
					{"rates": {kwargs["params"].get("symbols"): test_exchange_values.get(date)}}, 200
				)
	elif args[0].startswith("https://api.frankfurter.dev/v2") and kwargs.get("params"):
		if kwargs["params"].get("date") and test_exchange_values.get(kwargs["params"]["date"]):
			return PatchResponse({"rate": test_exchange_values.get(kwargs["params"]["date"])}, 200)

	return PatchResponse({"rates": None}, 404)


@mock.patch("requests.get", side_effect=patched_requests_get)
class TestCurrencyExchange(ERPNextTestSuite):
	def setUp(self):
		self.load_test_records("Currency Exchange")
		save_new_records(self.globalTestRecords["Currency Exchange"])

	def clear_cache(self):
		cache = frappe.cache()
		for date in test_exchange_values.keys():
			key = "currency_exchange_rate_{}:{}:{}".format(date, "USD", "INR")
			cache.delete_value(key)

	def test_exchange_rate(self, mock_get):
		frappe.db.set_single_value("Accounts Settings", "allow_stale", 1)

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
		self.assertNotEqual(exchange_rate, 60)
		self.assertEqual(flt(exchange_rate, 3), 66.999)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-20", "for_buying")
		self.assertNotEqual(exchange_rate, 60)
		self.assertEqual(flt(exchange_rate, 3), 65.1)

	def test_exchange_rate_via_exchangerate_host(self, mock_get):
		# Update Currency Exchange Rate
		settings = frappe.get_single("Currency Exchange Settings")
		settings.service_provider = "exchangerate.host"
		settings.access_key = "12345667890"
		settings.save()

		# Update exchange
		frappe.db.set_single_value("Accounts Settings", "allow_stale", 1)

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
		self.assertNotEqual(exchange_rate, 60)
		self.assertEqual(flt(exchange_rate, 3), 66.999)

		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-20", "for_buying")
		self.assertNotEqual(exchange_rate, 60)
		self.assertEqual(flt(exchange_rate, 3), 65.1)

		settings = frappe.get_single("Currency Exchange Settings")
		settings.service_provider = "frankfurter.dev"
		settings.save()

	def use_exchangerate_host(self, access_key):
		settings = frappe.get_single("Currency Exchange Settings")
		settings.service_provider = "exchangerate.host"
		settings.access_key = access_key
		settings.save()
		self.addCleanup(self.use_frankfurter)

	def use_frankfurter(self):
		settings = frappe.get_single("Currency Exchange Settings")
		settings.service_provider = "frankfurter.dev"
		settings.save()

	def test_exchangerate_host_access_key_is_sent_but_not_stored(self, mock_get):
		self.use_exchangerate_host("12345667890")
		frappe.db.set_single_value("Accounts Settings", "allow_stale", 1)

		settings = frappe.get_single("Currency Exchange Settings")
		self.assertEqual(settings.access_key, "*" * 11)
		self.assertNotIn("access_key", [row.key for row in settings.req_params])

		self.clear_cache()
		self.assertEqual(flt(get_exchange_rate("USD", "INR", "2015-12-15", "for_selling"), 3), 66.999)
		self.assertEqual(mock_get.call_args.kwargs["params"]["access_key"], "12345667890")

	def test_patch_moves_a_plain_text_access_key_to_the_password_store(self, mock_get):
		doctype = "Currency Exchange Settings"
		self.use_exchangerate_host("12345667890")
		# store the settings as they were before the access key became a password
		remove_encrypted_password(doctype, doctype, "access_key")
		frappe.db.set_single_value(doctype, "access_key", "12345667890")
		frappe.db.set_single_value(
			doctype, "url", "https://api.exchangerate.host/convert?access_key=12345667890&amount=1"
		)
		settings = frappe.get_single(doctype)
		settings.append("req_params", {"key": "access_key", "value": "12345667890"}).db_insert()

		encrypt_currency_exchange_access_key.execute()

		settings = frappe.get_single(doctype)
		self.assertEqual(settings.access_key, "*" * 11)
		self.assertEqual(settings.get_password("access_key"), "12345667890")
		self.assertNotIn("access_key", [row.key for row in settings.req_params])
		self.assertEqual(settings.url, "https://api.exchangerate.host/convert?amount=1")

	def test_exchange_rate_strict(self, mock_get):
		# strict currency settings
		frappe.db.set_single_value("Accounts Settings", "allow_stale", 0)
		frappe.db.set_single_value("Accounts Settings", "stale_days", 1)

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

		frappe.db.set_single_value("Accounts Settings", "allow_stale", 0)
		frappe.db.set_single_value("Accounts Settings", "stale_days", 1)

		self.clear_cache()
		exchange_rate = get_exchange_rate("USD", "INR", "2016-01-30", "for_buying")
		self.assertNotEqual(exchange_rate, 65)
		self.assertEqual(flt(exchange_rate, 3), 62.9)

	def test_side_specific_record_wins_on_same_date(self, mock_get):
		frappe.db.set_single_value("Accounts Settings", "allow_stale", 1)
		for for_buying, for_selling, rate in ((1, 1, 100), (0, 1, 101), (1, 0, 99)):
			frappe.get_doc(
				doctype="Currency Exchange",
				date="2031-03-10",
				from_currency="GBP",
				to_currency="INR",
				exchange_rate=rate,
				for_buying=for_buying,
				for_selling=for_selling,
			).insert()

		self.assertEqual(get_exchange_rate("GBP", "INR", "2031-03-10", "for_selling"), 101)
		self.assertEqual(get_exchange_rate("GBP", "INR", "2031-03-10", "for_buying"), 99)
		self.assertEqual(get_exchange_rate("GBP", "INR", "2031-03-11", "for_selling"), 101)

	def test_fields_in_name_cannot_change(self, mock_get):
		doc = frappe.get_doc(
			doctype="Currency Exchange",
			date="2031-03-01",
			from_currency="CHF",
			to_currency="INR",
			exchange_rate=70,
			for_selling=1,
		).insert()

		doc.exchange_rate = 71
		doc.save()

		doc.date = "2031-03-10"
		self.assertRaises(frappe.CannotChangeConstantError, doc.save)

		doc.reload()
		doc.for_buying = 0
		self.assertRaises(frappe.CannotChangeConstantError, doc.save)

	def test_reverse_record_is_used_when_no_direct_record(self, mock_get):
		frappe.db.set_single_value("Accounts Settings", "allow_stale", 1)
		self.disable_provider()
		frappe.get_doc(
			doctype="Currency Exchange",
			date="2031-03-10",
			from_currency="EUR",
			to_currency="INR",
			exchange_rate=82,
			for_buying=1,
			for_selling=0,
		).insert()

		self.assertAlmostEqual(get_exchange_rate("INR", "EUR", "2031-03-10"), 1 / 82)

	def test_reverse_record_flips_buying_selling_side(self, mock_get):
		frappe.db.set_single_value("Accounts Settings", "allow_stale", 1)
		self.disable_provider()
		for from_currency, for_buying, for_selling, rate, args in (
			("GBP", 0, 1, 82, "for_buying"),
			("EUR", 1, 0, 90, "for_selling"),
		):
			frappe.get_doc(
				doctype="Currency Exchange",
				date="2031-03-10",
				from_currency=from_currency,
				to_currency="INR",
				exchange_rate=rate,
				for_buying=for_buying,
				for_selling=for_selling,
			).insert()

			self.assertAlmostEqual(get_exchange_rate("INR", from_currency, "2031-03-10", args), 1 / rate)

	def test_direct_record_wins_over_reverse_record(self, mock_get):
		frappe.db.set_single_value("Accounts Settings", "allow_stale", 1)
		self.disable_provider()
		for from_currency, to_currency, rate, date in (
			("USD", "INR", 82, "2031-03-10"),
			("INR", "USD", 0.0125, "2031-03-09"),
		):
			frappe.get_doc(
				doctype="Currency Exchange",
				date=date,
				from_currency=from_currency,
				to_currency=to_currency,
				exchange_rate=rate,
				for_buying=1,
				for_selling=0,
			).insert()

		self.assertEqual(get_exchange_rate("INR", "USD", "2031-03-10"), 0.0125)

	def test_no_record_in_either_direction(self, mock_get):
		self.disable_provider()
		self.assertEqual(get_exchange_rate("CHF", "JPY", "2031-03-10"), 0.0)

	def disable_provider(self):
		previous = frappe.db.get_single_value("Currency Exchange Settings", "disabled")
		self.addCleanup(frappe.db.set_single_value, "Currency Exchange Settings", "disabled", previous)
		frappe.db.set_single_value("Currency Exchange Settings", "disabled", 1)
