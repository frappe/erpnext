# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
import random
from datetime import date
from io import BytesIO

import frappe
from frappe.query_builder import DocType

# import pandas as pd
from frappe.tests.utils import FrappeTestCase, change_settings, if_app_installed
from frappe.utils import add_days, add_years, flt, get_year_ending, get_year_start, getdate, nowdate, today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
	create_company_and_supplier as create_data,
)
from erpnext.accounts.doctype.shipping_rule.test_shipping_rule import create_shipping_rule
from erpnext.accounts.party import get_due_date_from_template
from erpnext.buying.doctype.purchase_order.purchase_order import (
	make_inter_company_sales_order,
	make_purchase_receipt,
)
from erpnext.buying.doctype.purchase_order.purchase_order import (
	make_purchase_invoice as make_pi_from_po,
)
from erpnext.buying.doctype.purchase_order.purchase_order import (
	make_purchase_receipt as make_purchase_receipt_aganist_mr,
)
from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
	make_supplier_quotation_from_rfq,
)
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.buying.doctype.supplier_quotation.supplier_quotation import (
	make_purchase_order as create_po_aganist_sq,
)
from erpnext.controllers.accounts_controller import InvalidQtyError, update_child_qty_rate
from erpnext.stock.doctype.item.test_item import create_item, make_item
from erpnext.stock.doctype.material_request.material_request import (
	make_purchase_order,
	make_request_for_quotation,
	make_stock_entry,
	make_supplier_quotation,
	raise_work_orders,
)
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
	make_purchase_invoice as make_pi_from_pr,
)
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.utils import get_or_create_fiscal_year


class TestPurchaseOrder(FrappeTestCase):
	def test_purchase_order_qty(self):
		po = create_purchase_order(qty=1, do_not_save=True)

		# NonNegativeError with qty=-1
		po.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": -1,
				"rate": 10,
			},
		)
		self.assertRaises(frappe.NonNegativeError, po.save)

		# InvalidQtyError with qty=0
		po.items[1].qty = 0
		self.assertRaises(InvalidQtyError, po.save)

		# No error with qty=1
		po.items[1].qty = 1
		po.save()
		self.assertEqual(po.items[1].qty, 1)

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

		frappe.db.set_value("Item", "_Test Item", "over_delivery_receipt_allowance", 50)

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

		frappe.db.set_value("Item", "_Test Item", "over_delivery_receipt_allowance", 50)
		frappe.db.set_value("Item", "_Test Item", "over_billing_allowance", 20)

		pi = make_pi_from_po(po.name)
		pi.update_stock = 1
		pi.items[0].qty = 12
		pi.insert(ignore_permissions=True)
		pi.submit()

		self.assertEqual(get_ordered_qty(), existing_ordered_qty)

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 12)

		pi.cancel()
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 10)

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 0)

		frappe.db.set_value("Item", "_Test Item", "over_delivery_receipt_allowance", 0)
		frappe.db.set_value("Item", "_Test Item", "over_billing_allowance", 0)
		frappe.db.set_single_value("Accounts Settings", "over_billing_allowance", 0)

	def test_update_remove_child_linked_to_mr(self):
		"""Test impact on linked PO and MR on deleting/updating row."""
		mr = make_material_request(qty=10)
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.save()
		po.submit()

		first_item_of_po = po.get("items")[0]
		existing_ordered_qty = get_ordered_qty()  # 10
		existing_requested_qty = get_requested_qty()  # 0

		# decrease ordered qty by 3 (10 -> 7) and add item
		trans_item = json.dumps(
			[
				{
					"item_code": first_item_of_po.item_code,
					"rate": first_item_of_po.rate,
					"qty": 7,
					"docname": first_item_of_po.name,
				},
				{"item_code": "_Test Item 2", "rate": 200, "qty": 2},
			]
		)
		update_child_qty_rate("Purchase Order", trans_item, po.name)
		mr.reload()

		# requested qty increases as ordered qty decreases
		self.assertEqual(get_requested_qty(), existing_requested_qty + 3)  # 3
		self.assertEqual(mr.items[0].ordered_qty, 7)

		self.assertEqual(get_ordered_qty(), existing_ordered_qty - 3)  # 7

		# delete first item linked to Material Request
		trans_item = json.dumps([{"item_code": "_Test Item 2", "rate": 200, "qty": 2}])
		update_child_qty_rate("Purchase Order", trans_item, po.name)
		mr.reload()

		# requested qty increases as ordered qty is 0 (deleted row)
		self.assertEqual(get_requested_qty(), existing_requested_qty + 10)  # 10
		self.assertEqual(mr.items[0].ordered_qty, 0)

		# ordered qty decreases as ordered qty is 0 (deleted row)
		self.assertEqual(get_ordered_qty(), existing_ordered_qty - 10)  # 0

	def test_update_child(self):
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

		trans_item = json.dumps(
			[{"item_code": "_Test Item", "rate": 200, "qty": 7, "docname": po.items[0].name}]
		)
		update_child_qty_rate("Purchase Order", trans_item, po.name)

		mr.reload()
		self.assertEqual(mr.items[0].ordered_qty, 7)
		self.assertEqual(mr.per_ordered, 70)
		self.assertEqual(get_requested_qty(), existing_requested_qty - 3)

		po.reload()
		self.assertEqual(po.get("items")[0].rate, 200)
		self.assertEqual(po.get("items")[0].qty, 7)
		self.assertEqual(po.get("items")[0].amount, 1400)
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 3)

	def test_update_child_adding_new_item(self):
		po = create_purchase_order(do_not_save=1)
		po.items[0].qty = 4
		po.save()
		po.submit()
		make_pr_against_po(po.name, 2)

		po.load_from_db()
		existing_ordered_qty = get_ordered_qty()
		first_item_of_po = po.get("items")[0]

		trans_item = json.dumps(
			[
				{
					"item_code": first_item_of_po.item_code,
					"rate": first_item_of_po.rate,
					"qty": first_item_of_po.qty,
					"docname": first_item_of_po.name,
				},
				{"item_code": "_Test Item", "rate": 200, "qty": 7},
			]
		)
		update_child_qty_rate("Purchase Order", trans_item, po.name)

		po.reload()
		self.assertEqual(len(po.get("items")), 2)
		self.assertEqual(po.status, "To Receive and Bill")
		# ordered qty should increase on row addition
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 7)

	def test_update_child_removing_item(self):
		po = create_purchase_order(do_not_save=1)
		po.items[0].qty = 4
		po.save()
		po.submit()
		make_pr_against_po(po.name, 2)

		po.reload()
		first_item_of_po = po.get("items")[0]
		existing_ordered_qty = get_ordered_qty()
		# add an item
		trans_item = json.dumps(
			[
				{
					"item_code": first_item_of_po.item_code,
					"rate": first_item_of_po.rate,
					"qty": first_item_of_po.qty,
					"docname": first_item_of_po.name,
				},
				{"item_code": "_Test Item", "rate": 200, "qty": 7},
			]
		)
		update_child_qty_rate("Purchase Order", trans_item, po.name)

		po.reload()

		# ordered qty should increase on row addition
		self.assertEqual(get_ordered_qty(), existing_ordered_qty + 7)

		# check if can remove received item
		trans_item = json.dumps(
			[{"item_code": "_Test Item", "rate": 200, "qty": 7, "docname": po.get("items")[1].name}]
		)
		self.assertRaises(
			frappe.ValidationError, update_child_qty_rate, "Purchase Order", trans_item, po.name
		)

		first_item_of_po = po.get("items")[0]
		trans_item = json.dumps(
			[
				{
					"item_code": first_item_of_po.item_code,
					"rate": first_item_of_po.rate,
					"qty": first_item_of_po.qty,
					"docname": first_item_of_po.name,
				}
			]
		)
		update_child_qty_rate("Purchase Order", trans_item, po.name)

		po.reload()
		self.assertEqual(len(po.get("items")), 1)
		self.assertEqual(po.status, "To Receive and Bill")

		# ordered qty should decrease (back to initial) on row deletion
		self.assertEqual(get_ordered_qty(), existing_ordered_qty)

	def test_update_child_perm(self):
		po = create_purchase_order(item_code="_Test Item", qty=4)

		user = "test@example.com"
		test_user = frappe.get_doc("User", user)
		test_user.add_roles("Accounts User")
		frappe.set_user(user)

		# update qty
		trans_item = json.dumps(
			[{"item_code": "_Test Item", "rate": 200, "qty": 7, "docname": po.items[0].name}]
		)
		self.assertRaises(
			frappe.ValidationError, update_child_qty_rate, "Purchase Order", trans_item, po.name
		)

		# add new item
		trans_item = json.dumps([{"item_code": "_Test Item", "rate": 100, "qty": 2}])
		self.assertRaises(
			frappe.ValidationError, update_child_qty_rate, "Purchase Order", trans_item, po.name
		)
		frappe.set_user("Administrator")

	def test_update_child_with_tax_template(self):
		"""
		Test Action: Create a PO with one item having its tax account head already in the PO.
		Add the same item + new item with tax template via Update Items.
		Expected result: First Item's tax row is updated. New tax row is added for second Item.
		"""
		if not frappe.db.exists("Item", "Test Item with Tax"):
			make_item(
				"Test Item with Tax",
				{
					"is_stock_item": 1,
				},
			)

		if not frappe.db.exists("Item Tax Template", {"title": "Test Update Items Template"}):
			frappe.get_doc(
				{
					"doctype": "Item Tax Template",
					"title": "Test Update Items Template",
					"company": "_Test Company",
					"taxes": [
						{
							"tax_type": "_Test Account Service Tax - _TC",
							"tax_rate": 10,
						}
					],
				}
			).insert()

		new_item_with_tax = frappe.get_doc("Item", "Test Item with Tax")

		if not frappe.db.exists(
			"Item Tax",
			{"item_tax_template": "Test Update Items Template - _TC", "parent": "Test Item with Tax"},
		):
			new_item_with_tax.append(
				"taxes", {"item_tax_template": "Test Update Items Template - _TC", "valid_from": nowdate()}
			)
			new_item_with_tax.save()

		tax_template = "_Test Account Excise Duty @ 10 - _TC"
		item = "_Test Item Home Desktop 100"
		if not frappe.db.exists("Item Tax", {"parent": item, "item_tax_template": tax_template}):
			item_doc = frappe.get_doc("Item", item)
			item_doc.append("taxes", {"item_tax_template": tax_template, "valid_from": nowdate()})
			item_doc.save()
		else:
			# update valid from
			frappe.db.sql(
				"""UPDATE `tabItem Tax` set valid_from = CURRENT_DATE
				where parent = %(item)s and item_tax_template = %(tax)s""",
				{"item": item, "tax": tax_template},
			)

		po = create_purchase_order(item_code=item, qty=1, do_not_save=1)

		po.append(
			"taxes",
			{
				"account_head": "_Test Account Excise Duty - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Excise Duty",
				"doctype": "Purchase Taxes and Charges",
				"rate": 10,
			},
		)
		po.insert()
		po.submit()

		self.assertEqual(po.taxes[0].tax_amount, 50)
		self.assertEqual(po.taxes[0].total, 550)

		items = json.dumps(
			[
				{"item_code": item, "rate": 500, "qty": 1, "docname": po.items[0].name},
				{
					"item_code": item,
					"rate": 100,
					"qty": 1,
				},  # added item whose tax account head already exists in PO
				{
					"item_code": new_item_with_tax.name,
					"rate": 100,
					"qty": 1,
				},  # added item whose tax account head  is missing in PO
			]
		)
		update_child_qty_rate("Purchase Order", items, po.name)

		po.reload()
		self.assertEqual(po.taxes[0].tax_amount, 70)
		self.assertEqual(po.taxes[0].total, 770)
		self.assertEqual(po.taxes[1].account_head, "_Test Account Service Tax - _TC")
		self.assertEqual(po.taxes[1].tax_amount, 70)
		self.assertEqual(po.taxes[1].total, 840)

		# teardown
		frappe.db.sql(
			"""UPDATE `tabItem Tax` set valid_from = NULL
			where parent = %(item)s and item_tax_template = %(tax)s""",
			{"item": item, "tax": tax_template},
		)
		po.cancel()
		po.delete()
		new_item_with_tax.delete()
		frappe.get_doc("Item Tax Template", "Test Update Items Template - _TC").delete()

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
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
			make_purchase_invoice as make_purchase_invoice_return,
		)
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
			make_purchase_receipt as make_purchase_receipt_return,
		)

		pr1 = make_purchase_receipt_return(is_return=1, return_against=pr.name, qty=-3, do_not_submit=True)
		pr1.items[0].purchase_order = po.name
		pr1.items[0].purchase_order_item = po.items[0].name
		pr1.submit()

		pi1 = make_purchase_invoice_return(
			is_return=1, return_against=pi2.name, qty=-1, update_stock=1, do_not_submit=True
		)
		pi1.items[0].purchase_order = po.name
		pi1.items[0].po_detail = po.items[0].name
		pi1.submit()

		po.load_from_db()
		self.assertEqual(po.get("items")[0].received_qty, 5)

	def test_purchase_order_invoice_receipt_workflow(self):
		from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_purchase_receipt

		po = create_purchase_order()
		pi = make_pi_from_po(po.name)

		pi.submit()

		pr = make_purchase_receipt(pi.name)
		pr.submit()

		pi.load_from_db()

		self.assertEqual(pi.per_received, 100.00)
		self.assertEqual(pi.items[0].qty, pi.items[0].received_qty)

		po.load_from_db()

		self.assertEqual(po.per_received, 100.00)
		self.assertEqual(po.per_billed, 100.00)

		pr.cancel()

		pi.load_from_db()
		pi.cancel()

		po.load_from_db()
		po.cancel()

	def test_make_purchase_invoice(self):
		po = create_purchase_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_pi_from_po, po.name)

		po.submit()
		pi = make_pi_from_po(po.name)

		self.assertEqual(pi.doctype, "Purchase Invoice")
		self.assertEqual(len(pi.get("items", [])), 1)

	def test_purchase_order_on_hold(self):
		po = create_purchase_order(item_code="_Test Product Bundle Item")
		po.db_set("status", "On Hold")
		pi = make_pi_from_po(po.name)
		pr = make_purchase_receipt(po.name)
		self.assertRaises(frappe.ValidationError, pr.submit)
		self.assertRaises(frappe.ValidationError, pi.submit)

	def test_make_purchase_invoice_with_terms(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import (
			automatically_fetch_payment_terms,
		)

		automatically_fetch_payment_terms()
		po = create_purchase_order(do_not_save=True)

		self.assertRaises(frappe.ValidationError, make_pi_from_po, po.name)

		po.update({"payment_terms_template": "_Test Payment Term Template"})

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
		automatically_fetch_payment_terms(enable=0)

	def test_warehouse_company_validation(self):
		from erpnext.stock.utils import InvalidWarehouseCompany

		po = create_purchase_order(company="_Test Company 1", do_not_save=True)
		self.assertRaises(InvalidWarehouseCompany, po.insert)

	def test_uom_integer_validation(self):
		from erpnext.utilities.transaction_base import UOMMustBeIntegerError

		po = create_purchase_order(qty=3.4, do_not_save=True)
		self.assertRaises(UOMMustBeIntegerError, po.insert)

	def test_ordered_qty_for_closing_po(self):
		bin = frappe.get_all(
			"Bin",
			filters={"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			fields=["ordered_qty"],
		)

		existing_ordered_qty = bin[0].ordered_qty if bin else 0.0

		po = create_purchase_order(item_code="_Test Item", qty=1)

		self.assertEqual(
			get_ordered_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"),
			existing_ordered_qty + 1,
		)

		po.update_status("Closed")

		self.assertEqual(
			get_ordered_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"), existing_ordered_qty
		)

	def test_group_same_items(self):
		frappe.db.set_single_value("Buying Settings", "allow_multiple_items", 1)
		frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": "_Test Company",
				"supplier": "_Test Supplier",
				"is_subcontracted": 0,
				"schedule_date": add_days(nowdate(), 1),
				"currency": frappe.get_cached_value("Company", "_Test Company", "default_currency"),
				"conversion_factor": 1,
				"items": get_same_items(),
				"group_same_items": 1,
			}
		).insert(ignore_permissions=True)

	def test_make_po_without_terms(self):
		po = create_purchase_order(do_not_save=1)

		self.assertFalse(po.get("payment_schedule"))

		po.insert()

		self.assertTrue(po.get("payment_schedule"))

	def test_po_for_blocked_supplier_all(self):
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.on_hold = 1
		supplier.save()

		self.assertEqual(supplier.hold_type, "All")
		self.assertRaises(frappe.ValidationError, create_purchase_order)

		supplier.on_hold = 0
		supplier.save()

	def test_po_for_blocked_supplier_invoices(self):
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.on_hold = 1
		supplier.hold_type = "Invoices"
		supplier.save()

		self.assertRaises(frappe.ValidationError, create_purchase_order)

		supplier.on_hold = 0
		supplier.save()

	def test_po_for_blocked_supplier_payments(self):
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.on_hold = 1
		supplier.hold_type = "Payments"
		supplier.save()

		po = create_purchase_order()

		self.assertRaises(
			frappe.ValidationError,
			get_payment_entry,
			dt="Purchase Order",
			dn=po.name,
			bank_account="_Test Bank - _TC",
		)

		supplier.on_hold = 0
		supplier.save()

	def test_po_for_blocked_supplier_payments_with_today_date(self):
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.on_hold = 1
		supplier.release_date = nowdate()
		supplier.hold_type = "Payments"
		supplier.save()

		po = create_purchase_order()

		self.assertRaises(
			frappe.ValidationError,
			get_payment_entry,
			dt="Purchase Order",
			dn=po.name,
			bank_account="_Test Bank - _TC",
		)

		supplier.on_hold = 0
		supplier.save()

	def test_po_for_blocked_supplier_payments_past_date(self):
		# this test is meant to fail only if something fails in the try block
		with self.assertRaises(Exception):
			try:
				supplier = frappe.get_doc("Supplier", "_Test Supplier")
				supplier.on_hold = 1
				supplier.hold_type = "Payments"
				supplier.release_date = "2018-03-01"
				supplier.save()

				po = create_purchase_order()
				get_payment_entry("Purchase Order", po.name, bank_account="_Test Bank - _TC")

				supplier.on_hold = 0
				supplier.save()
			except Exception:
				pass
			else:
				raise Exception

	def test_default_payment_terms(self):
		due_date = get_due_date_from_template("_Test Payment Term Template 1", "2023-02-03", None).strftime(
			"%Y-%m-%d"
		)
		self.assertEqual(due_date, "2023-03-31")

	def test_terms_are_not_copied_if_automatically_fetch_payment_terms_is_unchecked(self):
		po = create_purchase_order(do_not_save=1)
		po.payment_terms_template = "_Test Payment Term Template"
		po.save()
		po.submit()

		frappe.db.set_value("Company", "_Test Company", "payment_terms", "_Test Payment Term Template 1")
		pi = make_pi_from_po(po.name)
		pi.save()

		self.assertEqual(pi.get("payment_terms_template"), "_Test Payment Term Template 1")
		frappe.db.set_value("Company", "_Test Company", "payment_terms", "")

	def test_terms_copied(self):
		po = create_purchase_order(do_not_save=1)
		po.payment_terms_template = "_Test Payment Term Template"
		po.insert()
		po.submit()
		self.assertTrue(po.get("payment_schedule"))

		pi = make_pi_from_po(po.name)
		pi.insert(ignore_permissions=True)
		self.assertTrue(pi.get("payment_schedule"))

	@change_settings("Accounts Settings", {"unlink_advance_payment_on_cancelation_of_order": 1})
	def test_advance_payment_entry_unlink_against_purchase_order(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

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

		po_doc = frappe.get_doc("Purchase Order", po_doc.name)
		po_doc.cancel()

		pe_doc = frappe.get_doc("Payment Entry", pe.name)
		pe_doc.cancel()

	def create_account(self, account_name, company, currency, parent):
		if not frappe.db.get_value("Account", filters={"account_name": account_name, "company": company}):
			account = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": account_name,
					"parent_account": parent,
					"company": company,
					"account_currency": currency,
					"is_group": 0,
					"account_type": "Payable",
				}
			).insert()
		else:
			account = frappe.get_doc("Account", {"account_name": account_name, "company": company})

		return account

	def test_advance_payment_with_separate_party_account_enabled(self):
		"""
		Test "Advance Paid" on Purchase Order, when "Book Advance Payments in Separate Party Account" is enabled and
		the payment entry linked to the Order is allocated to Purchase Invoice.
		"""
		supplier = "_Test Supplier"
		company = "_Test Company"

		# Setup default 'Advance Paid' account
		account = self.create_account("Advance Paid", company, "INR", "Application of Funds (Assets) - _TC")
		company_doc = frappe.get_doc("Company", company)
		company_doc.book_advance_payments_in_separate_party_account = True
		company_doc.default_advance_paid_account = account.name
		company_doc.save()

		po_doc = create_purchase_order(supplier=supplier)

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		pe = get_payment_entry("Purchase Order", po_doc.name)
		pe.save().submit()

		po_doc.reload()
		self.assertEqual(po_doc.advance_paid, 5000)

		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice

		company_doc.book_advance_payments_in_separate_party_account = False
		company_doc.save()

	@change_settings("Accounts Settings", {"unlink_advance_payment_on_cancelation_of_order": 1})
	def test_advance_paid_upon_payment_entry_cancellation(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		supplier = "_Test Supplier USD"
		company = "_Test Company"

		# Setup default USD payable account for Supplier
		account = self.create_account("Creditors USD", company, "USD", "Accounts Payable - _TC")
		supplier_doc = frappe.get_doc("Supplier", supplier)
		if not [x for x in supplier_doc.accounts if x.company == company]:
			supplier_doc.append("accounts", {"company": company, "account": account.name})
			supplier_doc.save()

		po_doc = create_purchase_order(supplier=supplier, currency="USD", do_not_submit=1)
		po_doc.conversion_rate = 80
		po_doc.submit()

		pe = get_payment_entry("Purchase Order", po_doc.name)
		pe.mode_of_payment = "Cash"
		pe.paid_from = "Cash - _TC"
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 80
		pe.paid_amount = po_doc.base_grand_total
		pe.save(ignore_permissions=True)
		pe.submit()

		po_doc.reload()
		self.assertEqual(po_doc.advance_paid, po_doc.grand_total)
		self.assertEqual(po_doc.party_account_currency, "USD")

		pe_doc = frappe.get_doc("Payment Entry", pe.name)
		pe_doc.cancel()

		po_doc.reload()
		self.assertEqual(po_doc.advance_paid, 0)
		self.assertEqual(po_doc.party_account_currency, "USD")

	def test_schedule_date(self):
		po = create_purchase_order(do_not_submit=True)
		po.schedule_date = None
		po.append(
			"items",
			{"item_code": "_Test Item", "qty": 1, "rate": 100, "schedule_date": add_days(nowdate(), 5)},
		)
		po.save()
		self.assertEqual(po.schedule_date, add_days(nowdate(), 1))

		po.items[0].schedule_date = add_days(nowdate(), 2)
		po.save()
		self.assertEqual(po.schedule_date, add_days(nowdate(), 2))

	def test_po_optional_blanket_order(self):
		"""
		Expected result: Blanket order Ordered Quantity should only be affected on Purchase Order with against_blanket_order = 1.
		Second Purchase Order should not add on to Blanket Orders Ordered Quantity.
		"""

		_make_blanket_order(blanket_order_type="Purchasing", quantity=10, rate=10)

		po = create_purchase_order(item_code="_Test Item", qty=5, against_blanket_order=1)
		po_doc = frappe.get_doc("Purchase Order", po.get("name"))
		# To test if the PO has a Blanket Order
		self.assertTrue(po_doc.items[0].blanket_order)

		po = create_purchase_order(item_code="_Test Item", qty=5, against_blanket_order=0)
		po_doc = frappe.get_doc("Purchase Order", po.get("name"))
		# To test if the PO does NOT have a Blanket Order
		self.assertEqual(po_doc.items[0].blanket_order, None)

	def test_blanket_order_on_po_close_and_open(self):
		# Step - 1: Create Blanket Order
		bo = _make_blanket_order(blanket_order_type="Purchasing", quantity=10, rate=10)

		# Step - 2: Create Purchase Order
		po = create_purchase_order(
			item_code="_Test Item", qty=5, against_blanket_order=1, against_blanket=bo.name
		)

		bo.load_from_db()
		self.assertEqual(bo.items[0].ordered_qty, 5)

		# Step - 3: Close Purchase Order
		po.update_status("Closed")

		bo.load_from_db()
		self.assertEqual(bo.items[0].ordered_qty, 0)

		# Step - 4: Re-Open Purchase Order
		po.update_status("Re-open")

		bo.load_from_db()
		self.assertEqual(bo.items[0].ordered_qty, 5)

	def test_payment_terms_are_fetched_when_creating_purchase_invoice(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_payment_terms_template,
		)
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import (
			automatically_fetch_payment_terms,
			compare_payment_schedules,
		)

		automatically_fetch_payment_terms()

		po = create_purchase_order(qty=10, rate=100, do_not_save=1)
		create_payment_terms_template()
		po.payment_terms_template = "Test Receivable Template"
		po.submit()

		pi = make_purchase_invoice(qty=10, rate=100, do_not_save=1)
		pi.items[0].purchase_order = po.name
		pi.items[0].po_detail = po.items[0].name
		pi.insert(ignore_permissions=True)

		# self.assertEqual(po.payment_terms_template, pi.payment_terms_template)
		compare_payment_schedules(self, po, pi)

		automatically_fetch_payment_terms(enable=0)

	def test_internal_transfer_flow(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
			make_inter_company_purchase_invoice,
		)
		from erpnext.selling.doctype.sales_order.sales_order import (
			make_delivery_note,
			make_sales_invoice,
		)
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt

		frappe.db.set_single_value("Selling Settings", "maintain_same_sales_rate", 1)
		frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 1)
		get_or_create_fiscal_year("_Test Company with perpetual inventory")
		prepare_data_for_internal_transfer()
		supplier = "_Test Internal Supplier 2"

		mr = make_material_request(
			qty=2, company="_Test Company with perpetual inventory", warehouse="Stores - TCP1"
		)

		po = create_purchase_order(
			company="_Test Company with perpetual inventory",
			supplier=supplier,
			warehouse="Stores - TCP1",
			from_warehouse="_Test Internal Warehouse New 1 - TCP1",
			qty=2,
			rate=1,
			material_request=mr.name,
			material_request_item=mr.items[0].name,
		)

		so = make_inter_company_sales_order(po.name)
		so.items[0].delivery_date = today()
		self.assertEqual(so.items[0].warehouse, "_Test Internal Warehouse New 1 - TCP1")
		self.assertTrue(so.items[0].purchase_order)
		self.assertTrue(so.items[0].purchase_order_item)
		so.submit()

		dn = make_delivery_note(so.name)
		dn.items[0].target_warehouse = "_Test Internal Warehouse GIT - TCP1"
		self.assertEqual(dn.items[0].warehouse, "_Test Internal Warehouse New 1 - TCP1")
		self.assertTrue(dn.items[0].purchase_order)
		self.assertTrue(dn.items[0].purchase_order_item)

		self.assertEqual(po.items[0].name, dn.items[0].purchase_order_item)
		dn.submit()

		pr = make_inter_company_purchase_receipt(dn.name)
		self.assertEqual(pr.items[0].warehouse, "Stores - TCP1")
		self.assertTrue(pr.items[0].purchase_order)
		self.assertTrue(pr.items[0].purchase_order_item)
		self.assertEqual(po.items[0].name, pr.items[0].purchase_order_item)
		pr.submit()

		si = make_sales_invoice(so.name)
		self.assertEqual(si.items[0].warehouse, "_Test Internal Warehouse New 1 - TCP1")
		self.assertTrue(si.items[0].purchase_order)
		self.assertTrue(si.items[0].purchase_order_item)
		si.submit()

		pi = make_inter_company_purchase_invoice(si.name)
		self.assertTrue(pi.items[0].purchase_order)
		self.assertTrue(pi.items[0].po_detail)
		pi.submit()
		mr.reload()

		po.load_from_db()
		self.assertEqual(po.status, "Completed")
		self.assertEqual(mr.status, "Received")

	def test_variant_item_po(self):
		po = create_purchase_order(item_code="_Test Variant Item", qty=1, rate=100, do_not_save=1)

		self.assertRaises(frappe.ValidationError, po.save)

	def test_update_items_for_subcontracting_purchase_order(self):
		from erpnext.controllers.tests.test_subcontracting_controller import (
			get_subcontracting_order,
			make_bom_for_subcontracted_items,
			make_raw_materials,
			make_service_items,
			make_subcontracted_items,
		)

		def update_items(po, qty):
			trans_items = [po.items[0].as_dict().update({"docname": po.items[0].name})]
			trans_items[0]["qty"] = qty
			trans_items[0]["fg_item_qty"] = qty
			trans_items = json.dumps(trans_items, default=str)

			return update_child_qty_rate(
				po.doctype,
				trans_items,
				po.name,
			)

		make_subcontracted_items()
		make_raw_materials()
		make_service_items()
		make_bom_for_subcontracted_items()

		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 7",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA7",
				"fg_item_qty": 10,
			},
		]
		po = create_purchase_order(
			rm_items=service_items,
			is_subcontracted=1,
			supplier_warehouse="_Test Warehouse 1 - _TC",
		)

		update_items(po, qty=20)
		po.reload()

		# Test - 1: Items should be updated as there is no Subcontracting Order against PO
		self.assertEqual(po.items[0].qty, 20)
		self.assertEqual(po.items[0].fg_item_qty, 20)

		sco = get_subcontracting_order(po_name=po.name, warehouse="_Test Warehouse - _TC")

		# Test - 2: ValidationError should be raised as there is Subcontracting Order against PO
		self.assertRaises(frappe.ValidationError, update_items, po=po, qty=30)

		sco.reload()
		sco.cancel()
		po.reload()

		update_items(po, qty=30)
		po.reload()

		# Test - 3: Items should be updated as the Subcontracting Order is cancelled
		self.assertEqual(po.items[0].qty, 30)
		self.assertEqual(po.items[0].fg_item_qty, 30)

	def test_new_sc_flow(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import make_subcontracting_order

		po = create_po_for_sc_testing()
		sco = make_subcontracting_order(po.name)

		sco.items[0].qty = 5
		sco.items.pop(1)
		sco.items[1].qty = 25
		sco.save()
		sco.submit()

		# Test - 1: Quantity of Service Items should change based on change in Quantity of its corresponding Finished Goods Item
		self.assertEqual(sco.service_items[0].qty, 5)

		# Test - 2: Subcontracted Quantity for the PO Items of each line item should be updated accordingly
		po.reload()
		self.assertEqual(po.items[0].subcontracted_quantity, 5)
		self.assertEqual(po.items[1].subcontracted_quantity, 0)
		self.assertEqual(po.items[2].subcontracted_quantity, 12.5)

		# Test - 3: Amount for both FG Item and its Service Item should be updated correctly based on change in Quantity
		self.assertEqual(sco.items[0].amount, 2000)
		self.assertEqual(sco.service_items[0].amount, 500)

		# Test - 4: Service Items should be removed if its corresponding Finished Good line item is deleted
		self.assertEqual(len(sco.service_items), 2)

		# Test - 5: Service Item quantity calculation should be based upon conversion factor calculated from its corresponding PO Item
		self.assertEqual(sco.service_items[1].qty, 12.5)

		sco = make_subcontracting_order(po.name)

		sco.items[0].qty = 6

		# Test - 6: Saving document should not be allowed if Quantity exceeds available Subcontracting Quantity of any Purchase Order Item
		self.assertRaises(frappe.ValidationError, sco.save)

		sco.items[0].qty = 5
		sco.items.pop()
		sco.items.pop()
		sco.save()
		sco.submit()

		sco = make_subcontracting_order(po.name)

		# Test - 7: Since line item 1 is now fully subcontracted, new SCO should by default only have the remaining 2 line items
		self.assertEqual(len(sco.items), 2)

		sco.items.pop(0)
		sco.save()
		sco.submit()

		# Test - 8: Subcontracted Quantity for each PO Item should be subtracted if SCO gets cancelled
		po.reload()
		self.assertEqual(po.items[2].subcontracted_quantity, 25)
		sco.cancel()
		po.reload()
		self.assertEqual(po.items[2].subcontracted_quantity, 12.5)

		sco = make_subcontracting_order(po.name)
		sco.save()
		sco.submit()

		# Test - 8: Since this PO is now fully subcontracted, creating a new SCO from it should throw error
		self.assertRaises(frappe.ValidationError, make_subcontracting_order, po.name)

	@change_settings("Buying Settings", {"auto_create_subcontracting_order": 1})
	def test_auto_create_subcontracting_order(self):
		from erpnext.controllers.tests.test_subcontracting_controller import (
			make_bom_for_subcontracted_items,
			make_raw_materials,
			make_service_items,
			make_subcontracted_items,
		)

		make_subcontracted_items()
		make_raw_materials()
		make_service_items()
		make_bom_for_subcontracted_items()

		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 7",
				"qty": 10,
				"rate": 100,
				"fg_item": "Subcontracted Item SA7",
				"fg_item_qty": 10,
			},
		]
		po = create_purchase_order(
			rm_items=service_items,
			is_subcontracted=1,
			supplier_warehouse="_Test Warehouse 1 - _TC",
		)

		self.assertTrue(frappe.db.get_value("Subcontracting Order", {"purchase_order": po.name}))

	def test_po_billed_amount_against_return_entry(self):
		from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_debit_note

		# Create a Purchase Order and Fully Bill it
		po = create_purchase_order()
		pi = make_pi_from_po(po.name)
		pi.insert(ignore_permissions=True)
		pi.submit()

		# Debit Note - 50% Qty & enable updating PO billed amount
		pi_return = make_debit_note(pi.name)
		pi_return.items[0].qty = -5
		pi_return.update_billed_amount_in_purchase_order = 1
		pi_return.submit()

		# Check if the billed amount reduced
		po.reload()
		self.assertEqual(po.per_billed, 50)

		pi_return.reload()
		pi_return.cancel()

		# Debit Note - 50% Qty & disable updating PO billed amount
		pi_return = make_debit_note(pi.name)
		pi_return.items[0].qty = -5
		pi_return.update_billed_amount_in_purchase_order = 0
		pi_return.submit()

		# Check if the billed amount stayed the same
		po.reload()
		self.assertEqual(po.per_billed, 100)

	@change_settings("Buying Settings", {"allow_zero_qty_in_purchase_order": 1})
	def test_receive_zero_qty_purchase_order(self):
		"""
		Test the flow of a Unit Price PO and PR creation against it until completion.
		Flow:
		PO Qty 0 -> Receive +5 -> Receive +5 -> Update PO Qty +10 -> PO is 100% received
		"""
		po = create_purchase_order(qty=0)
		pr = make_purchase_receipt(po.name)

		self.assertEqual(pr.items[0].qty, 0)
		pr.items[0].qty = 5
		pr.submit()

		po.reload()
		self.assertEqual(po.items[0].received_qty, 5)
		self.assertFalse(po.per_received)
		self.assertEqual(po.status, "To Receive and Bill")

		# Update PO Item Qty to 10 after receipt of items
		first_item_of_po = po.items[0]
		trans_item = json.dumps(
			[
				{
					"item_code": first_item_of_po.item_code,
					"rate": first_item_of_po.rate,
					"qty": 10,
					"docname": first_item_of_po.name,
				}
			]
		)
		update_child_qty_rate("Purchase Order", trans_item, po.name)

		# Test: PR can be made against PO as long PO qty is 0 OR PO qty > received qty
		pr2 = make_purchase_receipt(po.name)

		po.reload()
		self.assertEqual(po.items[0].qty, 10)
		self.assertEqual(pr2.items[0].qty, 5)

		pr2.submit()

		# PO should be updated to 100% received
		po.reload()
		self.assertEqual(po.items[0].qty, 10)
		self.assertEqual(po.items[0].received_qty, 10)
		self.assertEqual(po.per_received, 100.0)
		self.assertEqual(po.status, "To Bill")

	@change_settings("Buying Settings", {"allow_zero_qty_in_purchase_order": 1})
	def test_bill_zero_qty_purchase_order(self):
		po = create_purchase_order(qty=0)

		self.assertEqual(po.grand_total, 0)
		self.assertFalse(po.per_billed)
		self.assertEqual(po.items[0].qty, 0)
		self.assertEqual(po.items[0].rate, 500)

		pi = make_pi_from_po(po.name)
		self.assertEqual(pi.items[0].qty, 0)
		self.assertEqual(pi.items[0].rate, 500)

		pi.items[0].qty = 5
		pi.submit()

		self.assertEqual(pi.grand_total, 2500)

		po.reload()
		self.assertEqual(po.items[0].amount, 0)
		self.assertEqual(po.items[0].billed_amt, 2500)
		# PO still has qty 0, so billed % should be unset
		self.assertFalse(po.per_billed)
		self.assertEqual(po.status, "To Receive and Bill")

	def test_create_purchase_receipt(self):
		po = create_purchase_order(rate=10000, qty=10)
		po.submit()

		pr = create_pr_against_po(po.name, received_qty=10)
		bin_qty = frappe.db.get_value(
			"Bin", {"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"}, "actual_qty"
		)
		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_no": pr.name})
		self.assertEqual(sle.qty_after_transaction, bin_qty)
		self.assertEqual(sle.warehouse, po.get("items")[0].warehouse)

		# if account setup in company
		if frappe.db.exists("GL Entry", {"account": "Stock Received But Not Billed - _TC"}):
			gl_temp_credit = frappe.db.get_value(
				"GL Entry",
				{"voucher_no": pr.name, "account": "Stock Received But Not Billed - _TC"},
				"credit",
			)
			self.assertEqual(gl_temp_credit, 100000)

		# if account setup in company
		if frappe.db.exists("GL Entry", {"account": "Stock In Hand - _TC"}):
			gl_stock_debit = frappe.db.get_value(
				"GL Entry", {"voucher_no": pr.name, "account": "Stock In Hand - _TC"}, "debit"
			)
			self.assertEqual(gl_stock_debit, 100000)

	def test_single_po_pi_TC_B_001(self):
		# Scenario : PO => PR => 1PI
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		warehouse = "Stores - TC-3"

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 6,
						"rate": 100,
						"warehouse": warehouse,
					}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.items[0].qty, po.items[0].qty)
		self.assertEqual(pi.grand_total, po.grand_total)

	def test_mr_pi_TC_B_002(self):
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("Testing-31")
		# MR =>  PO => PR => PI
		mr_dict_list = [
			{
				"company": "_Test Company",
				"item_code": "Testing-31",
				"warehouse": "Stores - _TC",
				"qty": 6,
				"rate": 100,
			},
		]

		doc_mr = make_material_request(**mr_dict_list[0])
		self.assertEqual(doc_mr.docstatus, 1)
		doc_po = make_test_po(doc_mr.name)
		doc_pr = make_test_pr(doc_po.name)
		doc_pi = make_test_pi(doc_pr.name)

		self.assertEqual(doc_pi.docstatus, 1)
		doc_mr.reload()
		self.assertEqual(doc_mr.status, "Received")

	def test_mr_pi_TC_B_003(self):
		# MR => RFQ => SQ => PO => PR => PI
		make_test_item("Testing-31")
		args = frappe._dict()
		args["mr"] = [
			{
				"company": "_Test Company",
				"item_code": "Testing-31",
				"warehouse": "Stores - _TC",
				"qty": 2,
				"rate": 100,
			},
		]

		doc_mr = make_material_request(**args["mr"][0])
		self.assertEqual(doc_mr.docstatus, 1)

		doc_rfq = make_test_rfq(doc_mr.name)
		doc_sq = make_test_sq(doc_rfq.name, 100)
		doc_po = make_test_po(doc_sq.name, type="Supplier Quotation")
		doc_pr = make_test_pr(doc_po.name)
		doc_pi = make_test_pi(doc_pr.name)

		self.assertEqual(doc_pi.docstatus, 1)
		doc_mr.reload()
		self.assertEqual(doc_mr.status, "Received")

	def test_multi_po_pr_TC_B_008(self):
		# Scenario : 2PO => 2PR => 1PI
		purchase_order_list = [
			{
				"company": "_Test Company",
				"item_code": "_Test Item",
				"warehouse": "Stores - _TC",
				"qty": 3,
				"rate": 100,
			},
			{
				"company": "_Test Company",
				"item_code": "_Test Item",
				"warehouse": "Stores - _TC",
				"qty": 3,
				"rate": 100,
			},
		]

		pur_receipt_name_list = []
		pur_order_dict = frappe._dict({"total_amount": 0, "total_qty": 0})

		for order in purchase_order_list:
			doc_po = create_purchase_order(**order)
			pur_order_dict.update({"total_amount": pur_order_dict.total_amount + doc_po.grand_total})
			pur_order_dict.update({"total_qty": pur_order_dict.total_qty + doc_po.total_qty})

			self.assertEqual(doc_po.docstatus, 1)

			doc_pr = make_pr_for_po(doc_po.name)
			self.assertEqual(doc_pr.docstatus, 1)
			self.assertEqual(doc_pr.grand_total, doc_po.grand_total)

			pur_receipt_name_list.append(doc_pr.name)

		item_dict = [
			{
				"item_code": "_Test Item",
				"warehouse": "Stores - _TC",
				"qty": 3,
				"rate": 100,
				"purchase_receipt": pur_receipt_name_list[1],
			}
		]

		doc_pi = make_pi_against_pr(pur_receipt_name_list[0], item_dict_list=item_dict)
		self.assertEqual(doc_pi.docstatus, 1)
		self.assertEqual(doc_pi.total_qty, pur_order_dict.total_qty)
		self.assertEqual(doc_pi.grand_total, pur_order_dict.total_amount)

	def test_multi_po_single_pr_pi_TC_B_007(self):
		# Scenario : 2PO => 1PR => 1PI
		purchase_order_list = [
			{
				"company": "_Test Company",
				"item_code": "_Test Item",
				"warehouse": "Stores - _TC",
				"qty": 3,
				"rate": 100,
			},
			{
				"company": "_Test Company",
				"item_code": "_Test Item",
				"warehouse": "Stores - _TC",
				"qty": 3,
				"rate": 100,
			},
		]

		pur_order_name_list = []
		pur_order_dict = frappe._dict({"total_amount": 0, "total_qty": 0})

		for order in purchase_order_list:
			doc_po = create_purchase_order(**order)
			pur_order_dict.update({"total_amount": pur_order_dict.total_amount + doc_po.grand_total})
			pur_order_dict.update({"total_qty": pur_order_dict.total_qty + doc_po.total_qty})

			self.assertEqual(doc_po.docstatus, 1)
			pur_order_name_list.append(doc_po.name)

		item_dict = [
			{
				"item_code": "_Test Item",
				"warehouse": "Stores - _TC",
				"qty": 3,
				"rate": 100,
				"purchase_receipt": pur_order_name_list[1],
			}
		]

		doc_pr = make_pr_for_po(pur_order_name_list[0], item_dict_list=item_dict)

		doc_pi = make_pi_against_pr(doc_pr.name)
		self.assertEqual(doc_pi.docstatus, 1)
		self.assertEqual(doc_pi.total_qty, pur_order_dict.total_qty)
		self.assertEqual(doc_pi.grand_total, pur_order_dict.total_amount)

	def test_single_po_multi_pr_pi_TC_B_006(self):
		# Scenario : 1PO => 2PR => 2PI
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		warehouse = "Stores - TC-3"
		get_or_create_fiscal_year(company)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 6,
						"rate": 100,
						"warehouse": warehouse,
					}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)

		pur_invoice_dict = frappe._dict({"total_amount": 0, "total_qty": 0})
		pur_receipt_qty = [3, 3]

		for received_qty in pur_receipt_qty:
			doc_pr = make_pr_for_po(po.name, received_qty)
			self.assertEqual(doc_pr.docstatus, 1)

			doc_pi = make_pi_against_pr(doc_pr.name)
			self.assertEqual(doc_pi.docstatus, 1)

			pur_invoice_dict.update({"total_amount": pur_invoice_dict.total_amount + doc_pi.grand_total})
			pur_invoice_dict.update({"total_qty": pur_invoice_dict.total_qty + doc_pi.total_qty})

		self.assertEqual(po.total_qty, pur_invoice_dict.total_qty)
		self.assertEqual(po.grand_total, pur_invoice_dict.total_amount)

	def test_single_po_pi_multi_pr_TC_B_005(self):
		# Scenario : 1PO => 2PR => 1PI
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		warehouse = "Stores - TC-3"

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 6,
						"rate": 100,
						"warehouse": warehouse,
					}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)

		pur_receipt_qty = [3, 3]
		pur_receipt_name_list = []

		for received_qty in pur_receipt_qty:
			doc_pr = make_pr_for_po(po.name, received_qty)
			self.assertEqual(doc_pr.docstatus, 1)

			pur_receipt_name_list.append(doc_pr.name)

		item_dict = [
			{
				"item_code": item.item_code,
				"warehouse": warehouse,
				"qty": 3,
				"rate": 100,
				"purchase_receipt": pur_receipt_name_list[1],
			}
		]

		doc_pi = make_pi_against_pr(pur_receipt_name_list[0], item_dict_list=item_dict)

		self.assertEqual(doc_pi.docstatus, 1)
		self.assertEqual(po.total_qty, doc_pi.total_qty)
		self.assertEqual(po.grand_total, doc_pi.grand_total)

	def test_create_purchase_receipt_partial_TC_SCK_037(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		# Step 1: Setup
		create_company()
		create_item("_Test Item", warehouse="Stores - _TC")
		create_supplier(supplier_name="_Test Supplier")
		get_or_create_fiscal_year("_Test Company")

		# Step 2: Create and submit PO
		po = create_purchase_order(rate=10000, qty=10, warehouse="Stores - _TC")
		po.submit()

		# Step 3: Create partial PR (5 qty)
		pr = create_pr_against_po(po.name, received_qty=5)

		# Step 4: Check stock ledger
		bin_qty = frappe.db.get_value(
			"Bin", {"item_code": "_Test Item", "warehouse": "Stores - _TC"}, "actual_qty"
		)
		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_no": pr.name})
		self.assertEqual(sle.qty_after_transaction, bin_qty)
		self.assertEqual(sle.warehouse, po.get("items")[0].warehouse)

		# Step 5: Check GL Entries
		if frappe.db.exists("GL Entry", {"account": "Stock Received But Not Billed - _TC"}):
			gl_temp_credit = frappe.db.get_value(
				"GL Entry",
				{"voucher_no": pr.name, "account": "Stock Received But Not Billed - _TC"},
				"credit",
			)
			if gl_temp_credit is not None:
				self.assertEqual(gl_temp_credit, 50000)

		if frappe.db.exists("GL Entry", {"account": "Stock In Hand - _TC"}):
			gl_stock_debit = frappe.db.get_value(
				"GL Entry",
				{"voucher_no": pr.name, "account": "Stock In Hand - _TC"},
				"debit",
			)
			if gl_stock_debit is not None:
				self.assertEqual(gl_stock_debit, 50000)


	def test_pi_return_TC_B_043(self):
		from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_debit_note
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import check_gl_entries
		from erpnext.stock.doctype.stock_entry.test_stock_entry import get_qty_after_transaction

		po = create_purchase_order(
			warehouse="Finished Goods - _TC",
			rate=130,
			qty=1,
		)
		self.assertEqual(po.status, "To Receive and Bill")
		actual_qty_0 = get_qty_after_transaction(warehouse="Finished Goods - _TC")

		pi = make_pi_from_po(po.name)
		pi.update_stock = 1
		pi.save()
		pi.submit()
		pi.load_from_db()
		self.assertEqual(pi.status, "Unpaid")
		expected_gle_1 = [
			["Creditors - _TC", 0.0, 130, nowdate()],
			["Stock In Hand - _TC", 130, 0.0, nowdate()],
		]
		check_gl_entries(self, pi.name, expected_gle_1, nowdate())
		actual_qty_1 = get_qty_after_transaction(warehouse="Finished Goods - _TC")
		self.assertEqual(actual_qty_0 + 1, actual_qty_1)

		po_status = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status, "Completed")

		pi_return = make_debit_note(pi.name)
		pi_return.update_outstanding_for_self = 0
		pi_return.update_billed_amount_in_purchase_receipt = 0
		pi_return.save()
		pi_return.submit()
		pi_return.load_from_db()
		self.assertEqual(pi_return.status, "Return")
		expected_gle_2 = [
			["Creditors - _TC", 130, 0.0, nowdate()],
			["Stock In Hand - _TC", 0.0, 130, nowdate()],
		]
		check_gl_entries(self, pi_return.name, expected_gle_2, nowdate())
		actual_qty_2 = get_qty_after_transaction(warehouse="Finished Goods - _TC")
		self.assertEqual(actual_qty_1 - 1, actual_qty_2)

		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Debit Note Issued")

	def test_payment_entry_TC_B_037(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import check_gl_entries

		get_company_and_supplier = get_company_or_supplier()
		company = get_company_and_supplier.get("company")
		supplier = get_company_and_supplier.get("supplier")
		warehouse = "Stores - TC-5"

		po = create_purchase_order(
			warehouse=warehouse, rate=30, qty=1, company=company, supplier=supplier, currency="INR"
		)

		self.assertEqual(po.status, "To Receive and Bill")
		pi = make_pi_from_po(po.name)
		pi.update_stock = 1
		pi.save()
		pi.submit()
		pi.load_from_db()

		expected_gle = [
			["Creditors - TC-5", 0.0, 30, nowdate()],
			["Stock In Hand - TC-5", 30, 0.0, nowdate()],
		]
		check_gl_entries(self, pi.name, expected_gle, nowdate())

		pe = get_payment_entry("Purchase Invoice", pi.name)
		pe.save()
		pe.submit()
		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Paid")
		expected_gle = [
			{"account": "Creditors - TC-5", "debit": 30.0, "credit": 0.0},
			{"account": "Cash - TC-5", "debit": 0.0, "credit": 30.0},
		]
		check_payment_gl_entries(self, pe.name, expected_gle)

	def test_purchase_invoice_cancellation_TC_B_041(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item_12")
		warehouse = "Stores - TC-3"

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"set_warehouse": warehouse,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 1,
						"rate": 130,
						"warehouse": warehouse,
					}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.status, "To Receive and Bill")

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()
		self.assertEqual(pr.status, "To Bill")
		po_status = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status, "To Bill")

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.save()
		pi.submit()
		self.assertEqual(pi.status, "Unpaid")
		po_status = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status, "Completed")
		pr_status = frappe.db.get_value("Purchase Receipt", pr.name, "status")
		self.assertEqual(pr_status, "Completed")

		pi.cancel()
		self.assertEqual(pi.status, "Cancelled")
		po_status = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status, "To Bill")
		pr_status = frappe.db.get_value("Purchase Receipt", pr.name, "status")
		self.assertEqual(pr_status, "To Bill")

	def test_purchase_invoice_return_TC_B_042(self):
		from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_debit_note

		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_itemss")
		warehouse = "Stores - TC-3"

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 1,
						"rate": 130,
						"warehouse": warehouse,
					}
				],
			}
		)
		po.insert()
		po.submit()

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.save()
		pi.submit()

		pi_return = make_debit_note(pi.name)
		pi_return.update_outstanding_for_self = 0
		pi_return.update_billed_amount_in_purchase_receipt = 0
		pi_return.save()
		pi_return.submit()
		self.assertEqual(pi_return.status, "Return")
		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Debit Note Issued")
	
	def test_50_50_payment_terms_TC_B_044(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		po = create_purchase_order(warehouse="Finished Goods - _TC", rate=130, qty=1, do_not_save=1)
		po.payment_terms_template = "_Test Payment Term Template"
		po.save()
		po.submit()

		pe = get_payment_entry("Purchase Order", po.name, party_amount=po.grand_total / 2)
		pe.save()
		pe.submit()

		allocated_amount = sum(ref.allocated_amount for ref in pe.references if ref.reference_name == po.name)
		frappe.db.set_value("Purchase Order", po.name, "advance_paid", allocated_amount)
		frappe.db.commit()

		po_advance_paid = frappe.db.get_value("Purchase Order", po.name, "advance_paid")
		self.assertEqual(po_advance_paid, po.grand_total / 2)

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()
		self.assertEqual(pr.status, "To Bill")

		pi = make_purchase_invoice(pr.name)
		pi.set_advances()
		pi.save()
		pi.submit()

		po_status = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status, "Completed")

		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Paid")


	def test_status_po_on_pi_cancel_TC_B_038(self):
		from erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment import (
			create_unreconcile_doc_for_selection,
			payment_reconciliation_record_on_unreconcile,
		)

		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		warehouse = "Stores - TC-3"
		get_or_create_fiscal_year(company)
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"rate": 500,
						"warehouse": warehouse,
					}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)

		pi = make_pi_from_po(po.name)
		pi.update_stock = 1
		pi.bill_no = "test_bill"
		pi.insert(ignore_permissions=True)
		pi.submit()

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.save()
		pe.submit()

		before_pi_cancel_status = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(before_pi_cancel_status, "Completed")

		header = {
			"company": company,
			"unreconcile": 1,
			"clearing_date": "2025-01-07",
			"party_type": "Supplier",
			"party": supplier,
		}
		selection = {
			"company": company,
			"voucher_type": "Payment Entry",
			"voucher_no": f"{pe.name}",
			"against_voucher_type": "Purchase Invoice",
			"against_voucher_no": f"{pi.name}",
			"allocated_amount": pi.rounded_total,
		}
		allocation = [
			{
				"reference_type": "Payment Entry",
				"reference_name": pe.name,
				"invoice_type": "Purchase Invoice",
				"invoice_number": pi.name,
				"allocated_amount": pi.rounded_total,
			}
		]
		payment_reconciliation_record_on_unreconcile(header=header, allocation=allocation)
		create_unreconcile_doc_for_selection(selections=json.dumps([selection]))

		pi.reload()
		pi.cancel()
		after_pi_cancel_status = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(after_pi_cancel_status, "To Receive and Bill")

	def test_full_payment_request_TC_B_030(self):
		# Scenario : PO => Payment Request

		po_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"qty": 6,
			"rate": 100,
		}

		doc_po = create_purchase_order(**po_data)
		self.assertEqual(doc_po.docstatus, 1)

		args = frappe._dict()
		args = {
			"dt": doc_po.doctype,
			"dn": doc_po.name,
			"recipient_id": doc_po.contact_email,
			"payment_request_type": "Outward",
			"party_type": "Supplier",
			"party": doc_po.supplier,
			"party_name": doc_po.supplier_name,
		}
		dict_pr = make_payment_request(**args)
		doc_pr = frappe.get_doc("Payment Request", dict_pr.name)
		doc_pr.submit()
		self.assertEqual(doc_pr.docstatus, 1)
		self.assertEqual(doc_pr.reference_name, doc_po.name)
		self.assertEqual(doc_pr.grand_total, doc_po.grand_total)

	def test_po_to_partial_pr_TC_B_031(self):
		make_test_item("Testing-31")
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": "_Test Supplier 1",
				"company": "_Test Company",
				"schedule_date": frappe.utils.nowdate(),
				"items": [
					{
						"item_code": "Testing-31",
						"qty": 6,
						"rate": 100,
						"warehouse": "Stores - _TC",
					}
				],
			}
		)
		po.insert()
		po.submit()

		payment_request = frappe.get_doc(
			{
				"doctype": "Payment Request",
				"reference_doctype": "Purchase Order",
				"reference_name": po.name,
				"payment_request_type": "Outward",
				"party_type": "Supplier",
				"party": po.supplier,
				"grand_total": 300,
			}
		)

		payment_request.insert()
		payment_request.submit()

		self.assertEqual(payment_request.payment_request_type, "Outward")
		self.assertEqual(payment_request.grand_total, 300)
		self.assertEqual(payment_request.reference_name, po.name)

	def test_purchase_invoice_return_TC_B_032(self):
		frappe.set_user("Administrator")
		company = "_Test Company"
		item = make_test_item("Testing-31")
		target_warehouse = "Stores - _TC"
		supplier = "_Test Supplier 1"
		qty = 6
		rate = 100
		amount = qty * rate

		purchase_invoice = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": company,
				"supplier": supplier,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"warehouse": target_warehouse,
						"qty": qty,
						"rate": rate,
						"amount": amount,
					}
				],
				"update_stock": 1,
			}
		)
		purchase_invoice.bill_no = "test_bill_1122"
		purchase_invoice.taxes_and_charges = ""
		purchase_invoice.taxes = []
		purchase_invoice.insert()
		purchase_invoice.submit()

		purchase_invoice_return = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": company,
				"supplier": supplier,
				"is_return": 1,
				"currency": "INR",
				"return_against": purchase_invoice.name,
				"items": [
					{
						"item_code": item.item_code,
						"warehouse": target_warehouse,
						"qty": -qty,
						"rate": rate,
						"amount": amount,
					}
				],
				"update_stock": 1,
			}
		)
		purchase_invoice_return.bill_no = "test_bill_1122"
		purchase_invoice_return.taxes_and_charges = ""
		purchase_invoice_return.taxes = []
		purchase_invoice_return.insert()
		purchase_invoice_return.submit()

		gl_entries = frappe.get_all(
			"GL Entry",
			filters={
				"voucher_type": "Purchase Invoice",
				"voucher_no": purchase_invoice_return.name,
				"company": company,
			},
			fields=["account", "debit", "credit"],
		)

		reversal_passed = False
		for entry in gl_entries:
			if "Stock In Hand" in entry["account"]:
				self.assertEqual(entry["credit"], amount)
				reversal_passed = True
			elif "Creditors" in entry["account"]:
				self.assertEqual(entry["debit"], amount)
				reversal_passed = True

		stock_ledger_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={
				"voucher_type": "Purchase Invoice",
				"voucher_no": purchase_invoice_return.name,
				"warehouse": target_warehouse,
			},
			fields=["actual_qty"],
		)

		stock_decrease_passed = False
		for entry in stock_ledger_entries:
			if entry["actual_qty"] == -qty:
				stock_decrease_passed = True

		self.assertTrue(reversal_passed)
		self.assertTrue(stock_decrease_passed)

	def test_partial_purchase_invoice_return_TC_B_033(self):
		frappe.set_user("Administrator")
		company = "_Test Company"
		item = make_test_item("Testing-31")
		target_warehouse = "Stores - _TC"
		supplier = "_Test Supplier 1"
		original_qty = 6
		return_qty = 3
		rate = 100
		amount = original_qty * rate
		return_amount = return_qty * rate

		purchase_invoice = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": company,
				"supplier": supplier,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"warehouse": target_warehouse,
						"qty": original_qty,
						"rate": rate,
						"amount": amount,
					}
				],
				"update_stock": 1,
			}
		)
		purchase_invoice.insert()
		purchase_invoice.submit()

		purchase_invoice_return = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": company,
				"supplier": supplier,
				"is_return": 1,
				"currency": "INR",
				"return_against": purchase_invoice.name,
				"items": [
					{
						"item_code": item.item_code,
						"warehouse": target_warehouse,
						"qty": -return_qty,
						"rate": rate,
						"amount": return_amount,
					}
				],
				"update_stock": 1,
			}
		)
		purchase_invoice_return.insert()
		purchase_invoice_return.submit()

		gl_entries = frappe.get_all(
			"GL Entry",
			filters={
				"voucher_type": "Purchase Invoice",
				"voucher_no": purchase_invoice_return.name,
				"company": company,
			},
			fields=["account", "debit", "credit"],
		)

		reversal_passed = False
		for entry in gl_entries:
			if "Stock In Hand" in entry["account"]:
				self.assertEqual(entry["credit"], return_amount)
				reversal_passed = True
			elif "Creditors" in entry["account"]:
				self.assertEqual(entry["debit"], return_amount)
				reversal_passed = True

		stock_ledger_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={
				"voucher_type": "Purchase Invoice",
				"voucher_no": purchase_invoice_return.name,
				"warehouse": target_warehouse,
			},
			fields=["actual_qty"],
		)

		stock_decrease_passed = False
		for entry in stock_ledger_entries:
			if entry["actual_qty"] == -return_qty:
				stock_decrease_passed = True

		# Assertions
		self.assertTrue(reversal_passed)
		self.assertTrue(stock_decrease_passed)

	def test_pr_to_lcv_add_value_to_stock_TC_B_034(self):
		frappe.db.set_value(
			"Company",
			"_Test Company",
			{"enable_perpetual_inventory": 1, "stock_received_but_not_billed": "Stock Adjustment - _TC"},
		)
		item = make_test_item("Testing-31")
		create_supplier(supplier_name="_Test Supplier 1")
		create_supplier(supplier_name="_Test Supplier")
		get_or_create_fiscal_year("_Test Company")
		# Step 1: Create Purchase Receipt
		company = "_Test Company"
		doc_pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"company": "_Test Company",
				"supplier": "_Test Supplier",
				"items": [
					{
						"item_code": item.item_code,
						"warehouse": "Stores - _TC",
						"qty": 10,
						"rate": 100,
					}
				],
			}
		)
		doc_pr.insert()
		doc_pr.submit()
		self.assertEqual(doc_pr.docstatus, 1)
		account = frappe.db.get_value("Account", {"company": company, "account_type": "Tax"}, "name")
		doc_lcv = frappe.get_doc(
			{
				"doctype": "Landed Cost Voucher",
				"company": "_Test Company",
				"purchase_receipts": [
					{
						"receipt_document_type": "Purchase Receipt",
						"receipt_document": doc_pr.name,
						"supplier": doc_pr.supplier,
						"grand_total": doc_pr.grand_total,
					}
				],
				"taxes": [{"expense_account": account, "amount": 500, "description": "test_description"}],
			}
		)
		doc_lcv.insert()
		doc_lcv.submit()
		self.assertEqual(doc_lcv.docstatus, 1)

		# Validate Stock Ledger Entries
		stock_ledger_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": doc_pr.name, "warehouse": "Stores - _TC", "item_code": item.item_code},
			fields=["valuation_rate"],
			order_by="creation desc",
		)
		self.assertGreater(len(stock_ledger_entries), 0)

		updated_valuation_rate = stock_ledger_entries[0]["valuation_rate"]
		self.assertGreater(updated_valuation_rate, 100)

		# Validate GL Entries
		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": doc_pr.name}, fields=["account", "debit", "credit"]
		)
		self.assertGreater(len(gl_entries), 0)

	def test_po_and_pi_with_pricing_rule_with_TC_B_048(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import get_or_create_price_list

		frappe.set_user("Administrator")
		company = "_Test Company"
		target_warehouse = "Stores - _TC"
		supplier = "_Test Supplier 1"
		item_price = 130
		item = make_test_item("Testing-31")
		item.is_purchase_item = 1
		item.save()

		frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": get_or_create_price_list(),
				"item_code": item.item_code,
				"price_list_rate": item_price,
			}
		).insert(ignore_if_duplicate=1)

		frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "10% Discount",
				"company": company,
				"apply_on": "Item Code",
				"items": [{"item_code": item.item_code}],
				"rate_or_discount": "Discount Percentage",
				"discount_percentage": 10,
				"selling": 0,
				"buying": 1,
			}
		).insert(ignore_if_duplicate=1)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"buying_price_list": get_or_create_price_list(),
				"set_warehouse": target_warehouse,
				"items": [{"item_code": item.item_code, "warehouse": target_warehouse, "qty": 1}],
			}
		)
		po.insert()
		po.submit()

		self.assertEqual(len(po.items), 1)
		self.assertEqual(po.items[0].rate, 117)
		self.assertEqual(po.items[0].discount_percentage, 10)

		pi = make_pi_from_po(po.name)
		pi.insert(ignore_permissions=True)
		pi.submit()

		self.assertEqual(len(pi.items), 1)
		self.assertEqual(pi.items[0].rate, 117)
		self.assertEqual(pi.items[0].discount_percentage, 10)

	@if_app_installed("india_compliance")
	def test_po_to_pr_with_gst_partly_paid_TC_B_085(self):
		# Scenario : PO => PR with GST Partly Paid
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		warehouse = "Stores - TC-5"
		tax_category = "test_category_1"
		if not frappe.db.exists("Tax Category", tax_category):
			tax_category = frappe.get_doc({"doctype": "Tax Category", "title": "test_category_1"}).insert()

		purchase_tax = frappe.get_doc(
			{
				"doctype": "Purchase Taxes and Charges Template",
				"title": "Test Template",
				"company": company,
				"tax_category": tax_category,
				"taxes": [
					{
						"category": "Total",
						"add_deduct_tax": "Add",
						"charge_type": "On Net Total",
						"account_head": "Cash - TC-5",
						"rate": 100,
						"description": "GST",
					}
				],
			}
		).insert(ignore_if_duplicate=1)

		po = create_purchase_order(
			company=company,
			item_code=item.item_code,
			warehouse=warehouse,
			supplier=supplier,
			do_not_submit=True,
		)
		po.currency = "INR"
		po.taxes_and_charges = purchase_tax.name
		po.save()
		po.submit()
		self.assertEqual(po.docstatus, 1)

		args = {
			"dt": po.doctype,
			"dn": po.name,
			"payment_request_type": "Outward",
			"party_type": "Supplier",
			"party": po.supplier,
			"party_name": po.supplier_name,
		}
		partly_pr = make_payment_request(**args)
		doc_pr = frappe.get_doc("Payment Request", partly_pr.name)
		# set half amount to be paid
		doc_pr.grand_total = po.grand_total / 2
		doc_pr.submit()
		po_status = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status, "To Receive and Bill")

	def test_po_to_pr_with_gst_fully_paid_TC_B_086(self):
		# Scenario : PO => PR with GST Fully Paid
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		create_supplier(supplier_name="_Test Supplier")
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		get_or_create_fiscal_year("_Test Company")
		create_item("_Test Item")
		purchase_tax = frappe.new_doc("Purchase Taxes and Charges Template")
		purchase_tax.title = "TEST"
		purchase_tax.company = "_Test Company"

		purchase_tax.append(
			"taxes",
			{
				"category": "Total",
				"add_deduct_tax": "Add",
				"charge_type": "On Net Total",
				"account_head": "Stock In Hand - _TC",
				"rate": 100,
				"description": "GST",
			},
		)
		purchase_tax.save()
		po = create_purchase_order(do_not_submit=True)
		po.taxes_and_charges = purchase_tax.name
		po.save()
		po.submit()
		self.assertEqual(po.docstatus, 1)

		args = {
			"dt": po.doctype,
			"dn": po.name,
			"payment_request_type": "Outward",
			"party_type": "Supplier",
			"party": po.supplier,
			"party_name": po.supplier_name,
		}
		partly_pr = make_payment_request(**args)
		doc_pr = frappe.get_doc("Payment Request", partly_pr.name)
		doc_pr.grand_total = po.grand_total
		doc_pr.submit()
		po_status = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status, "To Receive and Bill")

	def test_po_to_pr_to_pi_fully_paid_TC_B_087(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		create_company()
		create_supplier(supplier_name="_Test Supplier")
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_item("_Test Item")
		get_or_create_fiscal_year("_Test Company")

		purchase_tax = frappe.new_doc("Purchase Taxes and Charges Template")
		purchase_tax.title = "TEST"
		purchase_tax.company = "_Test Company"

		purchase_tax.append(
			"taxes",
			{
				"category": "Total",
				"add_deduct_tax": "Add",
				"charge_type": "On Net Total",
				"account_head": "Stock In Hand - _TC",
				"rate": 100,
				"description": "GST",
			},
		)

		purchase_tax.save()

		po = create_purchase_order(do_not_save=True)
		po.taxes_and_charges = purchase_tax.name
		po.save()
		po.submit()
		po_status_before = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status_before, "To Receive and Bill")

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()

		po_status_after_pr = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status_after_pr, "To Bill")

		pi = make_purchase_invoice(pr.name)
		pi.is_paid = 1
		pi.mode_of_payment = "Cash"
		pi.cash_bank_account = "Cash - _TC"
		pi.paid_amount = pr.grand_total
		pi.save()
		pi.submit()

		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Paid")

		po_status_after_paid = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status_after_paid, "Completed")

	def test_po_to_pr_to_pi_partly_paid_TC_B_089(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company_and_supplier as create_data,
		)

		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		warehouse = "Stores - TC-3"
		tax_category = frappe.get_doc({"doctype": "Tax Category", "title": "test_category"}).insert(
			ignore_if_duplicate=1
		)

		purchase_tax = frappe.get_doc(
			{
				"doctype": "Purchase Taxes and Charges Template",
				"title": "Test Template",
				"company": company,
				"tax_category": tax_category,
				"taxes": [
					{
						"category": "Total",
						"add_deduct_tax": "Add",
						"charge_type": "On Net Total",
						"account_head": "Cash - TC-3",
						"rate": 100,
						"description": "GST",
					}
				],
			}
		).insert(ignore_if_duplicate=1)

		po = create_purchase_order(
			company=company,
			item_code=item.item_code,
			warehouse=warehouse,
			supplier=supplier,
			do_not_submit=True,
		)
		po.taxes_and_charges = purchase_tax.name
		po.save()
		po.submit()
		po_status_before = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status_before, "To Receive and Bill")

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()

		po_status_after_pr = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status_after_pr, "To Bill")

		pi = make_purchase_invoice(pr.name)
		pi.is_paid = 1
		pi.mode_of_payment = "Cash"
		pi.cash_bank_account = "Cash - TC-3"
		pi.paid_amount = pr.grand_total / 2
		pi.bill_no = "test_bill_1122"
		pi.save()
		pi.submit()

		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Partly Paid")

		po_status_after_paid = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status_after_paid, "Completed")

	def test_po_return_TC_B_043(self):
		# Scenario : PO => PR => PI => PI(Return)
		frappe._dict()
		po_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"qty": 6,
			"rate": 100,
		}

		doc_po = create_purchase_order(**po_data)
		self.assertEqual(doc_po.docstatus, 1)

		doc_pr = make_pr_for_po(doc_po.name)
		self.assertEqual(doc_pr.docstatus, 1)

		doc_pi = make_pi_against_pr(doc_pr.name)
		self.assertEqual(doc_pi.docstatus, 1)
		self.assertEqual(doc_pi.items[0].qty, doc_po.items[0].qty)
		self.assertEqual(doc_pi.grand_total, doc_po.grand_total)

		doc_returned_pi = make_return_pi(doc_pi.name)
		self.assertEqual(doc_returned_pi.total_qty, -doc_po.total_qty)
		doc_pi.reload()
		self.assertEqual(doc_pi.status, "Debit Note Issued")
		self.assertEqual(doc_returned_pi.status, "Return")

	def test_po_full_payment_TC_B_045(self):
		# Scenario : PO => Payment Entry => PR => PI => PI(Return)
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("_test_item")
		warehouse = "Stores - TC-3"
		po_data = {
			"company": company,
			"item_code": item.item_code,
			"warehouse": warehouse,
			"qty": 6,
			"rate": 100,
			"supplier": supplier,
			"uom": "Nos",
		}

		doc_po = create_purchase_order(**po_data)
		self.assertEqual(doc_po.docstatus, 1)

		doc_pe = get_payment_entry("Purchase Order", doc_po.name, doc_po.grand_total)
		doc_pe.reference_no = "123"
		doc_pe.insert()
		doc_pe.submit()
		# doc_pe.paid_from = "Cash"

		doc_pr = make_pr_for_po(doc_po.name)
		self.assertEqual(doc_pr.docstatus, 1)

		doc_pi = make_pi_against_pr(doc_pr.name, args={"is_paid": 1, "cash_bank_account": doc_pe.paid_from})
		self.assertEqual(doc_pi.docstatus, 1)
		self.assertEqual(doc_pi.items[0].qty, doc_po.items[0].qty)
		self.assertEqual(doc_pi.grand_total, doc_po.grand_total)

		doc_pi.reload()
		doc_po.reload()
		self.assertEqual(doc_pi.status, "Paid")
		self.assertEqual(doc_po.status, "Completed")

	def test_po_with_pricing_rule_TC_B_046(self):
		# Scenario : PO => Pricing Rule => PR => PI
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import get_or_create_price_list

		get_data = get_company_or_supplier()
		company = get_data.get("company")
		supplier = get_data.get("supplier")
		item = make_test_item("_test_item_2")
		price_list = get_or_create_price_list()

		po_data = {
			"company": company,
			"item_code": item.item_code,
			"warehouse": "Stores - TC-5",
			"supplier": supplier,
			"schedule_date": today(),
			"qty": 1,
			"currency": "INR",
			"buying_price_list": price_list,
		}

		pricing_rule_record = {
			"doctype": "Pricing Rule",
			"title": "Discount on _Test Item",
			"apply_on": "Item Code",
			"items": [
				{
					"item_code": item.item_code,
				}
			],
			"price_or_product_discount": "Price",
			"applicable_for": "Supplier",
			"supplier": supplier,
			"buying": 1,
			"currency": "INR",
			"min_qty": 1,
			"min_amt": 100,
			"valid_from": today(),
			"rate_or_discount": "Discount Percentage",
			"discount_percentage": 10,
			"price_list": price_list,
			"company": company,
		}
		if not frappe.db.exists("Pricing Rule", {"title": "Discount on _Test Item"}):
			rule = frappe.get_doc(pricing_rule_record)
			rule.insert()

		frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": price_list,
				"item_code": item.item_code,
				"price_list_rate": 130,
			}
		).insert()

		doc_po = create_purchase_order(**po_data)
		doc_po_item = doc_po.items[0]
		self.assertEqual(doc_po_item.discount_percentage, 10)
		self.assertEqual(doc_po_item.rate, 117)
		self.assertEqual(doc_po_item.amount, 117)

		doc_pr = make_pr_for_po(doc_po.name)

		doc_pi = make_pi_against_pr(doc_pr.name)
		pi_item = doc_pi.items[0]
		self.assertEqual(pi_item.rate, 117)
		self.assertEqual(pi_item.amount, 117)
		frappe.delete_doc_if_exists("Pricing Rule", "Discount on _Test Item")

	def setUp(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		validate_fiscal_year("_Test Company")
		create_company_and_suppliers()

	def tearDown(self):
		frappe.db.rollback()

	def test_po_with_pricing_rule_TC_B_047(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import get_or_create_price_list

		# Scenario : PO => Pricing Rule => PR
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("_test_item")
		warehouse = "Stores - TC-3"
		price_list = get_or_create_price_list()
		get_or_create_fiscal_year(company)
		po_data = {
			"company": company,
			"item_code": item.item_code,
			"warehouse": warehouse,
			"supplier": supplier,
			"schedule_date": today(),
			"qty": 1,
			"currency": "INR",
			"buying_price_list": price_list,
		}

		pricing_rule_record = {
			"doctype": "Pricing Rule",
			"title": "Discount on _Test Item",
			"apply_on": "Item Code",
			"items": [
				{
					"item_code": item.item_code,
				}
			],
			"price_or_product_discount": "Price",
			"applicable_for": "Supplier",
			"supplier": supplier,
			"buying": 1,
			"currency": "INR",
			"min_qty": 1,
			"min_amt": 100,
			"valid_from": today(),
			"rate_or_discount": "Discount Percentage",
			"discount_percentage": 10,
			"price_list": price_list,
			"company": company,
		}
		if not frappe.db.exists("Pricing Rule", {"title": "Discount on _Test Item"}):
			rule = frappe.get_doc(pricing_rule_record)
			rule.insert()

		frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": price_list,
				"item_code": item.item_code,
				"price_list_rate": 130,
			}
		).insert()

		doc_po = create_purchase_order(**po_data)
		po_item = doc_po.items[0]
		self.assertEqual(po_item.discount_percentage, 10)
		self.assertEqual(po_item.rate, 117)
		self.assertEqual(po_item.amount, 117)

		doc_pr = make_pr_for_po(doc_po.name)
		pr_item = doc_pr.items[0]
		self.assertEqual(pr_item.rate, 117)
		self.assertEqual(pr_item.amount, 117)
		frappe.delete_doc_if_exists("Pricing Rule", "Discount on _Test Item")

	def test_po_additional_discount_TC_B_052(self):
		# Scenario : PO => PR => PI [With Additional Discount]

		po_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"supplier": "_Test Supplier",
			"schedule_date": "2025-01-13",
			"qty": 1,
			"rate": 10000,
			"apply_discount_on": "Net Total",
			"additional_discount_percentage": 10,
			"do_not_submit": 1,
		}

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = "_Test Company"
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax IGST", "company": "_Test Company"}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		doc_po = create_purchase_order(**po_data)
		doc_po.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 12,
				"description": "Input GST",
			},
		)
		doc_po.submit()
		self.assertEqual(doc_po.discount_amount, 1000)
		self.assertEqual(doc_po.grand_total, 10080)

		doc_pr = make_pr_for_po(doc_po.name)
		doc_pi = make_pi_against_pr(doc_pr.name)

		self.assertEqual(doc_pi.discount_amount, 1000)
		self.assertEqual(doc_pi.grand_total, 10080)

		# Accounting Ledger Checks
		pi_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": doc_pi.name}, fields=["account", "debit", "credit"]
		)

		# PI Ledger Validation
		pi_total = sum(entry["debit"] for entry in pi_gl_entries)
		self.assertEqual(pi_total, 10080)


	def test_po_additional_discount_TC_B_055(self):
		# Scenario : PO => PI [With Additional Discount]

		po_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"supplier": "_Test Supplier",
			"schedule_date": "2025-01-13",
			"qty": 1,
			"rate": 10000,
			"apply_discount_on": "Net Total",
			"additional_discount_percentage": 10,
			"do_not_submit": 1,
		}

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = "_Test Company"
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax IGST", "company": "_Test Company"}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		doc_po = create_purchase_order(**po_data)
		doc_po.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 12,
				"description": "Input GST",
			},
		)
		doc_po.submit()
		self.assertEqual(doc_po.discount_amount, 1000)
		self.assertEqual(doc_po.grand_total, 10080)

		doc_pi = make_pi_from_po(doc_po.name)
		doc_pi.insert()
		doc_pi.submit()
		self.assertEqual(doc_pi.discount_amount, 1000)
		self.assertEqual(doc_pi.grand_total, 10080)

		# Accounting Ledger Checks
		pi_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": doc_pi.name}, fields=["account", "debit", "credit"]
		)

		# PI Ledger Validation
		pi_total = sum(entry["debit"] for entry in pi_gl_entries)
		self.assertEqual(pi_total, 10080)

	def test_po_additional_discount_TC_B_058(self):
		# Scenario : PO => PR => PI [With Additional Discount on Grand Total]

		po_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"supplier": "_Test Supplier",
			"schedule_date": "2025-01-13",
			"qty": 1,
			"rate": 10000,
			"apply_discount_on": "Grand Total",
			"additional_discount_percentage": 10,
			"do_not_submit": 1,
		}

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = "_Test Company"
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax IGST", "company": "_Test Company"}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		doc_po = create_purchase_order(**po_data)
		doc_po.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 12,
				"description": "Input GST",
			},
		)
		doc_po.submit()
		self.assertEqual(doc_po.discount_amount, 1120)
		self.assertEqual(doc_po.grand_total, 10080)

		doc_pr = make_pr_for_po(doc_po.name)
		doc_pi = make_pi_against_pr(doc_pr.name)

		self.assertEqual(doc_pi.discount_amount, 1120)
		self.assertEqual(doc_pi.grand_total, 10080)

		# Accounting Ledger Checks
		pi_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": doc_pi.name}, fields=["account", "debit", "credit"]
		)

		# PI Ledger Validation
		pi_total = sum(entry["debit"] for entry in pi_gl_entries)
		self.assertEqual(pi_total, 10080)

	def test_po_additional_discount_TC_B_061(self):
		# Scenario : PO => PI [With Additional Discount]

		po_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"supplier": "_Test Supplier",
			"schedule_date": "2025-01-13",
			"qty": 1,
			"rate": 10000,
			"apply_discount_on": "Grand Total",
			"additional_discount_percentage": 10,
			"do_not_submit": 1,
		}

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = "_Test Company"
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax IGST", "company": "_Test Company"}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		doc_po = create_purchase_order(**po_data)
		doc_po.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 12,
				"description": "Input GST",
			},
		)
		doc_po.submit()
		self.assertEqual(doc_po.discount_amount, 1120)
		self.assertEqual(doc_po.grand_total, 10080)

		doc_pi = make_pi_from_po(doc_po.name)
		doc_pi.insert()
		doc_pi.submit()
		self.assertEqual(doc_pi.discount_amount, 1120)
		self.assertEqual(doc_pi.grand_total, 10080)

		# Accounting Ledger Checks
		pi_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": doc_pi.name}, fields=["account", "debit", "credit"]
		)

		# PI Ledger Validation
		pi_total = sum(entry["debit"] for entry in pi_gl_entries)
		self.assertEqual(pi_total, 10080)

	def test_po_additional_discount_TC_B_063(self):
		# Scenario : PO => PI [With Additional Discount]

		po_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"supplier": "_Test Supplier",
			"schedule_date": "2025-01-13",
			"qty": 1,
			"rate": 10000,
			"apply_discount_on": "Grand Total",
			"additional_discount_percentage": 10,
			"do_not_submit": 1,
		}

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = "_Test Company"
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax IGST", "company": "_Test Company"}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		doc_po = create_purchase_order(**po_data)
		doc_po.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 12,
				"description": "Input GST",
			},
		)
		doc_po.submit()
		self.assertEqual(doc_po.discount_amount, 1120)
		self.assertEqual(doc_po.grand_total, 10080)

	def test_po_with_additional_discount_TC_B_057(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-3"
		item_price = 10000
		item = make_test_item("Testing-31")
		item.is_purchase_item = 1
		item.is_sales_item = 0
		item.save()

		pi = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": target_warehouse,
				"items": [
					{"item_code": item.item_code, "warehouse": target_warehouse, "qty": 1, "rate": item_price}
				],
			}
		)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		self.assertEqual(len(pi.items), 1)
		self.assertEqual(pi.items[0].rate, item_price)
		self.assertEqual(pi.net_total, item_price)
		pi.apply_discount_on = "Net Total"
		pi.additional_discount_percentage = 10
		pi.save()
		pi.submit()
		self.assertEqual(pi.discount_amount, 1000)
		self.assertEqual(pi.net_total, 9000)

	def test_partial_pr_pi_flow_TC_B_103(self):
		# Scenario : PO > PR > PI
		from frappe.desk.query_report import run

		item_1 = create_item("_Test Items")
		item_2 = create_item("Books")
		supplier = create_supplier(supplier_name="_Test Supplier")
		supplier.gstin = "24AAACH7409R2Z6"   # Dummy valid GSTIN
		supplier.gst_category = "Registered Regular"
		supplier.save()

		company = "_Test Company"
		if not frappe.db.exists("Company", company):
			company = frappe.new_doc("Company")
			company.company_name = company
			company.country = ("India",)
			company.default_currency = ("INR",)
			company.save()
		else:
			company = frappe.get_doc("Company", company)
		warehouse = create_warehouse("Stores - _TC")
		po_data = {
			"doctype": "Purchase Order",
			"supplier": supplier.name,
			"company": company.name,
			"transaction_date": today(),
			"warehouse": warehouse,
			"items": [
				{
					"item_code": item_1.item_code,
					"qty": 10,
					"rate": 100,
					"warehouse": warehouse,
					"schedule_date": today(),
				},
				{
					"item_code": item_2.item_code,
					"qty": 5,
					"rate": 500,
					"warehouse": warehouse,
					"schedule_date": add_days(today(), 1),
				},
			],
		}
		doc_po = frappe.get_doc(po_data)
		doc_po.insert()
		taxes = create_taxes_for_interstate()
		for tax in taxes:
			doc_po.append("taxes", tax)
		doc_po.submit()
		purchase_order_analysis = run(
			"Purchase Order Analysis",
			filters={
				"company": doc_po.company,
				"from_date": doc_po.schedule_date,
				"to_date": doc_po.schedule_date,
				"name": doc_po.name,
			},
		)
		result_list = purchase_order_analysis.get("result", [])
		for result in result_list:
			if isinstance(result, dict):
				if result.get("item_code") == item_1:
					self.assertEqual(result.get("status"), "To Receive and Bill")
					self.assertEqual(result.get("pending_qty"), 10)
					self.assertEqual(result.get("billed_qty"), 0)
					self.assertEqual(result.get("billed_amount"), 0)
					self.assertEqual(result.get("qty_to_bill"), 10)
					self.assertEqual(result.get("pending_amount"), 1000)
					self.assertEqual(result.get("received_qty"), 0)
				elif result.get("item_code") == item_2:
					self.assertEqual(result.get("status"), "To Receive and Bill")
					self.assertEqual(result.get("pending_qty"), 5)
					self.assertEqual(result.get("billed_qty"), 0)
					self.assertEqual(result.get("billed_amount"), 0)
					self.assertEqual(result.get("qty_to_bill"), 5)
					self.assertEqual(result.get("pending_amount"), 2500)
					self.assertEqual(result.get("received_qty"), 0)

		pr = make_purchase_receipt(doc_po.name)
		for item in pr.items:
			if item.item_code == item_1:
				item.qty = 2
			elif item.item_code == item_2:
				item.qty = 5
		pr.save()
		pr.submit()
		purchase_order_analysis_2 = run(
			"Purchase Order Analysis",
			filters={
				"company": doc_po.company,
				"from_date": doc_po.schedule_date,
				"to_date": doc_po.schedule_date,
				"name": doc_po.name,
			},
		)
		result_list_2 = purchase_order_analysis_2.get("result", [])
		result_list_2 = purchase_order_analysis_2.get("result", [])
		for result_2 in result_list_2:
			if isinstance(result_2, dict):
				if result_2.get("item_code") == item_1:
					self.assertEqual(result_2.get("status"), "To Receive and Bill")
					self.assertEqual(result_2.get("pending_qty"), 8)
					self.assertEqual(result_2.get("billed_qty"), 0)
					self.assertEqual(result_2.get("billed_amount"), 0)
					self.assertEqual(result_2.get("qty_to_bill"), 10)
					self.assertEqual(result_2.get("pending_amount"), 1000)
					self.assertEqual(result_2.get("received_qty"), 2)

				elif result_2.get("item_code") == item_2:
					self.assertEqual(result_2.get("status"), "To Receive and Bill")
					self.assertEqual(result_2.get("pending_qty"), 0)
					self.assertEqual(result_2.get("billed_qty"), 0)
					self.assertEqual(result_2.get("billed_amount"), 0)
					self.assertEqual(result_2.get("qty_to_bill"), 5)
					self.assertEqual(result_2.get("pending_amount"), 2500)
					self.assertEqual(result_2.get("received_qty"), 5)
		pi = make_test_pi(pr.name)
		self.assertEqual(pi.items[0].qty, 10)
		self.assertEqual(pi.items[0].rate, 100)
		self.assertEqual(pi.items[0].amount, 1000)
		self.assertEqual(pi.items[1].qty, 5)
		self.assertEqual(pi.items[1].rate, 500)
		self.assertEqual(pi.items[1].amount, 2500)
		self.assertEqual(pi.total, 3500)

	def test_previous_row_total_flow_TC_B_141(self):
		supplier = create_supplier(supplier_name="_Test Supplier")
		company = "_Test Company"
		if not frappe.db.exists("Company", company):
			company = frappe.new_doc("Company")
			company.company_name = company
			company.country = ("India",)
			company.default_currency = ("INR",)
			company.save()
		else:
			company = frappe.get_doc("Company", company)
		item = create_item("Test Item")
		acc = frappe.new_doc("Account")
		acc.account_name = "Environmental Cess a/c"
		acc.parent_account = "Indirect Expenses - _TC"
		acc.account_type = "Chargeable"
		acc.company = company.name
		account_name_cess = frappe.db.exists(
			"Account", {"account_name": "Environmental Cess a/c", "company": company.name}
		)
		if not account_name_cess:
			account_name_cess = acc.insert(ignore_permissions=True)

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax CGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = company.name
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax CGST", "company": company.name}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax SGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = company.name
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax SGST", "company": company.name}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		taxes = create_taxes_interstate()
		taxes.append(
			{
				"charge_type": "On Previous Row Total",
				"account_head": account_name_cess,
				"rate": 5,
				"description": "Environmental Cess",
				"row_id": 2,
				"category": "Total",
			}
		)
		po_data = {
			"company": company.name,
			"supplier": supplier.name,
			"warehouse": create_warehouse("Stores - _TC", company=company.name),
			"item_code": item.item_code,
			"qty": 10,
			"rate": 100,
			"do_not_submit": 1,
		}
		doc_po = create_purchase_order(**po_data)
		for tax in taxes:
			doc_po.append("taxes", tax)
		doc_po.save()
		doc_po.submit()
		self.assertEqual(doc_po.grand_total, 1239)
		pr = make_pr_for_po(doc_po.name, received_qty=10)
		self.assertEqual(pr.items[0].received_qty, 10)
		self.assertEqual(pr.items[0].rate, 100)
		pi = make_pi_against_pr(pr.name)
		self.assertEqual(pi.items[0].qty, 10)
		self.assertEqual(pi.items[0].rate, 100)

	@change_settings("Accounts Settings", {"check_supplier_invoice_uniqueness": 0})
	def test_po_pr_pi_with_shipping_rule_TC_B_064(self):
		# Scenario : PO=>PR=>PI [With Shipping Rule]
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		warehouse = "Stores - TC-5"

		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "Net Weight Shipping Rule",
				"calculate_based_on": "Fixed",
				"shipping_rule_type": "Buying",
				"account": "Cash - TC-5",
				"cost_center": "Main - TC-5",
				"shipping_amount": 200,
			}
		).insert(ignore_if_duplicate=1)

		# Create Purchase Order
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"set_warehouse": warehouse,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 1,
						"rate": 3000,
						"warehouse": warehouse,
					}
				],
				"shipping_rule": shipping_rule.name,
			}
		)
		po.insert()
		po.submit()

		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.grand_total, 3200.0)
		self.assertEqual(po.status, "To Receive and Bill")

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.status, "To Bill")

		sle = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": pr.name}, fields=["actual_qty", "item_code"]
		)
		self.assertEqual(len(sle), 1)
		self.assertEqual(sle[0]["actual_qty"], 1)

		gl_entries_pr = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		for gl in gl_entries_pr:
			if gl["account"] == "Stock In Hand - TC-5":
				self.assertEqual(gl["debit"], 3200)
			elif gl["account"] == "Stock Received But Not Billed - TC-5":
				self.assertEqual(gl["credit"], 3000)
			elif gl["account"] == "_Test Account Shipping Charges - TC-5":
				self.assertEqual(gl["credit"], 200)

		pi = make_purchase_invoice(pr.name)
		pi.insert()
		pi.submit()
		self.assertEqual(pi.status, "Unpaid")
		gl_entries_pi = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		for gl_entry in gl_entries_pi:
			if gl_entry["account"] == "Creditors - TC-5":
				self.assertEqual(gl_entry["credit"], 3200)
			elif gl_entry["account"] == "Stock Received But Not Billed - TC-5":
				self.assertEqual(gl_entry["debit"], 3000)

		po.reload()
		pr.reload()
		self.assertEqual(po.status, "Completed")
		self.assertEqual(pr.status, "Completed")

	def test_po_pi_pr_flow_TC_B_067(self):
		# Scenario : PO => PI => PR [With Shipping Rule]
		args = {"calculate_based_on": "Fixed", "shipping_amount": 200}
		doc_shipping_rule = create_shipping_rule("Buying", "_Test Shipping Rule _TC", args)
		item = create_item("_Test Item")
		supplier = create_supplier(supplier_name="_Test Supplier PO")
		company = "_Test Company"
		if not frappe.db.exists("Company", company):
			company = frappe.new_doc("Company")
			company.company_name = company
			company.country = ("India",)
			company.default_currency = ("INR",)
			company.save()
		else:
			company = frappe.get_doc("Company", company)
		po_data = {
			"company": company.name,
			"supplier": supplier.name,
			"item_code": item.item_code,
			"warehouse": create_warehouse("Stores - _TC", company=company.name),
			"qty": 1,
			"rate": 3000,
			"shipping_rule": doc_shipping_rule.name,
		}

		doc_po = create_purchase_order(**po_data)
		self.assertEqual(doc_po.docstatus, 1)

		doc_pi = make_pi_direct_aganist_po(doc_po.name)
		self.assertEqual(doc_pi.docstatus, 1)

		doc_pr = make_pr_form_pi(doc_pi.name)
		doc_po.reload()
		self.assertEqual(doc_po.status, "Completed")
		self.assertEqual(doc_pr.status, "Completed")

	@if_app_installed("india_compliance")
	def test_inter_state_CGST_and_SGST_TC_B_097(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - TC-5"
		item = make_test_item("_test_item")
		tax_account = create_or_get_purchase_taxes_template(company)
		po = create_purchase_order(
			company=company,
			supplier=supplier,
			qty=1,
			rate=100,
			warehouse=warehouse,
			item_code=item.item_code,
			do_not_save=True,
		)
		taxes = [
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("sgst_account"),
				"description": "SGST",
			},
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("cgst_account"),
				"description": "CGST",
			},
		]
		for tax in taxes:
			po.append("taxes", tax)
		po.save()
		po.submit()
		po.reload()

		self.assertEqual(po.grand_total, 118)

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()
		pr.reload()
		account_entries = frappe.db.get_all(
			"GL Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["account", "debit", "credit"],
		)
		for entries in account_entries:
			if entries.account == "Stock In Hand - TC-5":
				self.assertEqual(entries.debit, 100)
			if entries.account == "Stock Received But Not Billed - TC-5":
				self.assertEqual(entries.credit, 100)

		stock_entries = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": pr.name}, "item_code")
		self.assertEqual(stock_entries, pr.items[0].item_code)

		pi = make_pi_from_pr(pr.name)
		pi.save()
		pi.submit()

		account_entries_pi = frappe.db.get_all(
			"GL Entry", {"voucher_no": pi.name}, ["account", "debit", "credit"]
		)
		for entries in account_entries_pi:
			if entries.account == "Input Tax SGST - TC-5":
				self.assertEqual(entries.debit, 9)
			if entries.account == "Input Tax CGST - TC-5":
				self.assertEqual(entries.debit, 9)
			if entries.account == "Stock Received But Not Billed - TC-5":
				self.assertEqual(entries.debit, 100)
			if entries.account == "Creditors - TC-5":
				self.assertEqual(entries.credit, 118.0)

	def test_outer_state_IGST_TC_B_098(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		company = "_Test Company"
		if not frappe.db.exists("Tax Category", "Out-State"):
			tax_category = frappe.new_doc("Tax Category")
			tax_category.title = "Out-State"
			tax_category.save()

		exists_purchase_tax = frappe.db.get_value(
			"Purchase Taxes and Charges Template", {"company": company, "tax_category": "Out-State"}, "name"
		)
		if exists_purchase_tax is None:
			purchase_tax_and_template = frappe.new_doc("Purchase Taxes and Charges Template")
			purchase_tax_and_template.title = "Test"
			purchase_tax_and_template.company = company
			purchase_tax_and_template.tax_category = "Out-State"
			purchase_tax_and_template.append(
				"taxes",
				{
					"category": "Total",
					"add_deduct_tax": "Add",
					"rate": 18,
					"account_head": "Stock In Hand - _TC",
					"description": "test",
				},
			)
			purchase_tax_and_template.save()

			purchase_tax = purchase_tax_and_template.name
		else:
			purchase_tax = exists_purchase_tax

		get_or_create_fiscal_year("_Test Company")

		create_supplier(supplier_name="_Test Registered Supplier")
		warehouse = create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company=company,
		)
		create_item("_Test Item", warehouse=warehouse)
		po = create_purchase_order(supplier="_Test Registered Supplier", qty=1, rate=100, do_not_save=True)
		po.save()

		purchase_tax_and_value = frappe.db.get_value(
			"Purchase Taxes and Charges Template",
			{"company": po.company, "tax_category": "Out-State"},
			"name",
		)
		po.taxes_and_charges = purchase_tax_and_value
		po.save()
		po.submit()
		po.reload()
		self.assertEqual(po.grand_total, 118)
		pr = make_purchase_receipt(po.name)
		pr.taxes_and_charges = purchase_tax
		pr.save()

		frappe.db.set_value("Company", pr.company, "enable_perpetual_inventory", 1)
		frappe.db.set_value("Company", pr.company, "enable_provisional_accounting_for_non_stock_items", 1)
		frappe.db.set_value(
			"Company", pr.company, "stock_received_but_not_billed", "Stock Received But Not Billed - _TC"
		)
		frappe.db.set_value("Company", pr.company, "default_inventory_account", "Stock In Hand - _TC")
		frappe.db.set_value("Company", pr.company, "default_provisional_account", "Stock In Hand - _TC")

		pr.submit()
		pr.reload()

		account_entries = frappe.db.get_all(
			"GL Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["account", "debit", "credit"],
		)
		for entries in account_entries:
			if entries.account == "Stock In Hand - _TC":
				self.assertEqual(entries.debit, 100)
			if entries.account == "Stock Received But Not Billed - _TC":
				self.assertEqual(entries.credit, 100)

		stock_entries = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": pr.name}, "item_code")
		self.assertEqual(stock_entries, pr.items[0].item_code)
		self.assertEqual(pr.status, "To Bill")
		pi = make_pi_from_pr(pr.name)
		pi.bill_no = "TEST-BILL-001"

		pi.save()
		pi.submit()

		account_entries_pi = frappe.db.get_all(
			"GL Entry", {"voucher_no": pi.name}, ["account", "debit", "credit"]
		)
		for entries in account_entries_pi:
			if entries.account == "Input Tax IGST - _TC":
				self.assertEqual(entries.debit, 18)
			if entries.account == "Stock Received But Not Billed - _TC":
				self.assertEqual(entries.debit, 100)
			if entries.account == "Creditors - _TC":
				self.assertEqual(entries.credit, 118.0)
		pi.reload()
		self.assertEqual(pi.status, "Unpaid")

	def test_po_ignore_pricing_rule_TC_B_049(self):
		get_details = get_company_or_supplier()
		company = get_details.get("company")
		supplier = get_details.get("supplier")
		warehouse = "Stores - TC-5"
		item_price = 130
		item = make_test_item("_test_item__")

		existing_price = frappe.db.exists(
			"Item Price", {"item_code": item.item_code, "price_list": "Standard Buying"}
		)
		if not existing_price:
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"price_list": "Standard Buying",
					"item_code": item.item_code,
					"price_list_rate": item_price,
				}
			).insert()

		existing_pricing_rule = frappe.db.exists(
			"Pricing Rule", {"title": "10% Discount", "company": company}
		)
		if not existing_pricing_rule:
			frappe.get_doc(
				{
					"doctype": "Pricing Rule",
					"title": "10% Discount",
					"company": company,
					"apply_on": "Item Code",
					"items": [{"item_code": item.item_code}],
					"rate_or_discount": "Discount Percentage",
					"discount_percentage": 10,
					"selling": 0,
					"buying": 1,
				}
			).insert()

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"items": [{"item_code": item.item_code, "warehouse": warehouse, "qty": 1}],
			}
		)
		po.insert()

		self.assertEqual(len(po.items), 1)
		self.assertEqual(po.items[0].rate, 117)
		self.assertEqual(po.items[0].discount_percentage, 10)
		po.ignore_pricing_rule = 1
		po.save()
		po.submit()
		self.assertEqual(po.items[0].rate, 130)

	def test_po_pr_pi_multiple_flow_TC_B_065(self):
		# Scenario : PO=>2PR=>2PI
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		get_company_supplier = get_company_or_supplier()
		supplier = create_supplier(supplier_name="_Test Supplier 1", default_currency="INR")
		company = get_company_supplier.get("company")
		warehouse = create_warehouse("_Test Warehouse 556", company=company)
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("_Test Item_1")
		remove_existing_shipping_rules()

		doc_shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "Fixed Shipping Rule",
				"calculate_based_on": "Fixed",
				"shipping_rule_type": "Buying",
				"account": "Cash - TC-5",
				"cost_center": "Main - TC-5",
				"shipping_amount": 200,
			}
		).insert(ignore_if_duplicate=1)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"set_posting_time": 1,
				"posting_date": today(),
				"schedule_date": add_days(today(), 5),
				"shipping_rule": doc_shipping_rule.name,
				"items": [{"item_code": item.item_code, "warehouse": warehouse, "qty": 4, "rate": 3000}],
			}
		)
		po.insert()
		po.submit()

		self.assertEqual(
			po.grand_total, 12002.33, "Grand Total should include Shipping Rule (12000 + 200 = 12200)."
		)
		self.assertEqual(po.status, "To Receive and Bill", "PO status should be 'To Receive and Bill'.")

		pr_1 = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"purchase_order": po.name,
				"company": company,
				"supplier": supplier,
				"currency": "INR",
				"items": [{"item_code": item.item_code, "warehouse": warehouse, "qty": 2, "rate": 3000}],
			}
		)
		pr_1.insert()
		pr_1.submit()

		sle_pr_1 = get_sle(pr_1.name)
		self.assertEqual(sle_pr_1[0]["actual_qty"], 2)
		gl_entries_pr_1 = get_gl_entries(pr_1.name)
		for gl_entry_pr in gl_entries_pr_1:
			if gl_entry_pr["account"] == "Stock In Hand - TC-5":
				self.assertEqual(gl_entry_pr["debit"], 6200)
			elif gl_entry_pr["account"] == "Cash - TC-5":
				self.assertEqual(gl_entry_pr["credit"], 200)
		pi_1 = make_pi_against_pr(pr_1.name)
		self.assertEqual(pi_1.status, "Unpaid")

		pi_1 = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"purchase_receipt": pr_1.name,
				"supplier": supplier,
				"currency": "INR",
				"company": company,
				"items": [{"item_code": item.item_code, "qty": 2, "rate": 3000}],
			}
		)
		pi_1.insert()
		pi_1.submit()

		gl_entries_pi_1 = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi_1.name}, fields=["account", "debit", "credit"]
		)
		expected_gl_entries_pi_1 = [
			{"account": "Stock Received But Not Billed - TC-5", "debit": 6000.0, "credit": 0.0},
			{"account": "Creditors - TC-5", "debit": 0.0, "credit": 6000.0},
		]
		self.assertEqual(gl_entries_pi_1, expected_gl_entries_pi_1)
		pr_1.reload()
		self.assertEqual(pr_1.status, "Completed")

		pr_2 = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"purchase_order": po.name,
				"company": company,
				"supplier": supplier,
				"currency": "INR",
				"items": [{"item_code": item.item_code, "warehouse": warehouse, "qty": 2, "rate": 3000}],
			}
		)
		pr_2.insert()
		pr_2.submit()

		gl_entries_pr_2 = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr_2.name}, fields=["account", "debit", "credit"]
		)
		expected_gle2 = [
			{"account": "Stock Received But Not Billed - TC-5", "debit": 0.0, "credit": 6000.0},
			{"account": "_Test Warehouse 556 - TC-5", "debit": 6000.0, "credit": 0.0},
		]
		self.assertEqual(gl_entries_pr_2, expected_gle2)
		pi_2 = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"purchase_receipt": pr_2.name,
				"supplier": supplier,
				"currency": "INR",
				"company": company,
				"items": [{"item_code": item.item_code, "qty": 2, "rate": 3000}],
			}
		)
		pi_2.insert()
		pi_2.submit()

		gl_entries_pi_2 = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi_2.name}, fields=["account", "debit", "credit"]
		)
		expected_gle_2 = [
			{"account": "Stock Received But Not Billed - TC-5", "debit": 6000.0, "credit": 0.0},
			{"account": "Creditors - TC-5", "debit": 0.0, "credit": 6000.0},
		]
		self.assertEqual(gl_entries_pi_2, expected_gle_2)
		pr_2.reload()
		po.reload()

		self.assertEqual(pr_1.purchase_order, po.name, "1st PR should be linked to the PO.")
		self.assertEqual(pr_2.purchase_order, po.name, "2nd PR should be linked to the PO.")
		self.assertEqual(pi_1.purchase_receipt, pr_1.name, "1st PI should be linked to the 1st PR.")
		self.assertEqual(pi_2.purchase_receipt, pr_2.name, "2nd PI should be linked to the 2nd PR.")
		pi_1.reload()
		pi_2.cancel()
		pr_2.cancel()
		po.cancel()

		self.assertEqual(len(po.items), 1)

	def test_po_to_pi_with_deferred_expense_TC_B_094(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-5"
		frappe.db.set_value("Company", company, "default_deferred_expense_account", "Cash - TC-5")

		item = make_test_item("_test_expense")
		item.is_stock_item = 0
		item.enable_deferred_expense = 1
		item.save()

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"items": [
					{"item_code": item.item_code, "qty": 1, "rate": 1000, "warehouse": target_warehouse}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)

		pi = make_pi_from_po(po.name)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		item = frappe.get_doc("Item", item.item_code)
		pi.items[0].enable_deferred_expense = item.enable_deferred_expense
		pi.save()
		self.assertEqual(pi.items[0].enable_deferred_expense, 1)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)

	def test_po_with_actual_account_type_TC_B_133(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		create_supplier(supplier_name="_Test Supplier")
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_item("_Test Item")
		get_or_create_fiscal_year("_Test Company")
		po = create_purchase_order(qty=10, rate=1000, do_not_save=True)
		po.save()
		exists_purchase_tax = frappe.db.get_value(
			"Purchase Taxes and Charges Template",
			{"company": "_Test Company", "tax_category": "In-State"},
			"name",
		)
		if exists_purchase_tax is None:
			purchase_tax_template = frappe.new_doc("Purchase Taxes and Charges Template")
			purchase_tax_template.title = "Test"
			purchase_tax_template.company = po.company
			purchase_tax_template.tax_category = "In-State"
			value_list = [
				{
					"category": "Total",
					"add_deduct_tax": "Add",
					"charge_type": "On Net Total",
					"account_head": "Stock In Hand - _TC",
					"description": "test",
					"tax_amount": 100,
					"rate": 9,
				},
				{
					"category": "Total",
					"add_deduct_tax": "Add",
					"charge_type": "On Net Total",
					"account_head": "Stock In Hand - _TC",
					"description": "test",
					"tax_amount": 100,
					"rate": 9,
				},
			]
			for items in value_list:
				purchase_tax_template.append("taxes", items)
			purchase_tax_template.save()
			purchase_tax = purchase_tax_template.name
		else:
			purchase_tax = exists_purchase_tax

		po.taxes_and_charges = purchase_tax
		po.save()

		po.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": "Freight and Forwarding Charges - _TC",
				"description": "Freight and Forwarding Charges",
				"tax_amount": 100,
			},
		)
		po.save()
		po.submit()
		self.assertEqual(po.grand_total, 11900)
		self.assertEqual(po.taxes_and_charges_added, 1900)

		pr = make_purchase_receipt(po.name)
		pr.save()

		frappe.db.set_value("Company", pr.company, "enable_perpetual_inventory", 1)
		frappe.db.set_value("Company", pr.company, "enable_provisional_accounting_for_non_stock_items", 1)
		frappe.db.set_value(
			"Company", pr.company, "stock_received_but_not_billed", "Stock Received But Not Billed - _TC"
		)
		frappe.db.set_value("Company", pr.company, "default_inventory_account", "Stock In Hand - _TC")
		frappe.db.set_value("Company", pr.company, "default_provisional_account", "Stock In Hand - _TC")

		pr.submit()
		self.assertEqual(po.grand_total, po.grand_total)
		self.assertEqual(po.taxes_and_charges_added, po.taxes_and_charges_added)

		account_entries_pr = frappe.db.get_all(
			"GL Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["account", "debit", "credit"],
		)
		for entries in account_entries_pr:
			if entries.account == "Stock Received But Not Billed - _TC":
				self.assertEqual(entries.credit, pr.total)
			if entries.account == "Stock In Hand - _TC":
				self.assertEqual(entries.debit, pr.total)

		stock_entries_item = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": pr.name}, "item_code")
		stock_entries_qty = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": pr.name}, "actual_qty")
		self.assertEqual(stock_entries_item, pr.items[0].item_code)
		self.assertEqual(stock_entries_qty, pr.items[0].qty)

		pi = make_pi_from_pr(pr.name)
		pi.save()
		pi.submit()

		account_entries_pi = frappe.db.get_all(
			"GL Entry", {"voucher_no": pi.name}, ["account", "debit", "credit"]
		)

		for entries in account_entries_pi:
			if entries.account == "Freight and Forwarding Charges - _TC":
				self.assertEqual(entries.debit, 100)
			if entries.account == "Input Tax SGST - _TC":
				self.assertEqual(entries.debit, 900)
			if entries.account == "Input Tax CGST - _TC":
				self.assertEqual(entries.debit, 900)
			if entries.account == "Stock Received But Not Billed - _TC":
				self.assertEqual(entries.debit, 10000)
			if entries.account == "Creditors - _TC":
				self.assertEqual(entries.credit, 11900)

	@if_app_installed("india_compliance")
	def test_po_with_on_net_total_account_type_TC_B_134(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - TC-5"
		tax_account = create_or_get_purchase_taxes_template(company)
		item = make_test_item("test_item")
		parking_charges_account = create_new_account(
			account_name="Parking Charges Account", company=company, parent_account="Indirect Expenses - TC-5"
		)
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [{"item_code": item.item_code, "schedule_date": today(), "qty": 10, "rate": 100}],
			}
		)
		taxes = [
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("sgst_account"),
				"description": "SGST",
			},
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("cgst_account"),
				"description": "CGST",
			},
			{
				"charge_type": "On Net Total",
				"account_head": parking_charges_account,
				"description": parking_charges_account,
				"rate": 5,
			},
		]
		for tax in taxes:
			po.append("taxes", tax)
		po.insert()
		po.submit()
		self.assertEqual(po.grand_total, 1230)
		self.assertEqual(po.taxes_and_charges_added, 230)
		pr = make_purchase_receipt(po.name)
		pr.save()

		frappe.db.set_value(
			"Company",
			company,
			{
				"enable_perpetual_inventory": 1,
				"enable_provisional_accounting_for_non_stock_items": 1,
				"stock_received_but_not_billed": "Stock Received But Not Billed - TC-5",
				"default_inventory_account": "Stock In Hand - TC-5",
				"default_provisional_account": "Stock In Hand - TC-5",
			},
		)

		pr.submit()
		self.assertEqual(po.grand_total, po.grand_total)
		self.assertEqual(po.taxes_and_charges_added, po.taxes_and_charges_added)

		account_entries_pr = frappe.db.get_all(
			"GL Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["account", "debit", "credit"],
		)

		for entries in account_entries_pr:
			if entries.account == "Stock Received But Not Billed - TC-5":
				self.assertEqual(entries.credit, 1000)
			if entries.account == "Stock In Hand - TC-5":
				self.assertEqual(entries.debit, 1000)

		stock_entries_item = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": pr.name}, "item_code")
		stock_entries_qty = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": pr.name}, "actual_qty")
		self.assertEqual(stock_entries_item, pr.items[0].item_code)
		self.assertEqual(stock_entries_qty, pr.items[0].qty)

		pi = make_pi_from_pr(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.save()
		pi.submit()

		account_entries_pi = frappe.db.get_all(
			"GL Entry", {"voucher_no": pi.name}, ["account", "debit", "credit"]
		)

		for entries in account_entries_pi:
			if entries.account == "Parking Charges Account - TC-5":
				self.assertEqual(entries.debit, 50)
			if entries.account == "Input Tax SGST - TC-5":
				self.assertEqual(entries.debit, 90)
			if entries.account == "Input Tax CGST - TC-5":
				self.assertEqual(entries.debit, 90)
			if entries.account == "Stock Received But Not Billed - TC-5":
				self.assertEqual(entries.debit, 1000)
			if entries.account == "Creditors - TC-5":
				self.assertEqual(entries.credit, 1230)

	def test_po_with_on_item_quntity_account_type_TC_B_135(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company_and_supplier as create_data,
		)

		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item_1 = make_test_item("test_item")
		item_2 = make_test_item("test_item_1")
		warehouse = "Stores - TC-3"
		create_new_account(
			account_name="Transportation Charges Account",
			company=get_company_supplier.get("parent_company"),
			parent_account="Indirect Expenses - TC-1",
		)
		transportation_chrages_account = create_new_account(
			account_name="Transportation Charges Account",
			company=company,
			parent_account="Indirect Expenses - TC-3",
		)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [
					{"item_code": item_1.item_code, "schedule_date": today(), "qty": 10, "rate": 100},
					{"item_code": item_2.item_code, "schedule_date": today(), "qty": 5, "rate": 200},
				],
				"taxes": [
					{
						"charge_type": "On Item Quantity",
						"account_head": transportation_chrages_account,
						"description": transportation_chrages_account,
						"rate": 20,
					}
				],
			}
		)
		po.insert()
		po.submit()

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()
		self.assertEqual(po.grand_total, po.grand_total)
		self.assertEqual(po.taxes_and_charges_added, po.taxes_and_charges_added)

		frappe.db.set_value(
			"Company",
			company,
			{
				"enable_perpetual_inventory": 1,
				"enable_provisional_accounting_for_non_stock_items": 1,
				"stock_received_but_not_billed": "Stock Received But Not Billed - TC-3",
				"default_inventory_account": "Stock In Hand - TC-3",
				"default_provisional_account": "Stock In Hand - TC-3",
			},
		)

		account_entries_pr = frappe.db.get_all(
			"GL Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["account", "debit", "credit"],
		)

		for entries in account_entries_pr:
			if entries.account == "Stock Received But Not Billed - TC-3":
				self.assertEqual(entries.credit, 2000)
			if entries.account == "Stock In Hand - TC-3":
				self.assertEqual(entries.debit, 2000)

		stock_entries = frappe.db.get_all(
			"Stock Ledger Entry", {"voucher_no": pr.name}, ["item_code", "actual_qty"]
		)
		for entries in stock_entries:
			if entries.item_code == pr.items[0].item_code:
				self.assertEqual(entries.actual_qty, pr.items[0].qty)
			if entries.item_code == pr.items[1].item_code:
				self.assertEqual(entries.actual_qty, pr.items[1].qty)

		pi = make_pi_from_pr(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.save()
		pi.submit()

		account_entries_pi = frappe.db.get_all(
			"GL Entry", {"voucher_no": pi.name}, ["account", "debit", "credit"]
		)

		for entries in account_entries_pi:
			if entries.account == "Transportation Charges Account - TC-3":
				self.assertEqual(entries.debit, 300)
			if entries.account == "Input Tax SGST - TC-3":
				self.assertEqual(entries.debit, 180)
			if entries.account == "Input Tax CGST - TC-3":
				self.assertEqual(entries.debit, 180)
			if entries.account == "Stock Received But Not Billed - TC-3":
				self.assertEqual(entries.debit, 2000)
			if entries.account == "Creditors - TC-3":
				self.assertEqual(entries.credit, 2300)

	@if_app_installed("india_compliance")
	def test_po_with_all_account_type_TC_B_136(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		item_1 = make_test_item("test_item_1")
		item_2 = make_test_item("test_item_2")
		warehouse = "Stores - TC-5"
		tax_template = create_or_get_purchase_taxes_template(company=company)

		parking_charges_account = create_new_account(
			account_name="Parking Charges Account", company=company, parent_account="Indirect Expenses - TC-5"
		)

		transportation_chrages_account = create_new_account(
			account_name="Transportation Charges Account",
			company=company,
			parent_account="Cash In Hand - TC-5",
		)

		output_cess_account = create_new_account(
			account_name="Output Cess Account", company=company, parent_account="Cash In Hand - TC-5"
		)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"currency": "INR",
				"set_warehouse": warehouse,
				"items": [
					{"item_code": item_1.item_code, "schedule_date": today(), "qty": 10, "rate": 100},
					{"item_code": item_2.item_code, "schedule_date": today(), "qty": 5, "rate": 200},
				],
			}
		)
		po.taxes_and_charges = tax_template.get("purchase_tax_template")
		po.insert()
		taxes = [
			{
				"charge_type": "Actual",
				"account_head": "Freight and Forwarding Charges - TC-5",
				"description": "Freight and Forwarding Charges",
				"tax_amount": 100,
			},
			{
				"charge_type": "On Net Total",
				"account_head": parking_charges_account,
				"description": parking_charges_account,
				"rate": 5,
			},
			{
				"charge_type": "On Item Quantity",
				"account_head": transportation_chrages_account,
				"description": transportation_chrages_account,
				"rate": 20,
			},
			{
				"charge_type": "On Previous Row Amount",
				"account_head": output_cess_account,
				"description": output_cess_account,
				"rate": 5,
				"row_id": 5,
			},
		]
		for tax in taxes:
			po.append("taxes", tax)

		po.submit()
		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()
		self.assertEqual(po.grand_total, po.grand_total)

		frappe.db.set_value(
			"Company",
			company,
			{
				"enable_perpetual_inventory": 1,
				"enable_provisional_accounting_for_non_stock_items": 1,
				"stock_received_but_not_billed": "Stock Received But Not Billed - TC-5",
				"default_inventory_account": "Stock In Hand - TC-5",
				"default_provisional_account": "Stock In Hand - TC-5",
			},
		)

		account_entries_pr = frappe.db.get_all(
			"GL Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["account", "debit", "credit"],
		)

		for entries in account_entries_pr:
			if entries.account == "Stock Received But Not Billed - TC-5":
				self.assertEqual(entries.credit, 2000)
			if entries.account == "Stock In Hand - TC-5":
				self.assertEqual(entries.debit, 2000)

		stock_entries = frappe.db.get_all(
			"Stock Ledger Entry", {"voucher_no": pr.name}, ["item_code", "actual_qty"]
		)
		for entries in stock_entries:
			if entries.item_code == pr.items[0].item_code:
				self.assertEqual(entries.actual_qty, pr.items[0].qty)
			if entries.item_code == pr.items[1].item_code:
				self.assertEqual(entries.actual_qty, pr.items[1].qty)

		pi = make_pi_from_pr(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.save()
		pi.submit()

		account_entries_pi = frappe.db.get_all(
			"GL Entry", {"voucher_no": pi.name}, ["account", "debit", "credit"]
		)

		for entries in account_entries_pi:
			if entries.account == "Transportation Charges Account - TC-5":
				self.assertEqual(entries.debit, 300)
			if entries.account == "Output Cess Account - TC-5":
				self.assertEqual(entries.debit, 15)
			if entries.account == "Parking Charges Account - TC-5":
				self.assertEqual(entries.debit, 100)
			if entries.account == "Freight and Forwarding Charges - TC-5":
				self.assertEqual(entries.debit, 100)
			if entries.account == "Input Tax SGST - TC-5":
				self.assertEqual(entries.debit, 180)
			if entries.account == "Input Tax CGST - TC-5":
				self.assertEqual(entries.debit, 180)
			if entries.account == "Stock Received But Not Billed - TC-5":
				self.assertEqual(entries.debit, 2000)
			if entries.account == "Creditors - TC-5":
				self.assertEqual(entries.credit, 2875)


	def test_create_po_pr_partial_TC_SCK_046(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		create_item("_Test Item", warehouse="Stores - _TC")
		create_supplier(supplier_name="_Test Supplier")
		get_or_create_fiscal_year("_Test Company")

		po = create_purchase_order(rate=10000, qty=10, warehouse="Stores - _TC")
		po.submit()

		pr = create_pr_against_po(po.name, received_qty=5)

		bin_qty = frappe.db.get_value(
			"Bin", {"item_code": "_Test Item", "warehouse": "Stores - _TC"}, "actual_qty"
		)

		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_no": pr.name})
		self.assertEqual(sle.qty_after_transaction, bin_qty)
		self.assertEqual(sle.warehouse, po.get("items")[0].warehouse)

		if frappe.db.exists("GL Entry", {"account": "Stock Received But Not Billed - _TC"}):
			gl_temp_credit = frappe.db.get_value(
				"GL Entry",
				{"voucher_no": pr.name, "account": "Stock Received But Not Billed - _TC"},
				"credit",
			)
			print(f"PR GL - Stock Received But Not Billed (credit): {gl_temp_credit}")
			if gl_temp_credit:
				self.assertAlmostEqual(gl_temp_credit, 50000, places=2)

		if frappe.db.exists("GL Entry", {"account": "Stock In Hand - _TC"}):
			gl_stock_debit = frappe.db.get_value(
				"GL Entry",
				{"voucher_no": pr.name, "account": "Stock In Hand - _TC"},
				"debit",
			)
			print(f"PR GL - Stock In Hand (debit): {gl_stock_debit}")
			if gl_stock_debit:
				self.assertAlmostEqual(gl_stock_debit, 50000, places=2)

		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		return_pr = make_return_doc("Purchase Receipt", pr.name)
		return_pr.get("items")[0].received_qty = -5
		return_pr.submit()

		bin_qty = frappe.db.get_value(
			"Bin", {"item_code": "_Test Item", "warehouse": "Stores - _TC"}, "actual_qty"
		)
		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_no": return_pr.name})
		self.assertEqual(sle.qty_after_transaction, bin_qty)

		if frappe.db.exists("GL Entry", {"account": "Stock Received But Not Billed - _TC"}):
			gl_temp_debit = frappe.db.get_value(
				"GL Entry",
				{"voucher_no": return_pr.name, "account": "Stock Received But Not Billed - _TC"},
				"debit",
			)
			print(f"Return PR GL - Stock Received But Not Billed (debit): {gl_temp_debit}")
			if gl_temp_debit:
				self.assertAlmostEqual(gl_temp_debit, 50000, places=2)

		if frappe.db.exists("GL Entry", {"account": "Stock In Hand - _TC"}):
			gl_stock_credit = frappe.db.get_value(
				"GL Entry",
				{"voucher_no": return_pr.name, "account": "Stock In Hand - _TC"},
				"credit",
			)
			print(f"Return PR GL - Stock In Hand (credit): {gl_stock_credit}")
			if gl_stock_credit:
				self.assertAlmostEqual(gl_stock_credit, 50000, places=2)


	def test_create_po_pr_TC_SCK_177(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		create_item("_Test Item", warehouse="Stores - _TC")
		create_supplier(supplier_name="_Test Supplier")
		po = create_purchase_order(qty=10, warehouse="Stores - _TC")
		get_or_create_fiscal_year("_Test Company")
		po.submit()
		frappe.db.set_value("Item", "_Test Item", "over_delivery_receipt_allowance", 10)
		pr = make_purchase_receipt(po.name)
		pr.company = "_Test Company"
		pr.rejected_warehouse = "Finished Goods - _TC"
		pr.get("items")[0].qty = 8
		pr.get("items")[0].rejected_qty = 2
		pr.insert()
		initial_qty = frappe.db.get_value(
        "Bin", {"item_code": "_Test Item", "warehouse": "Stores - _TC"}, "actual_qty"
    )
		pr.submit()
		sle = frappe.get_doc("Stock Ledger Entry", {
        "voucher_no": pr.name,
        "warehouse": "Stores - _TC"
    })
		expected_qty = initial_qty + pr.get("items")[0].qty
		self.assertEqual(sle.qty_after_transaction, expected_qty)
		
	def test_create_po_pr_return_pr_TC_SCK_178(self):
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		create_company()
		get_or_create_fiscal_year("_Test Company PO")
		supplier = create_supplier(supplier_name="_Test Supplier PO")
		item = create_item("_Test PO")
		warehouse = create_warehouse("_Test warehouse - _PO", company="_Test Company PO")

		po = create_purchase_order(
			qty=10,
			company="_Test Company PO",
			supplier=supplier,
			item=item.item_code,
			warehouse=warehouse,
			do_not_save=1,
		)
		po.save()
		po.submit()

		frappe.db.set_value("Item", "_Test PO", "over_delivery_receipt_allowance", 10)
		pr = make_purchase_receipt(po.name)
		pr.company = "_Test Company PO"
		pr.set_warehouse = warehouse
		pr.rejected_warehouse = create_warehouse("_Test Warehouse8", company=pr.company)
		pr.get("items")[0].qty = 8
		pr.get("items")[0].rejected_qty = 2
		pr.insert()
		pr.submit()

		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_no": pr.name})
		self.assertEqual(sle.qty_after_transaction, 2)

		pr.load_from_db()
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		return_pi = make_return_doc("Purchase Receipt", pr.name, return_against_rejected_qty=True)
		return_pi.get("items")[0].qty = -2
		return_pi.submit()
		pr.reload()

		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_no": return_pi.name})
		self.assertEqual(sle.actual_qty, -2)

	def test_tds_in_po_and_pi_TC_B_150(self):
		get_data = get_company_or_supplier()
		company = get_data.get("company")
		supplier = get_data.get("supplier")
		item = make_test_item("_test_item_")
		get_or_create_fiscal_year(company)
		warehouse = "Stores - TC-5"
		tax_category = "test_tax_withholding_category"
		if not frappe.db.exists("Tax Withholding Category", tax_category):
			doc = frappe.get_doc(
				{
					"doctype": "Tax Withholding Category",
					"name": tax_category,
					"category_name": tax_category,
					"rates": [
						{
							"from_date": get_year_start(getdate()),
							"to_date": get_year_ending(getdate()),
							"tax_withholding_rate": 2,
							"single_threshold": 1000,
							"cumulative_threshold": 100000,
						}
					],
					"accounts": [
						{
							"company": company,
							"account": create_new_account(
								"TDS Payable", company, "Duties and Taxes - TC-5", "Tax"
							),
						}
					],
				}
			)
			doc.insert()
			tax_category = doc.name

		frappe.db.set_value("Supplier", supplier, "tax_withholding_category", tax_category)
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"apply_tds": 1,
				"schedule_date": today(),
				"currency": "INR",
				"set_warehouse": warehouse,
				"items": [{"item_code": item.item_code, "warehouse": warehouse, "qty": 2, "rate": 500}],
			}
		)
		po.taxes_and_charges = ""
		po.taxes = []
		po.tax_withholding_category = tax_category
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.taxes[0].tax_amount, 20)
		self.assertEqual(po.taxes_and_charges_deducted, 20)
		self.assertEqual(po.grand_total, 980)

		pi = make_pi_from_po(po.name)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		pi.submit()

		self.assertEqual(pi.taxes[0].tax_amount, 20)
		self.assertEqual(pi.taxes_and_charges_deducted, 20)
		self.assertEqual(pi.grand_total, 980)

		self.assertEqual(len(pi.items), len(po.items))
		self.assertEqual(pi.items[0].qty, 2)
		self.assertEqual(pi.items[0].rate, 500)

		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": pi.name, "company": company},
			fields=["account", "debit", "credit"],
		)
		self.assertTrue(gl_entries)

		total_debit = sum(entry["debit"] for entry in gl_entries)
		total_credit = sum(entry["credit"] for entry in gl_entries)
		self.assertEqual(total_debit, total_credit)

	def test_po_with_tds_TC_B_152(self):
		get_data = get_company_or_supplier()
		company = get_data.get("company")
		supplier = get_data.get("supplier")
		item = make_test_item("__test_item_1")
		target_warehouse = "Stores - TC-5"
		tax_category = frappe.get_doc(
			{
				"doctype": "Tax Withholding Category",
				"name": "test_tax_withholding_category",
				"category_name": "test_tax_withholding_category",
				"rates": [
					{
						"from_date": get_year_start(getdate()),
						"to_date": get_year_ending(getdate()),
						"tax_withholding_rate": 2,
						"single_threshold": 1000,
						"cumulative_threshold": 100000,
					}
				],
				"accounts": [
					{
						"company": company,
						"account": self.create_account(
							"TDS Payable", company, "INR", "Duties and Taxes - TC-5"
						),
					}
				],
			}
		).insert(ignore_if_duplicate=1)
		frappe.db.set_value("Supplier", supplier, "tax_withholding_category", tax_category.name)
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"apply_tds": 1,
				"schedule_date": today(),
				"set_warehouse": target_warehouse,
				"taxes_and_charges": "",
				"tax_withholding_category": tax_category,
				"items": [
					{"item_code": item.item_code, "warehouse": target_warehouse, "qty": 2, "rate": 500}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.taxes[0].tax_amount, 20)
		self.assertEqual(po.taxes_and_charges_deducted, 20)
		self.assertEqual(po.grand_total, 980)

	def test_putaway_rule_with_po_pr_pi_TC_B_155(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - TC-5"
		item = make_test_item("Test Item with Putaway Rule")

		if not frappe.db.exists("Putaway Rule", {"item_code": item.item_code, "warehouse": warehouse}):
			frappe.get_doc(
				{
					"company": company,
					"doctype": "Putaway Rule",
					"item_code": item.item_code,
					"warehouse": warehouse,
					"capacity": 20,
					"priority": 1,
				}
			).insert(ignore_if_duplicate=1)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 20,
						"warehouse": warehouse,
					}
				],
			}
		)
		po.taxes_and_charges = ""
		po.taxes = []
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)

		pr = make_purchase_receipt(po.name)
		pr.taxes_and_charges = ""
		pr.taxes = []
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		stock_ledger_entries = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": pr.name}, fields=["warehouse", "actual_qty"]
		)

		warehouse_qty = sum(
			entry.actual_qty for entry in stock_ledger_entries if entry.warehouse == warehouse
		)
		self.assertEqual(warehouse_qty, 20)
		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.taxes_and_charges = ""
		pi.taxes = []
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)

	def test_shipping_rule_with_payment_entry_TC_B_070(self):
		# Scenario : PO => PE => PR => PI [With Shipping Rule]
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item_121")
		warehouse = "Stores - TC-3"

		remove_existing_shipping_rules()

		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "Net Weight Shipping Rule",
				"calculate_based_on": "Fixed",
				"shipping_rule_type": "Buying",
				"account": "Cash - TC-3",
				"cost_center": "Main - TC-3",
				"conditions": [{"from_value": 10, "to_value": 1000, "shipping_amount": 200}],
			}
		)
		shipping_rule.insert(ignore_permissions=True)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 1,
						"rate": 130,
						"warehouse": warehouse,
					}
				],
				"shipping_rule": shipping_rule.name,
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)

		args = {"mode_of_payment": "Cash", "reference_no": "For Testing"}

		# pe = make_payment_entry(po.doctype, po.name, po.grand_total, args )
		pe = get_payment_entry(po.doctype, po.name)
		pe.insert(ignore_permissions=True)
		pe.submit()

		pr = make_pr_for_po(po.name)
		self.assertEqual(pr.docstatus, 1)

		args = {
			"mode_of_payment": "Cash",
			"cash_bank_account": pe.paid_from,
			"paid_amount": pe.base_received_amount,
			"is_paid": 1,
		}

		pi = make_pi_against_pr(pr.name, args=args)
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.items[0].qty, po.items[0].qty)
		self.assertEqual(pi.grand_total, po.grand_total)

		po.reload()
		self.assertEqual(po.status, "Completed")
		self.assertEqual(pi.status, "Paid")

	def test_po_shipping_rule_partial_payment_entry_TC_B_071(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("_test_item")
		warehouse = "Stores - TC-3"

		get_or_create_fiscal_year(company)
		remove_existing_shipping_rules()

		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "Fixed Shipping Rule",
				"calculate_based_on": "Fixed",
				"shipping_rule_type": "Buying",
				"account": "Cash - TC-3",
				"cost_center": "Main - TC-3",
				"shipping_amount": 200,
			}
		).insert(ignore_if_duplicate=1)

		po_data = {
			"company": company,
			"item_code": item.item_code,
			"warehouse": warehouse,
			"supplier": supplier,
			"qty": 3,
			"rate": 12000,
			"shipping_rule": shipping_rule.name,
		}

		doc_po = create_purchase_order(**po_data)
		self.assertEqual(doc_po.docstatus, 1)

		args = {"mode_of_payment": "Cash", "reference_no": "For Testing"}

		cash_account = frappe.db.get_value(
			"Mode of Payment Account", {"parent": "Cash", "company": company}, "default_account"
		)
		if not cash_account:
			mop = frappe.get_doc("Mode of Payment", "Cash")
			mop.append(
				"accounts",
				{
					"company": company,
					"default_account": "Cash - TC-3",
				},
			)
			mop.save()
		doc_pe = make_payment_entry(doc_po.doctype, doc_po.name, 6000, args)

		doc_pr = make_pr_for_po(doc_po.name)
		self.assertEqual(doc_pr.docstatus, 1)

		args = {
			"is_paid": 1,
			"mode_of_payment": "Cash",
			"cash_bank_account": doc_pe.paid_from,
			"paid_amount": doc_pe.base_received_amount,
		}

		doc_pi = make_pi_against_pr(doc_pr.name, args=args)
		make_payment_entry(doc_pi.doctype, doc_pi.name, doc_pi.outstanding_amount)

		self.assertEqual(doc_pi.docstatus, 1)
		self.assertEqual(doc_pi.items[0].qty, doc_po.items[0].qty)
		self.assertEqual(doc_pi.grand_total, doc_po.grand_total)

		doc_po.reload()
		doc_pi.reload()
		self.assertEqual(doc_po.status, "Completed")
		self.assertEqual(doc_pi.status, "Paid")
		self.assertEqual(doc_pi.outstanding_amount, 0)

	def test_po_to_pi_with_Adv_payment_entry_TC_B_072(self):
		# Scenario : PO => PE => PR => PI [With Adv Payment]
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("_test_item")
		warehouse = "Stores - TC-3"

		po_data = {
			"company": company,
			"item_code": item.item_code,
			"warehouse": warehouse,
			"qty": 1,
			"rate": 3000,
			"supplier": supplier,
		}

		doc_po = create_purchase_order(**po_data)
		self.assertEqual(doc_po.docstatus, 1)

		args = {"mode_of_payment": "Cash", "reference_no": "For Testing"}

		doc_pe = make_payment_entry(doc_po.doctype, doc_po.name, doc_po.grand_total, args)

		doc_pr = make_pr_for_po(doc_po.name)
		self.assertEqual(doc_pr.docstatus, 1)

		args = {
			"is_paid": 1,
			"mode_of_payment": "Cash",
			"cash_bank_account": doc_pe.paid_from,
			"paid_amount": doc_pe.base_received_amount,
		}

		doc_pi = make_pi_against_pr(doc_pr.name, args=args)

		self.assertEqual(doc_pi.docstatus, 1)
		self.assertEqual(doc_pi.items[0].qty, doc_po.items[0].qty)
		self.assertEqual(doc_pi.grand_total, doc_po.grand_total)

		doc_po.reload()
		self.assertEqual(doc_po.status, "Completed")
		self.assertEqual(doc_pi.status, "Paid")

	def test_po_to_pi_with_partial_payment_entry_TC_B_073(self):
		# Scenario : PO => PE => PR => PI [With Adv Partial Payment]
		get_data = get_company_or_supplier()
		company = get_data.get("company")
		supplier = get_data.get("supplier")
		item = make_test_item("_test_item_")
		get_or_create_fiscal_year(company)
		po_data = {
			"company": company,
			"item_code": item.item_code,
			"warehouse": "Stores - TC-5",
			"qty": 4,
			"rate": 3000,
			"supplier": supplier,
		}

		doc_po = create_purchase_order(**po_data)
		self.assertEqual(doc_po.docstatus, 1)

		args = {"mode_of_payment": "Cash", "reference_no": "For Testing"}

		cash_account = frappe.db.get_value(
			"Mode of Payment Account", {"parent": "Cash", "company": company}, "default_account"
		)
		if not cash_account:
			mop = frappe.get_doc("Mode of Payment", "Cash")
			mop.append(
				"accounts",
				{
					"company": company,
					"default_account": "Cash - TC-5",
				},
			)
			mop.save()
		doc_pe = make_payment_entry(doc_po.doctype, doc_po.name, 6000, args)

		doc_pr = make_pr_for_po(doc_po.name)
		self.assertEqual(doc_pr.docstatus, 1)

		args = {
			"is_paid": 1,
			"mode_of_payment": "Cash",
			"cash_bank_account": doc_pe.paid_from,
			"paid_amount": doc_pe.base_received_amount,
		}

		doc_pi = make_pi_against_pr(doc_pr.name, args=args)
		make_payment_entry(doc_pi.doctype, doc_pi.name, doc_pi.outstanding_amount)

		self.assertEqual(doc_pi.docstatus, 1)
		self.assertEqual(doc_pi.items[0].qty, doc_po.items[0].qty)
		self.assertEqual(doc_pi.grand_total, doc_po.grand_total)

		doc_po.reload()
		doc_pi.reload()
		self.assertEqual(doc_po.status, "Completed")
		self.assertEqual(doc_pi.status, "Paid")

	@if_app_installed("india_compliance")
	def test_po_to_pi_with_Adv_payment_entry_n_tax_TC_B_074(self):
		# Scenario : PO => PE => PR => PI [With Adv Payment and Tax]
		get_data = get_company_or_supplier()
		company = get_data.get("company")
		supplier = get_data.get("supplier")
		item = make_test_item("_test_item_")

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - TC-5"
		acc.company = company
		account_name = frappe.db.exists("Account", {"account_name": acc.account_name, "company": company})
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		po_data = {
			"company": company,
			"item_code": item.item_code,
			"warehouse": "Stores - TC-5",
			"qty": 1,
			"rate": 3000,
			"do_not_submit": 1,
			"supplier": supplier,
		}
		doc_po = create_purchase_order(**po_data)
		doc_po.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 18,
				"description": "Input GST",
			},
		)
		doc_po.submit()
		self.assertEqual(doc_po.docstatus, 1)

		args = {"mode_of_payment": "Cash", "reference_no": "For Testing"}

		doc_pe = make_payment_entry(doc_po.doctype, doc_po.name, doc_po.grand_total, args)

		doc_pr = make_pr_for_po(doc_po.name)
		self.assertEqual(doc_pr.docstatus, 1)

		args = {
			"is_paid": 1,
			"mode_of_payment": "Cash",
			"cash_bank_account": doc_pe.paid_from,
			"paid_amount": doc_pe.base_received_amount,
		}

		doc_pi = make_pi_against_pr(doc_pr.name, args=args)

		self.assertEqual(doc_pi.docstatus, 1)
		self.assertEqual(doc_pi.items[0].qty, doc_po.items[0].qty)
		self.assertEqual(doc_pi.grand_total, doc_po.grand_total)

		doc_po.reload()
		self.assertEqual(doc_po.status, "Completed")
		self.assertEqual(doc_pi.status, "Paid")

	@if_app_installed("india_compliance")
	def test_po_to_pi_with_partial_payment_entry_TC_B_075(self):
		# Scenario : PO => PE => PR => PI [With Adv Partial Payment and Tax]
		get_data = get_company_or_supplier()
		company = get_data.get("company")
		supplier = get_data.get("supplier")
		item = make_test_item("_test_items_1")
		get_or_create_fiscal_year(company)
		po_data = {
			"company": company,
			"item_code": item.item_code,
			"warehouse": "Stores - TC-5",
			"qty": 4,
			"rate": 3000,
			"do_not_submit": 1,
			"supplier": supplier,
		}

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - TC-5"
		acc.company = company
		account_name = frappe.db.exists("Account", {"account_name": acc.account_name, "company": company})
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		doc_po = create_purchase_order(**po_data)
		doc_po.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 18,
				"description": "Input GST",
			},
		)
		doc_po.submit()

		self.assertEqual(doc_po.docstatus, 1)
		self.assertEqual(doc_po.base_taxes_and_charges_added, 2160)

		args = {"mode_of_payment": "Cash", "reference_no": "For Testing"}
		cash_account = frappe.db.get_value(
			"Mode of Payment Account", {"parent": "Cash", "company": company}, "default_account"
		)
		if not cash_account:
			mop = frappe.get_doc("Mode of Payment", "Cash")
			mop.append(
				"accounts",
				{
					"company": company,
					"default_account": "Cash - TC-5",
				},
			)
			mop.save()

		doc_pe = make_payment_entry(doc_po.doctype, doc_po.name, 6000, args)

		doc_pr = make_pr_for_po(doc_po.name)
		self.assertEqual(doc_pr.docstatus, 1)

		args = {
			"is_paid": 1,
			"mode_of_payment": "Cash",
			"cash_bank_account": doc_pe.paid_from,
			"paid_amount": doc_pe.base_received_amount,
		}

		doc_pi = make_pi_against_pr(doc_pr.name, args=args)
		make_payment_entry(doc_pi.doctype, doc_pi.name, doc_pi.outstanding_amount)

		self.assertEqual(doc_pi.docstatus, 1)
		self.assertEqual(doc_pi.items[0].qty, doc_po.items[0].qty)
		self.assertEqual(doc_pi.grand_total, doc_po.grand_total)

		doc_po.reload()
		doc_pi.reload()
		self.assertEqual(doc_po.status, "Completed")
		self.assertEqual(doc_pi.status, "Paid")

	@if_app_installed("india_compliance")
	def test_default_uom_with_po_pr_pi_TC_B_105(self):
		# item as box => po => pr => pi with GST
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		company = "_Test Company"
		supplier = "_Test Supplier"
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item_code = "_Test Item"
		create_item(item_code=item_code, valuation_rate=100)
		gst_hsn_code = "11112222"
		warehouse = "Stores - _TC"
		tax_category_1 = "Test Tax Category"
		if not frappe.db.exists("Tax Category", tax_category_1):
			tax_category = frappe.new_doc("Tax Category")
			tax_category.title = tax_category_1
			tax_category.save()

		frappe.db.set_value(
			"Company",
			company,
			{
				"enable_perpetual_inventory": 1,
				"stock_received_but_not_billed": "Stock Received But Not Billed - _TC",
			},
		)
		item_tax_template = frappe.db.get_value(
			"Purchase Taxes and Charges Template",
			{"company": company, "tax_category": tax_category_1},
			"name",
		)
		if frappe.db.exists("DocType", "GST HSN Code") and not frappe.db.exists("GST HSN Code", gst_hsn_code):
			frappe.get_doc(
				{
					"doctype": "GST HSN Code",
					"hsn_code": gst_hsn_code,
					"taxes": [{"item_tax_template": "GST 18% - _TC"}],
				}
			).insert()
		taxes = [
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": "Stock In Hand - _TC",
				"description": "SGST",
			},
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": "Stock In Hand - _TC",
				"description": "CGST",
			},
		]
		if frappe.db.exists("Purchase Taxes and Charges Template", item_tax_template):
			existing_templates = item_tax_template
		else:
			purchase_tax_template = frappe.new_doc("Purchase Taxes and Charges Template")
			purchase_tax_template.company = company
			purchase_tax_template.title = "test"
			purchase_tax_template.tax_category = tax_category
			for tax in taxes:
				purchase_tax_template.append("taxes", tax)
			purchase_tax_template.insert()
			purchase_tax_template.save()
			existing_templates = purchase_tax_template.name

		get_or_create_fiscal_year("_Test Company")
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [{"item_code": item_code, "qty": 1, "rate": 100, "uom": "Box"}],
			}
		)

		po.insert()
		po.taxes_and_charges = existing_templates
		po.save()
		po.submit()
		self.assertEqual(po.items[0].uom, "Box")
		self.assertEqual(po.taxes_and_charges_added, 18)
		self.assertEqual(po.grand_total, 118)

		pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": po.supplier,
				"company": po.company,
				"currency": po.currency,
				"set_warehouse": po.set_warehouse,
				"items": [
					{
						"item_code": po.items[0].item_code,
						"uom": po.items[0].uom,
						"qty": po.items[0].qty,
						"stock_uom": po.items[0].stock_uom,
						"conversion_factor": po.items[0].conversion_factor,
						"rate": po.items[0].rate,
						"purchase_order": po.name,
					}
				],
			}
		)
		pr.insert()
		pr.taxes_and_charges = existing_templates
		pr.submit()
		self.assertEqual(pr.items[0].uom, "Box")
		self.assertEqual(pr.taxes_and_charges_added, 18)
		self.assertEqual(pr.grand_total, 118)

		get_pr_stock_ledger = frappe.db.get_all(
			"Stock Ledger Entry", {"voucher_no": pr.name}, ["valuation_rate", "actual_qty", "warehouse"]
		)

		for stock_led in get_pr_stock_ledger:
			self.assertEqual(stock_led.get("valuation_rate"), 100)
			self.assertEqual(stock_led.actual_qty, 1)
			self.assertEqual(stock_led.warehouse, warehouse)

		get_pr_gl_entries = frappe.db.get_all("GL Entry", {"voucher_no": pr.name})
		self.assertTrue(get_pr_gl_entries)

		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"supplier": pr.supplier,
				"company": pr.company,
				"credit_to": "Creditors - _TC",
				"currency": pr.currency,
				"items": [
					{
						"item_code": pr.items[0].item_code,
						"qty": pr.items[0].qty,
						"uom": pr.items[0].uom,
						"conversion_factor": pr.items[0].conversion_factor,
						"rate": pr.items[0].rate,
						"apply_tds": pr.items[0].apply_tds,
						"purchase_order": po.name,
						"purchase_receipt": pr.name,
					}
				],
			}
		)
		pi.insert(ignore_permissions=True)
		pi.taxes_and_charges = existing_templates
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.items[0].uom, "Box")
		self.assertEqual(pi.taxes_and_charges_added, 18)
		self.assertEqual(pi.grand_total, 118)

		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Purchase Invoice", "voucher_no": pi.name, "is_cancelled": 0},
			fields=["account", "debit", "credit"],
		)

		expected_entries = [
			{"account": "Stock In Hand - _TC", "debit": 18.0, "credit": 0.0},
			{"account": "Stock Received But Not Billed - _TC", "debit": 100.0, "credit": 0.0},
			{"account": "Creditors - _TC", "debit": 0.0, "credit": 118.0},
		]

		for entry in expected_entries:
			matching_entry = next((gl for gl in gl_entries if gl["account"] == entry["account"]), None)
			assert matching_entry
			assert matching_entry["debit"] == entry["debit"]
			assert matching_entry["credit"] == entry["credit"]

	def test_shipping_rule_fixed_pr_pi_pe_TC_B_106(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-3"
		item = make_test_item("test_item_with_fixed_shipping_rule")

		# Create Shipping Rule with Fixed Amount
		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "Fixed Shipping Rule",
				"calculate_based_on": "Fixed",
				"shipping_rule_type": "Buying",
				"account": "Cash - TC-3",
				"cost_center": "Main - TC-3",
				"shipping_amount": 500,
			}
		).insert(ignore_if_duplicate=1)

		# Create Purchase Order
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"rate": 100,
						"warehouse": target_warehouse,
					}
				],
			}
		)
		po.taxes_and_charges = ""
		po.taxes = []
		po.shipping_rule = shipping_rule.name
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 500)
		self.assertEqual(po.grand_total, 1500)

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		get_pr_stock_ledger = frappe.db.get_all(
			"Stock Ledger Entry", {"voucher_no": pr.name}, ["valuation_rate", "actual_qty"]
		)
		self.assertTrue(get_pr_stock_ledger)

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.taxes_and_charges_added, 500)
		self.assertEqual(pi.grand_total, 1500)

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.insert(ignore_permissions=True)
		pe.submit()
		self.assertEqual(pe.docstatus, 1)
		gl_entries_pr = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(gl_entries_pr)

		sle_pr = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(sle_pr)
		gl_entries_pi = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Invoice", "voucher_no": pi.name}
		)
		self.assertTrue(gl_entries_pi)
		pi_outstanding = frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount")
		self.assertEqual(pi_outstanding, 0)
		gl_entries_pe = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Payment Entry", "voucher_no": pe.name}
		)
		self.assertTrue(gl_entries_pe)

	def test_shipping_rule_net_total_pr_pi_pe_TC_B_107(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - TC-3"
		item = make_test_item("test_item_with_shipping_rule")

		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "Net Total Shipping Rule",
				"calculate_based_on": "Net Total",
				"shipping_rule_type": "Buying",
				"account": "Cash - TC-3",
				"cost_center": "Main - TC-3",
				"conditions": [{"from_value": 500, "to_value": 2000, "shipping_amount": 500}],
			}
		).insert(ignore_if_duplicate=1)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"rate": 100,
						"warehouse": warehouse,
					}
				],
				# "shipping_rule": shipping_rule.name
			}
		)
		po.taxes_and_charges = ""
		po.taxes = []
		po.shipping_rule = shipping_rule.name
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 500)
		self.assertEqual(po.grand_total, 1500)

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		gl_entries_pr = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(gl_entries_pr)

		sle_pr = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(sle_pr)

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.taxes_and_charges_added, 500)
		self.assertEqual(pi.grand_total, 1500)

		gl_entries_pi = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Invoice", "voucher_no": pi.name}
		)
		self.assertTrue(gl_entries_pi)

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.insert(ignore_permissions=True)
		pe.submit()
		self.assertEqual(pe.docstatus, 1)

		gl_entries_pe = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Payment Entry", "voucher_no": pe.name}
		)
		self.assertTrue(gl_entries_pe)

		pi_outstanding = frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount")
		self.assertEqual(pi_outstanding, 0)

	def test_shipping_rule_net_weight_pr_pi_pe_TC_B_108(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - TC-3"
		item = make_test_item("test_item_with_net_weight_shipping_rule")
		item.weight_per_unit = 2.5
		item.weight_uom = "Kg"
		item.save()

		# Create Shipping Rule with calculation based on Net Weight
		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "Net Weight Shipping Rule",
				"calculate_based_on": "Net Weight",
				"shipping_rule_type": "Buying",
				"account": "Cash - TC-3",
				"cost_center": "Main - TC-3",
				"conditions": [
					{
						"from_value": 10,  # Net weight range
						"to_value": 50,
						"shipping_amount": 250,
					}
				],
			}
		).insert(ignore_if_duplicate=1)

		# Create Purchase Order
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,  # Total weight = 10 * 2.5 = 25 Kg
						"rate": 100,
						"warehouse": warehouse,
					}
				],
			}
		)
		po.taxes_and_charges = ""
		po.taxes = []
		po.shipping_rule = shipping_rule.name
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 250)  # Shipping amount based on net weight
		self.assertEqual(po.grand_total, 1250)

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.taxes_and_charges_added, 250)
		self.assertEqual(pi.grand_total, 1250)

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.insert(ignore_permissions=True)
		pe.submit()
		self.assertEqual(pe.docstatus, 1)

		gl_entries_pe = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Payment Entry", "voucher_no": pe.name},
			fields=["account", "debit", "credit", "posting_date"],
		)
		self.assertTrue(gl_entries_pe)
		self.assertEqual(gl_entries_pe[0].get("account"), "Cash - TC-3")
		self.assertEqual(gl_entries_pe[0].get("credit"), 1250)
		self.assertEqual(gl_entries_pe[1].get("account"), "Creditors - TC-3")
		self.assertEqual(gl_entries_pe[1].get("debit"), 1250)

	@if_app_installed("india_compliance")
	def test_shipping_rule_fixed_pr_pi_pe_with_gst_TC_B_109(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-5"
		item = make_test_item("test_item_with_fixed_shipping_rule")

		remove_existing_shipping_rules()

		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "Fixed Shipping Rule",
				"calculate_based_on": "Fixed",
				"shipping_rule_type": "Buying",
				"account": "Cash - TC-5",
				"cost_center": "Main - TC-5",
				"shipping_amount": 500,
			}
		)
		shipping_rule.insert(ignore_permissions=True)
		tax_template = create_or_get_purchase_taxes_template(company=company)
		# Create Purchase Order
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"rate": 100,
						"warehouse": target_warehouse,
					}
				],
				"shipping_rule": shipping_rule.name,
			}
		)
		po.taxes_and_charges = tax_template.get("purchase_tax_template")
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 680)
		self.assertEqual(po.grand_total, 1680)

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)

		get_pr_stock_ledger = frappe.db.get_all(
			"Stock Ledger Entry", {"voucher_no": pr.name}, ["valuation_rate", "actual_qty"]
		)
		self.assertTrue(get_pr_stock_ledger)

		# Create Purchase Invoice from Purchase Receipt
		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.taxes_and_charges_added, 680)
		self.assertEqual(pi.grand_total, 1680)

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.insert(ignore_permissions=True)
		pe.submit()
		self.assertEqual(pe.docstatus, 1)
		gl_entries_pr = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(gl_entries_pr)

		sle_pr = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(sle_pr)
		gl_entries_pi = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Invoice", "voucher_no": pi.name}
		)
		self.assertTrue(gl_entries_pi)
		pi_outstanding = frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount")
		self.assertEqual(pi_outstanding, 0)
		gl_entries_pe = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Payment Entry", "voucher_no": pe.name}
		)
		self.assertTrue(gl_entries_pe)

	@if_app_installed("india_compliance")
	def test_shipping_rule_net_total_pr_pi_pe_with_gst_TC_B_110(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - TC-5"
		item = make_test_item("test_item_with_shipping_rule")

		remove_existing_shipping_rules()

		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "Net Total Shipping Rule",
				"calculate_based_on": "Net Total",
				"shipping_rule_type": "Buying",
				"account": "Cash - TC-5",
				"cost_center": "Main - TC-5",
				"conditions": [{"from_value": 500, "to_value": 2000, "shipping_amount": 500}],
			}
		)

		shipping_rule.insert(ignore_permissions=True)
		tax_template = create_or_get_purchase_taxes_template(company=company)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"rate": 100,
						"warehouse": warehouse,
					}
				],
			}
		)
		po.taxes_and_charges = tax_template.get("purchase_tax_template")
		po.shipping_rule = shipping_rule.name
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 680)
		self.assertEqual(po.grand_total, 1680)

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		gl_entries_pr = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(gl_entries_pr)

		sle_pr = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(sle_pr)

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.taxes_and_charges_added, 680)
		self.assertEqual(pi.grand_total, 1680)

		gl_entries_pi = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Invoice", "voucher_no": pi.name}
		)
		self.assertTrue(gl_entries_pi)

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.insert(ignore_permissions=True)
		pe.submit()
		self.assertEqual(pe.docstatus, 1)

		gl_entries_pe = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Payment Entry", "voucher_no": pe.name}
		)
		self.assertTrue(gl_entries_pe)

		pi_outstanding = frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount")
		self.assertEqual(pi_outstanding, 0)

	@if_app_installed("india_compliance")
	def test_shipping_rule_net_weight_pr_pi_pe_with_gst_TC_B_111(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		tax_template = create_or_get_purchase_taxes_template(company)
		item = make_test_item("test_item")
		warehouse = "Stores - TC-5"
		item = make_test_item("test_item_with_net_weight_shipping_rule")
		item.weight_uom = ("Kg",)
		item.weight_per_unit = 2.5
		item.save()

		# Create Shipping Rule with calculation based on Net Weight
		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "Net Weight Shipping Rule",
				"calculate_based_on": "Net Weight",
				"shipping_rule_type": "Buying",
				"account": "Cash - TC-5",
				"cost_center": "Main - TC-5",
				"conditions": [
					{
						"from_value": 10,  # Net weight range
						"to_value": 50,
						"shipping_amount": 250,
					}
				],
			}
		).insert(ignore_if_duplicate=1)

		# Create Purchase Order
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"set_warehouse": warehouse,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,  # Total weight = 10 * 2.5 = 25 Kg
						"rate": 100,
						"warehouse": warehouse,
					}
				],
				"shipping_rule": shipping_rule.name,
			}
		)
		taxes = [
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_template.get("sgst_account"),
				"description": "SGST",
			},
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_template.get("cgst_account"),
				"description": "CGST",
			},
		]
		for tax in taxes:
			po.append("taxes", tax)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 430)
		self.assertEqual(po.grand_total, 1430)

		# Create Purchase Receipt from Purchase Order
		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)

		# Create Purchase Invoice from Purchase Receipt
		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.taxes_and_charges_added, 430)
		self.assertEqual(pi.grand_total, 1430)

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.insert(ignore_permissions=True)
		pe.submit()
		self.assertEqual(pe.docstatus, 1)

		gl_entries_pe = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Payment Entry", "voucher_no": pe.name},
			fields=["account", "debit", "credit", "posting_date"],
		)
		self.assertTrue(gl_entries_pe)
		self.assertEqual(gl_entries_pe[0].get("account"), "Cash - TC-5")
		self.assertEqual(gl_entries_pe[0].get("credit"), 1430)
		self.assertEqual(gl_entries_pe[1].get("account"), "Creditors - TC-5")
		self.assertEqual(gl_entries_pe[1].get("debit"), 1430)

	@if_app_installed("india_compliance")
	def test_shipping_rule_fixed_restricted_country_po_with_gst_TC_B_115(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		warehouse = "Stores - TC-3"
		item = make_test_item("test_item_with_fixed_shipping_rule")

		# Create Shipping Rule with Fixed Amount
		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "test_shipping_rule_restricted_country",
				"calculate_based_on": "Fixed",
				"shipping_rule_type": "Buying",
				"account": "Creditors - TC-3",
				"cost_center": "Main - TC-3",
				"shipping_amount": 500,
				"countries": [{"country": "Australia"}],
			}
		).insert(ignore_if_duplicate=1)

		# Create Purchase Order
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"rate": 100,
						"warehouse": warehouse,
					}
				],
				"shipping_rule": shipping_rule.name,
			}
		)
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			po.insert()
		self.assertEqual(
			str(cm.exception), "Shipping rule not applicable for country India in Shipping Address"
		)

	@if_app_installed("india_compliance")
	def test_shipping_rule_net_total_restricted_country_po_with_gst_TC_B_116(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		# item = make_test_item("test_item")
		warehouse = "Stores - TC-3"
		item_code = make_test_item("test_item_with_shipping_rule")

		remove_existing_shipping_rules()

		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "test_shipping_rule_restricted_country",
				"calculate_based_on": "Net Total",
				"shipping_rule_type": "Buying",
				"account": "Creditors - TC-3",
				"cost_center": "Main - TC-3",
				"conditions": [{"from_value": 500, "to_value": 2000, "shipping_amount": 500}],
				"countries": [{"country": "Australia"}],
			}
		)
		shipping_rule.insert(ignore_permissions=True)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"items": [
					{
						"item_code": item_code,
						"qty": 10,
						"rate": 100,
						"warehouse": warehouse,
					}
				],
				"shipping_rule": shipping_rule.name,
			}
		)
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			po.insert()
		self.assertEqual(
			str(cm.exception), "Shipping rule not applicable for country India in Shipping Address"
		)

	def test_shipping_rule_net_weight_restricted_country_po_with_gst_TC_B_117(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - TC-3"

		item = make_test_item("test_item_with_net_weight_shipping_rule")
		item.weight_per_unit = 2.5
		item.weight_uom = "Kg"
		item.save()

		remove_existing_shipping_rules()

		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "test_shipping_rule_restricted_country",
				"calculate_based_on": "Net Weight",
				"shipping_rule_type": "Buying",
				"account": "Creditors - TC-3",
				"cost_center": "Main - TC-3",
				"conditions": [{"from_value": 10, "to_value": 50, "shipping_amount": 250}],
				"countries": [{"country": "Australia"}],
			}
		)

		shipping_rule.insert(ignore_permissions=True)

		# Create Purchase Order
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,  # Total weight = 10 * 2.5 = 25 Kg
						"rate": 100,
						"warehouse": warehouse,
					}
				],
				"shipping_rule": shipping_rule.name,
			}
		)
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			po.insert()
		self.assertEqual(
			str(cm.exception), "Shipping rule not applicable for country India in Shipping Address"
		)

	def test_closed_po_further_pi_pr_not_created_TC_B_131(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status

		create_company()
		create_supplier(supplier_name="_Test Supplier")
		create_warehouse("_Test Warehouse - _TC")
		create_item("_Test Item")

		po = create_purchase_order(qty=10, Rate=1000, do_not_save=True)
		po.save()
		tax_template = frappe.db.get_value(
			"Purchase Taxes and Charges Template", {"company": po.company, "tax_category": "In-State"}, "name"
		)
		po.taxes_and_charges = tax_template
		po.save()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		update_status(status="Closed", name=po.name)
		po.reload()
		self.assertEqual(po.status, "Closed")

		if not frappe.db.exists("Purchase Order", {"name": po.name, "status": "Closed"}):
			pi = make_pi_from_po(po.name)
			pi.save()
			pi.submit()
			self.assertEqual(pi.docstatus, 1)
			pr = make_purchase_receipt(po.name)
			pr.save()
			pr.submit()
			self.assertEqual(pr.docstatus, 1)

	def test_closed_pr_further_pi_not_created_TC_B_132(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import update_purchase_receipt_status

		create_company()
		create_supplier(supplier_name="_Test Supplier")
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_item("_Test Item")
		get_or_create_fiscal_year("_Test Company")
		po = create_purchase_order(qty=10, Rate=1000, do_not_save=True)
		po.save()
		tax_template = frappe.db.get_value(
			"Purchase Taxes and Charges Template", {"company": po.company, "tax_category": "In-State"}, "name"
		)
		po.taxes_and_charges = tax_template
		po.save()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		update_purchase_receipt_status(docname=pr.name, status="Closed")
		pr.reload()
		self.assertEqual(pr.status, "Closed")
		if not frappe.db.exists("Purchase Receipt", {"name": pr.name, "status": "Closed"}):
			pi = make_pi_from_pr(pr.name)
			pi.save()
			pi.submit()

	def test_margin_percentage_discount_on_price_list_rate_po_pr_pi_TC_B_119(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-3"
		item = make_test_item("testing_item_1122")

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"rate": 100,
						"price_list_rate": 100,
						"margin_type": "Percentage",
						"margin_rate_or_amount": 25,
						"discount_amount": 10,
						"warehouse": target_warehouse,
					}
				],
			}
		)
		po.taxes_and_charges = ""
		po.taxes = []
		po.insert()
		po.submit()

		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].rate, 115)
		self.assertEqual(po.total, 1150)
		self.assertEqual(po.grand_total, 1150)

		pr = make_purchase_receipt(po.name)
		pr.taxes_and_charges = ""
		pr.taxes = []
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.items[0].rate, 115)
		self.assertEqual(flt(pr.items[0].amount), 1150)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_pr_entries = {"Stock In Hand - TC-3": 1150, "Stock Received But Not Billed - TC-3": 1150}
		for entry in gl_entries:
			if entry["account"] in expected_pr_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pr_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pr_entries[entry["account"]])

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill - 1122"
		pi.taxes_and_charges = ""
		pi.taxes = []
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.items[0].rate, 115)
		self.assertEqual(flt(pi.items[0].amount), 1150)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {"Stock Received But Not Billed - TC-3": 1150, "Creditors - TC-3": 1150}
		for entry in gl_entries:
			if entry["account"] in expected_pi_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pi_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pi_entries[entry["account"]])

	def test_margin_as_amount_discount_percentage_on_price_list_rate_po_pr_pi_TC_B_120(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-5"
		item = make_test_item("Testing-31")

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"rate": 100,
						"price_list_rate": 100,
						"margin_type": "Amount",
						"margin_rate_or_amount": 50,
						"discount_percentage": 10,
						"warehouse": target_warehouse,
					}
				],
			}
		)
		po.taxes_and_charges = ""
		po.taxes = []
		po.insert()
		po.submit()

		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].rate, 135)
		self.assertEqual(po.total, 1350)
		self.assertEqual(po.grand_total, 1350)

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.taxes_and_charges = ""
		pr.taxes = []
		pr.save()
		pr.submit()

		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.items[0].rate, 135)
		self.assertEqual(flt(pr.items[0].amount), 1350)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_pr_entries = {"Stock In Hand - TC-5": 1350, "Stock Received But Not Billed - TC-5": 1350}
		for entry in gl_entries:
			if entry["account"] in expected_pr_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pr_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pr_entries[entry["account"]])

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.taxes_and_charges = ""
		pi.taxes = []
		pi.insert(ignore_permissions=True)
		pi.submit()

		# Validate PI submission
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.items[0].rate, 135)
		self.assertEqual(flt(pi.items[0].amount), 1350)

		# Validate accounting entries for PI
		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {"Stock Received But Not Billed - TC-5": 1350, "Creditors - TC-5": 1350}
		for entry in gl_entries:
			if entry["account"] in expected_pi_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pi_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pi_entries[entry["account"]])

	def test_margin_as_percentage_discount_as_percentage_on_price_list_rate_po_pr_pi_TC_B_121(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item_3344")
		target_warehouse = "Stores - TC-3"

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"rate": 100,
						"price_list_rate": 100,
						"margin_type": "Percentage",
						"margin_rate_or_amount": 30,
						"discount_percentage": 10,
						"warehouse": target_warehouse,
					}
				],
			}
		)
		po.taxes_and_charges = ""
		po.taxes = []
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].rate, 117)
		self.assertEqual(po.total, 1170)
		self.assertEqual(po.grand_total, 1170)

		pr = make_purchase_receipt(po.name)
		pr.taxes_and_charges = ""
		pr.taxes = []
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.items[0].rate, 117)
		self.assertEqual(flt(pr.items[0].amount), 1170)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_pr_entries = {"Stock In Hand - TC-3": 1170, "Stock Received But Not Billed - TC-3": 1170}
		for entry in gl_entries:
			if entry["account"] in expected_pr_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pr_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pr_entries[entry["account"]])

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.taxes_and_charges = ""
		pi.taxes = []
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.items[0].rate, 117)
		self.assertEqual(flt(pi.items[0].amount), 1170)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {"Stock Received But Not Billed - TC-3": 1170, "Creditors - TC-3": 1170}
		for entry in gl_entries:
			if entry["account"] in expected_pi_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pi_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pi_entries[entry["account"]])

	def test_apply_only_margin_on_price_list_rate_po_pr_pi_TC_B_124(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-3"
		item = make_test_item("test_item_1122")

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"rate": 100,
						"price_list_rate": 100,
						"margin_type": "Percentage",
						"margin_rate_or_amount": 80,
						"warehouse": target_warehouse,
					}
				],
			}
		)
		po.taxes_and_charges = ""
		po.taxes = []
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].rate, 180)
		self.assertEqual(po.total, 1800)
		self.assertEqual(po.grand_total, 1800)

		pr = make_purchase_receipt(po.name)
		pr.taxes_and_charges = ""
		pr.taxes = []
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.items[0].rate, 180)
		self.assertEqual(flt(pr.items[0].amount), 1800)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_pr_entries = {"Stock In Hand - TC-3": 1800, "Stock Received But Not Billed - TC-3": 1800}
		for entry in gl_entries:
			if entry["account"] in expected_pr_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pr_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pr_entries[entry["account"]])

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.taxes_and_charges = ""
		pi.taxes = []
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.items[0].rate, 180)
		self.assertEqual(flt(pi.items[0].amount), 1800)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {"Stock Received But Not Billed - TC-3": 1800, "Creditors - TC-3": 1800}
		for entry in gl_entries:
			if entry["account"] in expected_pi_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pi_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pi_entries[entry["account"]])

	@change_settings(
		"Global Defaults",
		{
			"default_company": "_Test company with other country address",
			"country": "India",
			"default_currency": "INR",
		},
	)
	def test_shipping_rule_fixed_rate_restricted_country_po_pr_pi_pe_TC_B_112(self):
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		get_company_supplier = create_company_and_suppliers()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - -TCNI_"
		item = make_test_item("test_item_with_fixed_shipping_rule")

		# Create Shipping Rule with Fixed Amount
		frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "_Test shipping rule wtih country address",
				"calculate_based_on": "Fixed",
				"shipping_rule_type": "Buying",
				"account": self.create_account("Cash", company, "AUD", "Cash In Hand - -TCNI_"),
				"cost_center": "Main - -TCNI_",
				"shipping_amount": 500,
				"countries": [{"country": "Australia"}],
			}
		).insert(ignore_if_duplicate=1)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "AUD",
				"conversion_rate": 53.352000000,
				"price_list_currency": "",
				"buying_price_list": "",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 100,
						"rate": 100,
						"warehouse": warehouse,
					}
				],
				"taxes": [
					{
						"category": "Valuation and Total",
						"add_deduct_tax": "Add",
						"charge_type": "Actual",
						"account_head": "Cash - -TCNI_",
						"description": "Australia",
						"tax_amount": 9.37,
					}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.taxes_and_charges_added, 9.37)
		self.assertEqual(po.grand_total, 10009.37)
		self.assertEqual(po.base_grand_total, 534019.91)

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()

		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.taxes_and_charges_added, 9.37)
		self.assertEqual(pr.grand_total, 10009.37)
		self.assertEqual(pr.base_grand_total, 534019.91)
		frappe.db.set_value("Account", "Creditors - -TCNI_", "account_currency", "AUD")
		frappe.db.set_value("Supplier", supplier, "default_currency", "AUD")
		get_pr_stock_ledger = frappe.db.get_all(
			"Stock Ledger Entry", {"voucher_no": pr.name}, ["valuation_rate", "actual_qty"]
		)
		self.assertTrue(get_pr_stock_ledger)

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill - 1122"
		pi.insert(ignore_permissions=True)
		pi.submit()

		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.taxes_and_charges_added, 9.37)
		self.assertEqual(pi.grand_total, 10009.37)
		self.assertEqual(pi.base_grand_total, 534019.91)

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.insert(ignore_permissions=True)
		pe.submit()
		self.assertEqual(pe.docstatus, 1)
		gl_entries_pr = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(gl_entries_pr)

		sle_pr = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(sle_pr)
		gl_entries_pi = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Invoice", "voucher_no": pi.name}
		)
		self.assertTrue(gl_entries_pi)
		pi_outstanding = frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount")
		self.assertEqual(pi_outstanding, 0)
		gl_entries_pe = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Payment Entry", "voucher_no": pe.name}
		)
		self.assertTrue(gl_entries_pe)

	@change_settings(
		"Global Defaults",
		{
			"default_company": "_Test company with other country address",
			"country": "India",
			"default_currency": "INR",
		},
	)
	def test_shipping_rule_net_total_restricted_country_po_pr_pi_pe_TC_B_113(self):
		get_company_supplier = create_company_and_suppliers()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - -TCNI_"
		item = make_test_item("test_item_with_fixed_shipping_rule")

		# Create Shipping Rule with Fixed Amount
		frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "_Test shipping rule wtih country address",
				"calculate_based_on": "Net Total",
				"shipping_rule_type": "Buying",
				"account": self.create_account("Cash", company, "AUD", "Cash In Hand - -TCNI_"),
				"cost_center": "Main - -TCNI_",
				"conditions": [
					{"from_value": 1, "to_value": 99, "shipping_amount": 1500},
					{"from_value": 100, "to_value": 199, "shipping_amount": 1000},
					{"from_value": 200, "to_value": 9999, "shipping_amount": 500},
				],
				"countries": [{"country": "Australia"}],
			}
		).insert(ignore_if_duplicate=1)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "AUD",
				"conversion_rate": 53.352000000,
				"price_list_currency": "",
				"buying_price_list": "",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 1,
						"rate": 3,
						"warehouse": warehouse,
					}
				],
				"taxes": [
					{
						"category": "Valuation and Total",
						"add_deduct_tax": "Add",
						"charge_type": "Actual",
						"account_head": "Cash - -TCNI_",
						"description": "Australia",
						"tax_amount": 18.74,
					}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.taxes_and_charges_added, 18.74)
		self.assertEqual(po.grand_total, 21.74)
		self.assertEqual(po.base_grand_total, 1159.87)

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()

		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.taxes_and_charges_added, 18.74)
		self.assertEqual(pr.grand_total, 21.74)
		self.assertEqual(pr.base_grand_total, 1159.87)
		get_pr_stock_ledger = frappe.db.get_all(
			"Stock Ledger Entry", {"voucher_no": pr.name}, ["valuation_rate", "actual_qty"]
		)
		self.assertTrue(get_pr_stock_ledger)

		frappe.db.set_value("Account", "Creditors - -TCNI_", "account_currency", "AUD")
		frappe.db.set_value("Supplier", supplier, "default_currency", "AUD")
		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill - 1122"
		pi.insert(ignore_permissions=True)
		pi.submit()

		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.taxes_and_charges_added, 18.74)
		self.assertEqual(pi.grand_total, 21.74)
		self.assertEqual(pi.base_grand_total, 1159.87)

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.insert(ignore_permissions=True)
		pe.submit()
		self.assertEqual(pe.docstatus, 1)
		gl_entries_pr = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(gl_entries_pr)

		sle_pr = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(sle_pr)
		gl_entries_pi = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Invoice", "voucher_no": pi.name}
		)
		self.assertTrue(gl_entries_pi)
		pi_outstanding = frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount")
		self.assertEqual(pi_outstanding, 0)
		gl_entries_pe = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Payment Entry", "voucher_no": pe.name}
		)
		self.assertTrue(gl_entries_pe)

	@change_settings(
		"Global Defaults",
		{
			"default_company": "_Test company with other country address",
			"country": "India",
			"default_currency": "INR",
		},
	)
	def test_shipping_rule_net_weight_restricted_country_po_pr_pi_pe_TC_B_114(self):
		get_company_supplier = create_company_and_suppliers()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - -TCNI_"
		item = make_test_item("test_item_with_fixed_shipping_rule")

		# Create Shipping Rule with Fixed Amount
		frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"company": company,
				"label": "_Test shipping rule wtih country address",
				"calculate_based_on": "Net Weight",
				"shipping_rule_type": "Buying",
				"account": self.create_account("Cash", company, "AUD", "Cash In Hand - -TCNI_"),
				"cost_center": "Main - -TCNI_",
				"conditions": [
					{"from_value": 1, "to_value": 9, "shipping_amount": 100},
					{"from_value": 10, "to_value": 0, "shipping_amount": 120},
				],
				"countries": [{"country": "Australia"}],
			}
		).insert(ignore_if_duplicate=1)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "AUD",
				"conversion_rate": 53.352000000,
				"price_list_currency": "",
				"buying_price_list": "",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 15,
						"rate": 1.87,
						"warehouse": warehouse,
					}
				],
				"taxes": [
					{
						"category": "Valuation and Total",
						"add_deduct_tax": "Add",
						"charge_type": "Actual",
						"account_head": "Cash - -TCNI_",
						"description": "Australia",
						"tax_amount": 2.25,
					}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.taxes_and_charges_added, 2.25)
		self.assertEqual(po.grand_total, 30.30)
		self.assertEqual(po.base_grand_total, 1616.57)

		pr = make_purchase_receipt(po.name)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.taxes_and_charges_added, 2.25)
		self.assertEqual(pr.grand_total, 30.30)
		self.assertEqual(pr.base_grand_total, 1616.57)
		get_pr_stock_ledger = frappe.db.get_all(
			"Stock Ledger Entry", {"voucher_no": pr.name}, ["valuation_rate", "actual_qty"]
		)
		self.assertTrue(get_pr_stock_ledger)
		frappe.db.set_value("Account", "Creditors - -TCNI_", "account_currency", "AUD")
		frappe.db.set_value("Supplier", supplier, "default_currency", "AUD")
		# Create Purchase Invoice from Purchase Receipt
		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill - 1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.taxes_and_charges_added, 2.25)
		self.assertEqual(pi.grand_total, 30.30)
		self.assertEqual(pi.base_grand_total, 1616.57)

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.insert(ignore_permissions=True)
		pe.submit()
		self.assertEqual(pe.docstatus, 1)
		gl_entries_pr = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(gl_entries_pr)

		sle_pr = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_type": "Purchase Receipt", "voucher_no": pr.name}
		)
		self.assertTrue(sle_pr)
		gl_entries_pi = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Purchase Invoice", "voucher_no": pi.name}
		)
		self.assertTrue(gl_entries_pi)
		pi_outstanding = frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount")
		self.assertEqual(pi_outstanding, 0)
		gl_entries_pe = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Payment Entry", "voucher_no": pe.name}
		)
		self.assertTrue(gl_entries_pe)

	def test_discount_price_list_with_po_pr_pi_TC_B_118(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - TC-5"
		item = make_test_item("test_item_with_discount")

		# Create Purchase Order
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"set_warehouse": warehouse,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"price_list_rate": 100,
						"warehouse": warehouse,
						"rate": 100,
						"margin_type": "Amount",
						"margin_rate_or_amount": 50,
						"discount_amount": 10,
					}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total, 1400)
		self.assertEqual(po.items[0].rate, 140)

		# Create Purchase Receipt from Purchase Order
		pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": po.supplier,
				"company": po.company,
				"posting_date": today(),
				"set_warehouse": warehouse,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"price_list_rate": 100,
						"warehouse": warehouse,
						"rate": 100,
						"margin_type": "Amount",
						"margin_rate_or_amount": 50,
						"discount_amount": 10,
					}
				],
			}
		)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.total, 1400)
		self.assertEqual(pr.items[0].rate, 140)

		# Create Purchase Invoice from Purchase Receipt
		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"supplier": pr.supplier,
				"company": pr.company,
				"currency": "INR",
				# "credit_to": "_Test Creditors - _TC",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"price_list_rate": 100,
						"warehouse": warehouse,
						"rate": 100,
						"margin_type": "Amount",
						"margin_rate_or_amount": 50,
						"discount_amount": 10,
					}
				],
			}
		)
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.total, 1400)
		self.assertEqual(pi.items[0].rate, 140)
		gl_entries_pe = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Purchase Invoice", "voucher_no": pi.name},
			fields=["account", "debit", "credit", "posting_date"],
		)
		self.assertTrue(gl_entries_pe)
		self.assertEqual(gl_entries_pe[0].get("account"), "Stock Received But Not Billed - TC-5")
		self.assertEqual(gl_entries_pe[0].get("debit"), 1400)
		self.assertEqual(gl_entries_pe[1].get("account"), "Creditors - TC-5")
		self.assertEqual(gl_entries_pe[1].get("credit"), 1400)

	def test_get_item_from_po_to_pr_TC_B_147(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("_test1_item")
		warehouse = "Stores - TC-5"

		po_data = {
			"company": company,
			"item_code": item.item_code,
			"supplier": supplier,
			"warehouse": warehouse,
			"qty": 10,
			"rate": 1000,
			"do_not_submit": True,
		}
		get_accounts = create_or_get_purchase_taxes_template(company=company)
		doc_po = create_purchase_order(**po_data)
		taxes = [
			{
				"charge_type": "On Net Total",
				"account_head": get_accounts.get("sgst_account"),
				"rate": 2.5,
				"description": "Input GST",
			},
			{
				"charge_type": "On Net Total",
				"account_head": get_accounts.get("cgst_account"),
				"rate": 2.5,
				"description": "Input GST",
			},
		]
		for tax in taxes:
			doc_po.append("taxes", tax)
		doc_po.save()
		doc_po.submit()
		self.assertEqual(doc_po.grand_total, 10500)
		doc_pr = make_test_pr(doc_po.name)
		self.assertEqual(doc_pr.items[0].qty, 10)
		self.assertEqual(doc_pr.items[0].rate, 1000)
		gl_entries_pr = frappe.get_all(
			"GL Entry", filters={"voucher_no": doc_pr.name}, fields=["account", "debit", "credit"]
		)
		for gl_entries in gl_entries_pr:
			if gl_entries["account"] == "Stock In Hand - TC-5":
				self.assertEqual(gl_entries["debit"], 10000)
			elif gl_entries["account"] == "Stock Received But Not Billed - TC-5":
				self.assertEqual(gl_entries["credit"], 10000)
		doc_pi = make_purchase_invoice(doc_pr.name)
		doc_pi.bill_no = "test_bill_1122"
		doc_pi.save()
		doc_pi.submit()

	def test_po_to_qi_to_pr_pi_TC_B_148(self):
		get_data = get_company_or_supplier()
		company = get_data.get("company")
		supplier = get_data.get("supplier")
		item = make_test_item("_test_items_2")
		item.inspection_required_before_purchase = 1
		template = "Syringe"
		if not frappe.db.exists("Quality Inspection Template", template):
			template = create_quality_inspection_template(template)
		item.inspection_required_before_delivery = 1
		item.quality_inspection_template = template
		item.opening_stock = 1000
		item.valuation_rate = 100
		item.save()

		po_data = {
			"company": company,
			"supplier": supplier,
			"item_code": item.item_code,
			"warehouse": "Stores - TC-5",
			"qty": 5,
			"rate": 200,
		}
		po = create_purchase_order(**po_data)
		pr = make_purchase_receipt_aganist_mr(po.name)
		pr.save()
		readings = [
			{
				"specification": "Needle Shape",
				"reading_value": "OK",
			},
			{
				"specification": "Syringe Shape",
				"reading_value": "OK",
			},
			{
				"specification": "Plastic Clarity",
				"reading_value": "OK",
			},
			{
				"specification": "Syringe Length",
				"reading_value": 5,
			},
		]
		from erpnext.stock.doctype.quality_inspection.test_quality_inspection import create_quality_inspection

		qi = create_quality_inspection(
			reference_type=pr.doctype,
			reference_name=pr.name,
			inspection_type="Incoming",
			item_code=item.item_code,
			readings=readings,
			do_not_save=True,
		)
		qi.save()
		qi.submit()
		self.assertEqual(qi.readings[0].status, "Accepted")
		self.assertEqual(qi.readings[1].status, "Accepted")
		self.assertEqual(qi.readings[2].status, "Accepted")
		self.assertEqual(qi.readings[3].status, "Accepted")
		pr.reload()
		pr.submit()
		self.assertEqual(pr.status, "To Bill")
		gl_entries_pr = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		for gl_entries in gl_entries_pr:
			if gl_entries["account"] == "Stock In Hand - _TC":
				self.assertEqual(gl_entries["debit"], 1000)
			elif gl_entries["account"] == "Stock Received But Not Billed - _TC":
				self.assertEqual(gl_entries["credit"], 1000)
		doc_pi = make_purchase_invoice(pr.name)
		doc_pi.save()
		doc_pi.submit()
		self.assertEqual(doc_pi.status, "Unpaid")

	def test_apply_only_discount_amount_on_price_list_rate_po_pr_pi_TC_B_122(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-3"
		item = make_test_item("Testing-31")

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"price_list_rate": 100,
						"discount_amount": 10,
						"warehouse": target_warehouse,
					}
				],
			}
		)
		po.items[0].rate = po.items[0].price_list_rate - po.items[0].discount_amount
		po.taxes_and_charges = ""
		po.taxes = []
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].rate, 90)
		self.assertEqual(po.total, 900)
		self.assertEqual(po.grand_total, 900)

		pr = make_purchase_receipt(po.name)
		pr.taxes_and_charges = ""
		pr.taxes = []
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.items[0].rate, 90)
		self.assertEqual(flt(pr.items[0].amount), 900)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_pr_entries = {"Stock In Hand - TC-3": 900, "Stock Received But Not Billed - TC-3": 900}
		for entry in gl_entries:
			if entry["account"] in expected_pr_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pr_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pr_entries[entry["account"]])

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.taxes_and_charges = ""
		pi.taxes = []
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.items[0].rate, 90)
		self.assertEqual(flt(pi.items[0].amount), 900)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {"Stock Received But Not Billed - TC-3": 900, "Creditors - TC-3": 900}
		for entry in gl_entries:
			if entry["account"] in expected_pi_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pi_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pi_entries[entry["account"]])

	def test_apply_discount_percentage_on_price_list_rate_po_pr_pi_TC_B_123(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-3"
		item = make_test_item("Testing-31")

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"currency": "INR",
				"schedule_date": today(),
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"price_list_rate": 100,
						"discount_percentage": 10,
						"warehouse": target_warehouse,
					}
				],
			}
		)
		po.items[0].rate = po.items[0].price_list_rate - po.items[0].discount_percentage
		po.taxes_and_charges = ""
		po.taxes = []
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].rate, 90)
		self.assertEqual(po.total, 900)
		self.assertEqual(po.grand_total, 900)

		pr = make_purchase_receipt(po.name)
		pr.taxes_and_charges = ""
		pr.taxes = []
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.items[0].rate, 90)
		self.assertEqual(flt(pr.items[0].amount), 900)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_pr_entries = {"Stock In Hand - TC-3": 900, "Stock Received But Not Billed - TC-3": 900}
		for entry in gl_entries:
			if entry["account"] in expected_pr_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pr_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pr_entries[entry["account"]])

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.taxes_and_charges = ""
		pi.taxes = []
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.items[0].rate, 90)
		self.assertEqual(flt(pi.items[0].amount), 900)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {"Stock Received But Not Billed - TC-3": 900, "Creditors - TC-3": 900}
		for entry in gl_entries:
			if entry["account"] in expected_pi_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pi_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pi_entries[entry["account"]])

	def test_apply_only_margin_amount_rate_po_pr_pi_TC_B_125(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-3"
		item = make_test_item("test_item_margin_amount")

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"price_list_rate": 100,
						"margin_type": "Amount",
						"margin_rate_or_amount": 60,
						"warehouse": target_warehouse,
					}
				],
			}
		)
		po.taxes_and_charges = ""
		po.taxes = []
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].rate, 160)
		self.assertEqual(po.total, 1600)
		self.assertEqual(po.grand_total, 1600)

		pr = make_purchase_receipt(po.name)
		pr.taxes_and_charges = ""
		pr.taxes = []
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.items[0].rate, 160)
		self.assertEqual(flt(pr.items[0].amount), 1600)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_pr_entries = {"Stock In Hand - TC-3": 1600, "Stock Received But Not Billed - TC-3": 1600}
		for entry in gl_entries:
			if entry["account"] in expected_pr_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pr_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pr_entries[entry["account"]])

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.taxes_and_charges = ""
		pi.taxes = []
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.items[0].rate, 160)
		self.assertEqual(flt(pi.items[0].amount), 1600)

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {"Stock Received But Not Billed - TC-3": 1600, "Creditors - TC-3": 1600}
		for entry in gl_entries:
			if entry["account"] in expected_pi_entries:
				if entry["debit"]:
					self.assertEqual(entry["debit"], expected_pi_entries[entry["account"]])
				if entry["credit"]:
					self.assertEqual(entry["credit"], expected_pi_entries[entry["account"]])

	@if_app_installed("india_compliance")
	def test_po_with_update_items_TC_B_128(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		warehouse = "Stores - TC-5"
		tax_account = create_or_get_purchase_taxes_template(company)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"currency": "INR",
				"set_warehouse": warehouse,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 1,
						"warehouse": warehouse,
						"rate": 1000,
					}
				],
			}
		)
		taxes = [
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("sgst_account"),
				"description": "SGST",
			},
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("cgst_account"),
				"description": "CGST",
			},
		]
		for tax in taxes:
			po.append("taxes", tax)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].qty, 1)
		self.assertEqual(po.items[0].rate, 1000)
		self.assertEqual(po.total_taxes_and_charges, 180)
		self.assertEqual(po.grand_total, 1180)

		trans_item = json.dumps(
			[{"item_code": po.items[0].item_code, "rate": 1500, "qty": 5, "docname": po.items[0].name}]
		)

		update_child_qty_rate("Purchase Order", trans_item, po.name)

		po.reload()

		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].qty, 5)
		self.assertEqual(po.items[0].rate, 1500)
		self.assertEqual(po.total_taxes_and_charges, 1350)
		self.assertEqual(po.grand_total, 8850)

	@if_app_installed("india_compliance")
	def test_po_with_partial_pr_and_update_items_TC_B_129(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company_and_supplier as create_data,
		)

		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		warehouse = "Stores - TC-3"

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"warehouse": warehouse,
						"rate": 1000,
					}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].qty, 10)
		self.assertEqual(po.items[0].rate, 1000)
		self.assertEqual(po.total_taxes_and_charges, 1800)
		self.assertEqual(po.grand_total, 11800)

		pr = make_purchase_receipt(po.name)
		pr.items[0].qty = 2
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.items[0].qty, 2)
		self.assertEqual(pr.total_taxes_and_charges, 360)
		self.assertEqual(pr.grand_total, 2360)

		trans_item = json.dumps(
			[{"item_code": po.items[0].item_code, "rate": 1000, "qty": 2, "docname": po.items[0].name}]
		)

		update_child_qty_rate("Purchase Order", trans_item, po.name)

		po.reload()

		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].qty, 2)
		self.assertEqual(po.items[0].rate, 1000)
		self.assertEqual(po.total_taxes_and_charges, 360)
		self.assertEqual(po.grand_total, 2360)

	@if_app_installed("india_compliance")
	def test_po_with_partial_pi_and_update_items_TC_B_130(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company_and_supplier as create_data,
		)

		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		warehouse = "Stores - TC-3"
		get_or_create_fiscal_year(company)
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": company,
				"schedule_date": today(),
				"set_warehouse": warehouse,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 10,
						"warehouse": warehouse,
						"rate": 1000,
					}
				],
			}
		)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.items[0].qty, 10)
		self.assertEqual(po.items[0].rate, 1000)
		self.assertEqual(po.total_taxes_and_charges, 1800)
		self.assertEqual(po.grand_total, 11800)
		pi = frappe.db.get_all("Purchase Invoice", fields=["name"])
		if pi:
			bill_no = len(pi) + 1
		else:
			bill_no = 1
		pi_1 = make_pi_from_po(po.name)
		pi_1.bill_no = f"test_bill_{bill_no}"
		pi_1.items[0].qty = 3
		pi_1.update_stock = 1
		pi_1.currency = "INR"
		pi_1.insert()
		pi_1.submit()

		self.assertEqual(pi_1.docstatus, 1)
		self.assertEqual(pi_1.items[0].qty, 3)
		self.assertEqual(pi_1.items[0].rate, 1000)

		trans_item = json.dumps(
			[
				{
					"item_code": po.items[0].item_code,
					"rate": po.items[0].rate,
					"qty": 3,
					"docname": po.items[0].name,
				},
				{"item_code": item.item_code, "rate": 2000, "qty": 7},
			]
		)
		update_child_qty_rate("Purchase Order", trans_item, po.name)

		po.reload()

		pi_2 = make_pi_from_po(po.name)
		pi_2.update_stock = 1
		pi_2.bill_no = "test_bill - 1122"
		pi_2.currency = "INR"
		pi_2.save()
		pi_2.submit()

		self.assertEqual(pi_2.docstatus, 1)
		self.assertEqual(pi_2.items[0].qty, 7)
		self.assertEqual(pi_2.items[0].rate, 2000)

	@if_app_installed("india_compliance")
	def test_po_with_parking_charges_pr_pi_TC_B_137(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company_and_supplier as create_data,
		)

		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_item("_test_item")
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Parking Charges Account",
				"company": get_company_supplier.get("parent_company"),
				"parent_account": "Indirect Expenses - TC-1",
				"account_type": "Chargeable",
				"account_currency": "INR",
			}
		).insert(ignore_if_duplicate=1)
		parking_charges_account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Parking Charges Account",
				"company": get_company_supplier.get("child_company"),
				"parent_account": "Indirect Expenses - TC-3",
				"account_type": "Chargeable",
				"account_currency": "INR",
			}
		).insert(ignore_if_duplicate=1)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"set_warehouse": "Stores - TC-3",
				"items": [{"item_code": item.item_code, "schedule_date": today(), "qty": 10, "rate": 1000}],
			}
		)
		po.insert()
		po.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": parking_charges_account.name,
				"rate": 5,
				"category": "Valuation",
				"description": "Parking Charges Account",
			},
		)
		po.save()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 1800)
		self.assertEqual(po.grand_total, 11800)

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.total_taxes_and_charges, 1800)
		self.assertEqual(pr.grand_total, 11800)

		get_pr_stock_ledger = frappe.get_all(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["warehouse", "actual_qty"],
		)
		self.assertEqual(get_pr_stock_ledger[0].get("warehouse"), "Stores - TC-3")
		self.assertEqual(get_pr_stock_ledger[0].get("actual_qty"), 10)

		pr_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_si_entries = {
			"Stock In Hand - TC-3": {"debit": 10500, "credit": 0},
			"Stock Received But Not Billed - TC-3": {"debit": 0, "credit": 10000},
			"Parking Charges Account - TC-3": {"debit": 0, "credit": 500},
		}
		for entry in pr_gle_entries:
			self.assertEqual(entry["debit"], expected_si_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_si_entries.get(entry["account"], {}).get("credit", 0))

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill - 1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.total_taxes_and_charges, 1800)
		self.assertEqual(pi.grand_total, 11800)

		pi_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {
			"Stock Received But Not Billed - TC-3": {"debit": 10000, "credit": 0},
			"Input Tax CGST - TC-3": {"debit": 900, "credit": 0},
			"Input Tax SGST - TC-3": {"debit": 900, "credit": 0},
			"Creditors - TC-3": {"debit": 0, "credit": 11800},
		}
		for entry in pi_gle_entries:
			self.assertEqual(entry["debit"], expected_pi_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_pi_entries.get(entry["account"], {}).get("credit", 0))

	@if_app_installed("india_compliance")
	def test_po_with_create_tax_template_5_pr_pi_3_TC_B_146(self):
		supplier = create_supplier(supplier_name="_Test Supplier PO")
		company = "_Test Company"
		if not frappe.db.exists("Company", company):
			company = frappe.new_doc("Company")
			company.company_name = company
			company.country = ("India",)
			company.default_currency = ("INR",)
			company.save()
		else:
			company = frappe.get_doc("Company", company)
		tax_template = "GST 12% - TC-5"
		if not frappe.db.exists("Item Tax Template", tax_template):
			tax_template = frappe.get_doc(
				{
					"doctype": "Item Tax Template",
					"title": "GST 12%",
					"company": company,
					"gst_treatment": "Taxable",
					"gst_rate": 12,
					"taxes": [
						{"tax_type": "Input Tax CGST - _TC", "tax_rate": 12 / 2},
						{"tax_type": "Input Tax SGST - _TC", "tax_rate": 12 / 2},
					],
				}
			)
			tax_template.insert(ignore_if_duplicate=True)
		else:
			tax_template = frappe.get_doc("Item Tax Template", tax_template)
		item = create_item("_Test Item")
		item = frappe.get_doc("Item", item.item_code)
		gst_hsn = frappe.get_doc("GST HSN Code", item.gst_hsn_code)
		gst_hsn.append("taxes", {"item_tax_template": tax_template.name, "valid_from": today()})
		gst_hsn.save()
		warehouse = create_warehouse("Stores - _TC", company=company.name)
		po_data_1 = {
			"company": company.name,
			"supplier": supplier.name,
			"warehouse": warehouse,
			"item_code": item.item_code,
			"qty": 1,
			"rate": 100,
		}
		doc_po_1 = create_purchase_order(**po_data_1)
		doc_pr_1 = make_test_pr(doc_po_1.name)
		doc_pr_1.save()
		doc_pr_1.submit()
		self.assertEqual(doc_pr_1.items[0].qty, 1)
		self.assertEqual(doc_pr_1.items[0].rate, 100)
		pr_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": doc_pr_1.name}, fields=["account", "debit", "credit"]
		)
		for gl_entries in pr_gl_entries:
			if gl_entries["account"] == "Stock In Hand - _TC":
				self.assertEqual(gl_entries["debit"], 100)
			elif gl_entries["account"] == "Stock Received But Not Billed - _TC":
				self.assertEqual(gl_entries["credit"], 100)
		doc_pi_1 = make_purchase_invoice(doc_pr_1.name)
		doc_pi_1.save()
		doc_pi_1.submit()
		po_data_2 = {
			"company": company.name,
			"supplier": supplier.name,
			"warehouse": warehouse,
			"item_code": item.item_code,
			"qty": 1,
			"rate": 100,
		}
		doc_po_2 = create_purchase_order(**po_data_2)
		doc_pr_2 = make_test_pr(doc_po_2.name)
		doc_pr_2.save()
		doc_pr_2.submit()
		self.assertEqual(doc_pr_2.items[0].qty, 1)
		self.assertEqual(doc_pr_2.items[0].rate, 100)
		pr_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": doc_pr_2.name}, fields=["account", "debit", "credit"]
		)
		for gl_entries in pr_gl_entries:
			if gl_entries["account"] == "Stock In Hand - _TC":
				self.assertEqual(gl_entries["debit"], 100)
			elif gl_entries["account"] == "Stock Received But Not Billed - _TC":
				self.assertEqual(gl_entries["credit"], 100)
		doc_pi_2 = make_purchase_invoice(doc_pr_2.name)
		doc_pi_2.save()
		doc_pi_2.submit()
		self.assertEqual(doc_pi_2.items[0].qty, 1)
		self.assertEqual(doc_pi_2.items[0].rate, 100)

	def test_multicurrecy_TC_B_099(self):
		get_company_supplier = get_company_or_supplier()
		company = frappe.get_doc("Company", get_company_supplier.get("company"))
		company.default_currency = "INR"
		company.unrealized_exchange_gain_loss_account = "Cash - TC-5"
		company.save()
		supplier_name = "_test_usd_supplier_1"

		# Check if supplier exists
		if not frappe.db.exists("Supplier", supplier_name):
			supplier = frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": supplier_name,
					"supplier_type": "Individual",
					"default_currency": "USD",
				}
			).insert(ignore_mandatory=1)
			supplier_name = supplier.name
		supplier = frappe.get_doc("Supplier", supplier_name)
		supplier.default_currency = "USD"
		supplier.flags.ignore_mandatory = 1
		supplier.save()
		item = make_test_item("_test_item_3")

		account = self.create_account("Creditors USD 12", company.name, "USD", "Accounts Payable - TC-5")
		if not [x for x in supplier.accounts if x.company == company.name]:
			supplier.append("accounts", {"company": company.name, "account": account.name})
			supplier.save()
		bank_name = "Bank Of America"
		bank = frappe.get_doc("Bank", bank_name) if frappe.db.exists("Bank", bank_name) else None
		if not bank:
			bank = frappe.new_doc("Bank")
			bank.bank_name = bank_name
			bank.insert()

		bank_account_name = f"{bank_name} - {bank_name}"
		if not frappe.db.exists("Bank Account", bank_account_name):
			bank_account = frappe.new_doc("Bank Account")
			bank_account.account_name = bank_name
			bank_account.bank = bank.name
			bank_account.company = company.name
			bank_account.is_company_account = 1
			bank_account.insert()
		else:
			bank_account = frappe.get_doc("Bank Account", bank_account_name)

		po_doc = create_purchase_order(
			qty=10,
			company=company,
			supplier=supplier,
			item=item.item_code,
			warehouse="Stores - TC-5",
			rate=1.59,
			currency="USD",
			do_not_save=1,
		)
		po_doc.conversion_rate = 62.9
		po_doc.save()
		po_doc.submit()
		self.assertEqual(po_doc.base_total, 1000.11)
		pr = make_purchase_receipt(po_doc.name)
		pr.save()
		pr.submit()
		self.assertEqual(pr.items[0].received_qty, 10)
		self.assertEqual(pr.base_total, 1000.11)
		pi = make_purchase_invoice(pr.name)
		pi.save()
		pi.submit()
		pr_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		self.assertEqual(pr_gl_entries[0].get("account"), "Stock Received But Not Billed - TC-5")
		self.assertEqual(pr_gl_entries[0].get("debit"), 1000.11)
		self.assertEqual(pr_gl_entries[1].get("account"), "Creditors USD 12 - TC-5")
		self.assertEqual(pr_gl_entries[1].get("credit"), 1000.11)

		pe = get_payment_entry(pi.doctype, pi.name, bank_account=pi.credit_to)
		pe.mode_of_payment = "Bank Draft"
		pe.posting_date = add_days(today(), 1)
		pe.bank_account = bank_account.name
		pe.paid_from = "Cash - TC-5"
		pe.paid_from_account_currency = "INR"
		pe.reference_no = "123"
		pe.reference_date = nowdate()
		pe.paid_to_account_currency = pi.currency
		pe.source_exchange_rate = 60
		pe.paid_amount = pi.grand_total
		pe.save(ignore_permissions=True)
		pe.submit()

		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = company.name
		err.posting_date = today()
		accounts = err.get_accounts_data()
		err.extend("accounts", accounts)
		row = err.accounts[0]
		row.new_exchange_rate = 60
		row.new_balance_in_base_currency = flt(row.new_exchange_rate * flt(row.balance_in_account_currency))
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		err.set_total_gain_loss()
		err = err.save().submit()

		# Create JV for ERR
		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("revaluation_jv"))
		je = je.submit()

		je.reload()
		self.assertEqual(je.voucher_type, "Exchange Rate Revaluation")
		self.assertEqual(je.total_debit, 1000.11)
		self.assertEqual(je.total_credit, 1000.11)

	@if_app_installed("india_compliance")
	def test_po_with_environmental_cess_pr_pi_TC_B_138(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")

		environmental_cess = create_new_account(
			account_name="Environmental Cess", company=company, parent_account="Indirect Expenses - TC-5"
		)
		tax_template = create_or_get_purchase_taxes_template(company=company)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"set_warehouse": "Stores - TC-5",
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"schedule_date": today(),
						"qty": 10,
						"rate": 1000,
						"warehouse": "Stores - TC-5",
					}
				],
			}
		)
		po.taxes_and_charges = tax_template.get("purchase_tax_template")
		po.insert()
		po.append(
			"taxes",
			{
				"charge_type": "On Previous Row Total",
				"account_head": environmental_cess,
				"rate": 5,
				"category": "Total",
				"description": "Environmental Cess",
				"row_id": 2,
			},
		)
		po.save()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 2390)
		self.assertEqual(po.grand_total, 12390)

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.total_taxes_and_charges, 2390)
		self.assertEqual(pr.grand_total, 12390)

		get_pr_stock_ledger = frappe.get_all(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["warehouse", "actual_qty"],
		)
		self.assertEqual(get_pr_stock_ledger[0].get("warehouse"), "Stores - TC-5")
		self.assertEqual(get_pr_stock_ledger[0].get("actual_qty"), 10)

		pr_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_si_entries = {
			"Stock In Hand - TC-5": {"debit": 10000, "credit": 0},
			"Stock Received But Not Billed - TC-5": {"debit": 0, "credit": 10000},
		}
		for entry in pr_gle_entries:
			self.assertEqual(entry["debit"], expected_si_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_si_entries.get(entry["account"], {}).get("credit", 0))

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill - 1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.total_taxes_and_charges, 2390)
		self.assertEqual(pi.grand_total, 12390)

		pi_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {
			"Stock Received But Not Billed - TC-5": {"debit": 10000, "credit": 0},
			"Input Tax CGST - TC-5": {"debit": 900, "credit": 0},
			"Input Tax SGST - TC-5": {"debit": 900, "credit": 0},
			"Creditors - TC-5": {"debit": 0, "credit": 12390},
			"Environmental Cess - TC-5": {"debit": 590, "credit": 0},
		}
		for entry in pi_gle_entries:
			self.assertEqual(entry["debit"], expected_pi_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_pi_entries.get(entry["account"], {}).get("credit", 0))

	@if_app_installed("india_compliance")
	def test_po_with_transportation_charges_pr_pi_TC_B_139(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		tax_account = create_or_get_purchase_taxes_template(company)
		item = make_test_item("test_item")
		item_1 = make_test_item("test_item_1")

		transportation_charges_for_child = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Transportation Charges",
				"company": get_company_supplier.get("company"),
				"parent_account": "Indirect Expenses - TC-5",
				"account_type": "Chargeable",
				"account_currency": "INR",
			}
		).insert(ignore_if_duplicate=1)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"set_warehouse": "Stores - TC-5",
				"currency": "INR",
				"items": [
					{"item_code": item.item_code, "schedule_date": today(), "qty": 10, "rate": 1000},
					{"item_code": item_1.item_code, "schedule_date": today(), "qty": 5, "rate": 200},
				],
			}
		)
		taxes = [
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("sgst_account"),
				"description": "SGST",
			},
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("cgst_account"),
				"description": "CGST",
			},
			{
				"charge_type": "On Item Quantity",
				"account_head": transportation_charges_for_child.name,
				"rate": 20,
				"category": "Valuation and Total",
				"description": "Transportation Charges",
			},
		]
		for tax in taxes:
			po.append("taxes", tax)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 2280)
		self.assertEqual(po.grand_total, 13280)

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.total_taxes_and_charges, 2280)
		self.assertEqual(pr.grand_total, 13280)

		get_pr_stock_ledger = frappe.get_all(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["warehouse", "actual_qty"],
		)
		self.assertEqual(get_pr_stock_ledger[0].get("warehouse"), "Stores - TC-5")
		self.assertEqual(get_pr_stock_ledger[0].get("actual_qty"), 5)
		self.assertEqual(get_pr_stock_ledger[1].get("warehouse"), "Stores - TC-5")
		self.assertEqual(get_pr_stock_ledger[1].get("actual_qty"), 10)

		pr_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_si_entries = {
			"Stock In Hand - TC-5": {"debit": 11300, "credit": 0},
			"Stock Received But Not Billed - TC-5": {"debit": 0, "credit": 11000},
			"Transportation Charges - TC-5": {"debit": 0, "credit": 300},
		}
		for entry in pr_gle_entries:
			self.assertEqual(entry["debit"], expected_si_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_si_entries.get(entry["account"], {}).get("credit", 0))

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill - 1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.total_taxes_and_charges, 2280)
		self.assertEqual(pi.grand_total, 13280)

		pi_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {
			"Stock Received But Not Billed - TC-5": {"debit": 11000, "credit": 0},
			"Input Tax CGST - TC-5": {"debit": 990, "credit": 0},
			"Input Tax SGST - TC-5": {"debit": 990, "credit": 0},
			"Creditors - TC-5": {"debit": 0, "credit": 13280},
			"Transportation Charges - TC-5": {"debit": 300, "credit": 0},
		}
		for entry in pi_gle_entries:
			self.assertEqual(entry["debit"], expected_pi_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_pi_entries.get(entry["account"], {}).get("credit", 0))

	def test_stop_po_creation_when_value_exceeds_budget_TC_ACC_132(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.utils import get_fiscal_year

		validate_fiscal_year("_Test Company")
		year = get_fiscal_year(date=nowdate(), company="_Test Company")[0]

		budget = frappe.get_doc(
			{
				"doctype": "Budget",
				"budget_against": "Cost Center",
				"company": "_Test Company",
				"cost_center": "_Test Write Off Cost Center - _TC",
				"fiscal_year": year,
				"applicable_on_purchase_order": 1,
				"action_if_annual_budget_exceeded_on_po": "Stop",
				"action_if_accumulated_monthly_budget_exceeded_on_po": "Stop",
				"applicable_on_booking_actual_expenses": 1,
				"action_if_annual_budget_exceeded": "Stop",
				"action_if_accumulated_monthly_budget_exceeded": "Stop",
				"accounts": [{"account": "Administrative Expenses - _TC", "budget_amount": 10000}],
			}
		).insert(ignore_permissions=1)
		budget.load_from_db()
		budget.submit()

		item = make_test_item("_Test Item")
		try:
			po = create_purchase_order(
				supplier="_Test Supplier",
				company="_Test Company",
				item_code=item.name,
				rate=11000,
				qty=1,
				do_not_save=True,
				do_not_submit=True,
			)

			po.cost_center = "_Test Write Off Cost Center - _TC"
			po.items[0].expense_account = "Administrative Expenses - _TC"
			po.items[0].cost_center = "_Test Write Off Cost Center - _TC"
			po.flags.validate = False
			po.insert(ignore_permissions=True)
			po.load_from_db()
			self.assertRaises(frappe.ValidationError, po.submit)
		except Exception as _:
			pass

			# frappe.delete_doc("Budget", budget.name,force=1)
			# frappe.delete_doc("Purchase Order", po.name,force=1)

	def test_warn_po_creation_when_value_exceeds_budget_TC_ACC_144(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.utils import get_fiscal_year

		validate_fiscal_year("_Test Company")
		year = get_fiscal_year(date=nowdate(), company="_Test Company")[0]
		if not frappe.get_value(
			"Budget",
			{
				"company": "_Test Company",
				"fiscal_year": year,
				"cost_center": "_Test Write Off Cost Center - _TC",
			},
			"name",
		):
			budget = frappe.get_doc(
				{
					"doctype": "Budget",
					"budget_against": "Cost Center",
					"company": "_Test Company",
					"cost_center": "_Test Write Off Cost Center - _TC",
					"fiscal_year": year,
					"applicable_on_purchase_order": 1,
					"action_if_annual_budget_exceeded_on_po": "Warn",
					"action_if_accumulated_monthly_budget_exceeded_on_po": "Warn",
					"applicable_on_booking_actual_expenses": 1,
					"action_if_annual_budget_exceeded": "Warn",
					"action_if_accumulated_monthly_budget_exceeded": "Warn",
					"accounts": [{"account": "Administrative Expenses - _TC", "budget_amount": 10000}],
				}
			).insert(ignore_permissions=1)
			budget.load_from_db()
			budget.submit()
		item = make_test_item("_Test Item")

		po = create_purchase_order(
			supplier="_Test Supplier",
			company="_Test Company",
			item_code=item.name,
			rate=11000,
			qty=1,
			do_not_save=True,
			do_not_submit=True,
		)

		po.cost_center = "_Test Write Off Cost Center - _TC"
		po.items[0].expense_account = "Administrative Expenses - _TC"
		po.items[0].cost_center = "_Test Write Off Cost Center - _TC"
		po.flags.validate = False
		po.insert(ignore_permissions=True)
		po.load_from_db()
		po.submit()
		budget_exceeded_found = False

		for msg in frappe.get_message_log():
			if msg.get("title") == "Budget Exceeded" and msg.get("indicator") == "orange":
				if "Annual Budget for Account" in msg.get("message", ""):
					budget_exceeded_found = True
					break

		self.assertTrue(budget_exceeded_found, "Budget exceeded message not found")

		# frappe.delete_doc("Budget", budget.name,force=1)
		# frappe.delete_doc("Purchase Order", po.name,force=1)

	@if_app_installed("india_compliance")
	def test_po_with_damage_claims_pr_pi_TC_B_140(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("test_item")
		tax_account = create_or_get_purchase_taxes_template(company)

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"set_warehouse": "Stores - TC-5",
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"schedule_date": today(),
						"qty": 10,
						"rate": 1000,
						"warehouse": "Stores - TC-5",
					}
				],
			}
		)
		taxes = [
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("sgst_account"),
				"description": "SGST",
			},
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("cgst_account"),
				"description": "CGST",
			},
			{
				"charge_type": "Actual",
				"account_head": "Cash - TC-5",
				"tax_amount": 100,
				"category": "Total",
				"add_deduct_tax": "Deduct",
				"description": "Damage Claims",
			},
		]
		for tax in taxes:
			po.append("taxes", tax)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 1700)
		self.assertEqual(po.grand_total, 11700)

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.total_taxes_and_charges, 1700)
		self.assertEqual(pr.grand_total, 11700)

		get_pr_stock_ledger = frappe.get_all(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["warehouse", "actual_qty"],
		)
		self.assertEqual(get_pr_stock_ledger[0].get("warehouse"), "Stores - TC-5")
		self.assertEqual(get_pr_stock_ledger[0].get("actual_qty"), 10)

		pr_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_si_entries = {
			"Stock In Hand - TC-5": {"debit": 10000, "credit": 0},
			"Stock Received But Not Billed - TC-5": {"debit": 0, "credit": 10000},
		}
		for entry in pr_gle_entries:
			self.assertEqual(entry["debit"], expected_si_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_si_entries.get(entry["account"], {}).get("credit", 0))

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill - 1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.total_taxes_and_charges, 1700)
		self.assertEqual(pi.grand_total, 11700)

		pi_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {
			"Stock Received But Not Billed - TC-5": {"debit": 10000, "credit": 0},
			"Input Tax CGST - TC-5": {"debit": 900, "credit": 0},
			"Input Tax SGST - TC-5": {"debit": 900, "credit": 0},
			"Creditors - TC-5": {"debit": 0, "credit": 11700},
			"Cash - TC-5": {"debit": 0, "credit": 100},
		}
		for entry in pi_gle_entries:
			self.assertEqual(entry["debit"], expected_pi_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_pi_entries.get(entry["account"], {}).get("credit", 0))

	@if_app_installed("india_compliance")
	def test_po_with_item_tax_5_pr_pi_TC_B_142(self):
		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("_test_item")
		item_tax_template = "Test Item Tax Template"
		account = frappe.db.get_value("Account", {"company": company}, "name")
		tax_category = "Test Tax Category"
		if not frappe.db.exists("Tax Category", tax_category):
			tax_category = frappe.new_doc("Tax Category")
			tax_category.title = tax_category
			tax_category.save()

		if frappe.db.exists("Purchase Taxes and Charges Template", item_tax_template):
			existing_templates = item_tax_template
		else:
			purchase_tax_template = frappe.new_doc("Purchase Taxes and Charges Template")
			purchase_tax_template.company = company
			purchase_tax_template.title = item_tax_template
			purchase_tax_template.tax_category = tax_category
			purchase_tax_template.append(
				"taxes",
				{
					"category": "Total",
					"add_deduct_tax": "Add",
					"charge_type": "On Net Total",
					"account_head": account,
					"rate": 5,
					"description": "GST",
				},
			)
			purchase_tax_template.save()
			existing_templates = purchase_tax_template.name

		apply_tax_to_item = frappe.get_doc("Item", item.name)
		apply_tax_to_item.flags.ignore_mandatory = True
		apply_tax_to_item.save()

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"set_warehouse": "Stores - TC-3",
				"currency": "INR",
				"items": [{"item_code": item.item_code, "schedule_date": today(), "qty": 10, "rate": 1000}],
			}
		)
		po.insert()
		po.taxes_and_charges = existing_templates
		po.save()
		po.submit()
		frappe.db.commit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 500)
		self.assertEqual(po.grand_total, 10500)

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.total_taxes_and_charges, 500)
		self.assertEqual(pr.grand_total, 10500)

		get_pr_stock_ledger = frappe.get_all(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["warehouse", "actual_qty"],
		)
		self.assertEqual(get_pr_stock_ledger[0].get("warehouse"), "Stores - TC-3")
		self.assertEqual(get_pr_stock_ledger[0].get("actual_qty"), 10)

		pr_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_si_entries = {
			"Stock In Hand - TC-3": {"debit": 10000, "credit": 0},
			"Stock Received But Not Billed - TC-3": {"debit": 0, "credit": 10000},
		}
		for entry in pr_gle_entries:
			for accounts in expected_si_entries:
				if entry["account"] == accounts:
					self.assertEqual(entry["debit"], expected_si_entries[accounts]["debit"])
					self.assertEqual(entry["credit"], expected_si_entries[accounts]["credit"])

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill - 1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.total_taxes_and_charges, 500)
		self.assertEqual(pi.grand_total, 10500)

		pi_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {
			"Stock Received But Not Billed - TC-3": {"debit": 10000, "credit": 0},
			"Input Tax CGST - TC-3": {"debit": 250, "credit": 0},
			"Input Tax SGST - TC-3": {"debit": 250, "credit": 0},
			"Creditors - TC-3": {"debit": 0, "credit": 10500},
		}
		for entry in pi_gle_entries:
			for accounts in expected_pi_entries:
				if entry["account"] == accounts:
					self.assertEqual(entry["debit"], expected_pi_entries[accounts]["debit"])
					self.assertEqual(entry["credit"], expected_pi_entries[accounts]["credit"])

	@if_app_installed("india_compliance")
	def test_po_with_multiple_items_single_item_tax_10_pr_pi_TC_B_143(self):
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		item_1 = make_item("test_item")
		item_2 = make_item("test_item_1")
		tax_template = "GST 10% - TC-5"
		tax_account = create_or_get_purchase_taxes_template(company)
		if not frappe.db.exists("Item Tax Template", tax_template):
			tax_template = get_item_tax_template(company, tax_template, 10)

		apply_tax_to_item = frappe.get_doc("Item", item_2.name)
		apply_tax_to_item.append("taxes", {"item_tax_template": tax_template})
		apply_tax_to_item.ignore_mandatory = True
		apply_tax_to_item.save()

		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"set_warehouse": "Stores - TC-5",
				"currency": "INR",
				"items": [
					{
						"item_code": item_1.item_code,
						"schedule_date": today(),
						"qty": 1,
						"rate": 1000,
						"warehouse": "Stores - TC-5",
					},
					{
						"item_code": item_2.item_code,
						"schedule_date": today(),
						"qty": 1,
						"rate": 1000,
						"warehouse": "Stores - TC-5",
					},
				],
			}
		)
		taxes = [
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("sgst_account"),
				"description": "SGST",
			},
			{
				"charge_type": "On Net Total",
				"add_deduct_tax": "Add",
				"category": "Total",
				"rate": 9,
				"account_head": tax_account.get("cgst_account"),
				"description": "CGST",
			},
		]
		for tax in taxes:
			po.append("taxes", tax)
		po.insert()
		po.submit()
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total_taxes_and_charges, 280)
		self.assertEqual(po.grand_total, 2280)

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.total_taxes_and_charges, 280)
		self.assertEqual(pr.grand_total, 2280)

		get_pr_stock_ledger = frappe.get_all(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["warehouse", "actual_qty"],
		)
		self.assertEqual(get_pr_stock_ledger[0].get("warehouse"), "Stores - TC-5")
		self.assertEqual(get_pr_stock_ledger[0].get("actual_qty"), 1)
		self.assertEqual(get_pr_stock_ledger[1].get("warehouse"), "Stores - TC-5")
		self.assertEqual(get_pr_stock_ledger[1].get("actual_qty"), 1)

		pr_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_si_entries = {
			"Stock In Hand - TC-5": {"debit": 2000, "credit": 0},
			"Stock Received But Not Billed - TC-5": {"debit": 0, "credit": 2000},
		}
		for entry in pr_gle_entries:
			self.assertEqual(entry["debit"], expected_si_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_si_entries.get(entry["account"], {}).get("credit", 0))

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill - 1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.total_taxes_and_charges, 280)
		self.assertEqual(pi.grand_total, 2280)

		pi_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {
			"Stock Received But Not Billed - TC-5": {"debit": 2000, "credit": 0},
			"Input Tax CGST - TC-5": {"debit": 140, "credit": 0},
			"Input Tax SGST - TC-5": {"debit": 140, "credit": 0},
			"Creditors - TC-5": {"debit": 0, "credit": 2280},
		}
		for entry in pi_gle_entries:
			self.assertEqual(entry["debit"], expected_pi_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_pi_entries.get(entry["account"], {}).get("credit", 0))

	@if_app_installed("india_compliance")
	def test_po_not_assign_tax_template_directly_pr_pi_TC_B_144(self):
			get_company_supplier = create_data()
			company = get_company_supplier.get("child_company")
			supplier = get_company_supplier.get("supplier")
			warehouse = "Stores - TC-3"
			item = make_test_item("_test_item")
			get_or_create_fiscal_year(company)
			account = frappe.db.get_value("Account", {"company": company}, "name")
			tax_category_1 = "Test Tax Category"
			if not frappe.db.exists("Tax Category", tax_category_1):
				tax_category = frappe.new_doc("Tax Category")
				tax_category.title = tax_category_1
				tax_category.save()
			item_tax_template = frappe.db.get_value(
				"Purchase Taxes and Charges Template",
				{"company": company, "tax_category": tax_category_1},
				"name",
			)
			if frappe.db.exists("Purchase Taxes and Charges Template", item_tax_template):
				existing_templates = item_tax_template
			else:
				purchase_tax_template = frappe.new_doc("Purchase Taxes and Charges Template")
				purchase_tax_template.company = company
				purchase_tax_template.title = "test"
				purchase_tax_template.tax_category = tax_category
				purchase_tax_template.append(
					"taxes",
					{
						"category": "Total",
						"add_deduct_tax": "Add",
						"charge_type": "On Net Total",
						"account_head": account,
						"rate": 5,
						"description": "GST",
					},
				)
				purchase_tax_template.save()
				existing_templates = purchase_tax_template.name
			po = frappe.get_doc(
				{
					"doctype": "Purchase Order",
					"company": company,
					"supplier": supplier,
					"set_warehouse": warehouse,
					"items": [
						{
							"item_code": item.item_code,
							"schedule_date": today(),
							"qty": 1,
							"rate": 1000,
							"warehouse": warehouse,
						}
					],
				}
			)
			po.insert()
			po.taxes_and_charges = existing_templates
			po.taxes = []
			po.append("taxes", {
				"category": "Total",
				"add_deduct_tax": "Add",
				"charge_type": "On Net Total",
				"account_head": "test account - TC-3",
				"description": "GST",
				"rate": 5
			})
			po.save()
			po.submit()
			self.assertEqual(po.docstatus, 1)
			self.assertEqual(po.total_taxes_and_charges, 50)
			self.assertEqual(po.grand_total, 1050)
			pr = make_purchase_receipt(po.name)
			pr.save()
			pr.submit()
			self.assertEqual(pr.docstatus, 1)
			self.assertEqual(pr.total_taxes_and_charges, 50)
			self.assertEqual(pr.grand_total, 1050)
			get_pr_stock_ledger = frappe.get_all(
				"Stock Ledger Entry",
				{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
				["warehouse", "actual_qty"],
			)
			self.assertEqual(get_pr_stock_ledger[0].get("warehouse"), "Stores - TC-3")
			self.assertEqual(get_pr_stock_ledger[0].get("actual_qty"), 1)
			pr_gle_entries = frappe.get_all(
				"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
			)
			expected_si_entries = {
				"Stock In Hand - TC-3": {"debit": 1000, "credit": 0},
				"Stock Received But Not Billed - TC-3": {"debit": 0, "credit": 1000},
			}
			for entry in pr_gle_entries:
				for k in expected_si_entries:
					if entry.get("account") == k:
						self.assertEqual(entry.get("debit"), expected_si_entries[k].get("debit"))
						self.assertEqual(entry.get("credit"), expected_si_entries[k].get("credit"))
			pi = make_purchase_invoice(pr.name)
			pi.bill_no = "test_bill - 1122"
			pi.insert(ignore_permissions=True)
			pi.submit()
			self.assertEqual(pi.docstatus, 1)
			self.assertEqual(pi.total_taxes_and_charges, 50)
			self.assertEqual(pi.grand_total, 1050)
			pi_gle_entries = frappe.get_all(
				"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
			)
			expected_pi_entries = {
				"Stock Received But Not Billed - TC-3": {"debit": 1000, "credit": 0},
				"Input Tax CGST - TC-3": {"debit": 25, "credit": 0},
				"Input Tax SGST - TC-3": {"debit": 25, "credit": 0},
				"Creditors - TC-3": {"debit": 0, "credit": 1050},
			}
			for entry in pi_gle_entries:
				for k in expected_pi_entries:
					if entry.get("account") == k:
						self.assertEqual(entry.get("debit"), expected_pi_entries[k].get("debit"))
						self.assertEqual(entry.get("credit"), expected_pi_entries[k].get("credit"))


	@if_app_installed("india_compliance")
	def test_po_with_create_tax_template_5_pr_pi_2_TC_B_145(self):
		supplier = create_supplier(supplier_name="_Test Supplier PO")
		company = "_Test Company"
		if not frappe.db.exists("Company", company):
			company = frappe.new_doc("Company")
			company.company_name = company
			company.country = ("India",)
			company.default_currency = ("INR",)
			company.save()
		else:
			company = frappe.get_doc("Company", company)
		tax_template = "GST 5% - TC-4"
		if not frappe.db.exists("Item Tax Template", tax_template):
			tax_template = get_tax_template(company.name, tax_template, 5)
		item_group = frappe.get_doc("Item Group", "Raw Material")
		item_group.append("taxes", {"item_tax_template": tax_template})
		item_group.save()
		item = create_item("_Test Items")
		item.item_group = "Raw Material"
		item.save()
		po_data = {
			"company": company.name,
			"supplier": supplier.name,
			"warehouse": create_warehouse("Stores - _TC", company=company.name),
			"item_code": item.item_code,
			"qty": 10,
			"rate": 1000,
		}
		doc_po = create_purchase_order(**po_data)
		doc_pr = make_test_pr(doc_po.name)
		doc_pr.save()
		doc_pr.submit()
		self.assertEqual(doc_pr.items[0].qty, 10)
		self.assertEqual(doc_pr.items[0].rate, 1000)
		pr_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": doc_pr.name}, fields=["account", "debit", "credit"]
		)
		for gl_entries in pr_gl_entries:
			if gl_entries["account"] == "Stock In Hand - _TC":
				self.assertEqual(gl_entries["debit"], 10000)
			elif gl_entries["account"] == "Stock Received But Not Billed - _TC":
				self.assertEqual(gl_entries["credit"], 10000)
		doc_pi = make_purchase_invoice(doc_pr.name)
		doc_pi.save()
		doc_pi.submit()
		self.assertEqual(doc_pi.items[0].qty, 10)
		self.assertEqual(doc_pi.items[0].rate, 1000)

	def test_single_po_pi_multi_pr_TC_SCK_122(self):
		# Scenario : 1PO => 2PR => 1PI
		frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "10% Discount",
				"company": "_Test Company",
				"apply_on": "Item Code",
				"items": [{"item_code": "_Test Item"}],
				"rate_or_discount": "Discount Percentage",
				"discount_percentage": 10,
				"selling": 0,
				"buying": 1,
			}
		).insert(ignore_if_duplicate=1)

		purchase_order_list = [
			{
				"company": "_Test Company",
				"item_code": "_Test Item",
				"warehouse": "Stores - _TC",
				"qty": 6,
				"rate": 100,
			}
		]

		pur_receipt_qty = [3, 3]
		pur_receipt_name_list = []

		doc_po = create_purchase_order(**purchase_order_list[0])
		self.assertEqual(doc_po.docstatus, 1)

		for received_qty in pur_receipt_qty:
			doc_pr = make_pr_for_po(doc_po.name, received_qty)
			self.assertEqual(doc_pr.docstatus, 1)

			pur_receipt_name_list.append(doc_pr.name)

		item_dict = [
			{
				"item_code": "_Test Item",
				"warehouse": "Stores - _TC",
				"qty": 3,
				"rate": 100,
				"purchase_receipt": pur_receipt_name_list[1],
			}
		]

		doc_pi = make_pi_against_pr(pur_receipt_name_list[0], item_dict_list=item_dict)

		self.assertEqual(doc_pi.docstatus, 1)
		self.assertEqual(doc_po.total_qty, doc_pi.total_qty)
		self.assertEqual(doc_po.grand_total, doc_pi.grand_total)

	@change_settings("Accounts Settings", {"over_billing_allowance": 25})
	@change_settings("Stock Settings", {"over_delivery_receipt_allowance": 25})
	def test_purchase_order_and_PR_TC_SCK_181(self):
		from datetime import datetime, timedelta

		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		supplier = create_supplier(
			supplier_name="_Test Supplier 1",
			supplier_type="Company",
		)
		item_fields = {
			"item_name": "_Test Book",
			"is_stock_item": 1,
			"valuation_rate": 100,
		}
		item = make_item("_Test Book", item_fields)
		today = datetime.today().date()
		schedule_date = today + timedelta(days=10)

		purchase_order = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier.name,
				"schedule_date": schedule_date,
				"company": "_Test Company",
				"items": [
					{
						"item_code": item.name,
						"qty": 8,
						"rate": 10,
						"warehouse": create_warehouse("_Test Stores", company="_Test Company"),
					}
				],
			}
		)
		purchase_order.insert()
		purchase_order.submit()

		purchase_order_item = purchase_order.items[0].name

		# Create Purchase Receipt from Purchase Order
		purchase_receipt = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": supplier.name,
				"company": "_Test Company",
				"items": [
					{
						"item_code": item.name,
						"qty": 10,  # Over-billed qty (within 20% limit)
						"rate": 10,
						"warehouse": create_warehouse("_Test Stores", company="_Test Company"),
						"purchase_order": purchase_order.name,
						"so_detail": purchase_order_item,
					}
				],
			}
		)
		purchase_receipt.insert()
		purchase_receipt.submit()

		# Check Stock Ledger
		stock_ledger_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": purchase_receipt.name},
			fields=["actual_qty", "warehouse"],
		)

		self.assertTrue(
			any(
				entry["actual_qty"] == 10 and entry["warehouse"] == "_Test Stores - _TC"
				for entry in stock_ledger_entries
			),
			"Stock Ledger did not update correctly",
		)

	def test_po_with_uploaded_file_feature_TC_B_091(self):
		import os

		import openpyxl

		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		create_supplier(supplier_name="_Test Supplier")
		make_item("_Test Item 1")
		make_item("_Test Item 2")
		filename = "sample_data.xlsx"
		headers = ["item_code", "item_name", "schedule_date", "qty", "rate"]
		data = [
			["_Test Item 1", "_Test Item 1", nowdate(), 5, 100],
			["_Test Item 2", "_Test Item 2", nowdate(), 5, 100],
		]

		workbook = openpyxl.Workbook()
		sheet = workbook.active
		sheet.title = "Sheet1"
		sheet.append(headers)
		for row in data:
			sheet.append(row)

		workbook.save(filename)
		workbook = openpyxl.load_workbook(filename)
		sheet = workbook.active

		values = [value for value in sheet.iter_rows(values_only=True)][1:]
		main_items = []
		for row in values:
			item = {
				"item_code": row[0],
				"item_name": row[1],
				"schedule_date": row[2],
				"qty": row[3],
				"rate": row[4],
			}
			main_items.append(item)

		po = frappe.new_doc("Purchase Order")
		po.company = "_Test Company"
		po.supplier = "_Test Supplier"
		po.transaction_date = nowdate()
		po.set_warehouse = "_Test Warehouse - _TC"
		for item in main_items:
			po.append("items", item)
		po.insert()
		po.save()
		po.submit()
		pr = make_pr_against_po(po.name)
		pi = make_pi_against_pr(pr.name)

		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pr.total_qty, 10)
		self.assertEqual(pi.total_qty, 10)
		self.assertEqual(pr.grand_total, 1000)
		self.assertEqual(pi.grand_total, 1000)

		for item in pi.items:
			for expected_items in main_items:
				if item.item_code == expected_items.get("item_code"):
					self.assertEqual(item.item_name, expected_items.get("item_name"))
					self.assertEqual(item.qty, expected_items.get("qty"))
					self.assertEqual(item.rate, expected_items.get("rate"))

		os.remove(filename)

	def test_close_or_unclose_purchase_orders_with_close_status_TC_B_159(self):
		from .purchase_order import close_or_unclose_purchase_orders

		po_1 = create_purchase_order()
		po_2 = create_purchase_order()

		names = [po_1.name, po_2.name]

		close_or_unclose_purchase_orders(json.dumps(names), "Closed")

		po_1.load_from_db()
		po_2.load_from_db()

		self.assertEqual(po_1.status, "Closed")
		self.assertEqual(po_2.status, "Closed")

		close_or_unclose_purchase_orders(json.dumps(names), "Open")

		po_1.load_from_db()
		po_2.load_from_db()

		self.assertEqual(po_1.status, "To Receive and Bill")
		self.assertEqual(po_2.status, "To Receive and Bill")

	@if_app_installed("projects")
	def test_validate_available_budget_TC_B_160(self):
		from unittest.mock import patch

		project_name = "test_project" + frappe.generate_hash(length=5)
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert()

		project = frappe.db.get_value("Project", {"project_name": project_name})

		wbs = frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"project": project,
				"wbs_name": "test_wbs",
				"company": "_Test Company",
				"gl_account": "Cash - _TC",
			}
		)
		wbs.insert()
		wbs.submit()

		self.assertEqual(wbs.docstatus, 1)

		zero_budget = frappe.get_doc(
			{
				"doctype": "Zero Budget",
				"project": project,
				"posting_date": today(),
				"zero_budget_item": [{"wbs_element": wbs.name, "zero_budget": 100}],
			}
		)
		zero_budget.insert()
		zero_budget.submit()

		self.assertEqual(wbs.docstatus, 1)

		wbs.load_from_db()

		wbs_1 = frappe.copy_doc(wbs)
		wbs_1.insert()
		wbs_1.submit()

		with patch("frappe.msgprint") as mock_msgprint:
			args = {"qty": 1, "rate": 200, "do_not_submit": True}
			po = create_purchase_order(**args)
			po.items[0].work_breakdown_structure = wbs.name
			po.save()

			self.assertTrue(mock_msgprint.called)
			msg_args, _ = mock_msgprint.call_args
			self.assertIn("Available Budget Limit Exceeded", msg_args[0])

			po.append(
				"items",
				{
					"item_code": "_Test Item",
					"rate": 200,
					"qty": 1,
					"warehouse": "_Test Warehouse - _TC",
					"work_breakdown_structure": wbs_1.name,
				},
			)
			po.save()
			self.assertTrue(mock_msgprint.called)
			msg_args, _ = mock_msgprint.call_args
			self.assertIn("Available Budget Limit Exceeded", msg_args[0])

	@if_app_installed("projects")
	def test_update_committed_overall_budge_TC_B_161(self):
		project_name = "test_project" + frappe.generate_hash(length=5)
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert()

		project = frappe.db.get_value("Project", {"project_name": project_name})

		wbs = frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"project": project,
				"wbs_name": "test_wbs",
				"company": "_Test Company",
				"gl_account": "Cash - _TC",
			}
		)
		wbs.insert()
		wbs.submit()

		self.assertEqual(wbs.docstatus, 1)

		zero_budget = frappe.get_doc(
			{
				"doctype": "Zero Budget",
				"project": project,
				"posting_date": today(),
				"zero_budget_item": [{"wbs_element": wbs.name, "zero_budget": 100}],
			}
		)
		zero_budget.insert()
		zero_budget.submit()

		self.assertEqual(wbs.docstatus, 1)

		args = {"qty": 1, "rate": 200, "do_not_submit": True}
		po = create_purchase_order(**args)
		po.items[0].work_breakdown_structure = wbs.name
		po.save()
		po.submit()
		self.assertEqual(po.docstatus, 1)

		po.load_from_db()
		po.cancel()

	@if_app_installed("projects")
	def test_locked_update_committed_overall_budget_TC_B_162(self):
		project_name = "test_project" + frappe.generate_hash(length=5)
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert()

		project = frappe.db.get_value("Project", {"project_name": project_name})

		wbs = frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"project": project,
				"wbs_name": "test_wbs",
				"company": "_Test Company",
				"gl_account": "Cash - _TC",
			}
		)
		wbs.insert()
		wbs.submit()

		self.assertEqual(wbs.docstatus, 1)

		zero_budget = frappe.get_doc(
			{
				"doctype": "Zero Budget",
				"project": project,
				"posting_date": today(),
				"zero_budget_item": [{"wbs_element": wbs.name, "zero_budget": 100}],
			}
		)
		zero_budget.insert()
		zero_budget.submit()

		self.assertEqual(wbs.docstatus, 1)
		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 1)

		args = {"qty": 1, "rate": 100, "do_not_submit": True}
		po = create_purchase_order(**args)
		po.items[0].work_breakdown_structure = wbs.name
		po.save()
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			po.submit()

		self.assertIn("this WBS is locked", str(cm.exception))

		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 0)
		po.submit()
		self.assertEqual(po.docstatus, 1)

		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 1)
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			po.cancel()

		self.assertIn("this WBS is locked", str(cm.exception))

	@if_app_installed("projects")
	def test_locked_committed_overall_budget_mr_po_TC_B_163(self):
		project_name = "test_project" + frappe.generate_hash(length=5)
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert()

		project = frappe.db.get_value("Project", {"project_name": project_name})

		wbs = frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"project": project,
				"wbs_name": "test_wbs",
				"company": "_Test Company",
				"gl_account": "Cash - _TC",
			}
		)
		wbs.insert()
		wbs.submit()

		self.assertEqual(wbs.docstatus, 1)

		zero_budget = frappe.get_doc(
			{
				"doctype": "Zero Budget",
				"project": project,
				"posting_date": today(),
				"zero_budget_item": [{"wbs_element": wbs.name, "zero_budget": 100}],
			}
		)
		zero_budget.insert()
		zero_budget.submit()

		args = {"qty": 1, "rate": 100}
		mr = make_material_request(**args)
		self.assertEqual(mr.docstatus, 1)

		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 1)
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.items[0].work_breakdown_structure = wbs.name
		po.save()
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			po.submit()

		self.assertIn("this WBS is locked", str(cm.exception))

		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 0)
		po.submit()
		self.assertEqual(po.docstatus, 1)

		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 1)
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			po.cancel()

		self.assertIn("this WBS is locked", str(cm.exception))

	def test_validate_bom_for_subcontracting_items_TC_B_164(self):
		item = make_test_item("__Test_item_")
		frappe.db.set_value("Item", {"item_code": item.item_code}, "is_sub_contracted_item", 1)
		args = {"item_code": item.item_code, "do_not_save": True}
		po = create_purchase_order(**args)
		po.is_old_subcontracting_flow = 1
		# Expecting validation error due to missing BOM
		try:
			po.save()
		except frappe.exceptions.ValidationError as e:
			self.assertIn("BOM is not specified for subcontracting item", str(e))

	def test_validate_supplier_score_board_to_prevent_po_TC_B_165(self):
		from frappe.exceptions import ValidationError

		criteria = "test supplier cretiria"
		supplier_name = "_Test Supplier"

		setup_supplier_scorecard(
			supplier_name,
			criteria,
			[
				{
					"standing_name": "Very Poor",
					"standing_color": "Red",
					"min_grade": 0.00,
					"max_grade": 100.00,
					"prevent_pos": 1,
				}
			],
		)

		frappe.db.set_value("Supplier", supplier_name, "prevent_pos", 1)

		args = {"supplier": supplier_name, "do_not_save": True}

		po = create_purchase_order(**args)
		with self.assertRaises(ValidationError) as e:
			po.save()

		self.assertIn(
			"Purchase Orders are not allowed for _Test Supplier due to a scorecard standing of Very Poor.",
			str(e.exception),
		)

	def test_validate_supplier_score_board_to_warn_po_TC_B_166(self):
		criteria = "test supplier cretiria"
		supplier_name = "_Test Supplier"

		setup_supplier_scorecard(
			supplier_name,
			criteria,
			[
				{
					"standing_name": "Very Poor",
					"standing_color": "Red",
					"min_grade": 0.00,
					"max_grade": 100.00,
					"warn_pos": 1,
				}
			],
		)

		frappe.db.set_value("Supplier", supplier_name, "warn_pos", 1)

		args = {"supplier": supplier_name, "do_not_submit": True}

		po_warn = create_purchase_order(**args)
		po_warn.submit()
		self.assertEqual(po_warn.docstatus, 1)

	def test_validate_fg_item_for_subcontracting_TC_B_167(self):
		item = make_test_item("__test_item")
		item.is_stock_item = 0
		item.save()
		args = {"item_code": item.item_code, "do_not_save": True}
		po = create_purchase_order(**args)
		po.is_subcontracted = 1
		with self.assertRaises(frappe.exceptions.ValidationError) as e:
			po.save()

		self.assertIn(
			"Row #1: Finished Good Item is not specified for service item __test_item", str(e.exception)
		)
		frappe.db.set_value("Item", "_Test FG Item", "is_sub_contracted_item", 0)
		po.items[0].fg_item = "_Test FG Item"
		with self.assertRaises(frappe.exceptions.ValidationError) as e:
			po.save()

		self.assertIn(
			"Row #1: Finished Good Item _Test FG Item must be a sub-contracted item", str(e.exception)
		)

		frappe.db.set_value("Item", "_Test FG Item", "is_sub_contracted_item", 1)
		frappe.db.set_value("Item", "_Test FG Item", "default_bom", "")

		po.items[0].fg_item = "_Test FG Item"
		with self.assertRaises(frappe.exceptions.ValidationError) as e:
			po.save()

		self.assertIn("Row #1: Default BOM not found for FG Item _Test FG Item", str(e.exception))

		frappe.db.set_value("Item", "_Test FG Item", "default_bom", "BOM-_Test FG Item-001")
		po.items[0].fg_item_qty = ""
		with self.assertRaises(frappe.exceptions.ValidationError) as e:
			po.save()

		self.assertIn("Row #1: Finished Good Item Qty can not be zero", str(e.exception))

	def test_make_purchase_invoice_from_portal_TC_B_168(self):
		from .purchase_order import make_purchase_invoice_from_portal

		po = create_purchase_order()
		with self.assertRaises(frappe.PermissionError) as context:
			make_purchase_invoice_from_portal(po.name)

		self.assertIn("Not Permitted", str(context.exception))

		args = {"do_not_save": True}
		po_1 = create_purchase_order(**args)
		po_1.contact_email = frappe.session.user
		po_1.save()
		po_1.submit()
		make_purchase_invoice_from_portal(po_1.name)

		self.assertEqual(frappe.response["type"], "redirect")
		self.assertIn("/purchase-invoices/", frappe.response["location"])

	def test_get_last_purchase_rate_with_old_item_TC_B_169(self):
		po_1 = create_purchase_order()
		po_1.get_last_purchase_rate()
		self.assertEqual(po_1.docstatus, 1)
		self.assertEqual(po_1.items[0].last_purchase_rate, 500)

		item = make_test_item("test__item_1")
		args = {
			"item_code": item.item_code,
		}
		po = create_purchase_order(**args)
		po.get_last_purchase_rate()
		self.assertEqual(po.items[0].base_price_list_rate, 500)

	def test_get_last_purchase_rate_with_new_item_code_TC_B_170(self):
		item = make_test_item("test__item_1")
		args = {
			"item_code": item.item_code,
		}
		po = create_purchase_order(**args)
		po.get_last_purchase_rate()
		self.assertEqual(po.items[0].base_price_list_rate, 500)

	def test_set_service_items_for_finished_goods_TC_B_171(self):
		item = make_test_item("test_items_1")
		item.is_stock_item = 0
		item.save()
		filters = {
			"is_active": 1,
			"finished_good": "_Test FG Item",
			"finished_good_qty": 1,
			"service_item": item.item_code,
			"finished_good_bom": "BOM-_Test FG Item-001",
			"service_item_uom": "Nos",
			"conversion_factor": 1,
		}
		if not frappe.db.exists("Subcontracting BOM", filters):
			sub_contracting_bom = frappe.get_doc({"doctype": "Subcontracting BOM", **filters})
			sub_contracting_bom.insert()

		args = {"item_code": item.item_code, "do_not_save": True}
		po = create_purchase_order(**args)
		po.is_subcontracted = 1
		po.items[0].item_code = ""
		po.items[0].fg_item = "_Test FG Item"
		po.set_service_items_for_finished_goods()
		po.items[0].item_code = item.item_code
		po.items[0].qty = 1
		po.save()
		po.submit()
		self.assertEqual(po.docstatus, 1)


def create_po_for_sc_testing():
	from erpnext.controllers.tests.test_subcontracting_controller import (
		make_bom_for_subcontracted_items,
		make_raw_materials,
		make_service_items,
		make_subcontracted_items,
	)

	make_subcontracted_items()
	make_raw_materials()
	make_service_items()
	make_bom_for_subcontracted_items()

	service_items = [
		{
			"warehouse": "_Test Warehouse - _TC",
			"item_code": "Subcontracted Service Item 1",
			"qty": 10,
			"rate": 100,
			"fg_item": "Subcontracted Item SA1",
			"fg_item_qty": 10,
		},
		{
			"warehouse": "_Test Warehouse - _TC",
			"item_code": "Subcontracted Service Item 2",
			"qty": 20,
			"rate": 25,
			"fg_item": "Subcontracted Item SA2",
			"fg_item_qty": 15,
		},
		{
			"warehouse": "_Test Warehouse - _TC",
			"item_code": "Subcontracted Service Item 3",
			"qty": 25,
			"rate": 10,
			"fg_item": "Subcontracted Item SA3",
			"fg_item_qty": 50,
		},
	]

	return create_purchase_order(
		rm_items=service_items,
		is_subcontracted=1,
		supplier_warehouse="_Test Warehouse 1 - _TC",
	)


def prepare_data_for_internal_transfer():
	from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_internal_supplier
	from erpnext.selling.doctype.customer.test_customer import create_internal_customer
	from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	company = "_Test Company with perpetual inventory"

	create_internal_customer(
		"_Test Internal Customer 2",
		company,
		company,
	)

	create_internal_supplier(
		"_Test Internal Supplier 2",
		company,
		company,
	)

	warehouse = create_warehouse("_Test Internal Warehouse New 1", company=company)

	create_warehouse("_Test Internal Warehouse GIT", company=company)

	make_purchase_receipt(company=company, warehouse=warehouse, qty=2, rate=100)

	if not frappe.db.get_value("Company", company, "unrealized_profit_loss_account"):
		account = "Unrealized Profit and Loss - TCP1"
		if not frappe.db.exists("Account", account):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Unrealized Profit and Loss",
					"parent_account": "Direct Income - TCP1",
					"company": company,
					"is_group": 0,
					"account_type": "Income Account",
				}
			).insert()

		frappe.db.set_value("Company", company, "unrealized_profit_loss_account", account)


def make_pr_against_po(po, received_qty=0):
	pr = make_purchase_receipt(po)
	pr.get("items")[0].qty = received_qty or 5
	pr.insert()
	pr.submit()
	return pr


def make_return_pi(source_name):
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_debit_note

	return_pi = make_debit_note(source_name)
	return_pi.update_outstanding_for_self = 0
	return_pi.insert()
	return_pi.submit()
	return return_pi


def get_same_items():
	return [
		{
			"item_code": "_Test FG Item",
			"warehouse": "_Test Warehouse - _TC",
			"qty": 1,
			"rate": 500,
			"schedule_date": add_days(nowdate(), 1),
		},
		{
			"item_code": "_Test FG Item",
			"warehouse": "_Test Warehouse - _TC",
			"qty": 4,
			"rate": 500,
			"schedule_date": add_days(nowdate(), 1),
		},
	]


def create_purchase_order(**args):
	po = frappe.new_doc("Purchase Order")
	args = frappe._dict(args)
	if args.transaction_date:
		po.transaction_date = args.transaction_date

	po.schedule_date = add_days(nowdate(), 1)
	po.company = args.company or "_Test Company"
	po.supplier = args.supplier or "_Test Supplier"
	po.is_subcontracted = args.is_subcontracted or 0
	po.currency = args.currency or frappe.get_cached_value("Company", po.company, "default_currency")
	po.conversion_factor = args.conversion_factor or 1
	po.supplier_warehouse = args.supplier_warehouse or None
	po.apply_discount_on = args.apply_discount_on or None
	po.additional_discount_percentage = args.additional_discount_percentage or None
	po.discount_amount = args.discount_amount or None
	po.shipping_rule = args.shipping_rule or None
	po.buying_price_list = args.buying_price_list or "Standard Buying"

	if args.rm_items:
		for row in args.rm_items:
			po.append("items", row)
	else:
		po.append(
			"items",
			{
				"item_code": args.item or args.item_code or "_Test Item",
				"warehouse": args.warehouse or "_Test Warehouse - _TC",
				"from_warehouse": args.from_warehouse,
				"qty": args.qty if args.qty is not None else 10,
				"rate": args.rate or 500,
				"schedule_date": add_days(nowdate(), 1),
				"include_exploded_items": args.get("include_exploded_items", 1),
				"against_blanket_order": args.against_blanket_order,
				"against_blanket": args.against_blanket,
				"material_request": args.material_request,
				"material_request_item": args.material_request_item,
			},
		)

	if not args.do_not_save:
		po.set_missing_values()
		po.insert(ignore_permissions=True)
		if not args.do_not_submit:
			if po.is_subcontracted:
				supp_items = po.get("supplied_items")
				for d in supp_items:
					if not d.reserve_warehouse:
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
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "ordered_qty"))


def get_requested_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"):
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "indented_qty"))


test_dependencies = ["BOM", "Item Price"]

test_records = frappe.get_test_records("Purchase Order")


def make_pi_against_pr(source_name, received_qty=0, item_dict_list=None, args=None):
	doc_pi = make_pi_from_pr(source_name)
	if received_qty != 0:
		doc_pi.get("items")[0].qty = received_qty

	if item_dict_list is not None:
		for item in item_dict_list:
			doc_pi.append("items", item)

	if args:
		args = frappe._dict(args)
		doc_pi.update(args)

	pi = frappe.db.get_all("Purchase Invoice", fields=["name"])
	if pi:
		bill_no = len(pi) + 1
	else:
		bill_no = 1
	doc_pi.bill_no = f"test_bill_{bill_no}"
	doc_pi.insert()
	doc_pi.submit()
	return doc_pi


def make_pr_for_po(source_name, received_qty=0, item_dict_list=None):
	doc_pr = make_purchase_receipt(source_name)
	if received_qty != 0:
		doc_pr.get("items")[0].qty = received_qty

	if item_dict_list is not None:
		for item in item_dict_list:
			doc_pr.append("items", item)

	doc_pr.insert()
	doc_pr.submit()
	return doc_pr


def check_payment_gl_entries(
	self,
	voucher_no,
	expected_gle,
):
	gle = frappe.qb.DocType("GL Entry")
	gl_entries = (
		frappe.qb.from_(gle)
		.select(
			gle.account,
			gle.debit,
			gle.credit,
		)
		.where((gle.voucher_no == voucher_no) & (gle.is_cancelled == 0))
		.orderby(gle.account, gle.debit, gle.credit, order=frappe.qb.desc)
	).run(as_dict=True)
	for row in range(len(expected_gle)):
		for field in ["account", "debit", "credit"]:
			self.assertEqual(expected_gle[row][field], gl_entries[row][field])


def create_taxes_interstate():
	acc = frappe.new_doc("Account")
	acc.account_name = "Input Tax CGST"
	acc.parent_account = "Tax Assets - _TC"
	acc.company = "_Test Company"
	account_name_cgst = frappe.db.exists(
		"Account", {"account_name": "Input Tax CGST", "company": "_Test Company"}
	)
	if not account_name_cgst:
		account_name_cgst = acc.insert(ignore_permissions=True)

	acc = frappe.new_doc("Account")
	acc.account_name = "Input Tax SGST"
	acc.parent_account = "Tax Assets - _TC"
	acc.company = "_Test Company"
	account_name_sgst = frappe.db.exists(
		"Account", {"account_name": "Input Tax SGST", "company": "_Test Company"}
	)
	if not account_name_sgst:
		account_name_sgst = acc.insert(ignore_permissions=True)

	return [
		{
			"charge_type": "On Net Total",
			"account_head": account_name_cgst,
			"rate": 9,
			"description": "Input GST",
		},
		{
			"charge_type": "On Net Total",
			"account_head": account_name_sgst,
			"rate": 9,
			"description": "Input GST",
		},
	]

def create_taxes_for_interstate():
	"""Use this for different-state (inter-state) purchases → IGST"""
	acc_igst = frappe.db.exists("Account", {"account_name": "Input Tax IGST", "company": "_Test Company"})
	if not acc_igst:
		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = "_Test Company"
		acc_igst = acc.insert(ignore_permissions=True)

	return [
		{
			"charge_type": "On Net Total",
			"account_head": acc_igst,
			"rate": 18,
			"description": "Input IGST",
		}
	]


def create_new_account(account_name, company, parent_account, account_type=None, tax_rate=None):
	if not frappe.db.exists("Account", {"account_name": account_name, "company": company}):
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"company": company,
				"parent_account": parent_account,
				"account_type": account_type,
				"tax_rate": tax_rate,
			}
		)
		account.insert(ignore_if_duplicate=1, ignore_permissions=True)
		return account.name

	else:
		account = frappe.get_doc("Account", {"company": company, "account_name": account_name})
		return account.name


def create_company():
	company_name = "_Test Company PO"
	if not frappe.db.exists("Company", company_name):
		company = frappe.new_doc("Company")
		company.company_name = company_name
		company.country = ("India",)
		company.default_currency = ("INR",)
		company.create_chart_of_accounts_based_on = ("Standard Template",)
		company.chart_of_accounts = ("Standard",)
		company = company.save()
		company.load_from_db()

	return company_name


def create_fiscal_year():
	today = date.today()
	if today.month >= 4:  # Fiscal year starts in April
		start_date = date(today.year, 4, 1)
		end_date = date(today.year + 1, 3, 31)
	else:
		start_date = date(today.year - 1, 4, 1)
		end_date = date(today.year, 3, 31)

	company = ("_Test Company PO",)
	fy_doc = frappe.new_doc("Fiscal Year")
	fy_doc.year = "2025 PO"
	fy_doc.year_start_date = start_date
	fy_doc.year_end_date = end_date
	fy_doc.append("companies", {"company": company})
	fy_doc.submit()


def make_test_po(source_name, type="Material Request", received_qty=0, item_dict=None):
	if type == "Material Request":
		doc_po = make_purchase_order(source_name)

	if type == "Supplier Quotation":
		doc_po = create_po_aganist_sq(source_name)

	if doc_po.supplier is None:
		doc_po.supplier = "_Test Supplier"

	if received_qty:
		doc_po.items[0].qty = received_qty

	if item_dict is not None:
		doc_po.append("items", item_dict)

	doc_po.currency = "INR"
	doc_po.insert()
	doc_po.submit()
	return doc_po


def make_test_pr(source_name, received_qty=None, item_dict=None):
	doc_pr = make_purchase_receipt_aganist_mr(source_name)

	if received_qty is not None:
		doc_pr.items[0].qty = received_qty

	if item_dict is not None:
		doc_pr.append("items", item_dict)

	doc_pr.insert()
	doc_pr.submit()
	return doc_pr


def make_test_pi(source_name, received_qty=None, item_dict=None):
	doc_pi = make_purchase_invoice(source_name)
	if received_qty is not None:
		doc_pi.items[0].qty = received_qty

	if item_dict is not None:
		doc_pi.append("items", item_dict)
	
	doc_pi.bill_no = "BILL-123"   # ✅ Fix for mandatory Bill No
	doc_pi.bill_date = today()
	doc_pi.insert()
	doc_pi.submit()
	return doc_pi


def make_test_rfq(source_name, received_qty=0):
	doc_rfq = make_request_for_quotation(source_name)

	supplier_data = [
		{
			"supplier": "_Test Supplier",
			"email_id": "123_testrfquser@example.com",
		}
	]
	doc_rfq.append("suppliers", supplier_data[0])
	doc_rfq.message_for_supplier = "Please supply the specified items at the best possible rates."

	if received_qty:
		doc_rfq.items[0].qty = received_qty

	doc_rfq.insert()
	doc_rfq.submit()
	return doc_rfq


def make_test_sq(source_name, rate=0, received_qty=0):
	doc_sq = make_supplier_quotation_from_rfq(source_name, for_supplier="_Test Supplier")

	if received_qty:
		doc_sq.items[0].qty = received_qty

	doc_sq.items[0].rate = rate

	doc_sq.insert()
	doc_sq.submit()
	return doc_sq


def get_shipping_rule_name(args=None):
	from erpnext.accounts.doctype.shipping_rule.test_shipping_rule import create_shipping_rule

	doc_shipping_rule = create_shipping_rule("Buying", "_Test Shipping Rule -TC", args)
	return doc_shipping_rule.name


def make_payment_entry(dt, dn, paid_amount, args=None):
	doc_pe = get_payment_entry(dt, dn, paid_amount)

	args = frappe._dict() if args is None else frappe._dict(args)
	doc_pe.mode_of_payment = args.mode_of_payment or None
	doc_pe.reference_no = args.reference_no or "Test Reference"

	doc_pe.submit()
	return doc_pe


def make_pi_direct_aganist_po(source_name):
	doc_pi = make_pi_from_po(source_name)
	doc_pi.bill_no = "test_bill_1122"
	doc_pi.insert()
	doc_pi.submit()
	return doc_pi


def make_pr_form_pi(source_name):
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_purchase_receipt

	doc_pi = make_purchase_receipt(source_name)
	doc_pi.insert()
	doc_pi.submit()
	return doc_pi


def create_company_and_suppliers():
	from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import get_active_fiscal_year

	fiscal_year = get_active_fiscal_year()
	company = "_Test company with other country address"
	supplier = "Test supplier for other country address"
	if not frappe.db.exists("Company", company):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "_Test company with other country address",
				"abbr": "-TCNI_",
				"default_currency": "INR",
				"country": "India",
				"gst_category": "Unregistered",
			}
		)
		company.insert()

		add_company_fiscal_year = frappe.get_doc("Fiscal Year", fiscal_year)
		add_company_fiscal_year.append("companies", {"company": company})
		add_company_fiscal_year.save()

		company_address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_type": "Billing",
				"address_line1": "30 Pitt Street, Sydney Harbour Marriott",
				"country": "Australia",
				"city": "Sydney",
				"pincode": "2000",
				"gst_category": "Overseas",
				"is_your_company_address": 1,
				"links": [{"link_doctype": "Company", "link_name": company}],
			}
		)
		company_address.insert()

	if not frappe.db.exists("Supplier", supplier):
		supplier = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "Test supplier for other country address",
				"country": "India",
				"supplier_type": "Company",
				"place": "Hyderabad",
			}
		)
		supplier.insert()

		supplier_address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": supplier.supplier_name,
				"address_type": "Billing",
				"address_line1": "30 Pitt Street, Sydney Harbour Marriott",
				"city": "Sydney",
				"country": "Australia",
				"pincode": 2000,
				"gst_category": "Overseas",
				"links": [{"link_doctype": "Supplier", "link_name": supplier}],
			}
		)
		supplier_address.insert()
	company_name = frappe.get_doc("Company", company)
	supplier_name = frappe.get_doc("Supplier", supplier)

	return {"company": company_name.name, "supplier": supplier_name.name}


def get_item_tax_template(company, tax_template, rate):
	if not frappe.db.exists(tax_template):
		get_company = create_data()
		create_new_account(
			account_name="Input Tax SGST",
			company=get_company.get("parent_company"),
			parent_account="Tax Assets - TC-1",
			account_type="Tax",
		)
		create_new_account(
			account_name="Input Tax CGST",
			company=get_company.get("parent_company"),
			parent_account="Tax Assets - TC-1",
			account_type="Tax",
		)
		account_cgst = create_new_account(
			account_name="Input Tax CGST",
			company=company,
			parent_account="Tax Assets - TC-3",
			account_type="Tax",
		)
		account_sgst = create_new_account(
			account_name="Input Tax SGST",
			company=company,
			parent_account="Tax Assets - TC-3",
			account_type="Tax",
		)
		tax_template = frappe.get_doc(
			{
				"doctype": "Item Tax Template",
				"title": f"GST {rate}%",
				"company": company,
				"gst_treatment": "Taxable",
				"gst_rate": rate,
				"taxes": [
					{"tax_type": account_cgst, "tax_rate": rate / 2},
					{"tax_type": account_sgst, "tax_rate": rate / 2},
				],
			}
		)
		tax_template.insert(ignore_if_duplicate=True)

		return tax_template.name


def create_quality_inspection_template(template):
	if not frappe.db.exists("Quality Inspection Template", template):
		qi_template = frappe.get_doc(
			{
				"doctype": "Quality Inspection Template",
				"quality_inspection_template_name": template,
				"item_quality_inspection_parameter": [
					{"specification": "Needle Shape", "value": "OK"},
					{"specification": "Syringe Shape", "value": "OK"},
					{"specification": "Plastic Clarity", "value": "OK"},
					{"specification": "Syringe Length", "min_value": 4, "max_value": 6},
				],
			}
		)
		qi_template.insert(ignore_if_duplicate=True)
		return qi_template.name


def get_tax_template(company, tax_template, rate):
	if not frappe.db.exists(tax_template):
		tax_template = frappe.get_doc(
			{
				"doctype": "Item Tax Template",
				"title": f"GST {rate}%",
				"company": company,
				"gst_treatment": "Taxable",
				"gst_rate": rate,
				"taxes": [
					{"tax_type": "Input Tax CGST - _TC", "tax_rate": rate / 2},
					{"tax_type": "Input Tax SGST - _TC", "tax_rate": rate / 2},
				],
			}
		)
		tax_template.insert(ignore_if_duplicate=True)

		return tax_template.name


def get_gl_entries(voucher_no):
	return frappe.get_all(
		"GL Entry", filters={"voucher_no": voucher_no}, fields=["account", "debit", "credit"]
	)


def get_sle(voucher_no):
	return frappe.get_all(
		"Stock Ledger Entry", filters={"voucher_no": voucher_no}, fields=["actual_qty", "item_code"]
	)


def validate_fiscal_year(company):
	from erpnext.accounts.utils import get_fiscal_year

	year = get_fiscal_year(today())
	if len(year) > 1:
		fiscal_year = frappe.get_doc("Fiscal Year", year[0])
		company_list = {d.company for d in fiscal_year.companies}
		if company not in company_list:
			fiscal_year.append("companies", {"company": company})
			fiscal_year.save()


def create_fiscal_with_company(company):
	today = date.today()
	if today.month >= 4:  # Fiscal year starts in April
		start_date = date(today.year, 4, 1)
		end_date = date(today.year + 1, 3, 31)
	else:
		start_date = date(today.year - 1, 4, 1)
		end_date = date(today.year, 3, 31)

	fy_doc = frappe.new_doc("Fiscal Year")
	fy_doc.year = "2024-2025"
	fy_doc.year_start_date = start_date
	fy_doc.year_end_date = end_date
	fy_doc.append("companies", {"company": company})
	fy_doc.submit()


def get_company_or_supplier():
	from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import get_active_fiscal_year

	fiscal_year = get_active_fiscal_year()
	company = "Test Company-5566"
	supplier = "Test Supplier-5566"
	customer = "Test Customer-5566"

	if not frappe.db.exists("Company", company):
		frappe.get_doc(
			{"doctype": "Company", "company_name": company, "abbr": "TC-5", "default_currency": "INR"}
		).insert()

	fiscal_year_doc = frappe.get_doc("Fiscal Year", fiscal_year)
	linked_companies = {d.company for d in fiscal_year_doc.companies}

	if company not in linked_companies:
		fiscal_year_doc.append("companies", {"company": company})
		fiscal_year_doc.save()

	if not frappe.db.exists("Supplier", supplier):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": supplier,
				"supplier_type": "Individual",
				"country": "India",
			}
		).insert()

	if not frappe.db.exists("Customer", customer):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": customer,
				"customer_type": "Individual",
				"customer_group": "All Customer Groups",
				"territory": "All Territories",
			}
		).insert()

	return {"company": company, "supplier": supplier, "customer": customer}


def create_or_get_purchase_taxes_template(company):
	sgst_account = "Input Tax SGST - TC-5"
	cgst_account = "Input Tax CGST - TC-5"
	purchase_template = "Input GST In-state - TC-5"
	tax_category = "In-State"
	if not frappe.db.exists("Tax Category", tax_category):
		tax_category = frappe.get_doc({"doctype": "Tax Category", "title": tax_category}).insert().name

	if not frappe.db.exists("Account", sgst_account):
		sgst_account = create_new_account(
			account_name="Input Tax SGST",
			company=company,
			parent_account="Tax Assets - TC-5",
			account_type="Tax",
		)

	if not frappe.db.exists("Account", cgst_account):
		cgst_account = create_new_account(
			account_name="Input Tax CGST",
			company=company,
			parent_account="Tax Assets - TC-5",
			account_type="Tax",
		)

	if not frappe.db.exists("Purchase Taxes and Charges Template", purchase_template):
		purchase_template = (
			frappe.get_doc(
				{
					"doctype": "Purchase Taxes and Charges Template",
					"title": "Input GST In-state",
					"company": company,
					"tax_category": tax_category,
					"taxes": [
						{
							"charge_type": "On Net Total",
							"add_deduct_tax": "Add",
							"category": "Total",
							"rate": 9,
							"account_head": sgst_account,
							"description": "SGST",
						},
						{
							"charge_type": "On Net Total",
							"add_deduct_tax": "Add",
							"category": "Total",
							"rate": 9,
							"account_head": cgst_account,
							"description": "CGST",
						},
					],
				}
			)
			.insert()
			.name
		)

	return {
		"purchase_tax_template": purchase_template,
		"sgst_account": sgst_account,
		"cgst_account": cgst_account,
	}


def remove_existing_shipping_rules():
	existing_shipping_rules = frappe.get_all("Shipping Rule", pluck="name")
	for rule in existing_shipping_rules:
		frappe.delete_doc("Shipping Rule", rule, force=1)


def _make_blanket_order(**args):
	from erpnext.manufacturing.doctype.blanket_order.test_blanket_order import make_blanket_order

	return make_blanket_order(**args)


def setup_supplier_scorecard(supplier_name, criteria_name, standing_options):
	if not frappe.db.exists("Supplier Scorecard Criteria", criteria_name):
		frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Criteria",
				"criteria_name": criteria_name,
				"max_score": 100,
				"formula": "10",
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Supplier Scorecard", supplier_name):
		frappe.get_doc(
			{
				"doctype": "Supplier Scorecard",
				"supplier": supplier_name,
				"period": "Per Week",
				"standings": standing_options,
				"criteria": [{"criteria_name": criteria_name, "weight": 100}],
			}
		).insert(ignore_permissions=True)
