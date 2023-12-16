# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, flt, getdate, now_datetime, nowdate

from erpnext.controllers.item_variant import create_variant
from erpnext.manufacturing.doctype.production_plan.production_plan import (
	get_items_for_material_requests,
	get_non_completed_production_plans,
	get_sales_orders,
	get_warehouse_list,
)
from erpnext.manufacturing.doctype.work_order.work_order import OverProductionError
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry as make_se_from_wo
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import create_item, make_item
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)


class TestProductionPlan(FrappeTestCase):
	def setUp(self):
		for item in [
			"Test Production Item 1",
			"Subassembly Item 1",
			"Raw Material Item 1",
			"Raw Material Item 2",
		]:
			create_item(item, valuation_rate=100)

			sr = frappe.db.get_value(
				"Stock Reconciliation Item", {"item_code": item, "docstatus": 1}, "parent"
			)
			if sr:
				sr_doc = frappe.get_doc("Stock Reconciliation", sr)
				sr_doc.cancel()

		create_item("Test Non Stock Raw Material", is_stock_item=0)
		for item, raw_materials in {
			"Subassembly Item 1": ["Raw Material Item 1", "Raw Material Item 2"],
			"Test Production Item 1": [
				"Raw Material Item 1",
				"Subassembly Item 1",
				"Test Non Stock Raw Material",
			],
		}.items():
			if not frappe.db.get_value("BOM", {"item": item}):
				make_bom(item=item, raw_materials=raw_materials)

	def tearDown(self) -> None:
		frappe.db.rollback()

	def test_production_plan_mr_creation(self):
		"Test if MRs are created for unavailable raw materials."
		pln = create_production_plan(item_code="Test Production Item 1")
		self.assertTrue(len(pln.mr_items), 2)

		for row in pln.mr_items:
			row.schedule_date = add_to_date(nowdate(), days=10)

		pln.make_material_request()
		pln.reload()
		self.assertTrue(pln.status, "Material Requested")

		material_requests = frappe.get_all(
			"Material Request Item",
			fields=["distinct parent"],
			filters={"production_plan": pln.name},
			as_list=1,
		)

		self.assertTrue(len(material_requests), 2)

		for row in material_requests:
			mr_schedule_date = getdate(frappe.db.get_value("Material Request", row[0], "schedule_date"))

			expected_date = getdate(add_to_date(nowdate(), days=10))

			self.assertEqual(mr_schedule_date, expected_date)

		pln.make_work_order()
		work_orders = frappe.get_all(
			"Work Order", fields=["name"], filters={"production_plan": pln.name}, as_list=1
		)

		pln.make_work_order()
		nwork_orders = frappe.get_all(
			"Work Order", fields=["name"], filters={"production_plan": pln.name}, as_list=1
		)

		self.assertTrue(len(work_orders), len(nwork_orders))

		self.assertTrue(len(work_orders), len(pln.po_items))

		for name in material_requests:
			mr = frappe.get_doc("Material Request", name[0])
			if mr.docstatus != 0:
				mr.cancel()

		for name in work_orders:
			mr = frappe.delete_doc("Work Order", name[0])

		pln = frappe.get_doc("Production Plan", pln.name)
		pln.cancel()

	def test_production_plan_start_date(self):
		"Test if Work Order has same Planned Start Date as Prod Plan."
		planned_date = add_to_date(date=None, days=3)
		plan = create_production_plan(
			item_code="Test Production Item 1", planned_start_date=planned_date
		)
		plan.make_work_order()

		work_orders = frappe.get_all(
			"Work Order", fields=["name", "planned_start_date"], filters={"production_plan": plan.name}
		)

		self.assertEqual(work_orders[0].planned_start_date, planned_date)

		for wo in work_orders:
			frappe.delete_doc("Work Order", wo.name)

		plan.reload()
		plan.cancel()

	def test_production_plan_for_existing_ordered_qty(self):
		"""
		- Enable 'ignore_existing_ordered_qty'.
		- Test if MR Planning table pulls Raw Material Qty even if it is in stock.
		"""
		sr1 = create_stock_reconciliation(
			item_code="Raw Material Item 1", target="_Test Warehouse - _TC", qty=1, rate=110
		)
		sr2 = create_stock_reconciliation(
			item_code="Raw Material Item 2", target="_Test Warehouse - _TC", qty=1, rate=120
		)

		pln = create_production_plan(item_code="Test Production Item 1", ignore_existing_ordered_qty=1)
		self.assertTrue(len(pln.mr_items))
		self.assertTrue(flt(pln.mr_items[0].quantity), 1.0)

		sr1.cancel()
		sr2.cancel()
		pln.cancel()

	def test_production_plan_with_non_stock_item(self):
		"Test if MR Planning table includes Non Stock RM."
		pln = create_production_plan(item_code="Test Production Item 1", include_non_stock_items=1)
		self.assertTrue(len(pln.mr_items), 3)
		pln.cancel()

	def test_production_plan_without_multi_level(self):
		"Test MR Planning table for non exploded BOM."
		pln = create_production_plan(item_code="Test Production Item 1", use_multi_level_bom=0)
		self.assertTrue(len(pln.mr_items), 2)
		pln.cancel()

	def test_production_plan_without_multi_level_for_existing_ordered_qty(self):
		"""
		- Disable 'ignore_existing_ordered_qty'.
		- Test if MR Planning table avoids pulling Raw Material Qty as it is in stock for
		non exploded BOM.
		"""
		sr1 = create_stock_reconciliation(
			item_code="Raw Material Item 1", target="_Test Warehouse - _TC", qty=1, rate=130
		)
		sr2 = create_stock_reconciliation(
			item_code="Subassembly Item 1", target="_Test Warehouse - _TC", qty=1, rate=140
		)

		pln = create_production_plan(
			item_code="Test Production Item 1", use_multi_level_bom=0, ignore_existing_ordered_qty=0
		)
		self.assertFalse(len(pln.mr_items))

		sr1.cancel()
		sr2.cancel()
		pln.cancel()

	def test_production_plan_sales_orders(self):
		"Test if previously fulfilled SO (with WO) is pulled into Prod Plan."
		item = "Test Production Item 1"
		so = make_sales_order(item_code=item, qty=1)
		sales_order = so.name
		sales_order_item = so.items[0].name

		pln = frappe.new_doc("Production Plan")
		pln.company = so.company
		pln.get_items_from = "Sales Order"

		pln.append(
			"sales_orders",
			{
				"sales_order": so.name,
				"sales_order_date": so.transaction_date,
				"customer": so.customer,
				"grand_total": so.grand_total,
			},
		)

		pln.get_so_items()
		pln.submit()
		pln.make_work_order()

		work_order = frappe.db.get_value(
			"Work Order",
			{"sales_order": sales_order, "production_plan": pln.name, "sales_order_item": sales_order_item},
			"name",
		)

		wo_doc = frappe.get_doc("Work Order", work_order)
		wo_doc.update(
			{"wip_warehouse": "Work In Progress - _TC", "fg_warehouse": "Finished Goods - _TC"}
		)
		wo_doc.submit()

		so_wo_qty = frappe.db.get_value("Sales Order Item", sales_order_item, "work_order_qty")
		self.assertTrue(so_wo_qty, 5)

		pln = frappe.new_doc("Production Plan")
		pln.update(
			{
				"from_date": so.transaction_date,
				"to_date": so.transaction_date,
				"customer": so.customer,
				"item_code": item,
				"sales_order_status": so.status,
			}
		)
		sales_orders = get_sales_orders(pln) or {}
		sales_orders = [d.get("name") for d in sales_orders if d.get("name") == sales_order]

		self.assertEqual(sales_orders, [])

	def test_donot_allow_to_make_multiple_pp_against_same_so(self):
		item = "Test SO Production Item 1"
		create_item(item)

		raw_material = "Test SO RM Production Item 1"
		create_item(raw_material)

		if not frappe.db.get_value("BOM", {"item": item}):
			make_bom(item=item, raw_materials=[raw_material])

		so = make_sales_order(item_code=item, qty=4)
		pln = frappe.new_doc("Production Plan")
		pln.company = so.company
		pln.get_items_from = "Sales Order"

		pln.append(
			"sales_orders",
			{
				"sales_order": so.name,
				"sales_order_date": so.transaction_date,
				"customer": so.customer,
				"grand_total": so.grand_total,
			},
		)

		pln.get_so_items()
		pln.submit()

		pln = frappe.new_doc("Production Plan")
		pln.company = so.company
		pln.get_items_from = "Sales Order"

		pln.append(
			"sales_orders",
			{
				"sales_order": so.name,
				"sales_order_date": so.transaction_date,
				"customer": so.customer,
				"grand_total": so.grand_total,
			},
		)

		pln.get_so_items()
		self.assertRaises(frappe.ValidationError, pln.save)

	def test_so_based_bill_of_material(self):
		item = "Test SO Production Item 1"
		create_item(item)

		raw_material = "Test SO RM Production Item 1"
		create_item(raw_material)

		bom1 = make_bom(item=item, raw_materials=[raw_material])

		so = make_sales_order(item_code=item, qty=4)

		# Create new BOM and assign to new sales order
		bom2 = make_bom(item=item, raw_materials=[raw_material])
		so2 = make_sales_order(item_code=item, qty=4)

		pln1 = frappe.new_doc("Production Plan")
		pln1.company = so.company
		pln1.get_items_from = "Sales Order"

		pln1.append(
			"sales_orders",
			{
				"sales_order": so.name,
				"sales_order_date": so.transaction_date,
				"customer": so.customer,
				"grand_total": so.grand_total,
			},
		)

		pln1.get_so_items()

		self.assertEqual(pln1.po_items[0].bom_no, bom1.name)

		pln2 = frappe.new_doc("Production Plan")
		pln2.company = so2.company
		pln2.get_items_from = "Sales Order"

		pln2.append(
			"sales_orders",
			{
				"sales_order": so2.name,
				"sales_order_date": so2.transaction_date,
				"customer": so2.customer,
				"grand_total": so2.grand_total,
			},
		)

		pln2.get_so_items()

		self.assertEqual(pln2.po_items[0].bom_no, bom2.name)

	def test_production_plan_combine_items(self):
		"Test combining FG items in Production Plan."
		item = "Test Production Item 1"
		so1 = make_sales_order(item_code=item, qty=1)

		pln = frappe.new_doc("Production Plan")
		pln.company = so1.company
		pln.get_items_from = "Sales Order"
		pln.append(
			"sales_orders",
			{
				"sales_order": so1.name,
				"sales_order_date": so1.transaction_date,
				"customer": so1.customer,
				"grand_total": so1.grand_total,
			},
		)
		so2 = make_sales_order(item_code=item, qty=2)
		pln.append(
			"sales_orders",
			{
				"sales_order": so2.name,
				"sales_order_date": so2.transaction_date,
				"customer": so2.customer,
				"grand_total": so2.grand_total,
			},
		)
		pln.combine_items = 1
		pln.get_items()
		pln.submit()

		self.assertTrue(pln.po_items[0].planned_qty, 3)

		pln.make_work_order()
		work_order = frappe.db.get_value(
			"Work Order",
			{"production_plan_item": pln.po_items[0].name, "production_plan": pln.name},
			"name",
		)

		wo_doc = frappe.get_doc("Work Order", work_order)
		wo_doc.update(
			{
				"wip_warehouse": "Work In Progress - _TC",
			}
		)

		wo_doc.submit()
		so_items = []
		for plan_reference in pln.prod_plan_references:
			so_items.append(plan_reference.sales_order_item)
			so_wo_qty = frappe.db.get_value(
				"Sales Order Item", plan_reference.sales_order_item, "work_order_qty"
			)
			self.assertEqual(so_wo_qty, plan_reference.qty)

		wo_doc.cancel()
		for so_item in so_items:
			so_wo_qty = frappe.db.get_value("Sales Order Item", so_item, "work_order_qty")
			self.assertEqual(so_wo_qty, 0.0)

		pln.reload()
		pln.cancel()

	def test_production_plan_subassembly_default_supplier(self):
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom

		bom_tree_1 = {"Test Laptop": {"Test Motherboard": {"Test Motherboard Wires": {}}}}
		bom = create_nested_bom(bom_tree_1, prefix="")

		item_doc = frappe.get_doc("Item", "Test Motherboard")
		company = "_Test Company"

		item_doc.is_sub_contracted_item = 1
		for row in item_doc.item_defaults:
			if row.company == company and not row.default_supplier:
				row.default_supplier = "_Test Supplier"

		if not item_doc.item_defaults:
			item_doc.append("item_defaults", {"company": company, "default_supplier": "_Test Supplier"})

		item_doc.save()

		plan = create_production_plan(item_code="Test Laptop", use_multi_level_bom=1, do_not_submit=True)
		plan.get_sub_assembly_items()
		plan.set_default_supplier_for_subcontracting_order()

		self.assertEqual(plan.sub_assembly_items[0].supplier, "_Test Supplier")

	def test_production_plan_for_subcontracting_po(self):
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom

		bom_tree_1 = {"Test Laptop 1": {"Test Motherboard 1": {"Test Motherboard Wires 1": {}}}}
		create_nested_bom(bom_tree_1, prefix="")

		item_doc = frappe.get_doc("Item", "Test Motherboard 1")
		company = "_Test Company"

		item_doc.is_sub_contracted_item = 1
		for row in item_doc.item_defaults:
			if row.company == company and not row.default_supplier:
				row.default_supplier = "_Test Supplier"

		if not item_doc.item_defaults:
			item_doc.append("item_defaults", {"company": company, "default_supplier": "_Test Supplier"})

		item_doc.save()

		plan = create_production_plan(
			item_code="Test Laptop 1", planned_qty=10, use_multi_level_bom=1, do_not_submit=True
		)
		plan.get_sub_assembly_items()
		plan.set_default_supplier_for_subcontracting_order()
		plan.submit()

		self.assertEqual(plan.sub_assembly_items[0].supplier, "_Test Supplier")
		plan.make_work_order()

		po = frappe.db.get_value("Purchase Order Item", {"production_plan": plan.name}, "parent")
		po_doc = frappe.get_doc("Purchase Order", po)
		self.assertEqual(po_doc.supplier, "_Test Supplier")
		self.assertEqual(po_doc.items[0].qty, 10.0)
		self.assertEqual(po_doc.items[0].fg_item_qty, 10.0)
		self.assertEqual(po_doc.items[0].fg_item_qty, 10.0)
		self.assertEqual(po_doc.items[0].fg_item, "Test Motherboard 1")

	def test_production_plan_combine_subassembly(self):
		"""
		Test combining Sub assembly items belonging to the same BOM in Prod Plan.
		1) Red-Car -> Wheel (sub assembly) > BOM-WHEEL-001
		2) Green-Car -> Wheel (sub assembly) > BOM-WHEEL-001
		"""
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom

		bom_tree_1 = {"Red-Car": {"Wheel": {"Rubber": {}}}}
		bom_tree_2 = {"Green-Car": {"Wheel": {"Rubber": {}}}}

		parent_bom_1 = create_nested_bom(bom_tree_1, prefix="")
		parent_bom_2 = create_nested_bom(bom_tree_2, prefix="")

		# make sure both boms use same subassembly bom
		subassembly_bom = parent_bom_1.items[0].bom_no
		frappe.db.set_value("BOM Item", parent_bom_2.items[0].name, "bom_no", subassembly_bom)

		plan = create_production_plan(item_code="Red-Car", use_multi_level_bom=1, do_not_save=True)
		plan.append(
			"po_items",
			{  # Add Green-Car to Prod Plan
				"use_multi_level_bom": 1,
				"item_code": "Green-Car",
				"bom_no": frappe.db.get_value("Item", "Green-Car", "default_bom"),
				"planned_qty": 1,
				"planned_start_date": now_datetime(),
			},
		)
		plan.get_sub_assembly_items()
		self.assertTrue(len(plan.sub_assembly_items), 2)

		plan.combine_sub_items = 1
		plan.get_sub_assembly_items()

		self.assertTrue(len(plan.sub_assembly_items), 1)  # check if sub-assembly items merged
		self.assertEqual(plan.sub_assembly_items[0].qty, 2.0)
		self.assertEqual(plan.sub_assembly_items[0].stock_qty, 2.0)

		# change warehouse in one row, sub-assemblies should not merge
		plan.po_items[0].warehouse = "Finished Goods - _TC"
		plan.get_sub_assembly_items()
		self.assertTrue(len(plan.sub_assembly_items), 2)

	def test_pp_to_mr_customer_provided(self):
		"Test Material Request from Production Plan for Customer Provided Item."
		create_item(
			"CUST-0987", is_customer_provided_item=1, customer="_Test Customer", is_purchase_item=0
		)
		create_item("Production Item CUST")

		for item, raw_materials in {
			"Production Item CUST": ["Raw Material Item 1", "CUST-0987"]
		}.items():
			if not frappe.db.get_value("BOM", {"item": item}):
				make_bom(item=item, raw_materials=raw_materials)
		production_plan = create_production_plan(item_code="Production Item CUST")
		production_plan.make_material_request()

		material_request = frappe.db.get_value(
			"Material Request Item",
			{"production_plan": production_plan.name, "item_code": "CUST-0987"},
			"parent",
		)
		mr = frappe.get_doc("Material Request", material_request)

		self.assertTrue(mr.material_request_type, "Customer Provided")
		self.assertTrue(mr.customer, "_Test Customer")

	def test_production_plan_with_multi_level_bom(self):
		"""
		Item Code	|	Qty	|
		|Test BOM 1	|	1	|
		|Test BOM 2	|	2	|
		|Test BOM 3	|	3	|
		"""

		for item_code in ["Test BOM 1", "Test BOM 2", "Test BOM 3", "Test RM BOM 1"]:
			create_item(item_code, is_stock_item=1)

		# created bom upto 3 level
		if not frappe.db.get_value("BOM", {"item": "Test BOM 3"}):
			make_bom(item="Test BOM 3", raw_materials=["Test RM BOM 1"], rm_qty=3)

		if not frappe.db.get_value("BOM", {"item": "Test BOM 2"}):
			make_bom(item="Test BOM 2", raw_materials=["Test BOM 3"], rm_qty=3)

		if not frappe.db.get_value("BOM", {"item": "Test BOM 1"}):
			make_bom(item="Test BOM 1", raw_materials=["Test BOM 2"], rm_qty=2)

		item_code = "Test BOM 1"
		pln = frappe.new_doc("Production Plan")
		pln.company = "_Test Company"
		pln.append(
			"po_items",
			{
				"item_code": item_code,
				"bom_no": frappe.db.get_value("BOM", {"item": "Test BOM 1"}),
				"planned_qty": 3,
			},
		)

		pln.get_sub_assembly_items("In House")
		pln.submit()
		pln.make_work_order()

		# last level sub-assembly work order produce qty
		to_produce_qty = frappe.db.get_value(
			"Work Order", {"production_plan": pln.name, "production_item": "Test BOM 3"}, "qty"
		)

		self.assertEqual(to_produce_qty, 18.0)
		pln.cancel()
		frappe.delete_doc("Production Plan", pln.name)

	def test_get_warehouse_list_group(self):
		"Check if required child warehouses are returned."
		warehouse_json = '[{"warehouse":"_Test Warehouse Group - _TC"}]'

		warehouses = set(get_warehouse_list(warehouse_json))
		expected_warehouses = {"_Test Warehouse Group-C1 - _TC", "_Test Warehouse Group-C2 - _TC"}

		missing_warehouse = expected_warehouses - warehouses

		self.assertTrue(
			len(missing_warehouse) == 0,
			msg=f"Following warehouses were expected {', '.join(missing_warehouse)}",
		)

	def test_get_warehouse_list_single(self):
		"Check if same warehouse is returned in absence of child warehouses."
		warehouse_json = '[{"warehouse":"_Test Scrap Warehouse - _TC"}]'

		warehouses = set(get_warehouse_list(warehouse_json))
		expected_warehouses = {
			"_Test Scrap Warehouse - _TC",
		}

		self.assertEqual(warehouses, expected_warehouses)

	def test_get_sales_order_with_variant(self):
		"Check if Template BOM is fetched in absence of Variant BOM."
		rm_item = create_item("PIV_RM", valuation_rate=100)
		if not frappe.db.exists("Item", {"item_code": "PIV"}):
			item = create_item("PIV", valuation_rate=100)
			variant_settings = {
				"attributes": [
					{"attribute": "Colour"},
				],
				"has_variants": 1,
			}
			item.update(variant_settings)
			item.save()
			parent_bom = make_bom(item="PIV", raw_materials=[rm_item.item_code])
		if not frappe.db.exists("BOM", {"item": "PIV"}):
			parent_bom = make_bom(item="PIV", raw_materials=[rm_item.item_code])
		else:
			parent_bom = frappe.get_doc("BOM", {"item": "PIV"})

		if not frappe.db.exists("Item", {"item_code": "PIV-RED"}):
			variant = create_variant("PIV", {"Colour": "Red"})
			variant.save()
			variant_bom = make_bom(item=variant.item_code, raw_materials=[rm_item.item_code])
		else:
			variant = frappe.get_doc("Item", "PIV-RED")
		if not frappe.db.exists("BOM", {"item": "PIV-RED"}):
			variant_bom = make_bom(item=variant.item_code, raw_materials=[rm_item.item_code])

		"""Testing when item variant has a BOM"""
		so = make_sales_order(item_code="PIV-RED", qty=5)
		pln = frappe.new_doc("Production Plan")
		pln.company = so.company
		pln.get_items_from = "Sales Order"
		pln.item_code = "PIV-RED"
		pln.get_open_sales_orders()
		self.assertEqual(pln.sales_orders[0].sales_order, so.name)
		pln.get_so_items()
		self.assertEqual(pln.po_items[0].item_code, "PIV-RED")
		self.assertEqual(pln.po_items[0].bom_no, variant_bom.name)
		so.cancel()
		frappe.delete_doc("Sales Order", so.name)
		variant_bom.cancel()
		frappe.delete_doc("BOM", variant_bom.name)

		"""Testing when item variant doesn't have a BOM"""
		so = make_sales_order(item_code="PIV-RED", qty=5)
		pln.get_open_sales_orders()
		self.assertEqual(pln.sales_orders[0].sales_order, so.name)
		pln.po_items = []
		pln.get_so_items()
		self.assertEqual(pln.po_items[0].item_code, "PIV-RED")
		self.assertEqual(pln.po_items[0].bom_no, parent_bom.name)

		frappe.db.rollback()

	def test_multiple_work_order_for_production_plan_item(self):
		"Test producing Prod Plan (making WO) in parts."

		def create_work_order(item, pln, qty):
			# Get Production Items
			items_data = pln.get_production_items()

			# Update qty
			items_data[(item, None, None)]["qty"] = qty

			# Create and Submit Work Order for each item in items_data
			for key, item in items_data.items():
				if pln.sub_assembly_items:
					item["use_multi_level_bom"] = 0

				wo_name = pln.create_work_order(item)
				wo_doc = frappe.get_doc("Work Order", wo_name)
				wo_doc.update(
					{"wip_warehouse": "Work In Progress - _TC", "fg_warehouse": "Finished Goods - _TC"}
				)
				wo_doc.submit()
				wo_list.append(wo_name)

		item = "Test Production Item 1"
		raw_materials = ["Raw Material Item 1", "Raw Material Item 2"]

		# Create BOM
		bom = make_bom(item=item, raw_materials=raw_materials)

		# Create Production Plan
		pln = create_production_plan(item_code=bom.item, planned_qty=5)

		# All the created Work Orders
		wo_list = []

		# Create and Submit 1st Work Order for 3 qty
		create_work_order(item, pln, 3)
		pln.reload()
		self.assertEqual(pln.po_items[0].ordered_qty, 3)

		# Create and Submit 2nd Work Order for 2 qty
		create_work_order(item, pln, 2)
		pln.reload()
		self.assertEqual(pln.po_items[0].ordered_qty, 5)

		# Overproduction
		self.assertRaises(OverProductionError, create_work_order, item=item, pln=pln, qty=2)

		# Cancel 1st Work Order
		wo1 = frappe.get_doc("Work Order", wo_list[0])
		wo1.cancel()
		pln.reload()
		self.assertEqual(pln.po_items[0].ordered_qty, 2)

		# Cancel 2nd Work Order
		wo2 = frappe.get_doc("Work Order", wo_list[1])
		wo2.cancel()
		pln.reload()
		self.assertEqual(pln.po_items[0].ordered_qty, 0)

	def test_production_plan_pending_qty_with_sales_order(self):
		"""
		Test Prod Plan impact via: SO -> Prod Plan -> WO -> SE -> SE (cancel)
		"""
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record

		make_stock_entry(item_code="_Test Item", target="Work In Progress - _TC", qty=2, basic_rate=100)
		make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="Work In Progress - _TC", qty=4, basic_rate=100
		)

		item = "_Test FG Item"

		make_stock_entry(item_code=item, target="_Test Warehouse - _TC", qty=1)

		so = make_sales_order(item_code=item, qty=2)

		dn = make_delivery_note(so.name)
		dn.items[0].qty = 1
		dn.save()
		dn.submit()

		pln = create_production_plan(
			company=so.company, get_items_from="Sales Order", sales_order=so, skip_getting_mr_items=True
		)
		self.assertEqual(pln.po_items[0].pending_qty, 1)

		wo = make_wo_order_test_record(
			item_code=item,
			qty=1,
			company=so.company,
			wip_warehouse="Work In Progress - _TC",
			fg_warehouse="Finished Goods - _TC",
			skip_transfer=1,
			use_multi_level_bom=1,
			do_not_submit=True,
		)
		wo.production_plan = pln.name
		wo.production_plan_item = pln.po_items[0].name
		wo.submit()

		se = frappe.get_doc(make_se_from_wo(wo.name, "Manufacture", 1))
		se.submit()

		pln.reload()
		self.assertEqual(pln.po_items[0].pending_qty, 0)

		se.cancel()
		pln.reload()
		self.assertEqual(pln.po_items[0].pending_qty, 1)

	def test_production_plan_pending_qty_independent_items(self):
		"Test Prod Plan impact if items are added independently (no from SO or MR)."
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record

		make_stock_entry(
			item_code="Raw Material Item 1", target="Work In Progress - _TC", qty=2, basic_rate=100
		)
		make_stock_entry(
			item_code="Raw Material Item 2", target="Work In Progress - _TC", qty=2, basic_rate=100
		)

		pln = create_production_plan(item_code="Test Production Item 1", skip_getting_mr_items=True)
		self.assertEqual(pln.po_items[0].pending_qty, 1)

		wo = make_wo_order_test_record(
			item_code="Test Production Item 1",
			qty=1,
			company=pln.company,
			wip_warehouse="Work In Progress - _TC",
			fg_warehouse="Finished Goods - _TC",
			skip_transfer=1,
			use_multi_level_bom=1,
			do_not_submit=True,
		)
		wo.production_plan = pln.name
		wo.production_plan_item = pln.po_items[0].name
		wo.submit()

		se = frappe.get_doc(make_se_from_wo(wo.name, "Manufacture", 1))
		se.submit()

		pln.reload()
		self.assertEqual(pln.po_items[0].pending_qty, 0)

		se.cancel()
		pln.reload()
		self.assertEqual(pln.po_items[0].pending_qty, 1)

	def test_qty_based_status(self):
		pp = frappe.new_doc("Production Plan")
		pp.po_items = [frappe._dict(planned_qty=5, produce_qty=4)]
		self.assertFalse(pp.all_items_completed())

		pp.po_items = [
			frappe._dict(planned_qty=5, produce_qty=10),
			frappe._dict(planned_qty=5, produce_qty=4),
		]
		self.assertFalse(pp.all_items_completed())

	def test_production_plan_planned_qty(self):
		# Case 1: When Planned Qty is non-integer and UOM is integer.
		from erpnext.utilities.transaction_base import UOMMustBeIntegerError

		self.assertRaises(
			UOMMustBeIntegerError, create_production_plan, item_code="_Test FG Item", planned_qty=0.55
		)

		# Case 2: When Planned Qty is non-integer and UOM is also non-integer.
		from erpnext.stock.doctype.item.test_item import make_item

		fg_item = make_item(properties={"is_stock_item": 1, "stock_uom": "_Test UOM 1"}).name
		bom_item = make_item().name

		make_bom(item=fg_item, raw_materials=[bom_item], source_warehouse="_Test Warehouse - _TC")

		pln = create_production_plan(item_code=fg_item, planned_qty=0.55, stock_uom="_Test UOM 1")
		self.assertEqual(pln.po_items[0].planned_qty, 0.55)

	def test_temporary_name_relinking(self):

		pp = frappe.new_doc("Production Plan")

		# this can not be unittested so mocking data that would be expected
		# from client side.
		for _ in range(10):
			po_item = pp.append(
				"po_items",
				{
					"name": frappe.generate_hash(length=10),
					"temporary_name": frappe.generate_hash(length=10),
				},
			)
			pp.append("sub_assembly_items", {"production_plan_item": po_item.temporary_name})
		pp._rename_temporary_references()

		for po_item, subassy_item in zip(pp.po_items, pp.sub_assembly_items):
			self.assertEqual(po_item.name, subassy_item.production_plan_item)

		# bad links should be erased
		pp.append("sub_assembly_items", {"production_plan_item": frappe.generate_hash(length=16)})
		pp._rename_temporary_references()
		self.assertIsNone(pp.sub_assembly_items[-1].production_plan_item)
		pp.sub_assembly_items.pop()

		# reattempting on same doc shouldn't change anything
		pp._rename_temporary_references()
		for po_item, subassy_item in zip(pp.po_items, pp.sub_assembly_items):
			self.assertEqual(po_item.name, subassy_item.production_plan_item)

	def test_produced_qty_for_multi_level_bom_item(self):
		# Create Items and BOMs
		rm_item = make_item(properties={"is_stock_item": 1}).name
		sub_assembly_item = make_item(properties={"is_stock_item": 1}).name
		fg_item = make_item(properties={"is_stock_item": 1}).name

		make_stock_entry(
			item_code=rm_item,
			qty=60,
			to_warehouse="Work In Progress - _TC",
			rate=99,
			purpose="Material Receipt",
		)

		make_bom(item=sub_assembly_item, raw_materials=[rm_item], rm_qty=3)
		make_bom(item=fg_item, raw_materials=[sub_assembly_item], rm_qty=4)

		# Step - 1: Create Production Plan
		pln = create_production_plan(item_code=fg_item, planned_qty=5, skip_getting_mr_items=1)
		pln.get_sub_assembly_items()

		# Step - 2: Create Work Orders
		pln.make_work_order()
		work_orders = frappe.get_all("Work Order", filters={"production_plan": pln.name}, pluck="name")
		sa_wo = fg_wo = None
		for work_order in work_orders:
			wo_doc = frappe.get_doc("Work Order", work_order)
			if wo_doc.production_plan_item:
				wo_doc.update(
					{"wip_warehouse": "Work In Progress - _TC", "fg_warehouse": "Finished Goods - _TC"}
				)
				fg_wo = wo_doc.name
			else:
				wo_doc.update(
					{"wip_warehouse": "Work In Progress - _TC", "fg_warehouse": "Work In Progress - _TC"}
				)
				sa_wo = wo_doc.name
			wo_doc.submit()

		# Step - 3: Complete Work Orders
		se = frappe.get_doc(make_se_from_wo(sa_wo, "Manufacture"))
		se.submit()

		se = frappe.get_doc(make_se_from_wo(fg_wo, "Manufacture"))
		se.submit()

		# Step - 4: Check Production Plan Item Produced Qty
		pln.load_from_db()
		self.assertEqual(pln.status, "Completed")
		self.assertEqual(pln.po_items[0].produced_qty, 5)

	def test_material_request_item_for_purchase_uom(self):
		from erpnext.stock.doctype.item.test_item import make_item

		fg_item = make_item(properties={"is_stock_item": 1, "stock_uom": "_Test UOM 1"}).name
		bom_item = make_item(
			properties={"is_stock_item": 1, "stock_uom": "_Test UOM 1", "purchase_uom": "Nos"}
		).name

		if not frappe.db.exists("UOM Conversion Detail", {"parent": bom_item, "uom": "Nos"}):
			doc = frappe.get_doc("Item", bom_item)
			doc.append("uoms", {"uom": "Nos", "conversion_factor": 10})
			doc.save()

		make_bom(item=fg_item, raw_materials=[bom_item], source_warehouse="_Test Warehouse - _TC")

		pln = create_production_plan(
			item_code=fg_item, planned_qty=10, ignore_existing_ordered_qty=1, stock_uom="_Test UOM 1"
		)

		pln.make_material_request()

		for row in pln.mr_items:
			self.assertEqual(row.uom, "Nos")
			self.assertEqual(row.quantity, 1)

		for row in frappe.get_all(
			"Material Request Item",
			filters={"production_plan": pln.name},
			fields=["item_code", "uom", "qty"],
		):
			self.assertEqual(row.item_code, bom_item)
			self.assertEqual(row.uom, "Nos")
			self.assertEqual(row.qty, 1)

	def test_material_request_for_sub_assembly_items(self):
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom

		bom_tree = {
			"Fininshed Goods1 For MR": {
				"SubAssembly1 For MR": {"SubAssembly1-1 For MR": {"ChildPart1 For MR": {}}}
			}
		}

		parent_bom = create_nested_bom(bom_tree, prefix="")
		plan = create_production_plan(
			item_code=parent_bom.item, planned_qty=10, ignore_existing_ordered_qty=1, do_not_submit=1
		)

		plan.get_sub_assembly_items()

		mr_items = []
		for row in plan.sub_assembly_items:
			mr_items.append(row.production_item)
			row.type_of_manufacturing = "Material Request"

		plan.save()
		items = get_items_for_material_requests(plan.as_dict())

		validate_mr_items = [d.get("item_code") for d in items]
		for item_code in mr_items:
			self.assertTrue(item_code in validate_mr_items)

	def test_resered_qty_for_production_plan_for_material_requests(self):
		from erpnext.stock.utils import get_or_make_bin

		bin_name = get_or_make_bin("Raw Material Item 1", "_Test Warehouse - _TC")
		before_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))

		pln = create_production_plan(item_code="Test Production Item 1")

		bin_name = get_or_make_bin("Raw Material Item 1", "_Test Warehouse - _TC")
		after_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))

		self.assertEqual(after_qty - before_qty, 1)
		pln = frappe.get_doc("Production Plan", pln.name)
		pln.cancel()

		bin_name = get_or_make_bin("Raw Material Item 1", "_Test Warehouse - _TC")
		after_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))

		pln.reload()
		self.assertEqual(pln.docstatus, 2)
		self.assertEqual(after_qty, before_qty)

	def test_resered_qty_for_production_plan_for_work_order(self):
		from erpnext.stock.utils import get_or_make_bin

		bin_name = get_or_make_bin("Raw Material Item 1", "_Test Warehouse - _TC")
		before_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))

		pln = create_production_plan(item_code="Test Production Item 1")

		bin_name = get_or_make_bin("Raw Material Item 1", "_Test Warehouse - _TC")
		after_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))

		self.assertEqual(after_qty - before_qty, 1)

		pln.make_work_order()

		work_orders = []
		for row in frappe.get_all("Work Order", filters={"production_plan": pln.name}, fields=["name"]):
			wo_doc = frappe.get_doc("Work Order", row.name)
			wo_doc.source_warehouse = "_Test Warehouse - _TC"
			wo_doc.wip_warehouse = "_Test Warehouse 1 - _TC"
			wo_doc.fg_warehouse = "_Test Warehouse - _TC"
			for d in wo_doc.required_items:
				d.source_warehouse = "_Test Warehouse - _TC"
				make_stock_entry(
					item_code=d.item_code,
					qty=d.required_qty,
					rate=100,
					target="_Test Warehouse - _TC",
				)

			wo_doc.submit()
			work_orders.append(wo_doc)

		bin_name = get_or_make_bin("Raw Material Item 1", "_Test Warehouse - _TC")
		after_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))

		self.assertEqual(after_qty, before_qty)

		rm_work_order = None
		for wo_doc in work_orders:
			for d in wo_doc.required_items:
				if d.item_code == "Raw Material Item 1":
					rm_work_order = wo_doc
					break

		if rm_work_order:
			s = frappe.get_doc(make_se_from_wo(rm_work_order.name, "Material Transfer for Manufacture", 1))
			s.submit()
			bin_name = get_or_make_bin("Raw Material Item 1", "_Test Warehouse - _TC")
			after_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))

			self.assertEqual(after_qty, before_qty)

	def test_resered_qty_for_production_plan_for_less_rm_qty(self):
		from erpnext.stock.utils import get_or_make_bin

		bin_name = get_or_make_bin("Raw Material Item 1", "_Test Warehouse - _TC")
		before_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))

		pln = create_production_plan(item_code="Test Production Item 1", planned_qty=10)

		bin_name = get_or_make_bin("Raw Material Item 1", "_Test Warehouse - _TC")
		after_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))

		self.assertEqual(after_qty - before_qty, 10)

		pln.make_work_order()

		plans = []
		for row in frappe.get_all("Work Order", filters={"production_plan": pln.name}, fields=["name"]):
			wo_doc = frappe.get_doc("Work Order", row.name)
			wo_doc.source_warehouse = "_Test Warehouse - _TC"
			wo_doc.wip_warehouse = "_Test Warehouse 1 - _TC"
			wo_doc.fg_warehouse = "_Test Warehouse - _TC"
			for d in wo_doc.required_items:
				d.source_warehouse = "_Test Warehouse - _TC"
				d.required_qty -= 5
				make_stock_entry(
					item_code=d.item_code,
					qty=d.required_qty,
					rate=100,
					target="_Test Warehouse - _TC",
				)

			wo_doc.submit()
			plans.append(pln.name)

		bin_name = get_or_make_bin("Raw Material Item 1", "_Test Warehouse - _TC")
		after_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))

		self.assertEqual(after_qty, before_qty)

		completed_plans = get_non_completed_production_plans()
		for plan in plans:
			self.assertFalse(plan in completed_plans)

	def test_resered_qty_for_production_plan_for_material_requests_with_multi_UOM(self):
		from erpnext.stock.utils import get_or_make_bin

		fg_item = make_item(properties={"is_stock_item": 1, "stock_uom": "_Test UOM 1"}).name
		bom_item = make_item(
			properties={"is_stock_item": 1, "stock_uom": "_Test UOM 1", "purchase_uom": "Nos"}
		).name

		if not frappe.db.exists("UOM Conversion Detail", {"parent": bom_item, "uom": "Nos"}):
			doc = frappe.get_doc("Item", bom_item)
			doc.append("uoms", {"uom": "Nos", "conversion_factor": 25})
			doc.save()

		make_bom(item=fg_item, raw_materials=[bom_item], source_warehouse="_Test Warehouse - _TC")

		bin_name = get_or_make_bin(bom_item, "_Test Warehouse - _TC")
		before_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))

		pln = create_production_plan(
			item_code=fg_item, planned_qty=100, ignore_existing_ordered_qty=1, stock_uom="_Test UOM 1"
		)

		for row in pln.mr_items:
			self.assertEqual(row.uom, "Nos")
			self.assertEqual(row.quantity, 4)

			reserved_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan"))
			self.assertEqual(reserved_qty - before_qty, 100.0)

		pln.submit_material_request = 1
		pln.make_work_order()

		for work_order in frappe.get_all(
			"Work Order",
			fields=["name"],
			filters={"production_plan": pln.name},
		):
			wo_doc = frappe.get_doc("Work Order", work_order.name)
			wo_doc.source_warehouse = "_Test Warehouse - _TC"
			wo_doc.wip_warehouse = "_Test Warehouse 1 - _TC"
			wo_doc.fg_warehouse = "_Test Warehouse - _TC"
			wo_doc.submit()

		reserved_qty_after_mr = flt(
			frappe.db.get_value("Bin", bin_name, "reserved_qty_for_production_plan")
		)
		self.assertEqual(reserved_qty_after_mr, before_qty)

	def test_from_warehouse_for_purchase_material_request(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from erpnext.stock.utils import get_or_make_bin

		create_item("RM-TEST-123 For Purchase", valuation_rate=100)
		bin_name = get_or_make_bin("RM-TEST-123 For Purchase", "_Test Warehouse - _TC")
		t_warehouse = create_warehouse("_Test Store - _TC")
		make_stock_entry(
			item_code="Raw Material Item 1",
			qty=5,
			rate=100,
			target=t_warehouse,
		)

		plan = create_production_plan(item_code="Test Production Item 1", do_not_save=1)
		mr_items = get_items_for_material_requests(
			plan.as_dict(), warehouses=[{"warehouse": t_warehouse}]
		)

		for d in mr_items:
			plan.append("mr_items", d)

		plan.save()

		for row in plan.mr_items:
			if row.material_request_type == "Material Transfer":
				self.assertEqual(row.from_warehouse, t_warehouse)

			row.material_request_type = "Purchase"

		plan.save()

		for row in plan.mr_items:
			self.assertFalse(row.from_warehouse)

	def test_skip_available_qty_for_sub_assembly_items(self):
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom

		bom_tree = {
			"Fininshed Goods1 For SUB Test": {
				"SubAssembly1 For SUB Test": {"ChildPart1 For SUB Test": {}},
				"SubAssembly2 For SUB Test": {},
			}
		}

		parent_bom = create_nested_bom(bom_tree, prefix="")
		plan = create_production_plan(
			item_code=parent_bom.item,
			planned_qty=10,
			ignore_existing_ordered_qty=1,
			do_not_submit=1,
			skip_available_sub_assembly_item=1,
			warehouse="_Test Warehouse - _TC",
		)

		make_stock_entry(
			item_code="SubAssembly1 For SUB Test",
			qty=5,
			rate=100,
			target="_Test Warehouse - _TC",
		)

		self.assertTrue(plan.skip_available_sub_assembly_item)

		plan.get_sub_assembly_items()

		for row in plan.sub_assembly_items:
			if row.production_item == "SubAssembly1 For SUB Test":
				self.assertEqual(row.qty, 5)

		mr_items = get_items_for_material_requests(plan.as_dict())
		for row in mr_items:
			row = frappe._dict(row)
			if row.item_code == "ChildPart1 For SUB Test":
				self.assertEqual(row.quantity, 5)

			if row.item_code == "SubAssembly2 For SUB Test":
				self.assertEqual(row.quantity, 10)

	def test_transfer_and_purchase_mrp_for_purchase_uom(self):
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		bom_tree = {
			"Test FG Item INK PEN": {
				"Test RM Item INK": {},
			}
		}

		parent_bom = create_nested_bom(bom_tree, prefix="")
		if not frappe.db.exists("UOM Conversion Detail", {"parent": "Test RM Item INK", "uom": "Kg"}):
			doc = frappe.get_doc("Item", "Test RM Item INK")
			doc.purchase_uom = "Kg"
			doc.append("uoms", {"uom": "Kg", "conversion_factor": 0.5})
			doc.save()

		wh1 = create_warehouse("PNE Warehouse", company="_Test Company")
		wh2 = create_warehouse("MBE Warehouse", company="_Test Company")
		mrp_warhouse = create_warehouse("MRPBE Warehouse", company="_Test Company")

		make_stock_entry(
			item_code="Test RM Item INK",
			qty=2,
			rate=100,
			target=wh1,
		)

		make_stock_entry(
			item_code="Test RM Item INK",
			qty=2,
			rate=100,
			target=wh2,
		)

		plan = create_production_plan(
			item_code=parent_bom.item,
			planned_qty=10,
			do_not_submit=1,
			warehouse="_Test Warehouse - _TC",
		)

		plan.for_warehouse = mrp_warhouse

		items = get_items_for_material_requests(
			plan.as_dict(), warehouses=[{"warehouse": wh1}, {"warehouse": wh2}]
		)

		for row in items:
			row = frappe._dict(row)
			if row.material_request_type == "Material Transfer":
				self.assertTrue(row.uom == row.stock_uom)
				self.assertTrue(row.from_warehouse in [wh1, wh2])
				self.assertEqual(row.quantity, 2)

			if row.material_request_type == "Purchase":
				self.assertTrue(row.uom != row.stock_uom)
				self.assertTrue(row.warehouse == mrp_warhouse)
				self.assertEqual(row.quantity, 12.0)

	def test_mr_qty_for_same_rm_with_different_sub_assemblies(self):
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom

		bom_tree = {
			"Fininshed Goods2 For SUB Test": {
				"SubAssembly2 For SUB Test": {"ChildPart2 For SUB Test": {}},
				"SubAssembly3 For SUB Test": {"ChildPart2 For SUB Test": {}},
			}
		}

		parent_bom = create_nested_bom(bom_tree, prefix="")
		plan = create_production_plan(
			item_code=parent_bom.item,
			planned_qty=1,
			ignore_existing_ordered_qty=1,
			do_not_submit=1,
			skip_available_sub_assembly_item=1,
			warehouse="_Test Warehouse - _TC",
		)

		plan.get_sub_assembly_items()
		plan.make_material_request()

		for row in plan.mr_items:
			if row.item_code == "ChildPart2 For SUB Test":
				self.assertEqual(row.quantity, 2)

	def test_reserve_sub_assembly_items(self):
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		bom_tree = {
			"Fininshed Goods Bicycle": {
				"Frame Assembly": {"Frame": {}},
				"Chain Assembly": {"Chain": {}},
			}
		}
		parent_bom = create_nested_bom(bom_tree, prefix="")

		warehouse = "_Test Warehouse - _TC"
		company = "_Test Company"

		sub_assembly_warehouse = create_warehouse("SUB ASSEMBLY WH", company=company)

		for item_code in ["Frame", "Chain"]:
			make_stock_entry(item_code=item_code, target=warehouse, qty=2, basic_rate=100)

		before_qty = flt(
			frappe.db.get_value(
				"Bin",
				{"item_code": "Frame Assembly", "warehouse": sub_assembly_warehouse},
				"reserved_qty_for_production_plan",
			)
		)

		plan = create_production_plan(
			item_code=parent_bom.item,
			planned_qty=2,
			ignore_existing_ordered_qty=1,
			do_not_submit=1,
			skip_available_sub_assembly_item=1,
			warehouse=warehouse,
			sub_assembly_warehouse=sub_assembly_warehouse,
		)

		plan.get_sub_assembly_items()
		plan.submit()

		after_qty = flt(
			frappe.db.get_value(
				"Bin",
				{"item_code": "Frame Assembly", "warehouse": sub_assembly_warehouse},
				"reserved_qty_for_production_plan",
			)
		)

		self.assertEqual(after_qty, before_qty + 2)

		plan.make_work_order()
		work_orders = frappe.get_all(
			"Work Order",
			fields=["name", "production_item"],
			filters={"production_plan": plan.name},
			order_by="creation desc",
		)

		for d in work_orders:
			wo_doc = frappe.get_doc("Work Order", d.name)
			wo_doc.skip_transfer = 1
			wo_doc.from_wip_warehouse = 1

			wo_doc.wip_warehouse = (
				warehouse
				if d.production_item in ["Frame Assembly", "Chain Assembly"]
				else sub_assembly_warehouse
			)

			wo_doc.submit()

			if d.production_item == "Frame Assembly":
				self.assertEqual(wo_doc.fg_warehouse, sub_assembly_warehouse)
				se_doc = frappe.get_doc(make_se_from_wo(wo_doc.name, "Manufacture", 2))
				se_doc.submit()

		after_qty = flt(
			frappe.db.get_value(
				"Bin",
				{"item_code": "Frame Assembly", "warehouse": sub_assembly_warehouse},
				"reserved_qty_for_production_plan",
			)
		)

		self.assertEqual(after_qty, before_qty)

	def test_material_request_qty_purchase_and_material_transfer(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		fg_item = make_item(properties={"is_stock_item": 1, "stock_uom": "_Test UOM 1"}).name
		bom_item = make_item(
			properties={"is_stock_item": 1, "stock_uom": "_Test UOM 1", "purchase_uom": "Nos"}
		).name

		store_warehouse = create_warehouse("Store Warehouse", company="_Test Company")
		rm_warehouse = create_warehouse("RM Warehouse", company="_Test Company")

		make_stock_entry(
			item_code=bom_item,
			qty=60,
			target=store_warehouse,
			rate=99,
		)

		if not frappe.db.exists("UOM Conversion Detail", {"parent": bom_item, "uom": "Nos"}):
			doc = frappe.get_doc("Item", bom_item)
			doc.append("uoms", {"uom": "Nos", "conversion_factor": 10})
			doc.save()

		make_bom(item=fg_item, raw_materials=[bom_item], source_warehouse="_Test Warehouse - _TC")

		pln = create_production_plan(
			item_code=fg_item, planned_qty=10, stock_uom="_Test UOM 1", do_not_submit=1
		)

		pln.for_warehouse = rm_warehouse
		items = get_items_for_material_requests(
			pln.as_dict(), warehouses=[{"warehouse": store_warehouse}]
		)

		for row in items:
			self.assertEqual(row.get("quantity"), 10.0)
			self.assertEqual(row.get("material_request_type"), "Material Transfer")
			self.assertEqual(row.get("uom"), "_Test UOM 1")
			self.assertEqual(row.get("from_warehouse"), store_warehouse)
			self.assertEqual(row.get("conversion_factor"), 1.0)

		items = get_items_for_material_requests(
			pln.as_dict(), warehouses=[{"warehouse": pln.for_warehouse}]
		)

		for row in items:
			self.assertEqual(row.get("quantity"), 1.0)
			self.assertEqual(row.get("material_request_type"), "Purchase")
			self.assertEqual(row.get("uom"), "Nos")
			self.assertEqual(row.get("conversion_factor"), 10.0)


def create_production_plan(**args):
	"""
	sales_order (obj): Sales Order Doc Object
	get_items_from (str): Sales Order/Material Request
	skip_getting_mr_items (bool): Whether or not to plan for new MRs
	"""
	args = frappe._dict(args)

	pln = frappe.get_doc(
		{
			"doctype": "Production Plan",
			"company": args.company or "_Test Company",
			"customer": args.customer or "_Test Customer",
			"posting_date": nowdate(),
			"include_non_stock_items": args.include_non_stock_items or 0,
			"include_subcontracted_items": args.include_subcontracted_items or 0,
			"ignore_existing_ordered_qty": args.ignore_existing_ordered_qty or 0,
			"get_items_from": "Sales Order",
			"skip_available_sub_assembly_item": args.skip_available_sub_assembly_item or 0,
			"sub_assembly_warehouse": args.sub_assembly_warehouse,
		}
	)

	if not args.get("sales_order"):
		pln.append(
			"po_items",
			{
				"use_multi_level_bom": args.use_multi_level_bom or 1,
				"item_code": args.item_code,
				"bom_no": frappe.db.get_value("Item", args.item_code, "default_bom"),
				"planned_qty": args.planned_qty or 1,
				"planned_start_date": args.planned_start_date or now_datetime(),
				"stock_uom": args.stock_uom or "Nos",
				"warehouse": args.warehouse,
			},
		)

	if args.get("get_items_from") == "Sales Order" and args.get("sales_order"):
		so = args.get("sales_order")
		pln.append(
			"sales_orders",
			{
				"sales_order": so.name,
				"sales_order_date": so.transaction_date,
				"customer": so.customer,
				"grand_total": so.grand_total,
			},
		)
		pln.get_items()

	if not args.get("skip_getting_mr_items"):
		mr_items = get_items_for_material_requests(pln.as_dict())
		for d in mr_items:
			pln.append("mr_items", d)

	if not args.do_not_save:
		pln.insert()
		if not args.do_not_submit:
			pln.submit()

	return pln


def make_bom(**args):
	args = frappe._dict(args)

	bom = frappe.get_doc(
		{
			"doctype": "BOM",
			"is_default": 1,
			"item": args.item,
			"currency": args.currency or "USD",
			"quantity": args.quantity or 1,
			"company": args.company or "_Test Company",
			"routing": args.routing,
			"with_operations": args.with_operations or 0,
		}
	)

	for item in args.raw_materials:
		item_doc = frappe.get_doc("Item", item)
		bom.append(
			"items",
			{
				"item_code": item,
				"qty": args.rm_qty or 1.0,
				"uom": item_doc.stock_uom,
				"stock_uom": item_doc.stock_uom,
				"rate": item_doc.valuation_rate or args.rate,
				"source_warehouse": args.source_warehouse,
			},
		)

	if not args.do_not_save:
		bom.insert(ignore_permissions=True)

		if not args.do_not_submit:
			bom.submit()

	return bom
