# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, flt, getdate, nowdate
from frappe.utils.data import today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.party import get_due_date_from_template
from erpnext.buying.doctype.purchase_order.purchase_order import (
	make_inter_company_sales_order,
	make_purchase_receipt,
)
from erpnext.buying.doctype.purchase_order.purchase_order import (
	make_purchase_invoice as make_pi_from_po,
)
from erpnext.controllers.accounts_controller import InvalidQtyError, update_child_qty_rate
from erpnext.manufacturing.doctype.blanket_order.test_blanket_order import make_blanket_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
	make_purchase_invoice as make_pi_from_pr,
)


class TestPurchaseOrder(FrappeTestCase):
	def test_purchase_order_qty(self):
		po = create_purchase_order(qty=1, do_not_save=True)
		po.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": -1,
				"rate": 10,
			},
		)
		self.assertRaises(frappe.NonNegativeError, po.save)

		po.items[1].qty = 0
		self.assertRaises(InvalidQtyError, po.save)

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
		pi.insert()
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
		po.db_set("Status", "On Hold")
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
		pi.insert()
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

		make_blanket_order(blanket_order_type="Purchasing", quantity=10, rate=10)

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
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=10, rate=10)

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
		pi.insert()

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
		self.assertEqual(po.items[0].sco_qty, 5)
		self.assertEqual(po.items[1].sco_qty, 0)
		self.assertEqual(po.items[2].sco_qty, 12.5)

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
		self.assertEqual(po.items[2].sco_qty, 25)
		sco.cancel()
		po.reload()
		self.assertEqual(po.items[2].sco_qty, 12.5)

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
		pi.insert()
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
				"qty": args.qty or 10,
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
		po.insert()
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
