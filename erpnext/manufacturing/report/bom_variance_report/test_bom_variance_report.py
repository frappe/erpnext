# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission

from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
from erpnext.manufacturing.report.bom_variance_report.bom_variance_report import execute, get_work_orders
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestBOMVarianceReport(ERPNextTestSuite):
	def setUp(self):
		self.production_item = "_Test FG Item"
		self.warehouse = "_Test Warehouse - _TC"
		self.bom_no = frappe.db.get_value(
			"BOM", {"item": self.production_item, "is_active": 1, "is_default": 1}
		)
		self.raw_materials = self.get_bom_raw_materials()

		# allow over-production so a Work Order can produce more than planned; ERPNextTestSuite
		# rolls this back at tearDown, so no manual restore is needed
		frappe.db.set_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order", 100)

	def get_bom_raw_materials(self):
		return {
			row.item_code: row.qty
			for row in frappe.get_all(
				"BOM Item", filters={"parent": self.bom_no}, fields=["item_code", "qty"]
			)
		}

	def create_over_produced_work_order(self, ordered_qty=2, produced_qty=3, extra_consumption=0):
		work_order = make_wo_order_test_record(
			item=self.production_item,
			qty=ordered_qty,
			source_warehouse=self.warehouse,
			skip_transfer=1,
		)

		for item_code in self.raw_materials:
			test_stock_entry.make_stock_entry(
				item_code=item_code, target=self.warehouse, qty=100, basic_rate=100
			)

		stock_entry = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", produced_qty))
		for row in stock_entry.items:
			if row.s_warehouse:
				row.qty += extra_consumption
		stock_entry.submit()

		work_order.reload()
		self.assertEqual(work_order.produced_qty, produced_qty)
		return work_order

	def run_report(self, **extra):
		filters = frappe._dict({"bom_no": self.bom_no, **extra})
		return execute(filters)[1]

	def test_work_order_produced_exactly_on_plan_is_listed(self):
		work_order = self.create_over_produced_work_order(ordered_qty=2, produced_qty=2)

		data = self.run_report(work_order=work_order.name)

		matched = [row for row in data if row.get("work_order") == work_order.name]
		self.assertEqual(len(matched), 1)
		raw_material_rows = {
			row.get("raw_material_code"): row for row in data if row.get("raw_material_code")
		}
		for item_code, per_unit_qty in self.raw_materials.items():
			self.assertEqual(raw_material_rows[item_code].get("required_qty"), per_unit_qty * 2)
			self.assertEqual(raw_material_rows[item_code].get("consumed_qty"), per_unit_qty * 2)

	def make_work_order_with_loss(self, bom_no, production_item):
		work_order = make_wo_order_test_record(
			item=production_item, bom_no=bom_no, qty=2, source_warehouse=self.warehouse, skip_transfer=1
		)
		for item_code in self.raw_materials:
			test_stock_entry.make_stock_entry(
				item_code=item_code, target=self.warehouse, qty=100, basic_rate=100
			)
		stock_entry = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 2))
		for row in stock_entry.items:
			if row.is_finished_item:
				row.qty = 1
		stock_entry.submit()
		return work_order

	def material_rows(self, work_order):
		data = self.run_report(work_order=work_order.name)
		return {row.get("raw_material_code"): row for row in data if row.get("raw_material_code")}

	def test_planned_process_loss_is_not_excess_consumption(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		from erpnext.stock.doctype.item.test_item import make_item

		production_item = make_item(properties={"is_stock_item": 1}).name
		bom = make_bom(
			item=production_item,
			raw_materials=list(self.raw_materials),
			process_loss_percentage=50,
			quantity=2,
		)
		work_order = self.make_work_order_with_loss(bom.name, production_item)

		for row in self.material_rows(work_order).values():
			self.assertEqual(row.get("required_qty"), row.get("consumed_qty"))

	def test_unplanned_process_loss_shows_as_variance(self):
		work_order = self.make_work_order_with_loss(self.bom_no, self.production_item)

		rows = self.material_rows(work_order)
		for item_code, per_unit_qty in self.raw_materials.items():
			self.assertEqual(rows[item_code].get("required_qty"), per_unit_qty)
			self.assertEqual(rows[item_code].get("consumed_qty"), per_unit_qty * 2)

	def test_work_order_consuming_more_than_bom_shows_variance(self):
		work_order = self.create_over_produced_work_order(ordered_qty=2, produced_qty=2, extra_consumption=1)

		data = self.run_report(work_order=work_order.name)

		raw_material_rows = {
			row.get("raw_material_code"): row for row in data if row.get("raw_material_code")
		}
		for item_code, per_unit_qty in self.raw_materials.items():
			self.assertEqual(raw_material_rows[item_code].get("required_qty"), per_unit_qty * 2)
			self.assertEqual(raw_material_rows[item_code].get("consumed_qty"), per_unit_qty * 2 + 1)

	def test_material_rows_of_hidden_work_orders_are_left_out(self):
		permitted = self.create_over_produced_work_order(ordered_qty=2, produced_qty=2)
		hidden = self.create_over_produced_work_order(ordered_qty=2, produced_qty=2)

		user = create_user("bom-variance-work-order@example.com", "Manufacturing User")
		add_user_permission("Work Order", permitted.name, user.name)
		with self.set_user(user.name):
			data = self.run_report()

		work_orders = [row.get("work_order") for row in data if row.get("work_order")]
		self.assertIn(permitted.name, work_orders)
		self.assertNotIn(hidden.name, work_orders)
		self.assertEqual(
			len([row for row in data if row.get("raw_material_code")]),
			len(self.raw_materials) * len(work_orders),
		)

	def test_work_order_search_follows_permissions(self):
		permitted = self.create_over_produced_work_order(ordered_qty=2, produced_qty=2)
		hidden = self.create_over_produced_work_order(ordered_qty=2, produced_qty=2)

		def search(user):
			with self.set_user(user):
				rows = get_work_orders("Work Order", "", "name", 0, 1000, {"bom_no": self.bom_no})
			return {row[0] for row in rows}

		restricted = create_user("bom-variance-search@example.com", "Manufacturing User")
		add_user_permission("Work Order", permitted.name, restricted.name)
		names = search(restricted.name)
		self.assertIn(permitted.name, names)
		self.assertNotIn(hidden.name, names)

		accounts_user = create_user("bom-variance-accounts@example.com", "Accounts User")
		self.assertRaises(frappe.PermissionError, search, accounts_user.name)
