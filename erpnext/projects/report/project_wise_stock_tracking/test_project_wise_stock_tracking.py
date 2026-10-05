# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt, random_string, today

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.projects.report.project_wise_stock_tracking.project_wise_stock_tracking import execute
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestProjectWiseStockTracking(ERPNextTestSuite):
	def test_project_wise_stock_tracking(self):
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": "_Test PWST " + random_string(10),
				"status": "Open",
				"company": "_Test Company",
			}
		).insert()

		# Issued cost: a project-tagged Material Issue (t_warehouse empty) -> get_issued_items_cost.
		make_stock_entry(item_code="_Test Item", qty=10, to_warehouse="_Test Warehouse - _TC", rate=100)
		issue = make_stock_entry(
			item_code="_Test Item", qty=4, from_warehouse="_Test Warehouse - _TC", do_not_save=True
		)
		issue.project = project.name
		issue.save()
		issue.submit()
		expected_issued_cost = issue.items[0].amount

		# Purchased cost: a submitted Purchase Receipt Item tagged to the project. Inserted directly
		# (no parent receipt) so get_purchased_items_cost has data without running Purchase Receipt
		# validation (which would also pull in the landed-cost-voucher path).
		self.make_child_row("Purchase Receipt Item", "Purchase Receipt", 300, project=project.name)

		# Delivered cost: a submitted Delivery Note + line; the report joins on the parent's project.
		dn = self.make_parent_row("Delivery Note", company="_Test Company", customer="_Test Customer")
		frappe.db.set_value("Delivery Note", dn, "project", project.name)
		self.make_child_row("Delivery Note Item", "Delivery Note", 200, parent=dn)

		_columns, data = execute(filters=None)
		row = next((r for r in data if r[0] == project.name), None)
		# get_project_details must surface the freshly created project.
		self.assertIsNotNone(row, "Project row missing from report output")

		self.assertEqual(flt(row[1]), 300)  # get_purchased_items_cost (GROUP BY project)
		self.assertEqual(flt(row[2]), flt(expected_issued_cost))  # get_issued_items_cost
		self.assertEqual(flt(row[3]), 200)  # get_delivered_items_cost

	def test_issued_cost_follows_row_project(self):
		project, header_project = self.make_project(), self.make_project()
		item_code = self.make_stocked_item()
		self.make_issue(item_code, project)
		self.make_issue(item_code, project, header_project=header_project)

		self.assertEqual(self.get_report_row(project)[2], 200)
		self.assertEqual(self.get_report_row(header_project)[2], 0)

	def test_delivered_cost_includes_update_stock_invoices(self):
		project = self.make_project()
		item_code = self.make_stocked_item()
		self.submit_for_project(create_delivery_note(item_code=item_code, do_not_submit=True), project)
		self.submit_for_project(
			create_sales_invoice(item_code=item_code, update_stock=1, do_not_submit=True), project
		)

		self.assertEqual(self.get_report_row(project)[3], 200)

	def test_purchased_cost_includes_update_stock_invoices(self):
		project = self.make_project()
		item_code = make_item(properties={"is_stock_item": 1}).name
		make_purchase_invoice(item_code=item_code, qty=2, rate=100, update_stock=1, project=project)

		self.assertEqual(self.get_report_row(project)[1], 200)

	def make_project(self):
		return (
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": "_Test PWST " + random_string(10),
					"company": "_Test Company",
				}
			)
			.insert()
			.name
		)

	def make_stocked_item(self):
		item_code = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(item_code=item_code, qty=10, to_warehouse="_Test Warehouse - _TC", rate=100)
		return item_code

	def make_issue(self, item_code, project, header_project=None):
		issue = make_stock_entry(
			item_code=item_code, qty=1, from_warehouse="_Test Warehouse - _TC", do_not_save=True
		)
		issue.project = header_project
		issue.items[0].project = project
		issue.save()
		issue.submit()

	def submit_for_project(self, doc, project):
		doc.project = project
		doc.submit()

	def get_report_row(self, project):
		return next(row for row in execute()[1] if row[0] == project)

	def make_parent_row(self, doctype, **fields):
		doc = frappe.new_doc(doctype)
		for key, value in fields.items():
			doc.set(key, value)
		doc.posting_date = today()
		doc.docstatus = 1
		doc.flags.name_set = True
		doc.name = frappe.generate_hash("pwst", 12)
		doc.db_insert()
		return doc.name

	def make_child_row(self, doctype, parenttype, base_net_amount, project=None, parent=None):
		row = frappe.new_doc(doctype)
		row.parenttype = parenttype
		row.parentfield = "items"
		row.parent = parent or frappe.generate_hash("pwst", 12)
		row.idx = 1
		row.item_code = "_Test Item"
		row.item_name = "_Test Item"
		row.base_net_amount = base_net_amount
		if project:
			row.project = project
		row.docstatus = 1
		row.flags.name_set = True
		row.name = frappe.generate_hash("pwst", 12)
		row.db_insert()
		return row.name
