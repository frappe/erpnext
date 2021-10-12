# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import unittest
from datetime import datetime

import frappe

from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.buying.report.procurement_tracker.procurement_tracker import execute
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse


class TestProcurementTracker(unittest.TestCase):
	def test_result_for_procurement_tracker(self):
		filters = {
			'company': '_Test Procurement Company',
			'cost_center': 'Main - _TPC'
		}
		expected_data = self.generate_expected_data()
		report = execute(filters)

		length = len(report[1])
		self.assertEqual(expected_data, report[1][length-1])

	def generate_expected_data(self):
		if not frappe.db.exists("Company", "_Test Procurement Company"):
			frappe.get_doc(dict(
				doctype="Company",
				company_name="_Test Procurement Company",
				abbr="_TPC",
				default_currency="INR",
				country="Pakistan"
				)).insert()
		warehouse = create_warehouse("_Test Procurement Warehouse", company="_Test Procurement Company")
		mr = make_material_request(company="_Test Procurement Company", warehouse=warehouse, cost_center="Main - _TPC")
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.get("items")[0].cost_center = "Main - _TPC"
		po.submit()
		pr = make_purchase_receipt(po.name)
		pr.get("items")[0].cost_center = "Main - _TPC"
		pr.submit()
		date_obj = datetime.date(datetime.now())

		po.load_from_db()

		expected_data = {
			"material_request_date": date_obj,
			"cost_center": "Main - _TPC",
			"project": None,
			"requesting_site": "_Test Procurement Warehouse - _TPC",
			"requestor": "Administrator",
			"material_request_no": mr.name,
			"item_code": '_Test Item',
			"quantity": 10.0,
			"unit_of_measurement": "_Test UOM",
			"status": "To Bill",
			"purchase_order_date": date_obj,
			"purchase_order": po.name,
			"supplier": "_Test Supplier",
			"estimated_cost": 0.0,
			"actual_cost": 0.0,
			"purchase_order_amt": po.net_total,
			"purchase_order_amt_in_company_currency": po.base_net_total,
			"expected_delivery_date": date_obj,
			"actual_delivery_date": date_obj
		}

		return expected_data
