# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import re
from datetime import datetime

import frappe
import frappe.permissions
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.tests.utils import FrappeTestCase, change_settings, if_app_installed
from frappe.utils import add_days, add_months, add_to_date, flt, getdate, nowdate, today

from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.controllers.accounts_controller import InvalidQtyError
from erpnext.maintenance.doctype.maintenance_schedule.test_maintenance_schedule import (
	make_maintenance_schedule,
)
from erpnext.maintenance.doctype.maintenance_visit.test_maintenance_visit import (
	make_maintenance_visit,
)
from erpnext.selling.doctype.customer.customer import get_customer_outstanding
from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
from erpnext.selling.doctype.sales_order.sales_order import (
	WarehouseRequired,
	create_pick_list,
	make_delivery_note,
	make_material_request,
	make_raw_material_request,
	make_sales_invoice,
	make_work_orders,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.get_item_details import get_bin_details
from erpnext.stock.utils import get_or_create_fiscal_year


class TestSalesOrder(AccountsTestMixin, FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.unlink_setting = int(
			frappe.db.get_value(
				"Accounts Settings", "Accounts Settings", "unlink_advance_payment_on_cancelation_of_order"
			)
		)

	@classmethod
	def tearDownClass(cls) -> None:
		# reset config to previous state
		frappe.db.set_single_value(
			"Accounts Settings", "unlink_advance_payment_on_cancelation_of_order", cls.unlink_setting
		)
		super().tearDownClass()

	def setUp(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		create_company()
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		self.create_customer("_Test Customer Credit")
		self.create_customer("_Test Customer", currency="INR")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_sales_order_with_negative_rate(self):
		"""
		Test if negative rate is allowed in Sales Order via doc submission and update items
		"""
		so = make_sales_order(qty=1, rate=100, do_not_save=True)
		so.append("items", {"item_code": "_Test Item", "qty": 1, "rate": -10})
		so.save()
		so.submit()

		first_item = so.get("items")[0]
		second_item = so.get("items")[1]
		trans_item = json.dumps(
			[
				{
					"item_code": first_item.item_code,
					"rate": first_item.rate,
					"qty": first_item.qty,
					"docname": first_item.name,
				},
				{
					"item_code": second_item.item_code,
					"rate": -20,
					"qty": second_item.qty,
					"docname": second_item.name,
				},
			]
		)
		update_child_qty_rate("Sales Order", trans_item, so.name)

	def test_sales_order_qty(self):
		so = make_sales_order(qty=1, do_not_save=True)

		# NonNegativeError with qty=-1
		so.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": -1,
				"rate": 10,
			},
		)
		self.assertRaises(frappe.NonNegativeError, so.save)

		# InvalidQtyError with qty=0
		so.items[1].qty = 0
		self.assertRaises(InvalidQtyError, so.save)

		# No error with qty=1
		so.items[1].qty = 1
		so.save()
		self.assertEqual(so.items[0].qty, 1)

	def test_make_material_request(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_material_request, so.name)

		so.submit()
		mr = make_material_request(so.name)

		self.assertEqual(mr.material_request_type, "Purchase")
		self.assertEqual(len(mr.get("items")), len(so.get("items")))

		for item in mr.get("items"):
			actual_qty = get_bin_details(item.item_code, item.warehouse, mr.company, True).get(
				"actual_qty", 0
			)
			self.assertEqual(flt(item.actual_qty), actual_qty)

	def test_make_delivery_note(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_delivery_note, so.name)

		so.submit()
		dn = make_delivery_note(so.name)

		self.assertEqual(dn.doctype, "Delivery Note")
		self.assertEqual(len(dn.get("items")), len(so.get("items")))

	def test_make_sales_invoice(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_sales_invoice, so.name)

		so.submit()
		si = make_sales_invoice(so.name)

		self.assertEqual(len(si.get("items")), len(so.get("items")))
		self.assertEqual(len(si.get("items")), 1)

		si.insert()
		si.submit()

		si1 = make_sales_invoice(so.name)
		self.assertEqual(len(si1.get("items")), 0)

	def test_so_billed_amount_against_return_entry(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

		so = make_sales_order(do_not_submit=True)
		so.submit()

		si = make_sales_invoice(so.name)
		si.insert()
		si.submit()

		si1 = make_sales_return(si.name)
		si1.update_billed_amount_in_sales_order = 1
		si1.submit()
		so.load_from_db()
		self.assertEqual(so.per_billed, 0)

	def test_make_sales_invoice_with_terms(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_sales_invoice, so.name)

		so.update({"payment_terms_template": "_Test Payment Term Template"})

		so.save()
		so.submit()
		si = make_sales_invoice(so.name)

		self.assertEqual(len(si.get("items")), len(so.get("items")))
		self.assertEqual(len(si.get("items")), 1)

		si.insert()
		si.set("taxes", [])
		si.save()

		transaction_date = datetime.strptime(so.transaction_date, "%Y-%m-%d").date()
		self.assertEqual(si.payment_schedule[0].payment_amount, 500.0)
		self.assertEqual(si.payment_schedule[0].due_date, transaction_date)
		self.assertEqual(si.payment_schedule[1].payment_amount, 500.0)
		self.assertEqual(si.payment_schedule[1].due_date, add_days(transaction_date, 30))

		si.submit()

		si1 = make_sales_invoice(so.name)
		self.assertEqual(len(si1.get("items")), 0)

	def test_update_qty(self):
		so = make_sales_order()

		create_dn_against_so(so.name, 6)

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 6)

		# Check delivered_qty after make_sales_invoice without update_stock checked
		si1 = make_sales_invoice(so.name)
		si1.get("items")[0].qty = 6
		si1.insert()
		si1.submit()

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 6)

		# Check delivered_qty after make_sales_invoice with update_stock checked
		si2 = make_sales_invoice(so.name)
		si2.set("update_stock", 1)
		si2.get("items")[0].qty = 3
		si2.insert()
		si2.submit()

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 9)

	def test_return_against_sales_order(self):
		so = make_sales_order()

		dn = create_dn_against_so(so.name, 6)

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 6)

		# Check delivered_qty after make_sales_invoice with update_stock checked
		si2 = make_sales_invoice(so.name)
		si2.set("update_stock", 1)
		si2.get("items")[0].qty = 3
		si2.insert()
		si2.submit()

		so.load_from_db()

		self.assertEqual(so.get("items")[0].delivered_qty, 9)

		# Make return deliver note, sales invoice and check quantity
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		dn1 = create_delivery_note(is_return=1, return_against=dn.name, qty=-3, do_not_submit=True)
		dn1.items[0].against_sales_order = so.name
		dn1.items[0].so_detail = so.items[0].name
		dn1.submit()

		si1 = create_sales_invoice(
			is_return=1, return_against=si2.name, qty=-1, update_stock=1, do_not_submit=True
		)
		si1.items[0].sales_order = so.name
		si1.items[0].so_detail = so.items[0].name
		si1.submit()

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 5)

	def test_reserved_qty_for_partial_delivery(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)
		existing_reserved_qty = get_reserved_qty()

		so = make_sales_order()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

		dn = create_dn_against_so(so.name)
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 5)

		# close so
		so.load_from_db()
		so.update_status("Closed")
		self.assertEqual(get_reserved_qty(), existing_reserved_qty)

		# unclose so
		so.load_from_db()
		so.update_status("Draft")
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 5)

		dn.cancel()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

		# cancel
		so.load_from_db()
		so.cancel()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty)

	def test_reserved_qty_for_over_delivery(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)
		# set over-delivery allowance
		frappe.db.set_value("Item", "_Test Item", "over_delivery_receipt_allowance", 50)

		existing_reserved_qty = get_reserved_qty()

		so = make_sales_order()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

		dn = create_dn_against_so(so.name, 15)
		self.assertEqual(get_reserved_qty(), existing_reserved_qty)

		dn.cancel()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

	def test_reserved_qty_for_over_delivery_via_sales_invoice(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)

		# set over-delivery allowance
		frappe.db.set_value("Item", "_Test Item", "over_delivery_receipt_allowance", 50)
		frappe.db.set_value("Item", "_Test Item", "over_billing_allowance", 20)

		existing_reserved_qty = get_reserved_qty()

		so = make_sales_order()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

		si = make_sales_invoice(so.name)
		si.update_stock = 1
		si.get("items")[0].qty = 12
		si.insert()
		si.submit()

		self.assertEqual(get_reserved_qty(), existing_reserved_qty)

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 12)
		self.assertEqual(so.per_delivered, 100)

		si.cancel()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 0)
		self.assertEqual(so.per_delivered, 0)

	def test_reserved_qty_for_partial_delivery_with_packing_list(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)
		make_stock_entry(item="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", qty=10, rate=100)

		existing_reserved_qty_item1 = get_reserved_qty("_Test Item")
		existing_reserved_qty_item2 = get_reserved_qty("_Test Item Home Desktop 100")

		so = make_sales_order(item_code="_Test Product Bundle Item")

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 50)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2 + 20)

		dn = create_dn_against_so(so.name)

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 25)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2 + 10)

		# close so
		so.load_from_db()
		so.update_status("Closed")

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2)

		# unclose so
		so.load_from_db()
		so.update_status("Draft")

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 25)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2 + 10)

		dn.cancel()
		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 50)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2 + 20)

		so.load_from_db()
		so.cancel()
		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2)

	def test_sales_order_on_hold(self):
		so = make_sales_order(item_code="_Test Product Bundle Item")
		so.db_set("status", "On Hold")
		si = make_sales_invoice(so.name)
		self.assertRaises(frappe.ValidationError, create_dn_against_so, so.name)
		self.assertRaises(frappe.ValidationError, si.submit)

	def test_reserved_qty_for_over_delivery_with_packing_list(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)
		make_stock_entry(item="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", qty=10, rate=100)

		# set over-delivery allowance
		frappe.db.set_value("Item", "_Test Product Bundle Item", "over_delivery_receipt_allowance", 50)

		existing_reserved_qty_item1 = get_reserved_qty("_Test Item")
		existing_reserved_qty_item2 = get_reserved_qty("_Test Item Home Desktop 100")

		so = make_sales_order(item_code="_Test Product Bundle Item")

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 50)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2 + 20)

		dn = create_dn_against_so(so.name, 15)

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2)

		dn.cancel()
		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 50)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2 + 20)

	def test_update_child_adding_new_item(self):
		so = make_sales_order(item_code="_Test Item", qty=4)
		create_dn_against_so(so.name, 4)
		make_sales_invoice(so.name)

		prev_total = so.get("base_total")
		prev_total_in_words = so.get("base_in_words")

		# get reserved qty before update items
		reserved_qty_for_second_item = get_reserved_qty("_Test Item 2")

		first_item_of_so = so.get("items")[0]
		trans_item = json.dumps(
			[
				{
					"item_code": first_item_of_so.item_code,
					"rate": first_item_of_so.rate,
					"qty": first_item_of_so.qty,
					"docname": first_item_of_so.name,
				},
				{"item_code": "_Test Item 2", "rate": 200, "qty": 7},
			]
		)
		update_child_qty_rate("Sales Order", trans_item, so.name)

		so.reload()
		self.assertEqual(so.get("items")[-1].item_code, "_Test Item 2")
		self.assertEqual(so.get("items")[-1].rate, 200)
		self.assertEqual(so.get("items")[-1].qty, 7)
		self.assertEqual(so.get("items")[-1].amount, 1400)

		# reserved qty should increase after adding row
		self.assertEqual(get_reserved_qty("_Test Item 2"), reserved_qty_for_second_item + 7)

		self.assertEqual(so.status, "To Deliver and Bill")

		updated_total = so.get("base_total")
		updated_total_in_words = so.get("base_in_words")

		self.assertEqual(updated_total, prev_total + 1400)
		self.assertNotEqual(updated_total_in_words, prev_total_in_words)

	def test_update_child_removing_item(self):
		so = make_sales_order(**{"item_list": [{"item_code": "_Test Item", "qty": 5, "rate": 1000}]})
		create_dn_against_so(so.name, 2)
		make_sales_invoice(so.name)

		# get reserved qty before update items
		reserved_qty_for_second_item = get_reserved_qty("_Test Item 2")

		# add an item so as to try removing items
		trans_item = json.dumps(
			[
				{"item_code": "_Test Item", "qty": 5, "rate": 1000, "docname": so.get("items")[0].name},
				{"item_code": "_Test Item 2", "qty": 2, "rate": 500},
			]
		)
		update_child_qty_rate("Sales Order", trans_item, so.name)
		so.reload()
		self.assertEqual(len(so.get("items")), 2)

		# reserved qty should increase after adding row
		self.assertEqual(get_reserved_qty("_Test Item 2"), reserved_qty_for_second_item + 2)

		# check if delivered items can be removed
		trans_item = json.dumps(
			[{"item_code": "_Test Item 2", "qty": 2, "rate": 500, "docname": so.get("items")[1].name}]
		)
		self.assertRaises(frappe.ValidationError, update_child_qty_rate, "Sales Order", trans_item, so.name)

		# remove last added item
		trans_item = json.dumps(
			[{"item_code": "_Test Item", "qty": 5, "rate": 1000, "docname": so.get("items")[0].name}]
		)
		update_child_qty_rate("Sales Order", trans_item, so.name)

		so.reload()
		self.assertEqual(len(so.get("items")), 1)

		# reserved qty should decrease (back to initial) after deleting row
		self.assertEqual(get_reserved_qty("_Test Item 2"), reserved_qty_for_second_item)

		self.assertEqual(so.status, "To Deliver and Bill")

	def test_update_child(self):
		so = make_sales_order(item_code="_Test Item", qty=4)
		create_dn_against_so(so.name, 4)
		make_sales_invoice(so.name)

		existing_reserved_qty = get_reserved_qty()

		trans_item = json.dumps(
			[{"item_code": "_Test Item", "rate": 200, "qty": 7, "docname": so.items[0].name}]
		)
		update_child_qty_rate("Sales Order", trans_item, so.name)

		so.reload()
		self.assertEqual(so.get("items")[0].rate, 200)
		self.assertEqual(so.get("items")[0].qty, 7)
		self.assertEqual(so.get("items")[0].amount, 1400)
		self.assertEqual(so.status, "To Deliver and Bill")

		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 3)

		trans_item = json.dumps(
			[{"item_code": "_Test Item", "rate": 200, "qty": 2, "docname": so.items[0].name}]
		)
		self.assertRaises(frappe.ValidationError, update_child_qty_rate, "Sales Order", trans_item, so.name)

	def test_update_child_with_precision(self):
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter
		from frappe.model.meta import get_field_precision

		precision = get_field_precision(frappe.get_meta("Sales Order Item").get_field("rate"))

		make_property_setter("Sales Order Item", "rate", "precision", 7, "Currency")
		so = make_sales_order(item_code="_Test Item", qty=4, rate=200.34664)

		trans_item = json.dumps(
			[{"item_code": "_Test Item", "rate": 200.34669, "qty": 4, "docname": so.items[0].name}]
		)
		update_child_qty_rate("Sales Order", trans_item, so.name)

		so.reload()
		self.assertEqual(so.items[0].rate, 200.34669)
		make_property_setter("Sales Order Item", "rate", "precision", precision, "Currency")

	def test_update_child_perm(self):
		so = make_sales_order(item_code="_Test Item", qty=4)

		test_user = create_user("test_so_child_perms@example.com", "Accounts User")
		frappe.set_user(test_user.name)

		# update qty
		trans_item = json.dumps(
			[{"item_code": "_Test Item", "rate": 200, "qty": 7, "docname": so.items[0].name}]
		)
		self.assertRaises(frappe.ValidationError, update_child_qty_rate, "Sales Order", trans_item, so.name)

		# add new item
		trans_item = json.dumps([{"item_code": "_Test Item", "rate": 100, "qty": 2}])
		self.assertRaises(frappe.ValidationError, update_child_qty_rate, "Sales Order", trans_item, so.name)

	def test_update_child_qty_rate_with_workflow(self):
		from frappe.model.workflow import apply_workflow

		workflow = make_sales_order_workflow()
		so = make_sales_order(item_code="_Test Item", qty=1, rate=150, do_not_submit=1)
		apply_workflow(so, "Approve")

		user = "test@example.com"
		test_user = frappe.get_doc("User", user)
		test_user.add_roles("Sales User", "Test Junior Approver")
		frappe.set_user(user)

		# user shouldn't be able to edit since grand_total will become > 200 if qty is doubled
		trans_item = json.dumps(
			[{"item_code": "_Test Item", "rate": 150, "qty": 2, "docname": so.items[0].name}]
		)
		self.assertRaises(frappe.ValidationError, update_child_qty_rate, "Sales Order", trans_item, so.name)

		frappe.set_user("Administrator")
		user2 = "test2@example.com"
		test_user2 = frappe.get_doc("User", user2)
		test_user2.add_roles("Sales User", "Test Approver")
		frappe.set_user(user2)

		# Test Approver is allowed to edit with grand_total > 200
		update_child_qty_rate("Sales Order", trans_item, so.name)
		so.reload()
		self.assertEqual(so.items[0].qty, 2)

		frappe.set_user("Administrator")
		test_user.remove_roles("Sales User", "Test Junior Approver", "Test Approver")
		test_user2.remove_roles("Sales User", "Test Junior Approver", "Test Approver")
		workflow.is_active = 0
		workflow.save()

	def test_material_request_for_product_bundle(self):
		# Create the Material Request from the sales order for the Packing Items
		# Check whether the material request has the correct packing item or not.
		if not frappe.db.exists("Item", "_Test Product Bundle Item New 1"):
			bundle_item = make_item("_Test Product Bundle Item New 1", {"is_stock_item": 0})
			bundle_item.append(
				"item_defaults", {"company": "_Test Company", "default_warehouse": "_Test Warehouse - _TC"}
			)
			bundle_item.save(ignore_permissions=True)

		make_item("_Packed Item New 2", {"is_stock_item": 1})
		make_product_bundle("_Test Product Bundle Item New 1", ["_Packed Item New 2"], 2)

		so = make_sales_order(
			item_code="_Test Product Bundle Item New 1",
		)

		mr = make_material_request(so.name)
		self.assertEqual(mr.items[0].item_code, "_Packed Item New 2")

	def test_bin_details_of_packed_item(self):
		# test Update Items with product bundle
		if not frappe.db.exists("Item", "_Test Product Bundle Item New"):
			bundle_item = make_item("_Test Product Bundle Item New", {"is_stock_item": 0})
			bundle_item.append(
				"item_defaults", {"company": "_Test Company", "default_warehouse": "_Test Warehouse - _TC"}
			)
			bundle_item.save(ignore_permissions=True)

		make_item("_Packed Item New 1", {"is_stock_item": 1})
		make_product_bundle("_Test Product Bundle Item New", ["_Packed Item New 1"], 2)

		so = make_sales_order(
			item_code="_Test Product Bundle Item New",
			warehouse="_Test Warehouse - _TC",
			transaction_date=add_days(nowdate(), -1),
			do_not_submit=1,
		)

		make_stock_entry(item="_Packed Item New 1", target="_Test Warehouse - _TC", qty=120, rate=100)

		bin_details = frappe.db.get_value(
			"Bin",
			{"item_code": "_Packed Item New 1", "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "projected_qty", "ordered_qty"],
			as_dict=1,
		)

		so.transaction_date = nowdate()
		so.save()

		packed_item = so.packed_items[0]
		self.assertEqual(flt(bin_details.actual_qty), flt(packed_item.actual_qty))
		self.assertEqual(flt(bin_details.projected_qty), flt(packed_item.projected_qty))
		self.assertEqual(flt(bin_details.ordered_qty), flt(packed_item.ordered_qty))

	def test_update_child_product_bundle(self):
		# test Update Items with product bundle
		if not frappe.db.exists("Item", "_Product Bundle Item"):
			bundle_item = make_item("_Product Bundle Item", {"is_stock_item": 0})
			bundle_item.append(
				"item_defaults", {"company": "_Test Company", "default_warehouse": "_Test Warehouse - _TC"}
			)
			bundle_item.save(ignore_permissions=True)

		make_item("_Packed Item", {"is_stock_item": 1})
		make_product_bundle("_Product Bundle Item", ["_Packed Item"], 2)

		so = make_sales_order(item_code="_Test Item", warehouse=None)

		# get reserved qty of packed item
		existing_reserved_qty = get_reserved_qty("_Packed Item")

		added_item = json.dumps([{"item_code": "_Product Bundle Item", "rate": 200, "qty": 2}])
		update_child_qty_rate("Sales Order", added_item, so.name)

		so.reload()
		self.assertEqual(so.packed_items[0].qty, 4)

		# reserved qty in packed item should increase after adding bundle item
		self.assertEqual(get_reserved_qty("_Packed Item"), existing_reserved_qty + 4)

		# test uom and conversion factor change
		update_uom_conv_factor = json.dumps(
			[
				{
					"item_code": so.get("items")[0].item_code,
					"rate": so.get("items")[0].rate,
					"qty": so.get("items")[0].qty,
					"uom": "_Test UOM 1",
					"conversion_factor": 2,
					"docname": so.get("items")[0].name,
				}
			]
		)
		update_child_qty_rate("Sales Order", update_uom_conv_factor, so.name)

		so.reload()
		self.assertEqual(so.packed_items[0].qty, 8)

		# reserved qty in packed item should increase after changing bundle item uom
		self.assertEqual(get_reserved_qty("_Packed Item"), existing_reserved_qty + 8)

	def test_update_child_with_tax_template(self):
		"""
		Test Action: Create a SO with one item having its tax account head already in the SO.
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

		so = make_sales_order(item_code=item, qty=1, do_not_save=1)

		so.append(
			"taxes",
			{
				"account_head": "_Test Account Excise Duty - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Excise Duty",
				"doctype": "Sales Taxes and Charges",
				"rate": 10,
			},
		)
		so.insert()
		so.submit()

		self.assertEqual(so.taxes[0].tax_amount, 10)
		self.assertEqual(so.taxes[0].total, 110)

		old_stock_settings_value = frappe.db.get_single_value("Stock Settings", "default_warehouse")
		frappe.db.set_single_value("Stock Settings", "default_warehouse", "_Test Warehouse - _TC")

		items = json.dumps(
			[
				{"item_code": item, "rate": 100, "qty": 1, "docname": so.items[0].name},
				{
					"item_code": item,
					"rate": 200,
					"qty": 1,
				},  # added item whose tax account head already exists in PO
				{
					"item_code": new_item_with_tax.name,
					"rate": 100,
					"qty": 1,
				},  # added item whose tax account head  is missing in PO
			]
		)
		update_child_qty_rate("Sales Order", items, so.name)

		so.reload()
		self.assertEqual(so.taxes[0].tax_amount, 40)
		self.assertEqual(so.taxes[0].total, 440)
		self.assertEqual(so.taxes[1].account_head, "_Test Account Service Tax - _TC")
		self.assertEqual(so.taxes[1].tax_amount, 40)
		self.assertEqual(so.taxes[1].total, 480)

		# teardown
		frappe.db.sql(
			"""UPDATE `tabItem Tax` set valid_from = NULL
			where parent = %(item)s and item_tax_template = %(tax)s""",
			{"item": item, "tax": tax_template},
		)
		so.cancel()
		so.delete()
		new_item_with_tax.delete()
		frappe.get_doc("Item Tax Template", "Test Update Items Template - _TC").delete()
		frappe.db.set_single_value("Stock Settings", "default_warehouse", old_stock_settings_value)

	def test_warehouse_user(self):
		test_user = create_user("test_so_warehouse_user@example.com", "Sales User", "Stock User")

		test_user_2 = frappe.get_doc("User", "test2@example.com")
		test_user_2.add_roles("Sales User", "Stock User")
		test_user_2.remove_roles("Sales Manager")

		frappe.permissions.add_user_permission("Warehouse", "_Test Warehouse 1 - _TC", test_user.name)
		frappe.permissions.add_user_permission("Warehouse", "_Test Warehouse 2 - _TC1", test_user_2.name)
		frappe.permissions.add_user_permission("Company", "_Test Company 1", test_user_2.name)

		frappe.set_user(test_user.name)

		so = make_sales_order(
			company="_Test Company 1",
			customer="_Test Customer 1",
			warehouse="_Test Warehouse 2 - _TC1",
			do_not_save=True,
		)
		so.conversion_rate = 0.02
		so.plc_conversion_rate = 0.02
		self.assertRaises(frappe.PermissionError, so.insert)

		frappe.set_user(test_user_2.name)
		so.insert()

		frappe.set_user("Administrator")
		frappe.permissions.remove_user_permission("Warehouse", "_Test Warehouse 1 - _TC", test_user.name)
		frappe.permissions.remove_user_permission("Warehouse", "_Test Warehouse 2 - _TC1", test_user_2.name)
		frappe.permissions.remove_user_permission("Company", "_Test Company 1", test_user_2.name)

	def test_block_delivery_note_against_cancelled_sales_order(self):
		so = make_sales_order()

		dn = make_delivery_note(so.name)
		dn.insert()

		so.cancel()

		dn.load_from_db()

		self.assertRaises(frappe.CancelledLinkError, dn.submit)

	def test_service_type_product_bundle(self):
		make_item("_Test Service Product Bundle", {"is_stock_item": 0})
		make_item("_Test Service Product Bundle Item 1", {"is_stock_item": 0})
		make_item("_Test Service Product Bundle Item 2", {"is_stock_item": 0})

		make_product_bundle(
			"_Test Service Product Bundle",
			["_Test Service Product Bundle Item 1", "_Test Service Product Bundle Item 2"],
		)

		so = make_sales_order(item_code="_Test Service Product Bundle", warehouse=None)

		self.assertTrue("_Test Service Product Bundle Item 1" in [d.item_code for d in so.packed_items])
		self.assertTrue("_Test Service Product Bundle Item 2" in [d.item_code for d in so.packed_items])

	def test_mix_type_product_bundle(self):
		make_item("_Test Mix Product Bundle", {"is_stock_item": 0})
		make_item("_Test Mix Product Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Mix Product Bundle Item 2", {"is_stock_item": 0})

		make_product_bundle(
			"_Test Mix Product Bundle",
			["_Test Mix Product Bundle Item 1", "_Test Mix Product Bundle Item 2"],
		)

		self.assertRaises(
			WarehouseRequired, make_sales_order, item_code="_Test Mix Product Bundle", warehouse=""
		)

	def test_auto_insert_price(self):
		make_item("_Test Item for Auto Price List", {"is_stock_item": 0})
		make_item("_Test Item for Auto Price List with Discount Percentage", {"is_stock_item": 0})
		frappe.db.set_single_value(
			"Stock Settings",
			{
				"auto_insert_price_list_rate_if_missing": 1,
				"update_price_list_based_on": "Price List Rate",
			},
		)

		item_price = frappe.db.get_value(
			"Item Price", {"price_list": "_Test Price List", "item_code": "_Test Item for Auto Price List"}
		)
		if item_price:
			frappe.delete_doc("Item Price", item_price)

		make_sales_order(
			item_code="_Test Item for Auto Price List", selling_price_list="_Test Price List", rate=100
		)

		# ensure price gets inserted based on rate if price list rate is not defined by user
		self.assertEqual(
			frappe.db.get_value(
				"Item Price",
				{"price_list": "_Test Price List", "item_code": "_Test Item for Auto Price List"},
				"price_list_rate",
			),
			100,
		)

		# ensure price gets insterted based on user-defined *Price List Rate*
		# if update_price_list_based_on is set to Price List Rate
		make_sales_order(
			item_code="_Test Item for Auto Price List with Discount Percentage",
			selling_price_list="_Test Price List",
			price_list_rate=200,
			discount_percentage=20,
		)

		item_price = frappe.db.get_value(
			"Item Price",
			{
				"price_list": "_Test Price List",
				"item_code": "_Test Item for Auto Price List with Discount Percentage",
			},
			("name", "price_list_rate"),
			as_dict=True,
		)

		self.assertEqual(item_price.price_list_rate, 200)
		frappe.delete_doc("Item Price", item_price.name)

		frappe.db.set_single_value("Stock Settings", "update_price_list_based_on", "Rate")

		# ensure price gets insterted based on user-defined *Rate*
		# if update_price_list_based_on is set to Rate
		make_sales_order(
			item_code="_Test Item for Auto Price List with Discount Percentage",
			selling_price_list="_Test Price List",
			price_list_rate=200,
			discount_percentage=20,
		)

		item_price = frappe.db.get_value(
			"Item Price",
			{
				"price_list": "_Test Price List",
				"item_code": "_Test Item for Auto Price List with Discount Percentage",
			},
			("name", "price_list_rate"),
			as_dict=True,
		)

		self.assertEqual(item_price.price_list_rate, 160)
		frappe.delete_doc("Item Price", item_price.name)

		# do not update price list
		frappe.db.set_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing", 0)

		item_price = frappe.db.get_value(
			"Item Price", {"price_list": "_Test Price List", "item_code": "_Test Item for Auto Price List"}
		)
		if item_price:
			frappe.delete_doc("Item Price", item_price)

		make_sales_order(
			item_code="_Test Item for Auto Price List", selling_price_list="_Test Price List", rate=100
		)

		self.assertEqual(
			frappe.db.get_value(
				"Item Price",
				{"price_list": "_Test Price List", "item_code": "_Test Item for Auto Price List"},
				"price_list_rate",
			),
			None,
		)

		frappe.db.set_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing", 1)

	def test_update_existing_item_price(self):
		item_code = "_Test Item for Price List Updation"
		price_list = "_Test Price List"

		make_item(item_code, {"is_stock_item": 0})

		frappe.db.set_single_value(
			"Stock Settings",
			{
				"auto_insert_price_list_rate_if_missing": 1,
				"update_existing_price_list_rate": 1,
				"update_price_list_based_on": "Rate",
			},
		)

		# setup: price creation
		make_sales_order(item_code=item_code, selling_price_list=price_list, rate=100)

		# test price updation based on Rate
		make_sales_order(item_code=item_code, selling_price_list=price_list, rate=90)

		self.assertEqual(
			frappe.db.get_value(
				"Item Price",
				{"price_list": price_list, "item_code": item_code},
				"price_list_rate",
			),
			90,
		)

		frappe.db.set_single_value(
			"Stock Settings",
			{
				"update_price_list_based_on": "Price List Rate",
			},
		)

		# test price updation based on Price List Rate
		make_sales_order(
			item_code=item_code,
			selling_price_list=price_list,
			price_list_rate=200,
			discount_percentage=20,
		)

		self.assertEqual(
			frappe.db.get_value(
				"Item Price",
				{"price_list": price_list, "item_code": item_code},
				"price_list_rate",
			),
			200,
		)

		# reset `update_existing_price_list_rate` to 0
		frappe.db.set_single_value("Stock Settings", "update_existing_price_list_rate", 0)

	def test_drop_shipping(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status
		from erpnext.selling.doctype.sales_order.sales_order import (
			make_purchase_order_for_default_supplier,
		)
		from erpnext.selling.doctype.sales_order.sales_order import update_status as so_update_status

		# make items
		po_item = make_item("_Test Item for Drop Shipping", {"is_stock_item": 1, "delivered_by_supplier": 1})
		dn_item = make_item("_Test Regular Item", {"is_stock_item": 1})

		so_items = [
			{
				"item_code": po_item.item_code,
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			},
			{
				"item_code": dn_item.item_code,
				"warehouse": "_Test Warehouse - _TC",
				"qty": 2,
				"rate": 300,
				"conversion_factor": 1.0,
			},
		]

		if frappe.db.get_value("Item", "_Test Regular Item", "is_stock_item") == 1:
			make_stock_entry(item="_Test Regular Item", target="_Test Warehouse - _TC", qty=2, rate=100)

		# create so, po and dn
		so = make_sales_order(item_list=so_items, do_not_submit=True)
		so.submit()

		po = make_purchase_order_for_default_supplier(so.name, selected_items=[so_items[0]])[0]
		po.submit()

		dn = create_dn_against_so(so.name, delivered_qty=2)

		self.assertEqual(so.customer, po.customer)
		self.assertEqual(po.items[0].sales_order, so.name)
		self.assertEqual(po.items[0].item_code, po_item.item_code)
		self.assertEqual(dn.items[0].item_code, dn_item.item_code)
		# test po_item length
		self.assertEqual(len(po.items), 1)

		# test ordered_qty and reserved_qty for drop ship item
		bin_po_item = frappe.get_all(
			"Bin",
			filters={"item_code": po_item.item_code, "warehouse": "_Test Warehouse - _TC"},
			fields=["ordered_qty", "reserved_qty"],
		)

		ordered_qty = bin_po_item[0].ordered_qty if bin_po_item else 0.0
		reserved_qty = bin_po_item[0].reserved_qty if bin_po_item else 0.0

		# drop ship PO should not impact bin, test the same
		self.assertEqual(abs(flt(ordered_qty)), 0)
		self.assertEqual(abs(flt(reserved_qty)), 0)

		# test per_delivered status
		update_status("Delivered", po.name)
		self.assertEqual(flt(frappe.db.get_value("Sales Order", so.name, "per_delivered"), 2), 100.00)
		po.load_from_db()

		# test after closing so
		so.db_set("status", "Closed")
		so.update_reserved_qty()

		# test ordered_qty and reserved_qty for drop ship item after closing so
		bin_po_item = frappe.get_all(
			"Bin",
			filters={"item_code": po_item.item_code, "warehouse": "_Test Warehouse - _TC"},
			fields=["ordered_qty", "reserved_qty"],
		)

		ordered_qty = bin_po_item[0].ordered_qty if bin_po_item else 0.0
		reserved_qty = bin_po_item[0].reserved_qty if bin_po_item else 0.0

		self.assertEqual(abs(flt(ordered_qty)), 0)
		self.assertEqual(abs(flt(reserved_qty)), 0)

		# teardown
		so_update_status("Draft", so.name)
		dn.load_from_db()
		dn.cancel()
		po.cancel()
		so.load_from_db()
		so.cancel()

	def test_drop_shipping_partial_order(self):
		from erpnext.selling.doctype.sales_order.sales_order import (
			make_purchase_order_for_default_supplier,
		)
		from erpnext.selling.doctype.sales_order.sales_order import update_status as so_update_status

		# make items
		po_item1 = make_item(
			"_Test Item for Drop Shipping 1", {"is_stock_item": 1, "delivered_by_supplier": 1}
		)
		po_item2 = make_item(
			"_Test Item for Drop Shipping 2", {"is_stock_item": 1, "delivered_by_supplier": 1}
		)

		so_items = [
			{
				"item_code": po_item1.item_code,
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			},
			{
				"item_code": po_item2.item_code,
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			},
		]

		# create so and po
		so = make_sales_order(item_list=so_items, do_not_submit=True)
		so.submit()

		# create po for only one item
		po1 = make_purchase_order_for_default_supplier(so.name, selected_items=[so_items[0]])[0]
		po1.submit()

		self.assertEqual(so.customer, po1.customer)
		self.assertEqual(po1.items[0].sales_order, so.name)
		self.assertEqual(po1.items[0].item_code, po_item1.item_code)
		# test po item length
		self.assertEqual(len(po1.items), 1)

		# create po for remaining item
		po2 = make_purchase_order_for_default_supplier(so.name, selected_items=[so_items[1]])[0]
		po2.submit()

		# teardown
		so_update_status("Draft", so.name)

		po1.cancel()
		po2.cancel()
		so.load_from_db()
		so.cancel()

	def test_drop_shipping_full_for_default_suppliers(self):
		"""Test if multiple POs are generated in one go against different default suppliers."""
		from erpnext.selling.doctype.sales_order.sales_order import (
			make_purchase_order_for_default_supplier,
		)

		if not frappe.db.exists("Item", "_Test Item for Drop Shipping 1"):
			make_item("_Test Item for Drop Shipping 1", {"is_stock_item": 1, "delivered_by_supplier": 1})

		if not frappe.db.exists("Item", "_Test Item for Drop Shipping 2"):
			make_item("_Test Item for Drop Shipping 2", {"is_stock_item": 1, "delivered_by_supplier": 1})

		so_items = [
			{
				"item_code": "_Test Item for Drop Shipping 1",
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			},
			{
				"item_code": "_Test Item for Drop Shipping 2",
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier 1",
			},
		]

		# create so and po
		so = make_sales_order(item_list=so_items, do_not_submit=True)
		so.submit()

		purchase_orders = make_purchase_order_for_default_supplier(so.name, selected_items=so_items)

		self.assertEqual(len(purchase_orders), 2)
		self.assertEqual(purchase_orders[0].supplier, "_Test Supplier")
		self.assertEqual(purchase_orders[1].supplier, "_Test Supplier 1")

	def test_product_bundles_in_so_are_replaced_with_bundle_items_in_po(self):
		"""
		Tests if the the Product Bundles in the Items table of Sales Orders are replaced with
		their child items(from the Packed Items table) on creating a Purchase Order from it.
		"""
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order

		product_bundle = make_item("_Test Product Bundle", {"is_stock_item": 0})
		make_item("_Test Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Bundle Item 2", {"is_stock_item": 1})

		make_product_bundle("_Test Product Bundle", ["_Test Bundle Item 1", "_Test Bundle Item 2"])

		so_items = [
			{
				"item_code": product_bundle.item_code,
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			}
		]

		so = make_sales_order(item_list=so_items)

		purchase_order = make_purchase_order(so.name, selected_items=so_items)

		self.assertEqual(purchase_order.items[0].item_code, "_Test Bundle Item 1")
		self.assertEqual(purchase_order.items[1].item_code, "_Test Bundle Item 2")

	def test_purchase_order_updates_packed_item_ordered_qty(self):
		"""
		Tests if the packed item's `ordered_qty` is updated with the quantity of the Purchase Order
		"""
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order

		product_bundle = make_item("_Test Product Bundle", {"is_stock_item": 0})
		make_item("_Test Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Bundle Item 2", {"is_stock_item": 1})

		make_product_bundle("_Test Product Bundle", ["_Test Bundle Item 1", "_Test Bundle Item 2"])

		so_items = [
			{
				"item_code": product_bundle.item_code,
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			}
		]

		so = make_sales_order(item_list=so_items)

		purchase_order = make_purchase_order(so.name, selected_items=so_items)
		purchase_order.supplier = "_Test Supplier"
		purchase_order.set_warehouse = "_Test Warehouse - _TC"
		purchase_order.save()
		purchase_order.submit()

		so.reload()
		self.assertEqual(so.packed_items[0].ordered_qty, 2)
		self.assertEqual(so.packed_items[1].ordered_qty, 2)

	def test_reserved_qty_for_closing_so(self):
		bin = frappe.get_all(
			"Bin",
			filters={"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			fields=["reserved_qty"],
		)

		existing_reserved_qty = bin[0].reserved_qty if bin else 0.0

		so = make_sales_order(item_code="_Test Item", qty=1)

		self.assertEqual(
			get_reserved_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"),
			existing_reserved_qty + 1,
		)

		so.update_status("Closed")

		self.assertEqual(
			get_reserved_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"),
			existing_reserved_qty,
		)

	def test_create_so_with_margin(self):
		so = make_sales_order(item_code="_Test Item", qty=1, do_not_submit=True)
		so.items[0].price_list_rate = price_list_rate = 100
		so.items[0].margin_type = "Percentage"
		so.items[0].margin_rate_or_amount = 25
		so.save()

		new_so = frappe.copy_doc(so)
		new_so.save(ignore_permissions=True)

		self.assertEqual(new_so.get("items")[0].rate, flt((price_list_rate * 25) / 100 + price_list_rate))
		new_so.items[0].margin_rate_or_amount = 25
		new_so.payment_schedule = []
		new_so.save()
		new_so.submit()

		self.assertEqual(new_so.get("items")[0].rate, flt((price_list_rate * 25) / 100 + price_list_rate))

	def test_terms_auto_added(self):
		so = make_sales_order(do_not_save=1)

		self.assertFalse(so.get("payment_schedule"))

		so.insert()

		self.assertTrue(so.get("payment_schedule"))

	def test_terms_not_copied(self):
		so = make_sales_order()
		self.assertTrue(so.get("payment_schedule"))

		si = make_sales_invoice(so.name)
		self.assertFalse(si.get("payment_schedule"))

	def test_terms_copied(self):
		so = make_sales_order(do_not_copy=1, do_not_save=1)
		so.payment_terms_template = "_Test Payment Term Template"
		so.insert()
		so.submit()
		self.assertTrue(so.get("payment_schedule"))

		si = make_sales_invoice(so.name)
		si.insert()
		self.assertTrue(si.get("payment_schedule"))

	def test_make_work_order(self):
		from erpnext.selling.doctype.sales_order.sales_order import get_work_order_items

		# Make a new Sales Order
		so = make_sales_order(
			**{
				"item_list": [
					{"item_code": "_Test FG Item", "qty": 10, "rate": 100},
					{"item_code": "_Test FG Item", "qty": 20, "rate": 200},
				]
			}
		)

		# Raise Work Orders
		po_items = []
		so_item_name = {}
		for item in get_work_order_items(so.name):
			po_items.append(
				{
					"warehouse": item.get("warehouse"),
					"item_code": item.get("item_code"),
					"pending_qty": item.get("pending_qty"),
					"sales_order_item": item.get("sales_order_item"),
					"bom": item.get("bom"),
					"description": item.get("description"),
				}
			)
			so_item_name[item.get("sales_order_item")] = item.get("pending_qty")
		make_work_orders(json.dumps({"items": po_items}), so.name, so.company)

		# Check if Work Orders were raised
		for item in so_item_name:
			wo_qty = frappe.db.sql(
				"select sum(qty) from `tabWork Order` where sales_order=%s and sales_order_item=%s",
				(so.name, item),
			)
			self.assertEqual(wo_qty[0][0], so_item_name.get(item))

	def test_advance_payment_entry_unlink_against_sales_order(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		frappe.db.set_single_value("Accounts Settings", "unlink_advance_payment_on_cancelation_of_order", 0)

		so = make_sales_order()

		pe = get_payment_entry("Sales Order", so.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = so.currency
		pe.paid_to_account_currency = so.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = so.grand_total
		pe.save(ignore_permissions=True)
		pe.submit()

		so_doc = frappe.get_doc("Sales Order", so.name)

		self.assertRaises(frappe.LinkExistsError, so_doc.cancel)

	@change_settings("Accounts Settings", {"unlink_advance_payment_on_cancelation_of_order": 1})
	def test_advance_paid_upon_payment_cancellation(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		so = make_sales_order()

		pe = get_payment_entry("Sales Order", so.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = so.currency
		pe.paid_to_account_currency = so.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = so.grand_total
		pe.save(ignore_permissions=True)
		pe.submit()
		so.reload()

		self.assertEqual(so.advance_paid, so.base_grand_total)

		# cancel advance payment
		pe.reload()
		pe.cancel()

		so.reload()
		self.assertEqual(so.advance_paid, 0)

	def test_cancel_sales_order_after_cancel_payment_entry(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		# make a sales order
		so = make_sales_order()

		# disable unlinking of payment entry
		frappe.db.set_single_value("Accounts Settings", "unlink_advance_payment_on_cancelation_of_order", 0)

		# create a payment entry against sales order
		pe = get_payment_entry("Sales Order", so.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = so.currency
		pe.paid_to_account_currency = so.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = so.grand_total
		pe.save(ignore_permissions=True)
		pe.submit()

		# Cancel payment entry
		po_doc = frappe.get_doc("Payment Entry", pe.name)
		po_doc.cancel()

		# Cancel sales order
		try:
			so_doc = frappe.get_doc("Sales Order", so.name)
			so_doc.cancel()
		except Exception:
			self.fail("Can not cancel sales order with linked cancelled payment entry")

	def test_work_order_pop_up_from_sales_order(self):
		"Test `get_work_order_items` in Sales Order picks the right BOM for items to manufacture."

		from erpnext.controllers.item_variant import create_variant
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		from erpnext.selling.doctype.sales_order.sales_order import get_work_order_items

		make_item(  # template item
			"Test-WO-Tshirt",
			{
				"has_variant": 1,
				"variant_based_on": "Item Attribute",
				"attributes": [{"attribute": "Test Colour"}],
			},
		)
		make_item("Test-RM-Cotton")  # RM for BOM

		for colour in (
			"Red",
			"Green",
		):
			variant = create_variant("Test-WO-Tshirt", {"Test Colour": colour})
			variant.save()

		template_bom = make_bom(item="Test-WO-Tshirt", rate=100, raw_materials=["Test-RM-Cotton"])
		red_var_bom = make_bom(item="Test-WO-Tshirt-R", rate=100, raw_materials=["Test-RM-Cotton"])

		so = make_sales_order(
			**{
				"item_list": [
					{
						"item_code": "Test-WO-Tshirt-R",
						"qty": 1,
						"rate": 1000,
						"warehouse": "_Test Warehouse - _TC",
					},
					{
						"item_code": "Test-WO-Tshirt-G",
						"qty": 1,
						"rate": 1000,
						"warehouse": "_Test Warehouse - _TC",
					},
				]
			}
		)
		wo_items = get_work_order_items(so.name)

		self.assertEqual(wo_items[0].get("item_code"), "Test-WO-Tshirt-R")
		self.assertEqual(wo_items[0].get("bom"), red_var_bom.name)

		# Must pick Template Item BOM for Test-WO-Tshirt-G as it has no BOM
		self.assertEqual(wo_items[1].get("item_code"), "Test-WO-Tshirt-G")
		self.assertEqual(wo_items[1].get("bom"), template_bom.name)

	def test_request_for_raw_materials(self):
		from erpnext.selling.doctype.sales_order.sales_order import get_work_order_items

		item = make_item(
			"_Test Finished Item",
			{
				"is_stock_item": 1,
				"maintain_stock": 1,
				"valuation_rate": 500,
				"item_defaults": [{"default_warehouse": "_Test Warehouse - _TC", "company": "_Test Company"}],
			},
		)
		make_item(
			"_Test Raw Item A",
			{
				"maintain_stock": 1,
				"valuation_rate": 100,
				"item_defaults": [{"default_warehouse": "_Test Warehouse - _TC", "company": "_Test Company"}],
			},
		)
		make_item(
			"_Test Raw Item B",
			{
				"maintain_stock": 1,
				"valuation_rate": 200,
				"item_defaults": [{"default_warehouse": "_Test Warehouse - _TC", "company": "_Test Company"}],
			},
		)
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

		make_bom(item=item.item_code, rate=1000, raw_materials=["_Test Raw Item A", "_Test Raw Item B"])

		so = make_sales_order(**{"item_list": [{"item_code": item.item_code, "qty": 1, "rate": 1000}]})
		so.submit()
		mr_dict = frappe._dict()
		items = get_work_order_items(so.name, 1)
		mr_dict["items"] = items
		mr_dict["include_exploded_items"] = 0
		mr_dict["ignore_existing_ordered_qty"] = 1
		make_raw_material_request(mr_dict, so.company, so.name)
		mr = frappe.db.sql(
			"""select name from `tabMaterial Request` ORDER BY creation DESC LIMIT 1""", as_dict=1
		)[0]
		mr_doc = frappe.get_doc("Material Request", mr.get("name"))
		self.assertEqual(mr_doc.items[0].sales_order, so.name)

	def test_so_optional_blanket_order(self):
		"""
		Expected result: Blanket order Ordered Quantity should only be affected on Sales Order with against_blanket_order = 1.
		Second Sales Order should not add on to Blanket Orders Ordered Quantity.
		"""

		_make_blanket_order(blanket_order_type="Selling", quantity=10, rate=10)

		so = make_sales_order(item_code="_Test Item", qty=5, against_blanket_order=1)
		so_doc = frappe.get_doc("Sales Order", so.get("name"))
		# To test if the SO has a Blanket Order
		self.assertTrue(so_doc.items[0].blanket_order)

		so = make_sales_order(item_code="_Test Item", qty=5, against_blanket_order=0)
		so_doc = frappe.get_doc("Sales Order", so.get("name"))
		# To test if the SO does NOT have a Blanket Order
		self.assertEqual(so_doc.items[0].blanket_order, None)

	def test_so_cancellation_when_si_drafted(self):
		"""
		Test to check if Sales Order gets cancelled if Sales Invoice is in Draft state
		Expected result: sales order should not get cancelled
		"""
		so = make_sales_order()
		so.submit()
		si = make_sales_invoice(so.name)
		si.save()

		self.assertRaises(frappe.ValidationError, so.cancel)

	def test_so_cancellation_after_si_submission(self):
		"""
		Test to check if Sales Order gets cancelled when linked Sales Invoice has been Submitted
		Expected result: Sales Order should not get cancelled
		"""
		so = make_sales_order()
		so.submit()
		si = make_sales_invoice(so.name)
		si.submit()

		so.load_from_db()
		self.assertRaises(frappe.LinkExistsError, so.cancel)

	def test_so_cancellation_after_dn_submission(self):
		"""
		Test to check if Sales Order gets cancelled when linked Delivery Note has been Submitted
		Expected result: Sales Order should not get cancelled
		"""
		so = make_sales_order()
		so.submit()
		dn = make_delivery_note(so.name)
		dn.submit()

		so.load_from_db()
		self.assertRaises(frappe.LinkExistsError, so.cancel)

	def test_so_cancellation_after_maintenance_schedule_submission(self):
		"""
		Expected result: Sales Order should not get cancelled
		"""
		so = make_sales_order()
		so.submit()
		ms = make_maintenance_schedule()
		ms.items[0].sales_order = so.name
		ms.submit()

		so.load_from_db()
		self.assertRaises(frappe.LinkExistsError, so.cancel)

	def test_so_cancellation_after_maintenance_visit_submission(self):
		"""
		Expected result: Sales Order should not get cancelled
		"""
		so = make_sales_order()
		so.submit()
		mv = make_maintenance_visit()
		mv.purposes[0].prevdoc_doctype = "Sales Order"
		mv.purposes[0].prevdoc_docname = so.name
		mv.submit()

		so.load_from_db()
		self.assertRaises(frappe.LinkExistsError, so.cancel)

	def test_so_cancellation_after_work_order_submission(self):
		"""
		Expected result: Sales Order should not get cancelled
		"""
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record

		so = make_sales_order(item_code="_Test FG Item", qty=10)
		so.submit()
		make_wo_order_test_record(sales_order=so.name)

		so.load_from_db()
		self.assertRaises(frappe.LinkExistsError, so.cancel)

	def test_payment_terms_are_fetched_when_creating_sales_invoice(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_payment_terms_template,
		)
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		automatically_fetch_payment_terms()

		so = make_sales_order(uom="Nos", do_not_save=1)
		create_payment_terms_template()
		so.payment_terms_template = "Test Receivable Template"
		so.submit()

		si = create_sales_invoice(qty=10, do_not_save=1)
		si.items[0].sales_order = so.name
		si.items[0].so_detail = so.items[0].name
		si.insert()

		self.assertEqual(so.payment_terms_template, si.payment_terms_template)
		compare_payment_schedules(self, so, si)

		automatically_fetch_payment_terms(enable=0)

	def test_zero_amount_sales_order_billing_status(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		so = make_sales_order(uom="Nos", do_not_save=1)
		so.items[0].rate = 0
		so.save()
		so.submit()

		self.assertEqual(so.net_total, 0)
		self.assertEqual(so.billing_status, "Not Billed")

		si = create_sales_invoice(qty=10, do_not_save=1)
		si.price_list = "_Test Price List"
		si.items[0].rate = 0
		si.items[0].price_list_rate = 0
		si.items[0].sales_order = so.name
		si.items[0].so_detail = so.items[0].name
		si.save()
		si.submit()

		self.assertEqual(si.net_total, 0)
		so.load_from_db()
		self.assertEqual(so.billing_status, "Fully Billed")

	def test_so_billing_status_with_crnote_against_sales_return(self):
		"""
		| Step | Document creation                    |                               |
		|------+--------------------------------------+-------------------------------|
		|    1 | SO -> DN -> SI                       | SO Fully Billed and Completed |
		|    2 | DN -> Sales Return(Partial)          | SO 50% Delivered, 100% billed |
		|    3 | Sales Return(Partial) -> Credit Note | SO 50% Delivered, 50% billed  |

		"""
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		so = make_sales_order(uom="Nos", do_not_save=1)
		so.save()
		so.submit()

		self.assertEqual(so.billing_status, "Not Billed")

		dn1 = make_delivery_note(so.name)
		dn1.taxes_and_charges = ""
		dn1.taxes.clear()
		dn1.save().submit()

		si = create_sales_invoice(qty=10, do_not_save=1)
		si.items[0].sales_order = so.name
		si.items[0].so_detail = so.items[0].name
		si.items[0].delivery_note = dn1.name
		si.items[0].dn_detail = dn1.items[0].name
		si.save()
		si.submit()

		so.reload()
		self.assertEqual(so.billing_status, "Fully Billed")
		self.assertEqual(so.status, "Completed")

		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		dn1.reload()
		dn_ret = create_delivery_note(is_return=1, return_against=dn1.name, qty=-5, do_not_submit=True)
		dn_ret.items[0].against_sales_order = so.name
		dn_ret.items[0].so_detail = so.items[0].name
		dn_ret.submit()

		so.reload()
		self.assertEqual(so.per_billed, 100)
		self.assertEqual(so.per_delivered, 50)

		cr_note = create_sales_invoice(is_return=1, qty=-1, do_not_submit=True)
		cr_note.items[0].qty = -5
		cr_note.items[0].sales_order = so.name
		cr_note.items[0].so_detail = so.items[0].name
		cr_note.items[0].delivery_note = dn_ret.name
		cr_note.items[0].dn_detail = dn_ret.items[0].name
		cr_note.update_billed_amount_in_sales_order = True
		cr_note.submit()

		so.reload()
		self.assertEqual(so.per_billed, 50)
		self.assertEqual(so.per_delivered, 50)

	def test_so_back_updated_from_wo_via_mr(self):
		"SO -> MR (Manufacture) -> WO. Test if WO Qty is updated in SO."
		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as make_se_from_wo,
		)
		from erpnext.stock.doctype.material_request.material_request import raise_work_orders

		so = make_sales_order(item_list=[{"item_code": "_Test FG Item", "qty": 2, "rate": 100}])

		mr = make_material_request(so.name)
		mr.material_request_type = "Manufacture"
		mr.schedule_date = today()
		mr.submit()

		# WO from MR
		wo_name = raise_work_orders(mr.name)[0]
		wo = frappe.get_doc("Work Order", wo_name)
		wo.wip_warehouse = "Work In Progress - _TC"
		wo.skip_transfer = True

		self.assertEqual(wo.sales_order, so.name)
		self.assertEqual(wo.sales_order_item, so.items[0].name)

		wo.submit()
		make_stock_entry(
			item_code="_Test Item",
			target="_Test Warehouse - _TC",
			qty=4,
			basic_rate=100,  # Stock RM
		)
		make_stock_entry(
			item_code="_Test Item Home Desktop 100",  # Stock RM
			target="_Test Warehouse - _TC",
			qty=4,
			basic_rate=100,
		)

		se = frappe.get_doc(make_se_from_wo(wo.name, "Manufacture", 2))
		se.submit()  # Finish WO

		mr.reload()
		wo.reload()
		so.reload()
		self.assertEqual(so.items[0].work_order_qty, wo.produced_qty)
		self.assertEqual(mr.status, "Manufactured")

	def test_sales_order_with_shipping_rule(self):
		from erpnext.accounts.doctype.shipping_rule.test_shipping_rule import create_shipping_rule

		shipping_rule = create_shipping_rule(
			shipping_rule_type="Selling", shipping_rule_name="Shipping Rule - Sales Invoice Test"
		)
		sales_order = make_sales_order(do_not_save=True)
		sales_order.shipping_rule = shipping_rule.name

		sales_order.items[0].qty = 1
		sales_order.save()
		self.assertEqual(sales_order.taxes[0].tax_amount, 50)

		sales_order.items[0].qty = 2
		sales_order.save()
		self.assertEqual(sales_order.taxes[0].tax_amount, 100)

		sales_order.items[0].qty = 3
		sales_order.save()
		self.assertEqual(sales_order.taxes[0].tax_amount, 200)

		sales_order.items[0].qty = 21
		sales_order.save()
		self.assertEqual(sales_order.taxes[0].tax_amount, 0)

	def test_sales_order_partial_advance_payment(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_payment_entry,
			get_payment_entry,
		)
		from erpnext.selling.doctype.customer.test_customer import get_customer_dict

		# Make a customer
		customer = get_customer_dict("QA Logistics")
		frappe.get_doc(customer).insert()

		# Make a Sales Order
		so = make_sales_order(
			customer="QA Logistics",
			item_list=[
				{"item_code": "_Test Item", "qty": 1, "rate": 200},
				{"item_code": "_Test Item 2", "qty": 1, "rate": 300},
			],
		)

		# Create a advance payment against that Sales Order
		pe = get_payment_entry("Sales Order", so.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = so.currency
		pe.paid_to_account_currency = so.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = so.grand_total
		pe.save(ignore_permissions=True)
		pe.submit()

		# Make standalone advance payment entry
		create_payment_entry(
			payment_type="Receive",
			party_type="Customer",
			party="QA Logistics",
			paid_from="Debtors - _TC",
			paid_to="_Test Bank - _TC",
			save=1,
			submit=1,
		)

		si = make_sales_invoice(so.name)

		item = si.get("items")[1]
		si.remove(item)

		si.allocate_advances_automatically = 1
		si.save()

		self.assertEqual(len(si.get("advances")), 1)
		self.assertEqual(si.get("advances")[0].allocated_amount, 200)
		self.assertEqual(si.get("advances")[0].reference_name, pe.name)

		si.submit()
		pe.load_from_db()

		self.assertEqual(pe.references[0].reference_name, so.name)
		self.assertEqual(pe.references[0].allocated_amount, 300)
		self.assertEqual(pe.references[1].reference_name, si.name)
		self.assertEqual(pe.references[1].allocated_amount, 200)

	def test_delivered_item_material_request(self):
		"SO -> MR (Manufacture) -> WO. Test if WO Qty is updated in SO."

		so = make_sales_order(
			item_list=[
				{"item_code": "_Test FG Item", "qty": 10, "rate": 100, "warehouse": "Work In Progress - _TC"}
			]
		)

		make_stock_entry(item_code="_Test FG Item", target="Work In Progress - _TC", qty=4, basic_rate=100)

		dn = make_delivery_note(so.name)
		dn.items[0].qty = 4
		dn.submit()

		so.load_from_db()
		self.assertEqual(so.items[0].delivered_qty, 4)

		mr = make_material_request(so.name)
		mr.material_request_type = "Purchase"
		mr.schedule_date = today()
		mr.save()

		self.assertEqual(mr.items[0].qty, 6)

	def test_packed_items_for_partial_sales_order(self):
		# test Update Items with product bundle
		for product_bundle in [
			"_Test Product Bundle Item Partial 1",
			"_Test Product Bundle Item Partial 2",
		]:
			if not frappe.db.exists("Item", product_bundle):
				bundle_item = make_item(product_bundle, {"is_stock_item": 0})
				bundle_item.append(
					"item_defaults",
					{"company": "_Test Company", "default_warehouse": "_Test Warehouse - _TC"},
				)
				bundle_item.save(ignore_permissions=True)

		for product_bundle in ["_Packed Item Partial 1", "_Packed Item Partial 2"]:
			if not frappe.db.exists("Item", product_bundle):
				make_item(product_bundle, {"is_stock_item": 1, "stock_uom": "Nos"})

			make_stock_entry(item=product_bundle, target="_Test Warehouse - _TC", qty=2, rate=10)

		make_product_bundle("_Test Product Bundle Item Partial 1", ["_Packed Item Partial 1"], 1)

		make_product_bundle("_Test Product Bundle Item Partial 2", ["_Packed Item Partial 2"], 1)

		so = make_sales_order(
			item_code="_Test Product Bundle Item Partial 1",
			warehouse="_Test Warehouse - _TC",
			qty=1,
			uom="Nos",
			stock_uom="Nos",
			conversion_factor=1,
			transaction_date=nowdate(),
			delivery_note=nowdate(),
			do_not_submit=1,
		)

		so.append(
			"items",
			{
				"item_code": "_Test Product Bundle Item Partial 2",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 1,
				"uom": "Nos",
				"stock_uom": "Nos",
				"conversion_factor": 1,
				"delivery_note": nowdate(),
			},
		)

		so.save()
		so.submit()

		dn = make_delivery_note(so.name)
		dn.remove(dn.items[1])
		dn.save()
		dn.submit()

		self.assertEqual(len(dn.items), 1)
		self.assertEqual(len(dn.packed_items), 1)
		self.assertEqual(dn.items[0].item_code, "_Test Product Bundle Item Partial 1")

		so.load_from_db()

		dn = make_delivery_note(so.name)
		dn.save()

		self.assertEqual(len(dn.items), 1)
		self.assertEqual(len(dn.packed_items), 1)
		self.assertEqual(dn.items[0].item_code, "_Test Product Bundle Item Partial 2")

	@change_settings("Selling Settings", {"editable_bundle_item_rates": 1})
	def test_expired_rate_for_packed_item(self):
		bundle = "_Test Product Bundle 1"
		packed_item = "_Packed Item 1"

		# test Update Items with product bundle
		for product_bundle in [bundle]:
			if not frappe.db.exists("Item", product_bundle):
				bundle_item = make_item(product_bundle, {"is_stock_item": 0})
				bundle_item.append(
					"item_defaults",
					{"company": "_Test Company", "default_warehouse": "_Test Warehouse - _TC"},
				)
				bundle_item.save(ignore_permissions=True)

		for product_bundle in [packed_item]:
			if not frappe.db.exists("Item", product_bundle):
				make_item(product_bundle, {"is_stock_item": 0, "stock_uom": "Nos"})

		make_product_bundle(bundle, [packed_item], 1)

		for scenario in [
			{"valid_upto": add_days(nowdate(), -1), "expected_rate": 0.0},
			{"valid_upto": add_days(nowdate(), 1), "expected_rate": 111.0},
		]:
			with self.subTest(scenario=scenario):
				frappe.get_doc(
					{
						"doctype": "Item Price",
						"item_code": packed_item,
						"selling": 1,
						"price_list": "_Test Price List",
						"valid_from": add_days(nowdate(), -1),
						"valid_upto": scenario.get("valid_upto"),
						"price_list_rate": 111,
					}
				).save()

				so = frappe.new_doc("Sales Order")
				so.transaction_date = nowdate()
				so.delivery_date = nowdate()
				so.set_warehouse = ""
				so.company = "_Test Company"
				so.customer = "_Test Customer"
				so.currency = "INR"
				so.selling_price_list = "_Test Price List"
				so.append("items", {"item_code": bundle, "qty": 1})
				so.save()

				self.assertEqual(len(so.items), 1)
				self.assertEqual(len(so.packed_items), 1)
				self.assertEqual(so.items[0].item_code, bundle)
				self.assertEqual(so.packed_items[0].item_code, packed_item)
				self.assertEqual(so.items[0].rate, scenario.get("expected_rate"))
				self.assertEqual(so.packed_items[0].rate, scenario.get("expected_rate"))

	def test_pick_list_without_rejected_materials(self):
		serial_and_batch_item = make_item(
			"_Test Serial and Batch Item for Rejected Materials",
			properties={
				"has_serial_no": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "BAT-TSBIFRM-.#####",
				"serial_no_series": "SN-TSBIFRM-.#####",
			},
		).name

		serial_item = make_item(
			"_Test Serial Item for Rejected Materials",
			properties={
				"has_serial_no": 1,
				"serial_no_series": "SN-TSIFRM-.#####",
			},
		).name

		batch_item = make_item(
			"_Test Batch Item for Rejected Materials",
			properties={
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "BAT-TBIFRM-.#####",
			},
		).name

		normal_item = make_item("_Test Normal Item for Rejected Materials").name

		warehouse = "_Test Warehouse - _TC"
		rejected_warehouse = "_Test Dummy Rejected Warehouse - _TC"

		if not frappe.db.exists("Warehouse", rejected_warehouse):
			frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": rejected_warehouse,
					"company": "_Test Company",
					"warehouse_group": "_Test Warehouse Group",
					"is_rejected_warehouse": 1,
				}
			).insert()

		se = make_stock_entry(item_code=normal_item, qty=1, to_warehouse=warehouse, do_not_submit=True)
		for item in [serial_and_batch_item, serial_item, batch_item]:
			se.append("items", {"item_code": item, "qty": 1, "t_warehouse": warehouse})

		se.save()
		se.submit()

		se = make_stock_entry(
			item_code=normal_item, qty=1, to_warehouse=rejected_warehouse, do_not_submit=True
		)
		for item in [serial_and_batch_item, serial_item, batch_item]:
			se.append("items", {"item_code": item, "qty": 1, "t_warehouse": rejected_warehouse})

		se.save()
		se.submit()

		so = make_sales_order(item_code=normal_item, qty=2, do_not_submit=True)

		for item in [serial_and_batch_item, serial_item, batch_item]:
			so.append("items", {"item_code": item, "qty": 2, "warehouse": warehouse})

		so.save()
		so.submit()

		pick_list = create_pick_list(so.name)

		pick_list.save()
		for row in pick_list.locations:
			self.assertEqual(row.qty, 1.0)
			self.assertFalse(row.warehouse == rejected_warehouse)
			self.assertTrue(row.warehouse == warehouse)

	def test_pick_list_for_batch(self):
		from erpnext.stock.doctype.pick_list.pick_list import create_delivery_note

		batch_item = make_item(
			"_Test Batch Item for Pick LIST",
			properties={
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "BATCH-SDDTBIFRM-.#####",
			},
		).name

		warehouse = "_Test Warehouse - _TC"
		se = make_stock_entry(item_code=batch_item, qty=10, target=warehouse, use_serial_batch_fields=1)
		so = make_sales_order(item_code=batch_item, qty=10, warehouse=warehouse)
		pick_list = create_pick_list(so.name)

		pick_list.save()
		batch_no = frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": se.items[0].serial_and_batch_bundle},
			fields=["batch_no"],
		)[0].batch_no

		for row in pick_list.locations:
			self.assertEqual(row.qty, 10.0)
			self.assertTrue(row.warehouse == warehouse)
			self.assertTrue(row.batch_no == batch_no)

		pick_list.submit()

		dn = create_delivery_note(pick_list.name)
		for row in dn.items:
			self.assertEqual(row.qty, 10.0)
			self.assertTrue(row.warehouse == warehouse)
			self.assertTrue(row.batch_no == batch_no)

		dn.submit()
		dn.reload()

	def test_auto_update_price_list(self):
		item = make_item(
			"_Test Auto Update Price List Item",
		)

		frappe.db.set_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing", 1)
		so = make_sales_order(
			item_code=item.name, currency="USD", qty=1, rate=100, price_list_rate=100, do_not_submit=True
		)
		so.save()

		item_price = frappe.db.get_value("Item Price", {"item_code": item.name}, "price_list_rate")
		self.assertEqual(item_price, 100)

		so = make_sales_order(
			item_code=item.name, currency="USD", qty=1, rate=200, price_list_rate=100, do_not_submit=True
		)
		so.save()

		item_price = frappe.db.get_value("Item Price", {"item_code": item.name}, "price_list_rate")
		self.assertEqual(item_price, 100)

		frappe.db.set_single_value("Stock Settings", "update_existing_price_list_rate", 1)
		so = make_sales_order(
			item_code=item.name, currency="USD", qty=1, rate=200, price_list_rate=200, do_not_submit=True
		)
		so.save()

		item_price = frappe.db.get_value("Item Price", {"item_code": item.name}, "price_list_rate")
		self.assertEqual(item_price, 200)

		frappe.db.set_single_value("Stock Settings", "update_existing_price_list_rate", 0)
		frappe.db.set_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing", 0)

	def test_delivery_note_rate_on_change_of_warehouse(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		item = make_item(
			"_Test Batch Item for Delivery Note Rate",
			{
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "BH-SDDTBIFRM-.#####",
			},
		)

		frappe.db.set_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing", 1)
		so = make_sales_order(
			item_code=item.name, rate=27648.00, price_list_rate=27648.00, qty=1, do_not_submit=True
		)

		so.items[0].rate = 90
		so.save()
		self.assertTrue(so.items[0].discount_amount == 27558.0)
		so.submit()

		warehouse = create_warehouse("NW Warehouse FOR Rate", company=so.company)

		make_stock_entry(
			item_code=item.name,
			qty=2,
			target=warehouse,
			basic_rate=100,
			company=so.company,
			use_serial_batch_fields=1,
		)

		dn = make_delivery_note(so.name)
		dn.items[0].warehouse = warehouse
		dn.save()

		self.assertEqual(dn.items[0].rate, 90)

	def test_credit_limit_on_so_reopening(self):
		# set credit limit
		company = "_Test Company"
		customer = frappe.get_doc("Customer", self.customer)
		# dynamic credit limit
		credit_amt = frappe.db.sql(
			"""
						SELECT SUM(grand_total) AS total
						FROM `tabSales Order`
						WHERE customer = %s AND company = %s AND docstatus = 1
						""",
			(customer.name, company),
			as_dict=True,
		)
		so_amt = frappe.db.get_value(
			"Sales Order", {"customer": self.customer, "company": company}, "grand_total"
		)
		customer_credit_amt = credit_amt[0].get("total") + so_amt

		customer.credit_limits = []
		customer.append(
			"credit_limits",
			{"company": company, "credit_limit": customer_credit_amt, "bypass_credit_limit_check": False},
		)
		customer.save()

		so1 = make_sales_order(qty=9, rate=100, do_not_submit=True)
		so1.customer = self.customer
		so1.customer_address = so1.shipping_address_name = None
		so1.save().submit()

		so1.update_status("Closed")

		so2 = make_sales_order(qty=9, rate=100, do_not_submit=True)
		so2.customer = self.customer
		so2.customer_address = so2.shipping_address_name = None
		so2.save().submit()

		self.assertRaises(frappe.ValidationError, so1.update_status, "Draft")

	def test_item_tax_transfer_from_sales_to_purchase(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order

		item_tax = frappe.new_doc("Item Tax Template")
		item_tax.title = "Test Item Tax Template"
		item_tax.company = "_Test Company"
		item_tax.append("taxes", {"tax_type": "_Test Account Service Tax - _TC", "tax_rate": 2})
		item_tax.save()

		item_group = frappe.get_doc("Item Group", "_Test Item Group")
		item_group.append("taxes", {"item_tax_template": "Test Item Tax Template - _TC"})
		item_group.save()

		so = make_sales_order(item_code="_Test Item", qty=1, do_not_submit=1)
		so.append(
			"taxes",
			{
				"account_head": "_Test Account Service Tax - _TC",
				"charge_type": "On Net Total",
				"description": "TDS",
				"doctype": "Sales Taxes and Charges",
				"rate": 2,
			},
		)
		so.submit()

		po = make_purchase_order(so.name, selected_items=so.items)
		po.supplier = "_Test Supplier"
		po.items[0].rate = 100
		po.submit()
		self.assertEqual(po.taxes[0].tax_amount, 2)

	@change_settings("Selling Settings", {"allow_zero_qty_in_sales_order": 1})
	def test_deliver_zero_qty_purchase_order(self):
		"""
		Test the flow of a Unit Price SO and DN creation against it until completion.
		Flow:
		SO Qty 0 -> Deliver +5 -> Update SO Qty +10 -> Deliver +5 -> SO is 100% delivered
		"""
		so = make_sales_order(qty=0)
		dn = make_delivery_note(so.name)

		self.assertEqual(dn.items[0].qty, 0)
		dn.items[0].qty = 5
		dn.submit()

		# Test SO impact after DN
		so.reload()
		self.assertEqual(so.items[0].delivered_qty, 5)
		self.assertFalse(so.per_delivered)
		self.assertEqual(so.status, "To Deliver and Bill")

		# Update SO Qty to final qty
		first_item_of_so = so.items[0]
		trans_item = json.dumps(
			[
				{
					"item_code": first_item_of_so.item_code,
					"rate": first_item_of_so.rate,
					"qty": 10,
					"docname": first_item_of_so.name,
				}
			]
		)
		update_child_qty_rate("Sales Order", trans_item, so.name)

		# Test: DN maps pending qty from SO
		dn2 = make_delivery_note(so.name)

		so.reload()
		self.assertEqual(so.items[0].qty, 10)
		self.assertEqual(dn2.items[0].qty, 5)

		dn2.submit()

		so.reload()
		self.assertEqual(so.items[0].delivered_qty, 10)
		self.assertEqual(so.per_delivered, 100.0)
		self.assertEqual(so.status, "To Bill")

	@change_settings("Selling Settings", {"allow_zero_qty_in_sales_order": 1})
	def test_bill_zero_qty_sales_order(self):
		so = make_sales_order(qty=0)

		self.assertEqual(so.grand_total, 0)
		self.assertFalse(so.per_billed)
		self.assertEqual(so.items[0].qty, 0)
		self.assertEqual(so.items[0].rate, 100)

		si = make_sales_invoice(so.name)
		self.assertEqual(si.items[0].qty, 0)
		self.assertEqual(si.items[0].rate, 100)

		si.items[0].qty = 5
		si.submit()

		so.reload()
		self.assertEqual(so.items[0].amount, 0)
		self.assertEqual(so.items[0].billed_amt, si.grand_total)
		# SO still has qty 0, so billed % should be unset
		self.assertFalse(so.per_billed)
		self.assertEqual(so.status, "To Deliver and Bill")

	def test_sales_order_discount_on_total(self):
		make_item_price()
		make_pricing_rule()
		so = make_sales_order(qty=10, rate=100, do_not_save=True)
		so.save()
		so.submit()
		self.assertEqual(so.total, 900)

	def test_manual_discount_for_sales_order(self):
		so = make_sales_order(qty=10, rate=100, do_not_save=True)
		so.save()
		self.assertEqual(so.grand_total, 1000)
		so.apply_discount_on = "Grand Total"
		so.additional_discount_percentage = 10
		so.save()
		self.assertEqual(so.grand_total, 900)

	def test_line_item_discount(self):
		make_item_price()
		so = make_sales_order(qty=1, rate=90, do_not_save=True)
		so.save()
		self.assertEqual(so.items[0].discount_amount, 10)
		so.items[0].rate = 110
		so.save()
		self.assertEqual(so.items[0].margin_rate_or_amount, 10)

	def test_sales_order_with_advance_payment_TC_S_040(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(qty=1, rate=3000, do_not_save=True)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill")

		# create payment entry
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		pe = get_payment_entry("Sales Order", so.name)
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = so.currency
		pe.paid_to_account_currency = so.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = so.grand_total
		pe.save(ignore_permissions=True)
		pe.submit()

		self.assertEqual(pe.status, "Submitted")

		# check if the advance payment is recorded in the Sales Order
		so.reload()
		self.assertEqual(so.advance_paid, 3000)

		# create delivery note
		dn = make_delivery_note(so.name)
		dn.submit()

		# assert that 1 quantity is deducted from the warehouse stock
		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -1)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		self.validate_gl_entries(si.name, 3000)

	def test_sales_order_full_qty_process_TC_S_001(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=5,
			rate=5000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -5)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")
		self.validate_gl_entries(si.name, 25000)

	@if_app_installed("india_compliance")
	def test_sales_order_with_partial_advance_payment_TC_S_041(self):
		make_item("_Test Item", {"is_stock_item": 1})
		get_or_create_fiscal_year("_Test Company")
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=1,
			rate=5000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		self.create_and_submit_payment_entry(dt="Sales Order", dn=so.name, amt=2000)

		so.reload()
		self.assertEqual(so.advance_paid, 2000)

		dn = make_delivery_note(so.name)
		dn.submit()

		# check if the stock ledger and general ledger are updated
		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": dn.name,
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "_Test Item",
			},
			"actual_qty",
		)
		self.assertEqual(qty_change, -1)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.allocate_advances_automatically = 1
		si.save()
		si.submit()

		si.reload()
		self.assertEqual(si.status, "Partly Paid")
		self.assertEqual(si.outstanding_amount, 3000)
		self.assertEqual(si.total_advance, 2000)

		self.validate_gl_entries(si.name, 5000)

		# creating payment entry for remaining payment
		self.create_and_submit_payment_entry(dt="Sales Invoice", dn=si.name)

		# check updated sales invoice
		si.reload()
		self.assertEqual(si.status, "Paid")
		self.assertEqual(si.outstanding_amount, 0)

	def test_sales_order_for_partial_delivery_TC_S_002(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=5,
			rate=5000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn = make_delivery_note(so.name)
		dn.items[0].qty = 3
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -3)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")
		self.validate_gl_entries(si.name, 15000)

		dn2 = make_delivery_note(so.name)
		dn2.save()
		dn2.submit()

		self.assertEqual(dn2.status, "To Bill", "Delivery Note not created")

		qty_change2 = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn2.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change2, -2)

		si2 = make_sales_invoice(dn2.name)
		si2.save()
		si2.submit()

		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si2.name, "account": "Sales - _TC"}, "credit"),
			10000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si2.name, "account": "Debtors - _TC"}, "debit"),
			10000,
		)
		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")

	def test_sales_order_with_partial_sales_invoice_TC_S_003(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=4,
			rate=5000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -4)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si1 = make_sales_invoice(dn.name)
		si1.get("items")[0].qty = 2
		si1.insert()
		si1.submit()

		self.assertEqual(si1.status, "Unpaid", "Sales Invoice not created")
		self.validate_gl_entries(si1.name, 10000)

		si2 = make_sales_invoice(dn.name)
		si2.insert()
		si2.submit()

		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")
		self.validate_gl_entries(si2.name, 10000)

	def test_sales_order_via_sales_invoice_TC_S_004(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=4,
			rate=5000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		si = make_sales_invoice(so.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")
		self.validate_gl_entries(si.name, 20000)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

		dn = make_delivery_note(si.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "Completed", "Delivery Note not created")

		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -4)

	def test_sales_order_with_update_stock_in_si_TC_S_008(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=4,
			rate=5000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		si = make_sales_invoice(so.name)
		si.update_stock = 1
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")
		self.validate_gl_entries(si.name, 20000)

		voucher_params = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{**voucher_params, "item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -4)

		so.reload()
		self.assertEqual(so.status, "Completed")

	def test_sales_order_for_partial_dn_via_si_TC_S_005(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=4,
			rate=5000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		si = make_sales_invoice(so.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")
		self.validate_gl_entries(si.name, 20000)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

		dn1 = make_delivery_note(si.name)
		dn1.get("items")[0].qty = 2
		dn1.save()
		dn1.submit()

		self.assertEqual(dn1.status, "Completed", "Delivery Note not created")

		qty_change1 = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn1.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change1, -2)

		dn2 = make_delivery_note(si.name)
		dn2.save()
		dn2.submit()

		self.assertEqual(dn2.status, "Completed", "Delivery Note not created")

		qty_change2 = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn2.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change2, -2)

	def test_sales_order_with_update_stock_in_partial_si_TC_S_009(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=4,
			rate=5000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		si1 = make_sales_invoice(so.name)
		si1.get("items")[0].qty = 2
		si1.update_stock = 1
		si1.save()
		si1.submit()

		self.assertEqual(si1.status, "Unpaid", "Sales Invoice not created")
		self.validate_gl_entries(si1.name, 10000)

		voucher_params = {"voucher_type": "Sales Invoice", "voucher_no": si1.name}
		qty_change1 = frappe.db.get_value(
			"Stock Ledger Entry",
			{**voucher_params, "item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change1, -2)

		si2 = make_sales_invoice(so.name)
		si2.update_stock = 1
		si2.save()
		si2.submit()

		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")
		self.validate_gl_entries(si2.name, 10000)

		voucher_params_si2 = {"voucher_type": "Sales Invoice", "voucher_no": si2.name}
		qty_change2 = frappe.db.get_value(
			"Stock Ledger Entry",
			{**voucher_params_si2, "item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)

		self.assertEqual(qty_change2, -2)

		so.reload()
		self.assertEqual(so.status, "Completed")

	def test_sales_order_for_service_item_TC_S_010(self):
		make_service_item()

		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			item_code="Consultancy",
			qty=1,
			rate=5000,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		si = make_sales_invoice(so.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")
		self.validate_gl_entries(si.name, 5000)

	@if_app_installed("india_compliance")
	def test_sales_order_full_payment_with_gst_TC_S_011(self):
		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=1, rate=5000)

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change[0].get("actual_qty"), -1)

		dn_acc_credit1 = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name, "account": "Stock In Hand - _TIRC"},
			"credit",
		)
		self.assertEqual(dn_acc_credit1, 5000)

		dn_acc_debit1 = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name, "account": "Cost of Goods Sold - _TIRC"},
			"debit",
		)
		self.assertEqual(dn_acc_debit1, 5000)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.insert()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		gl_accounts = {
			"Sales - _TIRC": "credit",
			"Debtors - _TIRC": "debit",
			"Output Tax SGST - _TIRC": "credit",
			"Output Tax CGST - _TIRC": "credit",
		}
		gl_entries = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si, "account": account}, field)
			for account, field in gl_accounts.items()
		}

		self.assertEqual(gl_entries["Sales - _TIRC"], 5000)
		self.assertEqual(gl_entries["Debtors - _TIRC"], 5900)
		self.assertEqual(gl_entries["Output Tax SGST - _TIRC"], 450)
		self.assertEqual(gl_entries["Output Tax CGST - _TIRC"], 450)

		dn.reload()
		self.assertEqual(dn.status, "Completed")

	@if_app_installed("india_compliance")
	def test_sales_order_partial_payment_with_gst_TC_S_012(self):
		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=4, rate=5000)

		dn1 = make_delivery_note(so.name)
		dn1.get("items")[0].qty = 2
		dn1.save()
		dn1.submit()

		self.assertEqual(dn1.status, "To Bill", "Delivery Note not created")

		qty_change1 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn1.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change1[0].get("actual_qty"), -2)

		dn_acc_credit1 = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name, "account": "Stock In Hand - _TIRC"},
			"credit",
		)
		self.assertEqual(dn_acc_credit1, 10000)

		dn_acc_debit1 = frappe.db.get_value(
			"GL Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": dn1.name,
				"account": "Cost of Goods Sold - _TIRC",
			},
			"debit",
		)
		self.assertEqual(dn_acc_debit1, 10000)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si1 = make_sales_invoice(dn1.name)
		si1.insert()
		si1.submit()

		self.assertEqual(si1.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si1 = {"voucher_type": "Sales Invoice", "voucher_no": si1.name}
		gl_accounts = {
			"Sales - _TIRC": "credit",
			"Debtors - _TIRC": "debit",
			"Output Tax SGST - _TIRC": "credit",
			"Output Tax CGST - _TIRC": "credit",
		}
		gl_entries_si1 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si1, "account": account}, field)
			for account, field in gl_accounts.items()
		}
		self.assertEqual(gl_entries_si1["Sales - _TIRC"], 10000)
		self.assertEqual(gl_entries_si1["Debtors - _TIRC"], 11800)
		self.assertEqual(gl_entries_si1["Output Tax SGST - _TIRC"], 900)
		self.assertEqual(gl_entries_si1["Output Tax CGST - _TIRC"], 900)

		dn1.reload()
		self.assertEqual(dn1.status, "Completed")

		dn2 = make_delivery_note(so.name)
		dn2.save()
		dn2.submit()

		qty_change2 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn2.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change2[0].get("actual_qty"), -2)

		dn_acc_credit2 = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn2.name, "account": "Stock In Hand - _TIRC"},
			"credit",
		)
		self.assertEqual(dn_acc_credit2, 10000)

		dn_acc_debit2 = frappe.db.get_value(
			"GL Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": dn2.name,
				"account": "Cost of Goods Sold - _TIRC",
			},
			"debit",
		)
		self.assertEqual(dn_acc_debit2, 10000)

		si2 = make_sales_invoice(dn2.name)
		si2.insert()
		si2.submit()

		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si2 = {"voucher_type": "Sales Invoice", "voucher_no": si2.name}
		gl_accounts = {
			"Sales - _TIRC": "credit",
			"Debtors - _TIRC": "debit",
			"Output Tax SGST - _TIRC": "credit",
			"Output Tax CGST - _TIRC": "credit",
		}
		gl_entries_si2 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si2, "account": account}, field)
			for account, field in gl_accounts.items()
		}
		self.assertEqual(gl_entries_si2["Sales - _TIRC"], 10000)
		self.assertEqual(gl_entries_si2["Debtors - _TIRC"], 11800)
		self.assertEqual(gl_entries_si2["Output Tax SGST - _TIRC"], 900)
		self.assertEqual(gl_entries_si2["Output Tax CGST - _TIRC"], 900)

		dn2.reload()
		self.assertEqual(dn2.status, "Completed")

	@if_app_installed("india_compliance")
	def test_sales_order_partial_sales_invoice_with_gst_TC_S_013(self):
		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=4, rate=5000)

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change[0].get("actual_qty"), -4)

		dn_acc_credit1 = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name, "account": "Stock In Hand - _TIRC"},
			"credit",
		)
		self.assertEqual(dn_acc_credit1, 20000)

		dn_acc_debit1 = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name, "account": "Cost of Goods Sold - _TIRC"},
			"debit",
		)
		self.assertEqual(dn_acc_debit1, 20000)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si1 = make_sales_invoice(dn.name)
		si1.get("items")[0].qty = 2
		si1.insert()
		si1.submit()

		self.assertEqual(si1.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si1 = {"voucher_type": "Sales Invoice", "voucher_no": si1.name}
		gl_accounts = {
			"Sales - _TIRC": "credit",
			"Debtors - _TIRC": "debit",
			"Output Tax SGST - _TIRC": "credit",
			"Output Tax CGST - _TIRC": "credit",
		}
		gl_entries_si1 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si1, "account": account}, field)
			for account, field in gl_accounts.items()
		}
		self.assertEqual(gl_entries_si1["Sales - _TIRC"], 10000)
		self.assertEqual(gl_entries_si1["Debtors - _TIRC"], 11800)
		self.assertEqual(gl_entries_si1["Output Tax SGST - _TIRC"], 900)
		self.assertEqual(gl_entries_si1["Output Tax CGST - _TIRC"], 900)

		si2 = make_sales_invoice(dn.name)
		si2.insert()
		si2.submit()

		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si2 = {"voucher_type": "Sales Invoice", "voucher_no": si2.name}
		gl_accounts = {
			"Sales - _TIRC": "credit",
			"Debtors - _TIRC": "debit",
			"Output Tax SGST - _TIRC": "credit",
			"Output Tax CGST - _TIRC": "credit",
		}
		gl_entries_si2 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si2, "account": account}, field)
			for account, field in gl_accounts.items()
		}
		self.assertEqual(gl_entries_si2["Sales - _TIRC"], 10000)
		self.assertEqual(gl_entries_si2["Debtors - _TIRC"], 11800)
		self.assertEqual(gl_entries_si2["Output Tax SGST - _TIRC"], 900)
		self.assertEqual(gl_entries_si2["Output Tax CGST - _TIRC"], 900)

		dn.reload()
		self.assertEqual(dn.status, "Completed")

	@if_app_installed("india_compliance")
	def test_sales_order_create_dn_via_si_with_gst_TC_S_014(self):
		make_item("_Test Item", {"is_stock_item": 1})
		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=4, rate=5000)

		si = make_sales_invoice(so.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		si_acc_credit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si.name, "account": "Sales - _TIRC"},
			"credit",
		)
		self.assertEqual(si_acc_credit, 20000)

		si_acc_debit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si.name, "account": "Debtors - _TIRC"},
			"debit",
		)
		self.assertEqual(si_acc_debit, 23600)

		si_acc_credit_gst = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si.name, "account": "Output Tax SGST - _TIRC"},
			"credit",
		)
		self.assertEqual(si_acc_credit_gst, 1800)

		si_acc_debit_gst = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si.name, "account": "Output Tax CGST - _TIRC"},
			"credit",
		)
		self.assertEqual(si_acc_debit_gst, 1800)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

		dn = make_delivery_note(si.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "Completed", "Delivery Note not created")

		qty_change = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change[0].get("actual_qty"), -4)
		dn_acc_credit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name, "account": "Stock In Hand - _TIRC"},
			"credit",
		)
		self.assertEqual(dn_acc_credit, 20000)

		dn_acc_debit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name, "account": "Cost of Goods Sold - _TIRC"},
			"debit",
		)
		self.assertEqual(dn_acc_debit, 20000)

	@if_app_installed("india_compliance")
	def test_sales_order_create_partial_dn_via_si_with_gst_TC_S_015(self):
		make_item("_Test Item", {"is_stock_item": 1})
		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=4, rate=5000)

		si = make_sales_invoice(so.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		gl_accounts = {
			"Sales - _TIRC": "credit",
			"Debtors - _TIRC": "debit",
			"Output Tax SGST - _TIRC": "credit",
			"Output Tax CGST - _TIRC": "credit",
		}
		gl_entries = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si, "account": account}, field)
			for account, field in gl_accounts.items()
		}
		self.assertEqual(gl_entries["Sales - _TIRC"], 20000)
		self.assertEqual(gl_entries["Debtors - _TIRC"], 23600)
		self.assertEqual(gl_entries["Output Tax SGST - _TIRC"], 1800)
		self.assertEqual(gl_entries["Output Tax CGST - _TIRC"], 1800)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

		dn1 = make_delivery_note(si.name)
		dn1.get("items")[0].qty = 2
		dn1.save()
		dn1.submit()

		self.assertEqual(dn1.status, "Completed", "Delivery Note not created")

		qty_change1 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn1.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)
		actual_qty = qty_change1[0].get("actual_qty")

		self.assertEqual(actual_qty, -2)

		voucher_params_dn1 = {"voucher_type": "Delivery Note", "voucher_no": dn1.name}
		gl_accounts_dn1 = {"Stock In Hand - _TIRC": "credit", "Cost of Goods Sold - _TIRC": "debit"}
		gl_entries_dn1 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_dn1, "account": account}, field)
			for account, field in gl_accounts_dn1.items()
		}
		self.assertEqual(gl_entries_dn1["Stock In Hand - _TIRC"], 10000)
		self.assertEqual(gl_entries_dn1["Cost of Goods Sold - _TIRC"], 10000)

		dn2 = make_delivery_note(si.name)
		dn2.save()
		dn2.submit()

		self.assertEqual(dn1.status, "Completed", "Delivery Note not created")

		qty_change2 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn2.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)
		actual_qty = qty_change2[0].get("actual_qty")

		self.assertEqual(actual_qty, -2)

		voucher_params_dn2 = {"voucher_type": "Delivery Note", "voucher_no": dn2.name}
		gl_accounts_dn2 = {"Stock In Hand - _TIRC": "credit", "Cost of Goods Sold - _TIRC": "debit"}
		gl_entries_dn2 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_dn2, "account": account}, field)
			for account, field in gl_accounts_dn2.items()
		}
		self.assertEqual(gl_entries_dn2["Stock In Hand - _TIRC"], 10000)
		self.assertEqual(gl_entries_dn2["Cost of Goods Sold - _TIRC"], 10000)

	@if_app_installed("india_compliance")
	def test_sales_order_update_stock_in_si_with_gst_TC_S_018(self):
		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=4, rate=5000)

		si = make_sales_invoice(so.name)
		si.update_stock = 1
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		qty_change = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": si.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)
		actual_qty = qty_change[0].get("actual_qty")

		self.assertEqual(actual_qty, -4)

		voucher_params_si = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		gl_accounts_si = {
			"Stock In Hand - _TIRC": "credit",
			"Cost of Goods Sold - _TIRC": "debit",
			"Sales - _TIRC": "credit",
			"Debtors - _TIRC": "debit",
			"Output Tax SGST - _TIRC": "credit",
			"Output Tax CGST - _TIRC": "credit",
		}
		gl_entries_si = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si, "account": account}, field)
			for account, field in gl_accounts_si.items()
		}
		self.assertEqual(gl_entries_si["Stock In Hand - _TIRC"], 20000)
		self.assertEqual(gl_entries_si["Cost of Goods Sold - _TIRC"], 20000)
		self.assertEqual(gl_entries_si["Sales - _TIRC"], 20000)
		self.assertEqual(gl_entries_si["Debtors - _TIRC"], 23600)
		self.assertEqual(gl_entries_si["Output Tax SGST - _TIRC"], 1800)
		self.assertEqual(gl_entries_si["Output Tax CGST - _TIRC"], 1800)

		so.reload()
		self.assertEqual(so.status, "Completed")

	@if_app_installed("india_compliance")
	def test_sales_order_update_stock_in_partial_si_with_gst_TC_S_019(self):
		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=4, rate=5000)

		si1 = make_sales_invoice(so.name)
		si1.get("items")[0].qty = 2
		si1.update_stock = 1
		si1.save()
		si1.submit()

		self.assertEqual(si1.status, "Unpaid", "Sales Invoice not created")

		qty_change1 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": si1.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)

		actual_qty1 = qty_change1[0].get("actual_qty")

		self.assertEqual(actual_qty1, -2)

		voucher_params_si1 = {"voucher_type": "Sales Invoice", "voucher_no": si1.name}
		gl_accounts_si1 = {
			"Stock In Hand - _TIRC": "credit",
			"Cost of Goods Sold - _TIRC": "debit",
			"Sales - _TIRC": "credit",
			"Debtors - _TIRC": "debit",
		}
		gl_entries_si1 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si1, "account": account}, field)
			for account, field in gl_accounts_si1.items()
		}
		self.assertEqual(gl_entries_si1["Stock In Hand - _TIRC"], 10000)
		self.assertEqual(gl_entries_si1["Cost of Goods Sold - _TIRC"], 10000)
		self.assertEqual(gl_entries_si1["Sales - _TIRC"], 10000)
		self.assertEqual(gl_entries_si1["Debtors - _TIRC"], 11800)

		si2 = make_sales_invoice(so.name)
		si2.update_stock = 1
		si2.save()
		si2.submit()

		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")

		qty_change2 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": si2.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)
		actual_qty2 = qty_change2[0].get("actual_qty")

		self.assertEqual(actual_qty2, -2)

		voucher_params_si2 = {"voucher_type": "Sales Invoice", "voucher_no": si2.name}
		gl_accounts_si2 = {
			"Stock In Hand - _TIRC": "credit",
			"Cost of Goods Sold - _TIRC": "debit",
			"Sales - _TIRC": "credit",
			"Debtors - _TIRC": "debit",
		}
		gl_entries_si2 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si2, "account": account}, field)
			for account, field in gl_accounts_si2.items()
		}
		self.assertEqual(gl_entries_si2["Stock In Hand - _TIRC"], 10000)
		self.assertEqual(gl_entries_si2["Cost of Goods Sold - _TIRC"], 10000)
		self.assertEqual(gl_entries_si2["Sales - _TIRC"], 10000)
		self.assertEqual(gl_entries_si2["Debtors - _TIRC"], 11800)

		so.reload()
		self.assertEqual(so.status, "Completed")

	@if_app_installed("india_compliance")
	def test_sales_order_for_service_item_with_gst_TC_S_020(self):
		make_item("_Test Item", {"is_stock_item": 1})
		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=1, rate=5000)

		si = make_sales_invoice(so.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		gl_accounts_si = {
			"Sales - _TIRC": "credit",
			"Debtors - _TIRC": "debit",
			"Output Tax SGST - _TIRC": "credit",
			"Output Tax CGST - _TIRC": "credit",
		}
		gl_entries_si = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si, "account": account}, field)
			for account, field in gl_accounts_si.items()
		}
		self.assertEqual(gl_entries_si["Sales - _TIRC"], 5000)
		self.assertEqual(gl_entries_si["Debtors - _TIRC"], 5900)
		self.assertEqual(gl_entries_si["Output Tax SGST - _TIRC"], 450)
		self.assertEqual(gl_entries_si["Output Tax CGST - _TIRC"], 450)

	def test_sales_order_of_full_payment_with_shipping_rule_TC_S_021(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=1,
			rate=5000,
			do_not_save=True,
		)
		so.shipping_rule = "_Test Shipping Rule"
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")
		self.assertEqual(so.grand_total, so.total + so.total_taxes_and_charges)

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change[0].get("actual_qty"), -1)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		voucher_params_si = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		gl_accounts_si = {
			"Sales - _TC": "credit",
			"Debtors - _TC": "debit",
			"_Test Account Shipping Charges - _TC": "credit",
		}
		gl_entries_si = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si, "account": account}, field)
			for account, field in gl_accounts_si.items()
		}
		self.assertEqual(gl_entries_si["Sales - _TC"], 5000)
		self.assertEqual(gl_entries_si["Debtors - _TC"], 5200)
		self.assertEqual(gl_entries_si["_Test Account Shipping Charges - _TC"], 200)

	def test_sales_order_for_partial_delivery_with_shipping_rule_TC_S_022(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=4,
			rate=5000,
			do_not_save=True,
		)
		so.shipping_rule = "_Test Shipping Rule"
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")
		self.assertEqual(so.grand_total, so.total + so.total_taxes_and_charges)

		dn1 = make_delivery_note(so.name)
		dn1.items[0].qty = 2
		dn1.save()
		dn1.submit()

		self.assertEqual(dn1.status, "To Bill", "Delivery Note not created")

		qty_change1 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn1.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change1[0].get("actual_qty"), -2)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si1 = make_sales_invoice(dn1.name)
		si1.save()
		si1.submit()

		self.assertEqual(si1.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si1 = {"voucher_type": "Sales Invoice", "voucher_no": si1.name}

		gl_accounts_si1 = {
			"Sales - _TC": "credit",
			"Debtors - _TC": "debit",
			"_Test Account Shipping Charges - _TC": "credit",
		}
		gl_entries_si1 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si1, "account": account}, field)
			for account, field in gl_accounts_si1.items()
		}
		self.assertEqual(gl_entries_si1["Sales - _TC"], 10000)
		self.assertEqual(gl_entries_si1["Debtors - _TC"], 10200)
		self.assertEqual(gl_entries_si1["_Test Account Shipping Charges - _TC"], 200)

		dn2 = make_delivery_note(so.name)
		dn2.save()
		dn2.submit()

		self.assertEqual(dn2.status, "To Bill", "Delivery Note not created")

		qty_change2 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn2.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change2[0].get("actual_qty"), -2)

		si2 = make_sales_invoice(dn2.name)
		si2.save()
		si2.submit()

		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si2 = {"voucher_type": "Sales Invoice", "voucher_no": si2.name}
		gl_accounts_si2 = {
			"Sales - _TC": "credit",
			"Debtors - _TC": "debit",
			"_Test Account Shipping Charges - _TC": "credit",
		}
		gl_entries_si2 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si2, "account": account}, field)
			for account, field in gl_accounts_si2.items()
		}
		self.assertEqual(gl_entries_si2["Sales - _TC"], 10000)
		self.assertEqual(gl_entries_si2["Debtors - _TC"], 10200)
		self.assertEqual(gl_entries_si2["_Test Account Shipping Charges - _TC"], 200)

	def test_sales_order_for_partial_invoice_with_shipping_rule_TC_S_023(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=4,
			rate=5000,
			do_not_save=True,
		)
		so.shipping_rule = "_Test Shipping Rule"
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")
		self.assertEqual(so.grand_total, so.total + so.total_taxes_and_charges)

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change[0].get("actual_qty"), -4)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si1 = make_sales_invoice(dn.name)
		si1.items[0].qty = 2
		si1.save()
		si1.submit()

		self.assertEqual(si1.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si1 = {"voucher_type": "Sales Invoice", "voucher_no": si1.name}
		gl_accounts_si1 = {
			"Sales - _TC": "credit",
			"Debtors - _TC": "debit",
			"_Test Account Shipping Charges - _TC": "credit",
		}
		gl_entries_si1 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si1, "account": account}, field)
			for account, field in gl_accounts_si1.items()
		}
		self.assertEqual(gl_entries_si1["Sales - _TC"], 10000)
		self.assertEqual(gl_entries_si1["Debtors - _TC"], 10200)
		self.assertEqual(gl_entries_si1["_Test Account Shipping Charges - _TC"], 200)

		si2 = make_sales_invoice(dn.name)
		si2.save()
		si2.submit()

		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si2 = {"voucher_type": "Sales Invoice", "voucher_no": si2.name}
		gl_accounts_si2 = {
			"Sales - _TC": "credit",
			"Debtors - _TC": "debit",
			"_Test Account Shipping Charges - _TC": "credit",
		}
		gl_entries_si2 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si2, "account": account}, field)
			for account, field in gl_accounts_si2.items()
		}
		self.assertEqual(gl_entries_si2["Sales - _TC"], 10000)
		self.assertEqual(gl_entries_si2["Debtors - _TC"], 10200)
		self.assertEqual(gl_entries_si2["_Test Account Shipping Charges - _TC"], 200)

	def test_sales_order_via_sales_invoice_with_shipping_rule_TC_S_024(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=4,
			rate=5000,
			do_not_save=True,
		)
		so.shipping_rule = "_Test Shipping Rule"
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")
		self.assertEqual(so.grand_total, so.total + so.total_taxes_and_charges)

		si = make_sales_invoice(so.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		gl_accounts_si = {
			"Sales - _TC": "credit",
			"Debtors - _TC": "debit",
			"_Test Account Shipping Charges - _TC": "credit",
		}
		gl_entries_si = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si, "account": account}, field)
			for account, field in gl_accounts_si.items()
		}
		self.assertEqual(gl_entries_si["Sales - _TC"], 20000)
		self.assertEqual(gl_entries_si["Debtors - _TC"], 20200)
		self.assertEqual(gl_entries_si["_Test Account Shipping Charges - _TC"], 200)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

		dn = make_delivery_note(si.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "Completed", "Delivery Note not created")

		qty_change = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change[0].get("actual_qty"), -4)

	def test_sales_order_for_partial_dn_via_si_for_service_item_TC_S_025(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=4,
			rate=5000,
			do_not_save=True,
		)
		so.shipping_rule = "_Test Shipping Rule"
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")
		self.assertEqual(so.grand_total, so.total + so.total_taxes_and_charges)

		si = make_sales_invoice(so.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		gl_accounts_si = {
			"Sales - _TC": "credit",
			"Debtors - _TC": "debit",
			"_Test Account Shipping Charges - _TC": "credit",
		}
		gl_entries_si = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si, "account": account}, field)
			for account, field in gl_accounts_si.items()
		}
		self.assertEqual(gl_entries_si["Sales - _TC"], 20000)
		self.assertEqual(gl_entries_si["Debtors - _TC"], 20200)
		self.assertEqual(gl_entries_si["_Test Account Shipping Charges - _TC"], 200)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

		dn1 = make_delivery_note(si.name)
		dn1.get("items")[0].qty = 2
		dn1.save()
		dn1.submit()

		self.assertEqual(dn1.status, "Completed", "Delivery Note not created")

		qty_change = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn1.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change[0].get("actual_qty"), -2)

		dn2 = make_delivery_note(si.name)
		dn2.save()
		dn2.submit()

		self.assertEqual(dn2.status, "Completed", "Delivery Note not created")

		qty_change2 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn2.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change2[0].get("actual_qty"), -2)

	def test_so_with_customer_po_TC_S_031(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		frappe.db.set_single_value("Selling Settings", "allow_against_multiple_purchase_orders", 1)
		po = create_purchase_order()
		so_1 = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=5,
			rate=3000,
			do_not_save=True,
		)
		so_1.po_no = po.name
		so_1.po_date = today()
		so_1.save()
		so_1.submit()

		so_2 = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=8,
			rate=3000,
			do_not_save=True,
		)
		so_2.po_no = po.name
		so_2.po_date = today()
		so_2.save()
		so_2.submit()

		dn_1 = make_delivery_note(so_1.name)
		dn_1.save()
		dn_1.submit()

		dn_2 = make_delivery_note(so_2.name)
		dn_2.save()
		dn_2.submit()

		so_1.reload()
		so_2.reload()
		self.assertEqual(dn_1.status, "To Bill")
		self.assertEqual(dn_2.status, "To Bill")

		qty_change_dn_1 = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn_1.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_dn_1, -5)

		qty_change_dn_2 = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn_2.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_dn_2, -8)

		si_1 = make_sales_invoice(dn_1.name)
		si_1.insert()
		si_1.submit()
		self.assertEqual(si_1.status, "Unpaid")

		si_2 = make_sales_invoice(dn_2.name)
		si_2.insert()
		si_2.submit()
		self.assertEqual(si_2.status, "Unpaid")

		self.validate_gl_entries(si_1.name, 15000)
		self.validate_gl_entries(si_2.name, 24000)

	def test_so_with_qi_flow_TC_S_032(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		from erpnext.stock.doctype.quality_inspection.test_quality_inspection import create_quality_inspection

		item = make_item(
			"_Test Item for quality inspection",
			{"is_stock_item": 1, "inspection_required_before_delivery": 1},
		)

		parameters = [
			"_Test Needle Shape",
			"_Test Syringe Shape",
			"_Test Plastic Clarity",
			"_Test Syringe Length",
		]
		for param in parameters:
			frappe.get_doc({"doctype": "Quality Inspection Parameter", "parameter": param}).insert()

		template = frappe.get_doc(
			{
				"doctype": "Quality Inspection Template",
				"quality_inspection_template_name": "_Test Syringe",
				"item_quality_inspection_parameter": [
					{"specification": "_Test Needle Shape", "value": "OK"},
					{"specification": "_Test Syringe Shape", "value": "OK"},
					{"specification": "_Test Plastic Clarity", "value": "OK"},
					{"specification": "_Test Syringe Length", "numeric": 1, "min_value": 4, "max_value": 6},
				],
			}
		).insert()

		frappe.db.set_value("Item", item.name, "quality_inspection_template", template.name)
		item.reload()
		get_or_create_fiscal_year("_Test Company")
		make_stock_entry(item_code=item.name, qty=10, rate=5000, target="_Test Warehouse - _TC")

		sales_order = make_sales_order(item_code=item.name, qty=5, rate=200)

		delivery_note = make_delivery_note(sales_order.name)
		delivery_note.save()

		with self.assertRaises(frappe.ValidationError):
			delivery_note.submit()

		quality_inspection = create_quality_inspection(
			reference_type="Delivery Note",
			reference_name=delivery_note.name,
			item_code=item.name,
			do_not_save=True,
			readings=[
				{"specification": "_Test Needle Shape", "value": "OK"},
				{"specification": "_Test Syringe Shape", "value": "OK"},
				{"specification": "_Test Plastic Clarity", "value": "OK"},
				{
					"specification": "_Test Syringe Length",
					"numeric": 1,
					"reading_1": 5,
					"manual_inspection": 1,
				},
			],
		)
		self.assertEqual(quality_inspection.status, "Accepted")

		quality_inspection.child_row_reference = True
		quality_inspection.save()
		quality_inspection.submit()

		delivery_note.reload()
		delivery_note.submit()

		self.assertEqual(delivery_note.status, "To Bill")

		stock_entry = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item_code": item.name,
				"qty": -5,
				"warehouse": "Stores - _TC",
				"valuation_rate": 100,
				"stock_uom": "Nos",
			}
		)
		self.assertTrue(stock_entry)
		sales_invoice = make_sales_invoice(delivery_note.name)
		sales_invoice.insert()
		sales_invoice.submit()
		self.assertEqual(sales_invoice.status, "Unpaid")

	def test_sales_order_update_stock_in_si_with_shipping_rule_TC_S_028(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=4,
			rate=5000,
			do_not_save=True,
		)
		so.shipping_rule = "_Test Shipping Rule"
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")
		self.assertEqual(so.grand_total, so.total + so.total_taxes_and_charges)

		si = make_sales_invoice(so.name)
		si.update_stock = 1
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": si.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -4)

		voucher_params_si = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		gl_accounts_si = {
			"Sales - _TC": "credit",
			"Debtors - _TC": "debit",
			"_Test Account Shipping Charges - _TC": "credit",
		}
		gl_entries_si = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si, "account": account}, field)
			for account, field in gl_accounts_si.items()
		}
		self.assertEqual(gl_entries_si["Sales - _TC"], 20000)
		self.assertEqual(gl_entries_si["Debtors - _TC"], 20200)
		self.assertEqual(gl_entries_si["_Test Account Shipping Charges - _TC"], 200)

	def test_sales_order_update_stock_in_partial_si_with_shipping_rule_TC_S_029(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=4,
			rate=5000,
			do_not_save=True,
		)
		so.shipping_rule = "_Test Shipping Rule"
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")
		self.assertEqual(so.grand_total, so.total + so.total_taxes_and_charges)

		si1 = make_sales_invoice(so.name)
		si1.get("items")[0].qty = 2
		si1.update_stock = 1
		si1.save()
		si1.submit()

		self.assertEqual(si1.status, "Unpaid", "Sales Invoice not created")

		qty_change1 = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": si1.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change1, -2)

		voucher_params_si1 = {"voucher_type": "Sales Invoice", "voucher_no": si1.name}
		gl_accounts_si1 = {
			"Sales - _TC": "credit",
			"Debtors - _TC": "debit",
			"_Test Account Shipping Charges - _TC": "credit",
		}
		gl_entries_si1 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si1, "account": account}, field)
			for account, field in gl_accounts_si1.items()
		}
		self.assertEqual(gl_entries_si1["Sales - _TC"], 10000)
		self.assertEqual(gl_entries_si1["Debtors - _TC"], 10200)
		self.assertEqual(gl_entries_si1["_Test Account Shipping Charges - _TC"], 200)

		si2 = make_sales_invoice(so.name)
		si2.update_stock = 1
		si2.save()
		si2.submit()

		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")

		qty_change2 = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": si2.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change2, -2)

		voucher_params_si2 = {"voucher_type": "Sales Invoice", "voucher_no": si2.name}
		gl_accounts_si2 = {
			"Sales - _TC": "credit",
			"Debtors - _TC": "debit",
			"_Test Account Shipping Charges - _TC": "credit",
		}
		gl_entries_si2 = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si2, "account": account}, field)
			for account, field in gl_accounts_si2.items()
		}
		self.assertEqual(gl_entries_si2["Sales - _TC"], 10000)
		self.assertEqual(gl_entries_si2["Debtors - _TC"], 10200)
		self.assertEqual(gl_entries_si2["_Test Account Shipping Charges - _TC"], 200)

	def test_sales_order_for_sales_return_TC_S_033(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=5,
			rate=3000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change_dn = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_dn, -5)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		sr = make_sales_return(dn.name)
		sr.save()
		sr.submit()

		self.assertEqual(sr.status, "To Bill", "Sales Return not created")

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 5)

	def test_sales_order_for_sales_return_via_si_TC_S_034(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=5,
			rate=3000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change_dn = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_dn, -5)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		gl_accounts_si = {"Sales - _TC": "credit", "Debtors - _TC": "debit"}
		gl_entries_si = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si, "account": account}, field)
			for account, field in gl_accounts_si.items()
		}
		self.assertEqual(gl_entries_si["Sales - _TC"], 15000)
		self.assertEqual(gl_entries_si["Debtors - _TC"], 15000)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		sr = make_sales_return(dn.name)
		sr.save()
		sr.submit()

		self.assertEqual(sr.status, "To Bill", "Sales Return not created")

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 5)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return as make_credit_note

		cn = make_credit_note(si.name)
		cn.save()
		cn.submit()

		self.assertEqual(cn.status, "Return", "Credit Note not created")

		voucher_params_cn = {"voucher_type": "Sales Invoice", "voucher_no": cn.name}
		gl_accounts_cn = {"Debtors - _TC": "credit", "Sales - _TC": "debit"}
		gl_entries_cn = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_cn, "account": account}, field)
			for account, field in gl_accounts_cn.items()
		}
		self.assertEqual(gl_entries_cn["Debtors - _TC"], 15000)
		self.assertEqual(gl_entries_cn["Sales - _TC"], 15000)

	def test_sales_order_for_partial_return_TC_S_035(self):
		make_item("_Test Item", {"is_stock_item": 1})
		# stock_entry_doc = make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=5,
			rate=3000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change_dn = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_dn, -5)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		sr = make_sales_return(dn.name)
		sr.items[0].qty = -2
		sr.save()
		sr.submit()

		self.assertEqual(sr.status, "To Bill", "Sales Return not created")

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 2)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		gl_accounts_si = {"Sales - _TC": "credit", "Debtors - _TC": "debit"}
		gl_entries_si = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si, "account": account}, field)
			for account, field in gl_accounts_si.items()
		}

		self.assertEqual(gl_entries_si["Sales - _TC"], si.grand_total)
		self.assertEqual(gl_entries_si["Debtors - _TC"], si.grand_total)

	def test_sales_order_for_sales_return_via_payment_entry_TC_S_036(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=5,
			rate=3000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change_dn = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_dn, -5)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		voucher_params_si = {"voucher_type": "Sales Invoice", "voucher_no": si.name}
		gl_accounts_si = {"Sales - _TC": "credit", "Debtors - _TC": "debit"}
		gl_entries_si = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_si, "account": account}, field)
			for account, field in gl_accounts_si.items()
		}
		self.assertEqual(gl_entries_si["Sales - _TC"], 15000)
		self.assertEqual(gl_entries_si["Debtors - _TC"], 15000)

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

		pe = create_payment_entry(
			payment_type="Receive",
			party_type="Customer",
			party="_Test Customer",
			paid_from="Debtors - _TC",
			paid_to="Cash - _TC",
			paid_amount=15000,
		)
		reference = pe.append("references")
		reference.references_doctype = "Sales Invoice"
		reference.references_name = si.name
		reference.total_amount = 15000
		reference.account = "Debtors - _TC"
		pe.save()
		pe.submit()

		pe_acc_credit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Payment Entry", "voucher_no": pe.name, "account": "Debtors - _TC"},
			"credit",
		)
		self.assertEqual(pe_acc_credit, 15000)

		pe_acc_debit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Payment Entry", "voucher_no": pe.name, "account": "Cash - _TC"},
			"debit",
		)
		self.assertEqual(pe_acc_debit, 15000)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		sr = make_sales_return(dn.name)
		sr.save()
		sr.submit()

		self.assertEqual(sr.status, "To Bill", "Sales Return not created")

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 5)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return as make_credit_note

		cn = make_credit_note(si.name)
		cn.save()
		cn.submit()

		self.assertEqual(cn.status, "Return", "Credit Note not created")

		voucher_params_cn = {"voucher_type": "Sales Invoice", "voucher_no": cn.name}
		gl_accounts_cn = {"Debtors - _TC": "credit", "Sales - _TC": "debit"}
		gl_entries_cn = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_cn, "account": account}, field)
			for account, field in gl_accounts_cn.items()
		}
		self.assertEqual(gl_entries_cn["Debtors - _TC"], 15000)
		self.assertEqual(gl_entries_cn["Sales - _TC"], 15000)

	def test_sales_order_for_partial_sales_return_via_payment_entry_TC_S_037(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=5,
			rate=3000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change_dn = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_dn, -5)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		def validate_gl_entries(voucher_type, voucher_no, accounts):
			for account, field, expected_value in accounts:
				actual_value = frappe.db.get_value(
					"GL Entry",
					{"voucher_type": voucher_type, "voucher_no": voucher_no, "account": account},
					field,
				)
				self.assertEqual(actual_value, expected_value)

		validate_gl_entries(
			"Sales Invoice", si.name, [("Sales - _TC", "credit", 15000), ("Debtors - _TC", "debit", 15000)]
		)

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

		pe = create_payment_entry(
			payment_type="Receive",
			party_type="Customer",
			party="_Test Customer",
			paid_from="Debtors - _TC",
			paid_to="Cash - _TC",
			paid_amount=15000,
		)
		reference = pe.append("references")
		reference.reference_doctype = "Sales Invoice"
		reference.reference_name = si.name
		reference.total_amount = 15000
		reference.account = "Debtors - _TC"
		pe.save()
		pe.submit()

		validate_gl_entries(
			"Payment Entry", pe.name, [("Debtors - _TC", "credit", 15000), ("Cash - _TC", "debit", 15000)]
		)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		sr = make_sales_return(dn.name)
		sr.items[0].qty = -2
		sr.save()
		sr.submit()

		self.assertEqual(sr.status, "To Bill", "Sales Return not created")

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 2)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return as make_credit_note

		cn = make_credit_note(si.name)
		cn.save()
		cn.submit()

		self.assertEqual(cn.status, "Return", "Credit Note not created")

		validate_gl_entries(
			"Sales Invoice", cn.name, [("Debtors - _TC", "credit", 15000), ("Sales - _TC", "debit", 15000)]
		)

		so.reload()
		self.assertEqual(so.status, "To Deliver", "Sales Order not updated")

	@if_app_installed("india_compliance")
	def test_sales_order_create_si_via_pe_dn_with_gst_TC_S_042(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=1, rate=5000)
		make_item("_Test Item", {"is_stock_item": 1})
		pe = create_payment_entry(
			company="_Test Indian Registered Company",
			payment_type="Receive",
			party_type="Customer",
			party="_Test Registered Customer",
			paid_from="Debtors - _TIRC",
			paid_to="Cash - _TIRC",
			paid_amount=so.grand_total,
		)
		pe.append(
			"references",
			{
				"reference_doctype": "Sales Order",
				"reference_name": so.name,
				"total_amount": so.grand_total,
				"account": "Debtors - _TIRC",
			},
		)
		pe.save()
		pe.submit()

		self.assertEqual(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_type": "Payment Entry", "voucher_no": pe.name, "account": "Debtors - _TIRC"},
				"credit",
			),
			so.grand_total,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_type": "Payment Entry", "voucher_no": pe.name, "account": "Cash - _TIRC"},
				"debit",
			),
			so.grand_total,
		)

		dn = make_delivery_note(so.name)
		dn.submit()

		stock_entry = frappe.get_all(
			"Stock Ledger Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": dn.name,
				"warehouse": "Stores - _TIRC",
				"item_code": "_Test Item",
			},
			["valuation_rate", "actual_qty"],
		)[0]

		self.assertEqual(stock_entry.get("actual_qty"), -1)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_type": "Delivery Note", "voucher_no": dn.name, "account": "Stock In Hand - _TIRC"},
				"credit",
			),
			5000,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry",
				{
					"voucher_type": "Delivery Note",
					"voucher_no": dn.name,
					"account": "Cost of Goods Sold - _TIRC",
				},
				"debit",
			),
			5000,
		)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.allocate_advances_automatically = 1
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TIRC"}, "credit"),
			5000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TIRC"}, "debit"),
			5900,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": si.name, "account": "Output Tax SGST - _TIRC"}, "credit"
			),
			450,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": si.name, "account": "Output Tax CGST - _TIRC"}, "credit"
			),
			450,
		)

	@if_app_installed("india_compliance")
	def test_sales_order_create_si_via_partial_pe_dn_with_gst_TC_S_043(self):
		make_item("_Test Item", {"is_stock_item": 1})
		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=1, rate=5000)

		create_registered_bank_account()

		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		pe = get_payment_entry(dt="Sales Order", dn=so.name)
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_amount = 2000
		for i in pe.references:
			i.allocated_amount = 2000
		pe.save()
		pe.submit()

		self.assertEqual(pe.status, "Submitted")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pe.name, "account": "Debtors - _TIRC"}, "credit"),
			2000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pe.name, "account": "Cash - _TIRC"}, "debit"), 2000
		)

		dn = make_delivery_note(so.name)
		dn.submit()

		stock_entry = frappe.get_all(
			"Stock Ledger Entry",
			{"voucher_no": dn.name, "warehouse": "Stores - _TIRC", "item_code": "_Test Item"},
			["valuation_rate", "actual_qty"],
		)[0]
		self.assertEqual(stock_entry.get("actual_qty"), -1)

		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": dn.name, "account": "Stock In Hand - _TIRC"}, "credit"
			),
			5000,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": dn.name, "account": "Cost of Goods Sold - _TIRC"}, "debit"
			),
			5000,
		)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.allocate_advances_automatically = 1
		si.save()
		si.submit()

		si.reload()
		self.assertEqual(si.status, "Partly Paid")

		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TIRC"}, "credit"),
			5000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TIRC"}, "debit"),
			5900,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": si.name, "account": "Output Tax SGST - _TIRC"}, "credit"
			),
			450,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": si.name, "account": "Output Tax CGST - _TIRC"}, "credit"
			),
			450,
		)

		pe2 = get_payment_entry(dt="Sales Invoice", dn=si.name)
		pe2.reference_no = "1"
		pe2.reference_date = nowdate()
		pe2.save()
		pe2.submit()

		self.assertEqual(pe2.status, "Submitted")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pe2.name, "account": "Debtors - _TIRC"}, "credit"),
			3900,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pe2.name, "account": "Cash - _TIRC"}, "debit"),
			3900,
		)

		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		self.assertEqual(si.status, "Paid")

	@if_app_installed("india_compliance")
	def test_sales_order_with_full_advance_payment_and_shipping_rule_TC_S_044(self):
		make_item("_Test Item", {"is_stock_item": 1})
		get_or_create_fiscal_year("_Test Company")
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=1,
			rate=5000,
			do_not_save=True,
		)
		so.shipping_rule = "_Test Shipping Rule"
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")
		self.assertEqual(so.grand_total, so.total + so.total_taxes_and_charges)

		self.create_and_submit_payment_entry(dt="Sales Order", dn=so.name)

		dn = make_delivery_note(so.name)
		dn.submit()

		stock_ledger_entry = frappe.get_all(
			"Stock Ledger Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": dn.name,
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "_Test Item",
			},
			["valuation_rate", "actual_qty"],
		)
		self.assertEqual(stock_ledger_entry[0].get("actual_qty"), -1)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.allocate_advances_automatically = 1
		si.save()
		si.submit()
		si.reload()
		self.assertEqual(si.status, "Paid")

		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5200,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_no": si.name, "account": "_Test Account Shipping Charges - _TC"},
				"credit",
			),
			200,
		)

	@if_app_installed("india_compliance")
	def test_sales_order_with_partial_advance_payment_and_shipping_rule_TC_S_045(self):
		make_item("_Test Item", {"is_stock_item": 1})
		get_or_create_fiscal_year
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		so = make_sales_order(
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			qty=1,
			rate=5000,
			do_not_save=True,
		)
		so.shipping_rule = "_Test Shipping Rule"
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")
		self.assertEqual(so.grand_total, so.total + so.total_taxes_and_charges)

		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		pe = get_payment_entry(dt="Sales Order", dn=so.name)
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_amount = 2000
		for i in pe.references:
			i.allocated_amount = 2000
		pe.save()
		pe.submit()

		self.assertEqual(pe.status, "Submitted")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pe.name, "account": "Debtors - _TC"}, "credit"),
			2000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pe.name, "account": "Cash - _TC"}, "debit"), 2000
		)

		dn = make_delivery_note(so.name)
		dn.submit()

		stock_ledger_entry = frappe.get_all(
			"Stock Ledger Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": dn.name,
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "_Test Item",
			},
			["valuation_rate", "actual_qty"],
		)
		self.assertEqual(stock_ledger_entry[0].get("actual_qty"), -1)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.allocate_advances_automatically = 1
		si.save()
		si.submit()
		si.reload()
		self.assertEqual(si.status, "Partly Paid")

		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5200,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_no": si.name, "account": "_Test Account Shipping Charges - _TC"},
				"credit",
			),
			200,
		)

		pe2 = get_payment_entry(dt="Sales Invoice", dn=si.name)
		pe2.reference_no = "1"
		pe2.reference_date = nowdate()
		pe2.save()
		pe2.submit()

		self.assertEqual(pe2.status, "Submitted")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pe2.name, "account": "Debtors - _TC"}, "credit"),
			3200,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pe2.name, "account": "Cash - _TC"}, "debit"), 3200
		)

		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		self.assertEqual(si.status, "Paid")

	def test_sales_order_create_si_via_pe_dn_with_pricing_rule_TC_S_046(self):
		self.customer = frappe.get_doc("Customer", self.customer)
		# Append company if not already present
		company = "_Test Company"
		if company and not any(c.company == company for c in self.customer.companies):
			self.customer.append("companies", {"company": company})
			self.customer.save()
		make_item_price()
		make_pricing_rule()
		so = make_sales_order(qty=10, rate=90)
		so.save()
		so.submit()

		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		pe = get_payment_entry(dt="Sales Order", dn=so.name)
		pe.save()
		pe.submit()

		gl_entry_list = frappe.get_all(
			"GL Entry", filters={"voucher_no": pe.name}, fields=["account", "debit", "credit"]
		)

		# Get the first debit and credit entry with corresponding amounts
		debit_entry = next((entry for entry in gl_entry_list if entry["debit"] > 0), None)
		credit_entry = next((entry for entry in gl_entry_list if entry["credit"] > 0), None)

		# debit_account = debit_entry['account'] if debit_entry else None
		debit_amount = debit_entry["debit"] if debit_entry else None

		# credit_account = credit_entry['account'] if credit_entry else None
		credit_amount = credit_entry["credit"] if credit_entry else None

		self.assertEqual(pe.status, "Submitted")
		self.assertEqual(credit_amount, pe.paid_amount)
		self.assertEqual(debit_amount, pe.paid_amount)

		dn = make_delivery_note(so.name)
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")
		stock_ledger_entry = frappe.get_all(
			"Stock Ledger Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": dn.name,
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "_Test Item",
			},
			["valuation_rate", "actual_qty"],
		)
		self.assertEqual(stock_ledger_entry[0].get("actual_qty"), -10)

		si = self.create_and_submit_sales_invoice(
			dn.name, advances_automatically=1, expected_amount=dn.grand_total
		)
		si.reload()
		self.assertEqual(si.status, "Paid")

	def test_sales_order_create_si_via_partial_pe_with_pricing_rule_TC_S_047(self):
		make_item_price()
		make_pricing_rule()

		so = self.create_and_submit_sales_order(qty=10, rate=90)

		self.create_and_submit_payment_entry(dt="Sales Order", dn=so.name, amt=400)

		dn = make_delivery_note(so.name)
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")
		stock_ledger_entry = frappe.get_all(
			"Stock Ledger Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": dn.name,
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "_Test Item",
			},
			["valuation_rate", "actual_qty"],
		)
		self.assertEqual(stock_ledger_entry[0].get("actual_qty"), -10)

		si = self.create_and_submit_sales_invoice(dn.name, advances_automatically=1, expected_amount=1062)
		si.reload()
		self.assertEqual(si.status, "Partly Paid")

		self.create_and_submit_payment_entry(dt="Sales Invoice", dn=si.name)

		si.reload()
		self.assertEqual(si.status, "Paid")

	def test_sales_order_creating_credit_note_after_SR_TC_S_048(self):
		so = self.create_and_submit_sales_order(qty=5, rate=3000)

		self.create_and_submit_payment_entry(dt="Sales Order", dn=so.name)

		dn = self.create_and_validate_delivery_note(so.name, -5)

		si = self.create_and_submit_sales_invoice(dn.name, advances_automatically=1, expected_amount=15000)
		si.reload()
		self.assertEqual(si.status, "Paid")

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		sr = make_sales_return(dn.name)
		sr.save()
		sr.submit()

		self.assertEqual(sr.status, "To Bill", "Sales Return not created")

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 5)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return as make_credit_note

		cn = make_credit_note(si.name)
		cn.advances.clear()
		cn.save()
		cn.submit()

		self.assertEqual(cn.status, "Return", "Credit Note not created")

		voucher_params_cn = {"voucher_type": "Sales Invoice", "voucher_no": cn.name}
		gl_accounts_cn = {"Debtors - _TC": "credit", "Sales - _TC": "debit"}
		gl_entries_cn = {
			account: frappe.db.get_value("GL Entry", {**voucher_params_cn, "account": account}, field)
			for account, field in gl_accounts_cn.items()
		}
		self.assertEqual(gl_entries_cn["Debtors - _TC"], 15000)
		self.assertEqual(gl_entries_cn["Sales - _TC"], 15000)

	def test_sales_order_to_sales_return_SR_TC_S_049(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		so = self.create_and_submit_sales_order(qty=5, rate=3000)
		self.create_and_submit_payment_entry(dt="Sales Order", dn=so.name)

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		sr = make_sales_return(dn.name)
		sr.save()
		sr.submit()

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 5)

	def test_sales_order_creating_full_si_for_service_item_SI_TC_S_050(self):
		make_service_item()
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_customer

		customer = create_customer("_Test Customer 1", currency="INR")
		so = make_sales_order(
			customer=customer,
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			item_code="Consultancy",
			qty=1,
			rate=5000,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		self.create_and_submit_payment_entry(dt="Sales Order", dn=so.name)

		si = make_sales_invoice(so.name)
		si.allocate_advances_automatically = 1
		si.only_include_allocated_payments = 1
		si.save()
		si.submit()
		si.reload()

		self.assertEqual(si.status, "Paid", "Sales Invoice not created")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5000,
		)

	def test_sales_order_creating_partial_pe_for_service_item_SI_TC_S_051(self):
		make_service_item()

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_customer

		customer = create_customer("_Test Customer 1", currency="INR")
		so = make_sales_order(
			customer=customer,
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			item_code="Consultancy",
			qty=1,
			rate=5000,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		self.create_and_submit_payment_entry(dt="Sales Order", dn=so.name, amt=2000)

		si = make_sales_invoice(so.name)
		si.allocate_advances_automatically = 1
		si.only_include_allocated_payments = 1
		si.save()
		si.submit()
		si.reload()

		self.assertEqual(si.status, "Partly Paid", "Sales Invoice not created")
		self.assertEqual(si.outstanding_amount, 3000)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5000,
		)

		self.create_and_submit_payment_entry(dt="Sales Invoice", dn=si.name)

		si.reload()
		self.assertEqual(si.status, "Paid")
		self.assertEqual(si.outstanding_amount, 0)

	def test_sales_order_creating_si_with_update_stock_SI_TC_S_052(self):
		so = self.create_and_submit_sales_order(qty=1, rate=5000)

		self.create_and_submit_payment_entry(dt="Sales Order", dn=so.name, amt=so.grand_total)

		si = make_sales_invoice(so.name)
		si.allocate_advances_automatically = 1
		si.only_include_allocated_payments = 1
		si.update_stock = 1
		si.save()
		si.submit()
		si.reload()

		self.assertEqual(si.status, "Paid", "Sales Invoice not created")
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_no": si.name, "warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
				"actual_qty",
			),
			-1,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5000,
		)

	def test_sales_order_creating_partial_pe_with_update_stock_SI_TC_S_053(self):
		so = self.create_and_submit_sales_order(qty=1, rate=5000)

		self.create_and_submit_payment_entry(dt="Sales Order", dn=so.name, amt=2000)

		si = make_sales_invoice(so.name)
		si.allocate_advances_automatically = 1
		si.only_include_allocated_payments = 1
		si.update_stock = 1
		si.save()
		si.submit()
		si.reload()

		self.assertEqual(si.status, "Partly Paid", "Sales Invoice not created")
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_no": si.name, "warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
				"actual_qty",
			),
			-1,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5000,
		)

		self.create_and_submit_payment_entry(dt="Sales Invoice", dn=si.name)

		si.reload()
		self.assertEqual(si.status, "Paid")
		self.assertEqual(si.outstanding_amount, 0)

	def test_sales_order_creating_si_with_product_bundle_TC_S_057(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_customer

		customer = create_customer("_Test Customer 1", currency="INR")
		product_bundle = make_item("_Test Product Bundle", {"is_stock_item": 0})
		make_item("_Test Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Bundle Item 2", {"is_stock_item": 1})

		make_product_bundle("_Test Product Bundle", ["_Test Bundle Item 1", "_Test Bundle Item 2"])

		make_stock_entry(item="_Test Bundle Item 1", target="_Test Warehouse - _TC", qty=10, rate=4000)
		make_stock_entry(item="_Test Bundle Item 2", target="_Test Warehouse - _TC", qty=10, rate=4000)

		so = make_sales_order(
			customer=customer,
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			item_code=product_bundle.item_code,
			qty=1,
			rate=20000,
			do_not_save=True,
		)
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn = make_delivery_note(so.name)
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{
					"voucher_no": dn.name,
					"warehouse": "_Test Warehouse - _TC",
					"item_code": "_Test Bundle Item 1",
				},
				"actual_qty",
			),
			-1,
		)
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{
					"voucher_no": dn.name,
					"warehouse": "_Test Warehouse - _TC",
					"item_code": "_Test Bundle Item 2",
				},
				"actual_qty",
			),
			-1,
		)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()
		si.reload()
		self.assertEqual(si.status, "Unpaid")

		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"),
			20000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			20000,
		)

	def test_sales_order_creating_si_with_product_bundle_and_shipping_rule_TC_S_058(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_customer

		customer = create_customer("_Test Customer 1", currency="INR")
		product_bundle = make_item("_Test Product Bundle", {"is_stock_item": 0})
		make_item("_Test Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Bundle Item 2", {"is_stock_item": 1})

		make_product_bundle("_Test Product Bundle", ["_Test Bundle Item 1", "_Test Bundle Item 2"])
		make_stock_entry(item_code="_Test Bundle Item 1", qty=10, rate=5000, target="_Test Warehouse - _TC")
		make_stock_entry(item_code="_Test Bundle Item 2", qty=10, rate=5000, target="_Test Warehouse - _TC")

		so = make_sales_order(
			customer=customer,
			cost_center="Main - _TC",
			selling_price_list="Standard Selling",
			item_code=product_bundle.item_code,
			qty=1,
			rate=20000,
			do_not_save=True,
		)
		so.shipping_rule = "_Test Shipping Rule"
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")
		self.assertEqual(so.grand_total, so.total + so.total_taxes_and_charges)

		dn = make_delivery_note(so.name)
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{
					"voucher_no": dn.name,
					"warehouse": "_Test Warehouse - _TC",
					"item_code": "_Test Bundle Item 1",
				},
				"actual_qty",
			),
			-1,
		)
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{
					"voucher_no": dn.name,
					"warehouse": "_Test Warehouse - _TC",
					"item_code": "_Test Bundle Item 2",
				},
				"actual_qty",
			),
			-1,
		)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()
		si.reload()
		self.assertEqual(si.status, "Unpaid")

		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"),
			20000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			20200,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_no": si.name, "account": "_Test Account Shipping Charges - _TC"},
				"credit",
			),
			200,
		)

	@if_app_installed("india_compliance")
	def test_sales_order_creating_si_with_product_bundle_and_gst_rule_TC_S_059(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_registered_company

		create_registered_company()
		create_test_warehouse(
			name="Stores - _TIRC", warehouse_name="Stores", company="_Test Indian Registered Company"
		)
		get_or_create_fiscal_year("_Test Indian Registered Company")
		make_item("_Test Item", {"is_stock_item": 1})
		product_bundle = make_item("_Test Product Bundle", {"is_stock_item": 0})
		make_item("_Test Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Bundle Item 2", {"is_stock_item": 1})

		make_product_bundle("_Test Product Bundle", ["_Test Bundle Item 1", "_Test Bundle Item 2"])
		make_stock_entry(item_code="_Test Bundle Item 1", qty=10, rate=5000, target="Stores - _TIRC")
		make_stock_entry(item_code="_Test Bundle Item 2", qty=10, rate=5000, target="Stores - _TIRC")

		so = self.create_and_submit_sales_order_with_gst(product_bundle.item_code, qty=1, rate=20000)

		dn = make_delivery_note(so.name)
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_no": dn.name, "warehouse": "Stores - _TIRC", "item_code": "_Test Bundle Item 1"},
				"actual_qty",
			),
			-1,
		)
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_no": dn.name, "warehouse": "Stores - _TIRC", "item_code": "_Test Bundle Item 2"},
				"actual_qty",
			),
			-1,
		)

		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": dn.name, "account": "Cost of Goods Sold - _TIRC"}, "debit"
			),
			10000,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": dn.name, "account": "Stock In Hand - _TIRC"}, "credit"
			),
			10000,
		)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()
		si.reload()

		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TIRC"}, "credit"),
			20000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TIRC"}, "debit"),
			23600,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": si.name, "account": "Output Tax SGST - _TIRC"}, "credit"
			),
			1800,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": si.name, "account": "Output Tax CGST - _TIRC"}, "credit"
			),
			1800,
		)

	def test_sales_order_creating_si_with_installation_note_TC_S_060(self):
		so = self.create_and_submit_sales_order(qty=5, rate=3000)

		dn = make_delivery_note(so.name)
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")
		stock_ledger_entry = frappe.get_all(
			"Stock Ledger Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": dn.name,
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "_Test Item",
			},
			["valuation_rate", "actual_qty"],
		)
		self.assertEqual(stock_ledger_entry[0].get("actual_qty"), -5)

		from erpnext.stock.doctype.delivery_note.delivery_note import (
			make_installation_note,
			make_sales_invoice,
		)

		install_note = make_installation_note(dn.name)
		install_note.inst_date = nowdate()
		install_note.inst_time = datetime.now().time()
		install_note.submit()
		self.assertEqual(install_note.status, "Submitted", "Installation Note not created")

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"),
			15000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			15000,
		)

		return dn, si

	def test_sales_order_creating_returns_with_installation_note_TC_S_061(self):
		dn, si = self.test_sales_order_creating_si_with_installation_note_TC_S_060()

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		sr = make_sales_return(dn.name)
		sr.save()
		sr.submit()

		self.assertEqual(sr.status, "To Bill", "Sales Return not created")

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 5)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return as make_credit_note

		cn = make_credit_note(si.name)
		cn.save()
		cn.submit()

		self.assertEqual(cn.status, "Return", "Credit Note not created")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"),
			15000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			15000,
		)

	@if_app_installed("india_compliance")
	def test_sales_order_creating_invoice_with_installation_note_and_gst_TC_S_062(self):
		make_item("_Test Item", {"is_stock_item": 1})
		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=5, rate=5000)

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change[0].get("actual_qty"), -5)

		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": dn.name, "account": "Stock In Hand - _TIRC"}, "credit"
			),
			25000,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": dn.name, "account": "Cost of Goods Sold - _TIRC"}, "debit"
			),
			25000,
		)

		from erpnext.stock.doctype.delivery_note.delivery_note import (
			make_installation_note,
			make_sales_invoice,
		)

		install_note = make_installation_note(dn.name)
		install_note.inst_date = nowdate()
		install_note.inst_time = datetime.now().time()
		install_note.submit()
		self.assertEqual(install_note.status, "Submitted", "Installation Note not created")

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TIRC"}, "credit"),
			25000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TIRC"}, "debit"),
			29500,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": si.name, "account": "Output Tax SGST - _TIRC"}, "credit"
			),
			2250,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": si.name, "account": "Output Tax CGST - _TIRC"}, "credit"
			),
			2250,
		)

	@change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_sales_order_for_stock_reservation_TC_S_063(self, reuse=None, get_so_with_stock_reserved=None):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		make_item("_Test Item")
		create_company()
		frappe.db.set_value("Customer Credit Limit", {"parent": "_Test Customer"}, "credit_limit", 0)
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		get_or_create_fiscal_year("_Test Company")
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		stock_setting = frappe.get_doc("Stock Settings")
		stock_setting.enable_stock_resrvation = 1
		stock_setting.save()

		customer = frappe.get_doc("Customer", "_Test Customer")
		if customer:
			customer.credit_limits = []
			customer.save()

		so = self.create_and_submit_sales_order(qty=1, rate=5000)

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			create_stock_reservation_entries_for_so_items,
		)

		item_details = [
			{
				"__checked": 1,
				"sales_order_item": so.items[0].get("name"),
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty_to_reserve": 1,
				"idx": 1,
				"name": "row 1",
			}
		]

		create_stock_reservation_entries_for_so_items(
			sales_order=so,
			items_details=item_details,
			from_voucher_type=None,
			notify=True,
		)

		self.assertEqual(
			frappe.db.get_value("Stock Reservation Entry", {"voucher_no": so.name}, "status"), "Reserved"
		)

		if get_so_with_stock_reserved:
			return so

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -1)

		self.assertEqual(
			frappe.db.get_value("Stock Reservation Entry", {"voucher_no": so.name}, "status"), "Delivered"
		)

		if reuse:
			return dn

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5000,
		)

		return dn, si

	def test_sales_order_for_stock_reservation_with_returns_TC_S_064(self):
		dn, si = self.test_sales_order_for_stock_reservation_TC_S_063()

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		sr = make_sales_return(dn.name)
		sr.save()
		sr.submit()

		self.assertEqual(sr.status, "To Bill", "Sales Return not created")

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 1)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return as make_credit_note

		cn = make_credit_note(si.name)
		cn.save()
		cn.submit()

		self.assertEqual(cn.status, "Return", "Credit Note not created")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5000,
		)

		return si

	@if_app_installed("india_compliance")
	@change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_sales_order_for_stock_reservation_with_gst_TC_S_065(self):
		get_or_create_fiscal_year("_Test Indian Registered Company")
		create_test_warehouse(
			name="Stores - _TIRC", warehouse_name="Stores", company="_Test Indian Registered Company"
		)

		if not frappe.db.exists("Company", "_Test Indian Registered Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Indian Registered Company"
			company.default_currency = "INR"
			company.insert()
		make_stock_entry(
			company="_Test Indian Registered Company",
			item_code="_Test Item",
			qty=20,
			rate=20,
			target="Stores - _TIRC",
		)

		stock_setting = frappe.get_doc("Stock Settings")
		stock_setting.enable_stock_resrvation = 1
		stock_setting.save()

		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=5, rate=20)

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			create_stock_reservation_entries_for_so_items,
		)

		item_details = [
			{
				"__checked": 1,
				"sales_order_item": so.items[0].get("name"),
				"item_code": "_Test Item",
				"warehouse": "Stores - _TIRC",
				"qty_to_reserve": 5,
				"idx": 1,
				"name": "row 1",
			}
		]

		create_stock_reservation_entries_for_so_items(
			sales_order=so,
			items_details=item_details,
			from_voucher_type=None,
			notify=True,
		)

		self.assertEqual(
			frappe.db.get_value("Stock Reservation Entry", {"voucher_no": so.name}, "status"), "Reserved"
		)

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "Stores - _TIRC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change[0].get("actual_qty"), -5)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TIRC"}, "credit"),
			100,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TIRC"}, "debit"),
			118,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": si.name, "account": "Output Tax SGST - _TIRC"}, "credit"
			),
			9,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": si.name, "account": "Output Tax CGST - _TIRC"}, "credit"
			),
			9,
		)

	def test_sales_order_for_stock_reservation_with_installation_note_TC_S_066(self, reuse=None):
		dn = self.test_sales_order_for_stock_reservation_TC_S_063(reuse=1)

		from erpnext.stock.doctype.delivery_note.delivery_note import (
			make_installation_note,
			make_sales_invoice,
		)

		install_note = make_installation_note(dn.name)
		install_note.inst_date = nowdate()
		install_note.inst_time = datetime.now().time()
		install_note.submit()
		self.assertEqual(install_note.status, "Submitted", "Installation Note not created")

		if reuse:
			return dn

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5000,
		)

		return dn, si

	def test_sales_order_for_stock_reservation_with_installation_note_and_return_TC_S_067(self, reuse=None):
		dn = self.test_sales_order_for_stock_reservation_with_installation_note_TC_S_066(reuse=1)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		sr = make_sales_return(dn.name)
		sr.save()
		sr.submit()

		self.assertEqual(sr.status, "To Bill", "Sales Return not created")

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 1)

	def test_sales_order_for_stock_reservation_with_returns_and_note_TC_S_068(self):
		dn, si = self.test_sales_order_for_stock_reservation_TC_S_063()

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		sr = make_sales_return(dn.name)
		sr.save()
		sr.submit()

		self.assertEqual(sr.status, "To Bill", "Sales Return not created")

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 1)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return as make_credit_note

		cn = make_credit_note(si.name)
		cn.save()
		cn.submit()

		self.assertEqual(cn.status, "Return", "Credit Note not created")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5000,
		)

	@change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_sales_order_for_stock_reservation_with_pick_list_TC_S_069(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		make_item("_Test Item", {"is_stock_item": 1})
		get_or_create_fiscal_year("_Test Company")

		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		stock_setting = frappe.get_doc("Stock Settings")
		stock_setting.enable_stock_resrvation = 1
		stock_setting.save()

		so = self.create_and_submit_sales_order(qty=1, rate=5000)

		pick_list = create_pick_list(so.name)
		pick_list.save()
		pick_list.submit()

		self.assertEqual(pick_list.docstatus, 1, "Pick List not created")

		# Creating Stock Reservation Entries for Sales Order Items against Pick List
		so_items_details_map = {}
		for location in pick_list.locations:
			if location.warehouse and location.sales_order and location.sales_order_item:
				item_details = {
					"sales_order_item": location.sales_order_item,
					"item_code": location.item_code,
					"warehouse": location.warehouse,
					"qty_to_reserve": (flt(location.picked_qty) - flt(location.stock_reserved_qty)),
					"from_voucher_no": location.parent,
					"from_voucher_detail_no": location.name,
					"serial_and_batch_bundle": location.serial_and_batch_bundle,
				}
				so_items_details_map.setdefault(location.sales_order, []).append(item_details)

		if so_items_details_map:
			for so, items_details in so_items_details_map.items():
				so_doc = frappe.get_doc("Sales Order", so)
				so_doc.create_stock_reservation_entries(
					items_details=items_details,
					from_voucher_type="Pick List",
					notify=None,
				)

		self.assertEqual(
			frappe.db.get_value("Stock Reservation Entry", {"voucher_no": so_doc.name}, "status"), "Reserved"
		)

		from erpnext.stock.doctype.pick_list.pick_list import create_delivery_note

		dn = create_delivery_note(pick_list.name)
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")
		self.assertEqual(
			frappe.db.get_value("Stock Reservation Entry", {"voucher_no": so_doc.name}, "status"), "Delivered"
		)

		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -1)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5000,
		)

	@change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_sales_order_for_auto_stock_reservation_TC_S_070(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		create_company()
		make_item("_Test Item", {"is_stock_item": 1})
		create_supplier(supplier_name="_Test Supplier")
		get_or_create_fiscal_year("_Test Company")
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")
		frappe.db.set_value("Customer Credit Limit", {"parent": "_Test Customer"}, "credit_limit", 0)

		stock_setting = frappe.get_doc("Stock Settings")
		stock_setting.auto_reserve_stock_for_sales_order_on_purchase = 1
		stock_setting.save()

		so = self.create_and_submit_sales_order(qty=1, rate=5000)

		mr = make_material_request(so.name)
		mr.schedule_date = nowdate()
		for i in mr.items:
			i.cost_center = "Main - _TC"
			i.rate = 5000
		mr.schedule_date = today()
		mr.save()
		mr.submit()

		self.assertEqual(mr.status, "Pending")

		from erpnext.stock.doctype.material_request.material_request import make_purchase_order

		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.cost_center = "Main - _TC"
		po.currency = "INR"
		po.save()
		po.submit()

		self.assertEqual(po.status, "To Receive and Bill")

		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()

		self.assertEqual(pr.status, "To Bill")
		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": pr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, 1)
		self.assertEqual(
			frappe.db.get_value(
				"Stock Reservation Entry", {"voucher_no": so.name, "from_voucher_no": pr.name}, "status"
			),
			"Reserved",
		)

		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		pi = make_purchase_invoice(pr.name)
		pi.save()
		pi.submit()

		self.assertEqual(pi.status, "Unpaid")

		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pi.name, "account": "Creditors - _TC"}, "credit"),
			5000,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_no": pi.name, "account": "_Test Account Cost for Goods Sold - _TC"},
				"debit",
			),
			5000,
		)

	def test_sales_order_for_stock_unreserve_TC_S_071(self):
		so = self.test_sales_order_for_stock_reservation_TC_S_063(get_so_with_stock_reserved=1)

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			cancel_stock_reservation_entries,
		)

		cancel_stock_reservation_entries(
			voucher_type="Sales Order", voucher_no=so.name, sre_list=None, notify=True
		)

		self.assertEqual(
			frappe.db.get_value("Stock Reservation Entry", {"voucher_no": so.name}, "status"), "Cancelled"
		)

	@change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_stock_reservation_entry_on_cancel_TC_S_073(self):
		so = self.test_sales_order_for_stock_reservation_TC_S_063(get_so_with_stock_reserved=1)
		sre = frappe.get_doc("Stock Reservation Entry", {"voucher_no": so.name})
		sre.cancel()
		sre.reload()

		self.assertEqual(sre.status, "Cancelled")

	def test_bulk_stock_reservation_entry_cancel_TC_S_074(self):
		so1 = self.test_sales_order_for_stock_reservation_TC_S_063(get_so_with_stock_reserved=1)
		so2 = self.test_sales_order_for_stock_reservation_TC_S_063(get_so_with_stock_reserved=1)
		so3 = self.test_sales_order_for_stock_reservation_TC_S_063(get_so_with_stock_reserved=1)

		sre1 = frappe.get_doc("Stock Reservation Entry", {"voucher_no": so1.name})
		sre2 = frappe.get_doc("Stock Reservation Entry", {"voucher_no": so2.name})
		sre3 = frappe.get_doc("Stock Reservation Entry", {"voucher_no": so3.name})

		stock_reservation_entries = [sre1.name, sre2.name, sre3.name]

		frappe.get_all(
			"Stock Reservation Entry", filters={"name": ["in", stock_reservation_entries]}, pluck="name"
		)
		for sre in stock_reservation_entries:
			sre_doc = frappe.get_doc("Stock Reservation Entry", sre)
			sre_doc.cancel()
			sre_doc.reload()

		for sre in stock_reservation_entries:
			sre_doc = frappe.get_doc("Stock Reservation Entry", sre)
			self.assertEqual(sre_doc.status, "Cancelled")

	def test_sales_order_purchase_cycle_creating_pi_TC_S_089(self, reuse=None):
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		so = self.create_and_submit_sales_order(qty=1, rate=5000)

		mr = make_material_request(so.name)
		mr.schedule_date = nowdate()
		for i in mr.items:
			i.cost_center = "_Test Cost Center - _TC"
			i.rate = 5000
		mr.save()
		mr.submit()

		self.assertEqual(mr.status, "Pending")
		self.assertEqual(mr.items[0].get("sales_order"), so.name)

		if reuse:
			return so, mr

		from erpnext.stock.doctype.material_request.material_request import make_purchase_order

		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.cost_center = "_Test Cost Center - _TC"
		po.currency = "INR"
		po.save()
		po.submit()

		self.assertEqual(po.status, "To Receive and Bill")
		self.assertEqual(po.items[0].get("sales_order"), so.name)
		self.assertEqual(po.items[0].get("material_request"), mr.name)

		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()

		self.assertEqual(pr.status, "To Bill")
		self.assertEqual(pr.items[0].get("sales_order"), so.name)
		self.assertEqual(pr.items[0].get("material_request"), mr.name)
		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": pr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, 1)

		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		pi = make_purchase_invoice(pr.name)
		pi.save()
		pi.submit()

		self.assertEqual(pi.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pi.name, "account": "Creditors - _TC"}, "credit"),
			5000,
		)

	def test_sales_order_purchase_cycle_creating_pi_via_rfq_TC_S_090(self):
		so, mr = self.test_sales_order_purchase_cycle_creating_pi_TC_S_089(reuse=1)

		from erpnext.stock.doctype.material_request.material_request import make_request_for_quotation

		rfq = make_request_for_quotation(mr.name)
		supplier_data = [
			{
				"supplier": "_Test Supplier",
				"email_id": "123_testrfquser@example.com",
			}
		]
		rfq.append("suppliers", supplier_data[0])
		rfq.message_for_supplier = "Please provide a quotation for the requested items."
		rfq.save()
		rfq.submit()
		self.assertEqual(rfq.items[0].get("material_request"), mr.name)

		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
			make_supplier_quotation_from_rfq,
		)

		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier="_Test Supplier")
		sq.items[0].rate = 2500
		sq.save()
		sq.submit()
		self.assertEqual(sq.status, "Submitted")
		self.assertEqual(sq.items[0].get("material_request"), mr.name)
		self.assertEqual(sq.items[0].get("request_for_quotation"), rfq.name)

		from erpnext.buying.doctype.supplier_quotation.supplier_quotation import make_purchase_order

		po = make_purchase_order(sq.name)
		po.set_warehouse = "Stores - _TC"
		po.items[0].sales_order = so.name
		po.items[0].rate = 2500
		po.save()
		po.submit()

		self.assertEqual(po.status, "To Receive and Bill")
		self.assertEqual(po.items[0].get("sales_order"), so.name)
		self.assertEqual(po.items[0].get("material_request"), mr.name)
		self.assertEqual(po.items[0].get("supplier_quotation"), sq.name)

		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		pr = make_purchase_receipt(po.name)
		pr.items[0].rate = 2500
		pr.save()
		pr.submit()

		self.assertEqual(pr.status, "To Bill")
		self.assertEqual(pr.items[0].get("sales_order"), so.name)
		self.assertEqual(pr.items[0].get("material_request"), mr.name)
		self.assertEqual(pr.items[0].get("purchase_order"), po.name)
		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": pr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, 1)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": pr.name, "account": "_Test Account Excise Duty - _TC"}, "credit"
			),
			2500,
		)

		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		pi = make_purchase_invoice(pr.name)
		pi.save()
		pi.submit()

		self.assertEqual(pi.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pi.name, "account": "Creditors - _TC"}, "credit"),
			2500,
		)

	def test_sales_order_purchase_cycle_creating_pi_via_sq_TC_S_091(self):
		so, mr = self.test_sales_order_purchase_cycle_creating_pi_TC_S_089(reuse=1)

		from erpnext.stock.doctype.material_request.material_request import make_supplier_quotation

		sq = make_supplier_quotation(mr.name)
		sq.supplier = "_Test Supplier"
		sq.currency = "INR"
		sq.save()
		sq.submit()

		self.assertEqual(sq.status, "Submitted")
		self.assertEqual(sq.items[0].get("sales_order"), so.name)
		self.assertEqual(sq.items[0].get("material_request"), mr.name)

		from erpnext.buying.doctype.supplier_quotation.supplier_quotation import make_purchase_order

		po = make_purchase_order(sq.name)
		po.set_warehouse = "Stores - _TC"
		po.save()
		po.submit()

		self.assertEqual(po.status, "To Receive and Bill")
		self.assertEqual(po.items[0].get("sales_order"), so.name)
		self.assertEqual(po.items[0].get("material_request"), mr.name)
		self.assertEqual(po.items[0].get("supplier_quotation"), sq.name)

		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		pr = make_purchase_receipt(po.name)
		pr.save()
		pr.submit()

		self.assertEqual(pr.status, "To Bill")
		self.assertEqual(pr.items[0].get("sales_order"), so.name)
		self.assertEqual(pr.items[0].get("material_request"), mr.name)
		self.assertEqual(pr.items[0].get("purchase_order"), po.name)
		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": pr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, 1)

		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		pi = make_purchase_invoice(pr.name)
		pi.save()
		pi.submit()

		self.assertEqual(pi.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": pi.name, "account": "Creditors - _TC"}, "credit"),
			5000,
		)

	def test_sales_order_delivery_trip_creating_si_TC_S_092(self):
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		so = self.create_and_submit_sales_order(qty=1, rate=5000)

		dn = make_delivery_note(so.name)
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")
		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -1)

		driver, vehicle, add = get_transport_details(customer="_Test Customer")

		from erpnext.stock.doctype.delivery_note.delivery_note import make_delivery_trip

		trip = make_delivery_trip(dn.name)
		trip.driver = driver.name
		trip.vehicle = vehicle.name
		trip.departure_time = frappe.utils.now()
		for i in trip.delivery_stops:
			i.address = add.name
		trip.save()
		trip.submit()

		self.assertEqual(trip.status, "Scheduled")

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()
		si.reload()
		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5000,
		)

		so.reload()
		self.assertEqual(so.per_billed, 100)

		return dn, si

	def test_sales_order_delivery_trip_creating_si_with_returns_TC_S_093(self):
		dn, si = self.test_sales_order_delivery_trip_creating_si_TC_S_092()

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		sr = make_sales_return(dn.name)
		sr.save()
		sr.submit()

		self.assertEqual(sr.status, "To Bill", "Sales Return not created")

		qty_change_return = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": sr.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change_return, 1)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return as make_credit_note

		cn = make_credit_note(si.name)
		cn.save()
		cn.submit()

		self.assertEqual(cn.status, "Return", "Credit Note not created")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"}, "credit"), 5000
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TC"}, "debit"),
			5000,
		)

	@if_app_installed("india_compliance")
	def test_sales_order_delivery_trip_creating_si_with_gst_TC_S_094(self):
		make_item("_Test Item", {"is_stock_item": 1})
		so = self.create_and_submit_sales_order_with_gst("_Test Item", qty=1, rate=5000)

		dn = make_delivery_note(so.name)
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")
		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": dn.name, "warehouse": "Stores - _TIRC", "item_code": "_Test Item"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -1)

		driver, vehicle, add = get_transport_details(customer="_Test Registered Customer")

		from erpnext.stock.doctype.delivery_note.delivery_note import make_delivery_trip

		trip = make_delivery_trip(dn.name)
		trip.driver = driver.name
		trip.vehicle = vehicle.name
		trip.departure_time = frappe.utils.now()
		for i in trip.delivery_stops:
			i.address = add.name
		trip.save()
		trip.submit()

		self.assertEqual(trip.status, "Scheduled")

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(dn.name)
		si.save()
		si.submit()
		si.reload()
		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Sales - _TIRC"}, "credit"),
			5000,
		)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": "Debtors - _TIRC"}, "debit"),
			5900,
		)

		so.reload()
		self.assertEqual(so.per_billed, 100)

	def test_sales_order_delivery_trip_creating_partial_si_TC_S_095(self):
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		so = self.create_and_submit_sales_order(qty=5, rate=5000)

		dn = make_delivery_note(so.name)
		dn.submit()

		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")
		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -5)

		driver, vehicle, add = get_transport_details(customer="_Test Customer")

		from erpnext.stock.doctype.delivery_note.delivery_note import make_delivery_trip

		trip = make_delivery_trip(dn.name)
		trip.driver = driver.name
		trip.vehicle = vehicle.name
		trip.departure_time = frappe.utils.now()
		for i in trip.delivery_stops:
			i.address = add.name
		trip.save()
		trip.submit()

		self.assertEqual(trip.status, "Scheduled")

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si1 = make_sales_invoice(dn.name)
		si1.get("items")[0].qty = 2
		si1.insert()
		si1.submit()

		self.assertEqual(si1.status, "Unpaid", "Sales Invoice not created")

		si1_acc_credit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si1.name, "account": "Sales - _TC"},
			"credit",
		)
		self.assertEqual(si1_acc_credit, 10000)

		si1_acc_debit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si1.name, "account": "Debtors - _TC"},
			"debit",
		)
		self.assertEqual(si1_acc_debit, 10000)

		si2 = make_sales_invoice(dn.name)
		si2.insert()
		si2.submit()

		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")

		si2_acc_credit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si2.name, "account": "Sales - _TC"},
			"credit",
		)
		self.assertEqual(si2_acc_credit, 15000)

		si2_acc_debit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si2.name, "account": "Debtors - _TC"},
			"debit",
		)
		self.assertEqual(si2_acc_debit, 15000)

	@if_app_installed("india_compliance")
	def test_so_with_item_tax_creating_si_with_payment_TC_S_096(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		create_test_tax_data()
		if not frappe.db.exists("Item Tax Template", "GST 5% - _TC"):
			test_item_tax_template(title="GST 5%", gst_rate=5)

		so = make_sales_order(qty=5, rate=4000, do_not_save=True)
		so.tax_category = "In-State"
		so.taxes_and_charges = "Output GST In-state - _TC"
		for i in so.items:
			i.item_tax_template = "GST 5% - _TC"
		so.save()
		so.submit()
		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn = make_delivery_note(so.name)
		dn.submit()
		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")

		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC", "item_code": "_Test Item"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -5)

		si = self.create_and_submit_sales_invoice(dn.name)
		self.assertEqual(si.status, "Unpaid", "Sales Invoice not created")

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": si.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}

		self.assertEqual(gl_debits["Debtors - _TC"], 21000)
		self.assertEqual(gl_credits["Sales - _TC"], 20000)
		self.assertEqual(gl_credits["Output Tax CGST - _TC"], 500)
		self.assertEqual(gl_credits["Output Tax SGST - _TC"], 500)

		self.create_and_submit_payment_entry(dt="Sales Invoice", dn=si.name)
		si.reload()
		self.assertEqual(si.status, "Paid")

	@if_app_installed("india_compliance")
	def test_so_with_item_tax_creating_double_entries_with_1payment_TC_S_097(self):
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		create_test_tax_data()
		if not frappe.db.exists("Item Tax Template", "GST 5% - _TC"):
			test_item_tax_template(title="GST 5%", gst_rate=5)

		so = make_sales_order(qty=4, rate=5000, do_not_save=True)
		so.tax_category = "In-State"
		so.taxes_and_charges = "Output GST In-state - _TC"
		for i in so.items:
			i.item_tax_template = "GST 5% - _TC"
		so.save()
		so.submit()
		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn1 = make_delivery_note(so.name)
		dn1.items[0].qty = 2
		dn1.save()
		dn1.submit()

		self.assertEqual(dn1.status, "To Bill", "Delivery Note not created")
		qty_change1 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn1.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change1[0].get("actual_qty"), -2)

		si1 = self.create_and_submit_sales_invoice(dn1.name)
		self.assertEqual(si1.status, "Unpaid", "Sales Invoice not created")

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": si1.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}

		self.assertEqual(gl_debits["Debtors - _TC"], 10500)
		self.assertEqual(gl_credits["Sales - _TC"], 10000)
		self.assertEqual(gl_credits["Output Tax CGST - _TC"], 250)
		self.assertEqual(gl_credits["Output Tax SGST - _TC"], 250)

		dn2 = make_delivery_note(so.name)
		dn2.save()
		dn2.submit()

		self.assertEqual(dn2.status, "To Bill", "Delivery Note not created")
		qty_change1 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn2.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change1[0].get("actual_qty"), -2)

		si2 = self.create_and_submit_sales_invoice(dn2.name)
		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": si2.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}

		self.assertEqual(gl_debits["Debtors - _TC"], 10500)
		self.assertEqual(gl_credits["Sales - _TC"], 10000)
		self.assertEqual(gl_credits["Output Tax CGST - _TC"], 250)
		self.assertEqual(gl_credits["Output Tax SGST - _TC"], 250)

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

		pe = create_payment_entry(
			payment_type="Receive",
			party_type="Customer",
			party="_Test Customer",
			paid_from="Debtors - _TC",
			paid_to="Cash - _TC",
			paid_amount=si1.grand_total + si2.grand_total,
		)
		pe.append(
			"references",
			{
				"reference_doctype": "Sales Invoice",
				"reference_name": si1.name,
				"total_amount": si1.grand_total,
				"allocated_amount": si1.grand_total,
				"account": "Debtors - _TC",
			},
		)
		pe.append(
			"references",
			{
				"reference_doctype": "Sales Invoice",
				"reference_name": si2.name,
				"total_amount": si2.grand_total,
				"allocated_amount": si2.grand_total,
				"account": "Debtors - _TC",
			},
		)
		pe.save()
		pe.submit()
		si1.reload()
		si2.reload()
		self.assertEqual(si1.status, "Paid")
		self.assertEqual(si2.status, "Paid")
		self.assertEqual(pe.status, "Submitted")

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pe.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}
		total_debtors_credit = sum(
			entry["credit"] for entry in gl_entries if entry["account"] == "Debtors - _TC"
		)
		self.assertEqual(gl_debits["Cash - _TC"], 21000)
		self.assertEqual(total_debtors_credit, 21000)

	@if_app_installed("india_compliance")
	def test_so_with_item_tax_creating_double_entries_with_2payment_TC_S_098(self):
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		create_test_tax_data()
		if not frappe.db.exists("Item Tax Template", "GST 5% - _TC"):
			test_item_tax_template(title="GST 5%", gst_rate=5)

		so = make_sales_order(qty=4, rate=5000, do_not_save=True)
		so.tax_category = "In-State"
		so.taxes_and_charges = "Output GST In-state - _TC"
		for i in so.items:
			i.item_tax_template = "GST 5% - _TC"
		so.save()
		so.submit()
		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		dn1 = make_delivery_note(so.name)
		dn1.items[0].qty = 2
		dn1.save()
		dn1.submit()

		self.assertEqual(dn1.status, "To Bill", "Delivery Note not created")
		qty_change1 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn1.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change1[0].get("actual_qty"), -2)

		si1 = self.create_and_submit_sales_invoice(dn1.name)
		self.assertEqual(si1.status, "Unpaid", "Sales Invoice not created")

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": si1.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}

		self.assertEqual(gl_debits["Debtors - _TC"], 10500)
		self.assertEqual(gl_credits["Sales - _TC"], 10000)
		self.assertEqual(gl_credits["Output Tax CGST - _TC"], 250)
		self.assertEqual(gl_credits["Output Tax SGST - _TC"], 250)

		self.create_and_submit_payment_entry(dt="Sales Invoice", dn=si1.name)
		si1.reload()
		self.assertEqual(si1.status, "Paid")

		dn2 = make_delivery_note(so.name)
		dn2.save()
		dn2.submit()

		self.assertEqual(dn2.status, "To Bill", "Delivery Note not created")
		qty_change1 = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn2.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change1[0].get("actual_qty"), -2)

		si2 = self.create_and_submit_sales_invoice(dn2.name)
		self.assertEqual(si2.status, "Unpaid", "Sales Invoice not created")

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": si2.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}

		self.assertEqual(gl_debits["Debtors - _TC"], 10500)
		self.assertEqual(gl_credits["Sales - _TC"], 10000)
		self.assertEqual(gl_credits["Output Tax CGST - _TC"], 250)
		self.assertEqual(gl_credits["Output Tax SGST - _TC"], 250)

		self.create_and_submit_payment_entry(dt="Sales Invoice", dn=si2.name)
		si2.reload()
		self.assertEqual(si2.status, "Paid")

	def test_so_to_si_with_loyalty_point_creating_payment_TC_S_108(self):
		from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
			get_loyalty_program_details_with_points,
		)
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		make_item("_Test Item", {"is_stock_item": 1})
		get_or_create_fiscal_year("_Test Company")
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		so = make_sales_order(qty=4, rate=5000)

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")

		if not frappe.db.exists("Loyalty Program", "Test Single Loyalty"):
			frappe.get_doc(
				{
					"doctype": "Loyalty Program",
					"loyalty_program_name": "Test Single Loyalty",
					"auto_opt_in": 1,
					"from_date": today(),
					"loyalty_program_type": "Single Tier Program",
					"conversion_factor": 1,
					"expiry_duration": 10,
					"company": "_Test Company",
					"cost_center": "Main - _TC",
					"collection_rules": [
						{"tier_name": "Silver", "collection_factor": 1000, "min_spent": 1000}
					],
				}
			).insert()

		frappe.db.set_value("Customer", "_Test Customer", "loyalty_program", "Test Single Loyalty")
		before_lp_details = get_loyalty_program_details_with_points(
			"_Test Customer", loyalty_program="Test Single Loyalty"
		)

		si = make_sales_invoice(so.name)
		si.redeem_loyalty_points = 1
		si.loyalty_points = before_lp_details.loyalty_points
		si.loyalty_redemption_account = "Cash - _TC"
		si.loyalty_amount = 100
		si.save()
		si.submit()
		self.assertEqual(si.status, "Partly Paid")

		pe = get_payment_entry(dt="Sales Invoice", dn=si.name)
		pe.save()
		pe.submit()
		self.assertEqual(pe.status, "Submitted")
		si.reload()
		self.assertEqual(si.status, "Paid")

	def test_so_to_po_TC_S_109(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order_for_default_supplier

		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		so = make_sales_order(qty=1, rate=5000, do_not_save=True)
		for i in so.items:
			i.delivered_by_supplier = 1
			i.supplier = "_Test Supplier"
		so.save()
		so.submit()
		purchase_orders = make_purchase_order_for_default_supplier(so.name, selected_items=so.items)
		for i in purchase_orders[0].items:
			i.rate = 3000
		purchase_orders[0].submit()

		update_status("Delivered", purchase_orders[0].name)
		so.reload()
		purchase_orders[0].reload()
		self.assertEqual(so.status, "To Bill")
		self.assertEqual(purchase_orders[0].status, "Delivered")

	@if_app_installed("india_compliance")
	def test_so_to_po_with_gst_TC_S_110(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order_for_default_supplier

		create_test_tax_data()
		if not frappe.db.exists("Item Tax Template", "GST 18% - _TC"):
			test_item_tax_template(title="GST 18%")

		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		sales_order = make_sales_order(qty=1, rate=5000, do_not_save=True)
		for i in sales_order.items:
			i.delivered_by_supplier = 1
			i.item_tax_template = "GST 18% - _TC"
			i.supplier = "_Test Supplier"
		sales_order.tax_category = "In-State"
		sales_order.taxes_and_charges = "Output GST In-state - _TC"
		sales_order.save()
		sales_order.submit()

		purchase_orders = make_purchase_order_for_default_supplier(
			sales_order.name, selected_items=sales_order.items
		)
		for i in purchase_orders[0].items:
			i.rate = 3000
			i.item_tax_template = "GST 18% - _TC"
		purchase_orders[0].tax_category = "In-State"
		purchase_orders[0].taxes_and_charges = "Input GST In-state - _TC"
		purchase_orders[0].save()
		purchase_orders[0].submit()
		self.assertEqual(purchase_orders[0].grand_total, 3540)
		update_status("Delivered", purchase_orders[0].name)
		sales_order.reload()
		purchase_orders[0].reload()
		self.assertEqual(sales_order.status, "To Bill")
		self.assertEqual(purchase_orders[0].status, "Delivered")

	def test_so_to_si_with_po_TC_S_113(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import (
			make_purchase_invoice as make_pi_from_po,
		)
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order_for_default_supplier

		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		so = make_sales_order(qty=1, rate=5000, do_not_save=True)
		so.ignore_pricing_rule = 0
		for i in so.items:
			i.delivered_by_supplier = 1
			i.supplier = "_Test Supplier"
		so.save()
		so.submit()
		purchase_orders = make_purchase_order_for_default_supplier(so.name, selected_items=so.items)
		for i in purchase_orders[0].items:
			i.rate = 3000
		purchase_orders[0].currency = "INR"
		purchase_orders[0].submit()

		update_status("Delivered", purchase_orders[0].name)
		so.reload()
		purchase_orders[0].reload()
		self.assertEqual(so.status, "To Bill")
		self.assertEqual(purchase_orders[0].status, "Delivered")

		pi = make_pi_from_po(purchase_orders[0].name)
		pi.insert(ignore_permissions=True)
		pi.submit()

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}
		self.assertEqual(gl_debits["_Test Account Cost for Goods Sold - _TC"], 3000)
		self.assertEqual(gl_credits["Creditors - _TC"], 3000)

		si = make_sales_invoice(so.name)
		si.save()
		si.submit()

		gl_entries_si = frappe.get_all(
			"GL Entry", filters={"voucher_no": si.name}, fields=["account", "debit", "credit"]
		)
		gl_debits_si = {entry.account: entry.debit for entry in gl_entries_si}
		gl_credits_si = {entry.account: entry.credit for entry in gl_entries_si}
		self.assertEqual(gl_debits_si["Debtors - _TC"], 5000)
		self.assertEqual(gl_credits_si["Sales - _TC"], 5000)
		so.reload()
		self.assertEqual(so.status, "Completed")
		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(pi.status, "Unpaid")

	@if_app_installed("india_compliance")
	def test_so_to_si_with_po_with_gst_TC_S_115(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import (
			make_purchase_invoice as make_pi_from_po,
		)
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order_for_default_supplier

		create_test_tax_data()
		if not frappe.db.exists("Item Tax Template", "GST 18% - _TC"):
			test_item_tax_template(title="GST 18%")

		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		sales_order = make_sales_order(qty=1, rate=5000, do_not_save=True)
		for i in sales_order.items:
			i.delivered_by_supplier = 1
			i.item_tax_template = "GST 18% - _TC"
			i.supplier = "_Test Supplier"
		sales_order.tax_category = "In-State"
		sales_order.taxes_and_charges = "Output GST In-state - _TC"
		sales_order.save()
		sales_order.submit()
		purchase_orders = make_purchase_order_for_default_supplier(
			sales_order.name, selected_items=sales_order.items
		)
		for i in purchase_orders[0].items:
			i.rate = 3000
			i.item_tax_template = "GST 18% - _TC"
		purchase_orders[0].currency = "INR"
		purchase_orders[0].tax_category = "In-State"
		purchase_orders[0].taxes_and_charges = "Input GST In-state - _TC"
		purchase_orders[0].save()
		purchase_orders[0].submit()

		self.assertEqual(purchase_orders[0].grand_total, 3540)
		update_status("Delivered", purchase_orders[0].name)
		sales_order.reload()
		purchase_orders[0].reload()
		self.assertEqual(sales_order.status, "To Bill")
		self.assertEqual(purchase_orders[0].status, "Delivered")

		pi = make_pi_from_po(purchase_orders[0].name)
		pi.insert(ignore_permissions=True)
		pi.submit()

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}
		self.assertEqual(gl_debits["_Test Account Cost for Goods Sold - _TC"], 3000)
		self.assertEqual(gl_credits["Creditors - _TC"], 3540)

		si = make_sales_invoice(sales_order.name)
		si.save()
		si.submit()

		gl_entries_si = frappe.get_all(
			"GL Entry", filters={"voucher_no": si.name}, fields=["account", "debit", "credit"]
		)
		gl_debits_si = {entry.account: entry.debit for entry in gl_entries_si}
		gl_credits_si = {entry.account: entry.credit for entry in gl_entries_si}
		self.assertEqual(gl_debits_si["Debtors - _TC"], 5900)
		self.assertEqual(gl_credits_si["Sales - _TC"], 5000)
		self.assertEqual(gl_credits_si["Output Tax CGST - _TC"], 450)
		self.assertEqual(gl_credits_si["Output Tax SGST - _TC"], 450)
		sales_order.reload()
		self.assertEqual(sales_order.status, "Completed")
		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(pi.status, "Unpaid")

	def test_so_cancel_amend_with_qty_change_TC_S_126(self):
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		sales_order = make_sales_order(qty=1, rate=5000)
		sales_order.save()
		sales_order.submit()

		self.assertEqual(sales_order.status, "To Deliver and Bill")

		sales_order.cancel()
		sales_order.reload()
		self.assertEqual(sales_order.status, "Cancelled")

		amended_so = frappe.copy_doc(sales_order)
		amended_so.docstatus = 0
		amended_so.amended_from = sales_order.name
		amended_so.items[0].qty = 2
		amended_so.save()
		amended_so.submit()

		self.assertEqual(amended_so.status, "To Deliver and Bill")

	def test_so_cancel_amend_with_rate_change_TC_S_127(self):
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="_Test Warehouse - _TC")

		sales_order = make_sales_order(qty=1, rate=5000)
		sales_order.save()
		sales_order.submit()

		self.assertEqual(sales_order.status, "To Deliver and Bill")

		sales_order.cancel()
		sales_order.reload()
		self.assertEqual(sales_order.status, "Cancelled")

		amended_so = frappe.copy_doc(sales_order)
		amended_so.docstatus = 0
		amended_so.amended_from = sales_order.name
		amended_so.items[0].rate = 3000
		amended_so.save()
		amended_so.submit()

		self.assertEqual(amended_so.status, "To Deliver and Bill")

	def test_sales_order_with_product_bundle_TC_SCK_133(self):
		make_item("_Test Door", properties={"is_stock_item": 0})
		item2 = make_item("_Test Door Handle Set")
		item3 = make_item("_Test Door Stopper")
		item4 = make_item("_Test Door Tower Bolt")
		make_stock_entry(item_code=item2.item_code, qty=10, rate=100, target="_Test Warehouse - _TC")
		make_stock_entry(item_code=item3.item_code, qty=10, rate=100, target="_Test Warehouse - _TC")
		make_stock_entry(item_code=item4.item_code, qty=10, rate=100, target="_Test Warehouse - _TC")
		# Create Product Bundle
		product_bundle = make_product_bundle(
			"_Test Door", ["_Test Door Handle Set", "_Test Door Stopper", "_Test Door Tower Bolt"]
		)
		product_bundle.save()
		product_bundle.submit()

		# Create Sales Order
		sales_order = make_sales_order(
			item_code="_Test Door",
			qty=1,
			rate=5000,
			do_not_save=True,
		)
		sales_order.delivery_date = nowdate()
		sales_order.save()
		sales_order.submit()
		self.assertEqual(sales_order.status, "To Deliver and Bill")

		# Create Delivery Note from Sales Order
		delivery_note = make_delivery_note(sales_order.name)
		delivery_note.save()
		delivery_note.submit()
		self.assertEqual(delivery_note.status, "To Bill")

		# Check Stock Ledger Entries for sub-items
		for item_code in ["_Test Door Handle Set", "_Test Door Stopper", "_Test Door Tower Bolt"]:
			qty_change = frappe.db.get_value(
				"Stock Ledger Entry",
				{
					"voucher_no": delivery_note.name,
					"warehouse": "_Test Warehouse - _TC",
					"item_code": item_code,
				},
				"actual_qty",
			)
			self.assertEqual(qty_change, -1)

	def test_so_to_si_with_deferred_revenue_item_TC_S_134(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		item = make_test_item("_Test Item 1")
		item.enable_deferred_revenue = 1
		item.is_stock_item = 1
		item.no_of_months = 5
		item.save()

		make_stock_entry(item_code="_Test Item 1", qty=10, rate=5000, target="_Test Warehouse - _TC")

		sales_order = make_sales_order(item="_Test Item 1", qty=1, rate=5000)
		sales_order.save()
		sales_order.submit()
		self.assertEqual(sales_order.status, "To Deliver and Bill")

		deferred_account = create_account(
			account_name="Deferred Revenue",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
		)
		si = make_sales_invoice(sales_order.name)
		si.items[0].enable_deferred_revenue = 1
		si.items[0].deferred_revenue_account = deferred_account
		si.save()
		si.submit()
		self.assertEqual(si.status, "Unpaid")

	def test_so_to_si_with_manual_discount_grand_total_TC_S_136(self):
		make_stock_entry(item_code="_Test Item", qty=10, rate=100, target="_Test Warehouse - _TC")
		so = make_sales_order(qty=10, rate=100)
		self.assertEqual(so.status, "To Deliver and Bill")

		si = make_sales_invoice(so.name)

		self.assertEqual(si.grand_total, 1000)
		si.apply_discount_on = "Grand Total"
		si.additional_discount_percentage = 10
		si.save()
		si.submit()
		self.assertEqual(si.grand_total, 900)
		self.assertEqual(si.status, "Unpaid")

	def test_so_to_si_with_manual_discount_net_total_TC_S_137(self):
		make_stock_entry(item_code="_Test Item", qty=10, rate=100, target="_Test Warehouse - _TC")
		so = make_sales_order(qty=10, rate=100)
		self.assertEqual(so.status, "To Deliver and Bill")

		si = make_sales_invoice(so.name)

		self.assertEqual(si.grand_total, 1000)
		si.apply_discount_on = "Net Total"
		si.additional_discount_percentage = 10
		si.save()
		si.submit()
		self.assertEqual(si.grand_total, 900)

	@if_app_installed("sales_commission")
	def test_so_with_maintenance_visit_TC_S_138(self):
		from erpnext.maintenance.doctype.maintenance_visit.test_maintenance_visit import make_sales_person
		from erpnext.selling.doctype.sales_order.sales_order import make_maintenance_visit

		item = make_item("_Test Item 3")
		item.is_stock_item = 0
		item.save()
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "_Test Address for Customer",
				"address_type": "Office",
				"address_line1": "Station Road",
				"city": "_Test City",
				"state": "Tamil Nadu",
				"country": "India",
				"links": [{"link_doctype": "Customer", "link_name": "_Test Customer"}],
			}
		).insert()

		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "_Test Contact for _Test Customer",
				"links": [{"link_doctype": "Customer", "link_name": "_Test Customer"}],
			}
		)
		contact.add_email("test_contact_customer@example.com", is_primary=True)
		contact.add_phone("+91 0000000000", is_primary_phone=True)
		contact.insert()

		frappe.db.set_value("Customer", "_Test Customer", "customer_primary_address", address.name)
		frappe.db.set_value("Customer", "_Test Customer", "customer_primary_contact", contact.name)

		sales_order = make_sales_order(item_code="_Test Item 3", qty=1, rate=5000)
		sales_order.save()
		sales_order.submit()
		self.assertEqual(sales_order.status, "To Deliver and Bill")

		if not frappe.db.exists("Sales Person", "_Test Sales Person"):
			make_sales_person("_Test Sales Person")

		mv = make_maintenance_visit(sales_order.name)
		mv.completion_status = "Fully Completed"
		mv.maintenance_type = "Scheduled"
		mv.purposes[0].service_person = "_Test Sales Person"
		mv.purposes[0].work_done = "Test Work Done"
		mv.customer_feedback = "Test Maintenance Visit "
		mv.save()
		mv.submit()

		self.assertEqual(mv.completion_status, "Fully Completed")

		si = make_sales_invoice(sales_order.name)
		si.save()
		si.submit()
		self.assertEqual(si.status, "Unpaid")

	def test_discount_in_si_apply_in_net_total_TS_S_148(self):
		make_stock_entry(item_code="_Test Item", qty=10, rate=100, target="_Test Warehouse - _TC")
		sales_order = make_sales_order(qty=1, rate=5000)
		sales_order.save()
		sales_order.submit()
		self.assertEqual(sales_order.status, "To Deliver and Bill")

		delivery_note = make_delivery_note(sales_order.name)
		delivery_note.save()
		delivery_note.submit()
		self.assertEqual(delivery_note.status, "To Bill")

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		sales_invoice = make_sales_invoice(delivery_note.name)
		sales_invoice.apply_discount_on = "Net Total"
		sales_invoice.discount_amount = 1000
		sales_invoice.save()
		sales_invoice.submit()
		self.assertEqual(sales_invoice.status, "Unpaid")

	def test_discount_in_si_apply_in_grand_total_TS_S_149(self):
		make_stock_entry(item_code="_Test Item", qty=10, rate=100, target="_Test Warehouse - _TC")
		sales_order = make_sales_order(qty=1, rate=5000)
		sales_order.save()
		sales_order.submit()
		self.assertEqual(sales_order.status, "To Deliver and Bill")

		delivery_note = make_delivery_note(sales_order.name)
		delivery_note.save()
		delivery_note.submit()
		self.assertEqual(delivery_note.status, "To Bill")

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		sales_invoice = make_sales_invoice(delivery_note.name)
		sales_invoice.apply_discount_on = "Grand Total"
		sales_invoice.discount_amount = 1000
		sales_invoice.save()
		sales_invoice.submit()
		self.assertEqual(sales_invoice.status, "Unpaid")

	def test_discount_in_dn_apply_in_net_total_TS_S_150(self):
		make_stock_entry(item_code="_Test Item", qty=10, rate=100, target="_Test Warehouse - _TC")
		sales_order = make_sales_order(qty=1, rate=5000)
		sales_order.save()
		sales_order.submit()
		self.assertEqual(sales_order.status, "To Deliver and Bill")

		sales_invoice = make_sales_invoice(sales_order.name)
		sales_invoice.save()
		sales_invoice.submit()
		self.assertEqual(sales_invoice.status, "Unpaid")

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

		delivery_note = make_delivery_note(sales_invoice.name)
		delivery_note.apply_discount_on = "Net Total"
		delivery_note.discount_amount = 1000
		delivery_note.save()
		delivery_note.submit()

		self.assertEqual(delivery_note.status, "Completed")

	def test_discount_in_dn_apply_in_grand_total_TS_S_151(self):
		make_stock_entry(item_code="_Test Item", qty=10, rate=100, target="_Test Warehouse - _TC")
		sales_order = make_sales_order(qty=1, rate=5000)
		sales_order.save()
		sales_order.submit()
		self.assertEqual(sales_order.status, "To Deliver and Bill")

		sales_invoice = make_sales_invoice(sales_order.name)
		sales_invoice.save()
		sales_invoice.submit()
		self.assertEqual(sales_invoice.status, "Unpaid")

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

		delivery_note = make_delivery_note(sales_invoice.name)
		delivery_note.apply_discount_on = "Grand Total"
		delivery_note.discount_amount = 1000
		delivery_note.save()
		delivery_note.submit()

		self.assertEqual(delivery_note.status, "Completed")

	@change_settings("Selling Settings", {"hide_tax_id": 1})
	def test_sales_order_to_show_customer_tax_id_TC_S_160(self):
		customer = frappe.get_doc("Customer", "_Test Customer")
		customer.tax_id = "ABC12345"
		customer.save()

		def is_field_hidden(doctype, fieldname):
			meta = frappe.get_meta(doctype)
			field = meta.get_field(fieldname)

			if field:
				return field.hidden
			return None

		self.assertEqual(is_field_hidden("Sales Order", "tax_id"), 1)

	def create_and_submit_sales_order(self, qty=None, rate=None):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_customer

		customer = create_customer("_Test Customer 1", currency="INR")
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=100, rate=500, target="_Test Warehouse - _TC")
		sales_order = make_sales_order(
			customer=customer,
			cost_center="Main - _TC",
			selling_price_list="_Test Price List",
			do_not_save=True,
		)
		sales_order.delivery_date = nowdate()
		if qty and rate:
			for item in sales_order.items:
				item.qty = qty
				item.rate = rate
			sales_order.save()
		else:
			for item in sales_order.items:
				item.qty = qty
			sales_order.save()
		sales_order.submit()
		self.assertEqual(sales_order.status, "To Deliver and Bill")
		return sales_order

	def create_and_submit_sales_order_with_gst(self, item_code, qty=None, rate=None):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_registered_company

		create_registered_company()
		create_registered_customer()
		create_registered_address_for_gst_entities()
		get_or_create_fiscal_year("_Test Indian Registered Company")
		create_test_warehouse(
			name="Stores - _TIRC", warehouse_name="Stores", company="_Test Indian Registered Company"
		)
		make_item("_Test Item", {"is_stock_item": 1})
		make_stock_entry(item_code="_Test Item", qty=10, rate=rate, target="Stores - _TIRC")

		company = get_gst_details("Company", {"name": "_Test Indian Registered Company"})[0]
		customer = get_gst_details("Customer", {"name": "_Test Registered Customer"})[0]
		company_add = get_gst_details("Address", {"name": "_Test Indian Registered Company-Billing"})[0]
		customer_add = get_gst_details("Address", {"name": "_Test Registered Customer-Billing"})[0]

		if not (
			is_registered_regular(company)
			and is_registered_regular(customer)
			and is_registered_regular(company_add)
			and is_registered_regular(customer_add)
		):
			self.fail("GST details are not properly configured")
		customer = frappe.get_doc("Customer", "_Test Registered Customer")
		if customer:
			customer.credit_limits = []
			customer.save()
		so = make_sales_order(
			company="_Test Indian Registered Company",
			customer="_Test Registered Customer",
			warehouse="Stores - _TIRC",
			cost_center="Main - _TIRC",
			currency="INR",
			item_code=item_code,
			qty=qty,
			rate=rate,
			do_not_save=True,
		)
		so.tax_category = "In-State"
		so.taxes_and_charges = "Output GST In-state - _TIRC"
		so.customer_address = customer_add.get("name")
		so.billing_address_gstin = customer_add.get("gstin")
		so.company_address = company_add.get("name")
		so.company_gstin = company.get("gstin")
		for i in so.items:
			i.gst_hsn_code = "01011020"
		so.save()
		so.submit()

		self.assertEqual(so.status, "To Deliver and Bill", "Sales Order not created")
		self.assertEqual(so.grand_total, so.total + so.total_taxes_and_charges)

		return so

	def create_and_submit_sales_invoice(
		self, delivery_note_name, qty=None, expected_amount=None, advances_automatically=None
	):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		sales_invoice = make_sales_invoice(delivery_note_name)
		sales_invoice.insert()
		if qty:
			for item in sales_invoice.items:
				item.qty = qty

		if advances_automatically:
			sales_invoice.allocate_advances_automatically = 1
			sales_invoice.only_include_allocated_payments = 1
		sales_invoice.save()
		sales_invoice.submit()
		if expected_amount:
			self.validate_gl_entries(sales_invoice.name, expected_amount)
		return sales_invoice

	def create_and_submit_payment_entry(self, dt=None, dn=None, amt=None):
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		payment_entry = get_payment_entry(dt=dt, dn=dn)
		payment_entry.insert()
		if amt:
			payment_entry.paid_amount = amt
			for i in payment_entry.references:
				i.allocated_amount = amt
		payment_entry.save()
		payment_entry.submit()

		self.assertEqual(payment_entry.status, "Submitted", "Payment Entry not created")
		debit_account = (
			frappe.db.get_value("Company", "_Test Company", "default_bank_account") or "Cash - _TC"
		)
		credit_account = (
			frappe.db.get_value("Company", "_Test Company", "default_advance_received_account")
			or "Debtors - _TC"
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": payment_entry.name, "account": credit_account}, "credit"
			),
			payment_entry.paid_amount,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": payment_entry.name, "account": debit_account}, "debit"
			),
			payment_entry.paid_amount,
		)
		return payment_entry

	def validate_gl_entries(self, voucher_no, amount):
		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": voucher_no}, fields=["account", "debit", "credit"]
		)

		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}

		total_debits = sum(gl_debits.values())
		total_credits = sum(gl_credits.values())

		self.assertAlmostEqual(total_debits, amount)
		self.assertAlmostEqual(total_credits, amount)

	def create_and_validate_delivery_note(self, sales_order_name, expected_amount):
		delivery_note = make_delivery_note(sales_order_name)
		delivery_note.submit()

		self.assertEqual(delivery_note.status, "To Bill", "Delivery Note not created")
		stock_ledger_entry = frappe.get_all(
			"Stock Ledger Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": delivery_note.name,
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "_Test Item",
			},
			["valuation_rate", "actual_qty"],
		)
		self.assertEqual(stock_ledger_entry[0].get("actual_qty"), expected_amount)

		return delivery_note

	@change_settings("Accounts Settings", {"credit_controller": "Administrator"})
	def test_unlink_advance_payment_on_order_cancellation_TC_ACC_127(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		account_setting = frappe.get_doc("Accounts Settings")
		account_setting.unlink_advance_payment_on_cancelation_of_order = 0
		account_setting.save()

		item = make_item("_Test Item")
		so = make_sales_order(
			customer="_Test Customer",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
		)
		pe = get_payment_entry("Sales Order", so.name, bank_account="Cash - _TC")
		pe.submit()

		with self.assertRaises(frappe.LinkExistsError):
			so.load_from_db()
			so.cancel()

	def test_customer_credit_limit_bypass_TC_ACC_139(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		if frappe.session.user != "Administrator":
			account_setting = frappe.get_doc("Accounts Settings")
			account_setting.credit_controller = "Sales Manager"
			account_setting.save()
		customer = frappe.get_doc("Customer", "_Test Customer")
		if len(customer.credit_limits) == 0:
			customer.append("credit_limits", {"company": "_Test Company", "credit_limit": 1000})
			customer.flags.ignore_validate = True
			customer.save()
			item = make_test_item("_Test Item")

		try:
			sales_order = make_sales_order(
				customer="_Test Customer",
				company="_Test Company",
				item_code=item.name,
				qty=1,
				rate=1100,
				do_not_submit=True,
			)
			sales_order.load_from_db()
			sales_order.submit()
			self.assertRaises(frappe.ValidationError, sales_order.submit)
			customer.credit_limits = []
			customer.save()
			frappe.db.rollback()
		except Exception:
			pass

	@change_settings("Accounts Settings", {"over_billing_allowance": 25})
	@change_settings("Stock Settings", {"over_delivery_receipt_allowance": 25})
	def test_sales_order_and_delivery_TC_SCK_182(self):
		from datetime import datetime, timedelta

		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		customer = frappe.new_doc("Customer")
		customer.customer_name = "Test Customer 1"
		customer.insert()
		item_fields = {
			"item_name": "_Test Book",
			"is_stock_item": 1,
			"valuation_rate": 100,
		}
		item = make_item("_Test Book", item_fields)
		today = datetime.today().date()  # Get today's date
		delivery_date = today + timedelta(days=10)  # Add 10 days
		make_stock_entry(
			item_code=item.name,
			to_warehouse=create_warehouse("_Test Stores", company="_Test Company"),
			qty=20,
			purpose="Material Receipt",
		)

		sales_order = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": customer.name,
				"delivery_date": delivery_date,
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
		sales_order.insert()
		sales_order.submit()

		sales_order_item = sales_order.items[0].name

		# Create Delivery Note from Sales Order
		delivery_note = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"customer": customer.name,
				"company": "_Test Company",
				"items": [
					{
						"item_code": item.name,
						"qty": 10,  # Over-billed qty (within 20% limit)
						"rate": 10,
						"warehouse": create_warehouse("_Test Stores", company="_Test Company"),
						"against_sales_order": sales_order.name,
						"so_detail": sales_order_item,
					}
				],
			}
		)
		delivery_note.insert()
		delivery_note.submit()

		# Check Stock Ledger
		stock_ledger_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": delivery_note.name},
			fields=["actual_qty", "warehouse"],
		)

		self.assertTrue(
			any(
				entry["actual_qty"] == -10 and entry["warehouse"] == "_Test Stores - _TC"
				for entry in stock_ledger_entries
			),
			"Stock Ledger did not update correctly",
		)

	@change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_stock_reservation_from_so_to_dn_TC_SCK_143(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		create_company()
		customer = create_customer("_Test Customer 1")

		make_item("_Test Item", {"is_stock_item": 1})
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		get_or_create_fiscal_year("_Test Company")
		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=10, basic_rate=100)
		so = make_sales_order(customer=customer, item_code="_Test Item", qty=5, do_not_save=True)
		so.reserve_stock = 1
		so.items[0].reserve_stock = 1
		so.save()
		so.submit()
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			create_stock_reservation_entries_for_so_items,
		)

		item_details = [
			{
				"__checked": 1,
				"sales_order_item": so.items[0].get("name"),
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty_to_reserve": 5,
				"idx": 1,
				"name": "row 1",
			}
		]

		create_stock_reservation_entries_for_so_items(
			sales_order=so,
			items_details=item_details,
			from_voucher_type=None,
			notify=True,
		)

		self.assertEqual(
			frappe.db.get_value("Stock Reservation Entry", {"voucher_no": so.name}, "status"), "Reserved"
		)
		self.assertEqual(
			frappe.db.get_value("Stock Reservation Entry", {"voucher_no": so.name}, "reserved_qty"), 5
		)
		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()
		self.assertEqual(dn.status, "To Bill", "Delivery Note not created")
		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -5)
		self.assertEqual(
			frappe.db.get_value("Stock Reservation Entry", {"voucher_no": so.name}, "status"), "Delivered"
		)

	def test_validate_sales_mntc_quotation_coverage_TC_S_162(self):
		make_item("_Test Item")
		create_exchange_rate(date=today())

		# creating quotation
		qtn = frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Customer",
				"party_name": "_Test Customer",
				"order_type": "Sales",
				"transaction_date": nowdate(),
				"valid_till": add_months(nowdate(), 1),
			}
		)
		qtn.append("items", {"qty": "2", "item_code": "_Test Item"})
		qtn.submit()

		so = frappe.new_doc("Sales Order")
		so.customer = "_Test Customer"
		so.order_type = "Maintenance"
		so.append("items", {"item_code": "_Test Item", "qty": 1, "rate": 100, "prevdoc_docname": qtn.name})

		with self.assertRaises(frappe.ValidationError) as context:
			so.validate_sales_mntc_quotation()

		self.assertIn(f"Quotation {qtn.name} not of type Maintenance", str(context.exception))

	def test_validate_drop_ship_coverage_TC_S_163(self):
		so = frappe.new_doc("Sales Order")
		so.customer = "_Test Customer"
		so.order_type = "Sales"

		so.append(
			"items",
			{"item_code": "_Test Item", "qty": 1, "rate": 100, "delivered_by_supplier": 1, "supplier": None},
		)

		with self.assertRaises(frappe.ValidationError) as context:
			so.validate_drop_ship()

		self.assertIn("Set Supplier for item", str(context.exception))

	def test_check_modified_date_coverage_TC_S_164(self):
		make_item("_Test Item")

		so = make_sales_order(do_not_save=True)
		so.modified = add_to_date(today(), hours=-1)
		so.save()

		frappe.db.set_value("Sales Order", so.name, "modified", today())

		with self.assertRaises(frappe.ValidationError) as e:
			so.update_status("Draft")

		self.assertIn("has been modified", str(e.exception))

	def test_update_status_coverage_TC_S_165(self):
		make_item("_Test Item")

		so = make_sales_order()
		so.reload()

		so.check_credit_limit = lambda: None
		so.update_reserved_qty = lambda: None
		so.notify_update = lambda: None

		try:
			so.update_status("Draft")
		except Exception:
			self.fail("update_status() raised Exception unexpectedly!")

	def test_validate_delivery_date_coverage_TC_S_166(self):
		make_item("_Test Item")

		so = make_sales_order(do_not_save=1)
		so.delivery_date = add_days(so.transaction_date, -1)
		so.items[0].delivery_date = add_days(so.transaction_date, -1)

		with self.assertRaises(frappe.ValidationError) as e:
			so.validate_delivery_date()

		self.assertIn("Expected Delivery Date should be after Sales Order Date", str(e.exception))

	def test_update_enquiry_status_coverage_TC_S_167(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer

		create_company()
		create_customer("_Test Customer")
		make_item("_Test Item")
		create_exchange_rate(date=today())

		if not frappe.db.exists("Opportunity Type", "Sales"):
			opp_type = frappe.new_doc("Opportunity Type")
			opp_type.name = "Sales"
			opp_type.save()

		if not frappe.db.exists("Sales Stage", "Prospecting"):
			sal_stage = frappe.new_doc("Sales Stage")
			sal_stage.stage_name = "Prospecting"
			sal_stage.save()

		opp_doc = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"company": "_Test Company",
				"opportunity_from": "Customer",
				"opportunity_type": "Sales",
				"conversion_rate": 1.0,
				"transaction_date": today(),
				"party_name": "_Test Customer",
			}
		)
		opp_doc.insert()

		quotation = frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Customer",
				"company": "_Test Company",
				"party_name": "_Test Customer",
				"order_type": "Sales",
				"items": [
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 100,
						"prevdoc_doctype": "Opportunity",
						"prevdoc_docname": opp_doc.name,
					}
				],
			}
		).insert()
		quotation.submit()

		so = make_sales_order(do_not_save=1)
		so.update_enquiry_status(quotation.name, "Converted")

		opp_doc.reload()
		self.assertEqual(opp_doc.status, "Converted")

		quotation.cancel()

		so_c = frappe.new_doc("Sales Order")
		so_c.customer = "_Test Customer"
		so_c.order_type = "Maintenance"
		so_c.append(
			"items", {"item_code": "_Test Item", "qty": 1, "rate": 100, "prevdoc_docname": quotation.name}
		)

		with self.assertRaises(frappe.ValidationError) as context:
			so_c.update_prevdoc_status()

		self.assertIn(f"Quotation {quotation.name} is cancelled", str(context.exception))

	@change_settings("Selling Settings", {"allow_against_multiple_purchase_orders": 0})
	def test_validate_po_coverage_TC_S_168(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		create_company()
		create_customer("_Test Customer")
		make_item("_Test Item")
		create_supplier(supplier_name="_Test Supplier")

		po = create_purchase_order()

		invalid_delivery_date = add_days(po.transaction_date, -1)

		so1 = make_sales_order(do_not_save=1)
		so1.po_no = po.name
		so1.po_date = po.transaction_date
		so1.items[0].delivery_date = invalid_delivery_date

		with self.assertRaises(frappe.ValidationError) as ctx1:
			so1.validate_po()
		self.assertIn("Expected Delivery Date cannot be before Purchase Order Date", str(ctx1.exception))

		# so1.items[0].delivery_date = po.transaction_date

		# so2 = make_sales_order(do_not_save=1)
		# so2.po_no = po.name
		# so2.po_date = po.transaction_date
		# so2.save()
		# so2.submit()

		# with self.assertRaises(frappe.ValidationError) as ctx2:
		# 	so1.validate_po()
		# self.assertIn("already exists against Customer's Purchase Order", str(ctx2.exception))

	def test_cannot_cancel_closed_so_TC_S_169(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer

		create_company()
		create_customer("_Test Customer")
		make_item("_Test Item")

		so = make_sales_order()

		so.db_set("status", "Closed")
		so.reload()

		with self.assertRaises(frappe.ValidationError) as context:
			so.cancel()

		self.assertIn("Closed order cannot be cancelled", str(context.exception))

	def test_update_coupon_code_count_on_cancel_TC_S_173(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer

		create_company()
		create_customer("_Test Customer")
		make_item("_Test Item")
		pricing_rule = make_pricing_rule()
		pricing_rule.coupon_code_based = 1
		pricing_rule.save()

		frappe.delete_doc_if_exists("Coupon Code", "SAVE30")

		coupon_code = frappe.get_doc(
			{
				"doctype": "Coupon Code",
				"coupon_type": "Gift Card",
				"customer": "_Test Customer",
				"coupon_name": "SAVE30",
				"coupon_code": "SAVE30",
				"pricing_rule": pricing_rule.name,
				"maximum_use": 1,
				"used": 0,
			}
		)
		coupon_code.insert()

		so = make_sales_order(do_not_submit=True)
		so.coupon_code = coupon_code.name
		so.save()

		so.on_submit()
		self.assertEqual(frappe.db.get_value("Coupon Code", "SAVE30", "used"), 1)

		so.on_cancel()
		self.assertEqual(frappe.db.get_value("Coupon Code", "SAVE30", "used"), 0)

		self.assertEqual(coupon_code.used, 0)

	@change_settings("Stock Settings", {"over_picking_allowance": 10.0})
	def test_update_picking_status_coverage_TC_S_174(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer

		create_company()
		create_customer("_Test Customer")
		make_item("_Test Item")

		so = make_sales_order(do_not_submit=True)
		so.items[0].picked_qty = 10.0
		so.save().submit()

		so.update_picking_status()

		self.assertEqual(so.items[0].picked_qty + 1, 11.0)

	@change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_onload_coverage_TC_S_175(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		create_company()
		create_customer("_Test Customer")
		make_item("_Test Item")
		get_or_create_fiscal_year("_Test Company")
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)

		so = make_sales_order()
		so.onload()

		has_unreserved_stock = so.has_unreserved_stock()
		self.assertEqual(has_unreserved_stock, True)

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import has_reserved_stock

		reserved_stock = has_reserved_stock(so.doctype, so.name)
		self.assertEqual(reserved_stock, False)

	def test_validate_supplier_after_submit_coverage_TC_S_176(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		create_company()
		create_customer("_Test Customer")
		make_item("_Test Item")
		create_supplier(supplier_name="_Test Supplier")
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)

		so = make_sales_order(do_not_save=1)
		so.items[0].ordered_qty = 3
		so.save().submit()

		so.reload()
		so.items[0].supplier = "_Test Supplier"

		with self.assertRaises(frappe.ValidationError) as context:
			so.validate_supplier_after_submit()

		self.assertIn("Not allowed to change Supplier", str(context.exception))

	def test_on_recurring_coverage_TC_S_177(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer

		create_company()
		create_customer("_Test Customer")
		make_item("_Test Item")

		reference_so = make_sales_order()

		auto_repeat = frappe.get_doc(
			{
				"doctype": "Auto Repeat",
				"reference_doctype": "Sales Order",
				"reference_document": reference_so.name,
				"frequency": "Monthly",
				"next_schedule_date": add_days(today(), 30),
			}
		)
		auto_repeat.insert()

		new_so = make_sales_order(do_not_save=1)
		new_so.transaction_date = add_days(today(), 30)
		new_so.items[0].delivery_date = add_days(today(), 30)
		new_so.save().submit()

		new_so.on_recurring(reference_doc=reference_so, auto_repeat_doc=auto_repeat)

		self.assertIsNotNone(new_so.delivery_date)
		self.assertTrue(new_so.delivery_date > getdate(today()))

		for d in new_so.get("items"):
			self.assertIsNotNone(d.delivery_date)
			self.assertTrue(d.delivery_date > getdate(today()))

	def test_close_or_unclose_sales_orders_coverage_TC_S_178(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer

		create_company()
		create_customer("_Test Customer")
		make_item("_Test Item")

		so = make_sales_order()
		self.assertEqual(so.status, "To Deliver and Bill")

		from erpnext.selling.doctype.sales_order.sales_order import close_or_unclose_sales_orders

		close_or_unclose_sales_orders(names=json.dumps([so.name]), status="Closed")
		so.reload()
		self.assertEqual(so.status, "Closed")

		close_or_unclose_sales_orders(names=json.dumps([so.name]), status="Draft")
		so.reload()
		self.assertEqual(so.status, "To Deliver and Bill")

		if not frappe.db.exists("User", "testuser@example.com"):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": "testuser@example.com",
					"first_name": "Test",
					"roles": [{"role": "Accounts User"}],
				}
			)
			user.insert(ignore_permissions=True)

		frappe.set_user("testuser@example.com")

		self.assertEqual(frappe.has_permission("Sales Order", "write"), False)

	def test_validate_serial_no_based_delivery_coverage_TC_S_181(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

		if not frappe.db.exists("Item", "Test Serialized Item"):
			item = make_item("Test Serialized Item")
			item.has_serial_no = 1
			item.maintain_stock = 1
			item.save()

		make_item("_Test Raw Item A")
		make_bom(item=item.name, rate=100, raw_materials=["_Test Raw Item A"])

		so_1 = make_sales_order(item_code="Test Serialized Item", do_not_submit=1)
		so_1.items[0].ensure_delivery_based_on_produced_serial_no = 1
		so_1.append(
			"items",
			{
				"item_code": "Test Serialized Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 1,
				"rate": 100,
				"delivery_date": today(),
				"ensure_delivery_based_on_produced_serial_no": 0,
			},
		)

		with self.assertRaises(frappe.ValidationError) as cm1:
			so_1.validate_serial_no_based_delivery()

		self.assertTrue("Cannot ensure delivery by Serial No" in str(cm1.exception))

		frappe.db.delete("BOM", {"item": "Test Serialized Item"})

		with self.assertRaises(frappe.ValidationError) as cm2:
			so_1.validate_serial_no_based_delivery()

		self.assertTrue("No active BOM found for item" in str(cm2.exception))

	def test_set_indicator_coverage_TC_S_182(self):
		make_item("_Test Item")

		so = make_sales_order(do_not_submit=1)

		so.set_indicator()
		self.assertEqual(so.indicator_color, "red")

		so.submit()
		so.set_indicator()
		self.assertEqual(so.indicator_color, "orange")

		so.cancel()
		so.set_indicator()
		self.assertEqual(so.indicator_color, "red")

	def test_make_maintenance_schedule_coverage_TC_S_186(self):
		from .sales_order import make_maintenance_schedule

		make_item("_Test Item")

		so = make_sales_order()

		maint_schedule = make_maintenance_schedule(so.name)

		self.assertEqual(maint_schedule.status, "Draft")

	def test_make_project_coverage_TC_S_190(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer

		create_company()
		create_customer("_Test Customer")
		make_item("_Test Item")

		so = make_sales_order()

		from erpnext.selling.doctype.sales_order.sales_order import make_project

		project = make_project(so.name)

		self.assertEqual(project.status, "Open")
		self.assertEqual(project.sales_order, so.name)

	def test_make_purchase_order_for_default_supplier_coverage_TC_S_191(self):
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		from .sales_order import make_purchase_order_for_default_supplier

		create_exchange_rate(date=today())
		supplier = create_supplier(supplier_name="_Test Supplier")
		make_item("_Test Item 1")
		make_item("_Test Item 2")
		so_items = [
			{
				"item_code": "_Test Item 1",
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			},
			{
				"item_code": "_Test Item 2",
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			},
		]

		address = "_Test Address so-Billing-1"
		if not frappe.db.exists("Address", address):
			address = frappe.get_doc(
				{
					"doctype": "Address",
					"address_title": "_Test Address so",
					"address_type": "Billing",
					"address_line1": "123 Test Street",
					"address_line2": "Suite 101",
					"city": "Testville",
					"state": "Maharashtra",
					"pincode": "400083",
					"country": "India",
					"phone": "1234567890",
					"email_id": "test@example.com",
					"links": [{"link_doctype": "Customer", "link_name": "_Test Customer"}],
				}
			)
			address.insert(ignore_permissions=True)
			address = address.name
		so = make_sales_order(item_list=so_items, do_not_submit=True)
		so.shipping_address_name = address
		so.submit()

		po1 = make_purchase_order_for_default_supplier(so.name)
		self.assertEqual(po1, None)

		po2 = make_purchase_order_for_default_supplier(so.name, selected_items=json.dumps(so_items))
		self.assertEqual(po2[0].status, "Draft")

		if not frappe.db.exists("Payment Terms Template", "Test Receivable Template Selling"):
			frappe.get_doc(
				{
					"doctype": "Payment Terms Template",
					"template_name": "Test Receivable Template Selling",
					"allocate_payment_based_on_payment_terms": 1,
					"terms": [
						{
							"doctype": "Payment Terms Template Detail",
							"payment_term": "Basic Amount Receivable for Selling",
							"invoice_portion": 100,
							"credit_days_based_on": "Day(s) after invoice date",
							"credit_days": 1,
						}
					],
				}
			).insert()

		supplier.default_price_list = "Standard Selling"
		supplier.payment_terms = "Test Receivable Template Selling"
		supplier.save()

		po3 = make_purchase_order_for_default_supplier(so.name, selected_items=so_items)
		self.assertEqual(po3[0].status, "Draft")
		# Reset supplier's payment term
		supplier.reload()
		supplier.payment_terms = ""
		supplier.save()

	def test_set_delivery_date_coverage_TC_S_192(self):
		from .sales_order import set_delivery_date

		make_item("_Test Item")
		so = make_sales_order()

		set_delivery_date(items=None, sales_order=so.name)
		self.assertEqual(so.items[0].delivery_date, add_days(today(), 10))


@if_app_installed("india_compliance")
def create_test_tax_data():
	if not frappe.db.exists("Tax Category", "In-State"):
		frappe.get_doc({"doctype": "Tax Category", "title": "In-State"}).insert()

	if not frappe.db.exists("Sales Taxes and Charges Template", "Output GST In-state - _TC"):
		frappe.get_doc(
			{
				"doctype": "Sales Taxes and Charges Template",
				"title": "Output GST In-state",
				"company": "_Test Company",
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": "Output Tax SGST - _TC",
						"rate": 9,
						"description": "SGST - _TC",
					},
					{
						"charge_type": "On Net Total",
						"account_head": "Output Tax CGST - _TC",
						"rate": 9,
						"description": "CGST - _TC",
					},
				],
			}
		).insert()

	if not frappe.db.exists("Purchase Taxes and Charges Template", "Input GST In-state - _TC"):
		frappe.get_doc(
			{
				"doctype": "Purchase Taxes and Charges Template",
				"title": "Input GST In-state",
				"company": "_Test Company",
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": "Input Tax CGST - _TC",
						"rate": 9,
						"description": "CGST - _TC",
					},
					{
						"charge_type": "On Net Total",
						"account_head": "Input Tax SGST - _TC",
						"rate": 9,
						"description": "SGST - _TC",
					},
				],
			}
		).insert()


@if_app_installed("india_compliance")
def test_item_tax_template(**data):
	from india_compliance.gst_india.overrides.transaction import get_valid_accounts
	from india_compliance.gst_india.utils import get_gst_accounts_by_type

	doc = frappe.new_doc("Item Tax Template")
	gst_rate = data.get("gst_rate") if data.get("gst_rate") is not None else 18
	doc.update(
		{
			"company": data.get("company") or "_Test Company",
			"gst_treatment": data.get("gst_treatment") or "Taxable",
			"gst_rate": gst_rate,
			"title": data.get("title") or "GST 18%",
		}
	)

	if data.get("taxes"):
		doc.extend("taxes", data.get("taxes"))

		return doc.insert()

	__, intra_state_accounts, inter_state_accounts = get_valid_accounts(
		doc.company, for_sales=True, for_purchase=True, throw=False
	)

	if not intra_state_accounts and not inter_state_accounts:
		intra_state_accounts = frappe.get_all(
			"Account",
			filters={
				"company": doc.company,
				"account_type": "Tax",
			},
			pluck="name",
		)

	rcm_accounts = (get_gst_accounts_by_type(doc.company, "Sales Reverse Charge", throw=False)).values()

	for account in intra_state_accounts:
		tax_rate = gst_rate
		if account in rcm_accounts:
			tax_rate = tax_rate * -1

		doc.append(
			"taxes",
			{
				"tax_type": account,
				"tax_rate": tax_rate / 2,
			},
		)

	for account in inter_state_accounts:
		tax_rate = gst_rate
		if account in rcm_accounts:
			tax_rate = tax_rate * -1
		doc.append(
			"taxes",
			{
				"tax_type": account,
				"tax_rate": tax_rate,
			},
		)

	return doc.insert()


def create_test_warehouse(name, warehouse_name, company):
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	if not frappe.db.exists("Warehouse", name):
		warehouse = create_warehouse(warehouse_name, company=company)
		return warehouse


def get_transport_details(customer):
	driver = frappe.get_all("Driver", filters={"full_name": "Test Driver"}, fields=["name"])
	if not driver:
		driver = frappe.new_doc("Driver")
		driver.full_name = "Test Driver"
		driver.status = "Active"
		driver.save()
	else:
		driver = frappe.get_doc("Driver", driver[0].name)

	vehicle = frappe.get_all("Vehicle", filters={"license_plate": "Test1234"}, fields=["name"])
	if not vehicle:
		vehicle = frappe.new_doc("Vehicle")
		vehicle.license_plate = "Test1234"
		vehicle.model = "Test Model"
		vehicle.make = "Test Make"
		vehicle.last_odometer = 1000
		vehicle.fuel_type = "Petrol"
		vehicle.uom = "Litre"
		vehicle.save()
	else:
		vehicle = frappe.get_doc("Vehicle", vehicle[0].name)

	address = frappe.get_all("Address", filters={"address_title": "Test Address"}, fields=["name"])
	if not address:
		address = frappe.new_doc("Address")
		address.address_title = "Test Address"
		address.address_type = "Billing"
		address.address_line1 = "TEST"
		address.city = "Mumbai"
		address.state = "Maharashtra"
		address.country = "India"
		address.pincode = "400080"
		address.append("links", {"link_doctype": "Customer", "link_name": customer})
		address.save()
	else:
		address = frappe.get_doc("Address", address[0].name)

	return driver, vehicle, address


def get_gst_details(doctype, filters):
	return frappe.get_all(doctype, filters, ["gstin", "gst_category", "name"])


def is_registered_regular(details):
	return details.get("gst_category") == "Registered Regular" and details.get("gstin")


def create_registered_bank_account():
	if not frappe.db.exists("Account", {"name": "_Test Registered Bank Account - _TIRC"}):
		acc_doc = frappe.new_doc("Account")
		acc_data = {
			"account_name": "_Test Registered Bank Account",
			"company": "_Test Indian Registered Company",
			"parent_account": "Bank Accounts - _TIRC",
		}
		acc_doc.update(acc_data)
		acc_doc.save()
		return acc_doc


def automatically_fetch_payment_terms(enable=1):
	accounts_settings = frappe.get_doc("Accounts Settings")
	accounts_settings.automatically_fetch_payment_terms = enable
	accounts_settings.save()


def compare_payment_schedules(doc, doc1, doc2):
	for index, schedule in enumerate(doc1.get("payment_schedule")):
		doc.assertEqual(schedule.payment_term, doc2.payment_schedule[index].payment_term)
		doc.assertEqual(getdate(schedule.due_date), doc2.payment_schedule[index].due_date)
		doc.assertEqual(schedule.invoice_portion, doc2.payment_schedule[index].invoice_portion)
		doc.assertEqual(schedule.payment_amount, doc2.payment_schedule[index].payment_amount)


def make_sales_order(**args):
	so = frappe.new_doc("Sales Order")
	args = frappe._dict(args)
	if args.transaction_date:
		so.transaction_date = args.transaction_date

	so.set_warehouse = ""  # no need to test set_warehouse permission since it only affects the client
	so.company = args.company or "_Test Company"
	so.customer = args.customer or "_Test Customer"
	so.currency = args.currency or "INR"
	so.po_no = args.po_no or ""
	if args.selling_price_list:
		so.selling_price_list = args.selling_price_list
	if args.cost_center:
		so.cost_center = args.cost_center

	if "warehouse" not in args:
		args.warehouse = "_Test Warehouse - _TC"

	if args.item_list:
		for item in args.item_list:
			so.append("items", item)

	else:
		so.append(
			"items",
			{
				"item_code": args.item or args.item_code or "_Test Item",
				"warehouse": args.warehouse,
				"qty": args.qty if args.qty is not None else 10,
				"uom": args.uom or None,
				"price_list_rate": args.price_list_rate or None,
				"discount_percentage": args.discount_percentage or None,
				"rate": args.rate or (None if args.price_list_rate else 100),
				"against_blanket_order": args.against_blanket_order,
			},
		)

	so.delivery_date = add_days(so.transaction_date, 10)

	set_credit_limit_for_customer(customer_name=args.customer or "_Test Customer")

	if not args.do_not_save:
		so.insert()
		if not args.do_not_submit:
			so.submit()
		else:
			so.payment_schedule = []
	else:
		so.payment_schedule = []

	return so


def make_service_item():
	if not frappe.db.exists("Item", {"item_code": "Consultancy"}):
		si_doc = frappe.new_doc("Item")
		item_price_data = {
			"item_code": "Consultancy",
			"stock_uom": "_Test UOM",
			"in_stock_item": 0,
			"item_group": "Services",
			"gst_hsn_code": "01011020",
			"description": "Consultancy",
			"is_purchase_item": 1,
			"grant_commission": 1,
			"is_sales_item": 1,
		}
		si_doc.update(item_price_data)
		si_doc.save()
		return si_doc


def make_item_price():
	if not frappe.db.exists("Item Price", {"item_code": "_Test Item"}):
		ip_doc = frappe.new_doc("Item Price")
		item_price_data = {
			"item_code": "_Test Item",
			"uom": "_Test UOM",
			"price_list": "Standard Selling",
			"selling": 1,
			"price_list_rate": 100,
		}
		ip_doc.update(item_price_data)
		ip_doc.save()
		return ip_doc


def make_pricing_rule():
	if not frappe.db.exists("Pricing Rule", {"title": "Test Offer"}):
		pricing_rule_doc = frappe.new_doc("Pricing Rule")
		pricing_rule_data = {
			"title": "Test Offer",
			"apply_on": "Item Code",
			"price_or_product_discount": "Price",
			"selling": 1,
			"min_qty": 10,
			"company": "_Test Company",
			"margin_type": "Percentage",
			"discount_percentage": 10,
			"for_price_list": "Standard Selling",
			"items": [{"item_code": "_Test Item", "uom": "_Test UOM"}],
		}

		pricing_rule_doc.update(pricing_rule_data)
		pricing_rule_doc.save()
		return pricing_rule_doc
	else:
		pricing_rule_doc = frappe.get_doc("Pricing Rule", {"title": "Test Offer"})
		return pricing_rule_doc


def create_dn_against_so(so, delivered_qty=0, do_not_submit=False):
	frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)

	dn = make_delivery_note(so)
	dn.get("items")[0].qty = delivered_qty or 5
	dn.insert()
	if not do_not_submit:
		dn.submit()
	return dn


def get_reserved_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"):
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "reserved_qty"))


test_dependencies = ["Currency Exchange"]


def make_sales_order_workflow():
	if frappe.db.exists("Workflow", "SO Test Workflow"):
		doc = frappe.get_doc("Workflow", "SO Test Workflow")
		doc.set("is_active", 1)
		doc.save()
		return doc

	frappe.get_doc(dict(doctype="Role", role_name="Test Junior Approver")).insert(ignore_if_duplicate=True)
	frappe.get_doc(dict(doctype="Role", role_name="Test Approver")).insert(ignore_if_duplicate=True)
	frappe.cache().hdel("roles", frappe.session.user)

	workflow = frappe.get_doc(
		{
			"doctype": "Workflow",
			"workflow_name": "SO Test Workflow",
			"document_type": "Sales Order",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"send_email_alert": 0,
		}
	)
	workflow.append("states", dict(state="Pending", allow_edit="All"))
	workflow.append("states", dict(state="Approved", allow_edit="Test Approver", doc_status=1))
	workflow.append(
		"transitions",
		dict(
			state="Pending",
			action="Approve",
			next_state="Approved",
			allowed="Test Junior Approver",
			allow_self_approval=1,
			condition="doc.grand_total < 200",
		),
	)
	workflow.append(
		"transitions",
		dict(
			state="Pending",
			action="Approve",
			next_state="Approved",
			allowed="Test Approver",
			allow_self_approval=1,
			condition="doc.grand_total > 200",
		),
	)
	workflow.insert(ignore_permissions=True)

	return workflow


def _make_blanket_order(**args):
	from erpnext.manufacturing.doctype.blanket_order.test_blanket_order import make_blanket_order

	return make_blanket_order(**args)


def create_registered_customer():
	if not frappe.db.exists("Customer", "_Test Registered Customer"):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test Registered Customer",
				"customer_type": "Company",
				"customer_group": "Commercial",
				"territory": "_Test Territory",
				"gstin": "24AANFA2641L1ZF",
				"gst_category": "Registered Regular",
			}
		)
		customer.insert()

	if not frappe.db.exists("Address", "_Test Registered Customer-Billing"):
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "_Test Registered Customer",
				"address_type": "Billing",
				"address_line1": "Test Address - 1",
				"city": "Test City",
				"state": "Gujarat",
				"pincode": "380015",
				"country": "India",
				"gstin": "24AAQCA8719H1ZC",
				"gst_category": "Registered Regular",
				"is_primary_address": 1,
				"is_company_address": 1,
				"is_shipping_address": 1,
				"links": [{"link_doctype": "Customer", "link_name": "_Test Registered Customer"}],
			}
		)
		address.insert()


def create_registered_address_for_gst_entities():
	if not frappe.db.exists("Address", "_Test Indian Registered Company-Billing"):
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"name": "_Test Indian Registered Company-Billing",
				"address_title": "_Test Indian Registered Company",
				"address_type": "Billing",
				"address_line1": "Test Address - 1",
				"city": "Test City",
				"state": "Gujarat",
				"pincode": "380015",
				"country": "India",
				"gstin": "24AAQCA8719H1ZC",
				"gst_category": "Registered Regular",
				"is_primary_address": 1,
				"is_company_address": 1,
				"is_shipping_address": 1,
				"links": [
					{"link_doctype": "Company", "link_name": "_Test Indian Registered Company"},
					{"link_doctype": "Customer", "link_name": "_Test Registered Customer"},
				],
			}
		)
		address.insert(ignore_permissions=True)


def create_exchange_rate(date):
	# make an entry in Currency Exchange list. serves as a static exchange rate
	if frappe.db.exists(
		{"doctype": "Currency Exchange", "date": date, "from_currency": "USD", "to_currency": "INR"}
	):
		return
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": date,
				"from_currency": "USD",
				"to_currency": frappe.get_cached_value("Company", "_Test Company", "default_currency"),
				"exchange_rate": 70,
				"for_buying": True,
				"for_selling": True,
			}
		)
		doc.insert()


def set_credit_limit_for_customer(customer_name):
	customer = frappe.get_doc("Customer", customer_name)
	customer.credit_limits.clear()
	customer.append(
		"credit_limits",
		{"company": "_Test Company", "credit_limit": 100000000000.00},
	)
	customer.save()
