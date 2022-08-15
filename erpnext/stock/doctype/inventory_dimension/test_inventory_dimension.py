# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import (
	CanNotBeChildDoc,
	CanNotBeDefaultDimension,
	DoNotChangeError,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse


class TestInventoryDimension(FrappeTestCase):
	def setUp(self):
		prepare_test_data()

	def test_validate_inventory_dimension(self):
		# Can not be child doc
		inv_dim1 = create_inventory_dimension(
			reference_document="Stock Entry Detail",
			type_of_transaction="Outward",
			dimension_name="Stock Entry",
			apply_to_all_doctypes=0,
			istable=0,
			document_type="Stock Entry",
			do_not_save=True,
		)

		self.assertRaises(CanNotBeChildDoc, inv_dim1.insert)

		inv_dim1 = create_inventory_dimension(
			reference_document="Batch",
			type_of_transaction="Outward",
			dimension_name="Batch",
			apply_to_all_doctypes=0,
			document_type="Stock Entry Detail",
			do_not_save=True,
		)

		self.assertRaises(CanNotBeDefaultDimension, inv_dim1.insert)

	def test_inventory_dimension(self):
		warehouse = "Shelf Warehouse - _TC"
		item_code = "_Test Item"

		inv_dim1 = create_inventory_dimension(
			reference_document="Shelf",
			type_of_transaction="Outward",
			dimension_name="Shelf",
			apply_to_all_doctypes=0,
			document_type="Stock Entry Detail",
			condition="parent.purpose == 'Material Issue'",
		)

		create_inventory_dimension(
			reference_document="Shelf",
			type_of_transaction="Inward",
			dimension_name="To Shelf",
			apply_to_all_doctypes=0,
			document_type="Stock Entry Detail",
			condition="parent.purpose == 'Material Receipt'",
		)

		inward = make_stock_entry(
			item_code=item_code,
			target=warehouse,
			qty=5,
			basic_rate=10,
			do_not_save=True,
			purpose="Material Receipt",
		)

		inward.items[0].to_shelf = "Shelf 1"
		inward.save()
		inward.submit()
		inward.load_from_db()

		sle_data = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": inward.name}, ["shelf", "warehouse"], as_dict=1
		)

		self.assertEqual(inward.items[0].to_shelf, "Shelf 1")
		self.assertEqual(sle_data.warehouse, warehouse)
		self.assertEqual(sle_data.shelf, "Shelf 1")

		outward = make_stock_entry(
			item_code=item_code,
			source=warehouse,
			qty=3,
			basic_rate=10,
			do_not_save=True,
			purpose="Material Issue",
		)

		outward.items[0].shelf = "Shelf 1"
		outward.save()
		outward.submit()
		outward.load_from_db()

		sle_shelf = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": outward.name}, "shelf")
		self.assertEqual(sle_shelf, "Shelf 1")

		inv_dim1.load_from_db()
		inv_dim1.apply_to_all_doctypes = 1

		self.assertTrue(inv_dim1.has_stock_ledger())
		self.assertRaises(DoNotChangeError, inv_dim1.save)


def prepare_test_data():
	if not frappe.db.exists("DocType", "Shelf"):
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": "Shelf",
				"module": "Stock",
				"custom": 1,
				"naming_rule": "By fieldname",
				"autoname": "field:shelf_name",
				"fields": [{"label": "Shelf Name", "fieldname": "shelf_name", "fieldtype": "Data"}],
				"permissions": [
					{"role": "System Manager", "permlevel": 0, "read": 1, "write": 1, "create": 1, "delete": 1}
				],
			}
		).insert(ignore_permissions=True)

	for shelf in ["Shelf 1", "Shelf 2"]:
		if not frappe.db.exists("Shelf", shelf):
			frappe.get_doc({"doctype": "Shelf", "shelf_name": shelf}).insert(ignore_permissions=True)

	create_warehouse("Shelf Warehouse")


def create_inventory_dimension(**args):
	args = frappe._dict(args)

	if frappe.db.exists("Inventory Dimension", args.dimension_name):
		return frappe.get_doc("Inventory Dimension", args.dimension_name)

	doc = frappe.new_doc("Inventory Dimension")
	doc.update(args)

	if not args.do_not_save:
		doc.insert(ignore_permissions=True)

	return doc
