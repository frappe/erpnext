# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, nowdate

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry, make_stock_return_entry
from erpnext.manufacturing.report.work_order_consumed_materials.work_order_consumed_materials import execute
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry import test_stock_entry


class TestWorkOrderConsumedMaterials(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

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

	def get_wo_rows(self, data, work_order):
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

	@change_settings("Global Defaults", {"default_company": "_Test Company"})
	def test_returned_qty_is_in_the_stock_uom(self):
		wo, material = self.make_work_order_with_return()

		rows = self.get_wo_rows(self.run_report(name=wo.name), wo.name)

		self.assertEqual([(row.raw_material_item_code, row.returned_qty) for row in rows], [(material, 2)])

	@change_settings("Global Defaults", {"default_company": "_Test Company"})
	def test_consumed_qty_leaves_out_the_returned_qty(self):
		wo, material = self.make_work_order_with_return()

		rows = self.get_wo_rows(self.run_report(name=wo.name), wo.name)

		self.assertEqual(
			[(row.raw_material_item_code, row.consumed_qty, row.extra_consumed_qty) for row in rows],
			[(material, 8, 0)],
		)
