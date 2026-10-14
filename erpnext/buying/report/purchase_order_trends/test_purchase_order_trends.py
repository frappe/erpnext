# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.accounts.utils import get_fiscal_year
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.report.purchase_order_trends.purchase_order_trends import execute
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.stock.doctype.item.test_item import create_item


class TestPurchaseOrderTrends(FrappeTestCase):
	def test_restricted_user_sees_only_permitted_orders(self):
		item = create_item("_Test PO Trends Permission Item").name
		create_purchase_order(item_code=item, supplier="_Test Supplier", qty=3, rate=100)
		create_purchase_order(item_code=item, supplier="_Test Supplier 1", qty=5, rate=100)
		user = create_user("po_trends_restricted@example.com", "Purchase User").name
		add_user_permission("Supplier", "_Test Supplier", user)

		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": get_fiscal_year(today())[0],
				"period": "Monthly",
				"based_on": "Item",
			}
		)
		with self.set_user(user):
			data = execute(filters)[1]

		item_row = next(row for row in data if row[0] == item)
		self.assertEqual(item_row[-2:], [3, 300])

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
