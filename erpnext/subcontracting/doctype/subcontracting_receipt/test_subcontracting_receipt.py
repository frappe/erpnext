# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import copy

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint, flt

import erpnext
from erpnext.accounts.doctype.account.test_account import get_inventory_account
from erpnext.controllers.sales_and_purchase_return import make_return_doc
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
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import get_gl_entries
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
	make_subcontracting_receipt,
)


class TestSubcontractingReceipt(FrappeTestCase):
	def setUp(self):
		make_subcontracted_items()
		make_raw_materials()
		make_service_items()
		make_bom_for_subcontracted_items()

	def test_subcontracting(self):
		set_backflush_based_on("BOM")
		make_stock_entry(
			item_code="_Test Item", qty=100, target="_Test Warehouse 1 - _TC", basic_rate=100
		)
		make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			qty=100,
			target="_Test Warehouse 1 - _TC",
			basic_rate=100,
		)
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
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		scr = make_subcontracting_receipt(sco.name)
		scr.save()
		scr.submit()
		rm_supp_cost = sum(item.amount for item in scr.get("supplied_items"))
		self.assertEqual(scr.get("items")[0].rm_supp_cost, flt(rm_supp_cost))

	def test_available_qty_for_consumption(self):
		make_stock_entry(
			item_code="_Test Item", qty=100, target="_Test Warehouse 1 - _TC", basic_rate=100
		)
		make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			qty=100,
			target="_Test Warehouse 1 - _TC",
			basic_rate=100,
		)
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
		rm_items = [
			{
				"main_item_code": "_Test FG Item",
				"item_code": "_Test Item",
				"qty": 5.0,
				"rate": 100.0,
				"stock_uom": "_Test UOM",
				"warehouse": "_Test Warehouse - _TC",
			},
			{
				"main_item_code": "_Test FG Item",
				"item_code": "_Test Item Home Desktop 100",
				"qty": 10.0,
				"rate": 100.0,
				"stock_uom": "_Test UOM",
				"warehouse": "_Test Warehouse - _TC",
			},
		]
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		scr = make_subcontracting_receipt(sco.name)
		scr.save()
		self.assertRaises(frappe.ValidationError, scr.submit)

	def test_subcontracting_gle_fg_item_rate_zero(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import get_gl_entries

		set_backflush_based_on("BOM")
		make_stock_entry(
			item_code="_Test Item",
			target="Work In Progress - TCP1",
			qty=100,
			basic_rate=100,
			company="_Test Company with perpetual inventory",
		)
		make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="Work In Progress - TCP1",
			qty=100,
			basic_rate=100,
			company="_Test Company with perpetual inventory",
		)
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 10,
				"rate": 0,
				"fg_item": "_Test FG Item",
				"fg_item_qty": 10,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		scr = make_subcontracting_receipt(sco.name)
		scr.save()
		scr.submit()

		gl_entries = get_gl_entries("Subcontracting Receipt", scr.name)
		self.assertFalse(gl_entries)

	def test_subcontracting_over_receipt(self):
		"""
		Behaviour: Raise multiple SCRs against one SCO that in total
		        receive more than the required qty in the SCO.
		Expected Result: Error Raised for Over Receipt against SCO.
		"""
		from erpnext.controllers.subcontracting_controller import (
			make_rm_stock_entry as make_subcontract_transfer_entry,
		)
		from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
			make_subcontracting_receipt,
		)
		from erpnext.subcontracting.doctype.subcontracting_order.test_subcontracting_order import (
			make_subcontracted_item,
		)

		set_backflush_based_on("Material Transferred for Subcontract")
		item_code = "_Test Subcontracted FG Item 1"
		make_subcontracted_item(item_code=item_code)
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 1,
				"rate": 100,
				"fg_item": "_Test Subcontracted FG Item 1",
				"fg_item_qty": 1,
			},
		]
		sco = get_subcontracting_order(
			service_items=service_items,
			include_exploded_items=0,
		)

		# stock raw materials in a warehouse before transfer
		make_stock_entry(
			target="_Test Warehouse - _TC", item_code="Test Extra Item 1", qty=10, basic_rate=100
		)
		make_stock_entry(
			target="_Test Warehouse - _TC", item_code="_Test FG Item", qty=1, basic_rate=100
		)
		make_stock_entry(
			target="_Test Warehouse - _TC", item_code="Test Extra Item 2", qty=1, basic_rate=100
		)

		rm_items = [
			{
				"item_code": item_code,
				"rm_item_code": sco.supplied_items[0].rm_item_code,
				"item_name": "_Test FG Item",
				"qty": sco.supplied_items[0].required_qty,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": "Nos",
			},
			{
				"item_code": item_code,
				"rm_item_code": sco.supplied_items[1].rm_item_code,
				"item_name": "Test Extra Item 1",
				"qty": sco.supplied_items[1].required_qty,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": "Nos",
			},
		]
		ste = frappe.get_doc(make_subcontract_transfer_entry(sco.name, rm_items))
		ste.to_warehouse = "_Test Warehouse 1 - _TC"
		ste.save()
		ste.submit()

		scr1 = make_subcontracting_receipt(sco.name)
		scr2 = make_subcontracting_receipt(sco.name)

		scr1.submit()
		self.assertRaises(frappe.ValidationError, scr2.submit)

	def test_subcontracted_scr_for_multi_transfer_batches(self):
		from erpnext.controllers.subcontracting_controller import make_rm_stock_entry
		from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
			make_subcontracting_receipt,
		)

		set_backflush_based_on("Material Transferred for Subcontract")
		item_code = "_Test Subcontracted FG Item 3"

		make_item(
			"Sub Contracted Raw Material 3",
			{"is_stock_item": 1, "is_sub_contracted_item": 1, "has_batch_no": 1, "create_new_batch": 1},
		)

		make_subcontracted_item(
			item_code=item_code, has_batch_no=1, raw_materials=["Sub Contracted Raw Material 3"]
		)

		order_qty = 500
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 3",
				"qty": order_qty,
				"rate": 100,
				"fg_item": "_Test Subcontracted FG Item 3",
				"fg_item_qty": order_qty,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)

		ste1 = make_stock_entry(
			target="_Test Warehouse - _TC",
			item_code="Sub Contracted Raw Material 3",
			qty=300,
			basic_rate=100,
		)
		ste2 = make_stock_entry(
			target="_Test Warehouse - _TC",
			item_code="Sub Contracted Raw Material 3",
			qty=200,
			basic_rate=100,
		)

		transferred_batch = {ste1.items[0].batch_no: 300, ste2.items[0].batch_no: 200}

		rm_items = [
			{
				"item_code": item_code,
				"rm_item_code": "Sub Contracted Raw Material 3",
				"item_name": "_Test Item",
				"qty": 300,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": "Nos",
				"name": sco.supplied_items[0].name,
			},
			{
				"item_code": item_code,
				"rm_item_code": "Sub Contracted Raw Material 3",
				"item_name": "_Test Item",
				"qty": 200,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": "Nos",
				"name": sco.supplied_items[0].name,
			},
		]

		se = frappe.get_doc(make_rm_stock_entry(sco.name, rm_items))
		self.assertEqual(len(se.items), 2)
		se.items[0].batch_no = ste1.items[0].batch_no
		se.items[1].batch_no = ste2.items[0].batch_no
		se.submit()

		supplied_qty = frappe.db.get_value(
			"Subcontracting Order Supplied Item",
			{"parent": sco.name, "rm_item_code": "Sub Contracted Raw Material 3"},
			"supplied_qty",
		)

		self.assertEqual(supplied_qty, 500.00)

		scr = make_subcontracting_receipt(sco.name)
		scr.save()
		self.assertEqual(len(scr.supplied_items), 2)

		for row in scr.supplied_items:
			self.assertEqual(transferred_batch.get(row.batch_no), row.consumed_qty)

	def test_subcontracting_receipt_partial_return(self):
		sco = get_subcontracting_order()
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		scr1 = make_subcontracting_receipt(sco.name)
		scr1.save()
		scr1.submit()

		scr1_return = make_return_subcontracting_receipt(scr_name=scr1.name, qty=-3)
		scr1.load_from_db()
		self.assertEqual(scr1_return.status, "Return")
		self.assertIsNotNone(scr1_return.items[0].bom)
		self.assertEqual(scr1.items[0].returned_qty, 3)

		scr2_return = make_return_subcontracting_receipt(scr_name=scr1.name, qty=-7)
		scr1.load_from_db()
		self.assertEqual(scr2_return.status, "Return")
		self.assertIsNotNone(scr2_return.items[0].bom)
		self.assertEqual(scr1.status, "Return Issued")
		self.assertEqual(scr1.items[0].returned_qty, 10)

	def test_subcontracting_receipt_over_return(self):
		sco = get_subcontracting_order()
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		scr1 = make_subcontracting_receipt(sco.name)
		scr1.save()
		scr1.submit()

		from erpnext.controllers.status_updater import OverAllowanceError

		args = frappe._dict(scr_name=scr1.name, qty=-15)
		self.assertRaises(OverAllowanceError, make_return_subcontracting_receipt, **args)

	def test_subcontracting_receipt_no_gl_entry(self):
		sco = get_subcontracting_order()
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr = make_subcontracting_receipt(sco.name)
		scr.append(
			"additional_costs",
			{
				"expense_account": "Expenses Included In Valuation - _TC",
				"description": "Test Additional Costs",
				"amount": 100,
			},
		)
		scr.save()
		scr.submit()

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": "Subcontracting Receipt",
				"voucher_no": scr.name,
				"item_code": "Subcontracted Item SA7",
				"warehouse": "_Test Warehouse - _TC",
			},
			"stock_value_difference",
		)

		# Service Cost(100 * 10) + Raw Materials Cost(100 * 10) + Additional Costs(10 * 10) = 2100
		self.assertEqual(stock_value_difference, 2100)
		self.assertFalse(get_gl_entries("Subcontracting Receipt", scr.name))

	def test_subcontracting_receipt_gl_entry(self):
		sco = get_subcontracting_order(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
		)
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr = make_subcontracting_receipt(sco.name)
		additional_costs_expense_account = "Expenses Included In Valuation - TCP1"
		scr.append(
			"additional_costs",
			{
				"expense_account": additional_costs_expense_account,
				"description": "Test Additional Costs",
				"amount": 100,
				"base_amount": 100,
			},
		)
		scr.save()
		scr.submit()

		self.assertEqual(cint(erpnext.is_perpetual_inventory_enabled(scr.company)), 1)

		gl_entries = get_gl_entries("Subcontracting Receipt", scr.name)

		self.assertTrue(gl_entries)

		fg_warehouse_ac = get_inventory_account(scr.company, scr.items[0].warehouse)
		supplier_warehouse_ac = get_inventory_account(scr.company, scr.supplier_warehouse)
		expense_account = scr.items[0].expense_account

		if fg_warehouse_ac == supplier_warehouse_ac:
			expected_values = {
				fg_warehouse_ac: [2100.0, 1000.0],  # FG Amount (D), RM Cost (C)
				expense_account: [0.0, 1000.0],  # Service Cost (C)
				additional_costs_expense_account: [0.0, 100.0],  # Additional Cost (C)
			}
		else:
			expected_values = {
				fg_warehouse_ac: [2100.0, 0.0],  # FG Amount (D)
				supplier_warehouse_ac: [0.0, 1000.0],  # RM Cost (C)
				expense_account: [0.0, 1000.0],  # Service Cost (C)
				additional_costs_expense_account: [0.0, 100.0],  # Additional Cost (C)
			}

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.debit)
			self.assertEqual(expected_values[gle.account][1], gle.credit)

		scr.reload()
		scr.cancel()
		self.assertTrue(get_gl_entries("Subcontracting Receipt", scr.name))

	def test_supplied_items_consumed_qty(self):
		# Set Backflush Based On as "Material Transferred for Subcontracting" to transfer RM's more than the required qty
		set_backflush_based_on("Material Transferred for Subcontract")

		# Create Material Receipt for RM's
		make_stock_entry(
			item_code="_Test Item", qty=100, target="_Test Warehouse 1 - _TC", basic_rate=100
		)
		make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			qty=100,
			target="_Test Warehouse 1 - _TC",
			basic_rate=100,
		)

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

		# Create Subcontracting Order
		sco = get_subcontracting_order(service_items=service_items)

		# Transfer RM's
		rm_items = get_rm_items(sco.supplied_items)
		rm_items[0]["qty"] = 20  # Extra 10 Qty
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		# Create Subcontracting Receipt
		scr = make_subcontracting_receipt(sco.name)
		scr.rejected_warehouse = "_Test Warehouse 1 - _TC"

		scr.items[0].qty = 5  # Accepted Qty
		scr.items[0].rejected_qty = 3
		scr.save()

		# consumed_qty should be (accepted_qty * (transfered_qty / qty)) = (5 * (20 / 10)) = 10
		self.assertEqual(scr.supplied_items[0].consumed_qty, 10)

		# Set Backflush Based On as "BOM"
		set_backflush_based_on("BOM")

		scr.items[0].qty = 6  # Accepted Qty
		scr.items[0].rejected_qty = 4
		scr.save()

		# consumed_qty should be (accepted_qty * qty_consumed_per_unit) = (6 * 1) = 6
		self.assertEqual(scr.supplied_items[0].consumed_qty, 6)


def make_return_subcontracting_receipt(**args):
	args = frappe._dict(args)
	return_doc = make_return_doc("Subcontracting Receipt", args.scr_name)
	return_doc.supplier_warehouse = (
		args.supplier_warehouse or args.warehouse or "_Test Warehouse 1 - _TC"
	)

	if args.qty:
		for item in return_doc.items:
			item.qty = args.qty

	if not args.do_not_save:
		return_doc.save()
		if not args.do_not_submit:
			return_doc.submit()

	return_doc.load_from_db()
	return return_doc


def get_items(**args):
	args = frappe._dict(args)
	return [
		{
			"conversion_factor": 1.0,
			"description": "_Test Item",
			"doctype": "Subcontracting Receipt Item",
			"item_code": "_Test Item",
			"item_name": "_Test Item",
			"parentfield": "items",
			"qty": 5.0,
			"rate": 50.0,
			"received_qty": 5.0,
			"rejected_qty": 0.0,
			"stock_uom": "_Test UOM",
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"cost_center": args.cost_center or "Main - _TC",
		},
		{
			"conversion_factor": 1.0,
			"description": "_Test Item Home Desktop 100",
			"doctype": "Subcontracting Receipt Item",
			"item_code": "_Test Item Home Desktop 100",
			"item_name": "_Test Item Home Desktop 100",
			"parentfield": "items",
			"qty": 5.0,
			"rate": 50.0,
			"received_qty": 5.0,
			"rejected_qty": 0.0,
			"stock_uom": "_Test UOM",
			"warehouse": args.warehouse or "_Test Warehouse 1 - _TC",
			"cost_center": args.cost_center or "Main - _TC",
		},
	]
