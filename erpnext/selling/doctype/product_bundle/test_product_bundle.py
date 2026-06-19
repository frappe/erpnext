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

		_, parent_rows = execute({"item": self.parent, "section": "References"})
		rows = [r for r in parent_rows if r.document_name == bundle.name]
		self.assertTrue(rows)
		self.assertEqual(rows[0].disabled, 1)

	def test_child_cannot_be_active_bundle(self):
		make_product_bundle(self.parent, ["_Test PB Child A"])
		outer = make_item("_Test PB Outer", {"is_stock_item": 0, "is_sales_item": 1}).name

		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": outer})
		doc.append("items", {"item_code": self.parent, "qty": 1})
		self.assertRaises(frappe.ValidationError, doc.insert)
