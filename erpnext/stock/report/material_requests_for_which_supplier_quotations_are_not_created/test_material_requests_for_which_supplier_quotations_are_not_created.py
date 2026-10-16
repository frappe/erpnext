# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import os

import frappe

from erpnext.stock.doctype.material_request.mapper import make_supplier_quotation
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.tests.utils import ERPNextTestSuite


class TestMaterialRequestsWithoutSupplierQuotations(ERPNextTestSuite):
	def get_listed_request_items(self, request):
		path = os.path.join(
			os.path.dirname(__file__), "material_requests_for_which_supplier_quotations_are_not_created.json"
		)
		query = json.load(open(path))["query"]
		return sorted(row[2] for row in frappe.db.sql(query) if row[0] == request)

	def make_request(self):
		request = make_material_request(item_code="_Test Item", qty=5, do_not_submit=True)
		request.append("items", {**request.items[0].as_dict(), "name": None, "item_code": "_Test Item 2"})
		request.submit()
		return request

	def make_quotation(self, request, item_code):
		quotation = make_supplier_quotation(request.name)
		quotation.supplier = "_Test Supplier"
		quotation.items = [row for row in quotation.items if row.item_code == item_code]
		quotation.insert()
		quotation.submit()
		return quotation

	def test_cancelled_quotation_does_not_hide_the_request(self):
		request = self.make_request()
		self.make_quotation(request, "_Test Item").cancel()

		self.assertEqual(self.get_listed_request_items(request.name), ["_Test Item", "_Test Item 2"])
