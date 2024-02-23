# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from erpnext.controllers.subcontracting_controller import make_rm_stock_entry
from erpnext.controllers.tests.test_subcontracting_controller import (
	get_subcontracting_order,
	make_service_item,
	set_backflush_based_on,
)
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import (
	EmptyStockReconciliationItemsError,
)
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)
from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
	make_subcontracting_receipt,
)


class TestItemAlternative(FrappeTestCase):
	def setUp(self):
		super().setUp()
		make_items()

	def test_alternative_item_for_subcontract_rm(self):
		set_backflush_based_on("BOM")

		create_stock_reconciliation(
			item_code="Alternate Item For A RW 1", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)
		create_stock_reconciliation(
			item_code="Test FG A RW 2", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)

		supplier_warehouse = "Test Supplier Warehouse - _TC"

		make_service_item("Subcontracted Service Item 1")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 5,
				"rate": 3000,
				"fg_item": "Test Finished Goods - A",
				"fg_item_qty": 5,
			},
		]
		sco = get_subcontracting_order(
			service_items=service_items, supplier_warehouse=supplier_warehouse
		)
		rm_items = [
			{
				"item_code": "Test Finished Goods - A",
				"rm_item_code": "Test FG A RW 1",
				"item_name": "Test FG A RW 1",
				"qty": 5,
				"warehouse": "_Test Warehouse - _TC",
				"rate": 2000,
				"amount": 10000,
				"stock_uom": "Nos",
			},
			{
				"item_code": "Test Finished Goods - A",
				"rm_item_code": "Test FG A RW 2",
				"item_name": "Test FG A RW 2",
				"qty": 5,
				"warehouse": "_Test Warehouse - _TC",
				"rate": 2000,
				"amount": 10000,
				"stock_uom": "Nos",
			},
		]

		reserved_qty_for_sub_contract = frappe.db.get_value(
			"Bin",
			{"item_code": "Test FG A RW 1", "warehouse": "_Test Warehouse - _TC"},
			"reserved_qty_for_sub_contract",
		)

		se = frappe.get_doc(make_rm_stock_entry(sco.name, rm_items))
		se.to_warehouse = supplier_warehouse
		se.insert()

		doc = frappe.get_doc("Stock Entry", se.name)
		for item in doc.items:
			if item.item_code == "Test FG A RW 1":
				item.item_code = "Alternate Item For A RW 1"
				item.item_name = "Alternate Item For A RW 1"
				item.description = "Alternate Item For A RW 1"
				item.original_item = "Test FG A RW 1"

		doc.save()
		doc.submit()
		after_transfer_reserved_qty_for_sub_contract = frappe.db.get_value(
			"Bin",
			{"item_code": "Test FG A RW 1", "warehouse": "_Test Warehouse - _TC"},
			"reserved_qty_for_sub_contract",
		)

		self.assertEqual(
			after_transfer_reserved_qty_for_sub_contract, flt(reserved_qty_for_sub_contract - 5)
		)

		scr = make_subcontracting_receipt(sco.name)
		scr.save()

		scr = frappe.get_doc("Subcontracting Receipt", scr.name)
		status = False
		for item in scr.supplied_items:
			if item.rm_item_code == "Alternate Item For A RW 1":
				status = True

		self.assertEqual(status, True)
		set_backflush_based_on("Material Transferred for Subcontract")

	def test_alternative_item_for_production_rm(self):
		create_stock_reconciliation(
			item_code="Alternate Item For A RW 1", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)
		create_stock_reconciliation(
			item_code="Test FG A RW 2", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)
		pro_order = make_wo_order_test_record(
			production_item="Test Finished Goods - A",
			qty=5,
			source_warehouse="_Test Warehouse - _TC",
			wip_warehouse="Test Supplier Warehouse - _TC",
		)

		reserved_qty_for_production = frappe.db.get_value(
			"Bin",
			{"item_code": "Test FG A RW 1", "warehouse": "_Test Warehouse - _TC"},
			"reserved_qty_for_production",
		)

		ste = frappe.get_doc(make_stock_entry(pro_order.name, "Material Transfer for Manufacture", 5))
		ste.insert()

		for item in ste.items:
			if item.item_code == "Test FG A RW 1":
				item.item_code = "Alternate Item For A RW 1"
				item.item_name = "Alternate Item For A RW 1"
				item.description = "Alternate Item For A RW 1"
				item.original_item = "Test FG A RW 1"

		ste.submit()
		reserved_qty_for_production_after_transfer = frappe.db.get_value(
			"Bin",
			{"item_code": "Test FG A RW 1", "warehouse": "_Test Warehouse - _TC"},
			"reserved_qty_for_production",
		)

		self.assertEqual(
			reserved_qty_for_production_after_transfer, flt(reserved_qty_for_production - 5)
		)
		ste1 = frappe.get_doc(make_stock_entry(pro_order.name, "Manufacture", 5))

		status = False
		for d in ste1.items:
			if d.item_code == "Alternate Item For A RW 1":
				status = True

		self.assertEqual(status, True)
		ste1.submit()


def make_items():
	items = [
		"Test Finished Goods - A",
		"Test FG A RW 1",
		"Test FG A RW 2",
		"Alternate Item For A RW 1",
	]
	for item_code in items:
		if not frappe.db.exists("Item", item_code):
			create_item(item_code)

	try:
		create_stock_reconciliation(
			item_code="Test FG A RW 1", warehouse="_Test Warehouse - _TC", qty=10, rate=2000
		)
	except EmptyStockReconciliationItemsError:
		pass

	if frappe.db.exists("Item", "Test FG A RW 1"):
		doc = frappe.get_doc("Item", "Test FG A RW 1")
		doc.allow_alternative_item = 1
		doc.save()

	if frappe.db.exists("Item", "Test Finished Goods - A"):
		doc = frappe.get_doc("Item", "Test Finished Goods - A")
		doc.is_sub_contracted_item = 1
		doc.save()

	if not frappe.db.get_value("BOM", {"item": "Test Finished Goods - A", "docstatus": 1}):
		make_bom(item="Test Finished Goods - A", raw_materials=["Test FG A RW 1", "Test FG A RW 2"])

	if not frappe.db.get_value("Warehouse", {"warehouse_name": "Test Supplier Warehouse"}):
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Test Supplier Warehouse",
				"company": "_Test Company",
			}
		).insert(ignore_permissions=True)
