# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

from frappe.tests.utils import FrappeTestCase


class TestWebsiteListForContact(FrappeTestCase):
	def test_get_list_context_currency_symbols(self):
		# get_list_context builds the enabled-currency symbol map via frappe.get_all (converted from
		# raw SQL). Exercises that query and asserts a known enabled currency is present.
		from erpnext.controllers.website_list_for_contact import get_list_context

		context = get_list_context()

		symbols = json.loads(context["currency_symbols"])
		self.assertIsInstance(symbols, dict)
		self.assertIn("USD", symbols)

	def test_rfq_transaction_list_returns_supplier_rfq(self):
		# rfq_transaction_list filters RFQs by the supplier (parties[0]) and uses SELECT DISTINCT with
		# ORDER BY creation -- both must be valid on Postgres, and the supplier filter must compare to the
		# party value (not a stray `party[0]` column reference).
		from erpnext.buying.doctype.request_for_quotation.test_request_for_quotation import (
			make_request_for_quotation,
		)
		from erpnext.controllers.website_list_for_contact import rfq_transaction_list

		rfq = make_request_for_quotation()
		supplier = rfq.suppliers[0].supplier

		rows = rfq_transaction_list(
			"Request for Quotation Supplier", "Request for Quotation", [supplier], 0, 20
		)
		self.assertIn(rfq.name, [row.name for row in rows])
