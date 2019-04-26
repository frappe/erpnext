# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import unittest
from datetime import datetime
import frappe
from erpnext.buying.report.procurement_tracker.procurement_tracker import execute
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt, make_purchase_invoice

class TestProcurementTracker(unittest.TestCase):
	maxDiff = None
	def test_result_for_procurement_tracker(self):
		mr = make_material_request()
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.get("items")[0].cost_center = "_Test Cost Center - _TC"
		po.submit()
		pr = make_purchase_receipt(po.name)
		pr.submit()
		frappe.db.commit()
		date_obj = datetime.date(datetime.now())

		report = execute()
		expected_data = {
			"material_request_date": date_obj,
			"cost_center": "_Test Cost Center - _TC",
			"project": None,
			"requesting_site": "_Test Warehouse - _TC",
			"requestor": "Administrator",
			"material_request_no": mr.name,
			"description": '_Test Item 1',
			"quantity": 10.0,
			"unit_of_measurement": "_Test UOM",
			"status": "To Bill",
			"purchase_order_date": date_obj,
			"purchase_order": po.name,
			"supplier": "_Test Supplier",
			"estimated_cost": 0.0,
			"actual_cost": None,
			"purchase_order_amt": 0.0,
			"purchase_order_amt_in_company_currency": 0.0,
			"expected_delivery_date": date_obj,
			"actual_delivery_date": date_obj
		}
		length = len(report[1])
		self.assertEqual(expected_data, report[1][length-1])