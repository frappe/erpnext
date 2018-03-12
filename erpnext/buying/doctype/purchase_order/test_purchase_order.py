# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe
import frappe.defaults
from frappe.utils import flt, add_days, nowdate
from erpnext.buying.doctype.purchase_order.purchase_order import (make_purchase_receipt, make_purchase_invoice, make_rm_stock_entry as make_subcontract_transfer_entry)
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
import json

class TestPurchaseOrder(unittest.TestCase):
	def test_make_purchase_receipt(self):
		po = create_purchase_order(do_not_submit=True)
		self.assertRaises(frappe.ValidationError, make_purchase_receipt, po.name)
		po.submit()

		pr = create_pr_against_po(po.name)
		self.assertEquals(len(pr.get("items")), 1)

	def test_ordered_qty(self):
		existing_ordered_qty = get_ordered_qty()

		po = create_purchase_order(do_not_submit=True)
		self.assertRaises(frappe.ValidationError, make_purchase_receipt, po.name)

		po.submit()
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 10)

		create_pr_against_po(po.name)
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 6)

		po.load_from_db()
		self.assertEquals(po.get("items")[0].received_qty, 4)

		frappe.db.set_value('Item', '_Test Item', 'tolerance', 50)

		pr = create_pr_against_po(po.name, received_qty=8)
		self.assertEqual(get_ordered_qty(), existing_ordered_qty)

		po.load_from_db()
		self.assertEquals(po.get("items")[0].received_qty, 12)

		pr.cancel()
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 6)

		po.load_from_db()
		self.assertEquals(po.get("items")[0].received_qty, 4)
		
	def test_ordered_qty_against_pi_with_update_stock(self):
		existing_ordered_qty = get_ordered_qty()

		po = create_purchase_order()
		
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 10)

		frappe.db.set_value('Item', '_Test Item', 'tolerance', 50)

		pi = make_purchase_invoice(po.name)
		pi.update_stock = 1
		pi.items[0].qty = 12
		pi.insert()
		pi.submit()
		
		self.assertEqual(get_ordered_qty(), existing_ordered_qty)

		po.load_from_db()
		self.assertEquals(po.get("items")[0].received_qty, 12)

		pi.cancel()
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 10)

		po.load_from_db()
		self.assertEquals(po.get("items")[0].received_qty, 0)

	def test_make_purchase_invoice(self):
		po = create_purchase_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_purchase_invoice, po.name)

		po.submit()
		pi = make_purchase_invoice(po.name)

		self.assertEquals(pi.doctype, "Purchase Invoice")
		self.assertEquals(len(pi.get("items", [])), 1)

	def test_make_purchase_invoice_with_terms(self):
		po = create_purchase_order(do_not_save=True)

		self.assertRaises(frappe.ValidationError, make_purchase_invoice, po.name)

		po.update(
			{"payment_terms_template": "_Test Payment Term Template"}
		)

		po.save()
		po.submit()

		self.assertEqual(po.payment_schedule[0].payment_amount, 2500.0)
		self.assertEqual(po.payment_schedule[0].due_date, po.transaction_date)
		self.assertEqual(po.payment_schedule[1].payment_amount, 2500.0)
		self.assertEqual(po.payment_schedule[1].due_date, add_days(po.transaction_date, 30))
		pi = make_purchase_invoice(po.name)
		pi.save()

		self.assertEquals(pi.doctype, "Purchase Invoice")
		self.assertEquals(len(pi.get("items", [])), 1)

		self.assertEqual(pi.payment_schedule[0].payment_amount, 2500.0)
		self.assertEqual(pi.payment_schedule[0].due_date, po.transaction_date)
		self.assertEqual(pi.payment_schedule[1].payment_amount, 2500.0)
		self.assertEqual(pi.payment_schedule[1].due_date, add_days(po.transaction_date, 30))

	def test_subcontracting(self):
		po = create_purchase_order(item_code="_Test FG Item", is_subcontracted="Yes")
		self.assertEquals(len(po.get("supplied_items")), 2)

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

		self.assertEquals(get_ordered_qty(item_code= "_Test Item", warehouse="_Test Warehouse - _TC"), existing_ordered_qty+1)

		po.update_status("Closed")

		self.assertEquals(get_ordered_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"), existing_ordered_qty)
		
	def test_group_same_items(self):
		frappe.db.set_value("Buying Settings", None, "allow_multiple_items", 1)
		frappe.get_doc({
			"doctype": "Purchase Order",
			"company": "_Test Company",
			"supplier" : "_Test Supplier",
			"is_subcontracted" : "No",
			"schedule_date": add_days(nowdate(), 1),
			"currency" : frappe.db.get_value("Company", "_Test Company", "default_currency"),
			"conversion_factor" : 1,
			"items" : get_same_items(),
			"group_same_items": 1
			}).insert(ignore_permissions=True)

	def test_make_po_without_terms(self):
		po = create_purchase_order(do_not_save=1)

		self.assertFalse(po.get('payment_schedule'))

		po.insert()

		self.assertTrue(po.get('payment_schedule'))

	def test_terms_does_not_copy(self):
		po = create_purchase_order()

		self.assertTrue(po.get('payment_schedule'))

		pi = make_purchase_invoice(po.name)

		self.assertFalse(pi.get('payment_schedule'))

	def test_terms_copied(self):
		po = create_purchase_order(do_not_save=1)
		po.payment_terms_template = '_Test Payment Term Template'
		po.insert()
		po.submit()
		self.assertTrue(po.get('payment_schedule'))

		pi = make_purchase_invoice(po.name)
		pi.insert()
		self.assertTrue(pi.get('payment_schedule'))

	def test_reserved_qty_subcontract_po(self):
		# Make stock available for raw materials
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100)
		make_stock_entry(target="_Test Warehouse - _TC", item_code="_Test Item Home Desktop 100",
			qty=20, basic_rate=100)

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
		pi = make_purchase_invoice(po.name)
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
	po.currency = args.currency or frappe.db.get_value("Company", po.company, "default_currency")
	po.conversion_factor = args.conversion_factor or 1

	po.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"qty": args.qty or 10,
		"rate": args.rate or 500,
		"schedule_date": add_days(nowdate(), 1)
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

test_dependencies = ["BOM", "Item Price"]

test_records = frappe.get_test_records('Purchase Order')
