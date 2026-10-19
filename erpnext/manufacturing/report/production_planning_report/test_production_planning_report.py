# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import today

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry as make_work_order_entry
from erpnext.manufacturing.report.production_planning_report.production_planning_report import execute
from erpnext.selling.doctype.sales_order.test_sales_order import create_dn_against_so, make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"


class TestProductionPlanningReport(ERPNextTestSuite):
	def run_report(self, based_on, docnames, **filters):
		order_by = {"Sales Order": "Delivery Date", "Material Request": "Required Date"}.get(
			based_on, "Planned Start Date"
		)
		return execute(
			{"company": COMPANY, "based_on": based_on, "docnames": docnames, "order_by": order_by, **filters}
		)[1]

	def make_fg_with_bom(self, materials):
		fg_item = make_item(properties={"is_stock_item": 1}).name
		bom = make_bom(item=fg_item, raw_materials=[d[0] for d in materials], do_not_save=True)
		for row, (_item_code, qty, uom, conversion_factor) in zip(bom.items, materials, strict=True):
			row.update({"qty": qty, "uom": uom or row.uom, "conversion_factor": conversion_factor})
		bom.save()
		bom.submit()
		return fg_item

	def test_required_qty_is_in_the_stock_uom(self):
		material = make_item(
			properties={"is_stock_item": 1, "uoms": [{"uom": "Box", "conversion_factor": 12}]}
		).name
		fg_item = self.make_fg_with_bom([(material, 1, "Box", 12)])
		sales_order = make_sales_order(item_code=fg_item, qty=5, warehouse=WAREHOUSE)

		data = self.run_report("Sales Order", [sales_order.name])

		self.assertEqual([d.required_qty for d in data if d.get("item_code") == material], [60])

	def test_material_without_default_warehouse_uses_the_order_warehouse(self):
		other_warehouse = "_Test Warehouse 1 - _TC"
		materials = [
			make_item(
				properties={
					"is_stock_item": 1,
					"item_defaults": [{"company": COMPANY, "default_warehouse": other_warehouse}],
				}
			).name,
			make_item(properties={"is_stock_item": 1}).name,
			make_item(properties={"is_stock_item": 1}).name,
		]
		for material in materials:
			frappe.db.delete("Item Default", {"parent": material, "default_warehouse": WAREHOUSE})
			make_stock_entry(item_code=material, target=WAREHOUSE, qty=100, basic_rate=10)
		fg_item = self.make_fg_with_bom([(material, 1, None, 1) for material in materials])
		sales_order = make_sales_order(item_code=fg_item, qty=5, warehouse=WAREHOUSE)

		data = self.run_report("Sales Order", [sales_order.name])

		rows = {d.item_code: (d.warehouse, d.allotted_qty) for d in data if d.get("item_code")}
		self.assertEqual(rows[materials[0]], (other_warehouse, 0))
		self.assertEqual(rows[materials[1]], (WAREHOUSE, 5))
		self.assertEqual(rows[materials[2]], (WAREHOUSE, 5))

	def required_qty(self, data, item_code):
		return sum(d.required_qty for d in data if d.get("item_code") == item_code)

	def test_only_pending_quantities_are_planned(self):
		material = make_item(properties={"is_stock_item": 1}).name
		fg_item = self.make_fg_with_bom([(material, 2, None, 1)])
		make_stock_entry(item_code=fg_item, target=WAREHOUSE, qty=6, basic_rate=100)

		sales_order = make_sales_order(item_code=fg_item, qty=10, warehouse=WAREHOUSE)
		create_dn_against_so(sales_order.name, delivered_qty=6)
		data = self.run_report("Sales Order", [sales_order.name])
		self.assertEqual([d.qty_to_manufacture for d in data if d.get("production_item")], [4])
		self.assertEqual(self.required_qty(data, material), 8)

		material_request = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Manufacture",
				"company": COMPANY,
				"schedule_date": today(),
				"items": [
					{"item_code": fg_item, "qty": 10, "schedule_date": today(), "warehouse": WAREHOUSE}
				],
			}
		).insert()
		material_request.submit()
		work_order = make_wo_order_test_record(
			item=fg_item, qty=7, source_warehouse=WAREHOUSE, do_not_submit=True
		)
		work_order.material_request = material_request.name
		work_order.material_request_item = material_request.items[0].name
		work_order.submit()
		data = self.run_report("Material Request", [material_request.name])
		self.assertEqual([d.qty_to_manufacture for d in data if d.get("production_item")], [3])
		self.assertEqual(self.required_qty(data, material), 6)

		make_stock_entry(item_code=material, target=WAREHOUSE, qty=14, basic_rate=10)
		frappe.get_doc(
			make_work_order_entry(work_order.name, "Material Transfer for Manufacture", 7)
		).submit()
		data = self.run_report("Work Order", [work_order.name])
		self.assertEqual(self.required_qty(data, material), 0)

	def test_extra_transfer_leaves_no_negative_demand(self):
		material = make_item(properties={"is_stock_item": 1}).name
		fg_item = self.make_fg_with_bom([(material, 2, None, 1)])
		orders = [
			make_wo_order_test_record(item=fg_item, qty=5, source_warehouse=WAREHOUSE) for _order in range(2)
		]
		frappe.db.set_value(
			"Work Order Item", {"parent": orders[0].name, "item_code": material}, "transferred_qty", 12
		)

		data = self.run_report("Work Order", [order.name for order in orders])

		self.assertEqual(self.required_qty(data, material), 10)

	def test_returned_material_is_needed_again(self):
		material = make_item(properties={"is_stock_item": 1}).name
		fg_item = self.make_fg_with_bom([(material, 2, None, 1)])
		order = make_wo_order_test_record(item=fg_item, qty=5, source_warehouse=WAREHOUSE)
		frappe.db.set_value(
			"Work Order Item",
			{"parent": order.name, "item_code": material},
			{"transferred_qty": 10, "consumed_qty": 10, "returned_qty": 5},
		)

		data = self.run_report("Work Order", [order.name])

		self.assertEqual(self.required_qty(data, material), 5)

	def test_arrival_qty_is_in_the_stock_uom(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		material = make_item(
			properties={"is_stock_item": 1, "uoms": [{"uom": "Box", "conversion_factor": 12}]}
		).name
		fg_item = self.make_fg_with_bom([(material, 3, None, 1)])
		purchase_order = create_purchase_order(
			item_code=material, qty=2, warehouse=WAREHOUSE, do_not_save=True
		)
		purchase_order.items[0].update({"uom": "Box", "conversion_factor": 12})
		purchase_order.insert()
		purchase_order.submit()
		sales_order = make_sales_order(item_code=fg_item, qty=10, warehouse=WAREHOUSE)

		data = self.run_report("Sales Order", [sales_order.name])

		self.assertEqual(
			[(d.required_qty, d.arrival_qty) for d in data if d.get("item_code") == material], [(30, 24)]
		)
