# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe
import frappe.defaults
from frappe.utils import flt, add_days, nowdate
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt, make_purchase_invoice

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
			"currency" : frappe.db.get_value("Company", "_Test Company", "default_currency"),
			"conversion_factor" : 1,
			"items" : get_same_items(),
			"group_same_items": 1
			}).insert(ignore_permissions=True)

		
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
