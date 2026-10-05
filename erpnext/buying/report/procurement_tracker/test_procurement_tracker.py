# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.tests.utils import FrappeTestCase

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.report.procurement_tracker.procurement_tracker import execute


class TestProcurementTracker(FrappeTestCase):
	def test_uninvoiced_actual_cost_is_in_company_currency(self):
		po = create_purchase_order(supplier="_Test Supplier USD", currency="USD", rate=10, do_not_submit=1)
		po.conversion_rate = 80
		po.submit()

		data = execute({"company": "_Test Company"})[1]
		row = next(row for row in data if row.get("purchase_order") == po.name)
		self.assertEqual(row["actual_cost"], 8000)
