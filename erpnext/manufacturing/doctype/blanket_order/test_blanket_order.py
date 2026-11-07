# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import json

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, add_months, today

from erpnext import get_company_currency
from erpnext.controllers.accounts_controller import update_child_qty_rate
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.get_item_details import get_blanket_order_details

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
	def test_over_order_check_uses_stock_qty(self):
		item = make_box_item("_Test Blanket Order Box Item")
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100, item_code=item)

		po = make_purchase_order_against(bo, qty=9)
		po.items[0].uom = "Box"
		po.items[0].conversion_factor = 12
		po.items[0].warehouse = "_Test Warehouse - _TC"
		self.assertRaisesRegex(frappe.ValidationError, "cannot be ordered more than", po.submit)

		po.items[0].qty = 8
		po.submit()
		self.assertEqual(frappe.db.get_value("Blanket Order Item", bo.items[0].name, "ordered_qty"), 96)

	def test_order_must_match_blanket_order_party_and_type(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)

		other_party = make_purchase_order_against(bo, qty=4)
		other_party.supplier = "_Test Supplier 1"
		self.assertRaisesRegex(frappe.ValidationError, "is for", other_party.insert)

		selling_bo = make_blanket_order(blanket_order_type="Selling", quantity=100)
		wrong_type = make_purchase_order_against(bo, qty=4)
		wrong_type.items[0].blanket_order = selling_bo.name
		self.assertRaisesRegex(frappe.ValidationError, "cannot be used on", wrong_type.insert)

		make_purchase_order_against(bo, qty=4).insert()

	@change_settings("Buying Settings", {"blanket_order_allowance": 0})
	def test_closed_order_keeps_its_received_qty(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=100)
		po.submit()
		receive_purchase_order(po, 80)

		po.reload()
		po.update_status("Closed")
		self.assertEqual(blanket_order_ordered_qty(bo), 80)
		self.assertRaisesRegex(
			frappe.ValidationError,
			"cannot be ordered more than",
			make_purchase_order_against(bo, qty=30).submit,
		)

		make_purchase_order_against(bo, qty=20).submit()
		po.reload()
		self.assertRaisesRegex(
			frappe.ValidationError, "cannot be ordered more than", po.update_status, "Draft"
		)

	def test_to_date_edited_after_submit_cannot_be_before_from_date(self):
		bo = make_blanket_order(blanket_order_type="Purchasing")
		bo.db_set("from_date", add_days(today(), 30))
		bo.reload()

		bo.to_date = add_days(today(), 1)
		self.assertRaises(frappe.ValidationError, bo.save)

		bo.reload()
		bo.to_date = add_days(today(), 60)
		bo.save()

	def test_blanket_order_rate_is_set_by_the_server(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100, rate=100)
		po = make_purchase_order_against(bo, qty=10)
		po.items[0].blanket_order_rate = 999
		po.items[0].rate = 150
		po.insert()

		self.assertEqual(po.items[0].blanket_order_rate, 100)
		self.assertIn("differs from the rate", str(frappe.message_log[-1]))

	def test_party_and_order_type_are_enforced(self):
		bo = new_blanket_order(blanket_order_type="Selling")
		bo.supplier = "_Test Supplier"
		self.assertRaises(frappe.MandatoryError, bo.insert)

		bo.customer = "_Test Customer"
		bo.insert()
		self.assertIsNone(bo.supplier)
		bo.submit()

		frappe.flags.args.doctype = "Purchase Order"
		self.assertRaisesRegex(frappe.ValidationError, "cannot be made from", make_order, bo.name)

		untyped = new_blanket_order(blanket_order_type=None)
		self.assertRaises(frappe.MandatoryError, untyped.insert)

	@change_settings("Buying Settings", {"blanket_order_allowance": 0})
	def test_blanket_order_lookup_skips_fully_ordered_order(self):
		item = make_item("_Test Blanket Order Lookup Item", {"is_stock_item": 1}).name
		used_up = make_blanket_order(blanket_order_type="Purchasing", quantity=10, rate=100, item_code=item)
		po = make_purchase_order_against(used_up, qty=10)
		po.items[0].warehouse = "_Test Warehouse - _TC"
		po.submit()
		open_order = make_blanket_order(
			blanket_order_type="Purchasing", quantity=100, rate=90, item_code=item
		)

		details = get_purchase_blanket_order_details(open_order, item)
		self.assertEqual(details.blanket_order, open_order.name)
		self.assertEqual(details.blanket_order_rate, 90)

	@change_settings("Buying Settings", {"blanket_order_allowance": 10})
	def test_blanket_order_lookup_keeps_order_within_allowance(self):
		item = make_item("_Test Blanket Order Allowance Lookup Item", {"is_stock_item": 1}).name
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100, rate=90, item_code=item)
		po = make_purchase_order_against(bo, qty=100)
		po.items[0].warehouse = "_Test Warehouse - _TC"
		po.submit()

		self.assertEqual(get_purchase_blanket_order_details(bo, item).blanket_order, bo.name)

	def test_blanket_order_lookup_skips_order_not_started(self):
		item = make_item("_Test Blanket Order Not Started Lookup Item", {"is_stock_item": 1}).name
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100, rate=90, item_code=item)
		bo.db_set("from_date", add_days(today(), 30))

		self.assertFalse(get_purchase_blanket_order_details(bo, item))

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

	def test_update_items_cannot_raise_qty_past_blanket_order(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=50)
		po.submit()
		row = po.items[0]

		self.assertRaises(frappe.ValidationError, update_purchase_order_row_qty, po, row, 250)
		self.assertEqual(frappe.db.get_value("Purchase Order Item", row.name, "qty"), 50)

		update_purchase_order_row_qty(po, row, 100)
		self.assertEqual(frappe.db.get_value("Blanket Order Item", bo.items[0].name, "ordered_qty"), 100)

	@change_settings("Buying Settings", {"blanket_order_allowance": 0, "allow_multiple_items": 1})
	def test_update_items_checks_the_net_change(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=50)
		po.append("items", {**po.items[0].as_dict(), "name": None, "idx": None, "qty": 50})
		po.submit()

		payload = [
			{
				"docname": row.name,
				"item_code": row.item_code,
				"qty": qty,
				"rate": row.rate,
				"uom": row.uom,
				"conversion_factor": row.conversion_factor,
				"schedule_date": str(row.schedule_date),
			}
			for row, qty in zip(po.items, (40, 60), strict=True)
		]
		update_child_qty_rate("Purchase Order", json.dumps(payload), po.name)

		self.assertEqual(
			[frappe.db.get_value("Purchase Order Item", row.name, "qty") for row in po.items], [40, 60]
		)

	@change_settings("Buying Settings", {"blanket_order_allowance": 0, "allow_multiple_items": 1})
	def test_update_items_counts_the_qty_of_deleted_rows(self):
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)
		po = make_purchase_order_against(bo, qty=80)
		po.append("items", {**po.items[0].as_dict(), "name": None, "idx": None, "qty": 20})
		po.submit()

		update_purchase_order_row_qty(po, po.items[0], 100)

		self.assertEqual(frappe.db.get_value("Purchase Order Item", po.items[0].name, "qty"), 100)
		self.assertFalse(frappe.db.exists("Purchase Order Item", po.items[1].name))


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


def update_purchase_order_row_qty(po, row, qty):
	payload = {
		"docname": row.name,
		"item_code": row.item_code,
		"qty": qty,
		"rate": row.rate,
		"uom": row.uom,
		"conversion_factor": row.conversion_factor,
		"schedule_date": str(row.schedule_date),
	}
	update_child_qty_rate("Purchase Order", json.dumps([payload]), po.name)


def make_box_item(item_code):
	return make_item(
		item_code,
		{
			"is_stock_item": 1,
			"stock_uom": "Nos",
			"uoms": [{"uom": "Nos", "conversion_factor": 1}, {"uom": "Box", "conversion_factor": 12}],
		},
	).name


def receive_purchase_order(po, qty):
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	receipt = make_purchase_receipt(po.name)
	receipt.items[0].qty = qty
	receipt.submit()
	return receipt


def blanket_order_ordered_qty(bo):
	return frappe.db.get_value("Blanket Order Item", bo.items[0].name, "ordered_qty")


def new_blanket_order(blanket_order_type):
	bo = frappe.new_doc("Blanket Order")
	bo.blanket_order_type = blanket_order_type
	bo.company = "_Test Company"
	bo.from_date = today()
	bo.to_date = add_months(bo.from_date, months=12)
	bo.append("items", {"item_code": "_Test Item", "qty": 10, "rate": 100})
	return bo


def get_purchase_blanket_order_details(blanket_order, item_code):
	return get_blanket_order_details(
		{
			"company": "_Test Company",
			"supplier": blanket_order.supplier,
			"doctype": "Purchase Order",
			"item_code": item_code,
			"transaction_date": today(),
		}
	)
