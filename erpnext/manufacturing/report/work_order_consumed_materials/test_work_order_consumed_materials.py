# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.work_order_consumed_materials.work_order_consumed_materials import execute
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestWorkOrderConsumedMaterials(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": add_days(nowdate(), -1),
				"to_date": add_days(nowdate(), 1),
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def make_manufactured_work_order(self, qty=2):
		"""Create a submitted WO, stock its raw materials, transfer and fully manufacture it."""
		wo = make_wo_order_test_record(production_item="_Test FG Item", qty=qty, company="_Test Company")

		for item in wo.required_items:
			test_stock_entry.make_stock_entry(
				item_code=item.item_code,
				target=wo.wip_warehouse,
				qty=item.required_qty,
				basic_rate=100,
			)

		transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", qty))
		transfer.insert()
		transfer.submit()

		manufacture = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", qty))
		manufacture.insert()
		manufacture.submit()

		wo.reload()
		return wo

	def get_wo_rows(self, data, work_order):
		"""The report blanks parent fields after the first raw-material row, so match by raw
		material's parent work order instead of the (blanked) `name` column."""
		return [row for row in data if row.get("parent") == work_order]

	def test_consumed_materials_reported_after_manufacture(self):
		wo = self.make_manufactured_work_order(qty=2)

		# fully producing the WO consumes exactly the required quantity of each raw material
		self.assertEqual(wo.produced_qty, 2)

		data = self.run_report()
		rows = self.get_wo_rows(data, wo.name)

		self.assertEqual(len(rows), len(wo.required_items))

		# pair rows to required items by sorting rather than a dict keyed on item code, so
		# a BOM with two lines for the same component wouldn't silently collapse to one row
		rows_sorted = sorted(rows, key=lambda r: (r["raw_material_item_code"], r["required_qty"]))
		items_sorted = sorted(wo.required_items, key=lambda i: (i.item_code, i.required_qty))
		for row, item in zip(rows_sorted, items_sorted, strict=True):
			self.assertEqual(row["raw_material_item_code"], item.item_code)
			self.assertEqual(row["required_qty"], item.required_qty)
			self.assertEqual(row["transferred_qty"], item.required_qty)
			self.assertEqual(row["consumed_qty"], item.required_qty)
			# no over-consumption in a clean full manufacture
			self.assertEqual(row["extra_consumed_qty"], 0.0)
			self.assertEqual(row["returned_qty"], 0.0)

		# parent columns are populated on the first row only
		first = rows[0]
		self.assertEqual(first["status"], wo.status)
		self.assertEqual(first["production_item"], "_Test FG Item")
		self.assertEqual(first["qty"], 2)
		self.assertEqual(first["produced_qty"], 2)

	def test_work_order_filter_scopes_output(self):
		wo = self.make_manufactured_work_order(qty=1)

		data = self.run_report(name=wo.name)

		parents = {row.get("parent") for row in data}
		self.assertEqual(parents, {wo.name})
		self.assertTrue(data)

	def test_draft_work_order_is_excluded(self):
		# report only lists WOs in status In Process / Completed / Stopped
		draft = make_wo_order_test_record(
			production_item="_Test FG Item", qty=1, company="_Test Company", do_not_submit=True
		)

		data = self.run_report()
		self.assertNotIn(draft.name, {row.get("parent") for row in data})

	def test_date_range_filter_excludes_work_order(self):
		wo = self.make_manufactured_work_order(qty=1)

		# positive anchor: the WO shows up within the default (current) window
		self.assertIn(wo.name, {row.get("parent") for row in self.run_report()})

		# a window that ends before the WO was created must not include it
		data = self.run_report(from_date=add_days(nowdate(), -10), to_date=add_days(nowdate(), -5))
		self.assertNotIn(wo.name, {row.get("parent") for row in data})
