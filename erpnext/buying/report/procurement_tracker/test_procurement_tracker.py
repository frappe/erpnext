# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import unittest
from frappe.utils import nowdate, add_months
from erpnext.buying.report.procurement_tracker.procurement_tracker import execute
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt, make_purchase_invoice

class TestProcurementTracker(unittest.TestCase):
	def test_result_for_procurement_tracker(self):
		mr = make_material_request()
		mr.submit()
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.get("items")[0].cost_center = "_Test Cost Center - _TC"
		po.get("items")[0].amount = 1000
		po.get("items")[0].base_amount = 1000
		po.submit()
		pr = make_purchase_receipt(po.name)
		pr.submit()
		pi = make_purchase_invoice(po.name)
		pi.submit()

		report = execute()
		expected_data = {
			"material_request_date": nowdate(),
			"cost_center": "_Test Cost Center - _TC",
			"project": '',
			"requesting_site": "_Test Warehouse - _TC",
			"requestor": "Administrator",
			"material_request_no": mr.name,
			"description": '_Test Item 1',
			"quantity": 10,
			"unit_of_measurement": "_Test UOM",
			"status": "To Receive and Bill",
			"purchase_order_date": nowdate(),
			"purchase_order": po.name,
			"supplier": "_Test Supplier",
			"estimated_cost": 0.0,
			"actual_cost": 1000,
			"purchase_order_amt": 1000,
			"purchase_order_amt_usd": 1000,
			"expected_delivery_date": nowdate(),
			"actual_delivery_date": nowdate()
		}
		length = len(report[1])
		self.assertEqual(expected_data, report[1][length-1])