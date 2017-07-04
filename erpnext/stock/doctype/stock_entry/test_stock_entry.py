# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, unittest
import frappe.defaults
from frappe.utils import flt, nowdate, nowtime
from erpnext.stock.doctype.serial_no.serial_no import *
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt \
	import set_perpetual_inventory
from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import StockFreezeError
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import create_stock_reconciliation
from frappe.tests.test_permissions import set_user_permission_doctypes
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.accounts.doctype.account.test_account import get_inventory_account

def get_sle(**args):
	condition, values = "", []
	for key, value in args.iteritems():
		condition += " and " if condition else " where "
		condition += "`{0}`=%s".format(key)
		values.append(value)

	return frappe.db.sql("""select * from `tabStock Ledger Entry` %s
		order by timestamp(posting_date, posting_time) desc, name desc limit 1"""% condition,
		values, as_dict=1)

class TestStockEntry(unittest.TestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		set_perpetual_inventory(0)

		for role in ("Stock User", "Sales User"):
			set_user_permission_doctypes(doctype="Stock Entry", role=role,
				apply_user_permissions=0, user_permission_doctypes=None)

	def test_fifo(self):
		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)
		item_code = "_Test Item 2"
		warehouse = "_Test Warehouse - _TC"

		create_stock_reconciliation(item_code="_Test Item 2", warehouse="_Test Warehouse - _TC",
			qty=0, rate=100)

		make_stock_entry(item_code=item_code, target=warehouse, qty=1, basic_rate=10)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]
		self.assertEqual([[1, 10]], frappe.safe_eval(sle.stock_queue))

		# negative qty
		make_stock_entry(item_code=item_code, source=warehouse, qty=2, basic_rate=10)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]

		self.assertEqual([[-1, 10]], frappe.safe_eval(sle.stock_queue))

		# further negative
		make_stock_entry(item_code=item_code, source=warehouse, qty=1)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]

		self.assertEqual([[-2, 10]], frappe.safe_eval(sle.stock_queue))

		# move stock to positive
		make_stock_entry(item_code=item_code, target=warehouse, qty=3, basic_rate=20)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]
		self.assertEqual([[1, 20]], frappe.safe_eval(sle.stock_queue))

		# incoming entry with diff rate
		make_stock_entry(item_code=item_code, target=warehouse, qty=1, basic_rate=30)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]

		self.assertEqual([[1, 20],[1, 30]], frappe.safe_eval(sle.stock_queue))

		frappe.db.set_default("allow_negative_stock", 0)

	def test_auto_material_request(self):
		from erpnext.stock.doctype.item.test_item import make_item_variant
		make_item_variant()
		self._test_auto_material_request("_Test Item")
		self._test_auto_material_request("_Test Item", material_request_type="Transfer")

	def test_auto_material_request_for_variant(self):
		self._test_auto_material_request("_Test Variant Item-S")

	def test_auto_material_request_for_warehouse_group(self):
		self._test_auto_material_request("_Test Item Warehouse Group Wise Reorder", warehouse="_Test Warehouse Group-C1 - _TC")

	def _test_auto_material_request(self, item_code, material_request_type="Purchase", warehouse="_Test Warehouse - _TC"):
		variant = frappe.get_doc("Item", item_code)

		projected_qty, actual_qty = frappe.db.get_value("Bin", {"item_code": item_code,
			"warehouse": warehouse}, ["projected_qty", "actual_qty"]) or [0, 0]

		# stock entry reqd for auto-reorder
		create_stock_reconciliation(item_code=item_code, warehouse=warehouse,
			qty = actual_qty + abs(projected_qty) + 10, rate=100)

		projected_qty = frappe.db.get_value("Bin", {"item_code": item_code,
			"warehouse": warehouse}, "projected_qty") or 0

		frappe.db.set_value("Stock Settings", None, "auto_indent", 1)

		# update re-level qty so that it is more than projected_qty
		if projected_qty >= variant.reorder_levels[0].warehouse_reorder_level:
			variant.reorder_levels[0].warehouse_reorder_level += projected_qty
			variant.reorder_levels[0].material_request_type = material_request_type
			variant.save()

		from erpnext.stock.reorder_item import reorder_item
		mr_list = reorder_item()

		frappe.db.set_value("Stock Settings", None, "auto_indent", 0)

		items = []
		for mr in mr_list:
			for d in mr.items:
				items.append(d.item_code)

		self.assertTrue(item_code in items)

	def test_material_receipt_gl_entry(self):
		company = frappe.db.get_value('Warehouse', '_Test Warehouse - _TC', 'company')
		set_perpetual_inventory(1, company)

		mr = make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC",
			qty=50, basic_rate=100, expense_account="Stock Adjustment - _TC")

		stock_in_hand_account = get_inventory_account(mr.company, mr.get("items")[0].t_warehouse)
		self.check_stock_ledger_entries("Stock Entry", mr.name,
			[["_Test Item", "_Test Warehouse - _TC", 50.0]])

		self.check_gl_entries("Stock Entry", mr.name,
			sorted([
				[stock_in_hand_account, 5000.0, 0.0],
				["Stock Adjustment - _TC", 0.0, 5000.0]
			])
		)

		mr.cancel()

		self.assertFalse(frappe.db.sql("""select * from `tabStock Ledger Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mr.name))

		self.assertFalse(frappe.db.sql("""select * from `tabGL Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mr.name))

	def test_material_issue_gl_entry(self):
		company = frappe.db.get_value('Warehouse', '_Test Warehouse - _TC', 'company')
		set_perpetual_inventory(1, company)

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC",
			qty=50, basic_rate=100, expense_account="Stock Adjustment - _TC")

		mi = make_stock_entry(item_code="_Test Item", source="_Test Warehouse - _TC",
			qty=40, expense_account="Stock Adjustment - _TC")

		self.check_stock_ledger_entries("Stock Entry", mi.name,
			[["_Test Item", "_Test Warehouse - _TC", -40.0]])

		stock_in_hand_account = get_inventory_account(mi.company, "_Test Warehouse - _TC")
		stock_value_diff = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Stock Entry",
			"voucher_no": mi.name}, "stock_value_difference"))

		self.check_gl_entries("Stock Entry", mi.name,
			sorted([
				[stock_in_hand_account, 0.0, stock_value_diff],
				["Stock Adjustment - _TC", stock_value_diff, 0.0]
			])
		)

		mi.cancel()

		self.assertFalse(frappe.db.sql("""select name from `tabStock Ledger Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mi.name))

		self.assertFalse(frappe.db.sql("""select name from `tabGL Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mi.name))

	def test_material_transfer_gl_entry(self):
		company = frappe.db.get_value('Warehouse', '_Test Warehouse - _TC', 'company')
		set_perpetual_inventory(1, company)

		create_stock_reconciliation(qty=100, rate=100)

		mtn = make_stock_entry(item_code="_Test Item", source="_Test Warehouse - _TC",
			target="_Test Warehouse 1 - _TC", qty=45)

		self.check_stock_ledger_entries("Stock Entry", mtn.name,
			[["_Test Item", "_Test Warehouse - _TC", -45.0], ["_Test Item", "_Test Warehouse 1 - _TC", 45.0]])

		stock_in_hand_account = get_inventory_account(mtn.company, mtn.get("items")[0].s_warehouse)
		
		fixed_asset_account = get_inventory_account(mtn.company, mtn.get("items")[0].t_warehouse)
			
		if stock_in_hand_account == fixed_asset_account:
			# no gl entry as both source and target warehouse has linked to same account.
			self.assertFalse(frappe.db.sql("""select * from `tabGL Entry`
				where voucher_type='Stock Entry' and voucher_no=%s""", mtn.name))
			
		else:
			stock_value_diff = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Stock Entry",
				"voucher_no": mtn.name, "warehouse": "_Test Warehouse - _TC"}, "stock_value_difference"))
		
			self.check_gl_entries("Stock Entry", mtn.name,
				sorted([
					[stock_in_hand_account, 0.0, stock_value_diff],
					[fixed_asset_account, stock_value_diff, 0.0],
				])
			)

		mtn.cancel()
		self.assertFalse(frappe.db.sql("""select * from `tabStock Ledger Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mtn.name))

		self.assertFalse(frappe.db.sql("""select * from `tabGL Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mtn.name))

	def test_repack_no_change_in_valuation(self):
		company = frappe.db.get_value('Warehouse', '_Test Warehouse - _TC', 'company')
		set_perpetual_inventory(0, company)

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, basic_rate=100)
		make_stock_entry(item_code="_Test Item Home Desktop 100", target="_Test Warehouse - _TC",
			qty=50, basic_rate=100)

		repack = frappe.copy_doc(test_records[3])
		repack.posting_date = nowdate()
		repack.posting_time = nowtime()
		repack.insert()
		repack.submit()

		self.check_stock_ledger_entries("Stock Entry", repack.name,
			[["_Test Item", "_Test Warehouse - _TC", -50.0],
				["_Test Item Home Desktop 100", "_Test Warehouse - _TC", 1]])

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Stock Entry' and voucher_no=%s
			order by account desc""", repack.name, as_dict=1)
		self.assertFalse(gl_entries)

		set_perpetual_inventory(0, repack.company)

	def test_repack_with_additional_costs(self):
		company = frappe.db.get_value('Warehouse', '_Test Warehouse - _TC', 'company')
		set_perpetual_inventory(1, company)

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, basic_rate=100)
		repack = frappe.copy_doc(test_records[3])
		repack.posting_date = nowdate()
		repack.posting_time = nowtime()

		repack.set("additional_costs", [
			{
				"description": "Actual Oerating Cost",
				"amount": 1000
			},
			{
				"description": "additional operating costs",
				"amount": 200
			},
		])
		repack.insert()
		repack.submit()

		stock_in_hand_account = get_inventory_account(repack.company, repack.get("items")[1].t_warehouse)
		rm_stock_value_diff = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Stock Entry",
			"voucher_no": repack.name, "item_code": "_Test Item"}, "stock_value_difference"))

		fg_stock_value_diff = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Stock Entry",
			"voucher_no": repack.name, "item_code": "_Test Item Home Desktop 100"}, "stock_value_difference"))

		stock_value_diff = flt(fg_stock_value_diff - rm_stock_value_diff, 2)

		self.assertEqual(stock_value_diff, 1200)

		self.check_gl_entries("Stock Entry", repack.name,
			sorted([
				[stock_in_hand_account, 1200, 0.0],
				["Expenses Included In Valuation - _TC", 0.0, 1200.0]
			])
		)
		set_perpetual_inventory(0, repack.company)

	def check_stock_ledger_entries(self, voucher_type, voucher_no, expected_sle):
		expected_sle.sort(key=lambda x: x[0])

		# check stock ledger entries
		sle = frappe.db.sql("""select item_code, warehouse, actual_qty
			from `tabStock Ledger Entry` where voucher_type = %s
			and voucher_no = %s order by item_code, warehouse, actual_qty""",
			(voucher_type, voucher_no), as_list=1)
		self.assertTrue(sle)
		sle.sort(key=lambda x: x[0])

		for i, sle in enumerate(sle):
			self.assertEquals(expected_sle[i][0], sle[0])
			self.assertEquals(expected_sle[i][1], sle[1])
			self.assertEquals(expected_sle[i][2], sle[2])

	def check_gl_entries(self, voucher_type, voucher_no, expected_gl_entries):
		expected_gl_entries.sort(key=lambda x: x[0])

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type=%s and voucher_no=%s
			order by account asc, debit asc""", (voucher_type, voucher_no), as_list=1)

		self.assertTrue(gl_entries)
		gl_entries.sort(key=lambda x: x[0])
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_gl_entries[i][0], gle[0])
			self.assertEquals(expected_gl_entries[i][1], gle[1])
			self.assertEquals(expected_gl_entries[i][2], gle[2])

	def test_serial_no_not_reqd(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].serial_no = "ABCD"
		se.insert()
		self.assertRaises(SerialNoNotRequiredError, se.submit)

	def test_serial_no_reqd(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 2
		se.get("items")[0].transfer_qty = 2
		se.insert()
		self.assertRaises(SerialNoRequiredError, se.submit)

	def test_serial_no_qty_more(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 2
		se.get("items")[0].serial_no = "ABCD\nEFGH\nXYZ"
		se.get("items")[0].transfer_qty = 2
		se.insert()
		self.assertRaises(SerialNoQtyError, se.submit)

	def test_serial_no_qty_less(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 2
		se.get("items")[0].serial_no = "ABCD"
		se.get("items")[0].transfer_qty = 2
		se.insert()
		self.assertRaises(SerialNoQtyError, se.submit)

	def test_serial_no_transfer_in(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 2
		se.get("items")[0].serial_no = "ABCD\nEFGH"
		se.get("items")[0].transfer_qty = 2
		se.insert()
		se.submit()

		self.assertTrue(frappe.db.exists("Serial No", "ABCD"))
		self.assertTrue(frappe.db.exists("Serial No", "EFGH"))

		se.cancel()
		self.assertFalse(frappe.db.get_value("Serial No", "ABCD", "warehouse"))

	def test_serial_no_not_exists(self):
		frappe.db.sql("delete from `tabSerial No` where name in ('ABCD', 'EFGH')")
		make_serialized_item(target_warehouse="_Test Warehouse 1 - _TC")
		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Issue"
		se.get("items")[0].item_code = "_Test Serialized Item With Series"
		se.get("items")[0].qty = 2
		se.get("items")[0].s_warehouse = "_Test Warehouse 1 - _TC"
		se.get("items")[0].t_warehouse = None
		se.get("items")[0].serial_no = "ABCD\nEFGH"
		se.get("items")[0].transfer_qty = 2
		se.insert()

		self.assertRaises(SerialNoNotExistsError, se.submit)

	def test_serial_duplicate(self):
		se, serial_nos = self.test_serial_by_series()

		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item With Series"
		se.get("items")[0].qty = 1
		se.get("items")[0].serial_no = serial_nos[0]
		se.get("items")[0].transfer_qty = 1
		se.insert()
		self.assertRaises(SerialNoDuplicateError, se.submit)

	def test_serial_by_series(self):
		se = make_serialized_item()

		serial_nos = get_serial_nos(se.get("items")[0].serial_no)

		self.assertTrue(frappe.db.exists("Serial No", serial_nos[0]))
		self.assertTrue(frappe.db.exists("Serial No", serial_nos[1]))

		return se, serial_nos

	def test_serial_item_error(self):
		se, serial_nos = self.test_serial_by_series()
		make_serialized_item("_Test Serialized Item", "ABCD\nEFGH")

		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Transfer"
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 1
		se.get("items")[0].transfer_qty = 1
		se.get("items")[0].serial_no = serial_nos[0]
		se.get("items")[0].s_warehouse = "_Test Warehouse - _TC"
		se.get("items")[0].t_warehouse = "_Test Warehouse 1 - _TC"
		se.insert()
		self.assertRaises(SerialNoItemError, se.submit)

	def test_serial_move(self):
		se = make_serialized_item()
		serial_no = get_serial_nos(se.get("items")[0].serial_no)[0]

		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Transfer"
		se.get("items")[0].item_code = "_Test Serialized Item With Series"
		se.get("items")[0].qty = 1
		se.get("items")[0].transfer_qty = 1
		se.get("items")[0].serial_no = serial_no
		se.get("items")[0].s_warehouse = "_Test Warehouse - _TC"
		se.get("items")[0].t_warehouse = "_Test Warehouse 1 - _TC"
		se.insert()
		se.submit()
		self.assertTrue(frappe.db.get_value("Serial No", serial_no, "warehouse"), "_Test Warehouse 1 - _TC")

		se.cancel()
		self.assertTrue(frappe.db.get_value("Serial No", serial_no, "warehouse"), "_Test Warehouse - _TC")

	def test_serial_warehouse_error(self):
		make_serialized_item(target_warehouse="_Test Warehouse 1 - _TC")

		t = make_serialized_item()
		serial_nos = get_serial_nos(t.get("items")[0].serial_no)

		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Transfer"
		se.get("items")[0].item_code = "_Test Serialized Item With Series"
		se.get("items")[0].qty = 1
		se.get("items")[0].transfer_qty = 1
		se.get("items")[0].serial_no = serial_nos[0]
		se.get("items")[0].s_warehouse = "_Test Warehouse 1 - _TC"
		se.get("items")[0].t_warehouse = "_Test Warehouse - _TC"
		se.insert()
		self.assertRaises(SerialNoWarehouseError, se.submit)

	def test_serial_cancel(self):
		se, serial_nos = self.test_serial_by_series()
		se.cancel()

		serial_no = get_serial_nos(se.get("items")[0].serial_no)[0]
		self.assertFalse(frappe.db.get_value("Serial No", serial_no, "warehouse"))

	def test_warehouse_company_validation(self):
		company = frappe.db.get_value('Warehouse', '_Test Warehouse 2 - _TC1', 'company')
		set_perpetual_inventory(0, company)
		frappe.get_doc("User", "test2@example.com")\
			.add_roles("Sales User", "Sales Manager", "Stock User", "Stock Manager")
		frappe.set_user("test2@example.com")

		from erpnext.stock.utils import InvalidWarehouseCompany
		st1 = frappe.copy_doc(test_records[0])
		st1.get("items")[0].t_warehouse="_Test Warehouse 2 - _TC1"
		st1.insert()
		self.assertRaises(InvalidWarehouseCompany, st1.submit)

	# permission tests
	def test_warehouse_user(self):
		for role in ("Stock User", "Sales User"):
			set_user_permission_doctypes(doctype="Stock Entry", role=role,
				apply_user_permissions=1, user_permission_doctypes=["Warehouse"])

		frappe.defaults.add_default("Warehouse", "_Test Warehouse 1 - _TC", "test@example.com", "User Permission")
		frappe.defaults.add_default("Warehouse", "_Test Warehouse 2 - _TC1", "test2@example.com", "User Permission")
		test_user = frappe.get_doc("User", "test@example.com")
		test_user.add_roles("Sales User", "Sales Manager", "Stock User")
		test_user.remove_roles("Stock Manager")

		frappe.get_doc("User", "test2@example.com")\
			.add_roles("Sales User", "Sales Manager", "Stock User", "Stock Manager")

		frappe.set_user("test@example.com")
		st1 = frappe.copy_doc(test_records[0])
		st1.company = "_Test Company 1"
		set_perpetual_inventory(0, st1.company)
		st1.get("items")[0].t_warehouse="_Test Warehouse 2 - _TC1"
		self.assertRaises(frappe.PermissionError, st1.insert)

		frappe.set_user("test2@example.com")
		st1 = frappe.copy_doc(test_records[0])
		st1.company = "_Test Company 1"
		st1.get("items")[0].t_warehouse="_Test Warehouse 2 - _TC1"
		st1.get("items")[0].expense_account = "Stock Adjustment - _TC1"
		st1.get("items")[0].cost_center = "Main - _TC1"
		st1.insert()
		st1.submit()

		frappe.defaults.clear_default("Warehouse", "_Test Warehouse 1 - _TC",
			"test@example.com", parenttype="User Permission")
		frappe.defaults.clear_default("Warehouse", "_Test Warehouse 2 - _TC1",
			"test2@example.com", parenttype="User Permission")

	def test_freeze_stocks(self):
		frappe.db.set_value('Stock Settings', None,'stock_auth_role', '')

		# test freeze_stocks_upto
		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto", add_days(nowdate(), 5))
		se = frappe.copy_doc(test_records[0]).insert()
		self.assertRaises(StockFreezeError, se.submit)

		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto", '')

		# test freeze_stocks_upto_days
		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto_days", 7)
		se = frappe.copy_doc(test_records[0])
		se.set_posting_time = 1
		se.posting_date = add_days(nowdate(), -15)
		se.insert()
		self.assertRaises(StockFreezeError, se.submit)
		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto_days", 0)

	def test_production_order(self):
		from erpnext.manufacturing.doctype.production_order.production_order \
			import make_stock_entry as _make_stock_entry
		bom_no, bom_operation_cost = frappe.db.get_value("BOM", {"item": "_Test FG Item 2",
			"is_default": 1, "docstatus": 1}, ["name", "operating_cost"])

		production_order = frappe.new_doc("Production Order")
		production_order.update({
			"company": "_Test Company",
			"fg_warehouse": "_Test Warehouse 1 - _TC",
			"production_item": "_Test FG Item 2",
			"bom_no": bom_no,
			"qty": 1.0,
			"stock_uom": "_Test UOM",
			"wip_warehouse": "_Test Warehouse - _TC",
			"additional_operating_cost": 1000
		})
		production_order.insert()
		production_order.submit()

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, basic_rate=100)

		stock_entry = _make_stock_entry(production_order.name, "Manufacture", 1)

		rm_cost = 0
		for d in stock_entry.get("items"):
			if d.s_warehouse:
				rm_cost += flt(d.amount)

		fg_cost = filter(lambda x: x.item_code=="_Test FG Item 2", stock_entry.get("items"))[0].amount
		self.assertEqual(fg_cost,
			flt(rm_cost + bom_operation_cost + production_order.additional_operating_cost, 2))


	def test_variant_production_order(self):
		bom_no = frappe.db.get_value("BOM", {"item": "_Test Variant Item",
			"is_default": 1, "docstatus": 1})

		production_order = frappe.new_doc("Production Order")
		production_order.update({
			"company": "_Test Company",
			"fg_warehouse": "_Test Warehouse 1 - _TC",
			"production_item": "_Test Variant Item-S",
			"bom_no": bom_no,
			"qty": 1.0,
			"stock_uom": "_Test UOM",
			"wip_warehouse": "_Test Warehouse - _TC"
		})
		production_order.insert()
		production_order.submit()

		from erpnext.manufacturing.doctype.production_order.production_order import make_stock_entry

		stock_entry = frappe.get_doc(make_stock_entry(production_order.name, "Manufacture", 1))
		stock_entry.insert()
		self.assertTrue("_Test Variant Item-S" in [d.item_code for d in stock_entry.items])

	def test_same_serial_nos_in_repack_or_manufacture_entries(self):
		s1 = make_serialized_item(target_warehouse="_Test Warehouse - _TC")
		serial_nos = s1.get("items")[0].serial_no

		s2 = make_stock_entry(item_code="_Test Serialized Item With Series", source="_Test Warehouse - _TC",
			qty=2, basic_rate=100, purpose="Repack", serial_no=serial_nos, do_not_save=True)

		s2.append("items", {
			"item_code": "_Test Serialized Item",
			"t_warehouse": "_Test Warehouse - _TC",
			"qty": 2,
			"basic_rate": 120,
			"expense_account": "Stock Adjustment - _TC",
			"conversion_factor": 1.0,
			"cost_center": "_Test Cost Center - _TC",
			"serial_no": serial_nos
		})

		s2.submit()
		s2.cancel()

def make_serialized_item(item_code=None, serial_no=None, target_warehouse=None):
	se = frappe.copy_doc(test_records[0])
	se.get("items")[0].item_code = item_code or "_Test Serialized Item With Series"
	se.get("items")[0].serial_no = serial_no
	se.get("items")[0].qty = 2
	se.get("items")[0].transfer_qty = 2

	if target_warehouse:
		se.get("items")[0].t_warehouse = target_warehouse

	se.insert()
	se.submit()
	return se

def get_qty_after_transaction(**args):
	args = frappe._dict(args)

	last_sle = get_previous_sle({
		"item_code": args.item_code or "_Test Item",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"posting_date": args.posting_date or nowdate(),
		"posting_time": args.posting_time or nowtime()
	})

	return flt(last_sle.get("qty_after_transaction"))

test_records = frappe.get_test_records('Stock Entry')
