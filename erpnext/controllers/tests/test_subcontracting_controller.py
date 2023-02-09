# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import copy
from collections import defaultdict

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.controllers.subcontracting_controller import (
	get_materials_from_supplier,
	make_rm_stock_entry,
)
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
	make_subcontracting_receipt,
)


class TestSubcontractingController(FrappeTestCase):
	def setUp(self):
		make_subcontracted_items()
		make_raw_materials()
		make_service_items()
		make_bom_for_subcontracted_items()

	def test_remove_empty_rows(self):
		sco = get_subcontracting_order()
		len_before = len(sco.service_items)
		sco.service_items[0].item_code = None
		sco.remove_empty_rows()
		self.assertEqual((len_before - 1), len(sco.service_items))

	def test_set_missing_values_in_additional_costs(self):
		sco = get_subcontracting_order(do_not_submit=1)

		rate_without_additional_cost = sco.items[0].rate
		amount_without_additional_cost = sco.items[0].amount

		additional_amount = 120
		sco.append(
			"additional_costs",
			{
				"expense_account": "Cost of Goods Sold - _TC",
				"description": "Test",
				"amount": additional_amount,
			},
		)
		sco.save()

		additional_cost_per_qty = additional_amount / sco.items[0].qty

		self.assertEqual(sco.items[0].additional_cost_per_qty, additional_cost_per_qty)
		self.assertEqual(rate_without_additional_cost + additional_cost_per_qty, sco.items[0].rate)
		self.assertEqual(amount_without_additional_cost + additional_amount, sco.items[0].amount)

		sco.additional_costs = []
		sco.save()

		self.assertEqual(sco.items[0].additional_cost_per_qty, 0)
		self.assertEqual(rate_without_additional_cost, sco.items[0].rate)
		self.assertEqual(amount_without_additional_cost, sco.items[0].amount)

	def test_create_raw_materials_supplied(self):
		sco = get_subcontracting_order()
		sco.supplied_items = None
		sco.create_raw_materials_supplied()
		self.assertIsNotNone(sco.supplied_items)

	def test_sco_with_bom(self):
		"""
		- Set backflush based on BOM.
		- Create SCO for the item Subcontracted Item SA1 and add same item two times.
		- Transfer the components from Stores to Supplier warehouse with batch no and serial nos.
		- Create SCR against the SCO and check serial nos and batch no.
		"""

		set_backflush_based_on("BOM")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 5,
				"rate": 100,
				"fg_item": "Subcontracted Item SA1",
				"fg_item_qty": 5,
			},
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 6,
				"rate": 100,
				"fg_item": "Subcontracted Item SA1",
				"fg_item_qty": 6,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name if item.get("qty") == 5 else sco.items[1].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		scr = make_subcontracting_receipt(sco.name)
		scr.save()
		scr.submit()

		for key, value in get_supplied_items(scr).items():
			transferred_detais = itemwise_details.get(key)

			for field in ["qty", "serial_no", "batch_no"]:
				if value.get(field):
					transfer, consumed = (transferred_detais.get(field), value.get(field))
					if field == "serial_no":
						transfer, consumed = (sorted(transfer), sorted(consumed))

					self.assertEqual(transfer, consumed)

	def test_sco_with_material_transfer(self):
		"""
		- Set backflush based on Material Transfer.
		- Create SCO for the item Subcontracted Item SA1 and Subcontracted Item SA5.
		- Transfer the components from Stores to Supplier warehouse with batch no and serial nos.
		- Transfer extra item Subcontracted SRM Item 4 for the subcontract item Subcontracted Item SA5.
		- Create partial SCR against the SCO and check serial nos and batch no.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 5,
				"rate": 100,
				"fg_item": "Subcontracted Item SA1",
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
		rm_items.append(
			{
				"main_item_code": "Subcontracted Item SA5",
				"item_code": "Subcontracted SRM Item 4",
				"qty": 6,
			}
		)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name if item.get("qty") == 5 else sco.items[1].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr1 = make_subcontracting_receipt(sco.name)
		scr1.remove(scr1.items[1])
		scr1.save()
		scr1.submit()

		for key, value in get_supplied_items(scr1).items():
			transferred_detais = itemwise_details.get(key)

			for field in ["qty", "serial_no", "batch_no"]:
				if value.get(field):
					self.assertEqual(value.get(field), transferred_detais.get(field))

		scr2 = make_subcontracting_receipt(sco.name)
		scr2.save()
		scr2.submit()

		for key, value in get_supplied_items(scr2).items():
			transferred_detais = itemwise_details.get(key)

			for field in ["qty", "serial_no", "batch_no"]:
				if value.get(field):
					self.assertEqual(value.get(field), transferred_detais.get(field))

	def test_subcontracting_with_same_components_different_fg(self):
		"""
		- Set backflush based on Material Transfer.
		- Create SCO for the item Subcontracted Item SA2 and Subcontracted Item SA3.
		- Transfer the components from Stores to Supplier warehouse with serial nos.
		- Transfer extra qty of components for the item Subcontracted Item SA2.
		- Create partial SCR against the SCO and check serial nos.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
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
				"item_code": "Subcontracted Service Item 3",
				"qty": 6,
				"rate": 100,
				"fg_item": "Subcontracted Item SA3",
				"fg_item_qty": 6,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		rm_items[0]["qty"] += 1
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name if item.get("qty") == 5 else sco.items[1].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr1 = make_subcontracting_receipt(sco.name)
		scr1.items[0].qty = 3
		scr1.remove(scr1.items[1])
		scr1.save()
		scr1.submit()

		for key, value in get_supplied_items(scr1).items():
			transferred_detais = itemwise_details.get(key)

			self.assertEqual(value.qty, 4)
			self.assertEqual(sorted(value.serial_no), sorted(transferred_detais.get("serial_no")[0:4]))

		scr2 = make_subcontracting_receipt(sco.name)
		scr2.items[0].qty = 2
		scr2.remove(scr2.items[1])
		scr2.save()
		scr2.submit()

		for key, value in get_supplied_items(scr2).items():
			transferred_detais = itemwise_details.get(key)

			self.assertEqual(value.qty, 2)
			self.assertEqual(sorted(value.serial_no), sorted(transferred_detais.get("serial_no")[4:6]))

		scr3 = make_subcontracting_receipt(sco.name)
		scr3.save()
		scr3.submit()

		for key, value in get_supplied_items(scr3).items():
			transferred_detais = itemwise_details.get(key)

			self.assertEqual(value.qty, 6)
			self.assertEqual(sorted(value.serial_no), sorted(transferred_detais.get("serial_no")[6:12]))

	def test_return_non_consumed_materials(self):
		"""
		- Set backflush based on Material Transfer.
		- Create SCO for item Subcontracted Item SA2.
		- Transfer the components from Stores to Supplier warehouse with serial nos.
		- Transfer extra qty of component for the subcontracted item Subcontracted Item SA2.
		- Create SCR for full qty against the SCO and change the qty of raw material.
		- After that return the non consumed material back to the store from supplier's warehouse.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 2",
				"qty": 5,
				"rate": 100,
				"fg_item": "Subcontracted Item SA2",
				"fg_item_qty": 5,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		rm_items[0]["qty"] += 1
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr1 = make_subcontracting_receipt(sco.name)
		scr1.save()
		scr1.supplied_items[0].consumed_qty = 5
		scr1.supplied_items[0].serial_no = "\n".join(
			sorted(itemwise_details.get("Subcontracted SRM Item 2").get("serial_no")[0:5])
		)
		scr1.submit()

		for key, value in get_supplied_items(scr1).items():
			transferred_detais = itemwise_details.get(key)
			self.assertEqual(value.qty, 5)
			self.assertEqual(sorted(value.serial_no), sorted(transferred_detais.get("serial_no")[0:5]))

		sco.load_from_db()
		self.assertEqual(sco.supplied_items[0].consumed_qty, 5)
		doc = get_materials_from_supplier(sco.name, [d.name for d in sco.supplied_items])
		self.assertEqual(doc.items[0].qty, 1)
		self.assertEqual(doc.items[0].s_warehouse, "_Test Warehouse 1 - _TC")
		self.assertEqual(doc.items[0].t_warehouse, "_Test Warehouse - _TC")
		self.assertEqual(
			get_serial_nos(doc.items[0].serial_no),
			itemwise_details.get(doc.items[0].item_code)["serial_no"][5:6],
		)

	def test_item_with_batch_based_on_bom(self):
		"""
		- Set backflush based on BOM.
		- Create SCO for item Subcontracted Item SA4 (has batch no).
		- Transfer the components from Stores to Supplier warehouse with batch no and serial nos.
		- Transfer the components in multiple batches.
		- Create the 3 SCR against the SCO and split Subcontracted Items into two batches.
		- Keep the qty as 2 for Subcontracted Item in the SCR.
		"""

		set_backflush_based_on("BOM")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 4",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA4",
				"fg_item_qty": 10,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = [
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 1",
				"qty": 10.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 2",
				"qty": 10.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 3",
				"qty": 3.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 3",
				"qty": 3.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 3",
				"qty": 3.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 3",
				"qty": 1.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
		]
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr1 = make_subcontracting_receipt(sco.name)
		scr1.items[0].qty = 2
		add_second_row_in_scr(scr1)
		scr1.flags.ignore_mandatory = True
		scr1.save()
		scr1.set_missing_values()
		scr1.submit()

		for key, value in get_supplied_items(scr1).items():
			self.assertEqual(value.qty, 4)

		scr2 = make_subcontracting_receipt(sco.name)
		scr2.items[0].qty = 2
		add_second_row_in_scr(scr2)
		scr2.flags.ignore_mandatory = True
		scr2.save()
		scr2.set_missing_values()
		scr2.submit()

		for key, value in get_supplied_items(scr2).items():
			self.assertEqual(value.qty, 4)

		scr3 = make_subcontracting_receipt(sco.name)
		scr3.items[0].qty = 2
		scr3.flags.ignore_mandatory = True
		scr3.save()
		scr3.set_missing_values()
		scr3.submit()

		for key, value in get_supplied_items(scr3).items():
			self.assertEqual(value.qty, 2)

	def test_item_with_batch_based_on_material_transfer(self):
		"""
		- Set backflush based on Material Transferred for Subcontract.
		- Create SCO for item Subcontracted Item SA4 (has batch no).
		- Transfer the components from Stores to Supplier warehouse with batch no and serial nos.
		- Transfer the components in multiple batches with extra 2 qty for the batched item.
		- Create the 3 SCR against the SCO and split Subcontracted Items into two batches.
		- Keep the qty as 2 for Subcontracted Item in the SCR.
		- In the first SCR the batched raw materials will be consumed 2 extra qty.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 4",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA4",
				"fg_item_qty": 10,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = [
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 1",
				"qty": 10.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 2",
				"qty": 10.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 3",
				"qty": 3.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 3",
				"qty": 3.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 3",
				"qty": 3.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
			{
				"main_item_code": "Subcontracted Item SA4",
				"item_code": "Subcontracted SRM Item 3",
				"qty": 3.0,
				"rate": 100.0,
				"stock_uom": "Nos",
				"warehouse": "_Test Warehouse - _TC",
			},
		]
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr1 = make_subcontracting_receipt(sco.name)
		scr1.items[0].qty = 2
		add_second_row_in_scr(scr1)
		scr1.flags.ignore_mandatory = True
		scr1.save()
		scr1.set_missing_values()
		scr1.submit()

		for key, value in get_supplied_items(scr1).items():
			qty = 4 if key != "Subcontracted SRM Item 3" else 6
			self.assertEqual(value.qty, qty)

		scr2 = make_subcontracting_receipt(sco.name)
		scr2.items[0].qty = 2
		add_second_row_in_scr(scr2)
		scr2.flags.ignore_mandatory = True
		scr2.save()
		scr2.set_missing_values()
		scr2.submit()

		for key, value in get_supplied_items(scr2).items():
			self.assertEqual(value.qty, 4)

		scr3 = make_subcontracting_receipt(sco.name)
		scr3.items[0].qty = 2
		scr3.flags.ignore_mandatory = True
		scr3.save()
		scr3.set_missing_values()
		scr3.submit()

		for key, value in get_supplied_items(scr3).items():
			self.assertEqual(value.qty, 1)

	def test_partial_transfer_serial_no_components_based_on_material_transfer(self):
		"""
		- Set backflush based on Material Transferred for Subcontract.
		- Create SCO for the item Subcontracted Item SA2.
		- Transfer the partial components from Stores to Supplier warehouse with serial nos.
		- Create partial SCR against the SCO and change the qty manually.
		- Transfer the remaining components from Stores to Supplier warehouse with serial nos.
		- Create SCR for remaining qty against the SCO and change the qty manually.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 2",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA2",
				"fg_item_qty": 10,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		rm_items[0]["qty"] = 5
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr1 = make_subcontracting_receipt(sco.name)
		scr1.items[0].qty = 5
		scr1.flags.ignore_mandatory = True
		scr1.save()
		scr1.set_missing_values()

		for key, value in get_supplied_items(scr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, 3)
			self.assertEqual(sorted(value.serial_no), sorted(details.serial_no[0:3]))

		scr1.load_from_db()
		scr1.supplied_items[0].consumed_qty = 5
		scr1.supplied_items[0].serial_no = "\n".join(
			itemwise_details[scr1.supplied_items[0].rm_item_code]["serial_no"]
		)
		scr1.save()
		scr1.submit()

		for key, value in get_supplied_items(scr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(sorted(value.serial_no), sorted(details.serial_no))

		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr2 = make_subcontracting_receipt(sco.name)
		scr2.submit()

		for key, value in get_supplied_items(scr2).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(sorted(value.serial_no), sorted(details.serial_no))

	def test_incorrect_serial_no_components_based_on_material_transfer(self):
		"""
		- Set backflush based on Material Transferred for Subcontract.
		- Create SCO for the item Subcontracted Item SA2.
		- Transfer the serialized componenets to the supplier.
		- Create SCR and change the serial no which is not transferred.
		- System should throw the error and not allowed to save the SCR.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 2",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA2",
				"fg_item_qty": 10,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr1 = make_subcontracting_receipt(sco.name)
		scr1.save()
		scr1.supplied_items[0].serial_no = "ABCD"
		self.assertRaises(frappe.ValidationError, scr1.save)
		scr1.delete()

	def test_partial_transfer_batch_based_on_material_transfer(self):
		"""
		- Set backflush based on Material Transferred for Subcontract.
		- Create SCO for the item Subcontracted Item SA6.
		- Transfer the partial components from Stores to Supplier warehouse with batch.
		- Create partial SCR against the SCO and change the qty manually.
		- Transfer the remaining components from Stores to Supplier warehouse with batch.
		- Create SCR for remaining qty against the SCO and change the qty manually.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 6",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA6",
				"fg_item_qty": 10,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		rm_items[0]["qty"] = 5
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr1 = make_subcontracting_receipt(sco.name)
		scr1.items[0].qty = 5
		scr1.save()

		transferred_batch_no = ""
		for key, value in get_supplied_items(scr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, 3)
			transferred_batch_no = details.batch_no
			self.assertEqual(value.batch_no, details.batch_no)

		scr1.load_from_db()
		scr1.supplied_items[0].consumed_qty = 5
		scr1.supplied_items[0].batch_no = list(transferred_batch_no.keys())[0]
		scr1.save()
		scr1.submit()

		for key, value in get_supplied_items(scr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(value.batch_no, details.batch_no)

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		scr1 = make_subcontracting_receipt(sco.name)
		scr1.submit()

		for key, value in get_supplied_items(scr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(value.batch_no, details.batch_no)

	def test_sco_supplied_qty(self):
		"""
		Check if 'Supplied Qty' in SCO's Supplied Items table is reset on submit/cancel.
		"""
		set_backflush_based_on("Material Transferred for Subcontract")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 5,
				"rate": 100,
				"fg_item": "Subcontracted Item SA1",
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
		rm_items = [
			{"item_code": "Subcontracted SRM Item 1", "qty": 5, "main_item_code": "Subcontracted Item SA1"},
			{"item_code": "Subcontracted SRM Item 2", "qty": 5, "main_item_code": "Subcontracted Item SA1"},
			{"item_code": "Subcontracted SRM Item 3", "qty": 5, "main_item_code": "Subcontracted Item SA1"},
			{"item_code": "Subcontracted SRM Item 5", "qty": 6, "main_item_code": "Subcontracted Item SA5"},
			{"item_code": "Subcontracted SRM Item 4", "qty": 6, "main_item_code": "Subcontracted Item SA5"},
		]
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name if item.get("qty") == 5 else sco.items[1].name

		se = make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		sco.reload()
		for item in sco.get("supplied_items"):
			self.assertIn(item.supplied_qty, [5.0, 6.0])

		se.cancel()
		sco.reload()
		for item in sco.get("supplied_items"):
			self.assertEqual(item.supplied_qty, 0.0)


def add_second_row_in_scr(scr):
	item_dict = {}
	for column in [
		"item_code",
		"item_name",
		"qty",
		"uom",
		"bom",
		"warehouse",
		"stock_uom",
		"subcontracting_order",
		"subcontracting_order_finished_good_item",
		"conversion_factor",
		"rate",
		"expense_account",
		"sco_rm_detail",
	]:
		item_dict[column] = scr.items[0].get(column)

	scr.append("items", item_dict)


def get_supplied_items(scr_doc):
	supplied_items = {}
	for row in scr_doc.get("supplied_items"):
		if row.rm_item_code not in supplied_items:
			supplied_items.setdefault(
				row.rm_item_code, frappe._dict({"qty": 0, "serial_no": [], "batch_no": defaultdict(float)})
			)

		details = supplied_items[row.rm_item_code]
		update_item_details(row, details)

	return supplied_items


def make_stock_in_entry(**args):
	args = frappe._dict(args)

	items = {}
	for row in args.rm_items:
		row = frappe._dict(row)

		doc = make_stock_entry(
			target=row.warehouse or "_Test Warehouse - _TC",
			item_code=row.item_code,
			qty=row.qty or 1,
			basic_rate=row.rate or 100,
		)

		if row.item_code not in items:
			items.setdefault(
				row.item_code, frappe._dict({"qty": 0, "serial_no": [], "batch_no": defaultdict(float)})
			)

		child_row = doc.items[0]
		details = items[child_row.item_code]
		update_item_details(child_row, details)

	return items


def update_item_details(child_row, details):
	details.qty += (
		child_row.get("qty")
		if child_row.doctype == "Stock Entry Detail"
		else child_row.get("consumed_qty")
	)

	if child_row.serial_no:
		details.serial_no.extend(get_serial_nos(child_row.serial_no))

	if child_row.batch_no:
		details.batch_no[child_row.batch_no] += child_row.get("qty") or child_row.get("consumed_qty")


def make_stock_transfer_entry(**args):
	args = frappe._dict(args)

	items = []
	for row in args.rm_items:
		row = frappe._dict(row)

		item = {
			"item_code": row.main_item_code or args.main_item_code,
			"rm_item_code": row.item_code,
			"qty": row.qty or 1,
			"item_name": row.item_code,
			"rate": row.rate or 100,
			"stock_uom": row.stock_uom or "Nos",
			"warehouse": row.warehouse or "_Test Warehouse - _TC",
		}

		item_details = args.itemwise_details.get(row.item_code)

		if item_details and item_details.serial_no:
			serial_nos = item_details.serial_no[0 : cint(row.qty)]
			item["serial_no"] = "\n".join(serial_nos)
			item_details.serial_no = list(set(item_details.serial_no) - set(serial_nos))

		if item_details and item_details.batch_no:
			for batch_no, batch_qty in item_details.batch_no.items():
				if batch_qty >= row.qty:
					item["batch_no"] = batch_no
					item_details.batch_no[batch_no] -= row.qty
					break

		items.append(item)

	ste_dict = make_rm_stock_entry(args.sco_no, items)
	doc = frappe.get_doc(ste_dict)
	doc.insert()
	doc.submit()

	return doc


def make_subcontracted_items():
	sub_contracted_items = {
		"Subcontracted Item SA1": {},
		"Subcontracted Item SA2": {},
		"Subcontracted Item SA3": {},
		"Subcontracted Item SA4": {
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "SBAT.####",
		},
		"Subcontracted Item SA5": {},
		"Subcontracted Item SA6": {},
		"Subcontracted Item SA7": {},
	}

	for item, properties in sub_contracted_items.items():
		if not frappe.db.exists("Item", item):
			properties.update({"is_stock_item": 1, "is_sub_contracted_item": 1})
			make_item(item, properties)


def make_raw_materials():
	raw_materials = {
		"Subcontracted SRM Item 1": {},
		"Subcontracted SRM Item 2": {"has_serial_no": 1, "serial_no_series": "SRI.####"},
		"Subcontracted SRM Item 3": {
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "BAT.####",
		},
		"Subcontracted SRM Item 4": {"has_serial_no": 1, "serial_no_series": "SRII.####"},
		"Subcontracted SRM Item 5": {"has_serial_no": 1, "serial_no_series": "SRII.####"},
	}

	for item, properties in raw_materials.items():
		if not frappe.db.exists("Item", item):
			properties.update({"is_stock_item": 1})
			make_item(item, properties)


def make_service_item(item, properties={}):
	if not frappe.db.exists("Item", item):
		properties.update({"is_stock_item": 0})
		make_item(item, properties)


def make_service_items():
	service_items = {
		"Subcontracted Service Item 1": {},
		"Subcontracted Service Item 2": {},
		"Subcontracted Service Item 3": {},
		"Subcontracted Service Item 4": {},
		"Subcontracted Service Item 5": {},
		"Subcontracted Service Item 6": {},
		"Subcontracted Service Item 7": {},
	}

	for item, properties in service_items.items():
		make_service_item(item, properties)


def make_bom_for_subcontracted_items():
	boms = {
		"Subcontracted Item SA1": [
			"Subcontracted SRM Item 1",
			"Subcontracted SRM Item 2",
			"Subcontracted SRM Item 3",
		],
		"Subcontracted Item SA2": ["Subcontracted SRM Item 2"],
		"Subcontracted Item SA3": ["Subcontracted SRM Item 2"],
		"Subcontracted Item SA4": [
			"Subcontracted SRM Item 1",
			"Subcontracted SRM Item 2",
			"Subcontracted SRM Item 3",
		],
		"Subcontracted Item SA5": ["Subcontracted SRM Item 5"],
		"Subcontracted Item SA6": ["Subcontracted SRM Item 3"],
		"Subcontracted Item SA7": ["Subcontracted SRM Item 1"],
	}

	for item_code, raw_materials in boms.items():
		if not frappe.db.exists("BOM", {"item": item_code}):
			make_bom(item=item_code, raw_materials=raw_materials, rate=100)


def set_backflush_based_on(based_on):
	frappe.db.set_value(
		"Buying Settings", None, "backflush_raw_materials_of_subcontract_based_on", based_on
	)


def get_subcontracting_order(**args):
	from erpnext.subcontracting.doctype.subcontracting_order.test_subcontracting_order import (
		create_subcontracting_order,
	)

	args = frappe._dict(args)

	if args.get("po_name"):
		po = frappe.get_doc("Purchase Order", args.get("po_name"))

		if po.is_subcontracted:
			return create_subcontracting_order(po_name=po.name, **args)

	if not args.service_items:
		service_items = [
			{
				"warehouse": args.warehouse or "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 7",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA7",
				"fg_item_qty": 10,
			},
		]
	else:
		service_items = args.service_items

	po = create_purchase_order(
		rm_items=service_items,
		is_subcontracted=1,
		supplier_warehouse=args.supplier_warehouse or "_Test Warehouse 1 - _TC",
		company=args.company,
	)

	return create_subcontracting_order(po_name=po.name, **args)


def get_rm_items(supplied_items):
	rm_items = []

	for item in supplied_items:
		rm_items.append(
			{
				"main_item_code": item.main_item_code,
				"item_code": item.rm_item_code,
				"qty": item.required_qty,
				"rate": item.rate,
				"stock_uom": item.stock_uom,
				"warehouse": item.reserve_warehouse,
			}
		)

	return rm_items


def make_subcontracted_item(**args):
	from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

	args = frappe._dict(args)

	if not frappe.db.exists("Item", args.item_code):
		make_item(
			args.item_code,
			{
				"is_stock_item": 1,
				"is_sub_contracted_item": 1,
				"has_batch_no": args.get("has_batch_no") or 0,
			},
		)

	if not args.raw_materials:
		if not frappe.db.exists("Item", "Test Extra Item 1"):
			make_item(
				"Test Extra Item 1",
				{
					"is_stock_item": 1,
				},
			)

		if not frappe.db.exists("Item", "Test Extra Item 2"):
			make_item(
				"Test Extra Item 2",
				{
					"is_stock_item": 1,
				},
			)

		args.raw_materials = ["_Test FG Item", "Test Extra Item 1"]

	if not frappe.db.get_value("BOM", {"item": args.item_code}, "name"):
		make_bom(item=args.item_code, raw_materials=args.get("raw_materials"))
