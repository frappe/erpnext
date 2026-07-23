# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import (
	create_landed_cost_voucher,
)
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.report.landed_cost_report.landed_cost_report import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestLandedCostReport(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": add_days(today(), -1),
				"to_date": add_days(today(), 1),
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_landed_cost_applied_to_receipt(self):
		pr = make_purchase_receipt(
			item_code="_Test Item",
			supplier="_Test Supplier",
			company="_Test Company",
			warehouse="Stores - _TC",
			qty=10,
			rate=100,
		)

		charges = 75
		lcv = create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company, charges=charges)

		rows = self.run_report(raw_material_voucher_no=pr.name)

		matching = [row for row in rows if row.get("name") == lcv.name]
		self.assertTrue(matching, msg=f"No report row found for LCV {lcv.name}")

		row = matching[0]
		self.assertEqual(row.get("landed_cost"), charges)
		self.assertEqual(row.get("voucher_type"), "Purchase Receipt")
		self.assertEqual(row.get("voucher_no"), pr.name)
