# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


def make_product_bundle(parent, items, qty=None):
	if frappe.db.exists("Product Bundle", parent):
		return frappe.get_doc("Product Bundle", parent)

	product_bundle = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": parent})

	for item in items:
		product_bundle.append("items", {"item_code": item, "qty": qty or 1})

	product_bundle.insert()

	return product_bundle


class TestProductBundle(ERPNextTestSuite):
	def setUp(self):
		suffix = frappe.generate_hash(length=8)
		self.parent = make_item(f"_Test PB Parent {suffix}", {"is_stock_item": 0, "is_sales_item": 1}).name
		self.child = make_item(f"_Test PB Child {suffix}", {"is_stock_item": 1}).name

	def test_item_where_used_report_shows_disabled_flag(self):
		from erpnext.stock.report.item_where_used.item_where_used import execute

		bundle = make_product_bundle(self.parent, [self.child])
		bundle.disabled = 1
		bundle.save()

		_, component_rows = execute({"item": self.child, "section": "Where Used"})
		rows = [r for r in component_rows if r.document_name == bundle.name]
		self.assertTrue(rows)
		self.assertEqual(rows[0].disabled, 1)
		self.assertEqual(rows[0].is_active, 0)
		self.assertEqual(rows[0].stock_quantity, rows[0].quantity)
		self.assertEqual(rows[0].stock_uom, rows[0].uom)

		_, parent_rows = execute({"item": self.parent, "section": "References"})
		rows = [r for r in parent_rows if r.document_name == bundle.name]
		self.assertTrue(rows)
		self.assertEqual(rows[0].disabled, 1)

	def test_item_where_used_report_hides_internal_and_empty_columns(self):
		from erpnext.stock.report.item_where_used.item_where_used import execute

		bundle = make_product_bundle(self.parent, [self.child])

		columns, rows = execute({"item": self.child, "section": "Where Used"})
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

	def test_child_cannot_be_active_bundle(self):
		make_product_bundle(self.parent, [self.child])
		outer = make_item(
			f"_Test PB Outer {frappe.generate_hash(length=8)}", {"is_stock_item": 0, "is_sales_item": 1}
		).name

		doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": outer})
		doc.append("items", {"item_code": self.parent, "qty": 1})
		self.assertRaises(frappe.ValidationError, doc.insert)
