# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import add_to_date, flt, now_datetime, nowdate

from erpnext.controllers.item_variant import create_variant
from erpnext.manufacturing.doctype.production_plan.production_plan import (
	get_items_for_material_requests,
	get_sales_orders,
	get_warehouse_list,
)
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)


class TestProductionPlan(unittest.TestCase):
	def setUp(self):
		for item in ['Test Production Item 1', 'Subassembly Item 1',
			'Raw Material Item 1', 'Raw Material Item 2']:
			create_item(item, valuation_rate=100)

			sr = frappe.db.get_value('Stock Reconciliation Item',
				{'item_code': item, 'docstatus': 1}, 'parent')
			if sr:
				sr_doc = frappe.get_doc('Stock Reconciliation', sr)
				sr_doc.cancel()

		create_item('Test Non Stock Raw Material', is_stock_item=0)
		for item, raw_materials in {'Subassembly Item 1': ['Raw Material Item 1', 'Raw Material Item 2'],
			'Test Production Item 1': ['Raw Material Item 1', 'Subassembly Item 1',
			'Test Non Stock Raw Material']}.items():
			if not frappe.db.get_value('BOM', {'item': item}):
				make_bom(item = item, raw_materials = raw_materials)

	def test_production_plan(self):
		pln = create_production_plan(item_code='Test Production Item 1')
		self.assertTrue(len(pln.mr_items), 2)
		pln.make_material_request()

		pln = frappe.get_doc('Production Plan', pln.name)
		self.assertTrue(pln.status, 'Material Requested')
		material_requests = frappe.get_all('Material Request Item', fields = ['distinct parent'],
			filters = {'production_plan': pln.name}, as_list=1)

		self.assertTrue(len(material_requests), 2)

		pln.make_work_order()
		work_orders = frappe.get_all('Work Order', fields = ['name'],
			filters = {'production_plan': pln.name}, as_list=1)

		self.assertTrue(len(work_orders), len(pln.po_items))

		for name in material_requests:
			mr = frappe.get_doc('Material Request', name[0])
			if mr.docstatus != 0:
				mr.cancel()

		for name in work_orders:
			mr = frappe.delete_doc('Work Order', name[0])

		pln = frappe.get_doc('Production Plan', pln.name)
		pln.cancel()

	def test_production_plan_start_date(self):
		planned_date = add_to_date(date=None, days=3)
		plan = create_production_plan(item_code='Test Production Item 1', planned_start_date=planned_date)
		plan.make_work_order()

		work_orders = frappe.get_all('Work Order', fields = ['name', 'planned_start_date'],
			filters = {'production_plan': plan.name})

		self.assertEqual(work_orders[0].planned_start_date, planned_date)

		for wo in work_orders:
			frappe.delete_doc('Work Order', wo.name)

		frappe.get_doc('Production Plan', plan.name).cancel()

	def test_production_plan_for_existing_ordered_qty(self):
		sr1 = create_stock_reconciliation(item_code="Raw Material Item 1",
			target="_Test Warehouse - _TC", qty=1, rate=110)
		sr2 = create_stock_reconciliation(item_code="Raw Material Item 2",
			target="_Test Warehouse - _TC", qty=1, rate=120)

		pln = create_production_plan(item_code='Test Production Item 1', ignore_existing_ordered_qty=0)
		self.assertTrue(len(pln.mr_items), 1)
		self.assertTrue(flt(pln.mr_items[0].quantity), 1.0)

		sr1.cancel()
		sr2.cancel()
		pln.cancel()

	def test_production_plan_with_non_stock_item(self):
		pln = create_production_plan(item_code='Test Production Item 1', include_non_stock_items=0)
		self.assertTrue(len(pln.mr_items), 3)
		pln.cancel()

	def test_production_plan_without_multi_level(self):
		pln = create_production_plan(item_code='Test Production Item 1', use_multi_level_bom=0)
		self.assertTrue(len(pln.mr_items), 2)
		pln.cancel()

	def test_production_plan_without_multi_level_for_existing_ordered_qty(self):
		sr1 = create_stock_reconciliation(item_code="Raw Material Item 1",
			target="_Test Warehouse - _TC", qty=1, rate=130)
		sr2 = create_stock_reconciliation(item_code="Subassembly Item 1",
			target="_Test Warehouse - _TC", qty=1, rate=140)

		pln = create_production_plan(item_code='Test Production Item 1',
			use_multi_level_bom=0, ignore_existing_ordered_qty=0)
		self.assertTrue(len(pln.mr_items), 0)

		sr1.cancel()
		sr2.cancel()
		pln.cancel()

	def test_production_plan_sales_orders(self):
		item = 'Test Production Item 1'
		so = make_sales_order(item_code=item, qty=1)
		sales_order = so.name
		sales_order_item = so.items[0].name

		pln = frappe.new_doc('Production Plan')
		pln.company = so.company
		pln.get_items_from = 'Sales Order'

		pln.append('sales_orders', {
			'sales_order': so.name,
			'sales_order_date': so.transaction_date,
			'customer': so.customer,
			'grand_total': so.grand_total
		})

		pln.get_so_items()
		pln.submit()
		pln.make_work_order()

		work_order = frappe.db.get_value('Work Order', {'sales_order': sales_order,
			'production_plan': pln.name, 'sales_order_item': sales_order_item}, 'name')

		wo_doc = frappe.get_doc('Work Order', work_order)
		wo_doc.update({
			'wip_warehouse': 'Work In Progress - _TC',
			'fg_warehouse': 'Finished Goods - _TC'
		})
		wo_doc.submit()

		so_wo_qty = frappe.db.get_value('Sales Order Item', sales_order_item, 'work_order_qty')
		self.assertTrue(so_wo_qty, 5)

		pln = frappe.new_doc('Production Plan')
		pln.update({
			'from_date': so.transaction_date,
			'to_date': so.transaction_date,
			'customer': so.customer,
			'item_code': item,
			'sales_order_status': so.status
		})
		sales_orders = get_sales_orders(pln) or {}
		sales_orders = [d.get('name') for d in sales_orders if d.get('name') == sales_order]

		self.assertEqual(sales_orders, [])

	def test_production_plan_combine_items(self):
		item = 'Test Production Item 1'
		so = make_sales_order(item_code=item, qty=1)

		pln = frappe.new_doc('Production Plan')
		pln.company = so.company
		pln.get_items_from = 'Sales Order'
		pln.append('sales_orders', {
			'sales_order': so.name,
			'sales_order_date': so.transaction_date,
			'customer': so.customer,
			'grand_total': so.grand_total
		})
		so = make_sales_order(item_code=item, qty=2)
		pln.append('sales_orders', {
			'sales_order': so.name,
			'sales_order_date': so.transaction_date,
			'customer': so.customer,
			'grand_total': so.grand_total
		})
		pln.combine_items = 1
		pln.get_items()
		pln.submit()

		self.assertTrue(pln.po_items[0].planned_qty, 3)

		pln.make_work_order()
		work_order = frappe.db.get_value('Work Order', {
			'production_plan_item': pln.po_items[0].name,
			'production_plan': pln.name
		}, 'name')

		wo_doc = frappe.get_doc('Work Order', work_order)
		wo_doc.update({
			'wip_warehouse': 'Work In Progress - _TC',
		})

		wo_doc.submit()
		so_items = []
		for plan_reference in pln.prod_plan_references:
			so_items.append(plan_reference.sales_order_item)
			so_wo_qty = frappe.db.get_value('Sales Order Item', plan_reference.sales_order_item, 'work_order_qty')
			self.assertEqual(so_wo_qty, plan_reference.qty)

		wo_doc.cancel()
		for so_item in so_items:
			so_wo_qty = frappe.db.get_value('Sales Order Item', so_item, 'work_order_qty')
			self.assertEqual(so_wo_qty, 0.0)

		latest_plan = frappe.get_doc('Production Plan', pln.name)
		latest_plan.cancel()

	def test_pp_to_mr_customer_provided(self):
		#Material Request from Production Plan for Customer Provided
		create_item('CUST-0987', is_customer_provided_item = 1, customer = '_Test Customer', is_purchase_item = 0)
		create_item('Production Item CUST')
		for item, raw_materials in {'Production Item CUST': ['Raw Material Item 1', 'CUST-0987']}.items():
			if not frappe.db.get_value('BOM', {'item': item}):
				make_bom(item = item, raw_materials = raw_materials)
		production_plan = create_production_plan(item_code = 'Production Item CUST')
		production_plan.make_material_request()
		material_request = frappe.db.get_value('Material Request Item', {'production_plan': production_plan.name, 'item_code': 'CUST-0987'}, 'parent')
		mr = frappe.get_doc('Material Request', material_request)
		self.assertTrue(mr.material_request_type, 'Customer Provided')
		self.assertTrue(mr.customer, '_Test Customer')

	def test_production_plan_with_multi_level_bom(self):
		#|Item Code			|	Qty	|
		#|Test BOM 1	 		|	1	|
		#|	Test BOM 2		|	2	|
		#|		Test BOM 3	|	3	|

		for item_code in ["Test BOM 1", "Test BOM 2", "Test BOM 3", "Test RM BOM 1"]:
			create_item(item_code, is_stock_item=1)

		# created bom upto 3 level
		if not frappe.db.get_value('BOM', {'item': "Test BOM 3"}):
			make_bom(item = "Test BOM 3", raw_materials = ["Test RM BOM 1"], rm_qty=3)

		if not frappe.db.get_value('BOM', {'item': "Test BOM 2"}):
			make_bom(item = "Test BOM 2", raw_materials = ["Test BOM 3"], rm_qty=3)

		if not frappe.db.get_value('BOM', {'item': "Test BOM 1"}):
			make_bom(item = "Test BOM 1", raw_materials = ["Test BOM 2"], rm_qty=2)

		item_code = "Test BOM 1"
		pln = frappe.new_doc('Production Plan')
		pln.company = "_Test Company"
		pln.append("po_items", {
			"item_code": item_code,
			"bom_no": frappe.db.get_value('BOM', {'item': "Test BOM 1"}),
			"planned_qty": 3
		})

		pln.get_sub_assembly_items('In House')
		pln.submit()
		pln.make_work_order()

		#last level sub-assembly work order produce qty
		to_produce_qty = frappe.db.get_value("Work Order",
			{"production_plan": pln.name, "production_item": "Test BOM 3"}, "qty")

		self.assertEqual(to_produce_qty, 18.0)
		pln.cancel()
		frappe.delete_doc("Production Plan", pln.name)

	def test_get_warehouse_list_group(self):
		"""Check if required warehouses are returned"""
		warehouse_json = '[{\"warehouse\":\"_Test Warehouse Group - _TC\"}]'

		warehouses = set(get_warehouse_list(warehouse_json))
		expected_warehouses = {"_Test Warehouse Group-C1 - _TC", "_Test Warehouse Group-C2 - _TC"}

		missing_warehouse = expected_warehouses - warehouses

		self.assertTrue(len(missing_warehouse) == 0,
				msg=f"Following warehouses were expected {', '.join(missing_warehouse)}")

	def test_get_warehouse_list_single(self):
		warehouse_json = '[{\"warehouse\":\"_Test Scrap Warehouse - _TC\"}]'

		warehouses = set(get_warehouse_list(warehouse_json))
		expected_warehouses = {"_Test Scrap Warehouse - _TC", }

		self.assertEqual(warehouses, expected_warehouses)

	def test_get_sales_order_with_variant(self):
		rm_item = create_item('PIV_RM', valuation_rate = 100)
		if not frappe.db.exists('Item', {"item_code": 'PIV'}):
			item = create_item('PIV', valuation_rate = 100)
			variant_settings = {
				"attributes": [
					{
						"attribute": "Colour"
					},
				],
				"has_variants": 1
			}
			item.update(variant_settings)
			item.save()
			parent_bom = make_bom(item = 'PIV', raw_materials = [rm_item.item_code])
		if not frappe.db.exists('BOM', {"item": 'PIV'}):
			parent_bom = make_bom(item = 'PIV', raw_materials = [rm_item.item_code])
		else:
			parent_bom = frappe.get_doc('BOM', {"item": 'PIV'})

		if not frappe.db.exists('Item', {"item_code": 'PIV-RED'}):
			variant = create_variant("PIV", {"Colour": "Red"})
			variant.save()
			variant_bom = make_bom(item = variant.item_code, raw_materials = [rm_item.item_code])
		else:
			variant = frappe.get_doc('Item', 'PIV-RED')
		if not frappe.db.exists('BOM', {"item": 'PIV-RED'}):
			variant_bom = make_bom(item = variant.item_code, raw_materials = [rm_item.item_code])

		"""Testing when item variant has a BOM"""
		so = make_sales_order(item_code="PIV-RED", qty=5)
		pln = frappe.new_doc('Production Plan')
		pln.company = so.company
		pln.get_items_from = 'Sales Order'
		pln.item_code = 'PIV-RED'
		pln.get_open_sales_orders()
		self.assertEqual(pln.sales_orders[0].sales_order, so.name)
		pln.get_so_items()
		self.assertEqual(pln.po_items[0].item_code, 'PIV-RED')
		self.assertEqual(pln.po_items[0].bom_no, variant_bom.name)
		so.cancel()
		frappe.delete_doc('Sales Order', so.name)
		variant_bom.cancel()
		frappe.delete_doc('BOM', variant_bom.name)

		"""Testing when item variant doesn't have a BOM"""
		so = make_sales_order(item_code="PIV-RED", qty=5)
		pln.get_open_sales_orders()
		self.assertEqual(pln.sales_orders[0].sales_order, so.name)
		pln.po_items = []
		pln.get_so_items()
		self.assertEqual(pln.po_items[0].item_code, 'PIV-RED')
		self.assertEqual(pln.po_items[0].bom_no, parent_bom.name)

		frappe.db.rollback()

def create_production_plan(**args):
	args = frappe._dict(args)

	pln = frappe.get_doc({
		'doctype': 'Production Plan',
		'company': args.company or '_Test Company',
		'customer': args.customer or '_Test Customer',
		'posting_date': nowdate(),
		'include_non_stock_items': args.include_non_stock_items or 1,
		'include_subcontracted_items': args.include_subcontracted_items or 1,
		'ignore_existing_ordered_qty': args.ignore_existing_ordered_qty or 1,
		'po_items': [{
			'use_multi_level_bom': args.use_multi_level_bom or 1,
			'item_code': args.item_code,
			'bom_no': frappe.db.get_value('Item', args.item_code, 'default_bom'),
			'planned_qty': args.planned_qty or 1,
			'planned_start_date': args.planned_start_date or now_datetime()
		}]
	})
	mr_items = get_items_for_material_requests(pln.as_dict())
	for d in mr_items:
		pln.append('mr_items', d)

	if not args.do_not_save:
		pln.insert()
		if not args.do_not_submit:
			pln.submit()

	return pln

def make_bom(**args):
	args = frappe._dict(args)

	bom = frappe.get_doc({
		'doctype': 'BOM',
		'is_default': 1,
		'item': args.item,
		'currency': args.currency or 'USD',
		'quantity': args.quantity or 1,
		'company': args.company or '_Test Company',
		'routing': args.routing,
		'with_operations': args.with_operations or 0
	})

	for item in args.raw_materials:
		item_doc = frappe.get_doc('Item', item)

		bom.append('items', {
			'item_code': item,
			'qty': args.rm_qty or 1.0,
			'uom': item_doc.stock_uom,
			'stock_uom': item_doc.stock_uom,
			'rate': item_doc.valuation_rate or args.rate,
			'source_warehouse': args.source_warehouse
		})

	if not args.do_not_save:
		bom.insert(ignore_permissions=True)

		if not args.do_not_submit:
			bom.submit()

	return bom
