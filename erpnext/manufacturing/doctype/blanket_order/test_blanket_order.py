# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
from frappe.tests.utils import FrappeTestCase, change_settings, if_app_installed
from frappe.utils import add_days, add_months, nowdate, today

from erpnext import get_company_currency
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
from erpnext.stock.utils import get_or_create_fiscal_year

from .blanket_order import make_order


class TestBlanketOrder(FrappeTestCase):
	def setUp(self):
		frappe.flags.args = frappe._dict()
		if frappe.session.user != "Administrator":
			frappe.set_user("Administrator")

	def tearDown(self):
		frappe.db.rollback()

	def test_sales_order_creation(self):
		bo = make_blanket_order(blanket_order_type="Selling")

		frappe.flags.args.doctype = "Sales Order"
		so = make_order(bo.name)
		so.currency = get_company_currency(so.company)
		so.delivery_date = today()
		so.items[0].qty = 10
		so.submit()

		self.assertEqual(so.doctype, "Sales Order")
		self.assertEqual(len(so.get("items")), len(bo.get("items")))

		# check the rate, quantity and updation for the ordered quantity
		self.assertEqual(so.items[0].rate, bo.items[0].rate)

		bo = frappe.get_doc("Blanket Order", bo.name)
		self.assertEqual(so.items[0].qty, bo.items[0].ordered_qty)

		# test the quantity
		frappe.flags.args.doctype = "Sales Order"
		so1 = make_order(bo.name)
		so1.currency = get_company_currency(so1.company)
		self.assertEqual(so1.items[0].qty, (bo.items[0].qty - bo.items[0].ordered_qty))

	def test_purchase_order_creation(self):
		bo = make_blanket_order(blanket_order_type="Purchasing")

		frappe.flags.args.doctype = "Purchase Order"
		po = make_order(bo.name)
		po.currency = get_company_currency(po.company)
		po.schedule_date = today()
		po.items[0].qty = 10
		po.submit()

		self.assertEqual(po.doctype, "Purchase Order")
		self.assertEqual(len(po.get("items")), len(bo.get("items")))

		# check the rate, quantity and updation for the ordered quantity
		self.assertEqual(po.items[0].rate, po.items[0].rate)

		bo = frappe.get_doc("Blanket Order", bo.name)
		self.assertEqual(po.items[0].qty, bo.items[0].ordered_qty)

		# test the quantity
		frappe.flags.args.doctype = "Purchase Order"
		po1 = make_order(bo.name)
		po1.currency = get_company_currency(po1.company)
		self.assertEqual(po1.items[0].qty, (bo.items[0].qty - bo.items[0].ordered_qty))

	def test_blanket_order_allowance(self):
		# Sales Order
		bo = make_blanket_order(blanket_order_type="Selling", quantity=100)

		frappe.flags.args.doctype = "Sales Order"
		so = make_order(bo.name)
		so.currency = get_company_currency(so.company)
		so.delivery_date = today()
		so.items[0].qty = 110
		self.assertRaises(frappe.ValidationError, so.submit)

		frappe.db.set_single_value("Selling Settings", "blanket_order_allowance", 10)
		so.submit()

		# Purchase Order
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)

		frappe.flags.args.doctype = "Purchase Order"
		po = make_order(bo.name)
		po.currency = get_company_currency(po.company)
		po.schedule_date = today()
		po.items[0].qty = 110
		self.assertRaises(frappe.ValidationError, po.submit)

		frappe.db.set_single_value("Buying Settings", "blanket_order_allowance", 10)
		po.submit()

	def test_party_item_code(self):
		item_doc = make_item("_Test Item 1 for Blanket Order")
		item_code = item_doc.name

		customer = "_Test Customer"
		supplier = "_Test Supplier"

		if not frappe.db.exists("Item Customer Detail", {"customer_name": customer, "parent": item_code}):
			item_doc.append("customer_items", {"customer_name": customer, "ref_code": "CUST-REF-1"})
			item_doc.save()

		if not frappe.db.exists("Item Supplier", {"supplier": supplier, "parent": item_code}):
			item_doc.append("supplier_items", {"supplier": supplier, "supplier_part_no": "SUPP-PART-1"})
			item_doc.save()

		# Blanket Order for Selling
		bo = make_blanket_order(blanket_order_type="Selling", customer=customer, item_code=item_code)
		self.assertEqual(bo.items[0].party_item_code, "CUST-REF-1")

		bo = make_blanket_order(blanket_order_type="Purchasing", supplier=supplier, item_code=item_code)
		self.assertEqual(bo.items[0].party_item_code, "SUPP-PART-1")

	@if_app_installed("india_compliance")
	def test_blanket_order_to_invoice_TC_B_102(self):
		# Scenario : BO=>PO=>PR=PI
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.buying.doctype.purchase_order.test_purchase_order import (
			create_or_get_purchase_taxes_template,
			get_company_or_supplier,
		)

		data = get_company_or_supplier()
		company = data.get("company")
		supplier = data.get("supplier")
		item = make_test_item("_Test Item 1 for Blanket Order")
		tax_account = create_or_get_purchase_taxes_template(company)

		# 1. Create Blanket Order
		bo_data = {
			"doctype": "Blanket Order",
			"blanket_order_type": "Purchasing",
			"supplier": supplier,
			"company": company,
			"from_date": today(),
			"to_date": today(),
			"items": [{"item_code": item.item_code, "qty": 1000, "rate": 100}],
		}
		blanket_order = frappe.get_doc(bo_data)
		blanket_order.insert()
		blanket_order.submit()

		# 2. Create Purchase Order from Blanket Order
		frappe.flags.args.doctype = "Purchase Order"
		purchase_order = make_order(blanket_order.name)
		purchase_order.schedule_date = today()
		purchase_order.items[0].qty = 1000
		purchase_order.items[0].rate = 100
		purchase_order.items[0].warehouse = "Stores - TC-5"
		taxes = [
			{
				"charge_type": "On Net Total",
				"account_head": tax_account.get("sgst_account"),
				"rate": 9,
				"description": "Input GST",
			},
			{
				"charge_type": "On Net Total",
				"account_head": tax_account.get("cgst_account"),
				"rate": 9,
				"description": "Input GST",
			},
		]
		for tax in taxes:
			purchase_order.append("taxes", tax)
		purchase_order.insert()
		purchase_order.submit()

		# 3. Validate Blanket Order Updates
		blanket_order.reload()
		self.assertEqual(blanket_order.items[0].ordered_qty, 1000)

		purchase_receipt = make_purchase_receipt(purchase_order.name)
		purchase_receipt.insert()
		purchase_receipt.submit()

		stock_account = frappe.db.get_value("Account", {"company": company, "account_type": "Stock"}, "name")
		srbn_account = frappe.db.get_value("Account", {"company": company, "account_type": "Stock Received But Not Billed"}, "name")

		# Validate PR Accounting Entries
		pr_gl_entries = frappe.get_all("GL Entry", filters={"voucher_no": purchase_receipt.name}, fields=["account", "debit", "credit"])
		self.assertTrue(any(entry["account"] == stock_account and entry["debit"] == 100000 for entry in pr_gl_entries))
		self.assertTrue(any(entry["account"] == srbn_account and entry["credit"] == 100000 for entry in pr_gl_entries))
		pr_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": purchase_receipt.name}, fields=["account", "debit", "credit"]
		)
		self.assertTrue(
			any(
				entry["account"] == "Stock In Hand - TC-5" and entry["debit"] == 100000
				for entry in pr_gl_entries
			)
		)
		self.assertTrue(
			any(
				entry["account"] == "Stock Received But Not Billed - TC-5" and entry["credit"] == 100000
				for entry in pr_gl_entries
			)
		)

		purchase_invoice = make_purchase_invoice(purchase_receipt.name)
		purchase_invoice.insert()
		purchase_invoice.submit()

		# Validate PI Accounting Entries
		pi_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": purchase_invoice.name}, fields=["account", "debit", "credit"]
		)

		self.assertTrue(any(entry["account"] == srbn_account and entry["debit"] == 100000 for entry in pi_gl_entries))
		self.assertTrue(any(entry["account"] == "Input Tax CGST - TC-5" and entry["debit"] == 9000 for entry in pi_gl_entries))
		self.assertTrue(any(entry["account"] == "Input Tax SGST - TC-5" and entry["debit"] == 9000 for entry in pi_gl_entries))
		self.assertTrue(any(entry["account"] == "Creditors - TC-5" and entry["credit"] == 118000 for entry in pi_gl_entries))
		self.assertTrue(
			any(
				entry["account"] == "Stock Received But Not Billed - TC-5" and entry["debit"] == 100000
				for entry in pi_gl_entries
			)
		)
		self.assertTrue(
			any(
				entry["account"] == "Input Tax CGST - TC-5" and entry["debit"] == 9000
				for entry in pi_gl_entries
			)
		)
		self.assertTrue(
			any(
				entry["account"] == "Input Tax SGST - TC-5" and entry["debit"] == 9000
				for entry in pi_gl_entries
			)
		)
		self.assertTrue(
			any(
				entry["account"] == "Creditors - TC-5" and entry["credit"] == 118000
				for entry in pi_gl_entries
			)
		)

	def test_blanket_order_to_po_TC_B_093(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.buying.doctype.purchase_order.test_purchase_order import get_company_or_supplier

		data = get_company_or_supplier()
		company = data.get("company")
		supplier = data.get("supplier")
		target_warehouse = "Stores - TC-5"
		item = make_test_item("test_blanket_item")
		item_price = 3000
		qty = 3
		blanket_order = frappe.get_doc(
			{
				"doctype": "Blanket Order",
				"company": company,
				"supplier": supplier,
				"from_date": today(),
				"to_date": today(),
				"blanket_order_type": "Purchasing",
				"items": [
					{
						"item_code": item.item_code,
						"target_warehouse": target_warehouse,
						"rate": item_price,
						"qty": qty,
					}
				],
			}
		)
		blanket_order.insert()
		blanket_order.submit()
		self.assertEqual(blanket_order.docstatus, 1)
		purchase_order = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"schedule_date": today(),
				"items": [
					{
						"blanket_order": blanket_order.name,
						"item_code": item.item_code,
						"warehouse": target_warehouse,
						"qty": 5,
						"rate": item_price,
					}
				],
			}
		)
		purchase_order.items[0].qty = 2
		purchase_order.insert()
		purchase_order.submit()
		self.assertEqual(purchase_order.docstatus, 1)
		updated_blanket_order = frappe.get_doc("Blanket Order", blanket_order.name)
		self.assertEqual(updated_blanket_order.items[0].ordered_qty, 2)

	def test_blanket_order_to_sales_invoice_TC_S_054(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		frappe.flags.args.doctype = "Sales Order"
		get_or_create_fiscal_year("_Test Company")
		bo = make_blanket_order(blanket_order_type="Selling", quantity=50, rate=1000)
		so = make_order(bo.name)
		make_stock_entry(
			item_code=bo.items[0].item_code,
			qty=50,
			to_warehouse="_Test Warehouse - _TC",
			rate=1000,
			purpose="Material Receipt",
		)
		so.delivery_date = add_days(nowdate(), 5)
		so.currency = "INR"
		so.submit()

		bo.reload()
		self.assertEqual(bo.items[0].ordered_qty, 50)

		dn = make_delivery_note(so.name)
		dn.submit()
		self.assertEqual(dn.status, "To Bill")

		si = make_sales_invoice(dn.name)
		si.submit()

		debtor_account = frappe.db.get_value("Company", "_Test Company", "default_receivable_account")
		sales_account = frappe.db.get_value("Company", "_Test Company", "default_income_account")
		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": si.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}
		self.assertAlmostEqual(gl_debits[debtor_account], 50000)
		self.assertAlmostEqual(gl_credits[sales_account], 50000)

	def test_blanket_order_to_sales_invoice_with_update_stock_TC_S_055(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		frappe.flags.args.doctype = "Sales Order"
		get_or_create_fiscal_year("_Test Company")
		customer = frappe.get_doc("Customer", "_Test Customer")
		customer.default_currency = "INR"
		customer.save()
		customer.reload()
		bo = make_blanket_order(blanket_order_type="Selling", quantity=50, rate=1000)
		so = make_order(bo.name)
		so.currency = "INR"
		so.delivery_date = add_days(nowdate(), 5)
		so.submit()
		bo.reload()
		self.assertEqual(bo.items[0].ordered_qty, 50)

		make_stock_entry(
			item_code=bo.items[0].item_code,
			qty=50,
			to_warehouse="_Test Warehouse - _TC",
			rate=1000,
			purpose="Material Receipt",
		)
		si = make_sales_invoice(so.name)
		si.update_stock = 1
		si.insert()
		si.submit()

		debtor_account = frappe.db.get_value("Company", "_Test Company", "default_receivable_account")
		sales_account = frappe.db.get_value("Company", "_Test Company", "default_income_account")
		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": si.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}
		self.assertAlmostEqual(gl_debits[debtor_account], 50000)
		self.assertAlmostEqual(gl_credits[sales_account], 50000)

	def test_blanket_order_creating_quotation_TC_S_157(self):
		frappe.flags.args.doctype = "Quotation"
		bo = make_blanket_order(blanket_order_type="Selling", quantity=50, rate=1000)
		self.assertEqual(bo.docstatus, 1)

		quotation = make_order(bo.name)
		quotation.submit()
		quotation.reload()
		self.assertEqual(quotation.docstatus, 1)
		self.assertEqual(quotation.grand_total, 50000)

	@change_settings("Selling Settings", {"blanket_order_allowance": 5.0})
	def test_blanket_order_to_validate_allowance_in_sales_order_TC_S_161(self):
		frappe.flags.args.doctype = "Sales Order"

		bo = make_blanket_order(blanket_order_type="Selling", quantity=20, rate=100)
		self.assertEqual(bo.docstatus, 1)

		so = make_order(bo.name)
		so.delivery_date = add_days(nowdate(), 5)
		for itm in so.items:
			itm.qty = 21
		so.save()
		so.submit()
		so.reload()

		self.assertEqual(so.status, "To Deliver and Bill")


def make_blanket_order(**args):
	args = frappe._dict(args)
	bo = frappe.new_doc("Blanket Order")
	bo.blanket_order_type = args.blanket_order_type
	bo.company = args.company or "_Test Company"

	if args.blanket_order_type == "Selling":
		bo.customer = args.customer or "_Test Customer"
	else:
		bo.supplier = args.supplier or "_Test Supplier"

	bo.from_date = today()
	bo.to_date = add_months(bo.from_date, months=12)

	bo.append(
		"items",
		{
			"item_code": args.item_code or "_Test Item",
			"qty": args.quantity or 1000,
			"rate": args.rate or 100,
		},
	)

	# bypass permission checks to allow creation
	bo.flags.ignore_permissions = True
	bo.insert()
	bo.flags.ignore_permissions = True
	bo.submit()
	return bo


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
