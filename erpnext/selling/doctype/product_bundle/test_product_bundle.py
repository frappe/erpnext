# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.item.test_item import make_item

test_records = frappe.get_test_records("Product Bundle")


def make_product_bundle(parent, items, qty=None):
	if frappe.db.exists("Product Bundle", parent):
		return frappe.get_doc("Product Bundle", parent)

	product_bundle = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": parent})

	for item in items:
		product_bundle.append("items", {"item_code": item, "qty": qty or 1})

	product_bundle.insert()

	return product_bundle


class TestProductBundle(FrappeTestCase):
	def setUp(self):
		suffix = frappe.generate_hash(length=8)
		self.parent = make_item(f"_Test PB Parent {suffix}", {"is_stock_item": 0, "is_sales_item": 1}).name
		self.child = make_item(f"_Test PB Child {suffix}", {"is_stock_item": 1}).name

	def test_component_uom_must_be_convertible(self):
		suffix = frappe.generate_hash(length=8)
		child = make_item(f"_Test PB UOM Child {suffix}", {"is_stock_item": 1, "stock_uom": "Nos"}).name
		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": self.parent})
		doc.append("items", {"item_code": child, "qty": 1, "uom": "Box"})  # no Box conversion on the item
		self.assertRaises(frappe.ValidationError, doc.insert)
