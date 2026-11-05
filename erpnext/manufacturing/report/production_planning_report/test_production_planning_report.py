# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.report.production_planning_report.production_planning_report import execute
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"


class TestProductionPlanningReport(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

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
