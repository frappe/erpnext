# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import today

from erpnext.accounts.utils import get_fiscal_year
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.report.purchase_order_trends.purchase_order_trends import execute
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.tests.utils import ERPNextTestSuite


class TestPurchaseOrderTrends(ERPNextTestSuite):
	def test_based_on_project_leaves_out_rows_without_a_project(self):
		project = make_project({"project_name": "_Test PO Trends Project"}).name
		po = create_purchase_order(qty=2, rate=100, transaction_date=today(), do_not_save=True)
		po.items[0].project = project
		po.insert().submit()
		create_purchase_order(qty=3, rate=100, transaction_date=today())

		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": get_fiscal_year(today())[0],
				"period": "Monthly",
				"based_on": "Project",
			}
		)

		projects = [row[0] for row in execute(filters)[1]]
		self.assertIn(project, projects)
		self.assertTrue(all(projects))
