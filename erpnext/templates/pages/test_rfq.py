# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe

from erpnext.buying.doctype.request_for_quotation.test_request_for_quotation import (
	make_request_for_quotation,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestRFQPage(ERPNextTestSuite):
	def test_draft_rfq_page_is_not_permitted(self):
		from erpnext.templates.pages.rfq import get_context

		rfq = make_request_for_quotation(do_not_submit=True)
		with patch.dict(frappe.form_dict, {"doctype": "Request for Quotation", "name": rfq.name}):
			self.assertRaises(frappe.PermissionError, get_context, frappe._dict())

	def test_portal_user_of_several_suppliers_sees_each_suppliers_rfqs(self):
		from erpnext.controllers.website_list_for_contact import rfq_transaction_list
		from erpnext.templates.pages.rfq import get_supplier

		first_rfq = make_request_for_quotation(supplier_data=[{"supplier": "_Test Supplier"}])
		second_rfq = make_request_for_quotation(supplier_data=[{"supplier": "_Test Supplier 2"}])
		shared_rfq = make_request_for_quotation(
			supplier_data=[{"supplier": "_Test Supplier"}, {"supplier": "_Test Supplier 2"}]
		)

		listed = rfq_transaction_list(
			"Request for Quotation Supplier",
			"Request for Quotation",
			["_Test Supplier", "_Test Supplier 2"],
			0,
			100,
		)
		listed_names = [row.name for row in listed]
		self.assertTrue({first_rfq.name, second_rfq.name} <= set(listed_names))
		self.assertEqual(listed_names.count(shared_rfq.name), 1)

		with (
			patch(
				"erpnext.templates.pages.rfq.get_customers_suppliers",
				return_value=(None, ["_Test Supplier", "_Test Supplier 2"]),
			),
			patch.dict(frappe.form_dict, {"doctype": "Request for Quotation", "name": second_rfq.name}),
		):
			self.assertEqual(get_supplier(), "_Test Supplier 2")
