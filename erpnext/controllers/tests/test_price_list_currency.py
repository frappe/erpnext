# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests import UnitTestCase

from erpnext.controllers.accounts_controller import AccountsController


class TestPriceListCurrency(UnitTestCase):
	def test_price_list_currency_transition(self):
		cases = (
			("USD", "CDF", 1, 0.000444444, True),
			("EUR", "CDF", 1.2, 0.000444444, True),
			("CDF", "USD", 0.000444444, 1, False),
			("CDF", "CDF", 0.0005, 0.0005, False),
			("CDF", "CDF", 0, 0.000444444, True),
			(None, "CDF", 0.0005, 0.0005, False),
		)
		for direction in ("Selling", "Buying"):
			for previous_currency, currency, previous_rate, expected_rate, fetch_rate in cases:
				with self.subTest(
					direction=direction,
					previous_currency=previous_currency,
					currency=currency,
					previous_rate=previous_rate,
				):
					doc = frappe._dict(
						meta=Mock(),
						posting_date="2026-09-18",
						selling_price_list="New Selling Price List",
						buying_price_list="New Buying Price List",
						price_list_currency=previous_currency,
						plc_conversion_rate=previous_rate,
						company_currency="USD",
						currency="CDF",
						conversion_rate=0.000444444,
					)
					with (
						patch("erpnext.controllers.accounts_controller.frappe") as mock_frappe,
						patch(
							"erpnext.controllers.accounts_controller.get_exchange_rate",
							return_value=0.000444444,
						) as exchange_rate,
					):
						mock_frappe.db.get_value.return_value = currency
						mock_frappe.db.get_single_value.return_value = False
						AccountsController.set_price_list_currency(doc, direction)
						self.assertEqual(doc.price_list_currency, currency)
						self.assertEqual(doc.plc_conversion_rate, expected_rate)
						self.assertEqual(doc.conversion_rate, 0.000444444)
						if fetch_rate:
							exchange_rate.assert_called_once_with(
								currency, "USD", "2026-09-18", f"for_{direction.lower()}"
							)
						else:
							exchange_rate.assert_not_called()
