# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import copy
from collections import defaultdict

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from erpnext.buying.doctype.purchase_order.purchase_order import get_mapped_subcontracting_order
from erpnext.controllers.subcontracting_controller import (
	get_materials_from_supplier,
	make_rm_stock_entry,
)
from erpnext.controllers.tests.test_subcontracting_controller import (
	get_rm_items,
	get_subcontracting_order,
	make_bom_for_subcontracted_items,
	make_raw_materials,
	make_service_items,
	make_stock_in_entry,
	make_stock_transfer_entry,
	make_subcontracted_item,
	make_subcontracted_items,
	set_backflush_based_on,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
	make_subcontracting_receipt,
)


class TestSubcontractingOrder(FrappeTestCase):
	def setUp(self):
		make_subcontracted_items()
		make_raw_materials()
		make_service_items()
		make_bom_for_subcontracted_items()

	def test_populate_items_table(self):
		sco = get_subcontracting_order()
		sco.items = None
		sco.populate_items_table()
		self.assertEqual(len(sco.service_items), len(sco.items))

	def test_set_missing_values(self):
		sco = get_subcontracting_order()
		before = {sco.total_qty, sco.total, sco.total_additional_costs}
		sco.total_qty = sco.total = sco.total_additional_costs = 0
		sco.set_missing_values()
		after = {sco.total_qty, sco.total, sco.total_additional_costs}
		self.assertSetEqual(before, after)

	def test_update_status(self):
		# Draft
		sco = get_subcontracting_order(do_not_submit=1)
		self.assertEqual(sco.status, "Draft")

		# Open
		sco.submit()
		sco.load_from_db()
		self.assertEqual(sco.status, "Open")

		# Partial Material Transferred
		rm_items = get_rm_items(sco.supplied_items)
		rm_items[0]["qty"] -= 1
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		sco.load_from_db()
		self.assertEqual(sco.status, "Partial Material Transferred")

		# Material Transferred
		rm_items[0]["qty"] = 1
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		sco.load_from_db()
		self.assertEqual(sco.status, "Material Transferred")

		# Partially Received
		scr = make_subcontracting_receipt(sco.name)
		scr.items[0].qty -= 1
		scr.save()
		scr.submit()
		sco.load_from_db()
		self.assertEqual(sco.status, "Partially Received")

		# Closed
		sco.update_status("Closed")
		self.assertEqual(sco.status, "Closed")
		scr = make_subcontracting_receipt(sco.name)
		scr.save()
		self.assertRaises(frappe.exceptions.ValidationError, scr.submit)
		sco.update_status()
		self.assertEqual(sco.status, "Partially Received")
		scr.cancel()

		# Completed
		scr = make_subcontracting_receipt(sco.name)
		scr.save()
		scr.submit()
		sco.load_from_db()
		self.assertEqual(sco.status, "Completed")

		# Partially Received (scr cancelled)
		scr.load_from_db()
		scr.cancel()
		sco.load_from_db()
		self.assertEqual(sco.status, "Partially Received")

	def test_make_rm_stock_entry(self):
		sco = get_subcontracting_order()
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		ste = make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		self.assertEqual(len(ste.items), len(rm_items))

	def test_make_rm_stock_entry_for_serial_items(self):
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 2",
				"qty": 5,
				"rate": 100,
				"fg_item": "Subcontracted Item SA2",
				"fg_item_qty": 5,
			},
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 5",
				"qty": 6,
				"rate": 100,
				"fg_item": "Subcontracted Item SA5",
				"fg_item_qty": 6,
			},
		]

		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		ste = make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		self.assertEqual(len(ste.items), len(rm_items))

	def test_make_rm_stock_entry_for_batch_items(self):
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 4",
				"qty": 5,
				"rate": 100,
				"fg_item": "Subcontracted Item SA4",
				"fg_item_qty": 5,
			},
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 6",
				"qty": 6,
				"rate": 100,
				"fg_item": "Subcontracted Item SA6",
				"fg_item_qty": 6,
			},
		]

		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		ste = make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		self.assertEqual(len(ste.items), len(rm_items))

	def test_make_rm_stock_entry_for_batch_items_with_less_transfer(self):
		set_backflush_based_on("BOM")

		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 4",
				"qty": 5,
				"rate": 100,
				"fg_item": "Subcontracted Item SA4",
				"fg_item_qty": 5,
			}
		]

		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		itemwise_transfer_qty = defaultdict(int)
		for item in rm_items:
			item["qty"] -= 1
			itemwise_transfer_qty[item["item_code"]] += item["qty"]

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr = make_subcontracting_receipt(sco.name)

		for row in scr.supplied_items:
			self.assertEqual(row.consumed_qty, itemwise_transfer_qty.get(row.rm_item_code) + 1)

	def test_update_reserved_qty_for_subcontracting(self):
		# Create RM Material Receipt
		make_stock_entry(target="_Test Warehouse - _TC", item_code="_Test Item", qty=10, basic_rate=100)
		make_stock_entry(
			target="_Test Warehouse - _TC", item_code="_Test Item Home Desktop 100", qty=20, basic_rate=100
		)

		bin_before_sco = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname=["reserved_qty_for_sub_contract", "projected_qty", "modified"],
			as_dict=1,
		)

		# Create SCO
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 10,
				"rate": 100,
				"fg_item": "_Test FG Item",
				"fg_item_qty": 10,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)

		bin_after_sco = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname=["reserved_qty_for_sub_contract", "projected_qty", "modified"],
			as_dict=1,
		)

		# reserved_qty_for_sub_contract should be increased by 10
		self.assertEqual(
			bin_after_sco.reserved_qty_for_sub_contract, bin_before_sco.reserved_qty_for_sub_contract + 10
		)

		# projected_qty should be decreased by 10
		self.assertEqual(bin_after_sco.projected_qty, bin_before_sco.projected_qty - 10)

		self.assertNotEqual(bin_before_sco.modified, bin_after_sco.modified)

		# Create Stock Entry(Send to Subcontractor)
		rm_items = [
			{
				"item_code": "_Test FG Item",
				"rm_item_code": "_Test Item",
				"item_name": "_Test Item",
				"qty": 10,
				"warehouse": "_Test Warehouse - _TC",
				"rate": 100,
				"amount": 1000,
				"stock_uom": "Nos",
			},
			{
				"item_code": "_Test FG Item",
				"rm_item_code": "_Test Item Home Desktop 100",
				"item_name": "_Test Item Home Desktop 100",
				"qty": 20,
				"warehouse": "_Test Warehouse - _TC",
				"rate": 100,
				"amount": 2000,
				"stock_uom": "Nos",
			},
		]
		ste = frappe.get_doc(make_rm_stock_entry(sco.name, rm_items))
		ste.to_warehouse = "_Test Warehouse 1 - _TC"
		ste.save()
		ste.submit()

		bin_after_rm_transfer = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract",
			as_dict=1,
		)

		# reserved_qty_for_sub_contract should be decreased by 10
		self.assertEqual(
			bin_after_rm_transfer.reserved_qty_for_sub_contract,
			bin_after_sco.reserved_qty_for_sub_contract - 10,
		)

		# Cancel Stock Entry(Send to Subcontractor)
		ste.cancel()
		bin_after_cancel_ste = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract",
			as_dict=1,
		)

		# reserved_qty_for_sub_contract should be increased by 10
		self.assertEqual(
			bin_after_cancel_ste.reserved_qty_for_sub_contract,
			bin_after_rm_transfer.reserved_qty_for_sub_contract + 10,
		)

		# Cancel SCO
		sco.reload()
		sco.cancel()
		bin_after_cancel_sco = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract",
			as_dict=1,
		)

		# reserved_qty_for_sub_contract should be decreased by 10
		self.assertEqual(
			bin_after_cancel_sco.reserved_qty_for_sub_contract,
			bin_after_cancel_ste.reserved_qty_for_sub_contract - 10,
		)
		self.assertEqual(
			bin_after_cancel_sco.reserved_qty_for_sub_contract, bin_before_sco.reserved_qty_for_sub_contract
		)

	def test_exploded_items(self):
		item_code = "_Test Subcontracted FG Item 11"
		make_subcontracted_item(item_code=item_code)

		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 1,
				"rate": 100,
				"fg_item": item_code,
				"fg_item_qty": 1,
			},
		]

		sco1 = get_subcontracting_order(service_items=service_items, include_exploded_items=1)
		item_name = frappe.db.get_value("BOM", {"item": item_code}, "name")
		bom = frappe.get_doc("BOM", item_name)
		exploded_items = sorted([item.item_code for item in bom.exploded_items])
		supplied_items = sorted([item.rm_item_code for item in sco1.supplied_items])
		self.assertEqual(exploded_items, supplied_items)

		sco2 = get_subcontracting_order(service_items=service_items, include_exploded_items=0)
		supplied_items1 = sorted([item.rm_item_code for item in sco2.supplied_items])
		bom_items = sorted([item.item_code for item in bom.items])
		self.assertEqual(supplied_items1, bom_items)

	def test_backflush_based_on_stock_entry(self):
		item_code = "_Test Subcontracted FG Item 1"
		make_subcontracted_item(item_code=item_code)
		make_item("Sub Contracted Raw Material 1", {"is_stock_item": 1, "is_sub_contracted_item": 1})

		set_backflush_based_on("Material Transferred for Subcontract")

		order_qty = 5
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": order_qty,
				"rate": 100,
				"fg_item": item_code,
				"fg_item_qty": order_qty,
			},
		]

		sco = get_subcontracting_order(service_items=service_items)

		make_stock_entry(
			target="_Test Warehouse - _TC", item_code="_Test Item Home Desktop 100", qty=20, basic_rate=100
		)
		make_stock_entry(
			target="_Test Warehouse - _TC", item_code="Test Extra Item 1", qty=100, basic_rate=100
		)
		make_stock_entry(
			target="_Test Warehouse - _TC", item_code="Test Extra Item 2", qty=10, basic_rate=100
		)
		make_stock_entry(
			target="_Test Warehouse - _TC",
			item_code="Sub Contracted Raw Material 1",
			qty=10,
			basic_rate=100,
		)

		rm_items = [
			{
				"item_code": item_code,
				"rm_item_code": "Sub Contracted Raw Material 1",
				"item_name": "_Test Item",
				"qty": 10,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": "Nos",
			},
			{
				"item_code": item_code,
				"rm_item_code": "_Test Item Home Desktop 100",
				"item_name": "_Test Item Home Desktop 100",
				"qty": 20,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": "Nos",
			},
			{
				"item_code": item_code,
				"rm_item_code": "Test Extra Item 1",
				"item_name": "Test Extra Item 1",
				"qty": 10,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": "Nos",
			},
			{
				"item_code": item_code,
				"rm_item_code": "Test Extra Item 2",
				"stock_uom": "Nos",
				"qty": 10,
				"warehouse": "_Test Warehouse - _TC",
				"item_name": "Test Extra Item 2",
			},
		]

		ste = frappe.get_doc(make_rm_stock_entry(sco.name, rm_items))
		ste.submit()

		scr = make_subcontracting_receipt(sco.name)
		received_qty = 2

		# partial receipt
		scr.get("items")[0].qty = received_qty
		scr.save()
		scr.submit()

		transferred_items = sorted(
			[item.item_code for item in ste.get("items") if ste.subcontracting_order == sco.name]
		)
		issued_items = sorted([item.rm_item_code for item in scr.get("supplied_items")])

		self.assertEqual(transferred_items, issued_items)
		self.assertEqual(scr.get_supplied_items_cost(scr.get("items")[0].name), 2000)

		transferred_rm_map = frappe._dict()
		for item in rm_items:
			transferred_rm_map[item.get("rm_item_code")] = item

		set_backflush_based_on("BOM")

	def test_supplied_qty(self):
		item_code = "_Test Subcontracted FG Item 5"
		make_item("Sub Contracted Raw Material 4", {"is_stock_item": 1, "is_sub_contracted_item": 1})

		make_subcontracted_item(item_code=item_code, raw_materials=["Sub Contracted Raw Material 4"])

		set_backflush_based_on("Material Transferred for Subcontract")

		order_qty = 250
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": order_qty,
				"rate": 100,
				"fg_item": item_code,
				"fg_item_qty": order_qty,
			},
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": order_qty,
				"rate": 100,
				"fg_item": item_code,
				"fg_item_qty": order_qty,
			},
		]

		sco = get_subcontracting_order(service_items=service_items)

		# Material receipt entry for the raw materials which will be send to supplier
		make_stock_entry(
			target="_Test Warehouse - _TC",
			item_code="Sub Contracted Raw Material 4",
			qty=500,
			basic_rate=100,
		)

		rm_items = [
			{
				"item_code": item_code,
				"rm_item_code": "Sub Contracted Raw Material 4",
				"item_name": "_Test Item",
				"qty": 250,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": "Nos",
				"name": sco.supplied_items[0].name,
			},
			{
				"item_code": item_code,
				"rm_item_code": "Sub Contracted Raw Material 4",
				"item_name": "_Test Item",
				"qty": 250,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": "Nos",
			},
		]

		# Raw Materials transfer entry from stores to supplier's warehouse
		ste = frappe.get_doc(make_rm_stock_entry(sco.name, rm_items))
		ste.submit()

		# Test sco_rm_detail field has value or not
		for item_row in ste.items:
			self.assertEqual(item_row.sco_rm_detail, sco.supplied_items[item_row.idx - 1].name)

		sco.load_from_db()
		for row in sco.supplied_items:
			# Valid that whether transferred quantity is matching with supplied qty or not in the subcontracting order
			self.assertEqual(row.supplied_qty, 250.0)

		set_backflush_based_on("BOM")

	def test_get_materials_from_supplier(self):
		# Create SCO
		sco = get_subcontracting_order()

		# Transfer RM
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		# Create SCR (Partial)
		scr = make_subcontracting_receipt(sco.name)
		scr.items[0].qty -= 5
		scr.save()
		scr.submit()

		# Get RM from Supplier
		ste = get_materials_from_supplier(sco.name, [d.name for d in sco.supplied_items])
		ste.save()
		ste.submit()

		sco.load_from_db()

		self.assertEqual(sco.supplied_items[0].returned_qty, 5)

	def test_ordered_qty_for_subcontracting_order(self):
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 8",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA8",
				"fg_item_qty": 10,
			},
		]

		ordered_qty = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "Subcontracted Item SA8"},
			fieldname="ordered_qty",
		)
		ordered_qty = flt(ordered_qty)

		sco = get_subcontracting_order(service_items=service_items)
		sco.reload()

		new_ordered_qty = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "Subcontracted Item SA8"},
			fieldname="ordered_qty",
		)
		new_ordered_qty = flt(new_ordered_qty)

		self.assertEqual(ordered_qty + 10, new_ordered_qty)

		for row in sco.supplied_items:
			make_stock_entry(
				target="_Test Warehouse 1 - _TC",
				item_code=row.rm_item_code,
				qty=row.required_qty,
				basic_rate=100,
			)

		scr = make_subcontracting_receipt(sco.name)
		scr.submit()

		new_ordered_qty = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "Subcontracted Item SA8"},
			fieldname="ordered_qty",
		)

		self.assertEqual(ordered_qty, new_ordered_qty)

		scr.reload()
		scr.cancel()

		new_ordered_qty = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "Subcontracted Item SA8"},
			fieldname="ordered_qty",
		)

		self.assertEqual(ordered_qty + 10, new_ordered_qty)

	def test_requested_qty_for_subcontracting_order(self):
		from erpnext.stock.doctype.material_request.material_request import make_purchase_order
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		requested_qty = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "Subcontracted Item SA8"},
			fieldname="indented_qty",
		)
		requested_qty = flt(requested_qty)

		mr = make_material_request(
			item_code="Subcontracted Item SA8",
			material_request_type="Purchase",
			qty=10,
		)

		self.assertTrue(mr.docstatus == 1)

		new_requested_qty = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "Subcontracted Item SA8"},
			fieldname="indented_qty",
		)
		new_requested_qty = flt(new_requested_qty)

		self.assertEqual(requested_qty + 10, new_requested_qty)

		po = make_purchase_order(mr.name)
		po.is_subcontracted = 1
		po.supplier = "_Test Supplier"
		po.items[0].fg_item = "Subcontracted Item SA8"
		po.items[0].fg_item_qty = 10
		po.items[0].item_code = "Subcontracted Service Item 8"
		po.items[0].item_name = "Subcontracted Service Item 8"
		po.items[0].qty = 10
		po.supplier_warehouse = "_Test Warehouse 1 - _TC"
		po.save()
		po.submit()

		self.assertTrue(po.items[0].material_request)
		self.assertTrue(po.items[0].material_request_item)

		sco = create_subcontracting_order(po_name=po.name)
		self.assertTrue(sco.items[0].material_request)
		self.assertTrue(sco.items[0].material_request_item)

		new_requested_qty = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "Subcontracted Item SA8"},
			fieldname="indented_qty",
		)
		new_requested_qty = flt(new_requested_qty)

		self.assertEqual(requested_qty, new_requested_qty)


def create_subcontracting_order(**args):
	args = frappe._dict(args)
	sco = get_mapped_subcontracting_order(source_name=args.po_name)

	for item in sco.items:
		item.include_exploded_items = args.get("include_exploded_items", 1)

	if args.warehouse:
		for item in sco.items:
			item.warehouse = args.warehouse
	else:
		warehouse = frappe.get_value("Purchase Order", args.po_name, "set_warehouse")
		if warehouse:
			for item in sco.items:
				item.warehouse = warehouse
		else:
			po = frappe.get_doc("Purchase Order", args.po_name)
			warehouses = []
			for item in po.items:
				warehouses.append(item.warehouse)
			else:
				for idx, val in enumerate(sco.items):
					val.warehouse = warehouses[idx]

	warehouses = set()
	for item in sco.items:
		warehouses.add(item.warehouse)

	if len(warehouses) == 1:
		sco.set_warehouse = next(iter(warehouses))

	if not args.do_not_save:
		sco.insert()
		if not args.do_not_submit:
			sco.submit()

	return sco
