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

	def test_component_uom_resolved_by_global_conversion_is_allowed(self):
		# a UOM with only a global UOM Conversion Factor (Kg->Gram), not an item-level one,
		# is resolved by packing, so it must not be rejected
		suffix = frappe.generate_hash(length=8)
		child = make_item(
			f"_Test PB Global UOM Child {suffix}", {"is_stock_item": 1, "stock_uom": "Gram"}
		).name
		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": self.parent})
		doc.append("items", {"item_code": child, "qty": 1, "uom": "Kg"})
		doc.insert()  # must not raise
		self.assertTrue(doc.name)

	def test_bundle_cannot_reference_itself(self):
		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": self.parent})
		doc.append("items", {"item_code": self.parent, "qty": 1})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_duplicate_component_is_rejected(self):
		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": self.parent})
		doc.append("items", {"item_code": self.child, "qty": 2})
		doc.append("items", {"item_code": self.child, "qty": 3})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_merge_duplicate_items_patch_normalizes_to_stock_qty(self):
		from erpnext.patches.v16_0.merge_duplicate_product_bundle_items import (
			execute as merge_duplicate_items,
		)

		component = make_item(
			properties={"stock_uom": "Nos", "uoms": [{"uom": "Box", "conversion_factor": 12}]}
		).name
		bundle = frappe.get_doc(
			{"doctype": "Product Bundle", "new_item_code": make_item(properties={"is_stock_item": 0}).name}
		)
		bundle.append("items", {"item_code": component, "qty": 1})  # 1 Nos (stock UOM)
		bundle.insert()
		# inject a duplicate row in a different UOM (validation blocks this normally)
		frappe.get_doc(
			{
				"doctype": "Product Bundle Item",
				"parent": bundle.name,
				"parenttype": "Product Bundle",
				"parentfield": "items",
				"item_code": component,
				"qty": 1,
				"uom": "Box",  # 1 Box = 12 Nos
				"idx": 2,
			}
		).db_insert()

		merge_duplicate_items()

		rows = frappe.get_all(
			"Product Bundle Item",
			filters={"parent": bundle.name, "item_code": component},
			fields=["qty", "uom"],
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].qty, 13)  # 1 Nos + 1 Box (12 Nos), summed in stock units
		self.assertEqual(rows[0].uom, "Nos")

	def test_parent_used_as_component_cannot_become_a_bundle(self):
		# OUTER bundles INNER while INNER is still a plain item; turning INNER into its
		# own bundle afterwards would nest it under OUTER, so it must be rejected
		suffix = frappe.generate_hash(length=8)
		inner = make_item(f"_Test PB Nest Inner {suffix}", {"is_stock_item": 0, "is_sales_item": 1}).name
		outer = make_item(f"_Test PB Nest Outer {suffix}", {"is_stock_item": 0, "is_sales_item": 1}).name
		make_product_bundle(outer, [inner])

		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": inner})
		doc.append("items", {"item_code": self.child, "qty": 1})
		self.assertRaises(frappe.ValidationError, doc.insert)
