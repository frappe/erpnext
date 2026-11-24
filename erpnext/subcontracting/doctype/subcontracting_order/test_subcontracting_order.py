# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import copy
from collections import defaultdict
from unittest.mock import PropertyMock, patch

import frappe
from frappe.utils import flt

from erpnext.buying.doctype.purchase_order.mapper import get_mapped_subcontracting_order
from erpnext.controllers.item_variant import create_variant
from erpnext.controllers.subcontracting_controller import (
	get_materials_from_supplier,
	make_rm_stock_entry,
)
from erpnext.controllers.tests.test_subcontracting_controller import (
	get_rm_items,
	get_subcontracting_order,
	make_stock_in_entry,
	make_stock_transfer_entry,
	make_subcontracted_item,
	set_backflush_based_on,
)
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.patches.v16_0.recalculate_subcontracting_order_service_cost import (
	execute as recalculate_subcontracting_order_service_cost,
)
from erpnext.patches.v16_0.set_reserved_components_return_cutoff import (
	execute as set_reserved_components_return_cutoff,
)
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_numbers_from_bundle,
	make_serial_batch_bundle,
)
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.stock.utils import InvalidWarehouseCompany, get_bin
from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
	get_mapped_subcontracting_receipt,
	make_subcontracting_receipt,
	update_subcontracting_order_status,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSubcontractingOrder(ERPNextTestSuite):
	def test_finished_good_qty_uses_item_stock_uom(self):
		from erpnext.utilities.transaction_base import UOMMustBeIntegerError

		sco = get_subcontracting_order(do_not_save=1)
		sco.items[0].qty = 2.5
		sco.items[0].stock_uom = "Kg"

		self.assertRaises(UOMMustBeIntegerError, sco.save)

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

	def test_status_can_only_be_closed_or_reopened_when_submitted(self):
		sco = get_subcontracting_order(do_not_submit=1)
		self.assertRaises(frappe.ValidationError, update_subcontracting_order_status, sco.name, "Closed")

		sco.submit()
		self.assertRaises(frappe.ValidationError, update_subcontracting_order_status, sco.name, "Completed")

		update_subcontracting_order_status(sco.name, "Closed")
		self.assertEqual(frappe.db.get_value("Subcontracting Order", sco.name, "status"), "Closed")

	def test_closing_purchase_order_closes_all_its_subcontracting_orders(self):
		sco = get_subcontracting_order(do_not_save=1)
		sco.items[0].qty = 4
		sco.insert()
		sco.submit()
		create_subcontracting_order(po_name=sco.purchase_order)

		frappe.get_doc("Purchase Order", sco.purchase_order).update_status("Closed")

		self.assertEqual(
			frappe.get_all("Subcontracting Order", {"purchase_order": sco.purchase_order}, pluck="status"),
			["Closed", "Closed"],
		)

	def test_reopening_purchase_order_keeps_a_closed_subcontracting_order_closed(self):
		sco = get_subcontracting_order()
		update_subcontracting_order_status(sco.name, "Closed")

		po = frappe.get_doc("Purchase Order", sco.purchase_order)
		po.update_status("Closed")
		po.reload()
		po.update_status("Submitted")

		self.assertEqual(frappe.db.get_value("Subcontracting Order", sco.name, "status"), "Closed")

	def test_purchase_order_row_on_an_open_subcontracting_order_cannot_be_closed(self):
		from erpnext.controllers.item_close import update_closed_status

		sco = get_subcontracting_order()

		self.assertRaisesRegex(
			frappe.ValidationError,
			"Close it before closing the row",
			update_closed_status,
			"Purchase Order",
			sco.purchase_order,
			[sco.items[0].purchase_order_item],
			1,
		)

		update_subcontracting_order_status(sco.name, "Closed")
		update_closed_status("Purchase Order", sco.purchase_order, [sco.items[0].purchase_order_item], 1)

	def test_closed_purchase_order_row_cannot_go_back_on_an_open_subcontracting_order(self):
		from erpnext.controllers.item_close import update_closed_status

		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": item_code,
				"qty": 5,
				"rate": 10,
				"fg_item": fg_item,
				"fg_item_qty": 5,
			}
			for item_code, fg_item in [
				("Subcontracted Service Item 7", "Subcontracted Item SA7"),
				("Subcontracted Service Item 1", "Subcontracted Item SA1"),
			]
		]
		sco = get_subcontracting_order(service_items=service_items, do_not_submit=1)
		po_item = sco.items[0].purchase_order_item

		update_closed_status("Purchase Order", sco.purchase_order, [po_item], 1)
		self.assertRaisesRegex(frappe.ValidationError, "is closed in Purchase Order", sco.submit)

		update_closed_status("Purchase Order", sco.purchase_order, [po_item], 0)
		sco.reload()
		sco.submit()
		update_subcontracting_order_status(sco.name, "Closed")
		update_closed_status("Purchase Order", sco.purchase_order, [po_item], 1)
		self.assertRaisesRegex(
			frappe.ValidationError,
			"is closed in Purchase Order",
			update_subcontracting_order_status,
			sco.name,
		)

	def test_holding_purchase_order_keeps_a_closed_subcontracting_order_closed(self):
		sco = get_subcontracting_order(do_not_save=1)
		sco.items[0].qty = 4
		sco.insert()
		sco.submit()
		create_subcontracting_order(po_name=sco.purchase_order)
		update_subcontracting_order_status(sco.name, "Closed")

		frappe.get_doc("Purchase Order", sco.purchase_order).update_status("On Hold")

		self.assertEqual(frappe.db.get_value("Purchase Order", sco.purchase_order, "status"), "On Hold")
		self.assertEqual(frappe.db.get_value("Subcontracting Order", sco.name, "status"), "Closed")

	def test_quantity_is_checked_against_the_purchase_order(self):
		sco = get_subcontracting_order(do_not_save=1)
		sco.items[0].update({"subcontracting_conversion_factor": 0.1, "qty": 100})
		self.assertRaises(frappe.ValidationError, sco.insert)

		sco = create_subcontracting_order(po_name=sco.purchase_order, do_not_save=1)
		sco.append("items", sco.items[0].as_dict(no_default_fields=True))
		self.assertRaises(frappe.ValidationError, sco.insert)

	def test_order_must_match_its_purchase_order(self):
		sa1_bom = frappe.db.get_value("BOM", {"item": "Subcontracted Item SA1", "is_default": 1})
		changes = (
			lambda sco: sco.update({"supplier": "_Test Supplier 1"}),
			lambda sco: sco.items[0].update({"item_code": "Subcontracted Item SA1", "bom": sa1_bom}),
			lambda sco: sco.service_items[0].update({"rate": 1000}),
		)
		for change in changes:
			sco = get_subcontracting_order(do_not_save=1)
			change(sco)
			self.assertRaises(frappe.ValidationError, sco.insert)

	def test_finished_good_needs_its_service_item_row(self):
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 7",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA7",
				"fg_item_qty": 10,
			},
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 10,
				"rate": 200,
				"fg_item": "Subcontracted Item SA1",
				"fg_item_qty": 10,
			},
		]
		sco = get_subcontracting_order(service_items=service_items, do_not_save=1)
		sco.service_items.pop(0)

		self.assertRaises(frappe.ValidationError, sco.insert)

	def test_purchase_order_is_fully_subcontracted_with_a_non_integer_ratio(self):
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 7",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA7",
				"fg_item_qty": 3,
			},
		]
		po_name = get_subcontracting_order(service_items=service_items, do_not_save=1).purchase_order
		for _ in range(3):
			sco = create_subcontracting_order(po_name=po_name, do_not_save=1)
			sco.items[0].qty = 1
			sco.insert()
			sco.submit()

		self.assertEqual(
			frappe.db.get_value("Purchase Order Item", {"parent": po_name}, "subcontracted_qty"), 10
		)

	def test_purchase_order_stays_open_while_finished_goods_remain(self):
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 7",
				"qty": 1,
				"rate": 100,
				"fg_item": "Subcontracted Item SA7",
				"fg_item_qty": 3000,
			},
		]
		po_name = get_subcontracting_order(service_items=service_items, do_not_save=1).purchase_order
		sco = create_subcontracting_order(po_name=po_name, do_not_save=1)
		sco.items[0].qty = 2999
		sco.insert()
		sco.submit()

		next_sco = create_subcontracting_order(po_name=po_name, do_not_save=1)
		self.assertEqual(next_sco.items[0].qty, 1)

	def test_project_is_carried_over_from_purchase_order(self):
		project = make_project({"project_name": "_Test SCO Project"}).name
		po = make_subcontracted_purchase_order(project)

		sco = get_mapped_subcontracting_order(source_name=po.name)

		self.assertEqual(sco.project, project)
		self.assertEqual(sco.items[0].project, project)

	def test_project_cannot_differ_from_purchase_order(self):
		project = make_project({"project_name": "_Test SCO Project"}).name
		other_project = make_project({"project_name": "_Test SCO Project 2"}).name
		po = make_subcontracted_purchase_order(project)

		sco = get_mapped_subcontracting_order(source_name=po.name)
		sco.items[0].project = other_project
		self.assertRaises(frappe.ValidationError, sco.save)

	def test_sco_requires_a_subcontracting_purchase_order(self):
		sco = get_subcontracting_order(do_not_save=1)
		sco.purchase_order = None
		self.assertRaises(frappe.ValidationError, sco.validate_purchase_order_for_subcontracting)

	def test_service_item_must_be_non_stock(self):
		sco = get_subcontracting_order(do_not_submit=1)
		sco.service_items[0].item_code = "_Test Item"  # a stock item
		self.assertRaises(frappe.ValidationError, sco.validate_service_items)

	def test_reserve_warehouse_must_differ_from_supplier_warehouse(self):
		sco = get_subcontracting_order(do_not_submit=1)
		sco.supplied_items[0].reserve_warehouse = sco.supplier_warehouse
		self.assertRaises(frappe.ValidationError, sco.validate_supplied_items)

	def test_warehouses_must_belong_to_the_order_company(self):
		other_company_warehouse = "_Test Warehouse 2 - _TC1"
		for fieldname in ("warehouse", "set_reserve_warehouse", "supplier_warehouse"):
			sco = get_subcontracting_order(do_not_save=1)
			if fieldname == "warehouse":
				sco.set_warehouse = None
				sco.items[0].warehouse = other_company_warehouse
			else:
				sco.set(fieldname, other_company_warehouse)
			self.assertRaises(InvalidWarehouseCompany, sco.insert)

		sco = get_subcontracting_order(do_not_save=1)
		sco.set_reserve_warehouse = "_Test Warehouse - _TC"
		sco.insert()
		self.assertEqual(sco.supplied_items[0].reserve_warehouse, "_Test Warehouse - _TC")

	def test_reserve_warehouse_from_job_card_must_belong_to_the_order_company(self):
		def make_order_from_job_card(company, source_warehouse):
			sco = get_subcontracting_order(do_not_save=1)
			raw_materials = frappe.get_all("BOM Item", {"parent": sco.items[0].bom}, pluck="item_code")
			job_card = frappe.get_doc(
				{
					"doctype": "Job Card",
					"company": company,
					"items": [
						{"item_code": item, "source_warehouse": source_warehouse} for item in raw_materials
					],
				}
			)
			job_card.flags.ignore_validate = job_card.flags.ignore_mandatory = True
			job_card.flags.ignore_links = True
			job_card.insert()
			sco.set_reserve_warehouse = None
			sco.items[0].job_card = job_card.name
			return sco

		sco = make_order_from_job_card("_Test Company 1", "_Test Warehouse 2 - _TC1")
		self.assertRaises(InvalidWarehouseCompany, sco.insert)

		sco = make_order_from_job_card("_Test Company", "Stores - _TC")
		sco.insert()
		self.assertEqual({row.reserve_warehouse for row in sco.supplied_items}, {"Stores - _TC"})

	def test_receipt_supplier_warehouse_must_belong_to_the_receipt_company(self):
		set_backflush_based_on("BOM")
		sco = get_subcontracting_order()
		scr = make_subcontracting_receipt(sco.name)
		scr.supplier_warehouse = "_Test Warehouse 1 - _TC"
		scr.reset_raw_materials()
		raw_material = scr.supplied_items[0].rm_item_code
		make_stock_entry(item_code=raw_material, qty=7, target="_Test Warehouse 1 - _TC", basic_rate=100)
		scr.get_current_stock()
		expected = frappe.db.get_value(
			"Bin", {"item_code": raw_material, "warehouse": "_Test Warehouse 1 - _TC"}, "actual_qty"
		)
		self.assertEqual(scr.supplied_items[0].current_stock, expected)

		scr.supplier_warehouse = "_Test Warehouse 2 - _TC1"
		self.assertRaises(InvalidWarehouseCompany, scr.get_current_stock)
		self.assertRaises(InvalidWarehouseCompany, scr.reset_raw_materials)

	def test_subcontracting_receipt_applies_bom_process_loss(self):
		sco = get_subcontracting_order()
		frappe.db.set_value("BOM", sco.items[0].bom, "process_loss_percentage", 10)

		scr = make_subcontracting_receipt(sco.name)

		# 10% of the ordered 10 qty is lost in processing
		self.assertEqual(scr.items[0].received_qty, 10)
		self.assertEqual(scr.items[0].process_loss_qty, 1)
		self.assertEqual(scr.items[0].qty, 9)

	def test_partial_receipts_map_bom_process_loss_in_whole_units(self):
		sco = get_subcontracting_order()
		frappe.db.set_value("BOM", sco.items[0].bom, "process_loss_percentage", 10)
		frappe.db.set_value("UOM", sco.items[0].stock_uom, "must_be_whole_number", 1)

		losses = []
		for _ in range(2):
			scr = get_mapped_subcontracting_receipt(sco.name, items=[{"name": sco.items[0].name, "qty": 5}])
			row = scr.items[0]
			self.assertEqual(row.qty + row.process_loss_qty, 5)
			self.assertEqual(row.process_loss_qty, int(row.process_loss_qty))
			losses.append(row.process_loss_qty)
			# as if this receipt was submitted
			sco.items[0].db_set("received_qty", flt(sco.items[0].received_qty) + 5)

		# together the receipts lose the BOM's 10% of 10
		self.assertEqual(sum(losses), 1)

	def test_service_cost_is_matched_by_purchase_order_item(self):
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 7",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA7",
				"fg_item_qty": 10,
			},
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 10,
				"rate": 200,
				"fg_item": "Subcontracted Item SA1",
				"fg_item_qty": 10,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)
		expected = {item.purchase_order_item: item.service_cost_per_qty for item in sco.items}

		# The two finished goods have distinct service costs, so a position-based pairing would swap them
		self.assertEqual(len(set(expected.values())), 2)

		# Service costs must follow purchase_order_item, not list position
		sco.service_items.reverse()
		sco.calculate_service_costs()

		for item in sco.items:
			self.assertEqual(item.service_cost_per_qty, expected[item.purchase_order_item])

	def test_variant_without_bom_uses_template_bom(self):
		variant, template_bom = make_subcontracted_variant()
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 7",
				"qty": 10,
				"rate": 100,
				"fg_item": variant.name,
				"fg_item_qty": 10,
			},
		]

		sco = get_subcontracting_order(service_items=service_items, do_not_submit=1)

		self.assertEqual(sco.items[0].bom, template_bom.name)
		self.assertEqual([d.rm_item_code for d in sco.supplied_items], ["Subcontracted Template RM Item"])

	def test_draft_bom_is_refused(self):
		sco = get_subcontracting_order(do_not_save=1)
		draft_bom = make_bom(
			item=sco.items[0].item_code, raw_materials=["Subcontracted SRM Item 1"], do_not_submit=True
		)
		sco.items[0].bom = draft_bom.name

		self.assertRaises(frappe.ValidationError, sco.insert)

	def test_purchase_order_row_bom_is_carried_over(self):
		bom = make_bom(
			item="Subcontracted Item SA7",
			raw_materials=["Subcontracted SRM Item 1"],
			rm_qty=2,
			do_not_save=True,
		)
		bom.is_default = 0
		bom.insert()
		bom.submit()
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 7",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA7",
				"fg_item_qty": 10,
				"bom": bom.name,
			},
		]

		sco = get_subcontracting_order(service_items=service_items, do_not_submit=1)

		self.assertEqual(sco.items[0].bom, bom.name)
		self.assertEqual(sco.supplied_items[0].required_qty, 20)

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

	def test_reserved_qty_for_subcontracting_ignores_other_orders_transfers(self):
		get_subcontracting_order()
		sco = get_subcontracting_order(do_not_save=1)
		sco.set_reserve_warehouse = "_Test Warehouse 2 - _TC"
		sco.insert()
		sco.submit()

		stock_bin = get_bin("Subcontracted SRM Item 1", "_Test Warehouse - _TC")
		stock_bin.update_reserved_qty_for_sub_contracting()
		reserved_qty_before_transfer = stock_bin.reserved_qty_for_sub_contract

		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name, rm_items=rm_items, itemwise_details=copy.deepcopy(itemwise_details)
		)
		stock_bin.update_reserved_qty_for_sub_contracting()

		self.assertEqual(stock_bin.reserved_qty_for_sub_contract, reserved_qty_before_transfer)

	def test_transfer_locks_bin_of_reserve_warehouse(self):
		sco = get_subcontracting_order(do_not_save=1)
		sco.set_reserve_warehouse = "_Test Warehouse 2 - _TC"
		sco.insert()
		sco.submit()

		row = sco.supplied_items[0]
		transfer = make_supplied_item_transfer(sco, row)
		transfer.items[0].s_warehouse = "_Test Warehouse - _TC"

		item_warehouses = transfer.get_item_warehouses()
		self.assertIn((row.rm_item_code, "_Test Warehouse - _TC"), item_warehouses)
		self.assertIn((row.rm_item_code, "_Test Warehouse 2 - _TC"), item_warehouses)

	def test_alternative_item_transfer_without_supplied_row_releases_reserved_qty(self):
		sco = get_subcontracting_order()
		row = sco.supplied_items[0]
		alternative = make_item("_Test SCO Alternative RM", {"is_stock_item": 1, "valuation_rate": 10}).name
		set_alternative_item(row.rm_item_code, alternative)
		make_stock_entry(
			item_code=alternative, target=row.reserve_warehouse, qty=row.required_qty, basic_rate=10
		)

		transfer = make_supplied_item_transfer(sco, row, link=False)
		transfer.items[0].update(
			{"item_code": alternative, "original_item": row.rm_item_code, "allow_alternative_item": 1}
		)
		transfer.insert()
		transfer.submit()

		self.assertEqual(frappe.db.get_value(row.doctype, row.name, "total_supplied_qty"), row.required_qty)
		self.assertEqual(get_bin(row.rm_item_code, row.reserve_warehouse).reserved_qty_for_sub_contract, 0)

	def test_alternative_item_transfer_counts_against_its_original_requirement(self):
		service_item = {
			"warehouse": "_Test Warehouse - _TC",
			"item_code": "Subcontracted Service Item 1",
			"qty": 10,
			"rate": 100,
			"fg_item": "Subcontracted Item SA1",
			"fg_item_qty": 10,
		}
		sco = get_subcontracting_order(service_items=[service_item])
		original, alternative = sco.supplied_items[0], sco.supplied_items[1]
		set_alternative_item(original.rm_item_code, alternative.rm_item_code)
		make_stock_entry(
			item_code=alternative.rm_item_code,
			target=alternative.reserve_warehouse,
			qty=original.required_qty + alternative.required_qty,
			basic_rate=10,
		)

		replacement = make_supplied_item_transfer(sco, original)
		replacement.items[0].update(
			{
				"item_code": alternative.rm_item_code,
				"original_item": original.rm_item_code,
				"allow_alternative_item": 1,
			}
		)
		replacement.insert()
		replacement.submit()

		own_transfer = make_supplied_item_transfer(sco, alternative)
		own_transfer.insert()
		own_transfer.submit()

		self.assertEqual(own_transfer.docstatus, 1)

	def test_consumed_alternative_item_counts_on_its_original_row(self):
		sco = make_reserving_order_with_new_items("Alt Consumed")
		frappe.db.set_value("BOM", sco.items[0].bom, "allow_alternative_item", 1)
		sco.reserve_stock = 0
		sco.submit()
		original = sco.supplied_items[0]
		alternative = make_item("Subcontracted RM Item Alt Consumed Alternative", {"is_stock_item": 1}).name
		set_alternative_item(original.rm_item_code, alternative)
		make_stock_entry(
			item_code=alternative,
			target=original.reserve_warehouse,
			qty=original.required_qty,
			basic_rate=120,
		)

		transfer = make_supplied_item_transfer(sco, original)
		transfer.items[0].update(
			{"item_code": alternative, "original_item": original.rm_item_code, "allow_alternative_item": 1}
		)
		transfer.insert()
		transfer.submit()
		make_subcontracting_receipt(sco.name).submit()

		self.assertEqual(
			frappe.db.get_value(original.doctype, original.name, "consumed_qty"), original.required_qty
		)

	def test_alternative_item_counts_on_the_order_row_it_was_sent_on_net_of_returns(self):
		set_backflush_based_on("Material Transferred for Subcontract")
		suffix = "Row Alt"
		service_item = make_item(f"Subcontracted Service Item {suffix}", {"is_stock_item": 0}).name
		fg_item = make_item(
			f"Subcontracted FG Item {suffix}", {"is_stock_item": 1, "is_sub_contracted_item": 1}
		).name
		first, second, shared, other = (
			make_item(f"Subcontracted RM Item {suffix} {code}", {"is_stock_item": 1}).name for code in "ABXY"
		)
		make_bom(item=fg_item, raw_materials=[first, second], rate=100, currency="INR")
		set_alternative_item(first, shared)
		set_alternative_item(first, other)
		set_alternative_item(second, shared)
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": service_item,
				"qty": 5,
				"rate": 100,
				"fg_item": fg_item,
				"fg_item_qty": 5,
			}
		]
		sco = get_subcontracting_order(service_items=service_items)
		first_row, second_row = sco.supplied_items
		for item_code, qty in ((shared, 10), (other, 5)):
			make_stock_entry(item_code=item_code, target=first_row.reserve_warehouse, qty=qty, basic_rate=100)

		def send(row, alternative):
			transfer = make_supplied_item_transfer(sco, row)
			transfer.items[0].update(
				{"item_code": alternative, "original_item": row.rm_item_code, "allow_alternative_item": 1}
			)
			transfer.insert()
			transfer.submit()

		send(first_row, shared)
		frappe.flags.args = {"rm_details": [first_row.name]}
		returned = get_materials_from_supplier(sco.name)
		frappe.flags.args = None
		returned.submit()
		send(first_row, other)
		send(second_row, shared)
		make_subcontracting_receipt(sco.name).submit()

		self.assertEqual(
			[frappe.db.get_value(row.doctype, row.name, "consumed_qty") for row in sco.supplied_items], [5, 5]
		)

	@ERPNextTestSuite.change_settings("Buying Settings", {"allow_multiple_items": True})
	def test_return_booked_on_one_row_keeps_consumed_qty_positive(self):
		suffix = "Split Return"
		service_item = make_item(f"Subcontracted Service Item {suffix}", {"is_stock_item": 0}).name
		fg_item = make_item(
			f"Subcontracted FG Item {suffix}", {"is_stock_item": 1, "is_sub_contracted_item": 1}
		).name
		rm_item = make_item(f"Subcontracted RM Item {suffix}", {"is_stock_item": 1}).name
		make_bom(item=fg_item, raw_materials=[rm_item], rate=100, currency="INR")
		service_item_row = {
			"warehouse": "_Test Warehouse - _TC",
			"item_code": service_item,
			"qty": 5,
			"rate": 100,
			"fg_item": fg_item,
			"fg_item_qty": 5,
		}
		sco = get_subcontracting_order(service_items=[service_item_row, dict(service_item_row)])
		make_stock_entry(
			item_code=rm_item, target=sco.supplied_items[0].reserve_warehouse, qty=10, basic_rate=100
		)
		for row in sco.supplied_items:
			make_supplied_item_transfer(sco, row).submit()

		def receive_one():
			receipt = make_subcontracting_receipt(sco.name)
			receipt.items[0].qty = 1
			receipt.remove(receipt.items[1])
			receipt.submit()

		receive_one()
		# return 8 of the 9 left, all booked on the first row
		frappe.flags.args = {"rm_details": [sco.supplied_items[0].name]}
		returned = get_materials_from_supplier(sco.name)
		frappe.flags.args = None
		returned.items[0].qty = 8
		returned.submit()
		receive_one()

		self.assertEqual(
			[frappe.db.get_value(row.doctype, row.name, "consumed_qty") for row in sco.supplied_items], [0, 2]
		)

	def test_consumption_for_a_finished_good_counts_on_the_row_its_material_was_sent_on(self):
		set_backflush_based_on("BOM")
		rm_item = make_item("Subcontracted RM Item Sent For Other FG", {"is_stock_item": 1}).name
		service_items = []
		for code, service_item, qty in (
			("A", "Subcontracted Service Item 2", 10),
			("B", "Subcontracted Service Item 3", 6),
		):
			fg_item = make_item(
				f"Subcontracted FG Item Sent For Other FG {code}",
				{"is_stock_item": 1, "is_sub_contracted_item": 1},
			).name
			make_bom(item=fg_item, raw_materials=[rm_item], rate=100, currency="INR")
			service_items.append(
				{
					"warehouse": "_Test Warehouse - _TC",
					"item_code": service_item,
					"qty": qty,
					"rate": 100,
					"fg_item": fg_item,
					"fg_item_qty": qty,
				}
			)

		# 16 sent on FG A's and FG B's rows, then a receipt of 6 FG B
		for sent, consumed in (((16, 0), [6, 0]), ((14, 2), [4, 2])):
			sco = get_subcontracting_order(service_items=service_items)
			make_stock_entry(
				item_code=rm_item, target=sco.supplied_items[0].reserve_warehouse, qty=16, basic_rate=100
			)
			for row, qty in zip(sco.supplied_items, sent, strict=True):
				if qty:
					transfer = make_supplied_item_transfer(sco, row)
					transfer.items[0].qty = qty
					transfer.submit()

			receipt = make_subcontracting_receipt(sco.name)
			receipt.remove(receipt.items[0])
			receipt.submit()

			self.assertEqual(
				[frappe.db.get_value(row.doctype, row.name, "consumed_qty") for row in sco.supplied_items],
				consumed,
			)

	def test_close_subcontracting_order_releases_reserved_qty(self):
		# RM in stock at the reserve warehouse for transfer
		make_stock_entry(target="_Test Warehouse - _TC", item_code="_Test Item", qty=10, basic_rate=100)
		make_stock_entry(
			target="_Test Warehouse - _TC", item_code="_Test Item Home Desktop 100", qty=20, basic_rate=100
		)

		bin_before_sco = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract",
			as_dict=1,
		)

		# Create SCO with a reserve warehouse on the supplied items
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

		# Transfer only 90% of the raw materials to the supplier warehouse
		ste = frappe.get_doc(make_rm_stock_entry(sco.name))
		for item in ste.items:
			item.qty *= 0.9
		ste.save()
		ste.submit()
		sco.load_from_db()
		self.assertEqual(sco.status, "Partial Material Transferred")

		# Receive only a partial qty so the order stays open (per_received < 100)
		scr = make_subcontracting_receipt(sco.name)
		scr.items[0].qty -= 1
		scr.save()
		scr.submit()
		sco.load_from_db()
		self.assertEqual(sco.status, "Partially Received")

		# Keep another SCO open so transfers from the closed SCO must not reduce its reservation
		open_sco = get_subcontracting_order(service_items=service_items)
		self.assertEqual(open_sco.status, "Open")

		bin_before_close = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname=["reserved_qty_for_sub_contract", "projected_qty"],
			as_dict=1,
		)

		# One unit remains reserved for the partially transferred SCO, plus ten for the open SCO
		self.assertEqual(
			bin_before_close.reserved_qty_for_sub_contract,
			bin_before_sco.reserved_qty_for_sub_contract + 11,
		)

		# Close the partially-received order
		sco.update_status("Closed")
		self.assertEqual(sco.status, "Closed")

		bin_after_close = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname=["reserved_qty_for_sub_contract", "projected_qty"],
			as_dict=1,
		)

		# Closing releases the remaining unit without applying its transfer against the open SCO
		self.assertEqual(
			bin_after_close.reserved_qty_for_sub_contract,
			bin_before_sco.reserved_qty_for_sub_contract + 10,
		)
		self.assertEqual(bin_after_close.projected_qty, bin_before_close.projected_qty + 1)

	def test_send_to_subcontractor_ste_submit_without_sco_write_permission(self):
		"""A Stock-only user (can submit Stock Entries but has no Subcontracting Order write) must be
		able to submit and cancel a 'Send to Subcontractor' Stock Entry. The SCO status update on the
		on_submit/on_cancel path goes through the no-permission-check internal helper, not the
		whitelisted API boundary.

		Regression: the permission hardening put check_permission('write') on the shared status
		function, so a Stock Manager (no SCO write) hit PermissionError submitting/cancelling the
		Stock Entry. The suite otherwise runs as Administrator and never caught it."""
		from frappe.core.doctype.user_permission.test_user_permission import create_user

		make_stock_entry(target="_Test Warehouse - _TC", item_code="_Test Item", qty=10, basic_rate=100)

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
				"item_code": "_Test FG Item",
				"rm_item_code": "_Test Item",
				"item_name": "_Test Item",
				"qty": 10,
				"warehouse": "_Test Warehouse - _TC",
				"rate": 100,
				"amount": 1000,
				"stock_uom": "Nos",
			},
		]
		ste = frappe.get_doc(make_rm_stock_entry(sco.name, rm_items))
		ste.to_warehouse = "_Test Warehouse 1 - _TC"
		ste.save()

		stock_user = create_user("test_sco_stock_only@example.com", "Stock Manager")
		self.assertFalse(
			frappe.has_permission("Subcontracting Order", "write", user=stock_user.name),
			"Precondition: the Stock-only user must not have Subcontracting Order write permission.",
		)

		frappe.set_user(stock_user.name)
		try:
			ste.reload()
			ste.submit()  # must not raise PermissionError on the SCO status update
			ste.reload()
			ste.cancel()  # same on the cancel path
		finally:
			frappe.set_user("Administrator")

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

	@ERPNextTestSuite.change_settings("Buying Settings", {"allow_multiple_items": True})
	def test_supplied_qty(self):
		item_code = "_Test Subcontracted FG Item 5"
		make_item("Sub Contracted Raw Material 4", {"is_stock_item": 1, "is_sub_contracted_item": 1})

		make_subcontracted_item(item_code=item_code, raw_materials=["Sub Contracted Raw Material 4"])

		set_backflush_based_on("Material Transferred for Subcontract")

		order_qty = 250
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 2",
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

	def test_transfer_limit_counts_rows_sharing_a_raw_material(self):
		sco = get_subcontracting_order_sharing_a_raw_material()

		def transfer_20_for(fg_item):
			transfer_shared_raw_material(sco, fg_item, 20)

		both_rows = frappe.get_doc(make_rm_stock_entry(sco.name))
		for row in both_rows.items:
			row.qty = 20
		self.assertRaises(frappe.ValidationError, both_rows.save)

		stock_uom_row = frappe.get_doc(make_rm_stock_entry(sco.name))
		stock_uom_row.items = stock_uom_row.items[:1]
		stock_uom_row.items[0].update({"qty": 100, "conversion_factor": 0.1})
		self.assertRaisesRegex(frappe.ValidationError, "cannot be transferred more than", stock_uom_row.save)

		transfer_20_for("Subcontracted Item SA7")
		self.assertRaises(frappe.ValidationError, transfer_20_for, "Subcontracted Item Shared RM")

	@ERPNextTestSuite.change_settings(
		"Buying Settings",
		{"backflush_raw_materials_of_subcontract_based_on": "Material Transferred for Subcontract"},
	)
	def test_transfer_refuses_a_subcontracted_item_not_on_the_order(self):
		sco = get_subcontracting_order()
		make_stock_in_entry(rm_items=get_rm_items(sco.supplied_items))
		ste = frappe.get_doc(make_rm_stock_entry(sco.name))
		for row in ste.items:
			row.subcontracted_item = "Subcontracted Item SA1"

		self.assertRaisesRegex(frappe.ValidationError, "is not a finished good", ste.insert)

	@ERPNextTestSuite.change_settings(
		"Buying Settings",
		{"backflush_raw_materials_of_subcontract_based_on": "Material Transferred for Subcontract"},
	)
	def test_transfer_relinks_a_row_moved_to_another_finished_good(self):
		sco = get_subcontracting_order_sharing_a_raw_material()
		ste = frappe.get_doc(make_rm_stock_entry(sco.name))
		ste.items = [row for row in ste.items if row.subcontracted_item == "Subcontracted Item SA7"]
		ste.items[0].subcontracted_item = "Subcontracted Item Shared RM"
		ste.insert()
		ste.submit()

		sco.reload()
		supplied_qty = {row.main_item_code: row.supplied_qty for row in sco.supplied_items}
		self.assertEqual(supplied_qty, {"Subcontracted Item SA7": 0, "Subcontracted Item Shared RM": 10})

	@ERPNextTestSuite.change_settings(
		"Buying Settings",
		{"backflush_raw_materials_of_subcontract_based_on": "Material Transferred for Subcontract"},
	)
	def test_transfer_accepts_a_finished_good_without_supplied_items(self):
		fg_item = make_item("Subcontracted Item Supplier Sourced", {"is_sub_contracted_item": 1}).name
		bom = make_bom(item=fg_item, raw_materials=["Subcontracted SRM Item 1"], do_not_submit=True)
		bom.items[0].sourced_by_supplier = 1
		bom.submit()

		sco = get_subcontracting_order_with_sa7_and(fg_item, "Subcontracted Service Item 9")
		make_stock_in_entry(rm_items=get_rm_items(sco.supplied_items))
		ste = frappe.get_doc(make_rm_stock_entry(sco.name))
		ste.items[0].subcontracted_item = fg_item

		ste.insert()

	def test_material_to_supplier_maps_a_shared_raw_material_only_once(self):
		sco = get_subcontracting_order_sharing_a_raw_material()
		transfer_shared_raw_material(sco, "Subcontracted Item SA7", 20)

		ste = frappe.get_doc(make_rm_stock_entry(sco.name))
		self.assertFalse([row for row in ste.items if row.item_code == "Subcontracted SRM Item 1"])

	@ERPNextTestSuite.change_settings(
		"Buying Settings",
		{"backflush_raw_materials_of_subcontract_based_on": "Material Transferred for Subcontract"},
	)
	def test_material_to_supplier_counts_shared_raw_material_per_finished_good(self):
		sco = get_subcontracting_order_sharing_a_raw_material()
		transfer_shared_raw_material(sco, "Subcontracted Item SA7", 15)

		ste = frappe.get_doc(make_rm_stock_entry(sco.name))
		self.assertEqual(
			[
				(row.subcontracted_item, row.qty)
				for row in ste.items
				if row.item_code == "Subcontracted SRM Item 1"
			],
			[("Subcontracted Item Shared RM", 10)],
		)

	@ERPNextTestSuite.change_settings("Buying Settings", {"over_transfer_allowance": 10})
	def test_material_to_supplier_skips_fully_sent_materials(self):
		make_subcontracted_item(item_code="Subcontracted Item Two RM")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 8",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item Two RM",
				"fg_item_qty": 10,
			}
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		rm_items[-1]["qty"] -= 2
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details=itemwise_details)

		ste = frappe.get_doc(make_rm_stock_entry(sco.name))
		self.assertEqual([(row.item_code, row.qty) for row in ste.items], [(rm_items[-1]["item_code"], 2)])

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
		frappe.flags.args = frappe._dict(
			subcontract_order=sco.name,
			rm_details=[d.name for d in sco.supplied_items],
			order_doctype=sco.doctype,
		)
		ste = get_materials_from_supplier(sco.name)
		ste.save()
		ste.submit()

		sco.load_from_db()

		self.assertEqual(sco.supplied_items[0].returned_qty, 5)

	def test_status_counts_materials_returned_by_supplier(self):
		sco = get_subcontracting_order()
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name, rm_items=rm_items, itemwise_details=copy.deepcopy(itemwise_details)
		)

		frappe.flags.args = frappe._dict(
			subcontract_order=sco.name,
			rm_details=[d.name for d in sco.supplied_items],
			order_doctype=sco.doctype,
		)
		ste = get_materials_from_supplier(sco.name)
		ste.items[0].qty = 4
		ste.save()
		ste.submit()

		self.assertEqual(
			frappe.db.get_value("Subcontracting Order", sco.name, "status"), "Partial Material Transferred"
		)
		self.assertTrue(frappe.get_doc("Subcontracting Order", sco.name).get_unreserved_qty())

	@ERPNextTestSuite.change_settings("Buying Settings", {"over_transfer_allowance": 20})
	def test_status_stays_partial_while_one_raw_material_is_short(self):
		make_subcontracted_item(item_code="Subcontracted Item Two RM")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 8",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item Two RM",
				"fg_item_qty": 10,
			}
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		rm_items[0]["qty"] += 1
		rm_items[1]["qty"] -= 1
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details=itemwise_details)

		self.assertEqual(
			frappe.db.get_value("Subcontracting Order", sco.name, "status"), "Partial Material Transferred"
		)

	def test_transfer_cannot_be_cancelled_after_its_material_was_consumed(self):
		sco = make_reserving_order_with_new_items("Consumed Cancel")
		sco.reserve_stock = 0
		rm_items = get_rm_items(sco.supplied_items)
		make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		transfer = make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})
		# stock of other orders at the same supplier
		make_stock_entry(
			target=sco.supplier_warehouse, item_code=rm_items[0]["item_code"], qty=10, basic_rate=100
		)
		make_subcontracting_receipt(sco.name).submit()

		self.assertRaisesRegex(frappe.ValidationError, "already consumed", transfer.cancel)

	def test_return_of_material_sent_in_another_uom_is_in_stock_uom(self):
		sco = make_reserving_order_with_new_items(
			"Box Return", rm_properties={"uoms": [{"uom": "Box", "conversion_factor": 2}]}
		)
		sco.reserve_stock = 0
		make_stock_in_entry(rm_items=get_rm_items(sco.supplied_items))
		sco.submit()
		transfer = frappe.get_doc(make_rm_stock_entry(sco.name))
		transfer.items[0].update({"uom": "Box", "conversion_factor": 2, "qty": 2})
		transfer.submit()

		frappe.flags.args = frappe._dict(
			subcontract_order=sco.name,
			rm_details=[d.name for d in sco.supplied_items],
			order_doctype=sco.doctype,
		)
		ste = get_materials_from_supplier(sco.name)

		self.assertEqual((ste.items[0].qty, ste.items[0].uom), (4, ste.items[0].stock_uom))

	@ERPNextTestSuite.change_settings(
		"Buying Settings",
		{"backflush_raw_materials_of_subcontract_based_on": "Material Transferred for Subcontract"},
	)
	def test_receipt_skips_a_serial_no_returned_by_the_supplier(self):
		sco, received = make_order_sent_to_supplier(
			"Serial Return", {"has_serial_no": 1, "serial_no_series": "SCOSR-.####"}
		)
		ste = get_return_of_components(sco)
		ste.items[0].update({"qty": 1, "serial_no": received.serial_no[0]})
		ste.submit()

		scr = make_subcontracting_receipt(sco.name)
		scr.items[0].qty = scr.items[0].received_qty = 2
		scr.submit()

		consumed = get_serial_numbers_from_bundle(scr.supplied_items[0].serial_and_batch_bundle)
		self.assertEqual(consumed, sorted(received.serial_no[1:]))

	@ERPNextTestSuite.change_settings(
		"Buying Settings",
		{"backflush_raw_materials_of_subcontract_based_on": "Material Transferred for Subcontract"},
	)
	def test_receipt_refuses_a_returned_serial_no_in_the_serial_no_field(self):
		sco, received = make_order_sent_to_supplier(
			"Serial Field Return", {"has_serial_no": 1, "serial_no_series": "SCOSF-.####"}
		)
		ste = get_return_of_components(sco)
		ste.items[0].update({"qty": 1, "serial_no": received.serial_no[0]})
		ste.submit()

		scr = make_receipt_consuming_serial_no(sco, received.serial_no[0])

		self.assertRaisesRegex(frappe.ValidationError, "have not been supplied", scr.save)

	@ERPNextTestSuite.change_settings(
		"Buying Settings",
		{"backflush_raw_materials_of_subcontract_based_on": "Material Transferred for Subcontract"},
	)
	def test_serial_no_sent_on_a_serial_no_field_row_counts_once(self):
		sco, received = make_order_sent_to_supplier(
			"Serial Field Mix", {"has_serial_no": 1, "serial_no_series": "SCOSM-.####"}
		)
		get_return_of_components(sco).submit()
		first, second = received.serial_no[:2]
		resend = frappe.get_doc(make_rm_stock_entry(sco.name))
		field_row = resend.items[0]
		field_row.update(
			{"qty": 1, "serial_no": first, "use_serial_batch_fields": 1, "serial_and_batch_bundle": None}
		)
		bundle_row = resend.append("items", frappe.copy_doc(field_row).as_dict())
		bundle = make_serial_batch_bundle(
			frappe._dict(
				item_code=bundle_row.item_code,
				warehouse=bundle_row.s_warehouse,
				qty=-1,
				serial_nos=SerialBatchIdentity("Serial No").resolve(bundle_row.item_code, [second]),
				voucher_type="Stock Entry",
				type_of_transaction="Outward",
				do_not_submit=True,
			)
		)
		bundle_row.update(
			{"serial_no": "", "use_serial_batch_fields": 0, "serial_and_batch_bundle": bundle.name}
		)
		resend.submit()
		ste = get_return_of_components(sco)
		ste.items[0].update({"qty": 1, "serial_no": first})
		ste.submit()

		scr = make_receipt_consuming_serial_no(sco, first)

		self.assertRaisesRegex(frappe.ValidationError, "have not been supplied", scr.save)

	@ERPNextTestSuite.change_settings(
		"Buying Settings",
		{"backflush_raw_materials_of_subcontract_based_on": "Material Transferred for Subcontract"},
	)
	def test_return_of_components_skips_batch_qty_returned_by_the_supplier(self):
		sco, received = make_order_sent_to_supplier(
			"Batch Return", {"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "SCOBR-.####"}
		)
		ste = get_return_of_components(sco)
		row = ste.items[0]
		bundle = make_serial_batch_bundle(
			frappe._dict(
				item_code=row.item_code,
				warehouse=row.s_warehouse,
				qty=-1,
				batches={next(iter(received.batch_no)): 1},
				voucher_type="Stock Entry",
				type_of_transaction="Outward",
				do_not_submit=True,
			)
		)
		row.update(
			{"qty": 1, "batch_no": None, "use_serial_batch_fields": 0, "serial_and_batch_bundle": bundle.name}
		)
		ste.submit()

		self.assertEqual(get_return_of_components(sco).items[0].qty, 2)

	def test_return_cannot_take_back_more_than_the_order_has_at_the_supplier(self):
		sco = get_subcontracting_order()
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name, rm_items=rm_items, itemwise_details=copy.deepcopy(itemwise_details)
		)
		scr = make_subcontracting_receipt(sco.name)
		scr.items[0].qty -= 5
		scr.submit()

		frappe.flags.args = frappe._dict(
			subcontract_order=sco.name,
			rm_details=[d.name for d in sco.supplied_items],
			order_doctype=sco.doctype,
		)
		ste = get_materials_from_supplier(sco.name)
		row = next(
			row
			for row in ste.items
			if not any(frappe.get_cached_value("Item", row.item_code, ["has_serial_no", "has_batch_no"]))
		)
		row.qty += 1

		self.assertRaisesRegex(frappe.ValidationError, "can be returned against", ste.save)

	@ERPNextTestSuite.change_settings("Buying Settings", {"over_transfer_allowance": 100})
	def test_return_of_components_skips_the_float_remainder_of_a_consumed_material(self):
		fg_item = make_item(
			"Subcontracted FG Item Remainder", {"is_stock_item": 1, "is_sub_contracted_item": 1}
		).name
		consumed_item, leftover_item = (
			make_item(f"Subcontracted RM Item Remainder {n}", {"is_stock_item": 1, "stock_uom": "Kg"}).name
			for n in (1, 2)
		)
		make_bom(
			item=fg_item, raw_materials=[consumed_item, leftover_item], rm_qty=0.3, rate=100, currency="INR"
		)
		service_item = make_item("Subcontracted Service Item Remainder", {"is_stock_item": 0}).name
		sco = get_subcontracting_order(
			service_items=[
				{
					"warehouse": "_Test Warehouse - _TC",
					"item_code": service_item,
					"qty": 1,
					"rate": 100,
					"fg_item": fg_item,
					"fg_item_qty": 1,
				}
			]
		)
		rm_items = {row["item_code"]: row for row in get_rm_items(sco.supplied_items)}
		for item_code, qty in ((consumed_item, 0.1), (consumed_item, 0.2), (leftover_item, 0.5)):
			make_stock_entry(target="_Test Warehouse - _TC", item_code=item_code, qty=qty, basic_rate=100)
			make_stock_transfer_entry(
				sco_no=sco.name, rm_items=[{**rm_items[item_code], "qty": qty}], itemwise_details={}
			)
		make_subcontracting_receipt(sco.name).submit()

		# the order offers only the rows the receipt did not consume in full
		frappe.flags.args = frappe._dict(
			subcontract_order=sco.name,
			rm_details=[row.name for row in sco.supplied_items if row.rm_item_code == leftover_item],
			order_doctype=sco.doctype,
		)
		ste = get_materials_from_supplier(sco.name)

		self.assertEqual([(row.item_code, row.qty) for row in ste.items], [(leftover_item, 0.2)])

	def test_return_of_components_sent_in_another_uom(self):
		rm_item = make_item(
			"Subcontracted RM In Box", {"is_stock_item": 1}, uoms=[{"uom": "Box", "conversion_factor": 10}]
		).name
		make_subcontracted_item(item_code="Subcontracted Item RM In Box", raw_materials=[rm_item])
		sco = get_subcontracting_order(
			service_items=[
				{
					"warehouse": "_Test Warehouse - _TC",
					"item_code": "Subcontracted Service Item 7",
					"qty": 10,
					"rate": 100,
					"fg_item": "Subcontracted Item RM In Box",
					"fg_item_qty": 10,
				}
			]
		)
		make_stock_entry(target="_Test Warehouse - _TC", item_code=rm_item, qty=10, basic_rate=100)
		send = frappe.get_doc(make_rm_stock_entry(sco.name))
		send.items[0].update({"qty": 1, "uom": "Box", "conversion_factor": 10})
		send.submit()

		frappe.flags.args = frappe._dict(
			subcontract_order=sco.name,
			rm_details=[d.name for d in sco.supplied_items],
			order_doctype=sco.doctype,
		)
		ste = get_materials_from_supplier(sco.name)
		self.assertEqual((ste.items[0].qty, ste.items[0].conversion_factor), (10, 1))
		ste.submit()

		sco.load_from_db()
		self.assertEqual(sco.supplied_items[0].total_supplied_qty, 0)

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

		self.assertEqual(mr.docstatus, 1)

		new_requested_qty = frappe.db.get_value(
			"Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "Subcontracted Item SA8"},
			fieldname="indented_qty",
		)
		new_requested_qty = flt(new_requested_qty)

		self.assertEqual(requested_qty + 10, new_requested_qty)

		po = make_subcontracted_purchase_order_from_material_request(mr.name)

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

	def test_stopped_material_request_blocks_only_new_subcontracting_orders(self):
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		mr = make_material_request(
			item_code="Subcontracted Item SA8", material_request_type="Purchase", qty=10
		)
		po = make_subcontracted_purchase_order_from_material_request(mr.name)
		sco = create_subcontracting_order(po_name=po.name, do_not_save=1)
		sco.items[0].qty = 4
		sco.insert()
		sco.submit()
		frappe.get_doc("Material Request", mr.name).update_status("Stopped")

		update_subcontracting_order_status(sco.name, "Closed")
		self.assertEqual(frappe.db.get_value("Subcontracting Order", sco.name, "status"), "Closed")
		self.assertRaises(frappe.InvalidStatusError, create_subcontracting_order, po_name=po.name)

	@ERPNextTestSuite.change_settings("System Settings", {"float_precision": 3})
	def test_subcontracting_order_rm_required_items_for_precision(self):
		item_code = "Subcontracted Item SA9"
		raw_materials = ["Subcontracted SRM Item 9"]
		if not frappe.db.exists("BOM", {"item": item_code}):
			make_bom(item=item_code, raw_materials=raw_materials, rate=100, rm_qty=1.04)

		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 9",
				"qty": 1,  # 202.0656,
				"rate": 100,
				"fg_item": "Subcontracted Item SA9",
				"fg_item_qty": 202.0656,
			},
		]

		sco = get_subcontracting_order(service_items=service_items)
		sco.reload()

		self.assertEqual(sco.supplied_items[0].required_qty, 210.149)

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_stock_reservation(self):
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_sre_details_for_voucher,
		)

		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 4",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA4",
				"fg_item_qty": 10,
			}
		]

		sco = get_subcontracting_order(service_items=service_items, do_not_submit=1)
		sco.reserve_stock = 1

		rm_items = get_rm_items(sco.supplied_items)
		make_stock_in_entry(rm_items=rm_items)
		sco.submit()

		sre_list = get_sre_details_for_voucher("Subcontracting Order", sco.name)
		self.assertGreater(len(sre_list), 0)

		se_dict = make_rm_stock_entry(sco.name)
		se = frappe.get_doc(se_dict)
		se.items[-1].use_serial_batch_fields = 1
		se.save()
		se.submit()
		sco.reload()

		for sre in sre_list:
			self.assertEqual(frappe.get_value("Stock Reservation Entry", sre.name, "status"), "Closed")

		make_subcontracting_receipt(sco.name).submit()
		for status in frappe.get_all(
			"Stock Reservation Entry", filters={"voucher_no": sco.name, "docstatus": 1}, pluck="status"
		)[:3]:
			self.assertEqual(status, "Delivered")

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_used_reservations_are_not_reserved_stock(self):
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import has_reserved_stock

		sco = get_subcontracting_order(do_not_submit=1)
		sco.reserve_stock = 1
		make_stock_in_entry(rm_items=get_rm_items(sco.supplied_items))
		sco.submit()

		frappe.get_doc(make_rm_stock_entry(sco.name)).submit()
		make_subcontracting_receipt(sco.name).submit()

		self.assertFalse(has_reserved_stock(sco.doctype, sco.name))

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_closing_releases_stock_reservations(self):
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import has_reserved_stock

		sco = get_subcontracting_order(do_not_submit=1)
		sco.reserve_stock = 1
		make_stock_in_entry(rm_items=get_rm_items(sco.supplied_items))
		sco.submit()
		self.assertTrue(has_reserved_stock(sco.doctype, sco.name))

		update_subcontracting_order_status(sco.name, "Closed")

		self.assertFalse(has_reserved_stock(sco.doctype, sco.name))

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_closing_keeps_reservations_of_transferred_material(self):
		sco = get_subcontracting_order(do_not_submit=1)
		sco.reserve_stock = 1
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		make_stock_transfer_entry(
			sco_no=sco.name, rm_items=rm_items[:1], itemwise_details=copy.deepcopy(itemwise_details)
		)

		update_subcontracting_order_status(sco.name, "Closed")

		reservations = frappe.get_all(
			"Stock Reservation Entry",
			filters={"voucher_type": sco.doctype, "voucher_no": sco.name},
			fields=["transferred_qty", "docstatus"],
		)
		self.assertTrue([row for row in reservations if row.transferred_qty])
		for row in reservations:
			self.assertEqual(row.docstatus, 1 if row.transferred_qty else 2)

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_used_reservation_is_kept_on_unreserve_and_close(self):
		sco = get_subcontracting_order(do_not_submit=1)
		sco.reserve_stock = 1
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		make_stock_transfer_entry(
			sco_no=sco.name, rm_items=rm_items, itemwise_details=copy.deepcopy(itemwise_details)
		)
		receipt = make_subcontracting_receipt(sco.name)
		receipt.items[0].qty = 5
		receipt.submit()

		consumed = frappe.get_all(
			"Stock Reservation Entry",
			filters={"voucher_no": sco.name, "docstatus": 1, "consumed_qty": (">", 0)},
			pluck="name",
		)
		self.assertTrue(consumed)
		sre = frappe.get_doc("Stock Reservation Entry", consumed[0])
		self.assertRaisesRegex(frappe.ValidationError, "Close the Subcontracting Order", sre.cancel)

		update_subcontracting_order_status(sco.name, "Closed")
		sre = frappe.get_doc("Stock Reservation Entry", consumed[0])
		self.assertEqual(sre.docstatus, 1)
		self.assertRaisesRegex(frappe.ValidationError, "is already used by", sre.cancel)

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_closing_releases_unused_balance_of_partly_transferred_reservation(self):
		sco = get_subcontracting_order(do_not_submit=1)
		sco.reserve_stock = 1
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		half_transfer = copy.deepcopy(rm_items[:1])
		half_transfer[0]["qty"] /= 2
		make_stock_transfer_entry(
			sco_no=sco.name, rm_items=half_transfer, itemwise_details=copy.deepcopy(itemwise_details)
		)

		update_subcontracting_order_status(sco.name, "Closed")

		reservation = frappe.get_all(
			"Stock Reservation Entry",
			filters={"voucher_type": sco.doctype, "voucher_no": sco.name, "docstatus": 1},
			fields=["reserved_qty", "transferred_qty", "status"],
		)
		self.assertEqual(len(reservation), 1)
		self.assertEqual(reservation[0].transferred_qty, half_transfer[0]["qty"])
		self.assertEqual(reservation[0].reserved_qty, reservation[0].transferred_qty)
		self.assertEqual(reservation[0].status, "Closed")

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_closing_releases_unused_batches_of_partly_transferred_reservation(self):
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 4",
				"qty": 4,
				"rate": 100,
				"fg_item": "Subcontracted Item SA4",
				"fg_item_qty": 4,
			}
		]
		sco = get_subcontracting_order(service_items=service_items, do_not_submit=1)
		sco.reserve_stock = 1
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		half_transfer = copy.deepcopy(rm_items)
		for item in half_transfer:
			item["qty"] /= 2
		make_stock_transfer_entry(sco_no=sco.name, rm_items=half_transfer, itemwise_details=itemwise_details)

		update_subcontracting_order_status(sco.name, "Closed")

		reservations = frappe.get_all(
			"Stock Reservation Entry",
			filters={
				"voucher_type": sco.doctype,
				"voucher_no": sco.name,
				"docstatus": 1,
				"reservation_based_on": "Serial and Batch",
			},
			pluck="name",
		)
		self.assertTrue(reservations)
		for name in reservations:
			for entry in frappe.get_doc("Stock Reservation Entry", name).sb_entries:
				self.assertEqual(entry.qty, entry.delivered_qty)

		update_subcontracting_order_status(sco.name)
		make_stock_transfer_entry(sco_no=sco.name, rm_items=half_transfer, itemwise_details=itemwise_details)
		for name in reservations:
			reservation = frappe.get_doc("Stock Reservation Entry", name)
			self.assertLessEqual(reservation.transferred_qty, reservation.reserved_qty)

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"enable_stock_reservation": 1, "allow_partial_reservation": 1}
	)
	def test_transfer_keeps_the_supplier_warehouse_reservation_of_an_earlier_transfer(self):
		sco = make_reserving_order_with_new_items("Split Reserve")
		rm_items = get_rm_items(sco.supplied_items)
		rm_items[0]["qty"] = 2
		make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		make_stock_in_entry(rm_items=rm_items)

		first_transfer = make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})

		reservation = frappe.get_value(
			"Stock Reservation Entry",
			{"voucher_no": sco.name, "docstatus": 1, "from_voucher_no": first_transfer.name},
			["reserved_qty", "transferred_qty", "status"],
			as_dict=True,
		)
		self.assertEqual(reservation.reserved_qty, 2)
		self.assertEqual(reservation.transferred_qty, 0)
		self.assertEqual(reservation.status, "Reserved")

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_transfer_from_another_warehouse_uses_the_order_reservation(self):
		sco = make_reserving_order_with_new_items("Other Source")
		rm_items = get_rm_items(sco.supplied_items)
		make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		rm_items[0]["warehouse"] = "_Test Warehouse 2 - _TC"
		make_stock_in_entry(rm_items=rm_items)

		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})

		reservation = frappe.get_value(
			"Stock Reservation Entry",
			{"voucher_no": sco.name, "docstatus": 1, "warehouse": "_Test Warehouse - _TC"},
			["transferred_qty", "status"],
			as_dict=True,
		)
		self.assertEqual(reservation.transferred_qty, 4)
		self.assertEqual(reservation.status, "Closed")

	@ERPNextTestSuite.change_settings(
		"Stock Settings",
		{"enable_stock_reservation": 1, "auto_reserve_serial_and_batch": 1, "allow_partial_reservation": 1},
	)
	def test_transfer_cancel_reopens_the_reservations_of_the_remaining_transfers(self):
		sco = make_reserving_order_with_new_items(
			"Batch Cancel",
			qty=10,
			rm_properties={"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "SCOBC-.####"},
		)
		row = sco.supplied_items[0]
		rm_items = get_rm_items(sco.supplied_items)
		rm_items[0]["qty"] = 6
		batch_no = next(iter(make_stock_in_entry(rm_items=rm_items)[row.rm_item_code].batch_no))
		sco.submit()
		make_stock_entry(
			item_code=row.rm_item_code, qty=4, to_warehouse=row.reserve_warehouse, batch_no=batch_no, rate=100
		)
		sco.reserve_raw_materials(
			items=[{"name": row.name, "qty_to_reserve": 4, "warehouse": row.reserve_warehouse}]
		)

		itemwise_details = {
			row.rm_item_code: frappe._dict(
				{"qty": 10, "serial_no": [], "batch_no": defaultdict(float, {batch_no: 10})}
			)
		}
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details=itemwise_details)
		rm_items[0]["qty"] = 4
		make_stock_transfer_entry(
			sco_no=sco.name, rm_items=rm_items, itemwise_details=itemwise_details
		).cancel()

		reservations = frappe.get_all(
			"Stock Reservation Entry",
			filters={"voucher_no": sco.name, "docstatus": 1, "warehouse": row.reserve_warehouse},
			fields=["reserved_qty", "transferred_qty"],
			order_by="creation",
			as_list=True,
		)
		self.assertEqual([tuple(reservation) for reservation in reservations], [(6, 6), (4, 0)])

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"enable_stock_reservation": 1, "auto_reserve_serial_and_batch": 1}
	)
	def test_receipt_cancel_reopens_only_its_own_consumption(self):
		self.assertEqual(cancel_one_of_two_receipts(-1), [(6, 6), (4, 0)])

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"enable_stock_reservation": 1, "auto_reserve_serial_and_batch": 1}
	)
	def test_first_receipt_cancel_reopens_only_its_own_consumption(self):
		self.assertEqual(cancel_one_of_two_receipts(0), [(6, 0), (4, 4)])

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"enable_stock_reservation": 1, "auto_reserve_serial_and_batch": 1}
	)
	def test_receipt_cancel_replays_an_earlier_cancelled_receipt(self):
		sco = make_order_with_two_batch_transfers()
		first = make_receipt_of_qty(sco, 6)
		second = make_receipt_of_qty(sco, 4)
		first.cancel()
		make_receipt_of_qty(sco, 6)
		second.cancel()

		self.assertEqual(get_supplier_warehouse_consumption(sco), [(6, 6), (4, 0)])

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"enable_stock_reservation": 1, "auto_reserve_serial_and_batch": 1}
	)
	def test_transfer_takes_every_batch_the_order_reserved(self):
		sco = make_reserving_order_with_new_items(
			"Reserved Batches",
			rm_properties={"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "SCORB-.####"},
		)
		row = sco.supplied_items[0]
		# the order reserves 2 + 2, so the second batch has only 1 free
		for qty, rate in ((2, 100), (3, 120)):
			make_stock_entry(
				item_code=row.rm_item_code, qty=qty, to_warehouse=row.reserve_warehouse, rate=rate
			)
		sco.submit()

		transfer = make_stock_transfer_entry(
			sco_no=sco.name, rm_items=get_rm_items(sco.supplied_items), itemwise_details={}
		)

		reservation = frappe.get_doc(
			"Stock Reservation Entry",
			{"voucher_no": sco.name, "docstatus": 1, "warehouse": row.reserve_warehouse},
		)
		picked = frappe.get_all(
			"Serial and Batch Bundle",
			filters={"voucher_no": transfer.name, "docstatus": 1},
			fields=["entries.batch_no", "entries.qty"],
		)
		self.assertEqual(
			{entry.batch_no: abs(entry.qty) for entry in picked},
			{entry.batch_no: entry.qty for entry in reservation.sb_entries},
		)
		self.assertEqual(reservation.status, "Closed")

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"enable_stock_reservation": 1, "allow_partial_reservation": 1}
	)
	def test_transfer_cancel_keeps_earlier_unreserved_qty_off_a_later_reservation(self):
		sco, row, _first, second = make_transfers_around_a_later_reservation("Later Reservation")
		second.cancel()

		self.assertEqual(get_reserved_and_transferred_qty(sco, row.reserve_warehouse), [(6, 6), (2, 0)])

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"enable_stock_reservation": 1, "allow_partial_reservation": 1}
	)
	def test_transfer_cancel_times_a_transfer_by_its_first_ledger_entry(self):
		sco, row, first, second = make_transfers_around_a_later_reservation("Recreated Ledger")
		frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"based_on": "Transaction",
				"voucher_type": first.doctype,
				"voucher_no": first.name,
				"posting_date": first.posting_date,
				"posting_time": first.posting_time,
				"company": first.company,
				"recreate_stock_ledgers": 1,
			}
		).submit()
		second.cancel()

		self.assertEqual(get_reserved_and_transferred_qty(sco, row.reserve_warehouse), [(6, 6), (2, 0)])

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"enable_stock_reservation": 1, "auto_reserve_serial_and_batch": 0}
	)
	def test_transfer_uses_batched_raw_material_reservation_made_without_auto_reserve(self):
		service_item = make_item("Subcontracted Service Item Batch Reserve", {"is_stock_item": 0}).name
		fg_item = make_item(
			"Subcontracted FG Item Batch Reserve", {"is_stock_item": 1, "is_sub_contracted_item": 1}
		).name
		rm_item = make_item(
			"Subcontracted Batch RM Item Reserve",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "BATCH-RMRS-.####",
			},
		).name
		make_bom(item=fg_item, raw_materials=[rm_item], rate=100, currency="INR")

		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": service_item,
				"qty": 2,
				"rate": 100,
				"fg_item": fg_item,
				"fg_item_qty": 2,
			}
		]
		sco = get_subcontracting_order(service_items=service_items, do_not_submit=1)
		sco.reserve_stock = 1
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		sco.submit()

		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details=itemwise_details)

		reservation = frappe.get_value(
			"Stock Reservation Entry",
			{"voucher_no": sco.name, "docstatus": 1, "warehouse": sco.supplied_items[0].reserve_warehouse},
			["reserved_qty", "transferred_qty"],
			as_dict=True,
		)
		self.assertEqual(reservation.reserved_qty, 2)
		self.assertEqual(reservation.transferred_qty, 2)

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_return_of_components_reserves_the_returned_qty_again(self):
		sco = make_reserving_order_with_new_items("Return Reserved", qty=10)
		row = sco.supplied_items[0]
		rm_items = get_rm_items(sco.supplied_items)
		make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})
		warehouses = [row.reserve_warehouse, sco.supplier_warehouse]

		return_entry = make_return_of_components(sco, qty=4)
		self.assertEqual(get_reserved_stock(row.rm_item_code, warehouses), [4, 6])

		return_entry.cancel()
		self.assertEqual(get_reserved_stock(row.rm_item_code, warehouses), [0, 10])

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	@ERPNextTestSuite.change_settings("Buying Settings", {"over_transfer_allowance": 50})
	def test_return_of_components_releases_the_qty_the_order_does_not_need(self):
		sco = make_reserving_order_with_new_items("Return Surplus", qty=10)
		row = sco.supplied_items[0]
		rm_items = get_rm_items(sco.supplied_items)
		rm_items[0]["qty"] = 12
		make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})

		make_return_of_components(sco, qty=4)

		self.assertEqual(
			get_reserved_stock(row.rm_item_code, [row.reserve_warehouse, sco.supplier_warehouse]), [2, 8]
		)

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_return_of_components_reserves_each_warehouse_it_returns_to(self):
		sco = make_reserving_order_with_new_items("Return Split", qty=10)
		row = sco.supplied_items[0]
		rm_items = get_rm_items(sco.supplied_items)
		make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})

		return_entry = make_return_of_components(sco, qty=2, do_not_submit=True)
		return_entry.append("items", frappe.copy_doc(return_entry.items[0]))
		return_entry.items[1].t_warehouse = "_Test Warehouse 2 - _TC"
		return_entry.submit()

		self.assertEqual(
			get_reserved_stock(row.rm_item_code, [row.reserve_warehouse, "_Test Warehouse 2 - _TC"]), [2, 2]
		)

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_transfer_cancels_only_after_the_return_of_its_stock(self):
		sco = make_reserving_order_with_new_items("Return Before Cancel", qty=10)
		rm_items = get_rm_items(sco.supplied_items)
		make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		transfer = make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})
		return_entry = make_return_of_components(sco, qty=4)

		self.assertRaisesRegex(frappe.ValidationError, "later entry", transfer.cancel)

		return_entry.cancel()
		frappe.get_doc("Stock Entry", transfer.name).cancel()

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_return_cancels_only_after_the_resend_of_its_stock(self):
		sco = make_reserving_order_with_new_items("Resend Before Cancel", qty=10)
		rm_items = get_rm_items(sco.supplied_items)
		make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})
		return_entry = make_return_of_components(sco, qty=4)
		rm_items[0]["qty"] = 4
		resend = make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})

		self.assertRaisesRegex(frappe.ValidationError, "later entry", return_entry.cancel)

		resend.cancel()
		frappe.get_doc("Stock Entry", return_entry.name).cancel()

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_receipt_cancel_gives_back_only_its_own_batch_consumption(self):
		sco = make_reserving_order_with_new_items(
			"Return Batch",
			qty=10,
			rm_properties={"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "SCORB-.####"},
		)
		row = sco.supplied_items[0]
		rm_items = get_rm_items(sco.supplied_items)
		batch_no = next(iter(make_stock_in_entry(rm_items=rm_items)[row.rm_item_code].batch_no))
		sco.submit()
		itemwise_details = {
			row.rm_item_code: frappe._dict(
				{"qty": 10, "serial_no": [], "batch_no": defaultdict(float, {batch_no: 10})}
			)
		}
		rm_items[0]["qty"] = 5
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details=itemwise_details)
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details=itemwise_details)
		make_return_of_components(sco, qty=5)
		scr = make_subcontracting_receipt(sco.name)
		scr.items[0].qty = 5
		scr.save()
		scr.submit()

		scr.cancel()

		reservations = frappe.get_all(
			"Stock Reservation Entry",
			filters={"voucher_no": sco.name, "docstatus": 1, "warehouse": sco.supplier_warehouse},
			fields=["transferred_qty", "consumed_qty"],
			order_by="creation",
			as_list=True,
		)
		self.assertEqual([tuple(reservation) for reservation in reservations], [(5, 0), (0, 0)])

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	@ERPNextTestSuite.change_settings("Buying Settings", {"over_transfer_allowance": 50})
	def test_first_receipt_cancel_keeps_the_later_returns_and_receipts(self):
		sco = make_reserving_order_with_new_items(
			"Return Resend",
			qty=10,
			rm_properties={"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "SCORR-.####"},
		)
		row = sco.supplied_items[0]
		rm_items = get_rm_items(sco.supplied_items)
		batches = []
		for qty in (10, 5, 5):
			rm_items[0]["qty"] = qty
			batches.append(next(iter(make_stock_in_entry(rm_items=rm_items)[row.rm_item_code].batch_no)))
		a, b, c = batches
		sco.submit()

		def send(*batch_nos):
			itemwise_details = {
				row.rm_item_code: frappe._dict(
					{"qty": 10, "serial_no": [], "batch_no": defaultdict(float, dict.fromkeys(batch_nos, 5))}
				)
			}
			rows = [{**rm_items[0], "qty": 5} for _batch_no in batch_nos]
			make_stock_transfer_entry(sco_no=sco.name, rm_items=rows, itemwise_details=itemwise_details)

		def receive(batch_no):
			receipt = make_subcontracting_receipt(sco.name)
			receipt.items[0].qty = 5
			receipt.save()
			receipt.supplied_items[0].batch_no = batch_no
			receipt.save()
			return receipt.submit()

		send(a, b)
		first_receipt = receive(a)
		make_return_of_components(sco, qty=5)
		send(a, c)
		second_receipt = receive(c)
		make_return_of_components(sco, qty=5)

		first_receipt.cancel()

		self.assertEqual(
			get_supplier_warehouse_reservations(sco),
			[(5, 0, {a: 0, b: 5}), (5, 5, {a: 5, c: 5})],
		)

		second_receipt.cancel()

		self.assertEqual([reservation[1] for reservation in get_supplier_warehouse_reservations(sco)], [0, 0])

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_cancel_replay_skips_returns_from_before_the_upgrade(self):
		sco = make_reserving_order_with_new_items("Return Before Upgrade", qty=10)
		row = sco.supplied_items[0]
		rm_items = get_rm_items(sco.supplied_items)
		make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		rm_items[0]["qty"] = 5
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})
		# unreserved stock at the supplier let a return submit before the upgrade
		make_stock_entry(item_code=row.rm_item_code, target=sco.supplier_warehouse, qty=4, basic_rate=100)
		with patch.object(
			StockEntry, "is_reserved_components_return", new_callable=PropertyMock, return_value=False
		):
			legacy_return = make_return_of_components(sco, qty=4)
		set_reserved_components_return_cutoff()
		receipt = make_subcontracting_receipt(sco.name)
		receipt.items[0].qty = 5
		receipt.save()
		receipt.submit()

		legacy_return.cancel()

		self.assertEqual(
			[reservation[:2] for reservation in get_supplier_warehouse_reservations(sco)], [(0, 5), (0, 0)]
		)

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_reservation_counts_supplied_qty(self):
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 4",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA4",
				"fg_item_qty": 10,
			}
		]
		sco = get_subcontracting_order(service_items=service_items, do_not_submit=1)
		sco.reserve_stock = 1
		make_stock_in_entry(rm_items=get_rm_items(sco.supplied_items))
		sco.submit()

		se = frappe.get_doc(make_rm_stock_entry(sco.name))
		se.items[-1].use_serial_batch_fields = 1
		se.save()
		se.submit()

		row = sco.supplied_items[0]
		make_stock_in_entry(rm_items=[{"item_code": row.rm_item_code, "warehouse": row.reserve_warehouse}])
		self.assertRaises(
			frappe.ValidationError,
			sco.reserve_raw_materials,
			items=[{"name": row.name, "qty_to_reserve": 1}],
		)

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"enable_stock_reservation": 1, "allow_partial_reservation": 1}
	)
	def test_unreserved_qty_skips_the_reservation_of_transferred_stock(self):
		sco = make_reserving_order_with_new_items("Unreserved After Transfer", qty=10)
		rm_items = get_rm_items(sco.supplied_items)
		rm_items[0]["qty"] = 6
		make_stock_in_entry(rm_items=rm_items)
		sco.submit()
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})

		sco.reload()
		self.assertEqual(sco.get_unreserved_qty(), {sco.supplied_items[0].name: 4})

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"enable_stock_reservation": 1, "allow_partial_reservation": 1}
	)
	def test_transfer_shares_batch_qty_across_reservations_of_a_row(self):
		warehouse = "_Test Warehouse - _TC"
		rm_item = make_item(
			properties={"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "SCO-SRE-B-.####"}
		).name
		fg_item = make_item(properties={"is_sub_contracted_item": 1}).name
		make_bom(item=fg_item, raw_materials=[rm_item], rate=100, currency="INR")

		receipt = make_stock_entry(item_code=rm_item, target=warehouse, qty=2, basic_rate=100)
		batch_no = get_batch_from_bundle(receipt.items[0].serial_and_batch_bundle)
		service_items = [
			{
				"warehouse": warehouse,
				"item_code": "Subcontracted Service Item 4",
				"qty": 4,
				"rate": 100,
				"fg_item": fg_item,
				"fg_item_qty": 4,
			}
		]
		sco = get_subcontracting_order(service_items=service_items, do_not_submit=1)
		sco.reserve_stock = 1
		sco.supplied_items[0].reserve_warehouse = warehouse
		sco.submit()

		make_stock_entry(
			item_code=rm_item,
			target=warehouse,
			qty=2,
			basic_rate=100,
			batch_no=batch_no,
			use_serial_batch_fields=1,
		)
		row = sco.supplied_items[0]
		sco.reserve_raw_materials(items=[{"name": row.name, "qty_to_reserve": 2, "warehouse": warehouse}])

		se = frappe.get_doc(make_rm_stock_entry(sco.name))
		se.items[0].qty = 3
		se.items[0].use_serial_batch_fields = 1
		se.items[0].batch_no = batch_no
		se.submit()

		transferred_qty = frappe.get_all(
			"Stock Reservation Entry",
			filters={"voucher_no": sco.name, "voucher_detail_no": row.name, "warehouse": warehouse},
			order_by="creation",
			pluck="transferred_qty",
		)
		self.assertEqual(transferred_qty, [2, 1])

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"enable_stock_reservation": 1, "allow_partial_reservation": 1}
	)
	def test_fractional_transfer_closes_each_reservation_of_a_row(self):
		warehouse = "_Test Warehouse - _TC"
		rm_item = make_item(properties={"stock_uom": "Kg"}).name
		fg_item = make_item(properties={"is_sub_contracted_item": 1}).name
		make_bom(item=fg_item, raw_materials=[rm_item], rate=100, rm_qty=0.1, currency="INR")

		make_stock_entry(item_code=rm_item, target=warehouse, qty=0.1, basic_rate=100)
		service_items = [
			{
				"warehouse": warehouse,
				"item_code": "Subcontracted Service Item 4",
				"qty": 3,
				"rate": 100,
				"fg_item": fg_item,
				"fg_item_qty": 3,
			}
		]
		sco = get_subcontracting_order(service_items=service_items, do_not_submit=1)
		sco.reserve_stock = 1
		sco.supplied_items[0].reserve_warehouse = warehouse
		sco.submit()

		make_stock_entry(item_code=rm_item, target=warehouse, qty=0.2, basic_rate=100)
		row = sco.supplied_items[0]
		sco.reserve_raw_materials(items=[{"name": row.name, "qty_to_reserve": 0.2, "warehouse": warehouse}])

		se = frappe.get_doc(make_rm_stock_entry(sco.name))
		se.items[0].qty = 0.3
		se.submit()

		statuses = frappe.get_all(
			"Stock Reservation Entry",
			filters={"voucher_no": sco.name, "voucher_detail_no": row.name, "warehouse": warehouse},
			pluck="status",
		)
		self.assertEqual(statuses, ["Closed", "Closed"])

	def test_stock_reservation_transfer(self):
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_serial_batch_entries_for_voucher,
			get_sre_details_for_voucher,
		)

		def get_serial_batch_entries(voucher_type, voucher_no):
			return [
				sorted(
					get_serial_batch_entries_for_voucher([sre.name]),
					key=lambda x: x.get("serial_no") or x.get("batch_no") or "",
				)
				for sre in get_sre_details_for_voucher(voucher_type, voucher_no)
			]

		plan = make_reserved_production_plan()
		sbe_pp_list = get_serial_batch_entries("Production Plan", plan.name)
		sco = make_subcontracting_order_from_plan(plan)

		self.assertEqual(sbe_pp_list, get_serial_batch_entries("Subcontracting Order", sco.name))

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_order_from_plan_without_raw_material_rows_reserves_from_stock(self):
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_sre_details_for_voucher,
		)

		plan = make_reserved_production_plan(reserve_stock=False)
		sco = make_subcontracting_order_from_plan(plan)

		self.assertTrue(get_sre_details_for_voucher("Subcontracting Order", sco.name))

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_order_from_plan_reserves_unplanned_raw_materials_from_stock(self):
		unplanned_item = make_item(properties={"is_stock_item": 1}).name
		sub_assembly = make_item(properties={"is_stock_item": 1, "is_sub_contracted_item": 1}).name
		make_bom(
			item=sub_assembly,
			raw_materials=["Subcontracted SRM Item 10", unplanned_item],
			rate=100,
			currency="INR",
		)

		plan = make_reserved_production_plan(sub_assembly=sub_assembly, unplanned_items=[unplanned_item])
		sco = make_subcontracting_order_from_plan(plan)

		for row in sco.supplied_items:
			self.assertEqual(row.stock_reserved_qty, row.required_qty)

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_closing_gives_the_unused_balance_back_to_the_plan(self):
		plan = make_reserved_production_plan()
		sco = make_subcontracting_order_from_plan(plan)
		rm_item = next(
			row
			for row in get_rm_items(sco.supplied_items)
			if not any(frappe.get_cached_value("Item", row["item_code"], ["has_serial_no", "has_batch_no"]))
		)
		rm_item["qty"] = 4
		make_stock_transfer_entry(sco_no=sco.name, rm_items=[rm_item], itemwise_details={})

		update_subcontracting_order_status(sco.name, "Closed")

		reserved_qty, delivered_qty, status = frappe.get_value(
			"Stock Reservation Entry",
			{
				"voucher_type": "Production Plan",
				"voucher_no": plan.name,
				"item_code": rm_item["item_code"],
				"docstatus": 1,
			},
			["reserved_qty", "delivered_qty", "status"],
		)
		self.assertEqual(delivered_qty, 4)
		self.assertEqual(status, "Partially Delivered")
		self.assertEqual(get_bin(rm_item["item_code"], rm_item["warehouse"]).reserved_stock, reserved_qty - 4)

	def test_raw_material_cost_is_converted_from_bom_currency(self):
		service_item = make_item("Subcontracted Service Item USD BOM", {"is_stock_item": 0}).name
		fg_item = make_item(
			"Subcontracted FG Item USD BOM", {"is_stock_item": 1, "is_sub_contracted_item": 1}
		).name
		rm_item = make_item("Subcontracted RM Item USD BOM", {"is_stock_item": 1, "valuation_rate": 800}).name
		bom = make_bom(item=fg_item, raw_materials=[rm_item], currency="USD", do_not_submit=True)
		bom.conversion_rate = 80
		bom.save()
		bom.submit()

		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": service_item,
				"qty": 5,
				"rate": 100,
				"fg_item": fg_item,
				"fg_item_qty": 5,
			}
		]
		sco = get_subcontracting_order(service_items=service_items, include_exploded_items=0)

		self.assertEqual(sco.items[0].rm_cost_per_qty, 800)
		self.assertEqual(sco.supplied_items[0].rate, 800)
		self.assertEqual(sco.supplied_items[0].amount, 4000)

	def test_service_cost_is_converted_to_company_currency(self):
		sco = make_foreign_currency_subcontracting_order()

		self.assertEqual(sco.supplier_currency, "USD")
		self.assertEqual(sco.conversion_rate, 80)

		# service items stay in the supplier's currency, as on the Purchase Order
		self.assertEqual(sco.service_items[0].rate, 500)
		self.assertEqual(sco.service_items[0].amount, 5000)
		self.assertEqual(sco.service_items[0].base_rate, 500 * 80)
		self.assertEqual(sco.service_items[0].base_amount, 5000 * 80)

		# costing fields are in company currency
		self.assertEqual(sco.items[0].service_cost_per_qty, 500 * 80)
		self.assertEqual(
			sco.items[0].rate,
			sco.items[0].rm_cost_per_qty + sco.items[0].service_cost_per_qty,
		)
		self.assertEqual(sco.total, sco.items[0].amount)

	def test_service_cost_backfill_recosts_closed_order(self):
		sco = make_foreign_currency_subcontracting_order()
		set_unconverted_service_cost(sco)
		sco.update_status("Closed")

		recalculate_subcontracting_order_service_cost()

		sco.reload()
		self.assertEqual(sco.conversion_rate, 80)
		self.assertEqual(sco.service_items[0].base_amount, 5000 * 80)
		self.assertEqual(sco.items[0].service_cost_per_qty, 500 * 80)
		self.assertEqual(sco.items[0].rate, sco.items[0].rm_cost_per_qty + 500 * 80)
		self.assertEqual(sco.total, sco.items[0].amount)

	def test_service_cost_backfill_recosts_order_without_purchase_order_item(self):
		sco = make_foreign_currency_subcontracting_order()
		set_unconverted_service_cost(sco)
		sco.items[0].db_set("purchase_order_item", None)

		recalculate_subcontracting_order_service_cost()

		sco.reload()
		self.assertEqual(sco.items[0].service_cost_per_qty, 500 * 80)
		self.assertEqual(sco.total, sco.items[0].amount)

	def test_service_cost_backfill_updates_draft_receipt(self):
		sco = make_foreign_currency_subcontracting_order()
		scr = make_subcontracting_receipt(sco.name).save()
		set_unconverted_service_cost(sco)
		frappe.db.set_value("Subcontracting Receipt Item", scr.items[0].name, "service_cost_per_qty", 500)

		recalculate_subcontracting_order_service_cost()

		self.assertEqual(
			frappe.db.get_value("Subcontracting Receipt Item", scr.items[0].name, "service_cost_per_qty"),
			500 * 80,
		)


def make_transfers_around_a_later_reservation(suffix):
	"""Reserve 6, transfer 8, reserve 2 more, then transfer 2."""
	sco = make_reserving_order_with_new_items(suffix, qty=10)
	row = sco.supplied_items[0]
	rm_items = get_rm_items(sco.supplied_items)
	rm_items[0]["qty"] = 6
	make_stock_in_entry(rm_items=rm_items)
	sco.submit()

	make_stock_entry(item_code=row.rm_item_code, qty=2, to_warehouse=row.reserve_warehouse, rate=100)
	rm_items[0]["qty"] = 8
	first = make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})

	make_stock_entry(item_code=row.rm_item_code, qty=2, to_warehouse=row.reserve_warehouse, rate=100)
	sco.reserve_raw_materials(
		items=[{"name": row.name, "qty_to_reserve": 2, "warehouse": row.reserve_warehouse}]
	)
	rm_items[0]["qty"] = 2
	second = make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details={})
	return sco, row, first, second


def get_reserved_and_transferred_qty(sco, warehouse):
	reservations = frappe.get_all(
		"Stock Reservation Entry",
		filters={"voucher_no": sco.name, "docstatus": 1, "warehouse": warehouse},
		fields=["reserved_qty", "transferred_qty"],
		order_by="creation",
		as_list=True,
	)
	return [tuple(reservation) for reservation in reservations]


def make_reserving_order_with_new_items(suffix, qty=4, rm_properties=None):
	"""Draft order for `qty` of a new subcontracted item using 1 new raw material each, with Reserve Stock on."""
	service_item = make_item(f"Subcontracted Service Item {suffix}", {"is_stock_item": 0}).name
	fg_item = make_item(
		f"Subcontracted FG Item {suffix}", {"is_stock_item": 1, "is_sub_contracted_item": 1}
	).name
	rm_item = make_item(f"Subcontracted RM Item {suffix}", {"is_stock_item": 1, **(rm_properties or {})}).name
	make_bom(item=fg_item, raw_materials=[rm_item], rate=100, currency="INR")

	service_items = [
		{
			"warehouse": "_Test Warehouse - _TC",
			"item_code": service_item,
			"qty": qty,
			"rate": 100,
			"fg_item": fg_item,
			"fg_item_qty": qty,
		}
	]
	sco = get_subcontracting_order(service_items=service_items, do_not_submit=1)
	sco.reserve_stock = 1
	return sco


def make_order_sent_to_supplier(suffix, rm_properties):
	"""Submitted order for 3 of a new subcontracted item, with all its raw material sent to the supplier."""
	sco = make_reserving_order_with_new_items(suffix, qty=3, rm_properties=rm_properties)
	sco.reserve_stock = 0
	rm_items = get_rm_items(sco.supplied_items)
	itemwise_details = make_stock_in_entry(rm_items=rm_items)
	sco.submit()
	received = copy.deepcopy(itemwise_details[rm_items[0]["item_code"]])
	make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details=itemwise_details)
	return sco, received


def get_return_of_components(sco):
	frappe.flags.args = frappe._dict(
		subcontract_order=sco.name,
		rm_details=[d.name for d in sco.supplied_items],
		order_doctype=sco.doctype,
	)
	return get_materials_from_supplier(sco.name)


def make_receipt_consuming_serial_no(sco, serial_no):
	"""Draft receipt of 1 whose supplied item names `serial_no` in its Serial No field."""
	scr = make_subcontracting_receipt(sco.name)
	scr.items[0].qty = scr.items[0].received_qty = 1
	scr.insert()
	scr.supplied_items[0].update(
		{"serial_no": serial_no, "serial_and_batch_bundle": None, "use_serial_batch_fields": 1}
	)
	return scr


def transfer_shared_raw_material(sco, fg_item, qty):
	row = next(
		row
		for row in sco.supplied_items
		if row.main_item_code == fg_item and row.rm_item_code == "Subcontracted SRM Item 1"
	)
	ste = frappe.get_doc(make_rm_stock_entry(sco.name, [{**row.as_dict(), "qty": qty}]))
	ste.save()
	ste.submit()


def make_return_of_components(sco, qty, do_not_submit=False):
	frappe.flags.args = frappe._dict(
		subcontract_order=sco.name, rm_details=[d.name for d in sco.supplied_items], order_doctype=sco.doctype
	)
	return_entry = get_materials_from_supplier(sco.name)
	return_entry.items[0].qty = qty
	# the mapped warehouses come from any earlier transfer or return, so set them
	return_entry.items[0].s_warehouse = sco.supplier_warehouse
	return_entry.items[0].t_warehouse = sco.supplied_items[0].reserve_warehouse
	if not do_not_submit:
		return_entry.submit()
	return return_entry


def get_supplier_warehouse_reservations(sco):
	"""Transferred qty, consumed qty and used qty per batch of each supplier warehouse reservation, oldest first."""
	reservations = frappe.get_all(
		"Stock Reservation Entry",
		filters={"voucher_no": sco.name, "docstatus": 1, "warehouse": sco.supplier_warehouse},
		fields=["name", "transferred_qty", "consumed_qty"],
		order_by="creation",
	)
	return [
		(
			reservation.transferred_qty,
			reservation.consumed_qty,
			dict(
				frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": reservation.name, "parenttype": "Stock Reservation Entry"},
					fields=["batch_no", "delivered_qty"],
					as_list=True,
				)
			),
		)
		for reservation in reservations
	]


def get_reserved_stock(item_code, warehouses):
	return [
		frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "reserved_stock")
		for warehouse in warehouses
	]


def set_alternative_item(item_code, alternative_item_code):
	frappe.db.set_value("Item", item_code, "allow_alternative_item", 1)
	frappe.get_doc(
		doctype="Item Alternative", item_code=item_code, alternative_item_code=alternative_item_code
	).insert()


def make_supplied_item_transfer(sco, row, link=True):
	rm_item = {
		"item_code": row.main_item_code,
		"rm_item_code": row.rm_item_code,
		"qty": row.required_qty,
		"warehouse": row.reserve_warehouse,
		"stock_uom": row.stock_uom,
	}
	if link:
		rm_item["name"] = row.name
	return frappe.get_doc(make_rm_stock_entry(sco.name, [rm_item]))


def make_foreign_currency_subcontracting_order():
	from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

	service_items = [
		{
			"warehouse": "_Test Warehouse - _TC",
			"item_code": "Subcontracted Service Item 7",
			"qty": 10,
			"rate": 500,
			"fg_item": "Subcontracted Item SA7",
			"fg_item_qty": 10,
		},
	]
	po = create_purchase_order(
		rm_items=service_items,
		is_subcontracted=1,
		supplier="_Test Supplier USD",
		currency="USD",
		supplier_warehouse="_Test Warehouse 1 - _TC",
		do_not_submit=1,
	)
	po.conversion_rate = 80
	po.submit()

	return create_subcontracting_order(po_name=po.name)


def set_unconverted_service_cost(sco):
	frappe.db.set_value("Subcontracting Order", sco.name, {"conversion_rate": 1, "total": 0})
	frappe.db.set_value(
		"Subcontracting Order Service Item", sco.service_items[0].name, {"base_rate": 0, "base_amount": 0}
	)
	frappe.db.set_value(
		"Subcontracting Order Item", sco.items[0].name, {"service_cost_per_qty": 500, "rate": 0, "amount": 0}
	)


def make_reserved_production_plan(
	reserve_stock=True, sub_assembly="Subcontracted Item SA10", unplanned_items=()
):
	"""Production Plan of one subcontracted sub-assembly that reserves its raw materials when `reserve_stock`.

	`unplanned_items` get no raw material row; without `reserve_stock` no item does."""
	from erpnext.manufacturing.doctype.production_plan.production_plan import (
		get_items_for_material_requests,
	)
	from erpnext.manufacturing.doctype.production_plan.test_production_plan import create_production_plan

	parent_fg = make_item()
	make_bom(item=parent_fg.name, raw_materials=[sub_assembly], rate=100, rm_qty=1, currency="INR")
	plan = create_production_plan(
		item_code=parent_fg.name,
		planned_qty=10,
		do_not_submit=True,
		reserve_stock=reserve_stock,
		skip_available_sub_assembly_item=True,
		for_warehouse="_Test Warehouse - _TC",
		sub_assembly_warehouse="_Test Warehouse - _TC",
		skip_getting_mr_items=True,
	)
	plan.get_sub_assembly_items()
	plan.sub_assembly_items[0].supplier = "_Test Supplier"
	for d in get_items_for_material_requests(plan.as_dict()):
		if reserve_stock and d["item_code"] not in unplanned_items:
			plan.append("mr_items", d)
		make_stock_entry(target="_Test Warehouse - _TC", item_code=d["item_code"], qty=10, basic_rate=100)
	plan.submit()
	return plan


def make_subcontracting_order_from_plan(plan):
	"""Subcontracting Order whose raw material reservations are taken from the plan's."""
	plan.make_work_order()
	po = frappe.get_doc(
		"Purchase Order",
		frappe.get_value("Purchase Order Item", {"production_plan": plan.name}, "parent"),
	)
	po.items[0].item_code = "Subcontracted Service Item 4"
	po.items[0].qty = 10
	po.submit()
	sco = create_subcontracting_order(po_name=po.name, do_not_save=1)
	sco.supplier_warehouse = "_Test Warehouse 1 - _TC"
	sco.reserve_stock = True
	sco.submit()
	sco.reload()
	return sco


def get_subcontracting_order_sharing_a_raw_material():
	make_subcontracted_item(
		item_code="Subcontracted Item Shared RM", raw_materials=["Subcontracted SRM Item 1"]
	)
	sco = get_subcontracting_order_with_sa7_and(
		"Subcontracted Item Shared RM", "Subcontracted Service Item 8"
	)
	make_stock_entry(
		target="_Test Warehouse - _TC", item_code="Subcontracted SRM Item 1", qty=40, basic_rate=100
	)
	return sco


def get_subcontracting_order_with_sa7_and(fg_item, service_item):
	service_items = [
		{
			"warehouse": "_Test Warehouse - _TC",
			"item_code": "Subcontracted Service Item 7",
			"qty": 10,
			"rate": 100,
			"fg_item": "Subcontracted Item SA7",
			"fg_item_qty": 10,
		},
		{
			"warehouse": "_Test Warehouse - _TC",
			"item_code": service_item,
			"qty": 10,
			"rate": 100,
			"fg_item": fg_item,
			"fg_item_qty": 10,
		},
	]
	return get_subcontracting_order(service_items=service_items)


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


def make_subcontracted_purchase_order_from_material_request(material_request):
	from erpnext.stock.doctype.material_request.mapper import make_purchase_order

	po = make_purchase_order(material_request)
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

	return po


def make_subcontracted_variant():
	template = make_item(
		"Subcontracted Template Item",
		{
			"is_stock_item": 1,
			"is_sub_contracted_item": 1,
			"has_variants": 1,
			"attributes": [{"attribute": "Test Size"}],
		},
	)
	raw_material = make_item("Subcontracted Template RM Item", {"is_stock_item": 1})
	template_bom = make_bom(item=template.name, raw_materials=[raw_material.name])

	variant = create_variant(template.name, {"Test Size": "Small"})
	variant.is_sub_contracted_item = 1
	variant.insert()

	return variant, template_bom


def make_subcontracted_purchase_order(project):
	from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

	service_items = [
		{
			"warehouse": "_Test Warehouse - _TC",
			"item_code": "Subcontracted Service Item 7",
			"qty": 10,
			"rate": 100,
			"fg_item": "Subcontracted Item SA7",
			"fg_item_qty": 10,
		},
	]
	po = create_purchase_order(
		rm_items=service_items,
		is_subcontracted=1,
		supplier_warehouse="_Test Warehouse 1 - _TC",
		do_not_submit=1,
	)
	po.project = project
	for item in po.items:
		item.project = project
	po.save()
	po.submit()

	return po


def cancel_one_of_two_receipts(index):
	"""Receive 6 and then 4, cancel receipt `index`; return each reservation's consumption."""
	sco = make_order_with_two_batch_transfers()
	receipts = [make_receipt_of_qty(sco, qty) for qty in (6, 4)]
	receipts[index].cancel()
	return get_supplier_warehouse_consumption(sco)


def make_order_with_two_batch_transfers():
	"""Order of 10 with 6 and then 4 of one batch transferred, each reserved in the supplier warehouse."""
	sco = make_reserving_order_with_new_items(
		"Receipt Cancel",
		qty=10,
		rm_properties={"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "SCORC-.####"},
	)
	rm_items = get_rm_items(sco.supplied_items)
	itemwise_details = make_stock_in_entry(rm_items=rm_items)
	sco.submit()
	for qty in (6, 4):
		rm_items[0]["qty"] = qty
		make_stock_transfer_entry(sco_no=sco.name, rm_items=rm_items, itemwise_details=itemwise_details)

	return sco


def make_receipt_of_qty(sco, qty):
	receipt = make_subcontracting_receipt(sco.name)
	receipt.items[0].qty = qty
	return receipt.submit()


def get_supplier_warehouse_consumption(sco):
	reservations = frappe.get_all(
		"Stock Reservation Entry",
		filters={"voucher_no": sco.name, "docstatus": 1, "warehouse": sco.supplier_warehouse},
		fields=["reserved_qty", "consumed_qty"],
		order_by="creation",
		as_list=True,
	)
	return [tuple(reservation) for reservation in reservations]
