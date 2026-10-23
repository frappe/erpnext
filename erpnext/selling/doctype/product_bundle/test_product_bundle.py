# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.selling.doctype.product_bundle.product_bundle import (
	get_active_product_bundle,
	make_new_version,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


def make_product_bundle(parent, items, qty=None):
	"""Create (and submit) an active Product Bundle for ``parent``.

	Product Bundle is now submittable & versioned, so the active version is resolved
	by parent item code rather than by document name.
	"""
	if active := get_active_product_bundle(parent):
		return frappe.get_doc("Product Bundle", active)

	product_bundle = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": parent})

	for item in items:
		product_bundle.append("items", {"item_code": item, "qty": qty or 1})

	product_bundle.insert()
	product_bundle.submit()

	return product_bundle


class TestProductBundle(ERPNextTestSuite):
	def setUp(self):
		self.parent = make_item("_Test PB Parent", {"is_stock_item": 0, "is_sales_item": 1}).name
		make_item("_Test PB Child A", {"is_stock_item": 1})
		make_item("_Test PB Child B", {"is_stock_item": 1})

	def test_submit_makes_bundle_active_and_versioned(self):
		bundle = make_product_bundle(self.parent, ["_Test PB Child A"])
		self.assertEqual(bundle.docstatus, 1)
		self.assertEqual(bundle.is_active, 1)
		self.assertTrue(bundle.name.startswith("PB-"))
		self.assertEqual(get_active_product_bundle(self.parent), bundle.name)

	def test_new_version_deactivates_previous(self):
		v1 = make_product_bundle(self.parent, ["_Test PB Child A"])

		v2 = make_new_version(v1.name)
		v2.items[0].qty = 5
		v2.insert()
		v2.submit()

		self.assertNotEqual(v1.name, v2.name)
		self.assertEqual(get_active_product_bundle(self.parent), v2.name)
		self.assertEqual(frappe.db.get_value("Product Bundle", v1.name, "is_active"), 0)

	def test_reactivating_old_version_deactivates_current(self):
		v1 = make_product_bundle(self.parent, ["_Test PB Child A"])

		v2 = make_new_version(v1.name)
		v2.items[0].qty = 5
		v2.insert()
		v2.submit()
		self.assertEqual(get_active_product_bundle(self.parent), v2.name)

		# switch back to v1 by toggling is_active on the submitted doc (allow_on_submit)
		v1.reload()
		v1.is_active = 1
		v1.save()

		self.assertEqual(get_active_product_bundle(self.parent), v1.name)
		self.assertEqual(frappe.db.get_value("Product Bundle", v2.name, "is_active"), 0)

	def test_new_bundle_from_scratch_supersedes_existing(self):
		# An item that already has a bundle must remain selectable so a new version
		# can be created straight from the New Product Bundle form.
		from erpnext.selling.doctype.product_bundle.product_bundle import get_new_item_code

		v1 = make_product_bundle(self.parent, ["_Test PB Child A"])

		picker = [row[0] for row in get_new_item_code("Item", self.parent, "name", 0, 20, {})]
		self.assertIn(self.parent, picker)

		v2 = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": self.parent})
		v2.append("items", {"item_code": "_Test PB Child B", "qty": 1})
		v2.insert()
		v2.submit()

		self.assertNotEqual(v1.name, v2.name)
		self.assertEqual(get_active_product_bundle(self.parent), v2.name)
		self.assertEqual(frappe.db.get_value("Product Bundle", v1.name, "is_active"), 0)

	def test_cancel_clears_active(self):
		bundle = make_product_bundle(self.parent, ["_Test PB Child A"])
		bundle.cancel()
		self.assertEqual(frappe.db.get_value("Product Bundle", bundle.name, "is_active"), 0)
		self.assertIsNone(get_active_product_bundle(self.parent))

	def test_submitted_bundle_is_immutable(self):
		bundle = make_product_bundle(self.parent, ["_Test PB Child A"])
		bundle.items[0].qty = 99
		self.assertRaises(frappe.exceptions.UpdateAfterSubmitError, bundle.save)

	def test_disabled_bundle_is_not_resolved(self):
		bundle = make_product_bundle(self.parent, ["_Test PB Child A"])

		bundle.disabled = 1
		bundle.save()
		self.assertIsNone(get_active_product_bundle(self.parent))

		# disabling parks the version without ceding the active slot, so re-enabling
		# restores resolution without re-activation
		self.assertEqual(frappe.db.get_value("Product Bundle", bundle.name, "is_active"), 1)
		bundle.disabled = 0
		bundle.save()
		self.assertEqual(get_active_product_bundle(self.parent), bundle.name)

	def test_item_where_used_report_shows_disabled_flag(self):
		from erpnext.stock.report.item_where_used.item_where_used import execute

		bundle = make_product_bundle(self.parent, ["_Test PB Child A"])
		bundle.disabled = 1
		bundle.save()

		_, component_rows = execute({"item": "_Test PB Child A", "section": "Where Used"})
		rows = [r for r in component_rows if r.document_name == bundle.name]
		self.assertTrue(rows)
		self.assertEqual(rows[0].disabled, 1)
		self.assertEqual(rows[0].is_active, 1)
		self.assertEqual(rows[0].stock_quantity, rows[0].quantity)
		self.assertEqual(rows[0].stock_uom, rows[0].uom)

		_, parent_rows = execute({"item": self.parent, "section": "References"})
		rows = [r for r in parent_rows if r.document_name == bundle.name]
		self.assertTrue(rows)
		self.assertEqual(rows[0].disabled, 1)

	def test_item_where_used_report_hides_internal_and_empty_columns(self):
		from erpnext.stock.report.item_where_used.item_where_used import execute

		bundle = make_product_bundle(self.parent, ["_Test PB Child A"])

		columns, rows = execute({"item": "_Test PB Child A", "section": "Where Used"})
		fieldnames = [column["fieldname"] for column in columns]

		self.assertIn("stock_quantity", fieldnames)
		self.assertIn("stock_uom", fieldnames)
		self.assertNotIn("matched_field", fieldnames)
		self.assertNotIn("company", fieldnames)

		rows = [r for r in rows if r.document_name == bundle.name]
		self.assertTrue(rows)
		self.assertEqual(rows[0].stock_quantity, rows[0].quantity)
		self.assertEqual(rows[0].stock_uom, rows[0].uom)

	def test_item_where_used_report_hides_false_check_columns(self):
		from erpnext.stock.report.item_where_used.item_where_used import get_columns

		columns = get_columns([frappe._dict(stock_quantity=0, is_default=0)])
		fieldnames = [column["fieldname"] for column in columns]

		self.assertIn("stock_quantity", fieldnames)
		self.assertNotIn("is_default", fieldnames)

	def test_component_uom_must_be_convertible(self):
		child = make_item("_Test PB UOM Child", {"is_stock_item": 1, "stock_uom": "Nos"}).name
		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": self.parent})
		doc.append("items", {"item_code": child, "qty": 1, "uom": "Box"})  # no Box conversion on the item
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_component_uom_resolved_by_global_conversion_is_allowed(self):
		# a UOM with only a global UOM Conversion Factor (Kg->Gram), not an item-level one,
		# is resolved by packing, so it must not be rejected
		child = make_item("_Test PB Global UOM Child", {"is_stock_item": 1, "stock_uom": "Gram"}).name
		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": self.parent})
		doc.append("items", {"item_code": child, "qty": 1, "uom": "Kg"})
		doc.insert()  # must not raise
		self.assertTrue(doc.name)

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

	def test_child_cannot_be_active_bundle(self):
		make_product_bundle(self.parent, ["_Test PB Child A"])
		outer = make_item("_Test PB Outer", {"is_stock_item": 0, "is_sales_item": 1}).name

		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": outer})
		doc.append("items", {"item_code": self.parent, "qty": 1})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_duplicate_component_is_rejected(self):
		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": self.parent})
		doc.append("items", {"item_code": "_Test PB Child A", "qty": 2})
		doc.append("items", {"item_code": "_Test PB Child A", "qty": 3})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_bundle_cannot_reference_itself(self):
		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": self.parent})
		doc.append("items", {"item_code": self.parent, "qty": 1})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_parent_used_as_component_cannot_become_a_bundle(self):
		# OUTER bundles INNER while INNER is still a plain item; turning INNER into its
		# own bundle afterwards would nest it under OUTER, so it must be rejected
		inner = make_item("_Test PB Nest Inner", {"is_stock_item": 0, "is_sales_item": 1}).name
		outer = make_item("_Test PB Nest Outer", {"is_stock_item": 0, "is_sales_item": 1}).name
		make_product_bundle(outer, [inner])

		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": inner})
		doc.append("items", {"item_code": "_Test PB Child A", "qty": 1})
		self.assertRaises(frappe.ValidationError, doc.insert)
