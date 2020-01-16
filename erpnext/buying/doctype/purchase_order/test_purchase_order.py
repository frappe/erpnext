# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe
import json
import frappe.defaults
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.utils import flt, add_days, nowdate, getdate
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.buying.doctype.purchase_order.purchase_order \
	import (make_purchase_receipt, make_purchase_invoice as make_pi_from_po, make_rm_stock_entry as make_subcontract_transfer_entry)
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice as make_pi_from_pr
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.controllers.accounts_controller import update_child_qty_rate
from erpnext.controllers.status_updater import OverAllowanceError

class TestPurchaseOrder(unittest.TestCase):
	def test_make_purchase_receipt(self):
		po = create_purchase_order(do_not_submit=True)
		self.assertRaises(frappe.ValidationError, make_purchase_receipt, po.name)
		po.submit()

		pr = create_pr_against_po(po.name)
		self.assertEqual(len(pr.get("items")), 1)

	def test_ordered_qty(self):
		existing_ordered_qty = get_ordered_qty()

		po = create_purchase_order(do_not_submit=True)
		self.assertRaises(frappe.ValidationError, make_purchase_receipt, po.name)

		po.submit()
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 10)

		create_pr_against_po(po.name)
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 6)

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 4)

		frappe.db.set_value('Item', '_Test Item', 'over_delivery_receipt_allowance', 50)

		pr = create_pr_against_po(po.name, received_qty=8)
		self.assertEqual(get_ordered_qty(), existing_ordered_qty)

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 12)

		pr.cancel()
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 6)

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 4)

	def test_ordered_qty_against_pi_with_update_stock(self):
		existing_ordered_qty = get_ordered_qty()
		po = create_purchase_order()

		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 10)

		frappe.db.set_value('Item', '_Test Item', 'over_delivery_receipt_allowance', 50)
		frappe.db.set_value('Item', '_Test Item', 'over_billing_allowance', 20)

		pi = make_pi_from_po(po.name)
		pi.update_stock = 1
		pi.items[0].qty = 12
		pi.insert()
		pi.submit()

		self.assertEqual(get_ordered_qty(), existing_ordered_qty)

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 12)

		pi.cancel()
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 10)

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 0)

		frappe.db.set_value('Item', '_Test Item', 'over_delivery_receipt_allowance', 0)
		frappe.db.set_value('Item', '_Test Item', 'over_billing_allowance', 0)
		frappe.db.set_value("Accounts Settings", None, "over_billing_allowance", 0)


	def test_update_child_qty_rate(self):
		mr = make_material_request(qty=10)
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.items[0].qty = 4
		po.save()
		po.submit()

		create_pr_against_po(po.name)

		make_pi_from_po(po.name)

		existing_ordered_qty = get_ordered_qty()
		existing_requested_qty = get_requested_qty()

		trans_item = json.dumps([{'item_code' : '_Test Item', 'rate' : 200, 'qty' : 7, 'docname': po.items[0].name}])
		update_child_qty_rate('Purchase Order', trans_item, po.name)

		mr.reload()
		self.assertEqual(mr.items[0].ordered_qty, 7)
		self.assertEqual(mr.per_ordered, 70)
		self.assertEqual(get_requested_qty(), existing_requested_qty - 3)

		po.reload()
		self.assertEqual(po.get("items")[0].rate, 200)
		self.assertEqual(po.get("items")[0].qty, 7)
		self.assertEqual(po.get("items")[0].amount, 1400)
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 3)

	
	def test_add_new_item_in_update_child_qty_rate(self):
		po = create_purchase_order(do_not_save=1)
		po.items[0].qty = 4
		po.save()
		po.submit()
		pr = make_pr_against_po(po.name, 2)

		po.load_from_db()
		first_item_of_po = po.get("items")[0]

		trans_item = json.dumps([
			{
				'item_code': first_item_of_po.item_code,
				'rate': first_item_of_po.rate,
				'qty': first_item_of_po.qty,
				'docname': first_item_of_po.name
			},
			{'item_code' : '_Test Item', 'rate' : 200, 'qty' : 7}
		])
		update_child_qty_rate('Purchase Order', trans_item, po.name)

		po.reload()
		self.assertEquals(len(po.get('items')), 2)
		self.assertEqual(po.status, 'To Receive and Bill')

	
	def test_remove_item_in_update_child_qty_rate(self):
		po = create_purchase_order(do_not_save=1)
		po.items[0].qty = 4
		po.save()
		po.submit()
		pr = make_pr_against_po(po.name, 2)

		po.reload()
		first_item_of_po = po.get("items")[0]
		# add an item
		trans_item = json.dumps([
			{
				'item_code': first_item_of_po.item_code,
				'rate': first_item_of_po.rate,
				'qty': first_item_of_po.qty,
				'docname': first_item_of_po.name
			},
			{'item_code' : '_Test Item', 'rate' : 200, 'qty' : 7}])
		update_child_qty_rate('Purchase Order', trans_item, po.name)

		po.reload()
		# check if can remove received item
		trans_item = json.dumps([{'item_code' : '_Test Item', 'rate' : 200, 'qty' : 7, 'docname': po.get("items")[1].name}])
		self.assertRaises(frappe.ValidationError, update_child_qty_rate, 'Purchase Order', trans_item, po.name)

		first_item_of_po = po.get("items")[0]
		trans_item = json.dumps([
			{
				'item_code': first_item_of_po.item_code,
				'rate': first_item_of_po.rate,
				'qty': first_item_of_po.qty,
				'docname': first_item_of_po.name
			}
		])
		update_child_qty_rate('Purchase Order', trans_item, po.name)

		po.reload()
		self.assertEquals(len(po.get('items')), 1)
		self.assertEqual(po.status, 'To Receive and Bill')

	def test_update_qty(self):
		po = create_purchase_order()

		pr = make_pr_against_po(po.name, 2)

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 2)

		# Check received_qty after making PI from PR without update_stock checked
		pi1 = make_pi_from_pr(pr.name)
		pi1.get("items")[0].qty = 2
		pi1.insert()
		pi1.submit()

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 2)

		# Check received_qty after making PI from PO with update_stock checked
		pi2 = make_pi_from_po(po.name)
		pi2.set("update_stock", 1)
		pi2.get("items")[0].qty = 3
		pi2.insert()
		pi2.submit()

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 5)

		# Check received_qty after making PR from PO
		pr = make_pr_against_po(po.name, 1)

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 6)



	def test_return_against_purchase_order(self):
		po = create_purchase_order()

		pr = make_pr_against_po(po.name, 6)

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 6)

		pi2 = make_pi_from_po(po.name)
		pi2.set("update_stock", 1)
		pi2.get("items")[0].qty = 3
		pi2.insert()
		pi2.submit()

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 9)

		# Make return purchase receipt, purchase invoice and check quantity
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt \
				import make_purchase_receipt as make_purchase_receipt_return
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice \
				import make_purchase_invoice as make_purchase_invoice_return

		pr1 = make_purchase_receipt_return(is_return=1, return_against=pr.name, qty=-3, do_not_submit=True)
		pr1.items[0].purchase_order = po.name
		pr1.items[0].purchase_order_item = po.items[0].name
		pr1.submit()

		pi1= make_purchase_invoice_return(is_return=1, return_against=pi2.name, qty=-1, update_stock=1, do_not_submit=True)
		pi1.items[0].purchase_order = po.name
		pi1.items[0].po_detail = po.items[0].name
		pi1.submit()


		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 5)

	def test_make_purchase_invoice(self):
		po = create_purchase_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_pi_from_po, po.name)

		po.submit()
		pi = make_pi_from_po(po.name)

		self.assertEqual(pi.doctype, "Purchase Invoice")
		self.assertEqual(len(pi.get("items", [])), 1)

	def test_purchase_order_on_hold(self):
		po = create_purchase_order(item_code="_Test Product Bundle Item")
		po.db_set('Status', "On Hold")
		pi = make_pi_from_po(po.name)
		pr = make_purchase_receipt(po.name)
		self.assertRaises(frappe.ValidationError, pr.submit)
		self.assertRaises(frappe.ValidationError, pi.submit)


	def test_make_purchase_invoice_with_terms(self):
		po = create_purchase_order(do_not_save=True)

		self.assertRaises(frappe.ValidationError, make_pi_from_po, po.name)

		po.update(
			{"payment_terms_template": "_Test Payment Term Template"}
		)

		po.save()
		po.submit()

		self.assertEqual(po.payment_schedule[0].payment_amount, 2500.0)
		self.assertEqual(getdate(po.payment_schedule[0].due_date), getdate(po.transaction_date))
		self.assertEqual(po.payment_schedule[1].payment_amount, 2500.0)
		self.assertEqual(getdate(po.payment_schedule[1].due_date), add_days(getdate(po.transaction_date), 30))
		pi = make_pi_from_po(po.name)
		pi.save()

		self.assertEqual(pi.doctype, "Purchase Invoice")
		self.assertEqual(len(pi.get("items", [])), 1)

		self.assertEqual(pi.payment_schedule[0].payment_amount, 2500.0)
		self.assertEqual(getdate(pi.payment_schedule[0].due_date), getdate(po.transaction_date))
		self.assertEqual(pi.payment_schedule[1].payment_amount, 2500.0)
		self.assertEqual(getdate(pi.payment_schedule[1].due_date), add_days(getdate(po.transaction_date), 30))

	def test_subcontracting(self):
		po = create_purchase_order(item_code="_Test FG Item", is_subcontracted="Yes")
		self.assertEqual(len(po.get("supplied_items")), 2)

	def test_warehouse_company_validation(self):
		from erpnext.stock.utils import InvalidWarehouseCompany
		po = create_purchase_order(company="_Test Company 1", do_not_save=True)
		self.assertRaises(InvalidWarehouseCompany, po.insert)

	def test_uom_integer_validation(self):
		from erpnext.utilities.transaction_base import UOMMustBeIntegerError
		po = create_purchase_order(qty=3.4, do_not_save=True)
		self.assertRaises(UOMMustBeIntegerError, po.insert)

	def test_ordered_qty_for_closing_po(self):
		bin = frappe.get_all("Bin", filters={"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			fields=["ordered_qty"])

		existing_ordered_qty = bin[0].ordered_qty if bin else 0.0

		po = create_purchase_order(item_code= "_Test Item", qty=1)

		self.assertEqual(get_ordered_qty(item_code= "_Test Item", warehouse="_Test Warehouse - _TC"), existing_ordered_qty+1)

		po.update_status("Closed")

		self.assertEqual(get_ordered_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"), existing_ordered_qty)

	def test_group_same_items(self):
		frappe.db.set_value("Buying Settings", None, "allow_multiple_items", 1)
		frappe.get_doc({
			"doctype": "Purchase Order",
			"company": "_Test Company",
			"supplier" : "_Test Supplier",
			"is_subcontracted" : "No",
			"schedule_date": add_days(nowdate(), 1),
			"currency" : frappe.get_cached_value('Company',  "_Test Company",  "default_currency"),
			"conversion_factor" : 1,
			"items" : get_same_items(),
			"group_same_items": 1
			}).insert(ignore_permissions=True)

	def test_make_po_without_terms(self):
		po = create_purchase_order(do_not_save=1)

		self.assertFalse(po.get('payment_schedule'))

		po.insert()

		self.assertTrue(po.get('payment_schedule'))

	def test_po_for_blocked_supplier_all(self):
		supplier = frappe.get_doc('Supplier', '_Test Supplier')
		supplier.on_hold = 1
		supplier.save()

		self.assertEqual(supplier.hold_type, 'All')
		self.assertRaises(frappe.ValidationError, create_purchase_order)

		supplier.on_hold = 0
		supplier.save()

	def test_po_for_blocked_supplier_invoices(self):
		supplier = frappe.get_doc('Supplier', '_Test Supplier')
		supplier.on_hold = 1
		supplier.hold_type = 'Invoices'
		supplier.save()

		self.assertRaises(frappe.ValidationError, create_purchase_order)

		supplier.on_hold = 0
		supplier.save()

	def test_po_for_blocked_supplier_payments(self):
		supplier = frappe.get_doc('Supplier', '_Test Supplier')
		supplier.on_hold = 1
		supplier.hold_type = 'Payments'
		supplier.save()

		po = create_purchase_order()

		self.assertRaises(
			frappe.ValidationError, get_payment_entry, dt='Purchase Order', dn=po.name, bank_account="_Test Bank - _TC")

		supplier.on_hold = 0
		supplier.save()

	def test_po_for_blocked_supplier_payments_with_today_date(self):
		supplier = frappe.get_doc('Supplier', '_Test Supplier')
		supplier.on_hold = 1
		supplier.release_date = nowdate()
		supplier.hold_type = 'Payments'
		supplier.save()

		po = create_purchase_order()

		self.assertRaises(
			frappe.ValidationError, get_payment_entry, dt='Purchase Order', dn=po.name, bank_account="_Test Bank - _TC")

		supplier.on_hold = 0
		supplier.save()

	def test_po_for_blocked_supplier_payments_past_date(self):
		# this test is meant to fail only if something fails in the try block
		with self.assertRaises(Exception):
			try:
				supplier = frappe.get_doc('Supplier', '_Test Supplier')
				supplier.on_hold = 1
				supplier.hold_type = 'Payments'
				supplier.release_date = '2018-03-01'
				supplier.save()

				po = create_purchase_order()
				get_payment_entry('Purchase Order', po.name, bank_account='_Test Bank - _TC')

				supplier.on_hold = 0
				supplier.save()
			except:
				pass
			else:
				raise Exception

	def test_terms_does_not_copy(self):
		po = create_purchase_order()

		self.assertTrue(po.get('payment_schedule'))

		pi = make_pi_from_po(po.name)

		self.assertFalse(pi.get('payment_schedule'))

	def test_terms_copied(self):
		po = create_purchase_order(do_not_save=1)
		po.payment_terms_template = '_Test Payment Term Template'
		po.insert()
		po.submit()
		self.assertTrue(po.get('payment_schedule'))

		pi = make_pi_from_po(po.name)
		pi.insert()
		self.assertTrue(pi.get('payment_schedule'))

	def test_reserved_qty_subcontract_po(self):
		# Make stock available for raw materials
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100)
		make_stock_entry(target="_Test Warehouse - _TC", item_code="_Test Item Home Desktop 100",
			qty=20, basic_rate=100)
		make_stock_entry(target="_Test Warehouse 1 - _TC", item_code="_Test Item",
			qty=30, basic_rate=100)
		make_stock_entry(target="_Test Warehouse 1 - _TC", item_code="_Test Item Home Desktop 100",
			qty=30, basic_rate=100)

		bin1 = frappe.db.get_value("Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname=["reserved_qty_for_sub_contract", "projected_qty"], as_dict=1)

		# Submit PO
		po = create_purchase_order(item_code="_Test FG Item", is_subcontracted="Yes")

		bin2 = frappe.db.get_value("Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname=["reserved_qty_for_sub_contract", "projected_qty"], as_dict=1)

		self.assertEquals(bin2.reserved_qty_for_sub_contract, bin1.reserved_qty_for_sub_contract + 10)
		self.assertEquals(bin2.projected_qty, bin1.projected_qty - 10)

		# Create stock transfer
		rm_item = [{"item_code":"_Test FG Item","rm_item_code":"_Test Item","item_name":"_Test Item",
					"qty":6,"warehouse":"_Test Warehouse - _TC","rate":100,"amount":600,"stock_uom":"Nos"}]
		rm_item_string = json.dumps(rm_item)
		se = frappe.get_doc(make_subcontract_transfer_entry(po.name, rm_item_string))
		se.to_warehouse = "_Test Warehouse 1 - _TC"
		se.save()
		se.submit()

		bin3 = frappe.db.get_value("Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract", as_dict=1)

		self.assertEquals(bin3.reserved_qty_for_sub_contract, bin2.reserved_qty_for_sub_contract - 6)

		# close PO
		po.update_status("Closed")
		bin4 = frappe.db.get_value("Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract", as_dict=1)

		self.assertEquals(bin4.reserved_qty_for_sub_contract, bin1.reserved_qty_for_sub_contract)

		# Re-open PO
		po.update_status("Submitted")
		bin5 = frappe.db.get_value("Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract", as_dict=1)

		self.assertEquals(bin5.reserved_qty_for_sub_contract, bin2.reserved_qty_for_sub_contract - 6)

		make_stock_entry(target="_Test Warehouse 1 - _TC", item_code="_Test Item",
			qty=40, basic_rate=100)
		make_stock_entry(target="_Test Warehouse 1 - _TC", item_code="_Test Item Home Desktop 100",
			qty=40, basic_rate=100)

		# make Purchase Receipt against PO
		pr = make_purchase_receipt(po.name)
		pr.supplier_warehouse = "_Test Warehouse 1 - _TC"
		pr.save()
		pr.submit()

		bin6 = frappe.db.get_value("Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract", as_dict=1)

		self.assertEquals(bin6.reserved_qty_for_sub_contract, bin1.reserved_qty_for_sub_contract)

		# Cancel PR
		pr.cancel()
		bin7 = frappe.db.get_value("Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract", as_dict=1)

		self.assertEquals(bin7.reserved_qty_for_sub_contract, bin2.reserved_qty_for_sub_contract - 6)

		# Make Purchase Invoice
		pi = make_pi_from_po(po.name)
		pi.update_stock = 1
		pi.supplier_warehouse = "_Test Warehouse 1 - _TC"
		pi.insert()
		pi.submit()
		bin8 = frappe.db.get_value("Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract", as_dict=1)

		self.assertEquals(bin8.reserved_qty_for_sub_contract, bin1.reserved_qty_for_sub_contract)

		# Cancel PR
		pi.cancel()
		bin9 = frappe.db.get_value("Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract", as_dict=1)

		self.assertEquals(bin9.reserved_qty_for_sub_contract, bin2.reserved_qty_for_sub_contract - 6)

		# Cancel Stock Entry
		se.cancel()
		bin10 = frappe.db.get_value("Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract", as_dict=1)

		self.assertEquals(bin10.reserved_qty_for_sub_contract, bin1.reserved_qty_for_sub_contract + 10)

		# Cancel PO
		po.reload()
		po.cancel()
		bin11 = frappe.db.get_value("Bin",
			filters={"warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			fieldname="reserved_qty_for_sub_contract", as_dict=1)

		self.assertEquals(bin11.reserved_qty_for_sub_contract, bin1.reserved_qty_for_sub_contract)

	def test_exploded_items_in_subcontracted(self):
		item_code = "_Test Subcontracted FG Item 1"
		make_subcontracted_item(item_code)

		po = create_purchase_order(item_code=item_code, qty=1,
			is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC")

		name = frappe.db.get_value('BOM', {'item': item_code}, 'name')
		bom = frappe.get_doc('BOM', name)

		exploded_items = sorted([d.item_code for d in bom.exploded_items])
		supplied_items = sorted([d.rm_item_code for d in po.supplied_items])
		self.assertEquals(exploded_items, supplied_items)

		po1 = create_purchase_order(item_code=item_code, qty=1,
			is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC", include_exploded_items=0)

		supplied_items1 = sorted([d.rm_item_code for d in po1.supplied_items])
		bom_items = sorted([d.item_code for d in bom.items])

		self.assertEquals(supplied_items1, bom_items)

	def test_backflush_based_on_stock_entry(self):
		item_code = "_Test Subcontracted FG Item 1"
		make_subcontracted_item(item_code)
		make_item('Sub Contracted Raw Material 1', {
			'is_stock_item': 1,
			'is_sub_contracted_item': 1
		})

		update_backflush_based_on("Material Transferred for Subcontract")

		order_qty = 5
		po = create_purchase_order(item_code=item_code, qty=order_qty,
			is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC")

		make_stock_entry(target="_Test Warehouse - _TC",
			item_code="_Test Item Home Desktop 100", qty=10, basic_rate=100)
		make_stock_entry(target="_Test Warehouse - _TC",
			item_code = "Test Extra Item 1", qty=100, basic_rate=100)
		make_stock_entry(target="_Test Warehouse - _TC",
			item_code = "Test Extra Item 2", qty=10, basic_rate=100)
		make_stock_entry(target="_Test Warehouse - _TC",
			item_code = "Sub Contracted Raw Material 1", qty=10, basic_rate=100)

		rm_items = [
			{"item_code":item_code,"rm_item_code":"Sub Contracted Raw Material 1","item_name":"_Test Item",
				"qty":10,"warehouse":"_Test Warehouse - _TC", "stock_uom":"Nos"},
			{"item_code":item_code,"rm_item_code":"_Test Item Home Desktop 100","item_name":"_Test Item Home Desktop 100",
				"qty":20,"warehouse":"_Test Warehouse - _TC", "stock_uom":"Nos"},
			{"item_code":item_code,"rm_item_code":"Test Extra Item 1","item_name":"Test Extra Item 1",
				"qty":10,"warehouse":"_Test Warehouse - _TC", "stock_uom":"Nos"},
			{'item_code': item_code, 'rm_item_code': 'Test Extra Item 2', 'stock_uom':'Nos',
				'qty': 10, 'warehouse': '_Test Warehouse - _TC', 'item_name':'Test Extra Item 2'}]

		rm_item_string = json.dumps(rm_items)
		se = frappe.get_doc(make_subcontract_transfer_entry(po.name, rm_item_string))
		se.submit()

		pr = make_purchase_receipt(po.name)

		received_qty = 2
		# partial receipt
		pr.get('items')[0].qty = received_qty
		pr.save()
		pr.submit()

		transferred_items = sorted([d.item_code for d in se.get('items') if se.purchase_order == po.name])
		issued_items = sorted([d.rm_item_code for d in pr.get('supplied_items')])

		self.assertEquals(transferred_items, issued_items)
		self.assertEquals(pr.get('items')[0].rm_supp_cost, 2000)


		transferred_rm_map = frappe._dict()
		for item in rm_items:
			transferred_rm_map[item.get('rm_item_code')] = item

		for item in pr.get('supplied_items'):
			self.assertEqual(item.get('required_qty'), (transferred_rm_map[item.get('rm_item_code')].get('qty') / order_qty) * received_qty)

		update_backflush_based_on("BOM")

	def test_advance_payment_entry_unlink_against_purchase_order(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
		frappe.db.set_value("Accounts Settings", "Accounts Settings",
			"unlink_advance_payment_on_cancelation_of_order", 1)

		po_doc = create_purchase_order()

		pe = get_payment_entry("Purchase Order", po_doc.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = po_doc.currency
		pe.paid_to_account_currency = po_doc.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = po_doc.grand_total
		pe.save(ignore_permissions=True)
		pe.submit()

		po_doc = frappe.get_doc('Purchase Order', po_doc.name)
		po_doc.cancel()

		pe_doc = frappe.get_doc('Payment Entry', pe.name)
		pe_doc.cancel()

		frappe.db.set_value("Accounts Settings", "Accounts Settings",
			"unlink_advance_payment_on_cancelation_of_order", 0)

	def test_schedule_date(self):
		po = create_purchase_order(do_not_submit=True)
		po.schedule_date = None
		po.append("items", {
			"item_code": "_Test Item",
			"qty": 1,
			"rate": 100,
			"schedule_date": add_days(nowdate(), 5)
		})
		po.save()
		self.assertEqual(po.schedule_date, add_days(nowdate(), 1))

		po.items[0].schedule_date = add_days(nowdate(), 2)
		po.save()
		self.assertEqual(po.schedule_date, add_days(nowdate(), 2))


def make_pr_against_po(po, received_qty=0):
	pr = make_purchase_receipt(po)
	pr.get("items")[0].qty = received_qty or 5
	pr.insert()
	pr.submit()
	return pr

def make_subcontracted_item(item_code):
	from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

	if not frappe.db.exists('Item', item_code):
		make_item(item_code, {
			'is_stock_item': 1,
			'is_sub_contracted_item': 1
		})

	if not frappe.db.exists('Item', "Test Extra Item 1"):
		make_item("Test Extra Item 1", {
			'is_stock_item': 1,
		})

	if not frappe.db.exists('Item', "Test Extra Item 2"):
		make_item("Test Extra Item 2", {
			'is_stock_item': 1,
		})

	if not frappe.db.get_value('BOM', {'item': item_code}, 'name'):
		make_bom(item = item_code, raw_materials = ['_Test FG Item', 'Test Extra Item 1'])

def update_backflush_based_on(based_on):
	doc = frappe.get_doc('Buying Settings')
	doc.backflush_raw_materials_of_subcontract_based_on = based_on
	doc.save()

def get_same_items():
	return [
		{
			"item_code": "_Test FG Item",
			"warehouse": "_Test Warehouse - _TC",
			"qty": 1,
			"rate": 500,
			"schedule_date": add_days(nowdate(), 1)
		},
		{
			"item_code": "_Test FG Item",
			"warehouse": "_Test Warehouse - _TC",
			"qty": 4,
			"rate": 500,
			"schedule_date": add_days(nowdate(), 1)
		}
	]

def create_purchase_order(**args):
	po = frappe.new_doc("Purchase Order")
	args = frappe._dict(args)
	if args.transaction_date:
		po.transaction_date = args.transaction_date

	po.schedule_date = add_days(nowdate(), 1)
	po.company = args.company or "_Test Company"
	po.supplier = args.customer or "_Test Supplier"
	po.is_subcontracted = args.is_subcontracted or "No"
	po.currency = args.currency or frappe.get_cached_value('Company',  po.company,  "default_currency")
	po.conversion_factor = args.conversion_factor or 1
	po.supplier_warehouse = args.supplier_warehouse or None

	po.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"qty": args.qty or 10,
		"rate": args.rate or 500,
		"schedule_date": add_days(nowdate(), 1),
		"include_exploded_items": args.get('include_exploded_items', 1)
	})
	if not args.do_not_save:
		po.insert()
		if not args.do_not_submit:
			if po.is_subcontracted == "Yes":
				supp_items = po.get("supplied_items")
				for d in supp_items:
					d.reserve_warehouse = args.warehouse or "_Test Warehouse - _TC"
			po.submit()

	return po

def create_pr_against_po(po, received_qty=4):
	pr = make_purchase_receipt(po)
	pr.get("items")[0].qty = received_qty
	pr.insert()
	pr.submit()
	return pr

def get_ordered_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"):
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse},
		"ordered_qty"))

def get_requested_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"):
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse},
		"indented_qty"))

test_dependencies = ["BOM", "Item Price"]

test_records = frappe.get_test_records('Purchase Order')
