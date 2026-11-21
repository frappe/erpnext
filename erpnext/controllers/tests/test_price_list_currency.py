# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPriceListCurrency(FrappeTestCase):
	def test_price_list_rate_side_follows_doctype(self):
		from erpnext.stock.get_item_details import get_price_list_currency_and_exchange_rate

		cases = {
			"Supplier Quotation": "for_buying",
			"Material Request": "for_buying",
			"POS Invoice": "for_selling",
			"Sales Invoice": "for_selling",
		}
		for doctype, expected_side in cases.items():
			with self.subTest(doctype=doctype):
				args = frappe._dict(
					doctype=doctype,
					price_list="Any",
					company="Any",
					transaction_date="2026-09-18",
				)
				with (
					patch(
						"erpnext.stock.get_item_details.get_price_list_details",
						return_value={"currency": "EUR"},
					),
					patch("erpnext.stock.get_item_details.get_company_currency", return_value="USD"),
					patch("erpnext.stock.get_item_details.get_exchange_rate", return_value=1.1) as rate,
				):
					get_price_list_currency_and_exchange_rate(args)
					rate.assert_called_once_with("EUR", "USD", "2026-09-18", expected_side)
