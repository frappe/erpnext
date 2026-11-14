# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt

from erpnext.setup.utils import get_exchange_rate
from erpnext.tests.utils import ERPNextTestSuite

DATE = "2026-01-15"


class TestPeggedCurrencies(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value("Accounts Settings", "allow_pegged_currencies_exchange_rates", 1)
		pegged = frappe.get_single("Pegged Currencies")
		pegged.pegged_currency_item = []
		for source, ratio in (("AED", "3.6725"), ("SAR", "3.75")):
			pegged.append(
				"pegged_currency_item",
				{"source_currency": source, "pegged_against": "USD", "pegged_exchange_rate": ratio},
			)
		pegged.save()

	def rate(self, from_currency, to_currency):
		return flt(get_exchange_rate(from_currency, to_currency, DATE), 6)

	def test_rate_against_the_pegged_currency(self):
		# 1 USD = 3.6725 AED
		self.assertEqual(self.rate("USD", "AED"), 3.6725)
		self.assertEqual(self.rate("AED", "USD"), flt(1 / 3.6725, 6))
		self.assertEqual(self.rate("AED", "SAR"), flt(3.75 / 3.6725, 6))

	def test_rate_through_the_pegged_currency_record(self):
		frappe.db.set_single_value("Currency Exchange Settings", "disabled", 1)
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": DATE,
				"from_currency": "USD",
				"to_currency": "INR",
				"exchange_rate": 85,
				"for_buying": 1,
				"for_selling": 1,
			}
		).insert()

		self.assertEqual(self.rate("AED", "INR"), flt(85 / 3.6725, 6))
		# fixed pegs need no provider
		self.assertEqual(self.rate("USD", "AED"), 3.6725)

	def test_invalid_rows_are_refused(self):
		for row in (
			{"source_currency": "OMR", "pegged_against": "USD", "pegged_exchange_rate": "0"},
			{"source_currency": "OMR", "pegged_against": "USD", "pegged_exchange_rate": "0,3845"},
			{"source_currency": "OMR", "pegged_against": "OMR", "pegged_exchange_rate": "1"},
			{"source_currency": "AED", "pegged_against": "USD", "pegged_exchange_rate": "3.6725"},
		):
			with self.subTest(row=row):
				pegged = frappe.get_single("Pegged Currencies")
				pegged.append("pegged_currency_item", row)
				self.assertRaises(frappe.ValidationError, pegged.save)
