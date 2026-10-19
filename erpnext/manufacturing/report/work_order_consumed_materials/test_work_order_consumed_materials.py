# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import (
	close_work_order,
	make_stock_entry,
	make_stock_return_entry,
)
from erpnext.manufacturing.report.work_order_consumed_materials.work_order_consumed_materials import execute
from erpnext.stock.doctype.item.test_item import make_item
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

	def make_work_order_with_return(self):
		material = make_item(
			properties={
				"is_stock_item": 1,
				"stock_uom": "Kg",
				"uoms": [{"uom": "Kg", "conversion_factor": 1}, {"uom": "Gram", "conversion_factor": 0.001}],
			}
		).name
		fg_item = make_item(properties={"is_stock_item": 1}).name
		bom = make_bom(item=fg_item, raw_materials=[material])
		wo = make_wo_order_test_record(
			item=fg_item, bom_no=bom.name, qty=10, source_warehouse="_Test Warehouse - _TC"
		)
		test_stock_entry.make_stock_entry(
			item_code=material, target="_Test Warehouse - _TC", qty=10, basic_rate=100
		)
		frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10)).submit()
		manufacture = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
		for row in manufacture.items:
			if row.item_code == material:
				row.qty = 8
		manufacture.submit()

		return_entry = make_stock_return_entry(wo.name)
		return_entry.items[0].update({"uom": "Gram", "conversion_factor": 0.001, "qty": 2000})
		return_entry.submit()
		return wo, material

	def test_returned_qty_is_in_the_stock_uom(self):
		wo, material = self.make_work_order_with_return()

		rows = self.get_wo_rows(self.run_report(name=wo.name), wo.name)

		self.assertEqual([(row.raw_material_item_code, row.returned_qty) for row in rows], [(material, 2)])

	def test_consumed_qty_leaves_out_the_returned_qty(self):
		wo, material = self.make_work_order_with_return()

		rows = self.get_wo_rows(self.run_report(name=wo.name), wo.name)

		self.assertEqual(
			[(row.raw_material_item_code, row.consumed_qty, row.extra_consumed_qty) for row in rows],
			[(material, 8, 0)],
		)

	def test_closed_work_orders_are_listed(self):
		wo = make_wo_order_test_record(production_item="_Test FG Item", qty=10, company="_Test Company")
		for item in wo.required_items:
			test_stock_entry.make_stock_entry(
				item_code=item.item_code, target=item.source_warehouse, qty=item.required_qty, basic_rate=100
			)
		frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10)).submit()
		frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 5)).submit()
		close_work_order(wo.name, "Closed")

		rows = self.get_wo_rows(self.run_report(), wo.name)

		self.assertEqual(len(rows), len(wo.required_items))
		self.assertEqual(rows[0].status, "Closed")
