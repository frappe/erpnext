# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import json
import unittest
import frappe
import frappe.permissions
from frappe.utils import flt, add_days, nowdate
from frappe.core.doctype.user_permission.test_user_permission import create_user
from erpnext.selling.doctype.sales_order.sales_order \
	import make_material_request, make_delivery_note, make_sales_invoice, WarehouseRequired
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.selling.doctype.sales_order.sales_order import make_work_orders
from erpnext.controllers.accounts_controller import update_child_qty_rate
from erpnext.selling.doctype.sales_order.sales_order import make_raw_material_request
from erpnext.manufacturing.doctype.blanket_order.test_blanket_order import make_blanket_order
from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
from erpnext.stock.doctype.item.test_item import make_item

class TestSalesOrder(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		cls.unlink_setting = int(frappe.db.get_value("Accounts Settings", "Accounts Settings",
			"unlink_advance_payment_on_cancelation_of_order"))

	@classmethod
	def tearDownClass(cls) -> None:
		# reset config to previous state
		frappe.db.set_value("Accounts Settings", "Accounts Settings",
			"unlink_advance_payment_on_cancelation_of_order", cls.unlink_setting)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_make_material_request(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_material_request, so.name)

		so.submit()
		mr = make_material_request(so.name)

		self.assertEqual(mr.material_request_type, "Purchase")
		self.assertEqual(len(mr.get("items")), len(so.get("items")))

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
		si.set('taxes', [])
		si.save()

		self.assertEqual(si.payment_schedule[0].payment_amount, 500.0)
		self.assertEqual(si.payment_schedule[0].due_date, so.transaction_date)
		self.assertEqual(si.payment_schedule[1].payment_amount, 500.0)
		self.assertEqual(si.payment_schedule[1].due_date, add_days(so.transaction_date, 30))

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
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		dn1 = create_delivery_note(is_return=1, return_against=dn.name, qty=-3, do_not_submit=True)
		dn1.items[0].against_sales_order = so.name
		dn1.items[0].so_detail = so.items[0].name
		dn1.submit()

		si1 = create_sales_invoice(is_return=1, return_against=si2.name, qty=-1, update_stock=1, do_not_submit=True)
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
		so.update_status('Draft')
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
		frappe.db.set_value('Item', "_Test Item", 'over_delivery_receipt_allowance', 50)

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
		frappe.db.set_value('Item', "_Test Item", 'over_delivery_receipt_allowance', 50)
		frappe.db.set_value('Item', "_Test Item", 'over_billing_allowance', 20)

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
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 20)

		dn = create_dn_against_so(so.name)

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 25)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 10)

		# close so
		so.load_from_db()
		so.update_status("Closed")

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2)

		# unclose so
		so.load_from_db()
		so.update_status('Draft')

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 25)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 10)

		dn.cancel()
		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 50)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 20)

		so.load_from_db()
		so.cancel()
		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2)

	def test_sales_order_on_hold(self):
		so = make_sales_order(item_code="_Test Product Bundle Item")
		so.db_set('Status', "On Hold")
		si = make_sales_invoice(so.name)
		self.assertRaises(frappe.ValidationError, create_dn_against_so, so.name)
		self.assertRaises(frappe.ValidationError, si.submit)

	def test_reserved_qty_for_over_delivery_with_packing_list(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)
		make_stock_entry(item="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", qty=10, rate=100)

		# set over-delivery allowance
		frappe.db.set_value('Item', "_Test Product Bundle Item", 'over_delivery_receipt_allowance', 50)

		existing_reserved_qty_item1 = get_reserved_qty("_Test Item")
		existing_reserved_qty_item2 = get_reserved_qty("_Test Item Home Desktop 100")

		so = make_sales_order(item_code="_Test Product Bundle Item")

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 50)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 20)

		dn = create_dn_against_so(so.name, 15)

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2)

		dn.cancel()
		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 50)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 20)

	def test_update_child_adding_new_item(self):
		so = make_sales_order(item_code= "_Test Item", qty=4)
		create_dn_against_so(so.name, 4)
		make_sales_invoice(so.name)

		prev_total = so.get("base_total")
		prev_total_in_words = so.get("base_in_words")

		# get reserved qty before update items
		reserved_qty_for_second_item = get_reserved_qty("_Test Item 2")

		first_item_of_so = so.get("items")[0]
		trans_item = json.dumps([
			{'item_code' : first_item_of_so.item_code, 'rate' : first_item_of_so.rate, \
				'qty' : first_item_of_so.qty, 'docname': first_item_of_so.name},
			{'item_code' : '_Test Item 2', 'rate' : 200, 'qty' : 7}
		])
		update_child_qty_rate('Sales Order', trans_item, so.name)

		so.reload()
		self.assertEqual(so.get("items")[-1].item_code, '_Test Item 2')
		self.assertEqual(so.get("items")[-1].rate, 200)
		self.assertEqual(so.get("items")[-1].qty, 7)
		self.assertEqual(so.get("items")[-1].amount, 1400)

		# reserved qty should increase after adding row
		self.assertEqual(get_reserved_qty('_Test Item 2'), reserved_qty_for_second_item + 7)

		self.assertEqual(so.status, 'To Deliver and Bill')

		updated_total = so.get("base_total")
		updated_total_in_words = so.get("base_in_words")

		self.assertEqual(updated_total, prev_total+1400)
		self.assertNotEqual(updated_total_in_words, prev_total_in_words)

	def test_update_child_removing_item(self):
		so = make_sales_order(**{
			"item_list": [{
				"item_code": '_Test Item',
				"qty": 5,
				"rate":1000
			}]
		})
		create_dn_against_so(so.name, 2)
		make_sales_invoice(so.name)

		# get reserved qty before update items
		reserved_qty_for_second_item = get_reserved_qty("_Test Item 2")

		# add an item so as to try removing items
		trans_item = json.dumps([
			{"item_code": '_Test Item', "qty": 5, "rate":1000, "docname": so.get("items")[0].name},
			{"item_code": '_Test Item 2', "qty": 2, "rate":500}
		])
		update_child_qty_rate('Sales Order', trans_item, so.name)
		so.reload()
		self.assertEqual(len(so.get("items")), 2)

		# reserved qty should increase after adding row
		self.assertEqual(get_reserved_qty('_Test Item 2'), reserved_qty_for_second_item + 2)

		# check if delivered items can be removed
		trans_item = json.dumps([{
			"item_code": '_Test Item 2',
			"qty": 2,
			"rate":500,
			"docname": so.get("items")[1].name
		}])
		self.assertRaises(frappe.ValidationError, update_child_qty_rate, 'Sales Order', trans_item, so.name)

		#remove last added item
		trans_item = json.dumps([{
			"item_code": '_Test Item',
			"qty": 5,
			"rate":1000,
			"docname": so.get("items")[0].name
		}])
		update_child_qty_rate('Sales Order', trans_item, so.name)

		so.reload()
		self.assertEqual(len(so.get("items")), 1)

		# reserved qty should decrease (back to initial) after deleting row
		self.assertEqual(get_reserved_qty('_Test Item 2'), reserved_qty_for_second_item)

		self.assertEqual(so.status, 'To Deliver and Bill')


	def test_update_child(self):
		so = make_sales_order(item_code= "_Test Item", qty=4)
		create_dn_against_so(so.name, 4)
		make_sales_invoice(so.name)

		existing_reserved_qty = get_reserved_qty()

		trans_item = json.dumps([{'item_code' : '_Test Item', 'rate' : 200, 'qty' : 7, 'docname': so.items[0].name}])
		update_child_qty_rate('Sales Order', trans_item, so.name)

		so.reload()
		self.assertEqual(so.get("items")[0].rate, 200)
		self.assertEqual(so.get("items")[0].qty, 7)
		self.assertEqual(so.get("items")[0].amount, 1400)
		self.assertEqual(so.status, 'To Deliver and Bill')

		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 3)

		trans_item = json.dumps([{'item_code' : '_Test Item', 'rate' : 200, 'qty' : 2, 'docname': so.items[0].name}])
		self.assertRaises(frappe.ValidationError, update_child_qty_rate,'Sales Order', trans_item, so.name)

	def test_update_child_with_precision(self):
		from frappe.model.meta import get_field_precision
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter

		precision = get_field_precision(frappe.get_meta("Sales Order Item").get_field("rate"))

		make_property_setter("Sales Order Item", "rate", "precision", 7, "Currency")
		so = make_sales_order(item_code= "_Test Item", qty=4, rate=200.34664)

		trans_item = json.dumps([{'item_code' : '_Test Item', 'rate' : 200.34669, 'qty' : 4, 'docname': so.items[0].name}])
		update_child_qty_rate('Sales Order', trans_item, so.name)

		so.reload()
		self.assertEqual(so.items[0].rate, 200.34669)
		make_property_setter("Sales Order Item", "rate", "precision", precision, "Currency")

	def test_update_child_perm(self):
		so = make_sales_order(item_code= "_Test Item", qty=4)

		test_user = create_user("test_so_child_perms@example.com", "Accounts User")
		frappe.set_user(test_user.name)

		# update qty
		trans_item = json.dumps([{'item_code' : '_Test Item', 'rate' : 200, 'qty' : 7, 'docname': so.items[0].name}])
		self.assertRaises(frappe.ValidationError, update_child_qty_rate,'Sales Order', trans_item, so.name)

		# add new item
		trans_item = json.dumps([{'item_code' : '_Test Item', 'rate' : 100, 'qty' : 2}])
		self.assertRaises(frappe.ValidationError, update_child_qty_rate,'Sales Order', trans_item, so.name)

	def test_update_child_qty_rate_with_workflow(self):
		from frappe.model.workflow import apply_workflow

		workflow = make_sales_order_workflow()
		so = make_sales_order(item_code= "_Test Item", qty=1, rate=150, do_not_submit=1)
		apply_workflow(so, 'Approve')

		user = 'test@example.com'
		test_user = frappe.get_doc('User', user)
		test_user.add_roles("Sales User", "Test Junior Approver")
		frappe.set_user(user)

		# user shouldn't be able to edit since grand_total will become > 200 if qty is doubled
		trans_item = json.dumps([{'item_code' : '_Test Item', 'rate' : 150, 'qty' : 2, 'docname': so.items[0].name}])
		self.assertRaises(frappe.ValidationError, update_child_qty_rate, 'Sales Order', trans_item, so.name)

		frappe.set_user("Administrator")
		user2 = 'test2@example.com'
		test_user2 = frappe.get_doc('User', user2)
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

	def test_update_child_product_bundle(self):
		# test Update Items with product bundle
		if not frappe.db.exists("Item", "_Product Bundle Item"):
			bundle_item = make_item("_Product Bundle Item", {"is_stock_item": 0})
			bundle_item.append("item_defaults", {
					"company": "_Test Company",
					"default_warehouse": "_Test Warehouse - _TC"})
			bundle_item.save(ignore_permissions=True)

		make_item("_Packed Item", {"is_stock_item": 1})
		make_product_bundle("_Product Bundle Item", ["_Packed Item"], 2)

		so = make_sales_order(item_code = "_Test Item", warehouse=None)

		# get reserved qty of packed item
		existing_reserved_qty = get_reserved_qty("_Packed Item")

		added_item = json.dumps([{"item_code" : "_Product Bundle Item", "rate" : 200, 'qty' : 2}])
		update_child_qty_rate('Sales Order', added_item, so.name)

		so.reload()
		self.assertEqual(so.packed_items[0].qty, 4)

		# reserved qty in packed item should increase after adding bundle item
		self.assertEqual(get_reserved_qty("_Packed Item"), existing_reserved_qty + 4)

		# test uom and conversion factor change
		update_uom_conv_factor = json.dumps([{
			'item_code': so.get("items")[0].item_code,
			'rate': so.get("items")[0].rate,
			'qty': so.get("items")[0].qty,
			'uom': "_Test UOM 1",
			'conversion_factor': 2,
			'docname': so.get("items")[0].name
		}])
		update_child_qty_rate('Sales Order', update_uom_conv_factor, so.name)

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
			make_item("Test Item with Tax", {
				'is_stock_item': 1,
			})

		if not frappe.db.exists("Item Tax Template", {"title": 'Test Update Items Template'}):
			frappe.get_doc({
				'doctype': 'Item Tax Template',
				'title': 'Test Update Items Template',
				'company': '_Test Company',
				'taxes': [
					{
						'tax_type': "_Test Account Service Tax - _TC",
						'tax_rate': 10,
					}
				]
			}).insert()

		new_item_with_tax = frappe.get_doc("Item", "Test Item with Tax")

		new_item_with_tax.append("taxes", {
			"item_tax_template": "Test Update Items Template - _TC",
			"valid_from": nowdate()
		})
		new_item_with_tax.save()

		tax_template = "_Test Account Excise Duty @ 10 - _TC"
		item =  "_Test Item Home Desktop 100"
		if not frappe.db.exists("Item Tax", {"parent":item, "item_tax_template":tax_template}):
			item_doc = frappe.get_doc("Item", item)
			item_doc.append("taxes", {
				"item_tax_template": tax_template,
				"valid_from": nowdate()
			})
			item_doc.save()
		else:
			# update valid from
			frappe.db.sql("""UPDATE `tabItem Tax` set valid_from = CURDATE()
				where parent = %(item)s and item_tax_template = %(tax)s""",
					{"item": item, "tax": tax_template})

		so = make_sales_order(item_code=item, qty=1, do_not_save=1)

		so.append("taxes", {
			"account_head": "_Test Account Excise Duty - _TC",
			"charge_type": "On Net Total",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Excise Duty",
			"doctype": "Sales Taxes and Charges",
			"rate": 10
		})
		so.insert()
		so.submit()

		self.assertEqual(so.taxes[0].tax_amount, 10)
		self.assertEqual(so.taxes[0].total, 110)

		old_stock_settings_value = frappe.db.get_single_value("Stock Settings", "default_warehouse")
		frappe.db.set_value("Stock Settings", None, "default_warehouse", "_Test Warehouse - _TC")

		items = json.dumps([
			{'item_code' : item, 'rate' : 100, 'qty' : 1, 'docname': so.items[0].name},
			{'item_code' : item, 'rate' : 200, 'qty' : 1}, # added item whose tax account head already exists in PO
			{'item_code' : new_item_with_tax.name, 'rate' : 100, 'qty' : 1} # added item whose tax account head  is missing in PO
		])
		update_child_qty_rate('Sales Order', items, so.name)

		so.reload()
		self.assertEqual(so.taxes[0].tax_amount, 40)
		self.assertEqual(so.taxes[0].total, 440)
		self.assertEqual(so.taxes[1].account_head, "_Test Account Service Tax - _TC")
		self.assertEqual(so.taxes[1].tax_amount, 40)
		self.assertEqual(so.taxes[1].total, 480)

		# teardown
		frappe.db.sql("""UPDATE `tabItem Tax` set valid_from = NULL
			where parent = %(item)s and item_tax_template = %(tax)s""", {"item": item, "tax": tax_template})
		so.cancel()
		so.delete()
		new_item_with_tax.delete()
		frappe.get_doc("Item Tax Template", "Test Update Items Template - _TC").delete()
		frappe.db.set_value("Stock Settings", None, "default_warehouse", old_stock_settings_value)

	def test_warehouse_user(self):
		test_user = create_user("test_so_warehouse_user@example.com", "Sales User", "Stock User")

		test_user_2 = frappe.get_doc("User", "test2@example.com")
		test_user_2.add_roles("Sales User", "Stock User")
		test_user_2.remove_roles("Sales Manager")

		frappe.permissions.add_user_permission("Warehouse", "_Test Warehouse 1 - _TC", test_user.name)
		frappe.permissions.add_user_permission("Warehouse", "_Test Warehouse 2 - _TC1", test_user_2.name)
		frappe.permissions.add_user_permission("Company", "_Test Company 1", test_user_2.name)

		frappe.set_user(test_user.name)

		so = make_sales_order(company="_Test Company 1", customer="_Test Customer 1",
			warehouse="_Test Warehouse 2 - _TC1", do_not_save=True)
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

		self.assertRaises(frappe.CancelledLinkError, dn.submit)

	def test_service_type_product_bundle(self):
		make_item("_Test Service Product Bundle", {"is_stock_item": 0})
		make_item("_Test Service Product Bundle Item 1", {"is_stock_item": 0})
		make_item("_Test Service Product Bundle Item 2", {"is_stock_item": 0})

		make_product_bundle("_Test Service Product Bundle",
			["_Test Service Product Bundle Item 1", "_Test Service Product Bundle Item 2"])

		so = make_sales_order(item_code = "_Test Service Product Bundle", warehouse=None)

		self.assertTrue("_Test Service Product Bundle Item 1" in [d.item_code for d in so.packed_items])
		self.assertTrue("_Test Service Product Bundle Item 2" in [d.item_code for d in so.packed_items])

	def test_mix_type_product_bundle(self):
		make_item("_Test Mix Product Bundle", {"is_stock_item": 0})
		make_item("_Test Mix Product Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Mix Product Bundle Item 2", {"is_stock_item": 0})

		make_product_bundle("_Test Mix Product Bundle",
			["_Test Mix Product Bundle Item 1", "_Test Mix Product Bundle Item 2"])

		self.assertRaises(WarehouseRequired, make_sales_order, item_code = "_Test Mix Product Bundle", warehouse="")

	def test_auto_insert_price(self):
		make_item("_Test Item for Auto Price List", {"is_stock_item": 0})
		frappe.db.set_value("Stock Settings", None, "auto_insert_price_list_rate_if_missing", 1)

		item_price = frappe.db.get_value("Item Price", {"price_list": "_Test Price List",
			"item_code": "_Test Item for Auto Price List"})
		if item_price:
			frappe.delete_doc("Item Price", item_price)

		make_sales_order(item_code = "_Test Item for Auto Price List", selling_price_list="_Test Price List", rate=100)

		self.assertEqual(frappe.db.get_value("Item Price",
			{"price_list": "_Test Price List", "item_code": "_Test Item for Auto Price List"}, "price_list_rate"), 100)


		# do not update price list
		frappe.db.set_value("Stock Settings", None, "auto_insert_price_list_rate_if_missing", 0)

		item_price = frappe.db.get_value("Item Price", {"price_list": "_Test Price List",
			"item_code": "_Test Item for Auto Price List"})
		if item_price:
			frappe.delete_doc("Item Price", item_price)

		make_sales_order(item_code = "_Test Item for Auto Price List", selling_price_list="_Test Price List", rate=100)

		self.assertEqual(frappe.db.get_value("Item Price",
			{"price_list": "_Test Price List", "item_code": "_Test Item for Auto Price List"}, "price_list_rate"), None)

		frappe.db.set_value("Stock Settings", None, "auto_insert_price_list_rate_if_missing", 1)

	def test_drop_shipping(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order_for_default_supplier, \
			update_status as so_update_status
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status

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
				"supplier": '_Test Supplier'
			},
			{
				"item_code": dn_item.item_code,
				"warehouse": "_Test Warehouse - _TC",
				"qty": 2,
				"rate": 300,
				"conversion_factor": 1.0
			}
		]

		if frappe.db.get_value("Item", "_Test Regular Item", "is_stock_item")==1:
			make_stock_entry(item="_Test Regular Item", target="_Test Warehouse - _TC", qty=2, rate=100)

		#create so, po and dn
		so = make_sales_order(item_list=so_items, do_not_submit=True)
		so.submit()

		po = make_purchase_order_for_default_supplier(so.name, selected_items=[so_items[0]])[0]
		po.submit()

		dn = create_dn_against_so(so.name, delivered_qty=2)

		self.assertEqual(so.customer, po.customer)
		self.assertEqual(po.items[0].sales_order, so.name)
		self.assertEqual(po.items[0].item_code, po_item.item_code)
		self.assertEqual(dn.items[0].item_code, dn_item.item_code)
		#test po_item length
		self.assertEqual(len(po.items), 1)

		# test ordered_qty and reserved_qty for drop ship item
		bin_po_item = frappe.get_all("Bin", filters={"item_code": po_item.item_code, "warehouse": "_Test Warehouse - _TC"},
			fields=["ordered_qty", "reserved_qty"])

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
		so.db_set('status', "Closed")
		so.update_reserved_qty()

		# test ordered_qty and reserved_qty for drop ship item after closing so
		bin_po_item = frappe.get_all("Bin", filters={"item_code": po_item.item_code, "warehouse": "_Test Warehouse - _TC"},
			fields=["ordered_qty", "reserved_qty"])

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
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order_for_default_supplier, \
			update_status as so_update_status

		# make items
		po_item1 = make_item("_Test Item for Drop Shipping 1", {"is_stock_item": 1, "delivered_by_supplier": 1})
		po_item2 = make_item("_Test Item for Drop Shipping 2", {"is_stock_item": 1, "delivered_by_supplier": 1})

		so_items = [
			{
				"item_code": po_item1.item_code,
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": '_Test Supplier'
			},
			{
				"item_code": po_item2.item_code,
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": '_Test Supplier'
			}
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
		#test po item length
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
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order_for_default_supplier

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
				"supplier": '_Test Supplier'
			},
			{
				"item_code": "_Test Item for Drop Shipping 2",
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": '_Test Supplier 1'
			}
		]

		# create so and po
		so = make_sales_order(item_list=so_items, do_not_submit=True)
		so.submit()

		purchase_orders = make_purchase_order_for_default_supplier(so.name, selected_items=so_items)

		self.assertEqual(len(purchase_orders), 2)
		self.assertEqual(purchase_orders[0].supplier, '_Test Supplier')
		self.assertEqual(purchase_orders[1].supplier, '_Test Supplier 1')

	def test_reserved_qty_for_closing_so(self):
		bin = frappe.get_all("Bin", filters={"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			fields=["reserved_qty"])

		existing_reserved_qty = bin[0].reserved_qty if bin else 0.0

		so = make_sales_order(item_code="_Test Item", qty=1)

		self.assertEqual(get_reserved_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"), existing_reserved_qty+1)

		so.update_status("Closed")

		self.assertEqual(get_reserved_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"), existing_reserved_qty)

	def test_create_so_with_margin(self):
		so = make_sales_order(item_code="_Test Item", qty=1, do_not_submit=True)
		so.items[0].price_list_rate = price_list_rate = 100
		so.items[0].margin_type = 'Percentage'
		so.items[0].margin_rate_or_amount = 25
		so.save()

		new_so = frappe.copy_doc(so)
		new_so.save(ignore_permissions=True)

		self.assertEqual(new_so.get("items")[0].rate, flt((price_list_rate*25)/100 + price_list_rate))
		new_so.items[0].margin_rate_or_amount = 25
		new_so.payment_schedule = []
		new_so.save()
		new_so.submit()

		self.assertEqual(new_so.get("items")[0].rate, flt((price_list_rate*25)/100 + price_list_rate))

	def test_terms_auto_added(self):
		so = make_sales_order(do_not_save=1)

		self.assertFalse(so.get('payment_schedule'))

		so.insert()

		self.assertTrue(so.get('payment_schedule'))

	def test_terms_not_copied(self):
		so = make_sales_order()
		self.assertTrue(so.get('payment_schedule'))

		si = make_sales_invoice(so.name)
		self.assertFalse(si.get('payment_schedule'))

	def test_terms_copied(self):
		so = make_sales_order(do_not_copy=1, do_not_save=1)
		so.payment_terms_template = '_Test Payment Term Template'
		so.insert()
		so.submit()
		self.assertTrue(so.get('payment_schedule'))

		si = make_sales_invoice(so.name)
		si.insert()
		self.assertTrue(si.get('payment_schedule'))

	def test_make_work_order(self):
		# Make a new Sales Order
		so = make_sales_order(**{
			"item_list": [{
				"item_code": "_Test FG Item",
				"qty": 10,
				"rate":100
			},
			{
				"item_code": "_Test FG Item",
				"qty": 20,
				"rate":200
			}]
		})

		# Raise Work Orders
		po_items= []
		so_item_name= {}
		for item in so.get_work_order_items():
			po_items.append({
				"warehouse": item.get("warehouse"),
				"item_code": item.get("item_code"),
				"pending_qty": item.get("pending_qty"),
				"sales_order_item": item.get("sales_order_item"),
				"bom": item.get("bom"),
				"description": item.get("description")
			})
			so_item_name[item.get("sales_order_item")]= item.get("pending_qty")
		make_work_orders(json.dumps({"items":po_items}), so.name, so.company)

		# Check if Work Orders were raised
		for item in so_item_name:
			wo_qty = frappe.db.sql("select sum(qty) from `tabWork Order` where sales_order=%s and sales_order_item=%s", (so.name, item))
			self.assertEqual(wo_qty[0][0], so_item_name.get(item))

	def test_serial_no_based_delivery(self):
		frappe.set_value("Stock Settings", None, "automatically_set_serial_nos_based_on_fifo", 1)
		item = make_item("_Reserved_Serialized_Item", {"is_stock_item": 1,
					"maintain_stock": 1,
					"has_serial_no": 1,
					"serial_no_series": "SI.####",
					"valuation_rate": 500,
					"item_defaults": [
						{
							"default_warehouse": "_Test Warehouse - _TC",
							"company": "_Test Company"
						}]
					})
		frappe.db.sql("""delete from `tabSerial No` where item_code=%s""", (item.item_code))
		make_item("_Test Item A", {"maintain_stock": 1,
					"valuation_rate": 100,
					"item_defaults": [
						{
							"default_warehouse": "_Test Warehouse - _TC",
							"company": "_Test Company"
						}]
					})
		make_item("_Test Item B", {"maintain_stock": 1,
					"valuation_rate": 200,
					"item_defaults": [
						{
							"default_warehouse": "_Test Warehouse - _TC",
							"company": "_Test Company"
						}]
					})
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		make_bom(item=item.item_code, rate=1000,
			raw_materials = ['_Test Item A', '_Test Item B'])

		so = make_sales_order(**{
			"item_list": [{
				"item_code": item.item_code,
				"ensure_delivery_based_on_produced_serial_no": 1,
				"qty": 1,
				"rate":1000
			}]
		})
		so.submit()
		from erpnext.manufacturing.doctype.work_order.test_work_order import \
			make_wo_order_test_record
		work_order = make_wo_order_test_record(item=item.item_code,
			qty=1, do_not_save=True)
		work_order.fg_warehouse = "_Test Warehouse - _TC"
		work_order.sales_order = so.name
		work_order.submit()
		make_stock_entry(item_code=item.item_code, target="_Test Warehouse - _TC", qty=1)
		item_serial_no = frappe.get_doc("Serial No", {"item_code": item.item_code})
		from erpnext.manufacturing.doctype.work_order.work_order import \
			make_stock_entry as make_production_stock_entry
		se = frappe.get_doc(make_production_stock_entry(work_order.name, "Manufacture", 1))
		se.submit()
		reserved_serial_no = se.get("items")[2].serial_no
		serial_no_so = frappe.get_value("Serial No", reserved_serial_no, "sales_order")
		self.assertEqual(serial_no_so, so.name)
		dn = make_delivery_note(so.name)
		dn.save()
		self.assertEqual(reserved_serial_no, dn.get("items")[0].serial_no)
		item_line = dn.get("items")[0]
		item_line.serial_no = item_serial_no.name
		item_line = dn.get("items")[0]
		item_line.serial_no =  reserved_serial_no
		dn.submit()
		dn.load_from_db()
		dn.cancel()
		si = make_sales_invoice(so.name)
		si.update_stock = 1
		si.save()
		self.assertEqual(si.get("items")[0].serial_no, reserved_serial_no)
		item_line = si.get("items")[0]
		item_line.serial_no = item_serial_no.name
		self.assertRaises(frappe.ValidationError, dn.submit)
		item_line = si.get("items")[0]
		item_line.serial_no = reserved_serial_no
		self.assertTrue(si.submit)
		si.submit()
		si.load_from_db()
		si.cancel()
		si = make_sales_invoice(so.name)
		si.update_stock = 0
		si.submit()
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import \
			make_delivery_note as make_delivery_note_from_invoice
		dn = make_delivery_note_from_invoice(si.name)
		dn.save()
		dn.submit()
		self.assertEqual(dn.get("items")[0].serial_no, reserved_serial_no)
		dn.load_from_db()
		dn.cancel()
		si.load_from_db()
		si.cancel()
		se.load_from_db()
		se.cancel()
		self.assertFalse(frappe.db.exists("Serial No", {"sales_order": so.name}))

	def test_advance_payment_entry_unlink_against_sales_order(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
		frappe.db.set_value("Accounts Settings", "Accounts Settings",
			"unlink_advance_payment_on_cancelation_of_order", 0)

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

		so_doc = frappe.get_doc('Sales Order', so.name)

		self.assertRaises(frappe.LinkExistsError, so_doc.cancel)

	def test_cancel_sales_order_after_cancel_payment_entry(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
		# make a sales order
		so = make_sales_order()

		# disable unlinking of payment entry
		frappe.db.set_value("Accounts Settings", "Accounts Settings",
			"unlink_advance_payment_on_cancelation_of_order", 0)

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
			so_doc = frappe.get_doc('Sales Order', so.name)
			so_doc.cancel()
		except Exception:
			self.fail("Can not cancel sales order with linked cancelled payment entry")

	def test_request_for_raw_materials(self):
		item = make_item("_Test Finished Item", {"is_stock_item": 1,
			"maintain_stock": 1,
			"valuation_rate": 500,
			"item_defaults": [
				{
					"default_warehouse": "_Test Warehouse - _TC",
					"company": "_Test Company"
				}]
			})
		make_item("_Test Raw Item A", {"maintain_stock": 1,
					"valuation_rate": 100,
					"item_defaults": [
						{
							"default_warehouse": "_Test Warehouse - _TC",
							"company": "_Test Company"
						}]
					})
		make_item("_Test Raw Item B", {"maintain_stock": 1,
					"valuation_rate": 200,
					"item_defaults": [
						{
							"default_warehouse": "_Test Warehouse - _TC",
							"company": "_Test Company"
						}]
					})
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		make_bom(item=item.item_code, rate=1000,
			raw_materials = ['_Test Raw Item A', '_Test Raw Item B'])

		so = make_sales_order(**{
			"item_list": [{
				"item_code": item.item_code,
				"qty": 1,
				"rate":1000
			}]
		})
		so.submit()
		mr_dict = frappe._dict()
		items = so.get_work_order_items(1)
		mr_dict['items'] = items
		mr_dict['include_exploded_items'] = 0
		mr_dict['ignore_existing_ordered_qty'] = 1
		make_raw_material_request(mr_dict, so.company, so.name)
		mr = frappe.db.sql("""select name from `tabMaterial Request` ORDER BY creation DESC LIMIT 1""", as_dict=1)[0]
		mr_doc = frappe.get_doc('Material Request',mr.get('name'))
		self.assertEqual(mr_doc.items[0].sales_order, so.name)

	def test_so_optional_blanket_order(self):
		"""
			Expected result: Blanket order Ordered Quantity should only be affected on Sales Order with against_blanket_order = 1.
			Second Sales Order should not add on to Blanket Orders Ordered Quantity.
		"""

		bo = make_blanket_order(blanket_order_type = "Selling", quantity = 10, rate = 10)

		so = make_sales_order(item_code= "_Test Item", qty = 5, against_blanket_order = 1)
		so_doc = frappe.get_doc('Sales Order', so.get('name'))
		# To test if the SO has a Blanket Order
		self.assertTrue(so_doc.items[0].blanket_order)

		so = make_sales_order(item_code= "_Test Item", qty = 5, against_blanket_order = 0)
		so_doc = frappe.get_doc('Sales Order', so.get('name'))
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



def make_sales_order(**args):
	so = frappe.new_doc("Sales Order")
	args = frappe._dict(args)
	if args.transaction_date:
		so.transaction_date = args.transaction_date

	so.set_warehouse = "" # no need to test set_warehouse permission since it only affects the client
	so.company = args.company or "_Test Company"
	so.customer = args.customer or "_Test Customer"
	so.currency = args.currency or "INR"
	so.po_no = args.po_no or '12345'
	if args.selling_price_list:
		so.selling_price_list = args.selling_price_list

	if "warehouse" not in args:
		args.warehouse = "_Test Warehouse - _TC"

	if args.item_list:
		for item in args.item_list:
			so.append("items", item)

	else:
		so.append("items", {
			"item_code": args.item or args.item_code or "_Test Item",
			"warehouse": args.warehouse,
			"qty": args.qty or 10,
			"uom": args.uom or None,
			"rate": args.rate or 100,
			"against_blanket_order": args.against_blanket_order
		})

	so.delivery_date = add_days(so.transaction_date, 10)

	if not args.do_not_save:
		so.insert()
		if not args.do_not_submit:
			so.submit()
		else:
			so.payment_schedule = []
	else:
		so.payment_schedule = []

	return so

def create_dn_against_so(so, delivered_qty=0):
	frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

	dn = make_delivery_note(so)
	dn.get("items")[0].qty = delivered_qty or 5
	dn.insert()
	dn.submit()
	return dn

def get_reserved_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"):
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse},
		"reserved_qty"))

test_dependencies = ["Currency Exchange"]

def make_sales_order_workflow():
	if frappe.db.exists('Workflow', 'SO Test Workflow'):
		doc = frappe.get_doc("Workflow", "SO Test Workflow")
		doc.set("is_active", 1)
		doc.save()
		return doc

	frappe.get_doc(dict(doctype='Role', role_name='Test Junior Approver')).insert(ignore_if_duplicate=True)
	frappe.get_doc(dict(doctype='Role', role_name='Test Approver')).insert(ignore_if_duplicate=True)
	frappe.db.commit()
	frappe.cache().hdel('roles', frappe.session.user)

	workflow = frappe.get_doc({
		"doctype": "Workflow",
		"workflow_name": "SO Test Workflow",
		"document_type": "Sales Order",
		"workflow_state_field": "workflow_state",
		"is_active": 1,
		"send_email_alert": 0,
	})
	workflow.append('states', dict( state = 'Pending', allow_edit = 'All' ))
	workflow.append('states', dict( state = 'Approved', allow_edit = 'Test Approver', doc_status = 1 ))
	workflow.append('transitions', dict(
		state = 'Pending', action = 'Approve', next_state = 'Approved', allowed = 'Test Junior Approver', allow_self_approval = 1,
		condition = 'doc.grand_total < 200'
	))
	workflow.append('transitions', dict(
		state = 'Pending', action = 'Approve', next_state = 'Approved', allowed = 'Test Approver', allow_self_approval = 1,
		 condition = 'doc.grand_total > 200'
	))
	workflow.insert(ignore_permissions=True)

	return workflow
