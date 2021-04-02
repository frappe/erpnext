# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe, erpnext
import frappe.defaults
from frappe.utils import cint, flt, cstr, today, random_string
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
from erpnext.stock.doctype.item.test_item import create_item
from erpnext import set_perpetual_inventory
from erpnext.stock.doctype.serial_no.serial_no import SerialNoDuplicateError
from erpnext.accounts.doctype.account.test_account import get_inventory_account
from erpnext.stock.doctype.item.test_item import make_item
from six import iteritems
class TestPurchaseReceipt(unittest.TestCase):
	def setUp(self):
		set_perpetual_inventory(0)
		frappe.db.set_value("Buying Settings", None, "allow_multiple_items", 1)

	def test_make_purchase_invoice(self):
		pr = make_purchase_receipt(do_not_save=True)
		self.assertRaises(frappe.ValidationError, make_purchase_invoice, pr.name)
		pr.submit()

		pi = make_purchase_invoice(pr.name)

		self.assertEqual(pi.doctype, "Purchase Invoice")
		self.assertEqual(len(pi.get("items")), len(pr.get("items")))

		# modify rate
		pi.get("items")[0].rate = 200
		self.assertRaises(frappe.ValidationError, frappe.get_doc(pi).submit)

	def test_purchase_receipt_no_gl_entry(self):
		company = frappe.db.get_value('Warehouse', '_Test Warehouse - _TC', 'company')

		existing_bin_stock_value = frappe.db.get_value("Bin", {"item_code": "_Test Item",
			"warehouse": "_Test Warehouse - _TC"}, "stock_value")

		pr = make_purchase_receipt()

		stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name,
				"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"}, "stock_value_difference")

		self.assertEqual(stock_value_difference, 250)

		current_bin_stock_value = frappe.db.get_value("Bin", {"item_code": "_Test Item",
			"warehouse": "_Test Warehouse - _TC"}, "stock_value")
		self.assertEqual(current_bin_stock_value, existing_bin_stock_value + 250)

		self.assertFalse(get_gl_entries("Purchase Receipt", pr.name))
	
	def test_batched_serial_no_purchase(self):
		item = frappe.db.exists("Item", {'item_name': 'Batched Serialized Item'})
		if not item:
			item = create_item("Batched Serialized Item")
			item.has_batch_no = 1
			item.create_new_batch = 1
			item.has_serial_no = 1
			item.batch_number_series = "BS-BATCH-.##"
			item.serial_no_series = "BS-.####"
			item.save()
		else:
			item = frappe.get_doc("Item", {'item_name': 'Batched Serialized Item'})

		pr = make_purchase_receipt(item_code=item.name, qty=5, rate=500)

		self.assertTrue(frappe.db.get_value('Batch', {'item': item.name, 'reference_name': pr.name}))
		
		pr.load_from_db()
		batch_no = pr.items[0].batch_no
		pr.cancel()

		self.assertFalse(frappe.db.get_value('Batch', {'item': item.name, 'reference_name': pr.name}))
		self.assertFalse(frappe.db.get_all('Serial No', {'batch_no': batch_no}))

	def test_purchase_receipt_gl_entry(self):
		pr = make_purchase_receipt(company="_Test Company with perpetual inventory", warehouse = "Stores - TCP1", supplier_warehouse = "Work in Progress - TCP1", get_multiple_items = True, get_taxes_and_charges = True)
		self.assertEqual(cint(erpnext.is_perpetual_inventory_enabled(pr.company)), 1)

		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)

		stock_in_hand_account = get_inventory_account(pr.company, pr.items[0].warehouse)
		fixed_asset_account = get_inventory_account(pr.company, pr.items[1].warehouse)

		if stock_in_hand_account == fixed_asset_account:
			expected_values = {
				stock_in_hand_account: [750.0, 0.0],
				"Stock Received But Not Billed - TCP1": [0.0, 500.0],
				"_Test Account Shipping Charges - TCP1": [0.0, 100.0],
				"_Test Account Customs Duty - TCP1": [0.0, 150.0]
			}
		else:
			expected_values = {
				stock_in_hand_account: [375.0, 0.0],
				fixed_asset_account: [375.0, 0.0],
				"Stock Received But Not Billed - TCP1": [0.0, 500.0],
				"_Test Account Shipping Charges - TCP1": [0.0, 250.0]
			}
		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.debit)
			self.assertEqual(expected_values[gle.account][1], gle.credit)

		pr.cancel()
		self.assertFalse(get_gl_entries("Purchase Receipt", pr.name))

	def test_subcontracting(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		frappe.db.set_value("Buying Settings", None, "backflush_raw_materials_of_subcontract_based_on", "BOM")
		make_stock_entry(item_code="_Test Item", target="_Test Warehouse 1 - _TC", qty=100, basic_rate=100)
		make_stock_entry(item_code="_Test Item Home Desktop 100", target="_Test Warehouse 1 - _TC",
			qty=100, basic_rate=100)
		pr = make_purchase_receipt(item_code="_Test FG Item", qty=10, rate=500, is_subcontracted="Yes")
		self.assertEqual(len(pr.get("supplied_items")), 2)

		rm_supp_cost = sum([d.amount for d in pr.get("supplied_items")])
		self.assertEqual(pr.get("items")[0].rm_supp_cost, flt(rm_supp_cost, 2))

	def test_serial_no_supplier(self):
		pr = make_purchase_receipt(item_code="_Test Serialized Item With Series", qty=1)
		self.assertEqual(frappe.db.get_value("Serial No", pr.get("items")[0].serial_no, "supplier"),
			pr.supplier)

		pr.cancel()
		self.assertFalse(frappe.db.get_value("Serial No", pr.get("items")[0].serial_no, "warehouse"))

	def test_rejected_serial_no(self):
		pr = frappe.copy_doc(test_records[0])
		pr.get("items")[0].item_code = "_Test Serialized Item With Series"
		pr.get("items")[0].qty = 3
		pr.get("items")[0].rejected_qty = 2
		pr.get("items")[0].received_qty = 5
		pr.get("items")[0].rejected_warehouse = "_Test Rejected Warehouse - _TC"
		pr.insert()
		pr.submit()

		accepted_serial_nos = pr.get("items")[0].serial_no.split("\n")
		self.assertEqual(len(accepted_serial_nos), 3)
		for serial_no in accepted_serial_nos:
			self.assertEqual(frappe.db.get_value("Serial No", serial_no, "warehouse"),
				pr.get("items")[0].warehouse)

		rejected_serial_nos = pr.get("items")[0].rejected_serial_no.split("\n")
		self.assertEqual(len(rejected_serial_nos), 2)
		for serial_no in rejected_serial_nos:
			self.assertEqual(frappe.db.get_value("Serial No", serial_no, "warehouse"),
				pr.get("items")[0].rejected_warehouse)

	def test_purchase_return(self):

		pr = make_purchase_receipt(company="_Test Company with perpetual inventory", warehouse = "Stores - TCP1", supplier_warehouse = "Work in Progress - TCP1")

		return_pr = make_purchase_receipt(company="_Test Company with perpetual inventory", warehouse = "Stores - TCP1", supplier_warehouse = "Work in Progress - TCP1", is_return=1, return_against=pr.name, qty=-2)

		# check sle
		outgoing_rate = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": return_pr.name}, "outgoing_rate")

		self.assertEqual(outgoing_rate, 50)


		# check gl entries for return
		gl_entries = get_gl_entries("Purchase Receipt", return_pr.name)

		self.assertTrue(gl_entries)
		stock_in_hand_account = get_inventory_account(return_pr.company)

		expected_values = {
			stock_in_hand_account: [0.0, 100.0],
			"Stock Received But Not Billed - TCP1": [100.0, 0.0],
		}

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.debit)
			self.assertEqual(expected_values[gle.account][1], gle.credit)


	def test_purchase_return_for_rejected_qty(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import get_warehouse

		rejected_warehouse="_Test Rejected Warehouse - TCP1"
		if not frappe.db.exists("Warehouse", rejected_warehouse):
			get_warehouse(company = "_Test Company with perpetual inventory",
				abbr = " - TCP1", warehouse_name = "_Test Rejected Warehouse").name

		pr = make_purchase_receipt(company="_Test Company with perpetual inventory", warehouse = "Stores - TCP1", supplier_warehouse = "Work in Progress - TCP1", received_qty=4, qty=2, rejected_warehouse=rejected_warehouse)

		return_pr = make_purchase_receipt(company="_Test Company with perpetual inventory", warehouse = "Stores - TCP1", supplier_warehouse = "Work in Progress - TCP1", is_return=1, return_against=pr.name, received_qty = -4, qty=-2, rejected_warehouse=rejected_warehouse)

		actual_qty = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": return_pr.name, 'warehouse': return_pr.items[0].rejected_warehouse}, "actual_qty")

		self.assertEqual(actual_qty, -2)


	def test_purchase_return_for_serialized_items(self):
		def _check_serial_no_values(serial_no, field_values):
			serial_no = frappe.get_doc("Serial No", serial_no)
			for field, value in iteritems(field_values):
				self.assertEqual(cstr(serial_no.get(field)), value)

		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		pr = make_purchase_receipt(item_code="_Test Serialized Item With Series", qty=1)

		serial_no = get_serial_nos(pr.get("items")[0].serial_no)[0]

		_check_serial_no_values(serial_no, {
			"warehouse": "_Test Warehouse - _TC",
			"purchase_document_no": pr.name
		})

		return_pr = make_purchase_receipt(item_code="_Test Serialized Item With Series", qty=-1,
			is_return=1, return_against=pr.name, serial_no=serial_no)

		_check_serial_no_values(serial_no, {
			"warehouse": "",
			"purchase_document_no": pr.name,
			"delivery_document_no": return_pr.name
		})

	def test_purchase_return_for_multi_uom(self):
		item_code = "_Test Purchase Return For Multi-UOM"
		if not frappe.db.exists('Item', item_code):
			item = make_item(item_code, {'stock_uom': 'Box'})
			row = item.append('uoms', {
				'uom': 'Unit',
				'conversion_factor': 0.1
			})
			row.db_update()

		pr = make_purchase_receipt(item_code=item_code, qty=1, uom="Box", conversion_factor=1.0)
		return_pr = make_purchase_receipt(item_code=item_code, qty=-10, uom="Unit",
			stock_uom="Box", conversion_factor=0.1, is_return=1, return_against=pr.name)

		self.assertEqual(abs(return_pr.items[0].stock_qty), 1.0)

	def test_closed_purchase_receipt(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import update_purchase_receipt_status

		pr = make_purchase_receipt(do_not_submit=True)
		pr.submit()

		update_purchase_receipt_status(pr.name, "Closed")
		self.assertEqual(frappe.db.get_value("Purchase Receipt", pr.name, "status"), "Closed")

	def test_pr_billing_status(self):
		# PO -> PR1 -> PI and PO -> PI and PO -> PR2
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.doctype.purchase_order.purchase_order \
			import make_purchase_receipt, make_purchase_invoice as make_purchase_invoice_from_po

		po = create_purchase_order()

		pr1 = make_purchase_receipt(po.name)
		pr1.posting_date = today()
		pr1.posting_time = "10:00"
		pr1.get("items")[0].received_qty = 2
		pr1.get("items")[0].qty = 2
		pr1.submit()

		pi1 = make_purchase_invoice(pr1.name)
		pi1.submit()

		pr1.load_from_db()
		self.assertEqual(pr1.per_billed, 100)

		pi2 = make_purchase_invoice_from_po(po.name)
		pi2.get("items")[0].qty = 4
		pi2.submit()

		pr2 = make_purchase_receipt(po.name)
		pr2.posting_date = today()
		pr2.posting_time = "08:00"
		pr2.get("items")[0].received_qty = 5
		pr2.get("items")[0].qty = 5
		pr2.submit()

		pr1.load_from_db()
		self.assertEqual(pr1.get("items")[0].billed_amt, 1000)
		self.assertEqual(pr1.per_billed, 100)
		self.assertEqual(pr1.status, "Completed")

		self.assertEqual(pr2.get("items")[0].billed_amt, 2000)
		self.assertEqual(pr2.per_billed, 80)
		self.assertEqual(pr2.status, "To Bill")

	def test_serial_no_against_purchase_receipt(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		item_code = "Test Manual Created Serial No"
		if not frappe.db.exists("Item", item_code):
			item = make_item(item_code, dict(has_serial_no=1))

		serial_no = "12903812901"
		pr_doc = make_purchase_receipt(item_code=item_code,
			qty=1, serial_no = serial_no)

		self.assertEqual(serial_no, frappe.db.get_value("Serial No",
			{"purchase_document_type": "Purchase Receipt", "purchase_document_no": pr_doc.name}, "name"))

		pr_doc.cancel()

		item_code = "Test Auto Created Serial No"
		if not frappe.db.exists("Item", item_code):
			item = make_item(item_code, dict(has_serial_no=1, serial_no_series="KLJL.###"))

		new_pr_doc = make_purchase_receipt(item_code=item_code, qty=1)

		serial_no = get_serial_nos(new_pr_doc.items[0].serial_no)[0]
		self.assertEqual(serial_no, frappe.db.get_value("Serial No",
			{"purchase_document_type": "Purchase Receipt", "purchase_document_no": new_pr_doc.name}, "name"))

	def test_not_accept_duplicate_serial_no(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		item_code = frappe.db.get_value('Item', {'has_serial_no': 1, 'is_fixed_asset': 0, "has_batch_no": 0})
		if not item_code:
			item = make_item("Test Serial Item 1", dict(has_serial_no=1, has_batch_no=0))
			item_code = item.name

		serial_no = random_string(5)
		make_purchase_receipt(item_code=item_code, qty=1, serial_no=serial_no)
		create_delivery_note(item_code=item_code, qty=1, serial_no=serial_no)

		pr = make_purchase_receipt(item_code=item_code, qty=1, serial_no=serial_no, do_not_submit=True)
		self.assertRaises(SerialNoDuplicateError, pr.submit)

		se = make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=1,
			serial_no=serial_no, basic_rate=100, do_not_submit=True)
		self.assertRaises(SerialNoDuplicateError, se.submit)

	def test_auto_asset_creation(self):
		asset_item = "Test Asset Item"

		if not frappe.db.exists('Item', asset_item):
			asset_category = frappe.get_all('Asset Category')

			if asset_category:
				asset_category = asset_category[0].name

			if not asset_category:
				doc = frappe.get_doc({
					'doctype': 'Asset Category',
					'asset_category_name': 'Test Asset Category',
					'depreciation_method': 'Straight Line',
					'total_number_of_depreciations': 12,
					'frequency_of_depreciation': 1,
					'accounts': [{
						'company_name': '_Test Company',
						'fixed_asset_account': '_Test Fixed Asset - _TC',
						'accumulated_depreciation_account': '_Test Accumulated Depreciations - _TC',
						'depreciation_expense_account': '_Test Depreciation - _TC'
					}]
				}).insert()

				asset_category = doc.name

			item_data = make_item(asset_item, {'is_stock_item':0,
				'stock_uom': 'Box', 'is_fixed_asset': 1, 'auto_create_assets': 1,
				'asset_category': asset_category, 'asset_naming_series': 'ABC.###'})
			asset_item = item_data.item_code

		pr = make_purchase_receipt(item_code=asset_item, qty=3)
		assets = frappe.db.get_all('Asset', filters={'purchase_receipt': pr.name})

		self.assertEquals(len(assets), 3)

		location = frappe.db.get_value('Asset', assets[0].name, 'location')
		self.assertEquals(location, "Test Location")
	
	def test_purchase_return_with_submitted_asset(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_return

		pr = make_purchase_receipt(item_code="Test Asset Item", qty=1)

		asset = frappe.get_doc("Asset", {
			'purchase_receipt': pr.name
		})
		asset.available_for_use_date = frappe.utils.nowdate()
		asset.gross_purchase_amount = 50.0
		asset.append("finance_books", {
			"expected_value_after_useful_life": 10,
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 1,
			"depreciation_start_date": frappe.utils.nowdate()
		})
		asset.submit()

		pr_return = make_purchase_return(pr.name)
		self.assertRaises(frappe.exceptions.ValidationError, pr_return.submit)
		
		asset.load_from_db()
		asset.cancel()
		
		pr_return.submit()

	def test_purchase_receipt_for_enable_allow_cost_center_in_entry_of_bs_account(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		accounts_settings = frappe.get_doc('Accounts Settings', 'Accounts Settings')
		accounts_settings.allow_cost_center_in_entry_of_bs_account = 1
		accounts_settings.save()
		cost_center = "_Test Cost Center for BS Account - TCP1"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company with perpetual inventory")

		if not frappe.db.exists('Location', 'Test Location'):
			frappe.get_doc({
				'doctype': 'Location',
				'location_name': 'Test Location'
			}).insert()

		pr = make_purchase_receipt(cost_center=cost_center, company="_Test Company with perpetual inventory", warehouse = "Stores - TCP1", supplier_warehouse = "Work in Progress - TCP1")

		stock_in_hand_account = get_inventory_account(pr.company, pr.get("items")[0].warehouse)
		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)

		expected_values = {
			"Stock Received But Not Billed - TCP1": {
				"cost_center": cost_center
			},
			stock_in_hand_account: {
				"cost_center": cost_center
			}
		}
		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

		accounts_settings.allow_cost_center_in_entry_of_bs_account = 0
		accounts_settings.save()

	def test_purchase_receipt_for_disable_allow_cost_center_in_entry_of_bs_account(self):
		accounts_settings = frappe.get_doc('Accounts Settings', 'Accounts Settings')
		accounts_settings.allow_cost_center_in_entry_of_bs_account = 0
		accounts_settings.save()

		if not frappe.db.exists('Location', 'Test Location'):
			frappe.get_doc({
				'doctype': 'Location',
				'location_name': 'Test Location'
			}).insert()
		pr = make_purchase_receipt(company="_Test Company with perpetual inventory", warehouse = "Stores - TCP1", supplier_warehouse = "Work in Progress - TCP1")

		stock_in_hand_account = get_inventory_account(pr.company, pr.get("items")[0].warehouse)
		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)

		expected_values = {
			"Stock Received But Not Billed - TCP1": {
				"cost_center": None
			},
			stock_in_hand_account: {
				"cost_center": None
			}
		}
		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_make_purchase_invoice_from_pr_for_returned_qty(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order, create_pr_against_po

		po = create_purchase_order()
		pr = create_pr_against_po(po.name)

		pr1 = make_purchase_receipt(is_return=1, return_against=pr.name, qty=-1, do_not_submit=True)
		pr1.items[0].purchase_order = po.name
		pr1.items[0].purchase_order_item = po.items[0].name
		pr1.submit()

		pi = make_purchase_invoice(pr.name)
		self.assertEquals(pi.items[0].qty, 3)

	def test_make_purchase_invoice_from_pr_with_returned_qty_duplicate_items(self):
		pr1 = make_purchase_receipt(qty=8, do_not_submit=True)
		pr1.append("items", {
			"item_code": "_Test Item",
			"warehouse": "_Test Warehouse - _TC",
			"qty": 1,
			"received_qty": 1,
			"rate": 100,
			"conversion_factor": 1.0,
		})
		pr1.submit()

		pi1 = make_purchase_invoice(pr1.name)
		pi1.items[0].qty = 4
		pi1.items.pop(1)
		pi1.save()
		pi1.submit()

		make_purchase_receipt(is_return=1, return_against=pr1.name, qty=-2)

		pi2 = make_purchase_invoice(pr1.name)
		self.assertEquals(pi2.items[0].qty, 2)
		self.assertEquals(pi2.items[1].qty, 1)

def get_gl_entries(voucher_type, voucher_no):
	return frappe.db.sql("""select account, debit, credit, cost_center
		from `tabGL Entry` where voucher_type=%s and voucher_no=%s
		order by account desc""", (voucher_type, voucher_no), as_dict=1)

def get_taxes(**args):

	args = frappe._dict(args)

	return [{'account_head': '_Test Account Shipping Charges - TCP1',
			'add_deduct_tax': 'Add',
			'category': 'Valuation and Total',
			'charge_type': 'Actual',
			'cost_center': args.cost_center or 'Main - TCP1',
			'description': 'Shipping Charges',
			'doctype': 'Purchase Taxes and Charges',
			'parentfield': 'taxes',
			'rate': 100.0,
			'tax_amount': 100.0},
		{'account_head': '_Test Account VAT - TCP1',
			'add_deduct_tax': 'Add',
			'category': 'Total',
			'charge_type': 'Actual',
			'cost_center': args.cost_center or 'Main - TCP1',
			'description': 'VAT',
			'doctype': 'Purchase Taxes and Charges',
			'parentfield': 'taxes',
			'rate': 120.0,
			'tax_amount': 120.0},
		{'account_head': '_Test Account Customs Duty - TCP1',
			'add_deduct_tax': 'Add',
			'category': 'Valuation',
			'charge_type': 'Actual',
			'cost_center': args.cost_center or 'Main - TCP1',
			'description': 'Customs Duty',
			'doctype': 'Purchase Taxes and Charges',
			'parentfield': 'taxes',
			'rate': 150.0,
			'tax_amount': 150.0}]

def get_items(**args):
	args = frappe._dict(args)
	return [{
	"base_amount": 250.0,
	"conversion_factor": 1.0,
	"description": "_Test Item",
	"doctype": "Purchase Receipt Item",
	"item_code": "_Test Item",
	"item_name": "_Test Item",
	"parentfield": "items",
	"qty": 5.0,
	"rate": 50.0,
	"received_qty": 5.0,
	"rejected_qty": 0.0,
	"stock_uom": "_Test UOM",
	"uom": "_Test UOM",
	"warehouse": args.warehouse or "_Test Warehouse - _TC",
	"cost_center": args.cost_center or "Main - _TC"
	},
	{
	"base_amount": 250.0,
	"conversion_factor": 1.0,
	"description": "_Test Item Home Desktop 100",
	"doctype": "Purchase Receipt Item",
	"item_code": "_Test Item Home Desktop 100",
	"item_name": "_Test Item Home Desktop 100",
	"parentfield": "items",
	"qty": 5.0,
	"rate": 50.0,
	"received_qty": 5.0,
	"rejected_qty": 0.0,
	"stock_uom": "_Test UOM",
	"uom": "_Test UOM",
	"warehouse": args.warehouse or "_Test Warehouse 1 - _TC",
	"cost_center": args.cost_center or "Main - _TC"
	}]

def make_purchase_receipt(**args):
	if not frappe.db.exists('Location', 'Test Location'):
		frappe.get_doc({
			'doctype': 'Location',
			'location_name': 'Test Location'
		}).insert()

	frappe.db.set_value("Buying Settings", None, "allow_multiple_items", 1)
	pr = frappe.new_doc("Purchase Receipt")
	args = frappe._dict(args)
	pr.posting_date = args.posting_date or today()
	if args.posting_time:
		pr.posting_time = args.posting_time
	pr.company = args.company or "_Test Company"
	pr.supplier = args.supplier or "_Test Supplier"
	pr.is_subcontracted = args.is_subcontracted or "No"
	pr.supplier_warehouse = args.supplier_warehouse or "_Test Warehouse 1 - _TC"
	pr.currency = args.currency or "INR"
	pr.is_return = args.is_return
	pr.return_against = args.return_against
	qty = args.qty or 5
	received_qty = args.received_qty or qty
	rejected_qty = args.rejected_qty or flt(received_qty) - flt(qty)

	item_code = args.item or args.item_code or "_Test Item"
	uom = args.uom or frappe.db.get_value("Item", item_code, "stock_uom") or "_Test UOM"
	pr.append("items", {
		"item_code": item_code,
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"qty": qty,
		"received_qty": received_qty,
		"rejected_qty": rejected_qty,
		"rejected_warehouse": args.rejected_warehouse or "_Test Rejected Warehouse - _TC" if rejected_qty != 0 else "",
		"rate": args.rate or 50,
		"conversion_factor": args.conversion_factor or 1.0,
		"serial_no": args.serial_no,
		"stock_uom": args.stock_uom or "_Test UOM",
		"uom": uom,
		"cost_center": args.cost_center or frappe.get_cached_value('Company',  pr.company,  'cost_center'),
		"asset_location": args.location or "Test Location"
	})

	if args.get_multiple_items:
		pr.items = []
		for item in get_items(warehouse= args.warehouse, cost_center = args.cost_center or frappe.get_cached_value('Company', pr.company, 'cost_center')):
			pr.append("items", item)


	if args.get_taxes_and_charges:
		for tax in get_taxes():
			pr.append("taxes", tax)

	if not args.do_not_save:
		pr.insert()
		if not args.do_not_submit:
			pr.submit()
	return pr


test_dependencies = ["BOM", "Item Price", "Location"]
test_records = frappe.get_test_records('Purchase Receipt')
