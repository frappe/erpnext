# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_months, today

from erpnext import get_company_currency
from erpnext.stock.doctype.item.test_item import make_item

from .blanket_order import make_order


class TestBlanketOrder(FrappeTestCase):
	def setUp(self):
		frappe.flags.args = frappe._dict()

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

	@change_settings("Selling Settings", {"blanket_order_allowance": 0})
	@change_settings("Buying Settings", {"blanket_order_allowance": 0})
	@change_settings(
		"Stock Settings",
		{"over_delivery_receipt_allowance": 10, "role_allowed_to_over_deliver_receive": "Stock Manager"},
	)
	def test_stock_over_delivery_role_does_not_bypass_blanket_order_allowance(self):
		test_user = frappe.get_doc("User", "test@example.com")
		test_user.add_roles("Accounts User", "Stock Manager")

		frappe.clear_cache()
		for blanket_order_type, doctype, date_field in (
			("Selling", "Sales Order", "delivery_date"),
			("Purchasing", "Purchase Order", "schedule_date"),
		):
			bo = make_blanket_order(blanket_order_type=blanket_order_type, quantity=100)
			frappe.flags.args.doctype = doctype
			order = make_order(bo.name)
			order.currency = get_company_currency(order.company)
			setattr(order, date_field, today())
			order.items[0].qty = 110

			with self.set_user("test@example.com"):
				order.flags.ignore_permissions = True
				self.assertRaises(frappe.ValidationError, order.submit)

	@change_settings("Buying Settings", {"blanket_order_allowance": 0})
	def test_last_fraction_of_blanket_order_can_be_ordered(self):
		item = make_item(properties={"stock_uom": "Kg", "is_stock_item": 0}).name
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=1, item_code=item)

		frappe.flags.args.doctype = "Purchase Order"
		for qty in (0.9, 0.1):
			po = make_order(bo.name)
			po.currency = get_company_currency(po.company)
			po.schedule_date = today()
			po.items[0].qty = qty
			po.submit()

		bo.reload()
		self.assertEqual(bo.items[0].ordered_qty, 1)

<<<<<<< HEAD
=======
	def test_status_follows_close_reopen_and_cancel(self):
		bo = make_blanket_order(blanket_order_type="Selling")
		self.assertEqual(bo.status, "Submitted")

		bo.update_status("Closed")
		self.assertEqual(frappe.db.get_value("Blanket Order", bo.name, "status"), "Closed")

		bo.update_status("Submitted")
		self.assertEqual(frappe.db.get_value("Blanket Order", bo.name, "status"), "Submitted")

		bo.cancel()
		self.assertEqual(frappe.db.get_value("Blanket Order", bo.name, "status"), "Cancelled")

	def test_closed_blanket_order_cannot_be_ordered_against(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=10)

		bo.update_status("Closed")
		self.assertRaises(frappe.InvalidStatusError, make_order, bo.name)
		self.assertRaises(frappe.InvalidStatusError, po.save)

		filters = {"company": bo.company, "blanket_order_type": "Purchasing", "item": bo.items[0].item_code}
		orders = get_blanket_orders("Blanket Order", "", "name", 0, 20, filters)
		self.assertNotIn(bo.name, [order[0] for order in orders])

		details = get_blanket_order_details(
			{
				"blanket_order": bo.name,
				"company": bo.company,
				"currency": bo.currency,
				"supplier": bo.supplier,
				"doctype": "Purchase Order",
				"item_code": bo.items[0].item_code,
				"transaction_date": today(),
			}
		)
		self.assertFalse(details)

		bo.update_status("Submitted")
		po.save()

	def test_linked_row_is_checked_without_against_blanket_order(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=10)
		po.items[0].against_blanket_order = 0

		bo.update_status("Closed")
		self.assertRaises(frappe.InvalidStatusError, po.save)

	def test_update_items_cannot_raise_qty_against_closed_blanket_order(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=10)
		po.submit()
		bo.update_status("Closed")
		row = po.items[0]

		self.assertRaises(frappe.InvalidStatusError, update_purchase_order_row_qty, po, row, 20)

		update_purchase_order_row_qty(po, row, 5)
		self.assertEqual(frappe.db.get_value("Purchase Order Item", row.name, "qty"), 5)

	@ERPNextTestSuite.change_settings(
		"Buying Settings", {"blanket_order_allowance": 0, "allow_multiple_items": 1}
	)
	def test_update_items_counts_the_qty_of_deleted_rows(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=80)
		po.append("items", {**po.items[0].as_dict(), "name": None, "idx": None, "qty": 20})
		po.submit()

		update_purchase_order_row_qty(po, po.items[0], 100)

		self.assertEqual(frappe.db.get_value("Purchase Order Item", po.items[0].name, "qty"), 100)
		self.assertFalse(frappe.db.exists("Purchase Order Item", po.items[1].name))

	def test_update_items_refreshes_blanket_order_of_removed_row(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=10)
		second_item = make_item("_Test Blanket Order Second Item", {"is_stock_item": 1}).name
		po.append(
			"items",
			{
				"item_code": second_item,
				"qty": 5,
				"rate": 100,
				"warehouse": po.items[0].warehouse,
				"schedule_date": today(),
			},
		)
		po.submit()
		self.assertEqual(frappe.db.get_value("Blanket Order Item", {"parent": bo.name}, "ordered_qty"), 10)

		# Keep only the row without a blanket order
		update_purchase_order_row_qty(po, po.items[1], 5)

		self.assertEqual(frappe.db.get_value("Blanket Order Item", {"parent": bo.name}, "ordered_qty"), 0)

	@ERPNextTestSuite.change_settings(
		"Buying Settings", {"blanket_order_allowance": 0, "allow_multiple_items": 1}
	)
	def test_update_items_does_not_count_a_closed_row_as_deleted(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=80)
		po.append("items", {**po.items[0].as_dict(), "name": None, "idx": None, "qty": 20})
		po.submit()
		update_closed_status("Purchase Order", po.name, [po.items[1].name], 1)

		self.assertRaises(frappe.ValidationError, update_purchase_order_row_qty, po, po.items[0], 120)
		self.assertEqual(frappe.db.get_value("Purchase Order Item", po.items[0].name, "qty"), 80)

	def test_update_items_cannot_raise_qty_past_blanket_order(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=50)
		po.submit()
		row = po.items[0]

		self.assertRaises(frappe.ValidationError, update_purchase_order_row_qty, po, row, 250)
		self.assertEqual(frappe.db.get_value("Purchase Order Item", row.name, "qty"), 50)

		update_purchase_order_row_qty(po, row, 100)
		self.assertEqual(frappe.db.get_value("Blanket Order Item", bo.items[0].name, "ordered_qty"), 100)

	def test_cancelled_receipt_frees_the_qty_of_a_closed_row(self):
		from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

		bo = make_two_row_purchasing_blanket_order()
		frappe.flags.args.doctype = "Purchase Order"
		po = make_order(bo.name)
		po.currency = get_company_currency(po.company)
		po.schedule_date = today()
		for row in po.items:
			row.warehouse = "_Test Warehouse - _TC"
		po.submit()
		receipt = make_purchase_receipt(po.name)
		receipt.items = [row for row in receipt.items if row.item_code == "_Test Item"]
		receipt.items[0].qty = 80
		receipt.submit()
		update_closed_status("Purchase Order", po.name, [po.items[0].name], 1)
		self.assertEqual(frappe.db.get_value("Blanket Order Item", bo.items[0].name, "ordered_qty"), 80)

		receipt.cancel()

		self.assertEqual(frappe.db.get_value("Blanket Order Item", bo.items[0].name, "ordered_qty"), 0)

	def test_closing_an_unbilled_receipt_row_works(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		receipt = make_purchase_receipt(item_code="_Test Item", qty=5, rate=100)

		update_closed_status("Purchase Receipt", receipt.name, [receipt.items[0].name], 1)

		self.assertEqual(frappe.db.get_value("Purchase Receipt Item", receipt.items[0].name, "closed"), 1)

	def test_closing_every_row_closes_the_blanket_order(self):
		bo = make_blanket_order(blanket_order_type="Selling")
		row = bo.items[0].name

		update_closed_status("Blanket Order", bo.name, [row], 1)
		self.assertEqual(frappe.db.get_value("Blanket Order", bo.name, "status"), "Closed")

		bo.reload()
		self.assertRaises(frappe.ValidationError, bo.update_status, "Submitted")

		update_closed_status("Blanket Order", bo.name, [row], 0)
		self.assertEqual(frappe.db.get_value("Blanket Order", bo.name, "status"), "Submitted")

	def test_fully_ordered_row_cannot_be_closed(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=10)
		make_purchase_order_against(bo, qty=10).submit()

		self.assertRaises(
			frappe.ValidationError, update_closed_status, "Blanket Order", bo.name, [bo.items[0].name], 1
		)

	def test_closed_row_is_skipped_when_ordering(self):
		bo = make_two_row_purchasing_blanket_order()
		po = make_purchase_order_against(bo, qty=10)
		update_closed_status("Blanket Order", bo.name, [bo.items[0].name], 1)

		frappe.flags.args.doctype = "Purchase Order"
		self.assertEqual([row.item_code for row in make_order(bo.name).items], [bo.items[1].item_code])
		self.assertRaises(frappe.InvalidStatusError, po.save)

		for row, is_listed in ((bo.items[0], False), (bo.items[1], True)):
			filters = {"company": bo.company, "blanket_order_type": "Purchasing", "item": row.item_code}
			orders = get_blanket_orders("Blanket Order", "", "name", 0, 20, filters)
			self.assertEqual(bo.name in [order[0] for order in orders], is_listed)

			details = get_blanket_order_details(
				{
					"blanket_order": bo.name,
					"company": bo.company,
					"currency": bo.currency,
					"supplier": bo.supplier,
					"doctype": "Purchase Order",
					"item_code": row.item_code,
					"transaction_date": today(),
				}
			)
			self.assertEqual(bool(details), is_listed)

	def test_update_items_cannot_raise_qty_on_closed_row(self):
		bo = make_two_row_purchasing_blanket_order()
		po = make_purchase_order_against(bo, qty=10)
		po.submit()
		update_closed_status("Blanket Order", bo.name, [bo.items[0].name], 1)
		row = po.items[0]

		self.assertRaises(frappe.InvalidStatusError, update_purchase_order_row_qty, po, row, 20)

		update_purchase_order_row_qty(po, row, 5)
		self.assertEqual(frappe.db.get_value("Purchase Order Item", row.name, "qty"), 5)

	def test_update_items_cannot_raise_qty_after_blanket_order_expires(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=10)
		po.submit()
		bo.db_set("to_date", add_days(po.transaction_date, -1))
		row = po.items[0]

		self.assertRaisesRegex(
			frappe.ValidationError, "expired on", update_purchase_order_row_qty, po, row, 20
		)

		update_purchase_order_row_qty(po, row, 5)
		self.assertEqual(frappe.db.get_value("Purchase Order Item", row.name, "qty"), 5)

	def test_blanket_order_cannot_be_used_before_it_starts(self):
		bo = new_blanket_order(blanket_order_type="Purchasing")
		bo.from_date = add_days(today(), 30)
		bo.to_date = add_days(today(), 60)
		bo.append("items", {"item_code": "_Test Item", "qty": 100, "rate": 100})
		bo.insert()
		bo.submit()

		frappe.flags.args.doctype = "Purchase Order"
		self.assertRaisesRegex(frappe.ValidationError, "is valid from", make_order, bo.name)

		bo.reload()
		bo.to_date = add_days(today(), 1)
		self.assertRaises(frappe.ValidationError, bo.save)

	def test_expired_blanket_order_cannot_be_ordered_against(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		bo.db_set("to_date", today())

		frappe.flags.args.doctype = "Purchase Order"
		po = make_order(bo.name)
		po.currency = get_company_currency(po.company)
		po.transaction_date = add_days(today(), 1)
		po.schedule_date = po.transaction_date
		self.assertRaisesRegex(frappe.ValidationError, "expired on", po.save)

		po.transaction_date = today()
		po.save()

		bo.db_set("to_date", add_days(today(), -1))
		self.assertRaisesRegex(frappe.ValidationError, "expired on", make_order, bo.name)

		filters = {
			"company": bo.company,
			"blanket_order_type": "Purchasing",
			"item": bo.items[0].item_code,
			"transaction_date": today(),
		}
		orders = get_blanket_orders("Blanket Order", "", "name", 0, 20, filters)
		self.assertNotIn(bo.name, [order[0] for order in orders])

>>>>>>> 1ac7471 (test(manufacturing): Update Items refreshes blanket order of a removed row)
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

	@change_settings("Buying Settings", {"blanket_order_allowance": 10})
	def test_blanket_order_allowance_applies_to_blanket_order_qty(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		orders = [make_purchase_order_against(bo, qty=qty) for qty in (90, 15, 10)]
		orders[0].submit()
		orders[1].submit()

		self.assertRaises(frappe.ValidationError, orders[2].submit)


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

	bo.insert()
	bo.submit()
	return bo


def make_purchase_order_against(blanket_order, qty):
	frappe.flags.args.doctype = "Purchase Order"
	po = make_order(blanket_order.name)
	po.currency = get_company_currency(po.company)
	po.schedule_date = today()
	po.items[0].qty = qty
	return po
