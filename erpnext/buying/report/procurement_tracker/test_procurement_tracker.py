# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import unittest
from frappe.utils import nowdate, add_months
from apps.erpnext.erpnext.buying.report.procurement_tracker.procurement_tracker import execute
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from erpnext.accounts.doctype.budget.test_budget import make_budget

class TestProcurementTracker(unittest.TestCase):
	def test_result_for_procurement_tracker(self):
		mr = make_material_request()

		po = make_purchase_order(mr.name)
		po.get("Items")[0].cost_center = "_Test Cost Center - _TC"
		po.get("Items")[0].amount = 1000
		po.submit()

		report = execute()
		expected_data = {
			"material_request_date": nowdate(),
			"cost_center": "_Test Cost Center - _TC",
			"project": '',
			"requesting_site": "_Test Warehouse - _TC",
			"requestor": "Administrator",
			"material_request_no": mr.name,
			"description": '',
			"quantity": 10,
			"unit_of_measurement": "_Test UOM",
			"status": "To Receive and Bill",
			"purchase_order_date": nowdate(),
			"purchase_order": po.name,
			"supplier": '',
			"estimated_cost": '',
			"actual_cost": '',
			"purchase_order_amt": 1000,
			"purchase_order_amt_usd": 1000,
			"expected_delivery_date": nowdate(),
			"actual_delivery_date": ''
		}
		length = len(report[1])
		self.assertEqual(expected_data, report[length])