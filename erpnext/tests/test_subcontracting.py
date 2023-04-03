import copy
import unittest
from collections import defaultdict

import frappe
from frappe.utils import cint

from erpnext.buying.doctype.purchase_order.purchase_order import (
	get_materials_from_supplier,
	make_purchase_invoice,
	make_purchase_receipt,
	make_rm_stock_entry,
)
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry


class TestSubcontracting(unittest.TestCase):
	def setUp(self):
		make_subcontract_items()
		make_raw_materials()
		make_bom_for_subcontracted_items()

	def test_po_with_bom(self):
		"""
		- Set backflush based on BOM
		- Create subcontracted PO for the item Subcontracted Item SA1 and add same item two times.
		- Transfer the components from Stores to Supplier warehouse with batch no and serial nos.
		- Create purchase receipt against the PO and check serial nos and batch no.
		"""

		set_backflush_based_on("BOM")
		item_code = "Subcontracted Item SA1"
		items = [
			{"warehouse": "_Test Warehouse - _TC", "item_code": item_code, "qty": 5, "rate": 100},
			{"warehouse": "_Test Warehouse - _TC", "item_code": item_code, "qty": 6, "rate": 100},
		]

		rm_items = [
			{"item_code": "Subcontracted SRM Item 1", "qty": 5},
			{"item_code": "Subcontracted SRM Item 2", "qty": 5},
			{"item_code": "Subcontracted SRM Item 3", "qty": 5},
			{"item_code": "Subcontracted SRM Item 1", "qty": 6},
			{"item_code": "Subcontracted SRM Item 2", "qty": 6},
			{"item_code": "Subcontracted SRM Item 3", "qty": 6},
		]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name if d.get("qty") == 5 else po.items[1].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_receipt(po.name)
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			transferred_detais = itemwise_details.get(key)

			for field in ["qty", "serial_no", "batch_no"]:
				if value.get(field):
					transfer, consumed = (transferred_detais.get(field), value.get(field))
					if field == "serial_no":
						transfer, consumed = (sorted(transfer), sorted(consumed))

					self.assertEqual(transfer, consumed)

	def test_po_with_material_transfer(self):
		"""
		- Set backflush based on Material Transfer
		- Create subcontracted PO for the item Subcontracted Item SA1 and Subcontracted Item SA5.
		- Transfer the components from Stores to Supplier warehouse with batch no and serial nos.
		- Transfer extra item Subcontracted SRM Item 4 for the subcontract item Subcontracted Item SA5.
		- Create partial purchase receipt against the PO and check serial nos and batch no.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Item SA1",
				"qty": 5,
				"rate": 100,
			},
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Item SA5",
				"qty": 6,
				"rate": 100,
			},
		]

		rm_items = [
			{"item_code": "Subcontracted SRM Item 1", "qty": 5, "main_item_code": "Subcontracted Item SA1"},
			{"item_code": "Subcontracted SRM Item 2", "qty": 5, "main_item_code": "Subcontracted Item SA1"},
			{"item_code": "Subcontracted SRM Item 3", "qty": 5, "main_item_code": "Subcontracted Item SA1"},
			{"item_code": "Subcontracted SRM Item 5", "qty": 6, "main_item_code": "Subcontracted Item SA5"},
			{"item_code": "Subcontracted SRM Item 4", "qty": 6, "main_item_code": "Subcontracted Item SA5"},
		]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name if d.get("qty") == 5 else po.items[1].name

		make_stock_transfer_entry(
			po_no=po.name, rm_items=rm_items, itemwise_details=copy.deepcopy(itemwise_details)
		)

		pr1 = make_purchase_receipt(po.name)
		pr1.remove(pr1.items[1])
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			transferred_detais = itemwise_details.get(key)

			for field in ["qty", "serial_no", "batch_no"]:
				if value.get(field):
					self.assertEqual(value.get(field), transferred_detais.get(field))

		pr2 = make_purchase_receipt(po.name)
		pr2.submit()

		for key, value in get_supplied_items(pr2).items():
			transferred_detais = itemwise_details.get(key)

			for field in ["qty", "serial_no", "batch_no"]:
				if value.get(field):
					self.assertEqual(value.get(field), transferred_detais.get(field))

	def test_subcontract_with_same_components_different_fg(self):
		"""
		- Set backflush based on Material Transfer
		- Create subcontracted PO for the item Subcontracted Item SA2 and Subcontracted Item SA3.
		- Transfer the components from Stores to Supplier warehouse with serial nos.
		- Transfer extra qty of components for the item Subcontracted Item SA2.
		- Create partial purchase receipt against the PO and check serial nos and batch no.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Item SA2",
				"qty": 5,
				"rate": 100,
			},
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Item SA3",
				"qty": 6,
				"rate": 100,
			},
		]

		rm_items = [
			{"item_code": "Subcontracted SRM Item 2", "qty": 6, "main_item_code": "Subcontracted Item SA2"},
			{"item_code": "Subcontracted SRM Item 2", "qty": 6, "main_item_code": "Subcontracted Item SA3"},
		]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name if d.get("qty") == 5 else po.items[1].name

		make_stock_transfer_entry(
			po_no=po.name, rm_items=rm_items, itemwise_details=copy.deepcopy(itemwise_details)
		)

		pr1 = make_purchase_receipt(po.name)
		pr1.items[0].qty = 3
		pr1.remove(pr1.items[1])
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			transferred_detais = itemwise_details.get(key)
			self.assertEqual(value.qty, 4)
			self.assertEqual(sorted(value.serial_no), sorted(transferred_detais.get("serial_no")[0:4]))

		pr2 = make_purchase_receipt(po.name)
		pr2.items[0].qty = 2
		pr2.remove(pr2.items[1])
		pr2.submit()

		for key, value in get_supplied_items(pr2).items():
			transferred_detais = itemwise_details.get(key)

			self.assertEqual(value.qty, 2)
			self.assertEqual(sorted(value.serial_no), sorted(transferred_detais.get("serial_no")[4:6]))

		pr3 = make_purchase_receipt(po.name)
		pr3.submit()
		for key, value in get_supplied_items(pr3).items():
			transferred_detais = itemwise_details.get(key)

			self.assertEqual(value.qty, 6)
			self.assertEqual(sorted(value.serial_no), sorted(transferred_detais.get("serial_no")[6:12]))

	def test_return_non_consumed_materials(self):
		"""
		- Set backflush based on Material Transfer
		- Create subcontracted PO for the item Subcontracted Item SA2.
		- Transfer the components from Stores to Supplier warehouse with serial nos.
		- Transfer extra qty of component for the subcontracted item Subcontracted Item SA2.
		- Create purchase receipt for full qty against the PO and change the qty of raw material.
		- After that return the non consumed material back to the store from supplier's warehouse.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Item SA2",
				"qty": 5,
				"rate": 100,
			}
		]
		rm_items = [
			{"item_code": "Subcontracted SRM Item 2", "qty": 6, "main_item_code": "Subcontracted Item SA2"}
		]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name, rm_items=rm_items, itemwise_details=copy.deepcopy(itemwise_details)
		)

		pr1 = make_purchase_receipt(po.name)
		pr1.save()
		pr1.supplied_items[0].consumed_qty = 5
		pr1.supplied_items[0].serial_no = "\n".join(
			sorted(itemwise_details.get("Subcontracted SRM Item 2").get("serial_no")[0:5])
		)
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			transferred_detais = itemwise_details.get(key)
			self.assertEqual(value.qty, 5)
			self.assertEqual(sorted(value.serial_no), sorted(transferred_detais.get("serial_no")[0:5]))

		po.load_from_db()
		self.assertEqual(po.supplied_items[0].consumed_qty, 5)
		doc = get_materials_from_supplier(po.name, [d.name for d in po.supplied_items])
		self.assertEqual(doc.items[0].qty, 1)
		self.assertEqual(doc.items[0].s_warehouse, "_Test Warehouse 1 - _TC")
		self.assertEqual(doc.items[0].t_warehouse, "_Test Warehouse - _TC")
		self.assertEqual(
			get_serial_nos(doc.items[0].serial_no),
			itemwise_details.get(doc.items[0].item_code)["serial_no"][5:6],
		)

	def test_item_with_batch_based_on_bom(self):
		"""
		- Set backflush based on BOM
		- Create subcontracted PO for the item Subcontracted Item SA4 (has batch no).
		- Transfer the components from Stores to Supplier warehouse with batch no and serial nos.
		- Transfer the components in multiple batches.
		- Create the 3 purchase receipt against the PO and split Subcontracted Items into two batches.
		- Keep the qty as 2 for Subcontracted Item in the purchase receipt.
		"""

		set_backflush_based_on("BOM")
		item_code = "Subcontracted Item SA4"
		items = [{"warehouse": "_Test Warehouse - _TC", "item_code": item_code, "qty": 10, "rate": 100}]

		rm_items = [
			{"item_code": "Subcontracted SRM Item 1", "qty": 10},
			{"item_code": "Subcontracted SRM Item 2", "qty": 10},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 1},
		]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_receipt(po.name)
		pr1.items[0].qty = 2
		add_second_row_in_pr(pr1)
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			self.assertEqual(value.qty, 4)

		pr1 = make_purchase_receipt(po.name)
		pr1.items[0].qty = 2
		add_second_row_in_pr(pr1)
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			self.assertEqual(value.qty, 4)

		pr1 = make_purchase_receipt(po.name)
		pr1.items[0].qty = 2
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			self.assertEqual(value.qty, 2)

	def test_item_with_batch_based_on_material_transfer(self):
		"""
		- Set backflush based on Material Transferred for Subcontract
		- Create subcontracted PO for the item Subcontracted Item SA4 (has batch no).
		- Transfer the components from Stores to Supplier warehouse with batch no and serial nos.
		- Transfer the components in multiple batches with extra 2 qty for the batched item.
		- Create the 3 purchase receipt against the PO and split Subcontracted Items into two batches.
		- Keep the qty as 2 for Subcontracted Item in the purchase receipt.
		- In the first purchase receipt the batched raw materials will be consumed 2 extra qty.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		item_code = "Subcontracted Item SA4"
		items = [{"warehouse": "_Test Warehouse - _TC", "item_code": item_code, "qty": 10, "rate": 100}]

		rm_items = [
			{"item_code": "Subcontracted SRM Item 1", "qty": 10},
			{"item_code": "Subcontracted SRM Item 2", "qty": 10},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
		]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_receipt(po.name)
		pr1.items[0].qty = 2
		add_second_row_in_pr(pr1)
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			qty = 4 if key != "Subcontracted SRM Item 3" else 6
			self.assertEqual(value.qty, qty)

		pr1 = make_purchase_receipt(po.name)
		pr1.items[0].qty = 2
		add_second_row_in_pr(pr1)
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			self.assertEqual(value.qty, 4)

		pr1 = make_purchase_receipt(po.name)
		pr1.items[0].qty = 2
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			self.assertEqual(value.qty, 2)

	def test_partial_transfer_serial_no_components_based_on_material_transfer(self):
		"""
		- Set backflush based on Material Transferred for Subcontract
		- Create subcontracted PO for the item Subcontracted Item SA2.
		- Transfer the partial components from Stores to Supplier warehouse with serial nos.
		- Create partial purchase receipt against the PO and change the qty manually.
		- Transfer the remaining components from Stores to Supplier warehouse with serial nos.
		- Create purchase receipt for remaining qty against the PO and change the qty manually.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		item_code = "Subcontracted Item SA2"
		items = [{"warehouse": "_Test Warehouse - _TC", "item_code": item_code, "qty": 10, "rate": 100}]

		rm_items = [{"item_code": "Subcontracted SRM Item 2", "qty": 5}]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_receipt(po.name)
		pr1.items[0].qty = 5
		pr1.save()

		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, 3)
			self.assertEqual(sorted(value.serial_no), sorted(details.serial_no[0:3]))

		pr1.load_from_db()
		pr1.supplied_items[0].consumed_qty = 5
		pr1.supplied_items[0].serial_no = "\n".join(
			itemwise_details[pr1.supplied_items[0].rm_item_code]["serial_no"]
		)
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(sorted(value.serial_no), sorted(details.serial_no))

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_receipt(po.name)
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(sorted(value.serial_no), sorted(details.serial_no))

	def test_incorrect_serial_no_components_based_on_material_transfer(self):
		"""
		- Set backflush based on Material Transferred for Subcontract
		- Create subcontracted PO for the item Subcontracted Item SA2.
		- Transfer the serialized componenets to the supplier.
		- Create purchase receipt and change the serial no which is not transferred.
		- System should throw the error and not allowed to save the purchase receipt.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		item_code = "Subcontracted Item SA2"
		items = [{"warehouse": "_Test Warehouse - _TC", "item_code": item_code, "qty": 10, "rate": 100}]

		rm_items = [{"item_code": "Subcontracted SRM Item 2", "qty": 10}]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_receipt(po.name)
		pr1.save()
		pr1.supplied_items[0].serial_no = "ABCD"
		self.assertRaises(frappe.ValidationError, pr1.save)
		pr1.delete()

	def test_partial_transfer_batch_based_on_material_transfer(self):
		"""
		- Set backflush based on Material Transferred for Subcontract
		- Create subcontracted PO for the item Subcontracted Item SA6.
		- Transfer the partial components from Stores to Supplier warehouse with batch.
		- Create partial purchase receipt against the PO and change the qty manually.
		- Transfer the remaining components from Stores to Supplier warehouse with batch.
		- Create purchase receipt for remaining qty against the PO and change the qty manually.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		item_code = "Subcontracted Item SA6"
		items = [{"warehouse": "_Test Warehouse - _TC", "item_code": item_code, "qty": 10, "rate": 100}]

		rm_items = [{"item_code": "Subcontracted SRM Item 3", "qty": 5}]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_receipt(po.name)
		pr1.items[0].qty = 5
		pr1.save()

		transferred_batch_no = ""
		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, 3)
			transferred_batch_no = details.batch_no
			self.assertEqual(value.batch_no, details.batch_no)

		pr1.load_from_db()
		pr1.supplied_items[0].consumed_qty = 5
		pr1.supplied_items[0].batch_no = list(transferred_batch_no.keys())[0]
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(value.batch_no, details.batch_no)

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_receipt(po.name)
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(value.batch_no, details.batch_no)

	def test_item_with_batch_based_on_material_transfer_for_purchase_invoice(self):
		"""
		- Set backflush based on Material Transferred for Subcontract
		- Create subcontracted PO for the item Subcontracted Item SA4 (has batch no).
		- Transfer the components from Stores to Supplier warehouse with batch no and serial nos.
		- Transfer the components in multiple batches with extra 2 qty for the batched item.
		- Create the 3 purchase receipt against the PO and split Subcontracted Items into two batches.
		- Keep the qty as 2 for Subcontracted Item in the purchase receipt.
		- In the first purchase receipt the batched raw materials will be consumed 2 extra qty.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		item_code = "Subcontracted Item SA4"
		items = [{"warehouse": "_Test Warehouse - _TC", "item_code": item_code, "qty": 10, "rate": 100}]

		rm_items = [
			{"item_code": "Subcontracted SRM Item 1", "qty": 10},
			{"item_code": "Subcontracted SRM Item 2", "qty": 10},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
		]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_invoice(po.name)
		pr1.update_stock = 1
		pr1.items[0].qty = 2
		pr1.items[0].expense_account = "Stock Adjustment - _TC"
		add_second_row_in_pr(pr1)
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			qty = 4 if key != "Subcontracted SRM Item 3" else 6
			self.assertEqual(value.qty, qty)

		pr1 = make_purchase_invoice(po.name)
		pr1.update_stock = 1
		pr1.items[0].expense_account = "Stock Adjustment - _TC"
		pr1.items[0].qty = 2
		add_second_row_in_pr(pr1)
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			self.assertEqual(value.qty, 4)

		pr1 = make_purchase_invoice(po.name)
		pr1.update_stock = 1
		pr1.items[0].qty = 2
		pr1.items[0].expense_account = "Stock Adjustment - _TC"
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			self.assertEqual(value.qty, 2)

	def test_partial_transfer_serial_no_components_based_on_material_transfer_for_purchase_invoice(
		self,
	):
		"""
		- Set backflush based on Material Transferred for Subcontract
		- Create subcontracted PO for the item Subcontracted Item SA2.
		- Transfer the partial components from Stores to Supplier warehouse with serial nos.
		- Create partial purchase receipt against the PO and change the qty manually.
		- Transfer the remaining components from Stores to Supplier warehouse with serial nos.
		- Create purchase receipt for remaining qty against the PO and change the qty manually.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		item_code = "Subcontracted Item SA2"
		items = [{"warehouse": "_Test Warehouse - _TC", "item_code": item_code, "qty": 10, "rate": 100}]

		rm_items = [{"item_code": "Subcontracted SRM Item 2", "qty": 5}]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_invoice(po.name)
		pr1.update_stock = 1
		pr1.items[0].qty = 5
		pr1.items[0].expense_account = "Stock Adjustment - _TC"
		pr1.save()

		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, 3)
			self.assertEqual(sorted(value.serial_no), sorted(details.serial_no[0:3]))

		pr1.load_from_db()
		pr1.supplied_items[0].consumed_qty = 5
		pr1.supplied_items[0].serial_no = "\n".join(
			itemwise_details[pr1.supplied_items[0].rm_item_code]["serial_no"]
		)
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(sorted(value.serial_no), sorted(details.serial_no))

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_invoice(po.name)
		pr1.update_stock = 1
		pr1.items[0].expense_account = "Stock Adjustment - _TC"
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(sorted(value.serial_no), sorted(details.serial_no))

	def test_partial_transfer_batch_based_on_material_transfer_for_purchase_invoice(self):
		"""
		- Set backflush based on Material Transferred for Subcontract
		- Create subcontracted PO for the item Subcontracted Item SA6.
		- Transfer the partial components from Stores to Supplier warehouse with batch.
		- Create partial purchase receipt against the PO and change the qty manually.
		- Transfer the remaining components from Stores to Supplier warehouse with batch.
		- Create purchase receipt for remaining qty against the PO and change the qty manually.
		"""

		set_backflush_based_on("Material Transferred for Subcontract")
		item_code = "Subcontracted Item SA6"
		items = [{"warehouse": "_Test Warehouse - _TC", "item_code": item_code, "qty": 10, "rate": 100}]

		rm_items = [{"item_code": "Subcontracted SRM Item 3", "qty": 5}]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_invoice(po.name)
		pr1.update_stock = 1
		pr1.items[0].qty = 5
		pr1.items[0].expense_account = "Stock Adjustment - _TC"
		pr1.save()

		transferred_batch_no = ""
		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, 3)
			transferred_batch_no = details.batch_no
			self.assertEqual(value.batch_no, details.batch_no)

		pr1.load_from_db()
		pr1.supplied_items[0].consumed_qty = 5
		pr1.supplied_items[0].batch_no = list(transferred_batch_no.keys())[0]
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(value.batch_no, details.batch_no)

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_invoice(po.name)
		pr1.update_stock = 1
		pr1.items[0].expense_account = "Stock Adjustment - _TC"
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			details = itemwise_details.get(key)
			self.assertEqual(value.qty, details.qty)
			self.assertEqual(value.batch_no, details.batch_no)

	def test_item_with_batch_based_on_bom_for_purchase_invoice(self):
		"""
		- Set backflush based on BOM
		- Create subcontracted PO for the item Subcontracted Item SA4 (has batch no).
		- Transfer the components from Stores to Supplier warehouse with batch no and serial nos.
		- Transfer the components in multiple batches.
		- Create the 3 purchase receipt against the PO and split Subcontracted Items into two batches.
		- Keep the qty as 2 for Subcontracted Item in the purchase receipt.
		"""

		set_backflush_based_on("BOM")
		item_code = "Subcontracted Item SA4"
		items = [{"warehouse": "_Test Warehouse - _TC", "item_code": item_code, "qty": 10, "rate": 100}]

		rm_items = [
			{"item_code": "Subcontracted SRM Item 1", "qty": 10},
			{"item_code": "Subcontracted SRM Item 2", "qty": 10},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 3},
			{"item_code": "Subcontracted SRM Item 3", "qty": 1},
		]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name

		make_stock_transfer_entry(
			po_no=po.name,
			main_item_code=item_code,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		pr1 = make_purchase_invoice(po.name)
		pr1.update_stock = 1
		pr1.items[0].qty = 2
		pr1.items[0].expense_account = "Stock Adjustment - _TC"
		add_second_row_in_pr(pr1)
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			self.assertEqual(value.qty, 4)

		pr1 = make_purchase_invoice(po.name)
		pr1.update_stock = 1
		pr1.items[0].qty = 2
		pr1.items[0].expense_account = "Stock Adjustment - _TC"
		add_second_row_in_pr(pr1)
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			self.assertEqual(value.qty, 4)

		pr1 = make_purchase_invoice(po.name)
		pr1.update_stock = 1
		pr1.items[0].qty = 2
		pr1.items[0].expense_account = "Stock Adjustment - _TC"
		pr1.save()
		pr1.submit()

		for key, value in get_supplied_items(pr1).items():
			self.assertEqual(value.qty, 2)

	def test_po_supplied_qty(self):
		"""
		Check if 'Supplied Qty' in PO's Supplied Items table is reset on submit/cancel.
		"""
		set_backflush_based_on("Material Transferred for Subcontract")
		items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Item SA1",
				"qty": 5,
				"rate": 100,
			},
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Item SA5",
				"qty": 6,
				"rate": 100,
			},
		]

		rm_items = [
			{"item_code": "Subcontracted SRM Item 1", "qty": 5, "main_item_code": "Subcontracted Item SA1"},
			{"item_code": "Subcontracted SRM Item 2", "qty": 5, "main_item_code": "Subcontracted Item SA1"},
			{"item_code": "Subcontracted SRM Item 3", "qty": 5, "main_item_code": "Subcontracted Item SA1"},
			{"item_code": "Subcontracted SRM Item 5", "qty": 6, "main_item_code": "Subcontracted Item SA5"},
			{"item_code": "Subcontracted SRM Item 4", "qty": 6, "main_item_code": "Subcontracted Item SA5"},
		]

		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		po = create_purchase_order(
			rm_items=items, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)

		for d in rm_items:
			d["po_detail"] = po.items[0].name if d.get("qty") == 5 else po.items[1].name

		se = make_stock_transfer_entry(
			po_no=po.name, rm_items=rm_items, itemwise_details=copy.deepcopy(itemwise_details)
		)

		po.reload()
		for row in po.get("supplied_items"):
			self.assertIn(row.supplied_qty, [5.0, 6.0])

		se.cancel()
		po.reload()
		for row in po.get("supplied_items"):
			self.assertEqual(row.supplied_qty, 0.0)


def add_second_row_in_pr(pr):
	item_dict = {}
	for column in [
		"item_code",
		"item_name",
		"qty",
		"uom",
		"warehouse",
		"stock_uom",
		"purchase_order",
		"purchase_order_item",
		"conversion_factor",
		"rate",
		"expense_account",
		"po_detail",
	]:
		item_dict[column] = pr.items[0].get(column)

	pr.append("items", item_dict)
	pr.set_missing_values()


def get_supplied_items(pr_doc):
	supplied_items = {}
	for row in pr_doc.get("supplied_items"):
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
			"warehouse": row.warehuose or "_Test Warehouse - _TC",
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

	ste_dict = make_rm_stock_entry(args.po_no, items)
	doc = frappe.get_doc(ste_dict)
	doc.insert()
	doc.submit()

	return doc


def make_subcontract_items():
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
	}

	for item_code, raw_materials in boms.items():
		if not frappe.db.exists("BOM", {"item": item_code}):
			make_bom(item=item_code, raw_materials=raw_materials, rate=100)


def set_backflush_based_on(based_on):
	frappe.db.set_value(
		"Buying Settings", None, "backflush_raw_materials_of_subcontract_based_on", based_on
	)
