# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt


import frappe
from frappe import _dict
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_nos_from_bundle,
)
from erpnext.stock.doctype.serial_no.serial_no import *
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

test_dependencies = ["Item"]
test_records = frappe.get_test_records("Serial No")


class TestSerialNo(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_cannot_create_direct(self):
		frappe.delete_doc_if_exists("Serial No", "_TCSER0001")

		sr = frappe.new_doc("Serial No")
		sr.item_code = "_Test Serialized Item"
		sr.warehouse = "_Test Warehouse - _TC"
		sr.serial_no = "_TCSER0001"
		sr.purchase_rate = 10
		self.assertRaises(SerialNoCannotCreateDirectError, sr.insert)

		sr.warehouse = None
		sr.insert()
		self.assertTrue(sr.name)

		sr.warehouse = "_Test Warehouse - _TC"
		self.assertTrue(SerialNoCannotCannotChangeError, sr.save)

	def test_inter_company_transfer(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import validate_fiscal_year
		validate_fiscal_year("_Test Company 1")
		validate_fiscal_year("_Test Company")
		se = make_serialized_item(target_warehouse="_Test Warehouse - _TC")
		serial_nos = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)

		create_delivery_note(item_code="_Test Serialized Item With Series", qty=1, serial_no=[serial_nos[0]])

		serial_no = frappe.get_doc("Serial No", serial_nos[0])

		# check Serial No details after delivery
		self.assertEqual(serial_no.warehouse, None)

		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		make_purchase_receipt(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=[serial_nos[0]],
			company="_Test Company 1",
			warehouse=wh,
		)

		serial_no.reload()

		# check Serial No details after purchase in second company
		self.assertEqual(serial_no.warehouse, wh)

	def test_inter_company_transfer_intermediate_cancellation(self):
		"""
		Receive into and Deliver Serial No from one company.
		Then Receive into and Deliver from second company.
		Try to cancel intermediate receipts/deliveries to test if it is blocked.
		"""
		se = make_serialized_item(target_warehouse="_Test Warehouse - _TC")
		serial_nos = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)

		sn_doc = frappe.get_doc("Serial No", serial_nos[0])

		# check Serial No details after purchase in first company
		self.assertEqual(sn_doc.warehouse, "_Test Warehouse - _TC")

		dn = create_delivery_note(
			item_code="_Test Serialized Item With Series", qty=1, serial_no=[serial_nos[0]]
		)
		sn_doc.reload()
		# check Serial No details after delivery from **first** company
		self.assertEqual(sn_doc.warehouse, None)

		# try cancelling the first Serial No Receipt, even though it is delivered
		# block cancellation is Serial No is out of the warehouse
		self.assertRaises(frappe.ValidationError, se.cancel)

		# receive serial no in second company
		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		pr = make_purchase_receipt(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=[serial_nos[0]],
			company="_Test Company 1",
			warehouse=wh,
		)
		sn_doc.reload()

		self.assertEqual(sn_doc.warehouse, wh)
		# try cancelling the delivery from the first company
		# block cancellation as Serial No belongs to different company
		self.assertRaises(frappe.ValidationError, dn.cancel)

		# deliver from second company
		create_delivery_note(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=[serial_nos[0]],
			company="_Test Company 1",
			warehouse=wh,
		)
		sn_doc.reload()

		# check Serial No details after delivery from **second** company
		self.assertEqual(sn_doc.warehouse, None)

		# cannot cancel any intermediate document before last Delivery Note
		self.assertRaises(frappe.ValidationError, se.cancel)
		self.assertRaises(frappe.ValidationError, dn.cancel)
		self.assertRaises(frappe.ValidationError, pr.cancel)

	def test_inter_company_transfer_fallback_on_cancel(self):
		"""
		Test Serial No state changes on cancellation.
		If Delivery cancelled, it should fall back on last Receipt in the same company.
		If Receipt is cancelled, it should be Inactive in the same company.
		"""
		# Receipt in **first** company
		se = make_serialized_item(target_warehouse="_Test Warehouse - _TC")
		serial_nos = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)
		sn_doc = frappe.get_doc("Serial No", serial_nos[0])

		# Delivery from first company
		dn = create_delivery_note(
			item_code="_Test Serialized Item With Series", qty=1, serial_no=[serial_nos[0]]
		)

		# Receipt in **second** company
		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		pr = make_purchase_receipt(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=[serial_nos[0]],
			company="_Test Company 1",
			warehouse=wh,
		)

		# Delivery from second company
		dn_2 = create_delivery_note(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=[serial_nos[0]],
			company="_Test Company 1",
			warehouse=wh,
		)
		sn_doc.reload()

		self.assertEqual(sn_doc.warehouse, None)

		dn_2.cancel()
		sn_doc.reload()
		# Fallback on Purchase Receipt if Delivery is cancelled
		self.assertEqual(sn_doc.warehouse, wh)

		pr.cancel()
		sn_doc.reload()
		# Inactive in same company if Receipt cancelled
		self.assertEqual(sn_doc.warehouse, None)

		dn.cancel()
		sn_doc.reload()
		# Fallback on Purchase Receipt in FIRST company if
		# Delivery from FIRST company is cancelled
		self.assertEqual(sn_doc.warehouse, "_Test Warehouse - _TC")

	def test_correct_serial_no_incoming_rate(self):
		"""Check correct consumption rate based on serial no record."""
		item_code = "_Test Serialized Item"
		warehouse = "_Test Warehouse - _TC"
		serial_nos = ["LOWVALUATION", "HIGHVALUATION"]

		for serial_no in serial_nos:
			if not frappe.db.exists("Serial No", serial_no):
				frappe.get_doc(
					{"doctype": "Serial No", "item_code": item_code, "serial_no": serial_no}
				).insert()

		make_stock_entry(
			item_code=item_code, to_warehouse=warehouse, qty=1, rate=42, serial_no=[serial_nos[0]]
		)
		make_stock_entry(
			item_code=item_code, to_warehouse=warehouse, qty=1, rate=113, serial_no=[serial_nos[1]]
		)

		out = create_delivery_note(item_code=item_code, qty=1, serial_no=[serial_nos[0]], do_not_submit=True)

		bundle = out.items[0].serial_and_batch_bundle
		doc = frappe.get_doc("Serial and Batch Bundle", bundle)
		doc.entries[0].serial_no = serial_nos[1]
		doc.save()

		out.save()
		out.submit()

		value_diff = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": out.name, "voucher_type": "Delivery Note"},
			"stock_value_difference",
		)
		self.assertEqual(value_diff, -113)

	def test_auto_fetch(self):
		item_code = make_item(
			properties={
				"has_serial_no": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"serial_no_series": "TEST.#######",
			}
		).name
		warehouse = "_Test Warehouse - _TC"

		in1 = make_stock_entry(item_code=item_code, to_warehouse=warehouse, qty=5, rate=500)
		in2 = make_stock_entry(item_code=item_code, to_warehouse=warehouse, qty=5, rate=500)

		in1.reload()
		in2.reload()

		batch1 = get_batch_from_bundle(in1.items[0].serial_and_batch_bundle)
		batch2 = get_batch_from_bundle(in2.items[0].serial_and_batch_bundle)

		batch_wise_serials = {
			batch1: get_serial_nos_from_bundle(in1.items[0].serial_and_batch_bundle),
			batch2: get_serial_nos_from_bundle(in2.items[0].serial_and_batch_bundle),
		}

		# Test FIFO
		first_fetch = get_auto_serial_nos(
			_dict(
				{
					"qty": 5,
					"item_code": item_code,
					"warehouse": warehouse,
				}
			)
		)

		self.assertEqual(first_fetch, batch_wise_serials[batch1])

		# partial FIFO
		partial_fetch = get_auto_serial_nos(
			_dict(
				{
					"qty": 2,
					"item_code": item_code,
					"warehouse": warehouse,
				}
			)
		)

		self.assertTrue(
			set(partial_fetch).issubset(set(first_fetch)),
			msg=f"{partial_fetch} should be subset of {first_fetch}",
		)

		# exclusion
		remaining = get_auto_serial_nos(
			_dict(
				{
					"qty": 3,
					"item_code": item_code,
					"warehouse": warehouse,
					"ignore_serial_nos": partial_fetch,
				}
			)
		)

		self.assertEqual(sorted(remaining + partial_fetch), first_fetch)

		# batchwise
		for batch, expected_serials in batch_wise_serials.items():
			fetched_sr = get_auto_serial_nos(
				_dict({"qty": 5, "item_code": item_code, "warehouse": warehouse, "batches": [batch]})
			)

			self.assertEqual(fetched_sr, sorted(expected_serials))

		# non existing warehouse
		self.assertFalse(
			get_auto_serial_nos(
				_dict({"qty": 10, "item_code": item_code, "warehouse": "Non Existing Warehouse"})
			)
		)

		# multi batch
		all_serials = [sr for sr_list in batch_wise_serials.values() for sr in sr_list]
		fetched_serials = get_auto_serial_nos(
			_dict(
				{
					"qty": 10,
					"item_code": item_code,
					"warehouse": warehouse,
					"batches": list(batch_wise_serials.keys()),
				}
			)
		)
		self.assertEqual(sorted(all_serials), fetched_serials)

		# expiry date
		frappe.db.set_value("Batch", batch1, "expiry_date", "1980-01-01")
		non_expired_serials = get_auto_serial_nos(
			_dict({"qty": 5, "item_code": item_code, "warehouse": warehouse, "batches": [batch1]})
		)

		self.assertEqual(non_expired_serials, [])
  
	def test_get_pos_reserved_serial_nos_TC_ACC_302(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.item.test_item import (make_item, get_hsn)
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.buying.doctype.purchase_order.test_purchase_order import validate_fiscal_year
		create_company()
		validate_fiscal_year("_Test Company")
		warehouse = create_warehouse("_Test Warehouse", company="_Test Company")
		create_cost_center(cost_center_name="_Test Cost Center", company="_Test Company")

		item_code = "_Test Item POS"

		item = make_item(
			item_code,
			{
				"has_serial_no": 1,
				"serial_no_series": "SN-.#####",
				"is_stock_item": 1,
				"valuation_rate": 500,
				"gst_hsn_code": get_hsn(),
			}
		)
		pos_profile = frappe.get_doc({
		"doctype": "POS Profile",
		"name": "_Test POS Profile New Serial No",
		"company": "_Test Company",
		"currency": "INR",
		"write_off_cost_center": "_Test Cost Center - _TC",
		"write_off_account": "Sales - _TC",
		"warehouse": warehouse,	
		"accounts": [{
			"company": "_Test Company",
			"account": "_Test Account - _TC"  
		}],
		"payments": [{
				"default": 1,
				"mode_of_payment": "Cash",  
				"account": "Cash - _TC"
			}],
		"warehouses": [{
			"warehouse": warehouse
			}]
		})
		pos_profile.insert()

		se = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": "_Test Company",
			"items": [
				{
					"item_code": item.name,
					"qty": 1,
					"t_warehouse": warehouse
				},
				{
					"item_code": item.name,
					"qty": 1,
					"t_warehouse": warehouse
				}
			]
		})
		se.insert()
		se.submit()

		serial_nos = frappe.get_all("Serial No", filters={"item_code": item.name, "warehouse": warehouse}, fields=["name"])
		serial_no_1 = serial_nos[0].name
		pos_opening_entry = frappe.get_doc({
			"doctype": "POS Opening Entry",
			"pos_profile": pos_profile.name,
			"company": "_Test Company",
			"user": "Administrator",
			"period_start_date": frappe.utils.get_datetime(),
			"mode_of_payment": "Cash",
			"balance_details": [
				{
					"account": "Sales - _TC",
					"mode_of_payment": "Cash",
					"account_currency": "INR",
					"opening_amount": 1000
				}									
			],
			"posting_date": frappe.utils.today(),
			"cash_denominations": [
				{
					"mode_of_payment": "Cash",
					"account": "Cash - _TC",
					"opening_amount": 1000
				}
			]
		})
		pos_opening_entry.insert()
		pos_opening_entry.submit()
		pos_invoice = frappe.get_doc({
			"doctype": "POS Invoice",
			"docstatus": 1,
			"pos_profile": pos_profile.name,
			"company": "_Test Company",
			"cost_center": "_Test Cost Center - _TC",
			"is_return": 0,
			"paid_amount": 1000,
			"items": [{
				"item_code": item.name,
				"warehouse": warehouse,
				"serial_no": serial_no_1,
				"qty": 1
			}],
			"payments": [
				{
					"mode_of_payment": "Cash",
					"account": "Cash - _TC",
					"amount": 1000
				}
			]
		}).insert()

		filters = {
			"item_code": item.name,
			"warehouse": warehouse
		}

		result = get_pos_reserved_serial_nos(filters)
		self.assertIsInstance(result, list)
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0], serial_no_1)
	
	def test_auto_fetch_serial_number_basic_TC_ACC_303(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.buying.doctype.purchase_order.test_purchase_order import validate_fiscal_year

		create_company("_Test Company")
		validate_fiscal_year("_Test Company")

		if not frappe.db.exists("Supplier", "_Test Supplier Auto Fetch"):
			frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": "_Test Supplier Auto Fetch",
				"company": "_Test Company"
			}).insert(ignore_mandatory=True,ignore_permissions=True,ignore_links=True)
		if not frappe.db.exists("UOM", "_Test UOM"):
			frappe.get_doc({
				"doctype": "UOM",
				"uom_name": "_Test UOM",
				"company": "_Test Company"
			}).insert(ignore_mandatory=True,ignore_permissions=True,ignore_links=True)
		warehouse = create_warehouse("_Test Warehouse Auto Fetch", company="_Test Company")

		account = frappe.get_doc({
			"doctype": "Account",
			"account_name": "_Test Inventory Account",
			"parent_account": "Stock Assets - _TC",
			"company": "_Test Company",
			"is_group": 0,
			"account_type": "Stock"
		})
		account.insert(ignore_permissions=True)
		frappe.db.set_value("Warehouse", warehouse, "account", account.name)
	
		company = "_Test Company"
		default_inventory_account = frappe.db.get_value("Company", company, "default_inventory_account")

		if default_inventory_account != account.name:
			frappe.db.set_value("Company", company, "default_inventory_account", account.name)
   
		frappe.db.set_value("Company", company, {
			"enable_provisional_accounting_for_non_stock_items": 0,
			"enable_perpetual_inventory":0
		})
		frappe.local.enable_perpetual_inventory = {}
		frappe.local.enable_perpetual_inventory[company] = 0
		company_doc = frappe.get_doc("Company", company)
		frappe._set_document_in_cache("Company", company_doc)
		
		item = make_item("_Test Serial Item Auto", {
			"has_serial_no": 1,
			"serial_no_series": "AUTO-SERIAL-.###",
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_no_series": "AUTO-BATCH-.###",
			"valuation_rate": 100,
			"is_fixed_asset": False
		})

		pe = make_purchase_receipt(
			item_code=item.name,
			qty=2,
			supplier_warehouse=warehouse,
			company=company,
			supplier="_Test Supplier Auto Fetch",
			warehouse=warehouse
		)
		pe.submit()
		batch = frappe.get_all("Batch", {"item": item.name, "reference_name": pe.name})
		exclude_sr_nos = ["AUTO-SERIAL-001", "AUTO-SERIAL-002"]
		batch_nos = [d.name for d in batch]

		from erpnext.stock.doctype.serial_no.serial_no import auto_fetch_serial_number
		sr_nos = auto_fetch_serial_number(
			qty=2,
			item_code=item.name,
			warehouse=warehouse,
			exclude_sr_nos=exclude_sr_nos,
			batch_nos=batch_nos,
		)

		assert isinstance(sr_nos, list)
	
	def test_validate_warehouse_all_cases_TC_ACC_304(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		create_company("_Test Company")
		warehouse1 = create_warehouse("Stores", company="_Test Company")
		warehouse2 = create_warehouse("Finished Goods", company="_Test Company")
		item = make_item("_Test Item Auto", {
			"has_serial_no": 1,
			"serial_no_series": "AUTO-SERIAL-.###"
		})
		if not frappe.db.exists("UOM", "_Test UOM"):
			frappe.get_doc({
				"doctype": "UOM",
				"uom_name": "_Test UOM",
			}).insert(
				ignore_permissions=True,
				ignore_links=True,
				ignore_mandatory=True
			)
		if not frappe.db.exists("Supplier", "_Test Supplier"):
			frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": "_Test Supplier",
				"company": "_Test Company"
			}).insert(ignore_mandatory=True,ignore_permissions=True,ignore_links=True)
		pr = make_purchase_receipt(
			item_code=item.name,
			warehouse=warehouse1,
			supplier_warehouse=warehouse1,
			supplier="_Test Supplier",
			qty=1,
			rate=100,
			do_not_submit=True
		)
		pr.submit()

		serial_no = frappe.db.get_value("Serial No", {"purchase_document_no": pr.name}, "name")
		sn = frappe.get_doc("Serial No", serial_no)  

		local_sn = frappe.new_doc("Serial No")
		local_sn.__islocal = True
		local_sn.validate_warehouse() 

		sn.__islocal = False
		sn.item_code = "WRONG-ITEM"
		sn.via_stock_ledger = False
		with self.assertRaises(frappe.ValidationError) as e1:
			sn.validate_warehouse()
		self.assertIn("Item Code cannot be changed", str(e1.exception))

		sn = frappe.get_doc("Serial No", serial_no)
		sn.__islocal = False
		sn.item_code = item.name
		sn.warehouse = warehouse2
		sn.via_stock_ledger = False
		with self.assertRaises(frappe.ValidationError) as e2:
			sn.validate_warehouse()
		self.assertIn("Warehouse cannot be changed", str(e2.exception))
  
	def test_set_maintenance_status_all_cases_TC_ACC_305(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from frappe.utils import add_days, nowdate

		create_company("_Test Company")
		warehouse = create_warehouse("Stores", company="_Test Company")
		item = make_item("_Test Item Auto 1", {"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "AUTO-SERIAL-.###"})
		if not frappe.db.exists("UOM", "_Test UOM"):
			frappe.get_doc({
				"doctype": "UOM",
				"uom_name": "_Test UOM",
			}).insert(
				ignore_permissions=True,
				ignore_links=True,
				ignore_mandatory=True
			)
		if not frappe.db.exists("Supplier", "_Test Supplier"):
			frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": "_Test Supplier",
				"company": "_Test Company"
			}).insert(ignore_mandatory=True,ignore_permissions=True,ignore_links=True)
		pr = make_purchase_receipt(
			item_code=item.name,
			warehouse=warehouse,
			supplier="_Test Supplier",
			supplier_warehouse=warehouse,
			qty=1,
			rate=100,
		)
		pr.submit()

		serial_no = frappe.db.get_value("Serial No", {"purchase_document_no": pr.name}, "name")
		sn = frappe.get_doc("Serial No", serial_no)

		sn.warranty_expiry_date = None
		sn.amc_expiry_date = None
		sn.set_maintenance_status()
		self.assertIsNone(sn.maintenance_status)

		sn.warranty_expiry_date = add_days(nowdate(), -1)
		sn.amc_expiry_date = None
		sn.set_maintenance_status()
		self.assertEqual(sn.maintenance_status, "Out of Warranty")

		sn.warranty_expiry_date = None
		sn.amc_expiry_date = add_days(nowdate(), -1)
		sn.set_maintenance_status()
		self.assertEqual(sn.maintenance_status, "Out of AMC")

		sn.amc_expiry_date = add_days(nowdate(), 5)
		sn.set_maintenance_status()
		self.assertEqual(sn.maintenance_status, "Under AMC")

		sn.warranty_expiry_date = add_days(nowdate(), 5)
		sn.set_maintenance_status()
		self.assertEqual(sn.maintenance_status, "Under Warranty")
	
	def test_serial_generation_and_html_via_purchase_receipt_TC_ACC_306(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.doctype.serial_no.serial_no import (
			get_available_serial_nos,
			get_items_html,
		)
		import frappe

		create_company("_Test Company")
		warehouse = create_warehouse("Stores", company="_Test Company")
		item = make_item("_Test Item Auto 2", {
			"is_stock_item": 1,
			"has_serial_no": 1,
			"serial_no_series": "AUTO-SERIAL-.###"
		})
		if not frappe.db.exists("UOM", "_Test UOM"):
			frappe.get_doc({
				"doctype": "UOM",
				"uom_name": "_Test UOM",
			}).insert(
				ignore_permissions=True,
				ignore_links=True,
				ignore_mandatory=True
			)
		if not frappe.db.exists("Supplier", "_Test Supplier"):
			frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": "_Test Supplier",
				"company": "_Test Company"
			}).insert(ignore_mandatory=True,ignore_permissions=True,ignore_links=True)
		pr = make_purchase_receipt(
			item_code=item.name,
			warehouse=warehouse,
			supplier="_Test Supplier",
			supplier_warehouse=warehouse,
			qty=2,
			rate=100,
			do_not_submit=True  
		)
		pr.submit()

		serial_nos = frappe.get_all("Serial No", filters={"purchase_document_no": pr.name}, pluck="name")
		self.assertEqual(len(serial_nos), 2)
		
		html = get_items_html(serial_nos, item.name)
		self.assertIn(item.name, html)
		self.assertIn("Serial Numbers", html)
		for sn in serial_nos:
			self.assertIn(sn, html)

		new_serials = get_available_serial_nos("AUTO-SERIAL-.###", 2)
		self.assertEqual(len(new_serials), 2)
		for sn in new_serials:
			self.assertTrue(sn.startswith("AUTO-SERIAL-"))
			frappe.get_doc({
				"doctype": "Serial No",
				"serial_no": sn,
				"item_code": item.name
			}).insert()

		extra_html = get_items_html(new_serials, item.name)
		for sn in new_serials:
			self.assertIn(sn, extra_html)
	
	def test_update_maintenance_status_TC_ACC_307(self):
		from erpnext.stock.doctype.serial_no.serial_no import update_maintenance_status
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		create_company("_Test Company")
		warehouse = create_warehouse("Stores", company="_Test Company")

		item = make_item("_Test Item Auto 2", {
			"is_stock_item": 1,
			"has_serial_no": 1,
			"serial_no_series": "AUTO-SERIAL-.###"
		})

		if not frappe.db.exists("UOM", "_Test UOM"):
			frappe.get_doc({
				"doctype": "UOM",
				"uom_name": "_Test UOM",
			}).insert(ignore_permissions=True, ignore_links=True, ignore_mandatory=True)

		if not frappe.db.exists("Supplier", "_Test Supplier"):
			frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": "_Test Supplier",
				"company": "_Test Company"
			}).insert(ignore_mandatory=True, ignore_permissions=True, ignore_links=True)

		
		pr = make_purchase_receipt(
			item_code=item.name,
			warehouse=warehouse,
			supplier="_Test Supplier",
			supplier_warehouse=warehouse,
			qty=2,
			rate=100,
			do_not_submit=True
		)
		pr.submit()

		
		serial_nos = frappe.get_all("Serial No", filters={"item_code": item.name}, pluck="name")
		for sn in serial_nos:
			frappe.db.set_value("Serial No", sn, {
				"warranty_expiry_date": frappe.utils.add_days(frappe.utils.nowdate(), -1),
				"amc_expiry_date": frappe.utils.add_days(frappe.utils.nowdate(), -1),
				"maintenance_status": "Under AMC"
			})


		update_maintenance_status()

		for sn in serial_nos:
			updated_status = frappe.db.get_value("Serial No", sn, "maintenance_status")
			self.assertIn(updated_status, ("Out of Warranty", "Out of AMC"))
   
	def test_on_trash_with_single_qty_serial_no_TC_ACC_308(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		create_company("_Test Company")
		warehouse = create_warehouse("Stores", company="_Test Company")

		item = make_item("_Test Item Auto 2", {
			"is_stock_item": 1,
			"has_serial_no": 1,
			"serial_no_series": "AUTO-SERIAL-.###"
		})

		if not frappe.db.exists("UOM", "_Test UOM"):
			frappe.get_doc({
				"doctype": "UOM",
				"uom_name": "_Test UOM",
			}).insert(ignore_permissions=True, ignore_links=True, ignore_mandatory=True)

		if not frappe.db.exists("Supplier", "_Test Supplier"):
			frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": "_Test Supplier",
				"company": "_Test Company"
			}).insert(ignore_mandatory=True, ignore_permissions=True, ignore_links=True)

		
		pr = make_purchase_receipt(
			item_code=item.name,
			warehouse=warehouse,
			supplier="_Test Supplier",
			supplier_warehouse=warehouse,
			qty=1,
			rate=100,
			do_not_submit=True
		)
		pr.submit()
		stock_ledger = frappe.db.get_value(
		"Stock Ledger Entry",
		{
			"voucher_type": "Purchase Receipt",
			"voucher_no": pr.name,
			"voucher_detail_no":pr.items[0].name,
			"warehouse": warehouse,
			"is_cancelled": 0,
		},
		"name",
		)
		serial_nos = frappe.get_all("Serial No", filters={"purchase_document_no": pr.name}, pluck="name")
		sl_sno = frappe.db.get_value("Stock Ledger Entry",
		{
			"voucher_type": "Purchase Receipt",
			"voucher_no": pr.name,
			"voucher_detail_no":pr.items[0].name,
			"warehouse": warehouse,
			"is_cancelled": 0,
		},
		"serial_no",)
		if not sl_sno or sl_sno not in serial_nos:
			frappe.db.set_value("Stock Ledger Entry", stock_ledger, "serial_no", serial_nos[0])
		
		serial_doc = frappe.get_doc("Serial No", serial_nos[0])

		with self.assertRaises(frappe.ValidationError) as e2:
			serial_doc.on_trash()

		self.assertTrue("Cannot delete Serial No" in str(e2.exception))


def get_auto_serial_nos(kwargs):
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
		get_available_serial_nos,
	)

	serial_nos = get_available_serial_nos(kwargs)
	return sorted([d.serial_no for d in serial_nos])
