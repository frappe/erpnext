# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe
import frappe.defaults
from frappe.utils import flt

class TestPurchaseOrder(unittest.TestCase):
	def test_make_purchase_receipt(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		po = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_purchase_receipt,
			po.name)

		po = frappe.get_doc("Purchase Order", po.name)
		po.submit()

		pr = make_purchase_receipt(po.name)
		pr.supplier_warehouse = "_Test Warehouse 1 - _TC"
		pr.posting_date = "2013-05-12"
		self.assertEquals(pr.doctype, "Purchase Receipt")
		self.assertEquals(len(pr.get("purchase_receipt_details")), len(test_records[0]["po_details"]))

		pr.naming_series = "_T-Purchase Receipt-"
		frappe.get_doc(pr).insert()

	def test_ordered_qty(self):
		existing_ordered_qty = self._get_ordered_qty("_Test Item", "_Test Warehouse - _TC")
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		po = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_purchase_receipt,
			po.name)

		po = frappe.get_doc("Purchase Order", po.name)
		po.is_subcontracted = "No"
		po.get("po_details")[0].item_code = "_Test Item"
		po.submit()

		self.assertEquals(self._get_ordered_qty("_Test Item", "_Test Warehouse - _TC"), existing_ordered_qty + 10)

		pr = make_purchase_receipt(po.name)

		self.assertEquals(pr.doctype, "Purchase Receipt")
		self.assertEquals(len(pr.get("purchase_receipt_details", [])), len(test_records[0]["po_details"]))
		pr.posting_date = "2013-05-12"
		pr.naming_series = "_T-Purchase Receipt-"
		pr.purchase_receipt_details[0].qty = 4.0
		pr.insert()
		pr.submit()

		po.load_from_db()
		self.assertEquals(po.get("po_details")[0].received_qty, 4)
		self.assertEquals(self._get_ordered_qty("_Test Item", "_Test Warehouse - _TC"), existing_ordered_qty + 6)

		frappe.db.set_value('Item', '_Test Item', 'tolerance', 50)

		pr1 = make_purchase_receipt(po.name)
		pr1.naming_series = "_T-Purchase Receipt-"
		pr1.posting_date = "2013-05-12"
		pr1.get("purchase_receipt_details")[0].qty = 8
		pr1.insert()
		pr1.submit()

		po.load_from_db()
		self.assertEquals(po.get("po_details")[0].received_qty, 12)
		self.assertEquals(self._get_ordered_qty("_Test Item", "_Test Warehouse - _TC"), existing_ordered_qty)

		pr1.load_from_db()
		pr1.cancel()

		po.load_from_db()
		self.assertEquals(po.get("po_details")[0].received_qty, 4)
		self.assertEquals(self._get_ordered_qty("_Test Item", "_Test Warehouse - _TC"), existing_ordered_qty + 6)

	def test_make_purchase_invoice(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice

		po = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_purchase_invoice,
			po.name)

		po = frappe.get_doc("Purchase Order", po.name)
		po.submit()
		pi = make_purchase_invoice(po.name)

		self.assertEquals(pi.doctype, "Purchase Invoice")
		self.assertEquals(len(pi.get("entries", [])), len(test_records[0]["po_details"]))
		pi.posting_date = "2013-05-12"
		pi.bill_no = "NA"
		frappe.get_doc(pi).insert()

	def test_subcontracting(self):
		po = frappe.copy_doc(test_records[0])
		po.insert()
		self.assertEquals(len(po.get("po_raw_material_details")), 2)

	def test_warehouse_company_validation(self):
		from erpnext.stock.utils import InvalidWarehouseCompany
		po = frappe.copy_doc(test_records[0])
		po.company = "_Test Company 1"
		po.conversion_rate = 0.0167
		self.assertRaises(InvalidWarehouseCompany, po.insert)

	def test_uom_integer_validation(self):
		from erpnext.utilities.transaction_base import UOMMustBeIntegerError
		po = frappe.copy_doc(test_records[0])
		po.get("po_details")[0].qty = 3.4
		self.assertRaises(UOMMustBeIntegerError, po.insert)

	def test_recurring_order(self):
		from erpnext.controllers.tests.test_recurring_document import test_recurring_document
		test_recurring_document(self, test_records)

	def _get_ordered_qty(self, item_code, warehouse):
		return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "ordered_qty"))


test_dependencies = ["BOM", "Item Price"]

test_records = frappe.get_test_records('Purchase Order')
