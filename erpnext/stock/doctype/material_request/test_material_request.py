# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt


import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, today

from erpnext.controllers.accounts_controller import InvalidQtyError
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.material_request.material_request import (
	create_pick_list,
	make_in_transit_stock_entry,
	make_purchase_order,
	make_request_for_quotation,
	make_stock_entry,
	make_supplier_quotation,
	raise_work_orders,
)
from erpnext.stock.doctype.stock_entry.stock_entry import make_stock_in_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse


class TestMaterialRequest(FrappeTestCase):
	def test_material_request_qty(self):
		mr = frappe.copy_doc(test_records[0])
		mr.items[0].qty = 0
		with self.assertRaises(InvalidQtyError):
			mr.insert()

		# No error with qty=1
		mr.items[0].qty = 1
		mr.save()
		self.assertEqual(mr.items[0].qty, 1)

	def test_make_purchase_order(self):
		mr = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_purchase_order, mr.name)

		mr = frappe.get_doc("Material Request", mr.name)
		mr.submit()
		po = make_purchase_order(mr.name)

		self.assertEqual(po.doctype, "Purchase Order")
		self.assertEqual(len(po.get("items")), len(mr.get("items")))

	def test_make_request_for_quotation_skips_ordered_items(self):
		mr = frappe.copy_doc(test_records[0]).insert()
		mr = frappe.get_doc("Material Request", mr.name)
		mr.submit()

		# fully order the first item, leave the second pending
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.schedule_date = today()
		po.items = [po.items[0]]
		po.items[0].schedule_date = today()
		po.insert()
		po.submit()

		rfq = make_request_for_quotation(mr.name)

		self.assertEqual(len(rfq.get("items")), 1)
		self.assertEqual(rfq.items[0].material_request_item, mr.items[1].name)
		self.assertEqual(rfq.items[0].qty, mr.items[1].qty)

	def test_make_supplier_quotation(self):
		mr = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_supplier_quotation, mr.name)

		mr = frappe.get_doc("Material Request", mr.name)
		mr.submit()
		sq = make_supplier_quotation(mr.name)

		self.assertEqual(sq.doctype, "Supplier Quotation")
		self.assertEqual(len(sq.get("items")), len(mr.get("items")))

	def test_make_stock_entry(self):
		mr = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_stock_entry, mr.name)

		mr = frappe.get_doc("Material Request", mr.name)
		mr.material_request_type = "Material Transfer"
		mr.submit()
		se = make_stock_entry(mr.name)

		self.assertEqual(se.stock_entry_type, "Material Transfer")
		self.assertEqual(se.purpose, "Material Transfer")
		self.assertEqual(se.doctype, "Stock Entry")
		self.assertEqual(len(se.get("items")), len(mr.get("items")))

	def test_partial_make_stock_entry(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry as _make_stock_entry

		mr = frappe.copy_doc(test_records[0]).insert()

		source_wh = create_warehouse(
			warehouse_name="_Test Source Warehouse",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)

		mr = frappe.get_doc("Material Request", mr.name)
		mr.material_request_type = "Material Transfer"

		for row in mr.items:
			_make_stock_entry(
				item_code=row.item_code,
				qty=10,
				to_warehouse=source_wh,
				company="_Test Company",
				rate=100,
			)

			row.from_warehouse = source_wh
			row.qty = 10

		mr.save()
		mr.submit()

		se = make_stock_entry(mr.name)
		se.get("items")[0].qty = 5
		se.insert()
		se.submit()

		mr.reload()
		self.assertEqual(mr.status, "Partially Received")

	def test_in_transit_make_stock_entry(self):
		mr = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_stock_entry, mr.name)

		mr = frappe.get_doc("Material Request", mr.name)
		mr.material_request_type = "Material Transfer"
		mr.submit()

		in_transit_warehouse = get_in_transit_warehouse(mr.company)
		se = make_in_transit_stock_entry(mr.name, in_transit_warehouse)

		self.assertEqual(se.stock_entry_type, "Material Transfer")
		self.assertEqual(se.purpose, "Material Transfer")
		self.assertEqual(se.doctype, "Stock Entry")
		for row in se.get("items"):
			self.assertEqual(row.t_warehouse, in_transit_warehouse)

	def _insert_stock_entry(self, qty1, qty2, warehouse=None):
		se = frappe.get_doc(
			{
				"company": "_Test Company",
				"doctype": "Stock Entry",
				"posting_date": "2013-03-01",
				"posting_time": "00:00:00",
				"purpose": "Material Receipt",
				"items": [
					{
						"conversion_factor": 1.0,
						"doctype": "Stock Entry Detail",
						"item_code": "_Test Item Home Desktop 100",
						"parentfield": "items",
						"basic_rate": 100,
						"qty": qty1,
						"stock_uom": "_Test UOM 1",
						"transfer_qty": qty1,
						"uom": "_Test UOM 1",
						"t_warehouse": warehouse or "_Test Warehouse 1 - _TC",
						"cost_center": "_Test Cost Center - _TC",
					},
					{
						"conversion_factor": 1.0,
						"doctype": "Stock Entry Detail",
						"item_code": "_Test Item Home Desktop 200",
						"parentfield": "items",
						"basic_rate": 100,
						"qty": qty2,
						"stock_uom": "_Test UOM 1",
						"transfer_qty": qty2,
						"uom": "_Test UOM 1",
						"t_warehouse": warehouse or "_Test Warehouse 1 - _TC",
						"cost_center": "_Test Cost Center - _TC",
					},
				],
			}
		)

		se.set_stock_entry_type()
		se.insert()
		se.submit()

	def test_cannot_stop_cancelled_material_request(self):
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.submit()

		mr.load_from_db()
		mr.cancel()
		self.assertRaises(frappe.ValidationError, mr.update_status, "Stopped")

	def test_mr_changes_from_stopped_to_pending_after_reopen(self):
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.submit()
		self.assertEqual("Pending", mr.status)

		mr.update_status("Stopped")
		self.assertEqual("Stopped", mr.status)

		mr.update_status("Submitted")
		self.assertEqual("Pending", mr.status)

	def test_cannot_submit_cancelled_mr(self):
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.submit()
		mr.load_from_db()
		mr.cancel()
		self.assertRaises(frappe.ValidationError, mr.submit)

	def test_mr_changes_from_pending_to_cancelled_after_cancel(self):
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.submit()
		mr.cancel()
		self.assertEqual("Cancelled", mr.status)

	def test_cannot_change_cancelled_mr(self):
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.submit()
		mr.load_from_db()
		mr.cancel()

		self.assertRaises(frappe.InvalidStatusError, mr.update_status, "Draft")
		self.assertRaises(frappe.InvalidStatusError, mr.update_status, "Stopped")
		self.assertRaises(frappe.InvalidStatusError, mr.update_status, "Ordered")
		self.assertRaises(frappe.InvalidStatusError, mr.update_status, "Issued")
		self.assertRaises(frappe.InvalidStatusError, mr.update_status, "Transferred")
		self.assertRaises(frappe.InvalidStatusError, mr.update_status, "Pending")

	def test_cannot_submit_deleted_material_request(self):
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.delete()

		self.assertRaises(frappe.ValidationError, mr.submit)

	def test_cannot_delete_submitted_mr(self):
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.submit()

		self.assertRaises(frappe.ValidationError, mr.delete)

	def test_stopped_mr_changes_to_pending_after_reopen(self):
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.submit()
		mr.load_from_db()

		mr.update_status("Stopped")
		mr.update_status("Submitted")
		self.assertEqual(mr.status, "Pending")

	def test_pending_mr_changes_to_stopped_after_stop(self):
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.submit()
		mr.load_from_db()

		mr.update_status("Stopped")
		self.assertEqual(mr.status, "Stopped")

	def test_cannot_stop_unsubmitted_mr(self):
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		self.assertRaises(frappe.InvalidStatusError, mr.update_status, "Stopped")

	def test_completed_qty_for_purchase(self):
		existing_requested_qty_item1 = self._get_requested_qty(
			"_Test Item Home Desktop 100", "_Test Warehouse - _TC"
		)
		existing_requested_qty_item2 = self._get_requested_qty(
			"_Test Item Home Desktop 200", "_Test Warehouse - _TC"
		)

		# submit material request of type Purchase
		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.submit()

		# map a purchase order
		po_doc = make_purchase_order(mr.name)
		po_doc.supplier = "_Test Supplier"
		po_doc.transaction_date = "2013-07-07"
		po_doc.schedule_date = "2013-07-09"
		po_doc.get("items")[0].qty = 27.0
		po_doc.get("items")[1].qty = 1.5
		po_doc.get("items")[0].schedule_date = "2013-07-09"
		po_doc.get("items")[1].schedule_date = "2013-07-09"

		# check for stopped status of Material Request
		po = frappe.copy_doc(po_doc)
		po.insert()
		po.load_from_db()
		mr.update_status("Stopped")
		self.assertRaises(frappe.InvalidStatusError, po.submit)
		po.db_set("docstatus", 1)
		po.cancel()
		self.assertEqual(po.docstatus, 2)

		# resubmit and check for per complete
		mr.load_from_db()
		mr.update_status("Submitted")
		po = frappe.copy_doc(po_doc)
		po.insert()
		po.submit()

		# check if per complete is as expected
		mr.load_from_db()
		self.assertEqual(mr.per_ordered, 50)
		self.assertEqual(mr.get("items")[0].ordered_qty, 27.0)
		self.assertEqual(mr.get("items")[1].ordered_qty, 1.5)

		current_requested_qty_item1 = self._get_requested_qty(
			"_Test Item Home Desktop 100", "_Test Warehouse - _TC"
		)
		current_requested_qty_item2 = self._get_requested_qty(
			"_Test Item Home Desktop 200", "_Test Warehouse - _TC"
		)

		self.assertEqual(current_requested_qty_item1, existing_requested_qty_item1 + 27.0)
		self.assertEqual(current_requested_qty_item2, existing_requested_qty_item2 + 1.5)

		po.cancel()
		# check if per complete is as expected
		mr.load_from_db()
		self.assertEqual(mr.per_ordered, 0)
		self.assertEqual(mr.get("items")[0].ordered_qty, 0)
		self.assertEqual(mr.get("items")[1].ordered_qty, 0)

		current_requested_qty_item1 = self._get_requested_qty(
			"_Test Item Home Desktop 100", "_Test Warehouse - _TC"
		)
		current_requested_qty_item2 = self._get_requested_qty(
			"_Test Item Home Desktop 200", "_Test Warehouse - _TC"
		)

		self.assertEqual(current_requested_qty_item1, existing_requested_qty_item1 + 54.0)
		self.assertEqual(current_requested_qty_item2, existing_requested_qty_item2 + 3.0)

	def test_completed_qty_for_transfer(self):
		existing_requested_qty_item1 = self._get_requested_qty(
			"_Test Item Home Desktop 100", "_Test Warehouse - _TC"
		)
		existing_requested_qty_item2 = self._get_requested_qty(
			"_Test Item Home Desktop 200", "_Test Warehouse - _TC"
		)

		# submit material request of type Purchase
		mr = frappe.copy_doc(test_records[0])
		mr.material_request_type = "Material Transfer"
		mr.insert()
		mr.submit()

		# check if per complete is None
		mr.load_from_db()
		self.assertEqual(mr.per_ordered, 0)
		self.assertEqual(mr.get("items")[0].ordered_qty, 0)
		self.assertEqual(mr.get("items")[1].ordered_qty, 0)

		current_requested_qty_item1 = self._get_requested_qty(
			"_Test Item Home Desktop 100", "_Test Warehouse - _TC"
		)
		current_requested_qty_item2 = self._get_requested_qty(
			"_Test Item Home Desktop 200", "_Test Warehouse - _TC"
		)

		self.assertEqual(current_requested_qty_item1, existing_requested_qty_item1 + 54.0)
		self.assertEqual(current_requested_qty_item2, existing_requested_qty_item2 + 3.0)

		# map a stock entry
		se_doc = make_stock_entry(mr.name)
		se_doc.update(
			{
				"posting_date": "2013-03-01",
				"posting_time": "01:00",
				"fiscal_year": "_Test Fiscal Year 2013",
			}
		)
		se_doc.get("items")[0].update(
			{"qty": 27.0, "transfer_qty": 27.0, "s_warehouse": "_Test Warehouse 1 - _TC", "basic_rate": 1.0}
		)
		se_doc.get("items")[1].update(
			{"qty": 1.5, "transfer_qty": 1.5, "s_warehouse": "_Test Warehouse 1 - _TC", "basic_rate": 1.0}
		)

		# make available the qty in _Test Warehouse 1 before transfer
		self._insert_stock_entry(27.0, 1.5)

		# check for stopped status of Material Request
		se = frappe.copy_doc(se_doc)
		se.insert()
		mr.update_status("Stopped")
		self.assertRaises(frappe.InvalidStatusError, se.submit)

		mr.update_status("Submitted")

		se.flags.ignore_validate_update_after_submit = True
		se.submit()
		mr.update_status("Stopped")
		self.assertRaises(frappe.InvalidStatusError, se.cancel)

		mr.update_status("Submitted")
		se = frappe.copy_doc(se_doc)
		se.insert()
		se.submit()

		# check if per complete is as expected
		mr.load_from_db()
		self.assertEqual(mr.per_ordered, 50)
		self.assertEqual(mr.get("items")[0].ordered_qty, 27.0)
		self.assertEqual(mr.get("items")[1].ordered_qty, 1.5)

		current_requested_qty_item1 = self._get_requested_qty(
			"_Test Item Home Desktop 100", "_Test Warehouse - _TC"
		)
		current_requested_qty_item2 = self._get_requested_qty(
			"_Test Item Home Desktop 200", "_Test Warehouse - _TC"
		)

		self.assertEqual(current_requested_qty_item1, existing_requested_qty_item1 + 27.0)
		self.assertEqual(current_requested_qty_item2, existing_requested_qty_item2 + 1.5)

		# check if per complete is as expected for Stock Entry cancelled
		se.cancel()
		mr.load_from_db()
		self.assertEqual(mr.per_ordered, 0)
		self.assertEqual(mr.get("items")[0].ordered_qty, 0)
		self.assertEqual(mr.get("items")[1].ordered_qty, 0)

		current_requested_qty_item1 = self._get_requested_qty(
			"_Test Item Home Desktop 100", "_Test Warehouse - _TC"
		)
		current_requested_qty_item2 = self._get_requested_qty(
			"_Test Item Home Desktop 200", "_Test Warehouse - _TC"
		)

		self.assertEqual(current_requested_qty_item1, existing_requested_qty_item1 + 54.0)
		self.assertEqual(current_requested_qty_item2, existing_requested_qty_item2 + 3.0)

	def test_over_transfer_qty_allowance(self):
		mr = frappe.new_doc("Material Request")
		mr.company = "_Test Company"
		mr.scheduled_date = today()
		mr.append(
			"items",
			{
				"item_code": "_Test FG Item",
				"item_name": "_Test FG Item",
				"qty": 10,
				"schedule_date": today(),
				"uom": "_Test UOM 1",
				"warehouse": "_Test Warehouse - _TC",
			},
		)

		mr.material_request_type = "Material Transfer"
		mr.insert()
		mr.submit()

		frappe.db.set_single_value("Stock Settings", "mr_qty_allowance", 20)

		# map a stock entry

		se_doc = make_stock_entry(mr.name)
		se_doc.update(
			{
				"posting_date": today(),
				"posting_time": "00:00",
			}
		)
		se_doc.get("items")[0].update(
			{
				"qty": 13,
				"transfer_qty": 12.0,
				"s_warehouse": "_Test Warehouse - _TC",
				"t_warehouse": "_Test Warehouse 1 - _TC",
				"basic_rate": 1.0,
			}
		)

		# make available the qty in _Test Warehouse 1 before transfer
		sr = frappe.new_doc("Stock Reconciliation")
		sr.company = "_Test Company"
		sr.purpose = "Opening Stock"
		sr.append(
			"items",
			{
				"item_code": "_Test FG Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 20,
				"valuation_rate": 0.01,
			},
		)
		sr.insert()
		sr.submit()
		se = frappe.copy_doc(se_doc)
		se.insert()
		self.assertRaises(frappe.ValidationError)
		se.items[0].qty = 12
		se.submit()

	def test_completed_qty_for_over_transfer(self):
		existing_requested_qty_item1 = self._get_requested_qty(
			"_Test Item Home Desktop 100", "_Test Warehouse - _TC"
		)
		existing_requested_qty_item2 = self._get_requested_qty(
			"_Test Item Home Desktop 200", "_Test Warehouse - _TC"
		)

		# submit material request of type Purchase
		mr = frappe.copy_doc(test_records[0])
		mr.material_request_type = "Material Transfer"
		mr.insert()
		mr.submit()

		# map a stock entry

		se_doc = make_stock_entry(mr.name)
		se_doc.update(
			{
				"posting_date": "2013-03-01",
				"posting_time": "00:00",
				"fiscal_year": "_Test Fiscal Year 2013",
			}
		)
		se_doc.get("items")[0].update(
			{"qty": 54.0, "transfer_qty": 54.0, "s_warehouse": "_Test Warehouse 1 - _TC", "basic_rate": 1.0}
		)
		se_doc.get("items")[1].update(
			{"qty": 3.0, "transfer_qty": 3.0, "s_warehouse": "_Test Warehouse 1 - _TC", "basic_rate": 1.0}
		)

		# make available the qty in _Test Warehouse 1 before transfer
		self._insert_stock_entry(60.0, 3.0)

		# check for stopped status of Material Request
		se = frappe.copy_doc(se_doc)
		se.set_stock_entry_type()
		se.insert()
		mr.update_status("Stopped")
		self.assertRaises(frappe.InvalidStatusError, se.submit)
		self.assertRaises(frappe.InvalidStatusError, se.cancel)

		mr.update_status("Submitted")
		se = frappe.copy_doc(se_doc)
		se.set_stock_entry_type()
		se.insert()
		se.submit()

		# check if per complete is as expected
		mr.load_from_db()

		self.assertEqual(mr.per_ordered, 100)
		self.assertEqual(mr.get("items")[0].ordered_qty, 54.0)
		self.assertEqual(mr.get("items")[1].ordered_qty, 3.0)

		current_requested_qty_item1 = self._get_requested_qty(
			"_Test Item Home Desktop 100", "_Test Warehouse - _TC"
		)
		current_requested_qty_item2 = self._get_requested_qty(
			"_Test Item Home Desktop 200", "_Test Warehouse - _TC"
		)

		self.assertEqual(current_requested_qty_item1, existing_requested_qty_item1)
		self.assertEqual(current_requested_qty_item2, existing_requested_qty_item2)

		# check if per complete is as expected for Stock Entry cancelled
		se.cancel()
		mr.load_from_db()
		self.assertEqual(mr.per_ordered, 0)
		self.assertEqual(mr.get("items")[0].ordered_qty, 0)
		self.assertEqual(mr.get("items")[1].ordered_qty, 0)

		current_requested_qty_item1 = self._get_requested_qty(
			"_Test Item Home Desktop 100", "_Test Warehouse - _TC"
		)
		current_requested_qty_item2 = self._get_requested_qty(
			"_Test Item Home Desktop 200", "_Test Warehouse - _TC"
		)

		self.assertEqual(current_requested_qty_item1, existing_requested_qty_item1 + 54.0)
		self.assertEqual(current_requested_qty_item2, existing_requested_qty_item2 + 3.0)

	def test_incorrect_mapping_of_stock_entry(self):
		# submit material request of type Transfer
		mr = frappe.copy_doc(test_records[0])
		mr.material_request_type = "Material Transfer"
		mr.insert()
		mr.submit()

		se_doc = make_stock_entry(mr.name)
		se_doc.update(
			{
				"posting_date": "2013-03-01",
				"posting_time": "00:00",
				"fiscal_year": "_Test Fiscal Year 2013",
			}
		)
		se_doc.get("items")[0].update(
			{
				"qty": 60.0,
				"transfer_qty": 60.0,
				"s_warehouse": "_Test Warehouse - _TC",
				"t_warehouse": "_Test Warehouse 1 - _TC",
				"basic_rate": 1.0,
			}
		)
		se_doc.get("items")[1].update(
			{
				"item_code": "_Test Item Home Desktop 100",
				"qty": 3.0,
				"transfer_qty": 3.0,
				"s_warehouse": "_Test Warehouse 1 - _TC",
				"basic_rate": 1.0,
			}
		)

		# check for stopped status of Material Request
		se = frappe.copy_doc(se_doc)
		self.assertRaises(frappe.MappingMismatchError, se.insert)

		# submit material request of type Transfer
		mr = frappe.copy_doc(test_records[0])
		mr.material_request_type = "Material Issue"
		mr.insert()
		mr.submit()

		se_doc = make_stock_entry(mr.name)
		self.assertEqual(se_doc.get("items")[0].s_warehouse, "_Test Warehouse - _TC")

	def test_warehouse_company_validation(self):
		from erpnext.stock.utils import InvalidWarehouseCompany

		mr = frappe.copy_doc(test_records[0])
		mr.company = "_Test Company 1"
		self.assertRaises(InvalidWarehouseCompany, mr.insert)

	def _get_requested_qty(self, item_code, warehouse):
		return flt(
			frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "indented_qty")
		)

	def test_make_stock_entry_for_material_issue(self):
		mr = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_stock_entry, mr.name)

		mr = frappe.get_doc("Material Request", mr.name)
		mr.material_request_type = "Material Issue"
		mr.submit()
		se = make_stock_entry(mr.name)

		self.assertEqual(se.doctype, "Stock Entry")
		self.assertEqual(len(se.get("items")), len(mr.get("items")))

	def test_completed_qty_for_issue(self):
		def _get_requested_qty():
			return flt(
				frappe.db.get_value(
					"Bin",
					{"item_code": "_Test Item Home Desktop 100", "warehouse": "_Test Warehouse - _TC"},
					"indented_qty",
				)
			)

		existing_requested_qty = _get_requested_qty()

		mr = frappe.copy_doc(test_records[0])
		mr.material_request_type = "Material Issue"
		mr.submit()
		frappe.db.value_cache = {}

		# testing bin value after material request is submitted
		self.assertEqual(_get_requested_qty(), existing_requested_qty - 54.0)

		# receive items to allow issue
		self._insert_stock_entry(60, 6, "_Test Warehouse - _TC")

		# make stock entry against MR

		se_doc = make_stock_entry(mr.name)
		se_doc.fiscal_year = "_Test Fiscal Year 2014"
		se_doc.get("items")[0].qty = 54.0
		se_doc.insert()
		se_doc.submit()

		# check if per complete is as expected
		mr.load_from_db()
		self.assertEqual(mr.get("items")[0].ordered_qty, 54.0)
		self.assertEqual(mr.get("items")[1].ordered_qty, 3.0)

		# testing bin requested qty after issuing stock against material request
		self.assertEqual(_get_requested_qty(), existing_requested_qty)

	def test_material_request_type_manufacture(self):
		mr = frappe.copy_doc(test_records[1]).insert()
		mr = frappe.get_doc("Material Request", mr.name)
		mr.submit()
		completed_qty = mr.items[0].ordered_qty
		requested_qty = frappe.db.sql(
			"""select indented_qty from `tabBin` where \
			item_code= %s and warehouse= %s """,
			(mr.items[0].item_code, mr.items[0].warehouse),
		)[0][0]

		prod_order = raise_work_orders(mr.name)
		po = frappe.get_doc("Work Order", prod_order[0])
		po.wip_warehouse = "_Test Warehouse 1 - _TC"
		po.submit()

		mr = frappe.get_doc("Material Request", mr.name)
		self.assertEqual(completed_qty + po.qty, mr.items[0].ordered_qty)

		new_requested_qty = frappe.db.sql(
			"""select indented_qty from `tabBin` where \
			item_code= %s and warehouse= %s """,
			(mr.items[0].item_code, mr.items[0].warehouse),
		)[0][0]

		self.assertEqual(requested_qty - po.qty, new_requested_qty)

		po.cancel()

		mr = frappe.get_doc("Material Request", mr.name)
		self.assertEqual(completed_qty, mr.items[0].ordered_qty)

		new_requested_qty = frappe.db.sql(
			"""select indented_qty from `tabBin` where \
			item_code= %s and warehouse= %s """,
			(mr.items[0].item_code, mr.items[0].warehouse),
		)[0][0]
		self.assertEqual(requested_qty, new_requested_qty)

	def test_requested_qty_multi_uom(self):
		existing_requested_qty = self._get_requested_qty("_Test FG Item", "_Test Warehouse - _TC")

		mr = make_material_request(
			item_code="_Test FG Item",
			material_request_type="Manufacture",
			uom="_Test UOM 1",
			conversion_factor=12,
		)

		requested_qty = self._get_requested_qty("_Test FG Item", "_Test Warehouse - _TC")

		self.assertEqual(requested_qty, existing_requested_qty + 120)

		work_order = raise_work_orders(mr.name)
		wo = frappe.get_doc("Work Order", work_order[0])
		wo.qty = 50
		wo.wip_warehouse = "_Test Warehouse 1 - _TC"
		wo.submit()

		requested_qty = self._get_requested_qty("_Test FG Item", "_Test Warehouse - _TC")
		self.assertEqual(requested_qty, existing_requested_qty + 70)

		wo.cancel()

		requested_qty = self._get_requested_qty("_Test FG Item", "_Test Warehouse - _TC")
		self.assertEqual(requested_qty, existing_requested_qty + 120)

		mr.reload()
		mr.cancel()
		requested_qty = self._get_requested_qty("_Test FG Item", "_Test Warehouse - _TC")
		self.assertEqual(requested_qty, existing_requested_qty)

	def test_multi_uom_for_purchase(self):
		mr = frappe.copy_doc(test_records[0])
		mr.material_request_type = "Purchase"
		item = mr.items[0]
		mr.schedule_date = today()

		if not frappe.db.get_value("UOM Conversion Detail", {"parent": item.item_code, "uom": "Kg"}):
			item_doc = frappe.get_doc("Item", item.item_code)
			item_doc.append("uoms", {"uom": "Kg", "conversion_factor": 5})
			item_doc.save(ignore_permissions=True)

		item.uom = "Kg"
		for item in mr.items:
			item.schedule_date = mr.schedule_date

		mr.insert()
		self.assertRaises(frappe.ValidationError, make_purchase_order, mr.name)

		mr = frappe.get_doc("Material Request", mr.name)
		mr.submit()
		item = mr.items[0]

		self.assertEqual(item.uom, "Kg")
		self.assertEqual(item.conversion_factor, 5.0)
		self.assertEqual(item.stock_qty, flt(item.qty * 5))

		po = make_purchase_order(mr.name)
		self.assertEqual(po.doctype, "Purchase Order")
		self.assertEqual(len(po.get("items")), len(mr.get("items")))

		po.supplier = "_Test Supplier"
		po.insert()
		po.submit()
		mr = frappe.get_doc("Material Request", mr.name)
		self.assertEqual(mr.per_ordered, 100)

	def test_fractional_conversion_factor_for_purchase(self):
		item = create_item("_Test Fractional Conversion Item", stock_uom="Kg", is_purchase_item=1)
		conversion_factor = 0.453592292

		mr = make_material_request(
			item_code=item.name,
			qty=1000,
			uom="Pound",
			conversion_factor=conversion_factor,
		)
		mr.reload()

		self.assertEqual(mr.items[0].conversion_factor, conversion_factor)

		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.insert()
		po.reload()

		self.assertEqual(po.items[0].conversion_factor, conversion_factor)
		self.assertEqual(po.items[0].stock_qty, mr.items[0].stock_qty)

	def test_customer_provided_parts_mr(self):
		create_item("CUST-0987", is_customer_provided_item=1, customer="_Test Customer", is_purchase_item=0)
		existing_requested_qty = self._get_requested_qty("_Test Customer", "_Test Warehouse - _TC")

		mr = make_material_request(item_code="CUST-0987", material_request_type="Customer Provided")
		se = make_stock_entry(mr.name)
		se.insert()
		se.submit()
		self.assertEqual(se.get("items")[0].amount, 0)
		self.assertEqual(se.get("items")[0].material_request, mr.name)
		mr = frappe.get_doc("Material Request", mr.name)
		mr.submit()
		current_requested_qty = self._get_requested_qty("_Test Customer", "_Test Warehouse - _TC")

		self.assertEqual(mr.per_ordered, 100)
		self.assertEqual(existing_requested_qty, current_requested_qty)

	def test_auto_email_users_with_company_user_permissions(self):
		from erpnext.stock.reorder_item import get_email_list

		comapnywise_users = {
			"_Test Company": "test_auto_email_@example.com",
			"_Test Company 1": "test_auto_email_1@example.com",
		}

		permissions = []

		for company, user in comapnywise_users.items():
			if not frappe.db.exists("User", user):
				frappe.get_doc(
					{
						"doctype": "User",
						"email": user,
						"first_name": user,
						"send_notifications": 0,
						"enabled": 1,
						"user_type": "System User",
						"roles": [{"role": "Purchase Manager"}],
					}
				).insert(ignore_permissions=True)

			if not frappe.db.exists(
				"User Permission", {"user": user, "allow": "Company", "for_value": company}
			):
				perm_doc = frappe.get_doc(
					{
						"doctype": "User Permission",
						"user": user,
						"allow": "Company",
						"for_value": company,
						"apply_to_all_doctypes": 1,
					}
				).insert(ignore_permissions=True)

				permissions.append(perm_doc)

		comapnywise_mr_list = frappe._dict({})
		mr1 = make_material_request()
		comapnywise_mr_list.setdefault(mr1.company, []).append(mr1.name)

		mr2 = make_material_request(
			company="_Test Company 1", warehouse="Stores - _TC1", cost_center="Main - _TC1"
		)
		comapnywise_mr_list.setdefault(mr2.company, []).append(mr2.name)

		for company, _mr_list in comapnywise_mr_list.items():
			emails = get_email_list(company)

			self.assertTrue(comapnywise_users[company] in emails)

		for perm in permissions:
			perm.delete()

	def test_manufacture_type_status_over_wo(self):
		from erpnext.stock.doctype.material_request.material_request import raise_work_orders

		mr = make_material_request(
			item_code="_Test FG Item", material_request_type="Manufacture", do_not_submit=False
		)

		work_order = raise_work_orders(mr.name)
		wo = frappe.get_doc("Work Order", work_order[0])
		wo.wip_warehouse = "_Test Warehouse 1 - _TC"
		wo.submit()

		mr.reload()

		self.assertEqual(mr.per_ordered, 100)
		self.assertEqual(mr.status, "Ordered")

	def test_material_request_qty_over_sales_order_limit(self):
		from erpnext.controllers.status_updater import OverAllowanceError
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order()
		mr = make_material_request(qty=100, do_not_submit=True)
		mr.items[0].sales_order = so.name
		mr.items[0].sales_order_item = so.items[0].name
		mr.save()

		self.assertRaises(OverAllowanceError, mr.submit)

	def test_item_change_on_sales_order_row_is_blocked(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_material_request
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		other_item = create_item("_Test MR Item Swap").name
		so = make_sales_order()
		mr = make_material_request(so.name)
		mr.material_request_type = "Purchase"
		# swapping the fetched item would leave a stale link to the SO row
		mr.items[0].item_code = other_item
		self.assertRaises(frappe.ValidationError, mr.insert)

	def test_pending_qty_in_pick_list(self):
		"""Test for pick list mapped doc qty from partially received Material Request Transfer"""
		import json

		from erpnext.stock.doctype.pick_list.pick_list import create_stock_entry
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		new_item = create_item("_Test Pick List Item", is_stock_item=1)
		item_code = new_item.name

		make_stock_entry(
			item_code=item_code,
			target="_Test Warehouse - _TC",
			qty=10,
			do_not_save=False,
			do_not_submit=False,
		)

		mr = make_material_request(item_code=item_code, material_request_type="Material Transfer")
		pl = create_pick_list(mr.name)
		pl.save()
		pl.locations[0].qty = 5
		pl.locations[0].stock_qty = 5
		pl.submit()

		to_warehouse = create_warehouse("_Test Warehouse - _TC")

		se_data = create_stock_entry(json.dumps(pl.as_dict()))
		se = frappe.get_doc(se_data)
		se.items[0].t_warehouse = to_warehouse
		se.save()
		se.submit()

		pl.load_from_db()
		self.assertEqual(pl.locations[0].picked_qty, se.items[0].qty)

		mr.load_from_db()
		self.assertEqual(mr.status, "Partially Received")

		pl_for_pending = create_pick_list(mr.name)
		self.assertEqual(pl_for_pending.locations[0].qty, 5)

	def test_mr_status_with_partial_and_excess_end_transit(self):
		material_request = make_material_request(
			material_request_type="Material Transfer",
			item_code="_Test Item Home Desktop 100",
		)

		in_transit_wh = get_in_transit_warehouse(material_request.company)

		# Make sure stock is available in source warehouse
		self._insert_stock_entry(20.0, 20.0)

		# Stock Entry (Transfer to In-Transit)
		stock_entry_1 = make_in_transit_stock_entry(material_request.name, in_transit_wh)
		stock_entry_1.items[0].update(
			{
				"qty": 5,
				"s_warehouse": "_Test Warehouse 1 - _TC",
			}
		)
		stock_entry_1.save().submit()

		stock_entry_2 = make_in_transit_stock_entry(material_request.name, in_transit_wh)
		stock_entry_2.items[0].update(
			{
				"qty": 5,
				"s_warehouse": "_Test Warehouse 1 - _TC",
			}
		)
		stock_entry_2.save().submit()

		end_transit_1 = make_stock_in_entry(stock_entry_1.name)
		end_transit_1.save().submit()

		# Material Request Transfer Status should still be In Transit
		material_request.load_from_db()
		self.assertEqual(material_request.transfer_status, "In Transit")

		end_transit_2 = make_stock_in_entry(stock_entry_2.name)
		end_transit_2.items[0].update({"qty": 6})  # More than transferred
		end_transit_2.save()

		self.assertRaises(frappe.ValidationError, end_transit_2.submit)

	def test_make_stock_entry_material_issue_warehouse_mapping(self):
		"""Test to ensure while making stock entry from material request of type Material Issue, warehouse is mapped correctly"""
		mr = make_material_request(material_request_type="Material Issue", do_not_submit=True)
		mr.set_warehouse = "_Test Warehouse - _TC"
		mr.save()
		mr.submit()

		se = make_stock_entry(mr.name)
		self.assertEqual(se.from_warehouse, "_Test Warehouse - _TC")
		self.assertIsNone(se.to_warehouse)
		se.save()
		se.submit()

	def test_mr_status_for_mixed_direct_and_transit_transfer(self):
		material_request = make_material_request(
			material_request_type="Material Transfer",
			item_code="_Test Item Home Desktop 100",
			qty=5,
		)

		in_transit_wh = get_in_transit_warehouse(material_request.company)

		# Make stock available
		self._insert_stock_entry(20.0, 20.0)

		# Direct Transfer for 3 Qty
		direct_transfer = make_stock_entry(material_request.name)
		direct_transfer.items[0].update(
			{
				"qty": 3,
				"transfer_qty": 3,
				"s_warehouse": "_Test Warehouse 1 - _TC",
			}
		)
		direct_transfer.save()
		direct_transfer.submit()

		# In Transit Transfer for remaining 2 Qty
		transit_transfer = make_in_transit_stock_entry(material_request.name, in_transit_wh)
		transit_transfer.items[0].update(
			{
				"qty": 2,
				"s_warehouse": "_Test Warehouse 1 - _TC",
			}
		)
		transit_transfer.save()
		transit_transfer.submit()

		# Complete End Transit
		end_transit = make_stock_in_entry(transit_transfer.name)
		end_transit.save()
		end_transit.submit()

		material_request.reload()

		self.assertEqual(material_request.per_ordered, 100)
		self.assertEqual(material_request.status, "Transferred")
		self.assertEqual(material_request.transfer_status, "Completed")

<<<<<<< HEAD
=======
	def test_check_modified_date_detects_concurrent_modification(self):
		"""check_modified_date must raise when the in-memory doc is stale vs the DB modified
		timestamp. Covers the converted get_value + get_datetime comparison that replaced the
		raw MariaDB-only TIMEDIFF (which errors on Postgres); update_status() runs this guard."""
		from frappe.utils import add_to_date, get_datetime

		mr = make_material_request(qty=10)

		fresh = frappe.get_doc("Material Request", mr.name)
		# modified matches the DB row -> guard passes.
		fresh.check_modified_date()

		# Stale in-memory modified -> concurrent-modification guard must fire.
		fresh.modified = add_to_date(get_datetime(fresh.modified), seconds=-120)
		with self.assertRaises(frappe.ValidationError) as cm:
			fresh.check_modified_date()
		self.assertIn("has been modified", str(cm.exception))

	def test_validate_qty_against_so_blocks_over_request(self):
		"""validate_qty_against_so must block requesting more than the Sales Order qty, net of
		already-indented submitted MRs. Covers the converted Sales Order Item and Material Request
		Item SUM queries. (The guard is currently not wired into validate(), so call it directly.)"""
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		item_code = "_Test Item"
		so = make_sales_order(item_code=item_code, qty=10)  # submitted -> SO Item stock_qty 10

		def _mr_against_so(qty):
			mr = frappe.new_doc("Material Request")
			mr.material_request_type = "Purchase"
			mr.company = "_Test Company"
			mr.append(
				"items",
				{
					"item_code": item_code,
					"qty": qty,
					"uom": "_Test UOM",
					"conversion_factor": 1,
					"schedule_date": today(),
					"warehouse": "_Test Warehouse - _TC",
					"sales_order": so.name,
				},
			)
			return mr

		# An already-submitted MR consuming 6 of the SO's 10.
		mr1 = _mr_against_so(6)
		mr1.insert()
		mr1.submit()

		# A new request for 5 more -> already_indented 6 + 5 = 11 > 10 -> must throw.
		over = _mr_against_so(5)
		over.insert()
		with self.assertRaises(frappe.ValidationError) as cm:
			over.validate_qty_against_so()
		self.assertIn("maximum", str(cm.exception))

		# Exactly within the remaining 4 -> 6 + 4 = 10, not greater -> no throw.
		over.items[0].qty = 4
		over.validate_qty_against_so()

	def test_get_material_requests_based_on_supplier(self):
		"""The supplier-based Material Request picker must run on every engine.

		It deduplicated requests with SELECT DISTINCT while ordering by an item
		column that is not in the select list; PostgreSQL rejects that, so the
		picker has to group and order by an aggregate instead.
		"""
		from frappe.core.doctype.user.test_user import test_user

		from erpnext.stock.doctype.material_request.material_request import (
			get_material_requests_based_on_supplier,
		)

		item = create_item("_Test MR Default Supplier Item")
		item.set("item_defaults", [])
		item.append(
			"item_defaults",
			{
				"company": "_Test Company",
				"default_warehouse": "_Test Warehouse - _TC",
				"default_supplier": "_Test Supplier",
			},
		)
		item.save()

		mr1 = make_material_request(item_code=item.name, qty=5)
		mr2 = make_material_request(item_code=item.name, qty=7)

		result = get_material_requests_based_on_supplier(
			doctype="Material Request",
			txt="",
			searchfield="name",
			start=0,
			page_len=20,
			filters={"supplier": "_Test Supplier", "company": "_Test Company"},
		)
		returned = {row["name"] for row in result}
		self.assertIn(mr1.name, returned)
		self.assertIn(mr2.name, returned)

		with test_user(first_name="mr-supplier-picker", roles=["Purchase Manager"]) as user:
			with self.set_user(user.name):
				self.assertFalse(frappe.has_permission("Item", "read"))
				result = get_material_requests_based_on_supplier(
					doctype="Material Request",
					txt="",
					searchfield="name",
					start=0,
					page_len=20,
					filters={"supplier": "_Test Supplier", "company": "_Test Company"},
				)
				returned = {row["name"] for row in result}
				self.assertIn(mr1.name, returned)
				self.assertIn(mr2.name, returned)

	def test_default_supplier_item_permissions(self):
		from frappe.core.doctype.user.test_user import test_user
		from frappe.permissions import add_user_permission

		from erpnext.stock.doctype.material_request.mapper import get_items_based_on_default_supplier

		allowed_item = create_item_with_default_supplier("_Test MR Allowed Supplier Item", "_Test Supplier")
		restricted_item = create_item_with_default_supplier(
			"_Test MR Restricted Supplier Item", "_Test Supplier"
		)
		for role in ("Purchase User", "Purchase Manager"):
			with (
				self.subTest(role=role),
				test_user(first_name=f"mr-{frappe.scrub(role)}", roles=[role]) as user,
			):
				with self.set_user(user.name):
					self.assertTrue(frappe.has_permission("Item", "select"))
					self.assertEqual(frappe.has_permission("Item", "read"), role == "Purchase User")
					items = get_items_based_on_default_supplier("_Test Supplier")
					self.assertIn(allowed_item, items)
					self.assertIn(restricted_item, items)

				add_user_permission("Item", allowed_item, user.name)
				with self.set_user(user.name):
					self.assertEqual(get_items_based_on_default_supplier("_Test Supplier"), [allowed_item])
					self.assertEqual(get_items_based_on_default_supplier("_Test Supplier 1"), [])

	def test_default_supplier_items_deny_missing_access(self):
		from frappe.core.doctype.user.test_user import test_user

		from erpnext.stock.doctype.material_request.mapper import get_items_based_on_default_supplier

		with test_user(first_name="mr-no-item-access", roles=[], user_type="Website User") as user:
			for username in (user.name, "Guest"):
				with self.subTest(user=username), self.set_user(username):
					self.assertFalse(frappe.has_permission("Item", "select"))
					self.assertRaises(
						frappe.PermissionError, get_items_based_on_default_supplier, "_Test Supplier"
					)

	def test_default_supplier_items_preserve_order_and_duplicates(self):
		from erpnext.stock.doctype.material_request.mapper import get_items_based_on_default_supplier

		self.load_test_records("Company")
		item_code = create_item_with_default_supplier("_Test MR Supplier Z", "_Test Supplier")
		item = frappe.get_doc("Item", item_code)
		item.append("item_defaults", {"company": "_Test Company 1", "default_supplier": "_Test Supplier"})
		item.save()
		other_item = create_item_with_default_supplier("_Test MR Supplier A", "_Test Supplier")
		for index, row in enumerate(
			[*item.item_defaults, frappe.get_doc("Item", other_item).item_defaults[0]]
		):
			frappe.db.set_value("Item Default", row.name, "creation", f"2020-01-0{index + 1} 00:00:00")

		expected = frappe.get_all(
			"Item Default", {"default_supplier": "_Test Supplier", "parenttype": "Item"}, pluck="parent"
		)
		self.assertEqual(expected.count(item_code), 2)
		self.assertEqual(get_items_based_on_default_supplier("_Test Supplier"), expected)

	def test_get_item_default_suppliers(self):
		from erpnext.stock.doctype.material_request.mapper import get_item_default_suppliers

		with_supplier = create_item_with_default_supplier("_Test MR Item Supplier A", "_Test Supplier")
		without_supplier = create_item("_Test MR Item Without Supplier").name

		mr = make_material_request_for_items([with_supplier, without_supplier])
		items = get_item_default_suppliers(mr.name)

		self.assertEqual([d["item_code"] for d in items], [with_supplier, without_supplier])
		self.assertEqual(items[0]["supplier"], "_Test Supplier")
		self.assertFalse(items[1]["supplier"])
		self.assertEqual(items[0]["pending_qty"], 10)

	def test_make_purchase_orders_by_supplier(self):
		from erpnext.stock.doctype.material_request.mapper import make_purchase_orders_by_supplier

		item_codes = [create_item(f"_Test MR Grouped Item {index}").name for index in range(1, 4)]
		mr = make_material_request_for_items(item_codes)
		suppliers = ["_Test Supplier", "_Test Supplier", "_Test Supplier 1"]

		purchase_orders = make_purchase_orders_by_supplier(
			mr.name,
			[
				{
					"material_request_item": item.name,
					"item_code": item.item_code,
					"qty": qty,
					"supplier": supplier,
				}
				for item, supplier, qty in zip(mr.items, suppliers, [10, 10, 4], strict=True)
			],
		)

		self.assertEqual(len(purchase_orders), 2)

		first, second = (frappe.get_doc("Purchase Order", name) for name in purchase_orders)
		self.assertEqual(first.supplier, "_Test Supplier")
		self.assertEqual([d.item_code for d in first.items], item_codes[:2])
		self.assertEqual(second.supplier, "_Test Supplier 1")
		self.assertEqual([d.item_code for d in second.items], item_codes[2:])
		self.assertEqual(second.items[0].qty, 4)
		self.assertEqual(second.items[0].stock_qty, 4)

	def test_make_purchase_orders_by_supplier_sets_schedule_date(self):
		from erpnext.stock.doctype.material_request.mapper import make_purchase_orders_by_supplier

		mr = make_material_request_for_items(["_Test Item"])
		frappe.db.set_value("Material Request Item", mr.items[0].name, "schedule_date", add_days(today(), -1))

		purchase_orders = make_purchase_orders_by_supplier(
			mr.name,
			[
				{
					"material_request_item": mr.items[0].name,
					"item_code": "_Test Item",
					"qty": 10,
					"supplier": "_Test Supplier",
				}
			],
		)

		po = frappe.get_doc("Purchase Order", purchase_orders[0])
		self.assertEqual(po.schedule_date, getdate(today()))

		alerts = [m for m in frappe.get_message_log() if m.get("alert")]
		self.assertTrue(any("was set to today" in m.get("message") for m in alerts))

	def test_make_purchase_orders_by_supplier_invalid_rows(self):
		from erpnext.stock.doctype.material_request.mapper import make_purchase_orders_by_supplier

		mr = make_material_request_for_items(["_Test Item"])
		row = {
			"material_request_item": mr.items[0].name,
			"item_code": "_Test Item",
			"qty": 10,
			"supplier": "_Test Supplier",
		}

		for invalid in [{"supplier": None}, {"qty": 0}, {"qty": -5}, {"qty": 11}]:
			self.assertRaises(
				frappe.ValidationError, make_purchase_orders_by_supplier, mr.name, [row | invalid]
			)

		self.assertRaises(frappe.ValidationError, make_purchase_orders_by_supplier, mr.name, [])

		self.assertRaises(
			frappe.ValidationError,
			make_purchase_orders_by_supplier,
			mr.name,
			[row, row | {"supplier": "_Test Supplier 1"}],
		)

	def test_manufacture_request_from_sales_order_updates_requested_qty(self):
		from erpnext.selling.doctype.sales_order.mapper import make_material_request as make_request_from_so
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order(qty=5)
		mr = make_request_from_so(so.name)
		mr.material_request_type = "Manufacture"
		mr.items[0].schedule_date = today()
		mr.submit()

		self.assertEqual(frappe.db.get_value("Sales Order Item", so.items[0].name, "requested_qty"), 5)
		self.assertRaises(frappe.ValidationError, make_request_from_so, so.name)

		mr.cancel()
		self.assertEqual(frappe.db.get_value("Sales Order Item", so.items[0].name, "requested_qty"), 0)

	def test_work_orders_are_raised_once_per_requested_qty(self):
		mr = make_material_request(item_code="_Test FG Item", material_request_type="Manufacture", qty=10)

		first = raise_work_orders(mr.name, mr.company)
		self.assertEqual(raise_work_orders(mr.name, mr.company), [])

		extra = frappe.copy_doc(frappe.get_doc("Work Order", first[0]))
		extra.insert()
		for name in (first[0], extra.name):
			work_order = frappe.get_doc("Work Order", name)
			work_order.wip_warehouse = "_Test Warehouse 1 - _TC"
			work_order.save()

		frappe.get_doc("Work Order", first[0]).submit()
		self.assertRaises(frappe.ValidationError, frappe.get_doc("Work Order", extra.name).submit)

		stopped_mr = make_material_request(
			item_code="_Test FG Item", material_request_type="Manufacture", qty=3
		)
		draft = frappe.get_doc("Work Order", raise_work_orders(stopped_mr.name, stopped_mr.company)[0])
		draft.wip_warehouse = "_Test Warehouse 1 - _TC"
		draft.save()
		update_status(stopped_mr.name, "Stopped")
		self.assertRaises(frappe.InvalidStatusError, draft.submit)

	def test_closed_work_order_keeps_its_produced_qty(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry as make_wo_stock_entry
		from erpnext.manufacturing.doctype.work_order.work_order import close_work_order
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry as make_se

		fg_item = make_item(properties={"is_stock_item": 1})
		raw_material = make_item(properties={"is_stock_item": 1}).name
		make_se(item_code=raw_material, target="_Test Warehouse - _TC", qty=10, basic_rate=100)
		make_bom(item=fg_item.name, raw_materials=[raw_material], rm_qty=1)
		mr = make_material_request(
			item_code=fg_item.name, material_request_type="Manufacture", qty=10, uom=fg_item.stock_uom
		)

		work_order = frappe.get_doc("Work Order", raise_work_orders(mr.name, mr.company)[0])
		work_order.update(
			{
				"skip_transfer": 1,
				"wip_warehouse": "_Test Warehouse 1 - _TC",
				"source_warehouse": "_Test Warehouse - _TC",
			}
		)
		for row in work_order.required_items:
			row.source_warehouse = "_Test Warehouse - _TC"
		work_order.submit()
		frappe.get_doc(make_wo_stock_entry(work_order.name, "Manufacture", 4)).submit()
		close_work_order(work_order.name, "Closed")

		self.assertEqual(frappe.db.get_value("Material Request Item", mr.items[0].name, "ordered_qty"), 4)
		self.assertEqual(
			frappe.db.get_value("Work Order", raise_work_orders(mr.name, mr.company)[0], "qty"), 6
		)

	@change_settings("Manufacturing Settings", {"overproduction_percentage_for_work_order": 10})
	def test_closing_an_overproduced_work_order_is_allowed(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry as make_wo_stock_entry
		from erpnext.manufacturing.doctype.work_order.work_order import close_work_order
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry as make_se

		fg_item = make_item(properties={"is_stock_item": 1})
		raw_material = make_item(properties={"is_stock_item": 1}).name
		make_se(item_code=raw_material, target="_Test Warehouse - _TC", qty=20, basic_rate=100)
		make_bom(item=fg_item.name, raw_materials=[raw_material], rm_qty=1)
		mr = make_material_request(
			item_code=fg_item.name, material_request_type="Manufacture", qty=10, uom=fg_item.stock_uom
		)

		work_order = frappe.get_doc("Work Order", raise_work_orders(mr.name, mr.company)[0])
		work_order.update(
			{
				"skip_transfer": 1,
				"wip_warehouse": "_Test Warehouse 1 - _TC",
				"source_warehouse": "_Test Warehouse - _TC",
			}
		)
		for row in work_order.required_items:
			row.source_warehouse = "_Test Warehouse - _TC"
		work_order.submit()
		frappe.get_doc(make_wo_stock_entry(work_order.name, "Manufacture", 11)).submit()
		close_work_order(work_order.name, "Closed")

		self.assertEqual(frappe.db.get_value("Material Request Item", mr.items[0].name, "ordered_qty"), 10)

	@change_settings("Stock Settings", {"auto_indent": 1, "reorder_email_notify": 0})
	def test_reorder_raises_one_request_for_a_shortfall(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.reorder_item import reorder_item

		item_code = make_item(
			properties={
				"is_stock_item": 1,
				"reorder_levels": [
					{
						"warehouse": "_Test Warehouse - _TC",
						"warehouse_reorder_level": 10,
						"warehouse_reorder_qty": 5,
						"material_request_type": "Purchase",
					}
				],
			}
		).name

		def get_requested_qty(requests):
			return [d.stock_qty for mr in requests for d in mr.items if d.item_code == item_code]

		self.assertEqual(get_requested_qty(reorder_item()), [15])
		self.assertEqual(get_requested_qty(reorder_item() or []), [])

	def test_customer_provided_request_refuses_other_items(self):
		self.assertRaises(
			frappe.ValidationError,
			make_material_request,
			item_code="_Test Item",
			material_request_type="Customer Provided",
		)

	def test_production_plan_requested_qty_follows_the_stock_qty(self):
		plan, _mr = make_plan_request_in_boxes()

		self.assertEqual(
			frappe.db.get_value("Material Request Plan Item", plan.mr_items[0].name, "requested_qty"), 24
		)

	def test_production_plan_requested_qty_is_rebuilt_from_submitted_requests(self):
		from erpnext.patches.v16_0.rebuild_production_plan_requested_qty import execute

		plan, mr = make_plan_request_in_boxes()
		plan_item = plan.mr_items[0].name

		frappe.db.set_value("Material Request Plan Item", plan_item, "requested_qty", 2)
		execute()
		self.assertEqual(frappe.db.get_value("Material Request Plan Item", plan_item, "requested_qty"), 24)

		frappe.db.set_value("Material Request Plan Item", plan_item, "requested_qty", 2)
		mr.cancel()
		self.assertEqual(frappe.db.get_value("Material Request Plan Item", plan_item, "requested_qty"), 0)

	def test_pick_list_maps_only_the_qty_left_to_transfer(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry as make_se

		item_code = create_item("_Test MR Pick Transfer Item", is_stock_item=1).name
		make_se(item_code=item_code, target="_Test Warehouse - _TC", qty=20, basic_rate=100)
		mr = make_material_request(
			item_code=item_code,
			material_request_type="Material Transfer",
			from_warehouse="_Test Warehouse - _TC",
			warehouse="_Test Warehouse 1 - _TC",
			uom="Nos",
		)

		transfer = make_stock_entry(mr.name)
		transfer.items[0].qty = 6
		transfer.submit()

		self.assertEqual(create_pick_list(mr.name).locations[0].qty, 4)

		update_status(mr.name, "Stopped")
		self.assertRaises(frappe.InvalidStatusError, create_pick_list, mr.name)

	def test_mappers_skip_ordered_rows_and_stopped_requests(self):
		mr = make_material_request(item_code="_Test Item", qty=10)
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.submit()

		self.assertFalse(make_supplier_quotation(mr.name).items)
		self.assertRaises(frappe.ValidationError, create_pick_list, mr.name)

		stopped_mr = make_material_request(item_code="_Test Item", qty=10)
		update_status(stopped_mr.name, "Stopped")
		for mapper in (
			make_supplier_quotation,
			make_request_for_quotation,
			make_purchase_order,
			make_stock_entry,
		):
			self.assertRaises(frappe.InvalidStatusError, mapper, stopped_mr.name)

	def test_purchase_order_of_a_stopped_request_can_be_closed(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status as update_po_status

		mr = make_material_request(item_code="_Test Item", qty=10)
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.items[0].qty = 4
		po.submit()
		update_status(mr.name, "Stopped")

		update_po_status("Closed", po.name)

		self.assertEqual(frappe.db.get_value("Purchase Order", po.name, "status"), "Closed")

	def test_subcontracting_request_is_counted_in_indented_qty(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		existing_qty = self._get_requested_qty("Subcontracted Item SA1", "_Test Warehouse - _TC")

		mr = make_material_request(
			item_code="Subcontracted Item SA1", qty=10, material_request_type="Subcontracting"
		)
		self.assertEqual(
			self._get_requested_qty("Subcontracted Item SA1", "_Test Warehouse - _TC"), existing_qty + 10
		)

		po = create_purchase_order(
			rm_items=[
				{
					"warehouse": "_Test Warehouse - _TC",
					"item_code": "Subcontracted Service Item 1",
					"qty": 10,
					"rate": 100,
					"fg_item": "Subcontracted Item SA1",
					"fg_item_qty": 10,
				}
			],
			is_subcontracted=1,
			supplier_warehouse="_Test Warehouse 1 - _TC",
			do_not_save=True,
		)
		po.items[0].material_request = mr.name
		po.items[0].material_request_item = mr.items[0].name
		po.submit()

		self.assertEqual(
			self._get_requested_qty("Subcontracted Item SA1", "_Test Warehouse - _TC"), existing_qty
		)

	def test_reorder_mail_goes_to_the_company_and_shows_stock_qty(self):
		from erpnext.stock.reorder_item import get_email_list

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "reorder-other-company@example.com",
				"first_name": "Reorder",
				"send_welcome_email": 0,
				"roles": [{"role": "Stock Manager"}],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user.name,
				"allow": "Company",
				"for_value": "_Test Company",
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)

		self.assertNotIn(user.email, get_email_list("_Test Company 1"))

		scoped_user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "reorder-request-scoped@example.com",
				"first_name": "Reorder Scoped",
				"send_welcome_email": 0,
				"roles": [{"role": "Stock Manager"}],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": scoped_user.name,
				"allow": "Company",
				"for_value": "_Test Company",
				"apply_to_all_doctypes": 0,
				"applicable_for": "Material Request",
			}
		).insert(ignore_permissions=True)
		self.assertNotIn(scoped_user.email, get_email_list("_Test Company 1"))
		self.assertIn(scoped_user.email, get_email_list("_Test Company"))

		from unittest.mock import patch

		hidden_user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "reorder-parent-only@example.com",
				"first_name": "Reorder Parent Only",
				"send_welcome_email": 0,
				"roles": [{"role": "Stock Manager"}],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": hidden_user.name,
				"allow": "Company",
				"for_value": "_Test Company",
				"apply_to_all_doctypes": 0,
				"applicable_for": "Material Request",
				"hide_descendants": 1,
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Company", "_Test Company 1", "parent_company", "_Test Company")

		with patch("erpnext.stock.reorder_item.get_ancestors_of", return_value=["_Test Company"]):
			recipients = get_email_list("_Test Company 1")
			self.assertIn(user.email, recipients)
			self.assertNotIn(hidden_user.email, recipients)

		message = frappe.render_template(
			"templates/emails/reorder_item.html",
			{
				"mr_list": [
					frappe._dict(
						name="MR-1",
						items=[
							frappe._dict(item_code="X", qty=2, uom="Box", stock_qty=24, projected_on_hand=6)
						],
					)
				]
			},
		)
		self.assertIn(">30.0<", message)

	def test_purchase_request_clears_source_warehouse(self):
		mr = make_material_request(
			from_warehouse="_Test Warehouse - _TC",
			warehouse="_Test Warehouse - _TC",
			do_not_submit=True,
		)

		self.assertIsNone(mr.items[0].from_warehouse)

	def test_purchase_request_ignores_customer_item_restrictions(self):
		from erpnext.selling.doctype.party_specific_item.test_party_specific_item import (
			create_party_specific_item,
		)

		create_party_specific_item(
			party_type="Customer",
			party="_Test Customer",
			restrict_based_on="Item",
			based_on_value="_Test FG Item",
		)
		mr = make_material_request(do_not_submit=True)
		mr.customer = "_Test Customer"
		mr.save()

		self.assertIsNone(mr.customer)


def create_item_with_default_supplier(item_code, supplier):
	item = create_item(item_code)
	item.set("item_defaults", [])
	item.append(
		"item_defaults",
		{
			"company": "_Test Company",
			"default_warehouse": "_Test Warehouse - _TC",
			"default_supplier": supplier,
		},
	)
	item.save()

	return item.name


def make_material_request_for_items(item_codes, **args):
	args = frappe._dict(args)
	mr = frappe.new_doc("Material Request")
	mr.material_request_type = args.material_request_type or "Purchase"
	mr.company = args.company or "_Test Company"
	mr.schedule_date = today()
	for item_code in item_codes:
		mr.append(
			"items",
			{
				"item_code": item_code,
				"qty": args.qty or 10,
				"schedule_date": today(),
				"warehouse": args.warehouse or "_Test Warehouse - _TC",
			},
		)

	mr.insert()
	mr.submit()

	return mr

>>>>>>> 0e54fc8 (test(stock): purchase request ignores customer item restrictions)

def get_in_transit_warehouse(company):
	if not frappe.db.exists("Warehouse Type", "Transit"):
		frappe.get_doc(
			{
				"doctype": "Warehouse Type",
				"name": "Transit",
			}
		).insert()

	in_transit_warehouse = frappe.db.exists("Warehouse", {"warehouse_type": "Transit", "company": company})

	if not in_transit_warehouse:
		in_transit_warehouse = (
			frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": "Transit",
					"warehouse_type": "Transit",
					"company": company,
				}
			)
			.insert()
			.name
		)

	return in_transit_warehouse


def make_material_request(**args):
	args = frappe._dict(args)
	mr = frappe.new_doc("Material Request")
	mr.material_request_type = args.material_request_type or "Purchase"
	mr.company = args.company or "_Test Company"
	if mr.material_request_type == "Customer Provided":
		mr.customer = args.customer or "_Test Customer"
	mr.append(
		"items",
		{
			"item_code": args.item_code or "_Test Item",
			"qty": args.qty or 10,
			"uom": args.uom or "_Test UOM",
			"conversion_factor": args.conversion_factor or 1,
			"schedule_date": args.schedule_date or today(),
			"from_warehouse": args.from_warehouse,
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"cost_center": args.cost_center or "_Test Cost Center - _TC",
		},
	)
	mr.insert()
	if not args.do_not_submit:
		mr.submit()
	return mr


test_dependencies = ["Currency Exchange", "BOM"]
test_records = frappe.get_test_records("Material Request")
