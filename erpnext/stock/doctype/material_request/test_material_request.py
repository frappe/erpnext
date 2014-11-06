# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, unittest
from frappe.utils import flt

class TestMaterialRequest(unittest.TestCase):
	def setUp(self):
		frappe.defaults.set_global_default("auto_accounting_for_stock", 0)

	def test_make_purchase_order(self):
		from erpnext.stock.doctype.material_request.material_request import make_purchase_order

		mr = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_purchase_order,
			mr.name)

		mr = frappe.get_doc("Material Request", mr.name)
		mr.submit()
		po = make_purchase_order(mr.name)

		self.assertEquals(po.doctype, "Purchase Order")
		self.assertEquals(len(po.get("po_details")), len(mr.get("indent_details")))

	def test_make_supplier_quotation(self):
		from erpnext.stock.doctype.material_request.material_request import make_supplier_quotation

		mr = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_supplier_quotation, mr.name)

		mr = frappe.get_doc("Material Request", mr.name)
		mr.submit()
		sq = make_supplier_quotation(mr.name)

		self.assertEquals(sq.doctype, "Supplier Quotation")
		self.assertEquals(len(sq.get("quotation_items")), len(mr.get("indent_details")))


	def test_make_stock_entry(self):
		from erpnext.stock.doctype.material_request.material_request import make_stock_entry

		mr = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_stock_entry,
			mr.name)

		mr = frappe.get_doc("Material Request", mr.name)
		mr.material_request_type = "Transfer"
		mr.submit()
		se = make_stock_entry(mr.name)

		self.assertEquals(se.doctype, "Stock Entry")
		self.assertEquals(len(se.get("mtn_details")), len(mr.get("indent_details")))

	def _insert_stock_entry(self, qty1, qty2):
		se = frappe.get_doc({
				"company": "_Test Company",
				"doctype": "Stock Entry",
				"posting_date": "2013-03-01",
				"posting_time": "00:00:00",
				"purpose": "Material Receipt",
				"fiscal_year": "_Test Fiscal Year 2013",
				"mtn_details": [
					{
						"conversion_factor": 1.0,
						"doctype": "Stock Entry Detail",
						"item_code": "_Test Item Home Desktop 100",
						"parentfield": "mtn_details",
						"incoming_rate": 100,
						"qty": qty1,
						"stock_uom": "_Test UOM 1",
						"transfer_qty": qty1,
						"uom": "_Test UOM 1",
						"t_warehouse": "_Test Warehouse 1 - _TC",
					},
					{
						"conversion_factor": 1.0,
						"doctype": "Stock Entry Detail",
						"item_code": "_Test Item Home Desktop 200",
						"parentfield": "mtn_details",
						"incoming_rate": 100,
						"qty": qty2,
						"stock_uom": "_Test UOM 1",
						"transfer_qty": qty2,
						"uom": "_Test UOM 1",
						"t_warehouse": "_Test Warehouse 1 - _TC",
					}
				]
			})
		se.insert()
		se.submit()

	def test_completed_qty_for_purchase(self):
		existing_requested_qty_item1 = self._get_requested_qty("_Test Item Home Desktop 100", "_Test Warehouse - _TC")
		existing_requested_qty_item2 = self._get_requested_qty("_Test Item Home Desktop 200", "_Test Warehouse - _TC")

		# submit material request of type Purchase
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.submit()

		# check if per complete is None
		self.assertEquals(mr.per_ordered, None)
		self.assertEquals(mr.get("indent_details")[0].ordered_qty, 0)
		self.assertEquals(mr.get("indent_details")[1].ordered_qty, 0)

		# map a purchase order
		from erpnext.stock.doctype.material_request.material_request import make_purchase_order
		po_doc = make_purchase_order(mr.name)
		po_doc.supplier = "_Test Supplier"
		po_doc.transaction_date = "2013-07-07"
		po_doc.get("po_details")[0].qty = 27.0
		po_doc.get("po_details")[1].qty = 1.5
		po_doc.get("po_details")[0].schedule_date = "2013-07-09"
		po_doc.get("po_details")[1].schedule_date = "2013-07-09"


		# check for stopped status of Material Request
		po = frappe.copy_doc(po_doc)
		po.insert()
		po.load_from_db()
		mr.update_status('Stopped')
		self.assertRaises(frappe.InvalidStatusError, po.submit)
		frappe.db.set(po, "docstatus", 1)
		self.assertRaises(frappe.InvalidStatusError, po.cancel)

		# resubmit and check for per complete
		mr.load_from_db()
		mr.update_status('Submitted')
		po = frappe.copy_doc(po_doc)
		po.insert()
		po.submit()

		# check if per complete is as expected
		mr.load_from_db()
		self.assertEquals(mr.per_ordered, 50)
		self.assertEquals(mr.get("indent_details")[0].ordered_qty, 27.0)
		self.assertEquals(mr.get("indent_details")[1].ordered_qty, 1.5)

		current_requested_qty_item1 = self._get_requested_qty("_Test Item Home Desktop 100", "_Test Warehouse - _TC")
		current_requested_qty_item2 = self._get_requested_qty("_Test Item Home Desktop 200", "_Test Warehouse - _TC")

		self.assertEquals(current_requested_qty_item1, existing_requested_qty_item1 + 27.0)
		self.assertEquals(current_requested_qty_item2, existing_requested_qty_item2 + 1.5)

		po.cancel()
		# check if per complete is as expected
		mr.load_from_db()
		self.assertEquals(mr.per_ordered, None)
		self.assertEquals(mr.get("indent_details")[0].ordered_qty, None)
		self.assertEquals(mr.get("indent_details")[1].ordered_qty, None)

		current_requested_qty_item1 = self._get_requested_qty("_Test Item Home Desktop 100", "_Test Warehouse - _TC")
		current_requested_qty_item2 = self._get_requested_qty("_Test Item Home Desktop 200", "_Test Warehouse - _TC")

		self.assertEquals(current_requested_qty_item1, existing_requested_qty_item1 + 54.0)
		self.assertEquals(current_requested_qty_item2, existing_requested_qty_item2 + 3.0)

	def test_completed_qty_for_transfer(self):
		existing_requested_qty_item1 = self._get_requested_qty("_Test Item Home Desktop 100", "_Test Warehouse - _TC")
		existing_requested_qty_item2 = self._get_requested_qty("_Test Item Home Desktop 200", "_Test Warehouse - _TC")

		# submit material request of type Purchase
		mr = frappe.copy_doc(test_records[0])
		mr.material_request_type = "Transfer"
		mr.insert()
		mr.submit()

		# check if per complete is None
		self.assertEquals(mr.per_ordered, None)
		self.assertEquals(mr.get("indent_details")[0].ordered_qty, 0)
		self.assertEquals(mr.get("indent_details")[1].ordered_qty, 0)

		current_requested_qty_item1 = self._get_requested_qty("_Test Item Home Desktop 100", "_Test Warehouse - _TC")
		current_requested_qty_item2 = self._get_requested_qty("_Test Item Home Desktop 200", "_Test Warehouse - _TC")

		self.assertEquals(current_requested_qty_item1, existing_requested_qty_item1 + 54.0)
		self.assertEquals(current_requested_qty_item2, existing_requested_qty_item2 + 3.0)

		from erpnext.stock.doctype.material_request.material_request import make_stock_entry

		# map a stock entry
		se_doc = make_stock_entry(mr.name)
		se_doc.update({
			"posting_date": "2013-03-01",
			"posting_time": "01:00",
			"fiscal_year": "_Test Fiscal Year 2013",
		})
		se_doc.get("mtn_details")[0].update({
			"qty": 27.0,
			"transfer_qty": 27.0,
			"s_warehouse": "_Test Warehouse 1 - _TC",
			"incoming_rate": 1.0
		})
		se_doc.get("mtn_details")[1].update({
			"qty": 1.5,
			"transfer_qty": 1.5,
			"s_warehouse": "_Test Warehouse 1 - _TC",
			"incoming_rate": 1.0
		})

		# make available the qty in _Test Warehouse 1 before transfer
		self._insert_stock_entry(27.0, 1.5)

		# check for stopped status of Material Request
		se = frappe.copy_doc(se_doc)
		se.insert()
		mr.update_status('Stopped')
		self.assertRaises(frappe.InvalidStatusError, se.submit)

		mr.update_status('Submitted')

		se.ignore_validate_update_after_submit = True
		se.submit()
		mr.update_status('Stopped')
		self.assertRaises(frappe.InvalidStatusError, se.cancel)

		mr.update_status('Submitted')
		se = frappe.copy_doc(se_doc)
		se.insert()
		se.submit()

		# check if per complete is as expected
		mr.load_from_db()
		self.assertEquals(mr.per_ordered, 50)
		self.assertEquals(mr.get("indent_details")[0].ordered_qty, 27.0)
		self.assertEquals(mr.get("indent_details")[1].ordered_qty, 1.5)

		current_requested_qty_item1 = self._get_requested_qty("_Test Item Home Desktop 100", "_Test Warehouse - _TC")
		current_requested_qty_item2 = self._get_requested_qty("_Test Item Home Desktop 200", "_Test Warehouse - _TC")

		self.assertEquals(current_requested_qty_item1, existing_requested_qty_item1 + 27.0)
		self.assertEquals(current_requested_qty_item2, existing_requested_qty_item2 + 1.5)

		# check if per complete is as expected for Stock Entry cancelled
		se.cancel()
		mr.load_from_db()
		self.assertEquals(mr.per_ordered, 0)
		self.assertEquals(mr.get("indent_details")[0].ordered_qty, 0)
		self.assertEquals(mr.get("indent_details")[1].ordered_qty, 0)

		current_requested_qty_item1 = self._get_requested_qty("_Test Item Home Desktop 100", "_Test Warehouse - _TC")
		current_requested_qty_item2 = self._get_requested_qty("_Test Item Home Desktop 200", "_Test Warehouse - _TC")

		self.assertEquals(current_requested_qty_item1, existing_requested_qty_item1 + 54.0)
		self.assertEquals(current_requested_qty_item2, existing_requested_qty_item2 + 3.0)

	def test_completed_qty_for_over_transfer(self):
		existing_requested_qty_item1 = self._get_requested_qty("_Test Item Home Desktop 100", "_Test Warehouse - _TC")
		existing_requested_qty_item2 = self._get_requested_qty("_Test Item Home Desktop 200", "_Test Warehouse - _TC")

		# submit material request of type Purchase
		mr = frappe.copy_doc(test_records[0])
		mr.material_request_type = "Transfer"
		mr.insert()
		mr.submit()

		# check if per complete is None
		self.assertEquals(mr.per_ordered, None)
		self.assertEquals(mr.get("indent_details")[0].ordered_qty, 0)
		self.assertEquals(mr.get("indent_details")[1].ordered_qty, 0)

		# map a stock entry
		from erpnext.stock.doctype.material_request.material_request import make_stock_entry

		se_doc = make_stock_entry(mr.name)
		se_doc.update({
			"posting_date": "2013-03-01",
			"posting_time": "00:00",
			"fiscal_year": "_Test Fiscal Year 2013",
		})
		se_doc.get("mtn_details")[0].update({
			"qty": 60.0,
			"transfer_qty": 60.0,
			"s_warehouse": "_Test Warehouse 1 - _TC",
			"incoming_rate": 1.0
		})
		se_doc.get("mtn_details")[1].update({
			"qty": 3.0,
			"transfer_qty": 3.0,
			"s_warehouse": "_Test Warehouse 1 - _TC",
			"incoming_rate": 1.0
		})

		# make available the qty in _Test Warehouse 1 before transfer
		self._insert_stock_entry(60.0, 3.0)

		# check for stopped status of Material Request
		se = frappe.copy_doc(se_doc)
		se.insert()
		mr.update_status('Stopped')
		self.assertRaises(frappe.InvalidStatusError, se.submit)
		self.assertRaises(frappe.InvalidStatusError, se.cancel)

		mr.update_status('Submitted')
		se = frappe.copy_doc(se_doc)
		se.insert()
		se.submit()

		# check if per complete is as expected
		mr.load_from_db()

		self.assertEquals(mr.per_ordered, 100)
		self.assertEquals(mr.get("indent_details")[0].ordered_qty, 60.0)
		self.assertEquals(mr.get("indent_details")[1].ordered_qty, 3.0)

		current_requested_qty_item1 = self._get_requested_qty("_Test Item Home Desktop 100", "_Test Warehouse - _TC")
		current_requested_qty_item2 = self._get_requested_qty("_Test Item Home Desktop 200", "_Test Warehouse - _TC")

		self.assertEquals(current_requested_qty_item1, existing_requested_qty_item1)
		self.assertEquals(current_requested_qty_item2, existing_requested_qty_item2)

		# check if per complete is as expected for Stock Entry cancelled
		se.cancel()
		mr.load_from_db()
		self.assertEquals(mr.per_ordered, 0)
		self.assertEquals(mr.get("indent_details")[0].ordered_qty, 0)
		self.assertEquals(mr.get("indent_details")[1].ordered_qty, 0)

		current_requested_qty_item1 = self._get_requested_qty("_Test Item Home Desktop 100", "_Test Warehouse - _TC")
		current_requested_qty_item2 = self._get_requested_qty("_Test Item Home Desktop 200", "_Test Warehouse - _TC")

		self.assertEquals(current_requested_qty_item1, existing_requested_qty_item1 + 54.0)
		self.assertEquals(current_requested_qty_item2, existing_requested_qty_item2 + 3.0)

	def test_incorrect_mapping_of_stock_entry(self):
		# submit material request of type Purchase
		mr = frappe.copy_doc(test_records[0])
		mr.material_request_type = "Transfer"
		mr.insert()
		mr.submit()

		# map a stock entry
		from erpnext.stock.doctype.material_request.material_request import make_stock_entry

		se_doc = make_stock_entry(mr.name)
		se_doc.update({
			"posting_date": "2013-03-01",
			"posting_time": "00:00",
			"fiscal_year": "_Test Fiscal Year 2013",
		})
		se_doc.get("mtn_details")[0].update({
			"qty": 60.0,
			"transfer_qty": 60.0,
			"s_warehouse": "_Test Warehouse - _TC",
			"t_warehouse": "_Test Warehouse 1 - _TC",
			"incoming_rate": 1.0
		})
		se_doc.get("mtn_details")[1].update({
			"qty": 3.0,
			"transfer_qty": 3.0,
			"s_warehouse": "_Test Warehouse 1 - _TC",
			"incoming_rate": 1.0
		})

		# check for stopped status of Material Request
		se = frappe.copy_doc(se_doc)
		self.assertRaises(frappe.MappingMismatchError, se.insert)

	def test_warehouse_company_validation(self):
		from erpnext.stock.utils import InvalidWarehouseCompany
		mr = frappe.copy_doc(test_records[0])
		mr.company = "_Test Company 1"
		self.assertRaises(InvalidWarehouseCompany, mr.insert)

	def _get_requested_qty(self, item_code, warehouse):
		return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "indented_qty"))


test_dependencies = ["Currency Exchange"]
test_records = frappe.get_test_records('Material Request')
