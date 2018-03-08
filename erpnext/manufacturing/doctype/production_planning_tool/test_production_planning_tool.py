# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
import frappe.defaults
import unittest
from frappe.test_runner import make_test_records

from erpnext.manufacturing.doctype.production_planning_tool.production_planning_tool import ProductionPlanningTool

# load test records and dependencies

test_records = frappe.get_test_records('Production Planning Tool')

test_dependencies = ["Item","BOM"]

class TestEvent(unittest.TestCase):

	def test_materials_requests_all_raw_multi_level(self):
		items = ["_Test PPT Item Raw A","_Test PPT Item Raw B","_Test PPT Item Raw C","_Test PPT Item Raw D",
			"_Test PPT Item Sub A","_Test PPT Item Sub B","_Test PPT Item Sub C","_Test PPT Item SC A",
			"_Test PPT Item SC B","_Test PPT Item Master"]
		quantities = [14,9,36,1,0,0,0,0,0,0]
		types = ["Purchase","Purchase","Purchase","Purchase","Manufacture","Manufacture","Manufacture","Purchase",
			"Purchase","Manufacture"]

		self.runtest_materials_requests(items, quantities, types, use_multi_level_bom=1, only_raw_materials=1, \
			include_subcontracted=1)

	def test_materials_requests_multi_no_subcontracted(self):
		items = ["_Test PPT Item Raw A","_Test PPT Item Raw B","_Test PPT Item Raw C","_Test PPT Item Raw D",
			"_Test PPT Item Sub A","_Test PPT Item Sub B","_Test PPT Item Sub C","_Test PPT Item SC A",
			"_Test PPT Item SC B","_Test PPT Item Master"]
		quantities = [14,5,20,0,0,0,0,0,0,0]
		types = ["Purchase","Purchase","Purchase","Purchase","Manufacture","Manufacture","Manufacture","Purchase",
			"Purchase","Manufacture"]

		# This one should fail for now
		self.runtest_materials_requests(items, quantities, types, use_multi_level_bom=1, only_raw_materials=1, \
			include_subcontracted=0)



	def test_materials_requests_manufacture_and_sub_multi_level(self):
		items = ["_Test PPT Item Raw A","_Test PPT Item Raw B","_Test PPT Item Raw C","_Test PPT Item Raw D",
			"_Test PPT Item Sub A","_Test PPT Item Sub B","_Test PPT Item Sub C","_Test PPT Item SC A",
			"_Test PPT Item SC B","_Test PPT Item Master"]
		quantities = [14,9,36,1,2,5,2,1,4,0]
		types = ["Purchase","Purchase","Purchase","Purchase","Manufacture","Manufacture","Manufacture","Purchase",
			"Purchase","Manufacture"]

		self.runtest_materials_requests(items, quantities, types, use_multi_level_bom=1, only_raw_materials=0, \
			include_subcontracted=1)

	def test_materials_requests_manufacture_multi_level(self):
		items = ["_Test PPT Item Raw A","_Test PPT Item Raw B","_Test PPT Item Raw C","_Test PPT Item Raw D",
			"_Test PPT Item Sub A","_Test PPT Item Sub B","_Test PPT Item Sub C","_Test PPT Item SC A",
			"_Test PPT Item SC B","_Test PPT Item Master"]
		quantities = [14,5,20,0,2,5,2,1,4,0]
		types = ["Purchase","Purchase","Purchase","Purchase","Manufacture","Manufacture","Manufacture","Purchase",
			"Purchase","Manufacture"]

		self.runtest_materials_requests(items, quantities, types, use_multi_level_bom=1, only_raw_materials=0, \
			include_subcontracted=0)



	def test_materials_requests_single_level_purch_only(self):
		items = ["_Test PPT Item Raw A","_Test PPT Item Raw B","_Test PPT Item Raw C","_Test PPT Item Raw D",
			"_Test PPT Item Sub A","_Test PPT Item Sub B","_Test PPT Item Sub C","_Test PPT Item SC A",
			"_Test PPT Item SC B","_Test PPT Item Master"]
		quantities = [2,0,0,0,0,0,0,1,0,0]
		types = ["Purchase","Purchase","Purchase","Purchase","Manufacture","Manufacture","Manufacture","Purchase",
			"Purchase","Manufacture"]

		self.runtest_materials_requests(items, quantities, types, use_multi_level_bom=0, only_raw_materials=1, \
			include_subcontracted=0)

	def test_materials_requests_single_level(self):
		items = ["_Test PPT Item Raw A","_Test PPT Item Raw B","_Test PPT Item Raw C","_Test PPT Item Raw D",
			"_Test PPT Item Sub A","_Test PPT Item Sub B","_Test PPT Item Sub C","_Test PPT Item SC A",
			"_Test PPT Item SC B","_Test PPT Item Master"]
		quantities = [2,0,0,0,2,1,0,1,0,0]
		types = ["Purchase","Purchase","Purchase","Purchase","Manufacture","Manufacture","Manufacture","Purchase",
			"Purchase","Manufacture"]

		self.runtest_materials_requests(items, quantities, types, use_multi_level_bom=0, only_raw_materials=0, \
			include_subcontracted=0)

	def runtest_materials_requests(self, items, quantities, types,use_multi_level_bom, only_raw_materials, \
		include_subcontracted):

		clear_material_requests()
		create_test_records()

		ppt = run_production_planning_tool(use_multi_level_bom=use_multi_level_bom,
			only_raw_materials=only_raw_materials, include_subcontracted=include_subcontracted,
			item_code = "_Test PPT Item Master", bom_no = "BOM-_Test PPT Item Master-001",
			planned_qty = 1, planned_start_date = "5/5/2029",
			warehouse = "_Test Warehouse - _TC", company = "_Test Company")

		create_material_requests(ppt)

		for item, qty, type in zip(items, quantities, types):
			self.assertEqual(qty, get_requested_qty(item))
			for mat_req_type in get_requested_types(item):
				self.assertEqual(type, mat_req_type)

def create_test_records():
	from erpnext.stock.doctype.item.test_item import make_item

	subA = make_item("_Test PPT Item Sub A",{
		"item_code": "_Test PPT Item Sub A",
		"item_name": "_Test PPT Item Sub A",
		"description": "A manufactured _Test PPT Item Sub Assembly",
		"default_material_request_type": "Manufacture",
		"is_sub_contracted_item": 0,
		"is_stock_item": 1,
		"stock_uom": "_Test UOM",
		"item_group": "_Test Item Group",
		"default_warehouse": "_Test Warehouse - _TC"})

	subB = make_item("_Test PPT Item Sub B",{
		"item_code": "_Test PPT Item Sub B",
		"item_name": "_Test PPT Item Sub B",
		"description": "A manufactured _Test PPT Item Sub Assembly",
		"default_material_request_type": "Manufacture",
		"is_sub_contracted_item": 0,
		"is_stock_item": 1,
		"stock_uom": "_Test UOM",
		"item_group": "_Test Item Group",
		"default_warehouse": "_Test Warehouse - _TC"})

	subC = make_item("_Test PPT Item Sub C",{
		"item_code": "_Test PPT Item Sub C",
		"item_name": "_Test PPT Item Sub C",
		"description": "A manufactured _Test PPT Item Sub Assembly",
		"default_material_request_type": "Manufacture",
		"is_sub_contracted_item": 0,
		"is_stock_item": 1,
		"stock_uom": "_Test UOM",
		"item_group": "_Test Item Group",
		"default_warehouse": "_Test Warehouse - _TC"})

	sCA = make_item("_Test PPT Item SC A",{
		"item_code": "_Test PPT Item SC A",
		"item_name": "_Test PPT Item SC A",
		"description": "A subcontracted part with raw materials",
		"default_material_request_type": "Purchase",
		"is_sub_contracted_item": 1,
		"is_stock_item": 1,
		"stock_uom": "_Test UOM",
		"item_group": "_Test Item Group",
		"default_warehouse": "_Test Warehouse - _TC"})
	subA = make_item("_Test PPT Item Sub A",{
		"item_code": "_Test PPT Item Sub A",
		"item_name": "_Test PPT Item Sub A",
		"description": "A manufactured _Test PPT Item Sub Assembly",
		"default_material_request_type": "Manufacture",
		"is_sub_contracted_item": 0,
		"is_stock_item": 1,
		"stock_uom": "_Test UOM",
		"item_group": "_Test Item Group",
		"default_warehouse": "_Test Warehouse - _TC"})
	sCB = make_item("_Test PPT Item SC B",{
		"item_code": "_Test PPT Item SC B",
		"item_name": "_Test PPT Item SC B",
		"description": "A subcontracted part with raw materials",
		"default_material_request_type": "Purchase",
		"is_sub_contracted_item": 1,
		"is_stock_item": 1,
		"stock_uom": "_Test UOM",
		"item_group": "_Test Item Group",
		"default_warehouse": "_Test Warehouse - _TC"})

	rawA = make_item("_Test PPT Item Raw A",{
		"item_code": "_Test PPT Item Raw A",
		"item_name": "_Test PPT Item Raw A",
		"description": "A raw material",
		"default_material_request_type": "Purchase",
		"is_sub_contracted_item": 0,
		"is_stock_item": 1,
		"stock_uom": "_Test UOM",
		"item_group": "_Test Item Group",
		"default_warehouse": "_Test Warehouse - _TC"})

	rawB = make_item("_Test PPT Item Raw B",{
		"item_code": "_Test PPT Item Raw B",
		"item_name": "_Test PPT Item Raw B",
		"description": "A raw material",
		"default_material_request_type": "Purchase",
		"is_sub_contracted_item": 0,
		"is_stock_item": 1,
		"stock_uom": "_Test UOM",
		"item_group": "_Test Item Group",
		"default_warehouse": "_Test Warehouse - _TC"})

	rawC = make_item("_Test PPT Item Raw C",{
		"item_code": "_Test PPT Item Raw C",
		"item_name": "_Test PPT Item Raw C",
		"description": "A raw material",
		"default_material_request_type": "Purchase",
		"is_sub_contracted_item": 0,
		"is_stock_item": 1,
		"stock_uom": "_Test UOM",
		"item_group": "_Test Item Group",
		"default_warehouse": "_Test Warehouse - _TC"})

	rawD = make_item("_Test PPT Item Raw D",{
		"item_code": "_Test PPT Item Raw D",
		"item_name": "_Test PPT Item Raw D",
		"description": "A raw material",
		"default_material_request_type": "Purchase",
		"is_sub_contracted_item": 0,
		"is_stock_item": 1,
		"stock_uom": "_Test UOM",
		"item_group": "_Test Item Group",
		"default_warehouse": "_Test Warehouse - _TC"})

	master = make_item("_Test PPT Item Master",{
		"item_code": "_Test PPT Item Master",
		"item_name": "_Test PPT Item Master",
		"description": "The final assembly",
		"default_material_request_type": "Manufacture",
		"is_sub_contracted_item": 0,
		"is_stock_item": 1,
		"stock_uom": "_Test UOM",
		"item_group": "_Test Item Group",
		"default_warehouse": "_Test Warehouse - _TC"})



	bom_subB = make_bom("BOM-_Test PPT Item Sub B-001",{"quantity":1.0,
		"item": "_Test PPT Item Sub B",
		"is_active": 1,
		"is_default": 1,
		"docstatus": 1,
		"with_operations": 0}, [{"item_code": "_Test PPT Item Raw B", "doctype":"BOM Item", "stock_qty":1,
				"rate":100, "amount": 100, "stock_uom": "_Test UOM"},
			{"item_code": "_Test PPT Item Raw C", "doctype":"BOM Item", "stock_qty":4, "rate":100,
				"amount": 400,"stock_uom": "_Test UOM"}])

	bom_subC = make_bom("BOM-_Test PPT Item Sub C-001",{"quantity":1,
		"item": "_Test PPT Item Sub C",
		"is_active": 1,
		"is_default": 1,
		"docstatus": 1,
		"with_operations": 0}, [
			{"item_code": "_Test PPT Item Raw A","item_name": "_Test PPT Item Raw A",
				"doctype":"BOM Item", "stock_qty":6, "rate":100, "amount": 600},
			{"item_code": "_Test PPT Item Sub B","item_name": "_Test PPT Item Sub B",
				"bom_no":"BOM-_Test PPT Item Sub B-001", "doctype":"BOM Item", "stock_qty":2,
				"rate":100, "amount": 200}])

	bom_sCA = make_bom("BOM-_Test PPT Item SC A-001",{"quantity":1,
		"item": "_Test PPT Item SC A",
		"is_active": 1,
		"is_default": 1,
		"docstatus": 1,
		"with_operations": 0}, [
			{"item_code": "_Test PPT Item Raw D","item_name": "_Test PPT Item Raw D",
				"doctype":"BOM Item", "stock_qty":1, "rate":100, "amount": 100}])

	bom_sCB = make_bom("BOM-_Test PPT Item SC B-001",{"quantity":1,
		"item": "_Test PPT Item SC B",
		"is_active": 1,
		"is_default": 1,
		"docstatus": 1,
		"with_operations": 0}, [
			{"item_code": "_Test PPT Item Raw B","item_name": "_Test PPT Item Raw B",
				"doctype":"BOM Item", "stock_qty":1, "rate":100, "amount": 100},
			{"item_code": "_Test PPT Item Raw C","item_name": "_Test PPT Item Raw C",
				"doctype":"BOM Item", "stock_qty":4, "rate":100, "amount": 400}])

	bom_subA = make_bom("BOM-_Test PPT Item Sub A-001",{"quantity":1,
		"item": "_Test PPT Item Sub A",
		"is_active": 1,
		"is_default": 1,
		"docstatus": 1,
		"with_operations": 0}, [
			{"item_code": "_Test PPT Item Sub C","item_name": "_Test PPT Item Sub C",
				"bom_no":"BOM-_Test PPT Item Sub C-001", "doctype":"BOM Item",
				"stock_qty":1, "rate":100, "amount": 100},
			{"item_code": "_Test PPT Item SC B","item_name": "_Test PPT Item SC B",
				"bom_no":"BOM-_Test PPT Item SC B-001", "doctype":"BOM Item", "stock_qty":2,
				"rate":100, "amount": 200}])

	bom_master = make_bom("BOM-_Test PPT Item Master-001",{"quantity":1,
		"item": "_Test PPT Item Master",
		"is_active": 1,
		"is_default": 1,
		"docstatus": 1,
		"with_operations": 0}, [
			{"item_code": "_Test PPT Item Sub A","item_name": "_Test PPT Item Sub A",
				"bom_no":"BOM-_Test PPT Item Sub A-001",
				"doctype":"BOM Item", "stock_qty":2, "rate":100, "amount": 200},
			{"item_code": "_Test PPT Item Sub B","item_name": "_Test PPT Item Sub B",
				"bom_no":"BOM-_Test PPT Item Sub B-001",
				"doctype":"BOM Item", "stock_qty":1, "rate":100, "amount": 100},
			{"item_code": "_Test PPT Item Raw A","item_name": "_Test PPT Item Raw A",
				"doctype":"BOM Item", "stock_qty":2, "rate":100,
				"amount": 200},
			{"item_code": "_Test PPT Item SC A","item_name": "_Test PPT Item SC A",
				"bom_no":"BOM-_Test PPT Item SC A-001",
				"doctype":"BOM Item", "stock_qty":1, "rate":100, "amount": 100}
			])


def make_bom(name, properties=None, items=None):
	if frappe.db.exists("BOM", name):
		return frappe.get_doc("BOM", name)

	bom = frappe.new_doc("BOM")
	item = frappe.get_doc({
		"doctype": "BOM",
		"name": name,
		"quantity": "1",
		"with_operations": 0
	})

	if properties:
		bom.update(properties)

	if items:
		for item in items:
			bom.append("items", item)


	bom.insert()
	bom.submit()

	return bom

def clear_material_requests():
	frappe.db.sql("delete from `tabMaterial Request Item`")
	frappe.db.sql("delete from `tabMaterial Request`")


def run_production_planning_tool(**args):
	ppt = frappe.new_doc("Production Planning Tool")
	args = frappe._dict(args)

	if args.use_multi_level_bom:
		ppt.use_multi_level_bom = args.use_multi_level_bom
	else:
		ppt.use_multi_level_bom = 0

	if args.only_raw_materials:
		ppt.only_raw_materials = args.only_raw_materials
	else:
		ppt.only_raw_materials = 0

	if args.include_subcontracted:
		ppt.include_subcontracted = args.include_subcontracted
	else:
		ppt.include_subcontracted = 0

	if args.warehouse:
		ppt.purchase_request_for_warehouse = args.warehouse

	if args.company:
		ppt.company = args.company
	ppt.create_material_requests_for_all_required_qty = 1

	ppt.append("items",{"item_code": args.item_code, "bom_no": args.bom_no, "planned_qty": args.planned_qty,
		"planned_start_date": args.planned_start_date, "warehouse": args.warehouse})

	return ppt

def create_material_requests(ppt):
	ppt.raise_material_requests()

def get_requested_qty(item_code):
	total_qty = 0
	for d in frappe.db.sql("""select item.qty as qty
		from `tabMaterial Request` mat_req, `tabMaterial Request Item` item
		where item.item_code = %(item_code)s and item.parent = mat_req.name""", {"item_code":item_code}, as_dict=1):
		total_qty += d.qty
	return total_qty

def get_requested_types(item_code):
	types = []
	for d in frappe.db.sql("""select mat_req.material_request_type as type
		from `tabMaterial Request` mat_req, `tabMaterial Request Item` item
		where item.item_code = %(item_code)s and item.parent = mat_req.name""", {"item_code":item_code}, as_dict=1):
		types.append(d.type)
	return types

