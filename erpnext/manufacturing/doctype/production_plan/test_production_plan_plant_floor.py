import frappe
from frappe.utils import nowdate

from erpnext.manufacturing.doctype.plant_floor.test_plant_floor import (
	FINISHED_GOODS,
	STORE,
	make_ketchup_plant,
)
from erpnext.manufacturing.doctype.production_plan.services.material_request import (
	get_items_for_material_requests,
)
from erpnext.manufacturing.doctype.production_plan.services.planning_queries import (
	get_item_data,
	get_sales_orders,
)
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.material_request.test_material_request import make_material_request_for_items
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.tests.utils import ERPNextTestSuite

KETCHUP = "_Test Ketchup Bottle"


class TestProductionPlanPlantFloor(ERPNextTestSuite):
	def setUp(self):
		self.plant_floor = make_ketchup_plant()

	def test_sales_order_item_without_bom_comes_in_with_plant_floor(self):
		sales_order = make_sales_order(item_code=KETCHUP, qty=2000)
		open_orders = get_sales_orders(new_plan("Sales Order", item_code=KETCHUP))
		self.assertIn(sales_order.name, [row.name for row in open_orders])

		frappe.clear_messages()
		plan = make_plan(sales_order)
		row = plan.po_items[0]
		self.assertFalse(row.bom_no)
		self.assertNotIn("Default BOM", str(frappe.message_log))
		self.assertEqual(
			(row.item_code, row.plant_floor, row.planned_qty), (KETCHUP, self.plant_floor.name, 2000)
		)

		plan.insert()
		self.assertEqual(plan.po_items[0].warehouse, FINISHED_GOODS)

	def test_combined_sales_orders_make_one_plant_floor_row(self):
		plan = make_plan(
			*[make_sales_order(item_code=KETCHUP, qty=qty) for qty in (1200, 800)], combine_items=1
		)

		self.assertEqual(
			[(row.plant_floor, row.planned_qty) for row in plan.po_items], [(self.plant_floor.name, 2000)]
		)
		self.assertEqual(sorted(row.qty for row in plan.prod_plan_references), [800, 1200])

	def test_material_request_item_without_bom_comes_in_with_plant_floor(self):
		material_request = make_material_request_for_items(
			[KETCHUP], material_request_type="Manufacture", qty=500
		)
		plan = new_plan("Material Request")
		plan.get_pending_material_requests()
		self.assertIn(material_request.name, [row.material_request for row in plan.material_requests])

		plan.set("material_requests", [{"material_request": material_request.name}])
		plan.get_items()
		self.assertEqual(
			[(row.plant_floor, row.planned_qty) for row in plan.po_items], [(self.plant_floor.name, 500)]
		)

	def test_item_data_offers_plant_floor_when_item_has_no_bom(self):
		item_data = get_item_data(KETCHUP, "_Test Company")

		self.assertFalse(item_data["bom_no"])
		self.assertEqual(item_data["plant_floor"], self.plant_floor.name)

	def test_plant_floor_must_make_the_item_and_be_set_up(self):
		plan = make_plan(make_sales_order(item_code=KETCHUP, qty=2000))
		plan.po_items[0].item_code = "_Test Ketchup Sugar"
		self.assertRaisesRegex(frappe.ValidationError, "makes", plan.insert)

		self.plant_floor.db_set("batch_size", 0)
		plan = make_plan(make_sales_order(item_code=KETCHUP, qty=2000))
		self.assertRaisesRegex(frappe.ValidationError, "batch size", plan.insert)

	def test_work_order_from_plan_is_made_on_the_plant_floor(self):
		plan = make_plan(make_sales_order(item_code=KETCHUP, qty=2000))
		plan.insert()
		plan.get_sub_assembly_items()
		self.assertFalse(plan.sub_assembly_items)

		plan.submit()
		plan.make_work_order()
		work_order = frappe.get_doc("Work Order", {"production_plan": plan.name})

		self.assertFalse(work_order.bom_no)
		self.assertEqual(
			(
				work_order.plant_floor,
				work_order.qty,
				work_order.production_plan_item,
				work_order.fg_warehouse,
			),
			(self.plant_floor.name, 2000, plan.po_items[0].name, FINISHED_GOODS),
		)
		self.assertEqual(len(work_order.operations), 3)
		required = {row.item_code: row.required_qty for row in work_order.required_items}
		self.assertEqual(required["_Test Tomato Paste"], 500)

		work_order.submit()
		self.assertEqual(
			frappe.db.get_value("Production Plan Item", plan.po_items[0].name, "ordered_qty"), 2000
		)

	def test_raw_materials_follow_the_plant_floor_formula(self):
		plan = make_plan(make_sales_order(item_code=KETCHUP, qty=2000))
		plan.insert()

		mr_items = get_items_for_material_requests(plan.as_dict())
		self.assertEqual(
			sorted((row["item_code"], row["quantity"], row["warehouse"]) for row in mr_items),
			[
				("_Test Ketchup PET Bottle", 2000, STORE),
				("_Test Ketchup Sugar", 375, STORE),
				("_Test Process Water", 375, STORE),
				("_Test Tomato Paste", 500, STORE),
			],
		)
		self.assertEqual({row["main_item_code"] for row in mr_items}, {KETCHUP})

	def test_raw_materials_use_for_warehouse_and_projected_stock(self):
		warehouse = create_warehouse("_Test Plan Ketchup Store")
		make_stock_entry(item_code="_Test Tomato Paste", target=warehouse, qty=300, basic_rate=10)
		plan = make_plan(
			make_sales_order(item_code=KETCHUP, qty=2000),
			for_warehouse=warehouse,
			ignore_existing_ordered_qty=1,
		)
		plan.insert()

		mr_items = get_items_for_material_requests(plan.as_dict())
		quantities = {row["item_code"]: (row["quantity"], row["warehouse"]) for row in mr_items}
		self.assertEqual(quantities["_Test Tomato Paste"], (200, warehouse))
		self.assertEqual(quantities["_Test Ketchup PET Bottle"], (2000, warehouse))


def new_plan(get_items_from, **values):
	return frappe.new_doc(
		"Production Plan",
		company="_Test Company",
		posting_date=nowdate(),
		get_items_from=get_items_from,
		**values,
	)


def make_plan(*sales_orders, **values):
	plan = new_plan("Sales Order", **values)
	for sales_order in sales_orders:
		plan.append("sales_orders", {"sales_order": sales_order.name})
	plan.get_items()
	return plan
