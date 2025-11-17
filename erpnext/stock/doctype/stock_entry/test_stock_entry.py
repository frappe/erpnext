# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from datetime import date, datetime
from unittest.mock import patch

import frappe.utils
from frappe.desk.query_report import run
from frappe.permissions import add_user_permission, remove_user_permission
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, cstr, flt, get_time, getdate, nowtime, today

from erpnext.accounts.doctype.account.test_account import get_inventory_account
from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
from erpnext.controllers.accounts_controller import InvalidQtyError
from erpnext.stock.doctype.item.test_item import (
	create_item,
	make_item,
	make_item_variant,
	set_item_variant_settings,
)
from erpnext.stock.doctype.material_request.material_request import make_stock_entry as make_mr_se
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_nos_from_bundle,
	make_serial_batch_bundle,
)
from erpnext.stock.doctype.serial_no.serial_no import *
from erpnext.stock.doctype.stock_entry.stock_entry import (
	FinishedGoodError,
	create_serial_and_batch_bundle,
	get_items_from_subcontract_order,
	make_stock_in_entry,
	move_sample_to_retention_warehouse,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import StockFreezeError
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import (
	OpeningEntryAccountError,
)
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.serial_batch_bundle import SerialBatchCreation
from erpnext.stock.stock_ledger import NegativeStockError, get_previous_sle
from erpnext.stock.utils import get_or_create_fiscal_year


def get_sle(**args):
	condition, values = "", []
	for key, value in args.items():
		condition += " and " if condition else " where "
		condition += f"`{key}`=%s"
		values.append(value)

	return frappe.db.sql(
		"""select * from `tabStock Ledger Entry` %s
		order by (posting_date || ' ' || posting_time)::timestamp desc, creation desc limit 1"""
		% condition,
		values,
		as_dict=1,
	)


class TestStockEntry(FrappeTestCase):
	@classmethod
	def setUpClass(self):
		setup_defaults_data()

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def test_stock_entry_qty(self):
		item_code = "_Test Item 2"
		warehouse = "_Test Warehouse - _TC"
		se = make_stock_entry(item_code=item_code, target=warehouse, qty=0, do_not_save=True)
		with self.assertRaises(InvalidQtyError):
			se.save()

		# No error with qty=1
		se.items[0].qty = 1
		se.save()
		self.assertEqual(se.items[0].qty, 1)

	def test_fifo(self):
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)
		item_code = "_Test Item 2"
		warehouse = "_Test Warehouse - _TC"

		create_stock_reconciliation(
			item_code="_Test Item 2", warehouse="_Test Warehouse - _TC", qty=0, rate=100
		)

		make_stock_entry(item_code=item_code, target=warehouse, qty=1, basic_rate=10)
		sle = get_sle(item_code=item_code, warehouse=warehouse)[0]

		self.assertEqual([[1, 10]], frappe.safe_eval(sle.stock_queue))

		# negative qty
		make_stock_entry(item_code=item_code, source=warehouse, qty=2, basic_rate=10)
		sle = get_sle(item_code=item_code, warehouse=warehouse)[0]

		self.assertEqual([[-1, 10]], frappe.safe_eval(sle.stock_queue))

		# further negative
		make_stock_entry(item_code=item_code, source=warehouse, qty=1)
		sle = get_sle(item_code=item_code, warehouse=warehouse)[0]

		self.assertEqual([[-2, 10]], frappe.safe_eval(sle.stock_queue))

		# move stock to positive
		make_stock_entry(item_code=item_code, target=warehouse, qty=3, basic_rate=20)
		sle = get_sle(item_code=item_code, warehouse=warehouse)[0]
		self.assertEqual([[1, 20]], frappe.safe_eval(sle.stock_queue))

		# incoming entry with diff rate
		make_stock_entry(item_code=item_code, target=warehouse, qty=1, basic_rate=30)
		sle = get_sle(item_code=item_code, warehouse=warehouse)[0]

		self.assertEqual([[1, 20], [1, 30]], frappe.safe_eval(sle.stock_queue))

		frappe.db.set_default("allow_negative_stock", 0)

	def test_auto_material_request(self):
		make_item_variant()
		self._test_auto_material_request("_Test Item")
		self._test_auto_material_request("_Test Item", material_request_type="Transfer")

	def test_barcode_item_stock_entry(self):
		item_code = make_item("_Test Item Stock Entry For Barcode", barcode="BDD-1234567890")

		se = make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=1, basic_rate=100)
		self.assertEqual(se.items[0].barcode, "BDD-1234567890")

	def test_auto_material_request_for_variant(self):
		fields = [{"field_name": "reorder_levels"}]
		set_item_variant_settings(fields)
		make_item_variant()
		template = frappe.get_doc("Item", "_Test Variant Item")

		if not template.reorder_levels:
			template.append(
				"reorder_levels",
				{
					"material_request_type": "Purchase",
					"warehouse": "_Test Warehouse - _TC",
					"warehouse_reorder_level": 20,
					"warehouse_reorder_qty": 20,
				},
			)

		template.save()
		self._test_auto_material_request("_Test Variant Item-S")

	def test_auto_material_request_for_warehouse_group(self):
		self._test_auto_material_request(
			"_Test Item Warehouse Group Wise Reorder", warehouse="_Test Warehouse Group-C1 - _TC"
		)

	def _test_auto_material_request(
		self, item_code, material_request_type="Purchase", warehouse="_Test Warehouse - _TC"
	):
		variant = frappe.get_doc("Item", item_code)

		projected_qty, actual_qty = frappe.db.get_value(
			"Bin", {"item_code": item_code, "warehouse": warehouse}, ["projected_qty", "actual_qty"]
		) or [0, 0]

		# stock entry reqd for auto-reorder
		create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=actual_qty + abs(projected_qty) + 10, rate=100
		)

		projected_qty = (
			frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "projected_qty") or 0
		)

		frappe.db.set_single_value("Stock Settings", "auto_indent", 1)

		# update re-level qty so that it is more than projected_qty
		if projected_qty >= variant.reorder_levels[0].warehouse_reorder_level:
			variant.reorder_levels[0].warehouse_reorder_level += projected_qty
			variant.reorder_levels[0].material_request_type = material_request_type
			variant.save()

		from erpnext.stock.reorder_item import reorder_item

		mr_list = reorder_item()

		frappe.db.set_single_value("Stock Settings", "auto_indent", 0)

		items = []
		for mr in mr_list:
			for d in mr.items:
				items.append(d.item_code)

		self.assertTrue(item_code in items)

	def test_add_to_transit_entry(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		item_code = "_Test Transit Item"
		company = "_Test Company"

		create_warehouse("Test From Warehouse")
		create_warehouse("Test Transit Warehouse")
		create_warehouse("Test To Warehouse")

		create_item(
			item_code=item_code,
			is_stock_item=1,
			is_purchase_item=1,
			company=company,
		)

		# create inward stock entry
		make_stock_entry(
			item_code=item_code,
			target="Test From Warehouse - _TC",
			qty=10,
			basic_rate=100,
			expense_account="Stock Adjustment - _TC",
			cost_center="Main - _TC",
		)

		transit_entry = make_stock_entry(
			item_code=item_code,
			source="Test From Warehouse - _TC",
			target="Test Transit Warehouse - _TC",
			add_to_transit=1,
			stock_entry_type="Material Transfer",
			purpose="Material Transfer",
			qty=10,
			basic_rate=100,
			expense_account="Stock Adjustment - _TC",
			cost_center="Main - _TC",
		)

		end_transit_entry = make_stock_in_entry(transit_entry.name)

		self.assertEqual(end_transit_entry.stock_entry_type, "Material Transfer")
		self.assertEqual(end_transit_entry.purpose, "Material Transfer")
		self.assertEqual(transit_entry.name, end_transit_entry.outgoing_stock_entry)
		self.assertEqual(transit_entry.name, end_transit_entry.items[0].against_stock_entry)
		self.assertEqual(transit_entry.items[0].name, end_transit_entry.items[0].ste_detail)

		# create add to transit

	def test_material_receipt_gl_entry(self):
		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")

		mr = make_stock_entry(
			item_code="_Test Item",
			target="Stores - TCP1",
			company=company,
			qty=50,
			basic_rate=100,
			expense_account="Stock Adjustment - TCP1",
		)

		stock_in_hand_account = get_inventory_account(mr.company, mr.get("items")[0].t_warehouse)
		self.check_stock_ledger_entries("Stock Entry", mr.name, [["_Test Item", "Stores - TCP1", 50.0]])

		self.check_gl_entries(
			"Stock Entry",
			mr.name,
			sorted([[stock_in_hand_account, 5000.0, 0.0], ["Stock Adjustment - TCP1", 0.0, 5000.0]]),
		)

		mr.cancel()

		self.assertTrue(
			frappe.db.sql(
				"""select * from `tabStock Ledger Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""",
				mr.name,
			)
		)

		self.assertTrue(
			frappe.db.sql(
				"""select * from `tabGL Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""",
				mr.name,
			)
		)

	def test_material_issue_gl_entry(self):
		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")
		make_stock_entry(
			item_code="_Test Item",
			target="Stores - TCP1",
			company=company,
			qty=50,
			basic_rate=100,
			expense_account="Stock Adjustment - TCP1",
		)

		mi = make_stock_entry(
			item_code="_Test Item",
			source="Stores - TCP1",
			company=company,
			qty=40,
			expense_account="Stock Adjustment - TCP1",
		)

		self.check_stock_ledger_entries("Stock Entry", mi.name, [["_Test Item", "Stores - TCP1", -40.0]])

		stock_in_hand_account = get_inventory_account(mi.company, "Stores - TCP1")
		stock_value_diff = abs(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Stock Entry", "voucher_no": mi.name},
				"stock_value_difference",
			)
		)

		self.check_gl_entries(
			"Stock Entry",
			mi.name,
			sorted(
				[
					[stock_in_hand_account, 0.0, stock_value_diff],
					["Stock Adjustment - TCP1", stock_value_diff, 0.0],
				]
			),
		)
		mi.cancel()

	def test_material_transfer_gl_entry(self):
		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")

		item_code = "Hand Sanitizer - 001"
		create_item(
			item_code=item_code,
			is_stock_item=1,
			is_purchase_item=1,
			opening_stock=1000,
			valuation_rate=10,
			company=company,
			warehouse="Stores - TCP1",
		)

		mtn = make_stock_entry(
			item_code=item_code,
			source="Stores - TCP1",
			target="Finished Goods - TCP1",
			qty=45,
			company=company,
		)

		self.check_stock_ledger_entries(
			"Stock Entry",
			mtn.name,
			[[item_code, "Stores - TCP1", -45.0], [item_code, "Finished Goods - TCP1", 45.0]],
		)

		source_warehouse_account = get_inventory_account(mtn.company, mtn.get("items")[0].s_warehouse)

		target_warehouse_account = get_inventory_account(mtn.company, mtn.get("items")[0].t_warehouse)

		if source_warehouse_account == target_warehouse_account:
			# no gl entry as both source and target warehouse has linked to same account.
			self.assertFalse(
				frappe.db.sql(
					"""select * from `tabGL Entry`
				where voucher_type='Stock Entry' and voucher_no=%s""",
					mtn.name,
					as_dict=1,
				)
			)

		else:
			stock_value_diff = abs(
				frappe.db.get_value(
					"Stock Ledger Entry",
					{"voucher_type": "Stock Entry", "voucher_no": mtn.name, "warehouse": "Stores - TCP1"},
					"stock_value_difference",
				)
			)

			self.check_gl_entries(
				"Stock Entry",
				mtn.name,
				sorted(
					[
						[source_warehouse_account, 0.0, stock_value_diff],
						[target_warehouse_account, stock_value_diff, 0.0],
					]
				),
			)

		mtn.cancel()

	def test_repack_multiple_fg(self):
		"Test `is_finished_item` for one item repacked into two items."
		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=100, basic_rate=100)

		repack = frappe.copy_doc(test_records[3])
		repack.posting_date = nowdate()
		repack.posting_time = nowtime()

		repack.items[0].qty = 100.0
		repack.items[0].transfer_qty = 100.0
		repack.items[1].qty = 50.0

		repack.append(
			"items",
			{
				"conversion_factor": 1.0,
				"cost_center": "_Test Cost Center - _TC",
				"doctype": "Stock Entry Detail",
				"expense_account": "Stock Adjustment - _TC",
				"basic_rate": 150,
				"item_code": "_Test Item 2",
				"parentfield": "items",
				"qty": 50.0,
				"stock_uom": "_Test UOM",
				"t_warehouse": "_Test Warehouse - _TC",
				"transfer_qty": 50.0,
				"uom": "_Test UOM",
			},
		)
		repack.set_stock_entry_type()
		repack.insert()

		self.assertEqual(repack.items[1].is_finished_item, 1)
		self.assertEqual(repack.items[2].is_finished_item, 1)

		repack.items[1].is_finished_item = 0
		repack.items[2].is_finished_item = 0

		# must raise error if 0 fg in repack entry
		self.assertRaises(FinishedGoodError, repack.validate_finished_goods)

		repack.delete()  # teardown

	def test_repack_no_change_in_valuation(self):
		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, basic_rate=100)
		make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", qty=50, basic_rate=100
		)

		repack = frappe.copy_doc(test_records[3])
		repack.posting_date = nowdate()
		repack.posting_time = nowtime()
		repack.set_stock_entry_type()
		repack.insert()
		repack.submit()

		self.check_stock_ledger_entries(
			"Stock Entry",
			repack.name,
			[
				["_Test Item", "_Test Warehouse - _TC", -50.0],
				["_Test Item Home Desktop 100", "_Test Warehouse - _TC", 1],
			],
		)

		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Stock Entry' and voucher_no=%s
			order by account desc""",
			repack.name,
			as_dict=1,
		)
		self.assertFalse(gl_entries)

	def test_repack_with_additional_costs(self):
		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")

		make_stock_entry(
			item_code="_Test Item",
			target="Stores - TCP1",
			company=company,
			qty=50,
			basic_rate=100,
			expense_account="Stock Adjustment - TCP1",
		)

		repack = make_stock_entry(company=company, purpose="Repack", do_not_save=True)
		repack.posting_date = nowdate()
		repack.posting_time = nowtime()

		default_expense_account = frappe.get_value("Company", company, "default_expense_account")

		items = get_multiple_items()
		repack.items = []
		for item in items:
			repack.append("items", item)

		repack.set(
			"additional_costs",
			[
				{
					"expense_account": default_expense_account,
					"description": "Actual Operating Cost",
					"amount": 1000,
				},
				{
					"expense_account": default_expense_account,
					"description": "Additional Operating Cost",
					"amount": 200,
				},
			],
		)

		repack.set_stock_entry_type()
		repack.insert()
		repack.submit()

		stock_in_hand_account = get_inventory_account(repack.company, repack.get("items")[1].t_warehouse)
		rm_stock_value_diff = abs(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Stock Entry", "voucher_no": repack.name, "item_code": "_Test Item"},
				"stock_value_difference",
			)
		)

		fg_stock_value_diff = abs(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{
					"voucher_type": "Stock Entry",
					"voucher_no": repack.name,
					"item_code": "_Test Item Home Desktop 100",
				},
				"stock_value_difference",
			)
		)

		stock_value_diff = flt(fg_stock_value_diff - rm_stock_value_diff, 2)

		self.assertEqual(stock_value_diff, 1200)

		self.check_gl_entries(
			"Stock Entry",
			repack.name,
			sorted([[stock_in_hand_account, 1200, 0.0], ["Cost of Goods Sold - TCP1", 0.0, 1200.0]]),
		)

	def check_stock_ledger_entries(self, voucher_type, voucher_no, expected_sle):
		expected_sle.sort(key=lambda x: x[1])

		# check stock ledger entries
		sle = frappe.db.sql(
			"""select item_code, warehouse, actual_qty
			from `tabStock Ledger Entry` where voucher_type = %s
			and voucher_no = %s order by item_code, warehouse, actual_qty""",
			(voucher_type, voucher_no),
			as_list=1,
		)
		self.assertTrue(sle)
		sle.sort(key=lambda x: x[1])

		for i, sle_value in enumerate(sle):
			self.assertEqual(expected_sle[i][0], sle_value[0])
			self.assertEqual(expected_sle[i][1], sle_value[1])
			self.assertEqual(expected_sle[i][2], sle_value[2])

	def check_gl_entries(self, voucher_type, voucher_no, expected_gl_entries):
		expected_gl_entries.sort(key=lambda x: x[0])

		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type=%s and voucher_no=%s
			order by account asc, debit asc""",
			(voucher_type, voucher_no),
			as_list=1,
		)

		self.assertTrue(gl_entries)
		gl_entries.sort(key=lambda x: x[0])
		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gl_entries[i][0], gle[0])
			self.assertEqual(expected_gl_entries[i][1], gle[1])
			self.assertEqual(expected_gl_entries[i][2], gle[2])

	def test_serial_no_not_reqd(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].serial_no = "ABCD"

		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": se.get("items")[0].item_code,
					"warehouse": se.get("items")[0].t_warehouse,
					"company": se.company,
					"qty": 2,
					"voucher_type": "Stock Entry",
					"serial_nos": ["ABCD"],
					"posting_date": se.posting_date,
					"posting_time": se.posting_time,
					"do_not_save": True,
				}
			)
		)

		self.assertRaises(frappe.ValidationError, bundle_id.make_serial_and_batch_bundle)

	def test_serial_no_reqd(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 2
		se.get("items")[0].transfer_qty = 2

		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": se.get("items")[0].item_code,
					"warehouse": se.get("items")[0].t_warehouse,
					"company": se.company,
					"qty": 2,
					"voucher_type": "Stock Entry",
					"posting_date": se.posting_date,
					"posting_time": se.posting_time,
					"do_not_save": True,
				}
			)
		)

		self.assertRaises(frappe.ValidationError, bundle_id.make_serial_and_batch_bundle)

	def test_serial_no_qty_less(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 2
		se.get("items")[0].serial_no = "ABCD"
		se.get("items")[0].transfer_qty = 2

		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": se.get("items")[0].item_code,
					"warehouse": se.get("items")[0].t_warehouse,
					"company": se.company,
					"qty": 2,
					"serial_nos": ["ABCD"],
					"voucher_type": "Stock Entry",
					"posting_date": se.posting_date,
					"posting_time": se.posting_time,
					"do_not_save": True,
				}
			)
		)

		self.assertRaises(frappe.ValidationError, bundle_id.make_serial_and_batch_bundle)

	def test_serial_no_transfer_in(self):
		serial_nos = ["ABCD1", "EFGH1"]
		for serial_no in serial_nos:
			if not frappe.db.exists("Serial No", serial_no):
				doc = frappe.new_doc("Serial No")
				doc.serial_no = serial_no
				doc.item_code = "_Test Serialized Item"
				doc.insert(ignore_permissions=True)

		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 2
		se.get("items")[0].transfer_qty = 2
		se.set_stock_entry_type()

		se.get("items")[0].serial_and_batch_bundle = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": se.get("items")[0].item_code,
					"warehouse": se.get("items")[0].t_warehouse,
					"company": se.company,
					"qty": 2,
					"voucher_type": "Stock Entry",
					"serial_nos": serial_nos,
					"posting_date": se.posting_date,
					"posting_time": se.posting_time,
					"do_not_submit": True,
				}
			)
		).name

		se.insert()
		se.submit()

		self.assertTrue(frappe.db.get_value("Serial No", "ABCD1", "warehouse"))
		self.assertTrue(frappe.db.get_value("Serial No", "EFGH1", "warehouse"))

		se.cancel()
		self.assertFalse(frappe.db.get_value("Serial No", "ABCD1", "warehouse"))

	def test_serial_by_series(self):
		se = make_serialized_item()

		serial_nos = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)

		self.assertTrue(frappe.db.exists("Serial No", serial_nos[0]))
		self.assertTrue(frappe.db.exists("Serial No", serial_nos[1]))

		return se, serial_nos

	def test_serial_move(self):
		se = make_serialized_item()
		serial_no = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)[0]
		frappe.flags.use_serial_and_batch_fields = True

		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Transfer"
		se.get("items")[0].item_code = "_Test Serialized Item With Series"
		se.get("items")[0].qty = 1
		se.get("items")[0].transfer_qty = 1
		se.get("items")[0].serial_no = [serial_no]
		se.get("items")[0].s_warehouse = "_Test Warehouse - _TC"
		se.get("items")[0].t_warehouse = "_Test Warehouse 1 - _TC"
		se.set_stock_entry_type()
		se.insert()
		se.submit()
		self.assertTrue(frappe.db.get_value("Serial No", serial_no, "warehouse"), "_Test Warehouse 1 - _TC")

		se.cancel()
		self.assertTrue(frappe.db.get_value("Serial No", serial_no, "warehouse"), "_Test Warehouse - _TC")
		frappe.flags.use_serial_and_batch_fields = False

	def test_serial_cancel(self):
		se, serial_nos = self.test_serial_by_series()
		se.load_from_db()
		serial_no = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)[0]

		se.cancel()
		self.assertFalse(frappe.db.get_value("Serial No", serial_no, "warehouse"))

	def test_serial_batch_item_stock_entry(self):
		"""
		Behaviour: 1) Submit Stock Entry (Receipt) with Serial & Batched Item
		2) Cancel same Stock Entry
		Expected Result: 1) Batch is created with Reference in Serial No
		2) Batch is deleted and Serial No is Inactive
		"""
		from erpnext.stock.doctype.batch.batch import get_batch_qty

		item = frappe.db.exists("Item", {"item_name": "Batched and Serialised Item"})
		if not item:
			item = create_item("Batched and Serialised Item")
			item.has_batch_no = 1
			item.create_new_batch = 1
			item.has_serial_no = 1
			item.batch_number_series = "B-BATCH-.##"
			item.serial_no_series = "S-.####"
			item.save()
		else:
			item = frappe.get_doc("Item", {"item_name": "Batched and Serialised Item"})

		se = make_stock_entry(item_code=item.item_code, target="_Test Warehouse - _TC", qty=1, basic_rate=100)
		batch_no = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)
		serial_no = get_serial_nos_from_bundle(se.items[0].serial_and_batch_bundle)[0]
		batch_qty = get_batch_qty(batch_no, "_Test Warehouse - _TC", item.item_code)

		batch_in_serial_no = frappe.db.get_value("Serial No", serial_no, "batch_no")
		self.assertEqual(batch_in_serial_no, batch_no)

		self.assertEqual(batch_qty, 1)

		se.cancel()

		batch_in_serial_no = frappe.db.get_value("Serial No", serial_no, "batch_no")
		self.assertEqual(frappe.db.get_value("Serial No", serial_no, "warehouse"), None)

	def test_warehouse_company_validation(self):
		frappe.db.get_value("Warehouse", "_Test Warehouse 2 - _TC1", "company")
		frappe.get_doc("User", "test2@example.com").add_roles(
			"Sales User", "Sales Manager", "Stock User", "Stock Manager"
		)
		frappe.set_user("test2@example.com")

		from erpnext.stock.utils import InvalidWarehouseCompany

		st1 = frappe.copy_doc(test_records[0])
		st1.get("items")[0].t_warehouse = "_Test Warehouse 2 - _TC1"
		st1.set_stock_entry_type()
		st1.insert()
		self.assertRaises(InvalidWarehouseCompany, st1.submit)

	# permission tests
	def test_warehouse_user(self):
		add_user_permission("Warehouse", "_Test Warehouse 1 - _TC", "test@example.com")
		add_user_permission("Warehouse", "_Test Warehouse 2 - _TC1", "test2@example.com")
		add_user_permission("Company", "_Test Company 1", "test2@example.com")
		test_user = frappe.get_doc("User", "test@example.com")
		test_user.add_roles("Sales User", "Sales Manager", "Stock User")
		test_user.remove_roles("Stock Manager", "System Manager")

		frappe.get_doc("User", "test2@example.com").add_roles(
			"Sales User", "Sales Manager", "Stock User", "Stock Manager"
		)

		st1 = frappe.copy_doc(test_records[0])
		st1.company = "_Test Company 1"

		frappe.set_user("test@example.com")
		st1.get("items")[0].t_warehouse = "_Test Warehouse 2 - _TC1"
		self.assertRaises(frappe.PermissionError, st1.insert)

		test_user.add_roles("System Manager")

		frappe.set_user("test2@example.com")
		st1 = frappe.copy_doc(test_records[0])
		st1.company = "_Test Company 1"
		st1.get("items")[0].t_warehouse = "_Test Warehouse 2 - _TC1"
		st1.get("items")[0].expense_account = "Stock Adjustment - _TC1"
		st1.get("items")[0].cost_center = "Main - _TC1"
		st1.set_stock_entry_type()
		st1.insert()
		st1.submit()
		st1.cancel()

		frappe.set_user("Administrator")
		remove_user_permission("Warehouse", "_Test Warehouse 1 - _TC", "test@example.com")
		remove_user_permission("Warehouse", "_Test Warehouse 2 - _TC1", "test2@example.com")
		remove_user_permission("Company", "_Test Company 1", "test2@example.com")

	def test_freeze_stocks(self):
		frappe.db.set_single_value("Stock Settings", "stock_auth_role", "")

		# test freeze_stocks_upto
		frappe.db.set_single_value("Stock Settings", "stock_frozen_upto", add_days(nowdate(), 5))
		se = frappe.copy_doc(test_records[0]).insert()
		self.assertRaises(StockFreezeError, se.submit)

		frappe.db.set_single_value("Stock Settings", "stock_frozen_upto", "")

		# test freeze_stocks_upto_days
		frappe.db.set_single_value("Stock Settings", "stock_frozen_upto_days", -1)
		se = frappe.copy_doc(test_records[0])
		se.set_posting_time = 1
		se.posting_date = nowdate()
		se.set_stock_entry_type()
		se.insert()
		self.assertRaises(StockFreezeError, se.submit)
		frappe.db.set_single_value("Stock Settings", "stock_frozen_upto_days", 0)

	def test_work_order(self):
		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as _make_stock_entry,
		)

		bom_no, bom_operation_cost = frappe.db.get_value(
			"BOM", {"item": "_Test FG Item 2", "is_default": 1, "docstatus": 1}, ["name", "operating_cost"]
		)

		work_order = frappe.new_doc("Work Order")
		work_order.update(
			{
				"company": "_Test Company",
				"fg_warehouse": "_Test Warehouse 1 - _TC",
				"production_item": "_Test FG Item 2",
				"bom_no": bom_no,
				"qty": 1.0,
				"stock_uom": "_Test UOM",
				"wip_warehouse": "_Test Warehouse - _TC",
				"additional_operating_cost": 1000,
			}
		)
		work_order.insert()
		work_order.submit()

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, basic_rate=100)
		make_stock_entry(item_code="_Test Item 2", target="_Test Warehouse - _TC", qty=50, basic_rate=20)

		stock_entry = _make_stock_entry(work_order.name, "Manufacture", 1)

		rm_cost = 0
		for d in stock_entry.get("items"):
			if d.item_code != "_Test FG Item 2":
				rm_cost += flt(d.amount)
		fg_cost = next(filter(lambda x: x.item_code == "_Test FG Item 2", stock_entry.get("items"))).amount
		self.assertEqual(fg_cost, flt(rm_cost + bom_operation_cost + work_order.additional_operating_cost, 2))

	@change_settings("Manufacturing Settings", {"material_consumption": 1})
	def test_work_order_manufacture_with_material_consumption(self):
		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as _make_stock_entry,
		)

		bom_no = frappe.db.get_value("BOM", {"item": "_Test FG Item", "is_default": 1, "docstatus": 1})

		work_order = frappe.new_doc("Work Order")
		work_order.update(
			{
				"company": "_Test Company",
				"fg_warehouse": "_Test Warehouse 1 - _TC",
				"production_item": "_Test FG Item",
				"bom_no": bom_no,
				"qty": 1.0,
				"stock_uom": "_Test UOM",
				"wip_warehouse": "_Test Warehouse - _TC",
			}
		)
		work_order.insert()
		work_order.submit()

		make_stock_entry(item_code="_Test Item", target="Stores - _TC", qty=10, basic_rate=5000.0)
		make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="Stores - _TC", qty=10, basic_rate=1000.0
		)

		s = frappe.get_doc(_make_stock_entry(work_order.name, "Material Transfer for Manufacture", 1))
		for d in s.get("items"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		# When Stock Entry has RM and FG
		s = frappe.get_doc(_make_stock_entry(work_order.name, "Manufacture", 1))
		s.save()
		rm_cost = 0
		for d in s.get("items"):
			if d.s_warehouse:
				rm_cost += d.amount
		fg_cost = next(filter(lambda x: x.item_code == "_Test FG Item", s.get("items"))).amount
		scrap_cost = next(filter(lambda x: x.is_scrap_item, s.get("items"))).amount
		self.assertEqual(fg_cost, flt(rm_cost - scrap_cost, 2))

		# When Stock Entry has only FG + Scrap
		s.items.pop(0)
		s.items.pop(0)
		s.submit()

		rm_cost = 0
		for d in s.get("items"):
			if d.s_warehouse:
				rm_cost += d.amount
		self.assertEqual(rm_cost, 0)
		expected_fg_cost = s.get_basic_rate_for_manufactured_item(1)
		fg_cost = next(filter(lambda x: x.item_code == "_Test FG Item", s.get("items"))).amount
		self.assertEqual(flt(fg_cost, 2), flt(expected_fg_cost, 2))

	def test_variant_work_order(self):
		bom_no = frappe.db.get_value("BOM", {"item": "_Test Variant Item", "is_default": 1, "docstatus": 1})

		make_item_variant()  # make variant of _Test Variant Item if absent

		work_order = frappe.new_doc("Work Order")
		work_order.update(
			{
				"company": "_Test Company",
				"fg_warehouse": "_Test Warehouse 1 - _TC",
				"production_item": "_Test Variant Item-S",
				"bom_no": bom_no,
				"qty": 1.0,
				"stock_uom": "_Test UOM",
				"wip_warehouse": "_Test Warehouse - _TC",
				"skip_transfer": 1,
			}
		)
		work_order.insert()
		work_order.submit()

		from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

		stock_entry = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 1))
		stock_entry.insert()
		self.assertTrue("_Test Variant Item-S" in [d.item_code for d in stock_entry.items])

	def test_nagative_stock_for_batch(self):
		item = make_item(
			"_Test Batch Negative Item",
			{
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "B-BATCH-.##",
				"is_stock_item": 1,
			},
		)

		make_stock_entry(item_code=item.name, target="_Test Warehouse - _TC", qty=50, basic_rate=100)

		ste = frappe.new_doc("Stock Entry")
		ste.purpose = "Material Issue"
		ste.company = "_Test Company"
		for qty in [50, 20, 30]:
			ste.append(
				"items",
				{
					"item_code": item.name,
					"s_warehouse": "_Test Warehouse - _TC",
					"qty": qty,
					"uom": item.stock_uom,
					"stock_uom": item.stock_uom,
					"conversion_factor": 1,
					"transfer_qty": qty,
				},
			)

		ste.set_stock_entry_type()
		ste.insert()
		make_stock_entry(item_code=item.name, target="_Test Warehouse - _TC", qty=50, basic_rate=100)

		self.assertRaises(frappe.ValidationError, ste.submit)

	def test_quality_check_for_scrap_item(self):
		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as _make_stock_entry,
		)

		scrap_item = "_Test Scrap Item 1"
		make_item(scrap_item, {"is_stock_item": 1, "is_purchase_item": 0})

		bom_name = frappe.db.get_value("BOM Scrap Item", {"docstatus": 1}, "parent")
		production_item = frappe.db.get_value("BOM", bom_name, "item")

		work_order = frappe.new_doc("Work Order")
		work_order.production_item = production_item
		work_order.update(
			{
				"company": "_Test Company",
				"fg_warehouse": "_Test Warehouse 1 - _TC",
				"production_item": production_item,
				"bom_no": bom_name,
				"qty": 1.0,
				"stock_uom": frappe.db.get_value("Item", production_item, "stock_uom"),
				"skip_transfer": 1,
			}
		)

		work_order.get_items_and_operations_from_bom()
		work_order.submit()

		stock_entry = frappe.get_doc(_make_stock_entry(work_order.name, "Manufacture", 1))
		for row in stock_entry.items:
			if row.s_warehouse:
				make_stock_entry(
					item_code=row.item_code,
					target=row.s_warehouse,
					qty=row.qty,
					basic_rate=row.basic_rate or 100,
				)

			if row.is_scrap_item:
				row.item_code = scrap_item
				row.uom = frappe.db.get_value("Item", scrap_item, "stock_uom")
				row.stock_uom = frappe.db.get_value("Item", scrap_item, "stock_uom")

		stock_entry.inspection_required = 1
		stock_entry.save()

		self.assertTrue([row.item_code for row in stock_entry.items if row.is_scrap_item])

		for row in stock_entry.items:
			if not row.is_scrap_item:
				qc = frappe.get_doc(
					{
						"doctype": "Quality Inspection",
						"reference_name": stock_entry.name,
						"inspected_by": "Administrator",
						"reference_type": "Stock Entry",
						"inspection_type": "In Process",
						"status": "Accepted",
						"sample_size": 1,
						"item_code": row.item_code,
					}
				)

				qc_name = qc.submit()
				row.quality_inspection = qc_name

		stock_entry.reload()
		stock_entry.submit()
		for row in stock_entry.items:
			if row.is_scrap_item:
				self.assertFalse(row.quality_inspection)
			else:
				self.assertTrue(row.quality_inspection)

	def test_quality_check(self):
		item_code = "_Test Item For QC"
		if not frappe.db.exists("Item", item_code):
			create_item(item_code)

		repack = frappe.copy_doc(test_records[3])
		repack.inspection_required = 1
		for d in repack.items:
			if not d.s_warehouse and d.t_warehouse:
				d.item_code = item_code
				d.qty = 1
				d.uom = "Nos"
				d.stock_uom = "Nos"
				d.basic_rate = 5000

		repack.insert()
		self.assertRaises(frappe.ValidationError, repack.submit)

	def test_customer_provided_parts_se(self):
		create_item("CUST-0987", is_customer_provided_item=1, customer="_Test Customer", is_purchase_item=0)
		se = make_stock_entry(
			item_code="CUST-0987", purpose="Material Receipt", qty=4, to_warehouse="_Test Warehouse - _TC"
		)
		self.assertEqual(se.get("items")[0].allow_zero_valuation_rate, 1)
		self.assertEqual(se.get("items")[0].amount, 0)

	def test_zero_incoming_rate(self):
		"""Make sure incoming rate of 0 is allowed while consuming.

		qty  | rate | valuation rate
		 1   | 100  | 100
		 1   | 0    | 50
		-1   | 100  | 0
		-1   | 0  <--- assert this
		"""
		item_code = "_TestZeroVal"
		warehouse = "_Test Warehouse - _TC"
		create_item("_TestZeroVal")
		_receipt = make_stock_entry(item_code=item_code, qty=1, to_warehouse=warehouse, rate=100)
		receipt2 = make_stock_entry(
			item_code=item_code, qty=1, to_warehouse=warehouse, rate=0, do_not_save=True
		)
		receipt2.items[0].allow_zero_valuation_rate = 1
		receipt2.save()
		receipt2.submit()

		issue = make_stock_entry(item_code=item_code, qty=1, from_warehouse=warehouse)

		value_diff = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": issue.name, "voucher_type": "Stock Entry"},
			"stock_value_difference",
		)
		self.assertEqual(value_diff, -100)

		issue2 = make_stock_entry(item_code=item_code, qty=1, from_warehouse=warehouse)
		value_diff = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": issue2.name, "voucher_type": "Stock Entry"},
			"stock_value_difference",
		)
		self.assertEqual(value_diff, 0)

	def test_gle_for_opening_stock_entry(self):
		mr = make_stock_entry(
			item_code="_Test Item",
			target="Stores - TCP1",
			company="_Test Company with perpetual inventory",
			qty=50,
			basic_rate=100,
			expense_account="Stock Adjustment - TCP1",
			is_opening="Yes",
			do_not_save=True,
		)

		self.assertRaises(OpeningEntryAccountError, mr.save)

		mr.items[0].expense_account = "Temporary Opening - TCP1"

		mr.save()
		mr.submit()

		is_opening = frappe.db.get_value(
			"GL Entry",
			filters={"voucher_type": "Stock Entry", "voucher_no": mr.name},
			fieldname="is_opening",
		)
		self.assertEqual(is_opening, "Yes")

	def test_total_basic_amount_zero(self):
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"purpose": "Material Receipt",
				"stock_entry_type": "Material Receipt",
				"posting_date": nowdate(),
				"company": "_Test Company with perpetual inventory",
				"items": [
					{
						"item_code": "_Test Item",
						"description": "_Test Item",
						"qty": 1,
						"basic_rate": 0,
						"uom": "Nos",
						"t_warehouse": "Stores - TCP1",
						"allow_zero_valuation_rate": 1,
						"cost_center": "Main - TCP1",
					},
					{
						"item_code": "_Test Item",
						"description": "_Test Item",
						"qty": 2,
						"basic_rate": 0,
						"uom": "Nos",
						"t_warehouse": "Stores - TCP1",
						"allow_zero_valuation_rate": 1,
						"cost_center": "Main - TCP1",
					},
				],
				"additional_costs": [
					{
						"expense_account": "Miscellaneous Expenses - TCP1",
						"amount": 100,
						"description": "miscellanous",
					}
				],
			}
		)
		se.insert()
		se.submit()

		self.check_gl_entries(
			"Stock Entry",
			se.name,
			sorted([["Stock Adjustment - TCP1", 100.0, 0.0], ["Miscellaneous Expenses - TCP1", 0.0, 100.0]]),
		)

	def test_conversion_factor_change(self):
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)
		repack_entry = frappe.copy_doc(test_records[3])
		repack_entry.posting_date = nowdate()
		repack_entry.posting_time = nowtime()
		repack_entry.set_stock_entry_type()
		repack_entry.insert()

		# check current uom and conversion factor
		self.assertTrue(repack_entry.items[0].uom, "_Test UOM")
		self.assertTrue(repack_entry.items[0].conversion_factor, 1)

		# change conversion factor
		repack_entry.items[0].uom = "_Test UOM 1"
		repack_entry.items[0].stock_uom = "_Test UOM 1"
		repack_entry.items[0].conversion_factor = 2
		repack_entry.save()
		repack_entry.submit()

		self.assertEqual(repack_entry.items[0].conversion_factor, 2)
		self.assertEqual(repack_entry.items[0].uom, "_Test UOM 1")
		self.assertEqual(repack_entry.items[0].qty, 50)
		self.assertEqual(repack_entry.items[0].transfer_qty, 100)

		frappe.db.set_default("allow_negative_stock", 0)

	def test_additional_cost_distribution_manufacture(self):
		se = frappe.get_doc(
			doctype="Stock Entry",
			purpose="Manufacture",
			additional_costs=[frappe._dict(base_amount=100)],
			items=[
				frappe._dict(item_code="RM", basic_amount=10),
				frappe._dict(item_code="FG", basic_amount=20, t_warehouse="X", is_finished_item=1),
				frappe._dict(item_code="scrap", basic_amount=30, t_warehouse="X"),
			],
		)

		se.distribute_additional_costs()

		distributed_costs = [d.additional_cost for d in se.items]
		self.assertEqual([0.0, 100.0, 0.0], distributed_costs)

	def test_additional_cost_distribution_non_manufacture(self):
		se = frappe.get_doc(
			doctype="Stock Entry",
			purpose="Material Receipt",
			additional_costs=[frappe._dict(base_amount=100)],
			items=[
				frappe._dict(item_code="RECEIVED_1", basic_amount=20, t_warehouse="X"),
				frappe._dict(item_code="RECEIVED_2", basic_amount=30, t_warehouse="X"),
			],
		)

		se.distribute_additional_costs()

		distributed_costs = [d.additional_cost for d in se.items]
		self.assertEqual([40.0, 60.0], distributed_costs)

	def test_independent_manufacture_entry(self):
		"Test FG items and incoming rate calculation in Maniufacture Entry without WO or BOM linked."
		se = frappe.get_doc(
			doctype="Stock Entry",
			purpose="Manufacture",
			stock_entry_type="Manufacture",
			company="_Test Company",
			items=[
				frappe._dict(
					item_code="_Test Item", qty=1, basic_rate=200, s_warehouse="_Test Warehouse - _TC"
				),
				frappe._dict(item_code="_Test FG Item", qty=4, t_warehouse="_Test Warehouse 1 - _TC"),
			],
		)
		# SE must have atleast one FG
		self.assertRaises(FinishedGoodError, se.save)

		se.items[0].is_finished_item = 1
		se.items[1].is_finished_item = 1
		# SE cannot have multiple FGs
		self.assertRaises(FinishedGoodError, se.save)

		se.items[0].is_finished_item = 0
		se.save()

		# Check if FG cost is calculated based on RM total cost
		# RM total cost = 200, FG rate = 200/4(FG qty) =  50
		self.assertEqual(se.items[1].basic_rate, flt(se.items[0].basic_rate / 4))
		self.assertEqual(se.value_difference, 0.0)
		self.assertEqual(se.total_incoming_value, se.total_outgoing_value)

	@change_settings("Stock Settings", {"allow_negative_stock": 0})
	def test_future_negative_sle(self):
		# Initialize item, batch, warehouse, opening qty
		item_code = "_Test Future Neg Item"
		batch_no = "_Test Future Neg Batch"
		warehouses = ["_Test Future Neg Warehouse Source", "_Test Future Neg Warehouse Destination"]
		warehouse_names = initialize_records_for_future_negative_sle_test(
			item_code, batch_no, warehouses, opening_qty=2, posting_date="2021-07-01"
		)

		# Executing an illegal sequence should raise an error
		sequence_of_entries = [
			dict(
				item_code=item_code,
				qty=2,
				from_warehouse=warehouse_names[0],
				to_warehouse=warehouse_names[1],
				batch_no=batch_no,
				posting_date="2021-07-03",
				purpose="Material Transfer",
			),
			dict(
				item_code=item_code,
				qty=2,
				from_warehouse=warehouse_names[1],
				to_warehouse=warehouse_names[0],
				batch_no=batch_no,
				posting_date="2021-07-04",
				purpose="Material Transfer",
			),
			dict(
				item_code=item_code,
				qty=2,
				from_warehouse=warehouse_names[0],
				to_warehouse=warehouse_names[1],
				batch_no=batch_no,
				posting_date="2021-07-02",  # Illegal SE
				purpose="Material Transfer",
			),
		]

		self.assertRaises(NegativeStockError, create_stock_entries, sequence_of_entries)

	@change_settings("Stock Settings", {"allow_negative_stock": 0})
	def test_future_negative_sle_batch(self):
		from erpnext.stock.doctype.batch.test_batch import TestBatch

		# Initialize item, batch, warehouse, opening qty
		item_code = "_Test MultiBatch Item"
		TestBatch.make_batch_item(item_code)

		batch_nos = []  # store generate batches
		warehouse = "_Test Warehouse - _TC"

		se1 = make_stock_entry(
			item_code=item_code,
			qty=2,
			to_warehouse=warehouse,
			posting_date="2021-09-01",
			purpose="Material Receipt",
		)
		batch_nos.append(get_batch_from_bundle(se1.items[0].serial_and_batch_bundle))
		se2 = make_stock_entry(
			item_code=item_code,
			qty=2,
			to_warehouse=warehouse,
			posting_date="2021-09-03",
			purpose="Material Receipt",
		)
		batch_nos.append(get_batch_from_bundle(se2.items[0].serial_and_batch_bundle))

		with self.assertRaises(frappe.ValidationError):
			make_stock_entry(
				item_code=item_code,
				qty=1,
				from_warehouse=warehouse,
				batch_no=batch_nos[1],
				posting_date="2021-09-02",  # backdated consumption of 2nd batch
				purpose="Material Issue",
			)

	def test_multi_batch_value_diff(self):
		"""Test value difference on stock entry in case of multi-batch.
		| Stock entry | batch | qty | rate | value diff on SE             |
		| ---         | ---   | --- | ---  | ---                          |
		| receipt     | A     | 1   | 10   | 30                           |
		| receipt     | B     | 1   | 20   |                              |
		| issue       | A     | -1  | 10   | -30 (to assert after submit) |
		| issue       | B     | -1  | 20   |                              |
		"""
		from erpnext.stock.doctype.batch.test_batch import TestBatch

		item_code = "_TestMultibatchFifo"
		TestBatch.make_batch_item(item_code)
		warehouse = "_Test Warehouse - _TC"
		receipt = make_stock_entry(
			item_code=item_code,
			qty=1,
			rate=10,
			to_warehouse=warehouse,
			purpose="Material Receipt",
			do_not_save=True,
		)
		receipt.append(
			"items", frappe.copy_doc(receipt.items[0], ignore_no_copy=False).update({"basic_rate": 20})
		)
		receipt.save()
		receipt.submit()
		receipt.load_from_db()

		batches = frappe._dict(
			{get_batch_from_bundle(row.serial_and_batch_bundle): row.qty for row in receipt.items}
		)

		self.assertEqual(receipt.value_difference, 30)

		issue = make_stock_entry(
			item_code=item_code,
			qty=2,
			from_warehouse=warehouse,
			purpose="Material Issue",
			do_not_save=True,
			batches=batches,
		)

		issue.save()
		issue.submit()
		issue.reload()  # reload because reposting current voucher updates rate
		self.assertEqual(issue.value_difference, -30)

	def test_transfer_qty_validation(self):
		se = make_stock_entry(item_code="_Test Item", do_not_save=True, qty=0.001, rate=100)
		se.items[0].uom = "Kg"
		se.items[0].conversion_factor = 0.002

		self.assertRaises(frappe.ValidationError, se.save)

	def test_mapped_stock_entry(self):
		"Check if rate and stock details are populated in mapped SE given warehouse."
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_stock_entry
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item_code = "_TestMappedItem"
		create_item(item_code, is_stock_item=True)

		pr = make_purchase_receipt(
			item_code=item_code, qty=2, rate=100, company="_Test Company", warehouse="Stores - _TC"
		)

		mapped_se = make_stock_entry(pr.name)

		self.assertEqual(mapped_se.items[0].s_warehouse, "Stores - _TC")
		self.assertEqual(mapped_se.items[0].actual_qty, 2)
		self.assertEqual(mapped_se.items[0].basic_rate, 100)
		self.assertEqual(mapped_se.items[0].basic_amount, 200)

	def test_stock_entry_item_details(self):
		item = make_item()

		se = make_stock_entry(
			item_code=item.name, qty=1, to_warehouse="_Test Warehouse - _TC", do_not_submit=True
		)

		self.assertEqual(se.items[0].item_name, item.item_name)
		se.items[0].item_name = "wat"
		se.items[0].stock_uom = "Kg"
		se.save()

		self.assertEqual(se.items[0].item_name, item.item_name)
		self.assertEqual(se.items[0].stock_uom, item.stock_uom)

	@change_settings("Stock Reposting Settings", {"item_based_reposting": 0})
	def test_reposting_for_depedent_warehouse(self):
		from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import repost_sl_entries
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		# Inward at WH1 warehouse (Component)
		# 1st Repack (Component (WH1) - Subcomponent (WH2))
		# 2nd Repack (Subcomponent (WH2) - FG Item (WH3))
		# Material Transfer of FG Item -> WH 3 -> WH2 -> Wh1 (Two transfer entries)
		# Backdated transction which should update valuation rate in repack as well trasfer entries

		for item_code in ["FG Item 1", "Sub Component 1", "Component 1"]:
			create_item(item_code)

		for warehouse in ["WH 1", "WH 2", "WH 3"]:
			create_warehouse(warehouse)

		make_stock_entry(
			item_code="Component 1",
			rate=100,
			purpose="Material Receipt",
			qty=10,
			to_warehouse="WH 1 - _TC",
			posting_date=add_days(nowdate(), -10),
		)

		repack1 = make_stock_entry(
			item_code="Component 1",
			purpose="Repack",
			do_not_save=True,
			qty=10,
			from_warehouse="WH 1 - _TC",
			posting_date=add_days(nowdate(), -9),
		)

		repack1.append(
			"items",
			{
				"item_code": "Sub Component 1",
				"qty": 10,
				"t_warehouse": "WH 2 - _TC",
				"transfer_qty": 10,
				"uom": "Nos",
				"stock_uom": "Nos",
				"conversion_factor": 1.0,
			},
		)

		repack1.save()
		repack1.submit()

		self.assertEqual(repack1.items[1].basic_rate, 100)
		self.assertEqual(repack1.items[1].amount, 1000)

		repack2 = make_stock_entry(
			item_code="Sub Component 1",
			purpose="Repack",
			do_not_save=True,
			qty=10,
			from_warehouse="WH 2 - _TC",
			posting_date=add_days(nowdate(), -8),
		)

		repack2.append(
			"items",
			{
				"item_code": "FG Item 1",
				"qty": 10,
				"t_warehouse": "WH 3 - _TC",
				"transfer_qty": 10,
				"uom": "Nos",
				"stock_uom": "Nos",
				"conversion_factor": 1.0,
			},
		)

		repack2.save()
		repack2.submit()

		self.assertEqual(repack2.items[1].basic_rate, 100)
		self.assertEqual(repack2.items[1].amount, 1000)

		transfer1 = make_stock_entry(
			item_code="FG Item 1",
			purpose="Material Transfer",
			qty=10,
			from_warehouse="WH 3 - _TC",
			to_warehouse="WH 2 - _TC",
			posting_date=add_days(nowdate(), -7),
		)

		self.assertEqual(transfer1.items[0].basic_rate, 100)
		self.assertEqual(transfer1.items[0].amount, 1000)

		transfer2 = make_stock_entry(
			item_code="FG Item 1",
			purpose="Material Transfer",
			qty=10,
			from_warehouse="WH 2 - _TC",
			to_warehouse="WH 1 - _TC",
			posting_date=add_days(nowdate(), -6),
		)

		self.assertEqual(transfer2.items[0].basic_rate, 100)
		self.assertEqual(transfer2.items[0].amount, 1000)

		# Backdated transaction
		receipt2 = make_stock_entry(
			item_code="Component 1",
			rate=200,
			purpose="Material Receipt",
			qty=10,
			to_warehouse="WH 1 - _TC",
			posting_date=add_days(nowdate(), -15),
		)

		self.assertEqual(receipt2.items[0].basic_rate, 200)
		self.assertEqual(receipt2.items[0].amount, 2000)

		repost_name = frappe.db.get_value(
			"Repost Item Valuation", {"voucher_no": receipt2.name, "docstatus": 1}, "name"
		)

		if repost_name:
			doc = frappe.get_doc("Repost Item Valuation", repost_name)
			repost_sl_entries(doc)

		for obj in [repack1, repack2, transfer1, transfer2]:
			obj.load_from_db()

			index = 1 if obj.purpose == "Repack" else 0
			self.assertEqual(obj.items[index].basic_rate, 200)
			self.assertEqual(obj.items[index].basic_amount, 2000)

	def test_batch_expiry(self):
		from erpnext.controllers.stock_controller import BatchExpiredError
		from erpnext.stock.doctype.batch.test_batch import make_new_batch

		item_code = "Test Batch Expiry Test Item - 001"
		item_doc = create_item(item_code=item_code, is_stock_item=1, valuation_rate=10)

		item_doc.has_batch_no = 1
		item_doc.save()

		batch = make_new_batch(
			batch_id=frappe.generate_hash("", 5), item_code=item_doc.name, expiry_date=add_days(today(), -1)
		)

		se = make_stock_entry(
			item_code=item_code,
			purpose="Material Receipt",
			qty=4,
			to_warehouse="_Test Warehouse - _TC",
			batch_no=batch.name,
			use_serial_batch_fields=1,
			do_not_save=True,
		)

		self.assertRaises(BatchExpiredError, se.save)

	def test_negative_stock_reco(self):
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 0)

		item_code = "Test Negative Item - 001"
		create_item(item_code=item_code, is_stock_item=1, valuation_rate=10)

		make_stock_entry(
			item_code=item_code,
			posting_date=add_days(today(), -3),
			posting_time="00:00:00",
			target="_Test Warehouse - _TC",
			qty=10,
			to_warehouse="_Test Warehouse - _TC",
		)

		make_stock_entry(
			item_code=item_code,
			posting_date=today(),
			posting_time="00:00:00",
			source="_Test Warehouse - _TC",
			qty=8,
			from_warehouse="_Test Warehouse - _TC",
		)

		sr_doc = create_stock_reconciliation(
			purpose="Stock Reconciliation",
			posting_date=add_days(today(), -3),
			posting_time="00:00:00",
			item_code=item_code,
			warehouse="_Test Warehouse - _TC",
			valuation_rate=10,
			qty=7,
			do_not_submit=True,
		)

		self.assertRaises(frappe.ValidationError, sr_doc.submit)

	def test_negative_batch(self):
		item_code = "Test Negative Batch Item - 001"
		make_item(
			item_code,
			{"has_batch_no": 1, "create_new_batch": 1, "batch_naming_series": "Test-BCH-NNS.#####"},
		)

		se1 = make_stock_entry(
			item_code=item_code,
			purpose="Material Receipt",
			qty=100,
			target="_Test Warehouse - _TC",
		)

		se1.reload()

		batch_no = get_batch_from_bundle(se1.items[0].serial_and_batch_bundle)

		se2 = make_stock_entry(
			item_code=item_code,
			purpose="Material Issue",
			batch_no=batch_no,
			qty=10,
			source="_Test Warehouse - _TC",
		)

		se2.reload()

		se3 = make_stock_entry(
			item_code=item_code,
			purpose="Material Receipt",
			qty=100,
			target="_Test Warehouse - _TC",
		)

		se3.reload()

		self.assertRaises(frappe.ValidationError, se1.cancel)

	def test_auto_reorder_level(self):
		from erpnext.stock.reorder_item import reorder_item

		item_doc = make_item(
			"Test Auto Reorder Item - 001",
			properties={"stock_uom": "Kg", "purchase_uom": "Nos", "is_stock_item": 1},
			uoms=[{"uom": "Nos", "conversion_factor": 5}],
		)

		if not frappe.db.exists("Item Reorder", {"parent": item_doc.name}):
			item_doc.append(
				"reorder_levels",
				{
					"warehouse_reorder_level": 0,
					"warehouse_reorder_qty": 10,
					"warehouse": "_Test Warehouse - _TC",
					"material_request_type": "Purchase",
				},
			)

		item_doc.save(ignore_permissions=True)

		frappe.db.set_single_value("Stock Settings", "auto_indent", 1)

		mr_list = reorder_item()

		frappe.db.set_single_value("Stock Settings", "auto_indent", 0)
		mrs = frappe.get_all(
			"Material Request Item",
			fields=["qty", "stock_uom", "stock_qty"],
			filters={"item_code": item_doc.name, "uom": "Nos"},
		)

		for mri in mrs:
			self.assertEqual(mri.stock_uom, "Kg")
			self.assertEqual(mri.stock_qty, 10)
			self.assertEqual(mri.qty, 2)

		for mr in mr_list:
			mr.cancel()
			mr.delete()

	def test_use_serial_and_batch_fields(self):
		item = make_item(
			"Test Use Serial and Batch Item SN Item",
			{"has_serial_no": 1, "is_stock_item": 1},
		)

		serial_nos = [
			"Test Use Serial and Batch Item SN Item - SN 001",
			"Test Use Serial and Batch Item SN Item - SN 002",
		]

		se = make_stock_entry(
			item_code=item.name,
			qty=2,
			to_warehouse="_Test Warehouse - _TC",
			use_serial_batch_fields=1,
			serial_no="\n".join(serial_nos),
		)

		self.assertTrue(se.items[0].use_serial_batch_fields)
		self.assertTrue(se.items[0].serial_no)
		self.assertTrue(se.items[0].serial_and_batch_bundle)

		for serial_no in serial_nos:
			self.assertTrue(frappe.db.exists("Serial No", serial_no))
			self.assertEqual(frappe.db.get_value("Serial No", serial_no, "status"), "Active")

		se1 = make_stock_entry(
			item_code=item.name,
			qty=2,
			from_warehouse="_Test Warehouse - _TC",
			use_serial_batch_fields=1,
			serial_no="\n".join(serial_nos),
		)

		se1.reload()

		self.assertTrue(se1.items[0].use_serial_batch_fields)
		self.assertTrue(se1.items[0].serial_no)
		self.assertTrue(se1.items[0].serial_and_batch_bundle)

		for serial_no in serial_nos:
			self.assertTrue(frappe.db.exists("Serial No", serial_no))
			self.assertEqual(frappe.db.get_value("Serial No", serial_no, "status"), "Delivered")

	def test_serial_batch_bundle_type_of_transaction(self):
		item = make_item(
			"Test Use Serial and Batch Item SN Item",
			{
				"has_batch_no": 1,
				"is_stock_item": 1,
				"create_new_batch": 1,
				"batch_naming_series": "Test-SBBTYT-NNS.#####",
			},
		).name

		se = make_stock_entry(
			item_code=item,
			qty=2,
			target="_Test Warehouse - _TC",
			use_serial_batch_fields=1,
		)

		batch_no = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)

		se = make_stock_entry(
			item_code=item,
			qty=2,
			source="_Test Warehouse - _TC",
			target="Stores - _TC",
			use_serial_batch_fields=0,
			batch_no=batch_no,
			do_not_submit=True,
		)

		se.reload()
		sbb = se.items[0].serial_and_batch_bundle
		frappe.db.set_value("Serial and Batch Bundle", sbb, "type_of_transaction", "Inward")
		self.assertRaises(frappe.ValidationError, se.submit)

	def test_stock_entry_for_same_posting_date_and_time(self):
		warehouse = "_Test Warehouse - _TC"
		item_code = "Test Stock Entry For Same Posting Datetime 1"
		make_item(item_code, {"is_stock_item": 1})
		posting_date = nowdate()
		posting_time = nowtime()

		for index in range(25):
			se = make_stock_entry(
				item_code=item_code,
				qty=1,
				to_warehouse=warehouse,
				posting_date=posting_date,
				posting_time=posting_time,
				do_not_submit=True,
				purpose="Material Receipt",
				basic_rate=100,
			)

			se.append(
				"items",
				{
					"item_code": item_code,
					"item_name": se.items[0].item_name,
					"description": se.items[0].description,
					"t_warehouse": se.items[0].t_warehouse,
					"basic_rate": 100,
					"qty": 1,
					"stock_qty": 1,
					"conversion_factor": 1,
					"expense_account": se.items[0].expense_account,
					"cost_center": se.items[0].cost_center,
					"uom": se.items[0].uom,
					"stock_uom": se.items[0].stock_uom,
				},
			)

			se.remarks = f"The current number is {cstr(index)}"

			se.submit()

		sles = frappe.get_all(
			"Stock Ledger Entry",
			fields=[
				"posting_date",
				"posting_time",
				"actual_qty",
				"qty_after_transaction",
				"incoming_rate",
				"stock_value_difference",
				"stock_value",
			],
			filters={"item_code": item_code, "warehouse": warehouse},
			order_by="creation",
		)

		self.assertEqual(len(sles), 50)
		i = 0
		for sle in sles:
			i += 1
			self.assertEqual(getdate(sle.posting_date), getdate(posting_date))
			self.assertEqual(get_time(sle.posting_time), get_time(posting_time))
			self.assertEqual(sle.actual_qty, 1)
			self.assertEqual(sle.qty_after_transaction, i)
			self.assertEqual(sle.incoming_rate, 100)
			self.assertEqual(sle.stock_value_difference, 100)
			self.assertEqual(sle.stock_value, 100 * i)

	def test_stock_entry_amount(self):
		warehouse = "_Test Warehouse - _TC"
		rm_item_code = "Test Stock Entry Amount 1"
		make_item(rm_item_code, {"is_stock_item": 1})

		fg_item_code = "Test Repack Stock Entry Amount 1"
		make_item(fg_item_code, {"is_stock_item": 1})

		make_stock_entry(
			item_code=rm_item_code,
			qty=1,
			to_warehouse=warehouse,
			basic_rate=200,
			posting_date=nowdate(),
		)

		se = make_stock_entry(
			item_code=rm_item_code,
			qty=1,
			purpose="Repack",
			basic_rate=100,
			do_not_save=True,
		)

		se.items[0].s_warehouse = warehouse
		se.append(
			"items",
			{
				"item_code": fg_item_code,
				"qty": 1,
				"t_warehouse": warehouse,
				"uom": "Nos",
				"conversion_factor": 1.0,
			},
		)
		se.set_stock_entry_type()
		se.submit()

		self.assertEqual(se.items[0].amount, 200)
		self.assertEqual(se.items[0].basic_amount, 200)

		make_stock_entry(
			item_code=rm_item_code,
			qty=1,
			to_warehouse=warehouse,
			basic_rate=300,
			posting_date=add_days(nowdate(), -1),
		)

		se.reload()
		self.assertEqual(se.items[0].amount, 300)
		self.assertEqual(se.items[0].basic_amount, 300)

	def test_use_batch_wise_valuation_for_moving_average_item(self):
		item_code = "_Test Use Batch Wise MA Valuation Item"

		make_item(
			item_code,
			{
				"is_stock_item": 1,
				"valuation_method": "Moving Average",
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_naming_series": "Test-UBWVMAV-T-NNS.#####",
			},
		)

		frappe.db.set_single_value("Stock Settings", "do_not_use_batchwise_valuation", 0)

		batches = []
		se = make_stock_entry(
			item_code=item_code,
			qty=10,
			to_warehouse="_Test Warehouse - _TC",
			basic_rate=100,
			posting_date=add_days(nowdate(), -2),
		)

		batches.append(get_batch_from_bundle(se.items[0].serial_and_batch_bundle))

		se = make_stock_entry(
			item_code=item_code,
			qty=10,
			to_warehouse="_Test Warehouse - _TC",
			basic_rate=300,
			posting_date=add_days(nowdate(), -1),
		)

		batches.append(get_batch_from_bundle(se.items[0].serial_and_batch_bundle))

		se = make_stock_entry(
			item_code=item_code,
			qty=5,
			from_warehouse="_Test Warehouse - _TC",
			batch_no=batches[1],
			posting_date=nowdate(),
		)

		self.assertEqual(se.items[0].basic_rate, 300)

	def test_create_partial_material_transfer_stock_entry_and_TC_SCK_048(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.material_request.material_request import (
			make_stock_entry as _make_stock_entry,
		)
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry as __make_stock_entry

		create_company("_Test Company")
		make_item("_Test Item", {"is_stock_item": 1})
		create_cost_center(cost_center_name="_Test Cost Center", company="_Test Company")
		source_warehouse = create_warehouse(
			"_Test Source Warehouse", properties=None, company="_Test Company"
		)

		frappe.db.set_value(
			"Company",
			"_Test Company",
			{"enable_provisional_accounting_for_non_stock_items": 0, "enable_perpetual_inventory": 0},
		)
		company_doc = frappe.get_doc("Company", "_Test Company")
		frappe.local.enable_perpetual_inventory = {}
		frappe.local.enable_perpetual_inventory[company_doc.name] = 0
		frappe._set_document_in_cache("Company", company_doc)
		target_warehouse = create_warehouse("_Test Warehouse", properties=None, company="_Test Company")
		qty = 5
		__make_stock_entry(
			item_code="_Test Item",
			qty=qty,
			to_warehouse=source_warehouse,
			company="_Test Company",
			rate=100,
		)
		s_bin_qty = (
			frappe.db.get_value(
				"Bin", {"item_code": "_Test Item", "warehouse": source_warehouse}, "actual_qty"
			)
			or 0
		)

		mr = make_material_request(
			material_request_type="Material Transfer",
			qty=qty,
			warehouse=target_warehouse,
			from_warehouse=source_warehouse,
			item="_Test Item",
		)
		self.assertEqual(mr.status, "Pending")
		se = _make_stock_entry(mr.name)
		se.get("items")[0].qty = 3
		se.insert()
		se.submit()
		mr.load_from_db()
		self.assertEqual(mr.status, "Partially Received")
		self.check_stock_ledger_entries(
			"Stock Entry",
			se.name,
			[["_Test Item", target_warehouse, 3], ["_Test Item", source_warehouse, -3]],
		)

		se1 = _make_stock_entry(mr.name)
		se1.get("items")[0].qty = 2
		se1.insert()
		se1.submit()
		mr.load_from_db()
		self.assertEqual(mr.status, "Transferred")
		self.check_stock_ledger_entries(
			"Stock Entry",
			se1.name,
			[["_Test Item", target_warehouse, 2], ["_Test Item", source_warehouse, -2]],
		)

		se1.cancel()
		mr.load_from_db()
		self.assertEqual(mr.status, "Partially Received")

		se.cancel()
		mr.load_from_db()
		self.assertEqual(mr.status, "Pending")
		current_s_bin_qty = (
			frappe.db.get_value(
				"Bin", {"item_code": "_Test Item", "warehouse": source_warehouse}, "actual_qty"
			)
			or 0
		)
		self.assertEqual(current_s_bin_qty, s_bin_qty)

	def test_create_partial_material_request_stock_entry_for_batch_item_TC_SCK_189(self):
		from erpnext.stock.doctype.material_request.material_request import (
			make_stock_entry as _make_stock_entry,
		)
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		company = "_Test Company"
		if not frappe.db.exists("Company", company):
			company_doc = frappe.new_doc("Company")
			company_doc.company_doc_name = company
			company_doc.country = "India"
			company_doc.default_currency = "INR"
			company_doc.save()
		else:
			company_doc = frappe.get_doc("Company", company)
		warehouse = create_warehouse("_Test Warehouse", company=company_doc.name)
		properties = {
			"has_batch_no": 1,
			"create_new_batch": 1,
			"has_expiry_date": 1,
			"shelf_life_in_days": 365,
		}
		item = make_item("_Test Item MR", properties=properties)
		item.batch_number_series = f"{item.name}.-BT-.####."
		item.save()
		mr = make_material_request(
			material_request_type="Material Issue", qty=10, warehouse=warehouse, item=item.name
		)
		se = _make_stock_entry(mr.name)
		se.get("items")[0].qty = 5
		se.save()
		se.submit()
		mr.reload()
		self.assertEqual(mr.status, "Partially Ordered")

	def test_create_partial_material_request_stock_entry_for_serial_item_TC_SCK_190(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer
		from erpnext.stock.doctype.material_request.material_request import (
			make_stock_entry as _make_stock_entry,
		)
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		create_company()
		create_customer("_Test Customer")
		make_item("_Test Item", {"is_stock_item": 1})
		warehouse = create_warehouse(
			warehouse_name="_Test Warehouse",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		warehouse = create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		item = make_item("_Test Item MR", properties={"has_serial_no": 1})
		get_or_create_fiscal_year("_Test Company")

		item.serial_no_series = f"{item.item_code}.-SL-.####."
		item.save()
		cost_center = frappe.db.get_all("Cost Center", {"company": "_Test Company"}, "name")
		mr = make_material_request(
			material_request_type="Material Issue",
			qty=10,
			warehouse=warehouse,
			item=item.name,
			uom="Box",
			cost_center=cost_center[1].name,
		)
		se = _make_stock_entry(mr.name)
		se.get("items")[0].qty = 5
		se.get("items")[0].allow_zero_valuation_rate = 1
		se.save()
		se.submit()
		mr.reload()
		self.assertEqual(mr.status, "Partially Ordered")

	def test_stock_entry_for_mr_purpose(self):
		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")

		se = make_stock_entry(
			item_code="_Test Item",
			is_opening="Yes",
			expense_account="Temporary Opening - TCP1",
			company=company,
			purpose="Material Receipt",
			target="Stores - TCP1",
			qty=10,
			basic_rate=100,
		)

		self.assertEqual(se.stock_entry_type, "Material Receipt")

		gl_temp_credit = frappe.db.get_value(
			"GL Entry", {"voucher_no": se.name, "account": "Temporary Opening - TCP1"}, "credit"
		)
		self.assertEqual(gl_temp_credit, 1000)

		gl_stock_debit = frappe.db.get_value(
			"GL Entry", {"voucher_no": se.name, "account": "Stock In Hand - TCP1"}, "debit"
		)
		self.assertEqual(gl_stock_debit, 1000)

		actual_qty = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": se.name, "voucher_type": "Stock Entry", "warehouse": "Stores - TCP1"},
			["qty_after_transaction"],
		)
		self.assertEqual(actual_qty, 10)

	def test_create_partial_material_request_stock_entry_for_serial_batch_item_TC_SCK_191(self):
		from erpnext.stock.doctype.material_request.material_request import (
			make_stock_entry as _make_stock_entry,
		)
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		company = "_Test Company"
		if not frappe.db.exists("Company", company):
			company_doc = frappe.new_doc("Company")
			company_doc.company_doc_name = company
			company_doc.country = "India"
			company_doc.default_currency = "INR"
			company_doc.save()
		else:
			company_doc = frappe.get_doc("Company", company)
		warehouse = create_warehouse("_Test Warehouse", company=company_doc.name)
		properties = {
			"has_serial_no": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"has_expiry_date": 1,
			"shelf_life_in_days": 365,
		}
		item = make_item("_Test Item 65", properties=properties)
		item.serial_no_series = f"{item.item_code}.-SL-.####."
		item.batch_number_series = f"{item.item_code}.-BT-.####."
		item.save()
		mr = make_material_request(
			material_request_type="Material Issue", qty=10, warehouse=warehouse, item=item.name
		)
		se = _make_stock_entry(mr.name)
		se.get("items")[0].qty = 5
		se.save()
		se.submit()
		mr.reload()
		self.assertEqual(mr.status, "Partially Ordered")

	def test_stock_entry_ledgers_for_mr_purpose_and_TC_SCK_052(self):
		from erpnext.stock.doctype.material_request.test_material_request import get_gle

		stock_in_hand_account = get_inventory_account("_Test Company", "_Test Warehouse - _TC")
		frappe.db.set_value("Company", "_Test Company", "enable_perpetual_inventory", 1)

		se = make_stock_entry(
			item_code="_Test Item",
			expense_account="Stock Adjustment - _TC",
			to_warehouse="_Test Warehouse - _TC",
			company="_Test Company",
			purpose="Material Receipt",
			qty=10,
			basic_rate=100,
		)
		self.assertEqual(se.stock_entry_type, "Material Receipt")

		self.check_stock_ledger_entries(
			"Stock Entry",
			se.name,
			[
				["_Test Item", "_Test Warehouse - _TC", 10],
			],
		)

		self.check_gl_entries(
			"Stock Entry",
			se.name,
			sorted([[stock_in_hand_account, 1000, 0.0], ["Stock Adjustment - _TC", 0.0, 1000.0]]),
		)

		se.cancel()

		sh_gle = get_gle(se.company, se.name, stock_in_hand_account)
		sa_gle = get_gle(se.company, se.name, "Stock Adjustment - _TC")
		self.assertEqual(sh_gle[0], sh_gle[1])
		self.assertEqual(sa_gle[0], sa_gle[1])

	def test_create_stock_repack_via_bom_TC_SCK_016(self):
		self.create_stock_repack_via_bom()

	def test_create_and_cancel_stock_repack_via_bom_TC_SCK_065(self):
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		warehouse = ["_Test Warehouse", "_Test Target Warehouse", "_Test Warehouse 1"]
		create_supplier(supplier_name="_Test Supplier", default_currency="INR")

		for w in warehouse:
			create_warehouse(warehouse_name=w, company="_Test Company")

		company_doc = frappe.get_doc("Company", "_Test Company")
		frappe.local.enable_perpetual_inventory = {}
		frappe.local.enable_perpetual_inventory[company_doc.name] = 0
		frappe._set_document_in_cache("Company", company_doc)

		se = self.create_stock_repack_via_bom()
		se.cancel()

		sl_entry_cancelled = frappe.db.get_all(
			"Stock Ledger Entry",
			{"voucher_type": "Stock Entry", "voucher_no": se.name},
			["actual_qty", "warehouse"],
			order_by="creation",
		)
		warehouse_qty = {"_Test Target Warehouse - _TC": 0, "_Test Warehouse - _TC": 0}

		for sle in sl_entry_cancelled:
			warehouse_qty[sle.get("warehouse")] += sle.get("actual_qty")

		self.assertEqual(len(sl_entry_cancelled), 4)
		self.assertEqual(warehouse_qty["_Test Target Warehouse - _TC"], 0)
		self.assertEqual(warehouse_qty["_Test Warehouse - _TC"], 0)

	def test_create_stock_entry_TC_SCK_231(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		account = create_account(
			account_name="_Test Account Tax Assets",
			account_type="Fixed Asset",
			company="_Test Company",
			is_group=1,
			parent_account="Fixed Assets - _TC",
			do_not_save=True,
		)
		account.root_type = "Asset"
		account.save()
		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		frappe.db.set_value(
			"Company",
			"_Test Company",
			{"enable_provisional_accounting_for_non_stock_items": 0, "enable_perpetual_inventory": 0},
		)
		company_doc = frappe.get_doc("Company", "_Test Company")
		frappe.local.enable_perpetual_inventory = {}
		frappe.local.enable_perpetual_inventory[company_doc.name] = 0
		frappe._set_document_in_cache("Company", company_doc)
		# Create test item
		item_fields = {
			"item_name": "Test Pen",
			"is_stock_item": 1,
			"valuation_rate": 500,
		}
		item = make_item("Test Pen", item_fields)
		parent_acc = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Current Assets - _TC",
				"account_type": "Fixed Asset",
				"parent_account": "_Test Account Tax Assets - _TC",
				"root_type": "Asset",
				"is_group": 1,
				"company": "_Test Company",
			}
		)
		parent_acc.save()
		asset_account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Stock Adjustment - _TC",
				"account_type": "Fixed Asset",
				"parent_account": "Current Assets - _TC",
				"company": "_Test Company",
			}
		)
		asset_account.save()
		# item = make_test_objects("Item", {"item_code": "Test Pen", "item_name": "Test Pen"})

		# Set stock entry details
		stock_entry_type = "Material Receipt"
		target_warehouse = create_warehouse("Stores-test", properties=None, company="_Test Company")
		item_code = item.name
		qty = 5

		# Create stock entry
		se = make_stock_entry(
			item_code=item_code,
			company="_Test Company",
			purpose=stock_entry_type,
			expense_account=asset_account.name,
			qty=qty,
			do_not_submit=True,
			do_not_save=True,
		)
		se.items[0].t_warehouse = target_warehouse
		se.items[0].is_opening = "Yes"
		se.save()
		se.submit()

		# Assert opening balance
		bin = frappe.get_doc("Bin", {"item_code": item_code, "warehouse": target_warehouse})
		self.assertEqual(bin.actual_qty, qty)

		# Tear down
		# frappe.delete_doc("Stock Entry", se.name)
		# frappe.delete_doc("Item", item.name)

	def test_stock_reco_TC_SCK_232(self):
		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		item_fields = {
			"item_name": "Test CPU",
			"is_stock_item": 1,
			"valuation_rate": 500,
		}
		self.warehouse = create_warehouse("Stores", properties=None, company="_Test Company")
		self.company = "_Test Company"
		self.item_code = make_item("Test CPU", item_fields).name
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		sr = create_stock_reconciliation(
			purpose="Opening Stock",
			expense_account="Temporary Opening - _TC",
			item_code=self.item_code,
			warehouse=self.warehouse,
			qty=5,
			rate=500,
		)
		sr.submit()
		reserved_qty = frappe.db.get_value(
			"Bin", {"item_code": self.item_code, "warehouse": self.warehouse}, "actual_qty"
		)
		self.assertEqual(reserved_qty, 5)

	def test_stock_ent_TC_SCK_233(self):
		from erpnext.stock.utils import get_bin, get_or_create_fiscal_year

		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		get_or_create_fiscal_year("_Test Company")
		frappe.db.set_value("Company", "_Test Company", "stock_adjustment_account", "Stock Adjustment - _TC")
		parent_warehouse = frappe.db.get_value(
			"Warehouse", {"company": "_Test Company", "is_group": 1}, "name"
		)
		warehouse = create_warehouse(
			warehouse_name="Department Store",
			properties={"parent_warehouse": f"{parent_warehouse}"},
			company="_Test Company",
		)
		item_fields = {
			"item_name": "Test 1231",
			"is_stock_item": 1,
			"valuation_rate": 100,
			"stock_uom": "Nos",
			"gst_hsn_code": "01011010",
			"opening_stock": 5,
			"item_defaults": [{"company": "_Test Company", "default_warehouse": warehouse}],
		}
		self.item_code = make_item("Test 1231", item_fields)
		bin = get_bin(self.item_code.name, warehouse)

		self.assertEqual(bin.actual_qty, item_fields["opening_stock"])

	def test_stock_reco_TC_SCK_127(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		company = "_Test Company"
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")

		get_or_create_fiscal_year("_Test Company")
		self.source_warehouse = create_warehouse(
			"Stores-test", properties={"parent_warehouse": "All Warehouses - _TC"}, company="_Test Company"
		)
		self.target_warehouse = create_warehouse(
			"Department Stores-test",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)

		item_fields1 = {
			"item_name": "Test Brown Rice",
			"is_stock_item": 1,
			"valuation_rate": 100,
			"stock_uom": "Kg",
		}
		self.item_code1 = make_item("Test Brown Rice", item_fields1)
		item_fields2 = {
			"item_name": "Test Brown Rice 5kg",
			"is_stock_item": 1,
			"valuation_rate": 100,
			"stock_uom": "Kg",
		}
		self.item_code2 = make_item("Test Brown Rice 5kg", item_fields2)
		item_fields3 = {
			"item_name": "Test Brown Rice 500g",
			"is_stock_item": 1,
			"valuation_rate": 100,
			"stock_uom": "Kg",
		}
		self.item_code3 = make_item("Test Brown Rice 500g", item_fields3)
		se1 = make_stock_entry(
			item_code=self.item_code1.name,
			company="_Test Company",
			purpose="Material Receipt",
			qty=10,
			do_not_submit=True,
			do_not_save=True,
		)

		se1.items[0].t_warehouse = self.source_warehouse
		se1.save()
		se1.submit()

		self.material_request = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Material Transfer",
				"set_from_warehouse": self.source_warehouse,
				"set_warehouse": self.target_warehouse,
				"company": "_Test Company",
				"items": [
					{"item_code": self.item_code1.name, "qty": 10, "schedule_date": frappe.utils.nowdate()},
					{"item_code": self.item_code3.name, "qty": 10, "schedule_date": frappe.utils.nowdate()},
					{"item_code": self.item_code2.name, "qty": 2, "schedule_date": frappe.utils.nowdate()},
				],
			}
		)
		self.material_request.insert()
		self.material_request.submit()

		se = frappe.get_doc(
			{"doctype": "Stock Entry", "stock_entry_type": "Repack", "company": "_Test Company", "items": []}
		)
		se.append(
			"items", {"item_code": self.item_code1.name, "qty": 10, "s_warehouse": self.source_warehouse}
		)
		se.append(
			"items",
			{
				"item_code": self.item_code3.name,
				"qty": 10,  # Fixed the qty
				"t_warehouse": self.target_warehouse,
			},
		)
		se.append(
			"items",
			{
				"item_code": self.item_code2.name,
				"qty": 2,  # Fixed the qty
				"t_warehouse": self.target_warehouse,
			},
		)
		se.save()
		se.submit()
		stock_ledger_entries = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": se.name}, fields=["item_code", "actual_qty"]
		)

		stock_movements = {s["item_code"]: s["actual_qty"] for s in stock_ledger_entries}

		self.assertEqual(stock_movements.get(self.item_code1.name), -10, "Brown Rice should be 10 Outward")
		self.assertEqual(stock_movements.get(self.item_code3.name), 10, "Brown Rice 500g should be 10 Inward")
		self.assertEqual(stock_movements.get(self.item_code2.name), 2, "Brown Rice 5kg should be 2 Inward")

	def create_stock_repack_via_bom(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		create_company()
		create_warehouse(warehouse_name="_Test Warehouse 1", company="_Test Company")
		create_supplier(supplier_name="_Test Supplier", default_currency="INR")
		company = "_Test Company"
		frappe.db.set_value("Company", company, "stock_received_but_not_billed", "Cost of Goods Sold - _TC")
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")

		company_doc = frappe.get_doc("Company", "_Test Company")
		frappe.local.enable_perpetual_inventory = {}
		frappe.local.enable_perpetual_inventory[company_doc.name] = 0
		frappe._set_document_in_cache("Company", company_doc)

		t_warehouse = create_warehouse(
			warehouse_name="_Test Target Warehouse",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		fields = {
			"is_stock_item": 1,
			"stock_uom": "Kg",
			"uoms": [{"uom": "Kg", "conversion_factor": 1}, {"uom": "Tonne", "conversion_factor": 1000}],
		}
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_wheet = make_item("_Test Item Wheet", properties=fields).name
		fields["stock_uom"] = "Nos"
		fields["uoms"] = [{"uom": "Nos", "conversion_factor": 1}, {"uom": "Kg", "conversion_factor": 10}]
		item_wheet_bag = make_item("_Test Item Wheet 10Kg Bag", properties=fields).name

		# Create Purchase Receipt
		pr = make_purchase_receipt(
			item_code=item_wheet, qty=1, rate=20000, uom="Tonne", stock_uom="Kg", conversion_factor=1000
		)

		# Check Stock Ledger Entries
		self.check_stock_ledger_entries(
			"Purchase Receipt",
			pr.name,
			[
				["_Test Item Wheet", "_Test Warehouse - _TC", 1000],
			],
		)

		# Create BOM
		rm_items = [{"item_code": item_wheet, "qty": 10, "uom": "Kg"}]
		bom_doc = create_bom(item_wheet_bag, rm_items)

		# Create Repack
		se = make_stock_entry(
			item_code=item_wheet,
			expense_account="Stock Adjustment - _TC",
			company="_Test Company",
			purpose="Repack",
			qty=10,
			do_not_submit=True,
			do_not_save=True,
		)
		se.from_bom = 1
		se.bom_no = bom_doc.name
		se.fg_completed_qty = 10
		se.get_items()
		se.items[0].s_warehouse = "_Test Warehouse - _TC"
		se.items[0].t_warehouse = None
		se.items[1].s_warehouse = None
		se.items[1].t_warehouse = t_warehouse
		se.save()
		se.submit()

		# Check Stock Ledger Entries
		self.check_stock_ledger_entries(
			"Stock Entry",
			se.name,
			[
				["_Test Item Wheet 10Kg Bag", "_Test Target Warehouse - _TC", 10.0],
				["_Test Item Wheet", "_Test Warehouse - _TC", -100.0],
			],
		)

		return se

	def setUp(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer

		create_company()
		create_customer(name="_Test Customer")
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)

	def test_partial_material_issue_TC_SCK_204(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		create_company()
		company_doc = frappe.get_doc("Company", "_Test Company")
		frappe.local.enable_perpetual_inventory = {}
		frappe.local.enable_perpetual_inventory[company_doc.name] = 0
		frappe._set_document_in_cache("Company", company_doc)
		company = "_Test Company"
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")
		get_or_create_fiscal_year("_Test Company")
		create_customer(name="_Test Customer")

		fields = {
			"shelf_life_in_days": 365,
			"end_of_life": "2099-12-31",
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"has_expiry_date": 1,
			"batch_number_series": "Test-SABBMRP-Bno.#####",
			"valuation_rate": 100,
		}
		# if if_app_installed("india_compliance"):
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_code = make_item("COOKIES (BT)", fields).name

		source_warehouse = "Stores - _TC"
		target_warehouse = create_warehouse(
			warehouse_name="Department Store",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company=company,
		)
		qty = 10

		# Stock Receipt
		se_receipt = make_stock_entry(
			item_code=item_code,
			qty=qty,
			to_warehouse=target_warehouse,
			# purpose="Material Receipt",
			company=company,
			do_not_save=True,
		)
		se_receipt.save()
		se_receipt.submit()
		cost_center = frappe.db.get_all("Cost Center", {"company": company, "is_group": 0}, "name")
		# Create Material Request
		mr = make_material_request(
			material_request_type="Material Issue",
			qty=qty,
			warehouse=target_warehouse,
			item_code=item_code,
			company=company,
			cost_center=cost_center[0].name,
			uom="Unit",
		)
		self.assertEqual(mr.status, "Pending")

		se1 = make_mr_se(mr.name)
		se1.company = company
		se1.items[0].qty = 5
		se1.s_warehouse = (target_warehouse,)
		se1.t_warehouse = source_warehouse
		se1.items[0].expense_account = "Cost of Goods Sold - _TC"
		se1.insert()
		se1.submit()

	def test_stock_enrty_with_batch_TC_SCK_076(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Stock Adjustment",
			parent_account="Stock Expenses - _TC",
			company="_Test Company",
		)

		fields = {
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ABC.##",
		}
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item = make_item("_Test Batch Item", properties=fields).name
		se = make_stock_entry(
			item_code=item,
			qty=10,
			rate=100,
			target="_Test Warehouse - _TC",
			purpose="Material Receipt",
			expense_account="Stock Adjustment - _TC",
		)

		batch = frappe.get_all(
			"Batch",
			filters={"item": item, "reference_name": se.name},
			fields=["name", "batch_qty", "item", "reference_name"],
		)

		self.assertEqual(len(batch), 1)
		self.assertEqual(batch[0]["item"], item)
		self.assertEqual(batch[0]["batch_qty"], 10)
		self.assertEqual(batch[0]["reference_name"], se.name)

	def test_stock_enrty_with_serial_and_batch_TC_SCK_077(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Stock Adjustment",
			parent_account="Stock Expenses - _TC",
			company="_Test Company",
		)

		fields = {
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ABC.##",
			"has_serial_no": 1,
			"serial_no_series": "AAB.##",
		}
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item = make_item("_Test Batch Item", properties=fields).name
		se = make_stock_entry(
			item_code=item,
			qty=5,
			rate=100,
			target="_Test Warehouse - _TC",
			purpose="Material Receipt",
			expense_account="Stock Adjustment - _TC",
		)

		batch = frappe.get_all(
			"Batch",
			filters={"item": item, "reference_name": se.name},
			fields=["name", "batch_qty", "item", "reference_name"],
		)

		serial_no = frappe.get_all(
			"Serial No",
			filters={"item_code": item, "purchase_document_no": se.name},
			fields=["name", "batch_no", "item_code", "purchase_document_no"],
		)

		self.assertEqual(len(batch), 1)
		self.assertEqual(batch[0]["item"], item)
		self.assertEqual(batch[0]["batch_qty"], 5)
		self.assertEqual(batch[0]["reference_name"], se.name)

		self.assertEqual(len(serial_no), 5, "Serial number count mismatch")
		for serial in serial_no:
			self.assertEqual(serial["item_code"], item)
			self.assertEqual(serial["purchase_document_no"], se.name)
			self.assertEqual(serial["batch_no"], batch[0]["name"])

	def test_stock_entry_for_multiple_items_with_serial_batch_no_TC_SCK_078(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Stock Adjustment",
			parent_account="Stock Expenses - _TC",
			company="_Test Company",
		)

		fields = {
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ABC.##",
			"has_serial_no": 1,
			"serial_no_series": "AAB.##",
		}

		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_1 = make_item("_Test Batch Item 1", properties=fields).name
		item_2 = make_item("_Test Batch Item 2", properties=fields).name

		se = make_stock_entry(
			item_code=item_1,
			qty=5,
			rate=100,
			target="_Test Warehouse - _TC",
			purpose="Material Receipt",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)

		se.append(
			"items",
			{
				"item_code": item_2,
				"qty": 5,
				"basic_rate": 150,
				"t_warehouse": "_Test Warehouse - _TC",
				"expense_account": "Stock Adjustment - _TC",
			},
		)

		se.save()
		se.submit()

		for item, expected_qty in [(item_1, 5), (item_2, 5)]:
			batch = frappe.get_all(
				"Batch",
				filters={"item": item, "reference_name": se.name},
				fields=["name", "batch_qty", "item", "reference_name"],
			)

			serial_no = frappe.get_all(
				"Serial No",
				filters={"item_code": item, "purchase_document_no": se.name},
				fields=["name", "batch_no", "item_code", "purchase_document_no"],
			)

			self.assertEqual(len(batch), 1, f"Batch record mismatch for {item}")
			self.assertEqual(batch[0]["item"], item)
			self.assertEqual(batch[0]["batch_qty"], expected_qty)
			self.assertEqual(batch[0]["reference_name"], se.name)

			self.assertEqual(len(serial_no), expected_qty, f"Serial number count mismatch for {item}")
			for serial in serial_no:
				self.assertEqual(serial["item_code"], item)
				self.assertEqual(serial["purchase_document_no"], se.name)
				self.assertEqual(serial["batch_no"], batch[0]["name"])

	def test_stock_entry_for_multiple_items_with_batch_no_TC_SCK_079(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Stock Adjustment",
			parent_account="Stock Expenses - _TC",
			company="_Test Company",
		)

		fields = {
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ABC.##",
		}

		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_1 = make_item("_Test Batch Item 1", properties=fields).name
		item_2 = make_item("_Test Batch Item 2", properties=fields).name

		se = make_stock_entry(
			item_code=item_1,
			qty=5,
			rate=100,
			target="_Test Warehouse - _TC",
			purpose="Material Receipt",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)

		se.append(
			"items",
			{
				"item_code": item_2,
				"qty": 5,
				"basic_rate": 150,
				"t_warehouse": "_Test Warehouse - _TC",
				"expense_account": "Stock Adjustment - _TC",
			},
		)

		se.save()
		se.submit()

		for item, expected_qty in [(item_1, 5), (item_2, 5)]:
			batch = frappe.get_all(
				"Batch",
				filters={"item": item, "reference_name": se.name},
				fields=["name", "batch_qty", "item", "reference_name"],
			)

			self.assertEqual(len(batch), 1, f"Batch record mismatch for {item}")
			self.assertEqual(batch[0]["item"], item)
			self.assertEqual(batch[0]["batch_qty"], expected_qty)
			self.assertEqual(batch[0]["reference_name"], se.name)

	@change_settings("Stock Settings", {"default_warehouse": "_Test Warehouse - _TC"})
	@change_settings("Global Defaults", {"default_company": "_Test Company"})
	def test_item_opening_stock_TC_SCK_080(self):
		stock_in_hand_account = get_inventory_account("_Test Company", "_Test Warehouse - _TC")
		frappe.db.set_value("Company", "_Test Company", "stock_adjustment_account", "Stock Adjustment - _TC")
		frappe.db.set_value("Company", "_Test Company", "default_inventory_account", stock_in_hand_account)

		fields = {"is_stock_item": 1, "opening_stock": 15, "valuation_rate": 100}

		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"
		item_1 = create_item(
			item_code="_Test Stock OP", is_stock_item=1, opening_stock=15, valuation_rate=100
		)
		stock = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": item_1.name},
			fields=["warehouse", "actual_qty", "valuation_rate", "stock_value"],
		)
		self.assertEqual(stock[0]["warehouse"], "_Test Warehouse - _TC")
		self.assertEqual(stock[0]["actual_qty"], 15)
		self.assertEqual(stock[0]["valuation_rate"], 100)
		self.assertEqual(stock[0]["stock_value"], 1500)

	@change_settings("Stock Settings", {"default_warehouse": "_Test Warehouse - _TC"})
	@change_settings("Global Defaults", {"default_company": "_Test Company"})
	def test_item_opening_stock_with_item_defaults_TC_SCK_081(self):
		stock_in_hand_account = get_inventory_account("_Test Company", "_Test Warehouse - _TC")
		frappe.db.set_value(
			"Company", "_Test Company", "stock_adjustment_account", "Cost of Goods Sold - _TC"
		)
		frappe.db.set_value("Company", "_Test Company", "default_inventory_account", stock_in_hand_account)
		fields = {"is_stock_item": 1, "opening_stock": 15, "valuation_rate": 100}

		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_1 = create_item(
			item_code="_Test Stock OP", is_stock_item=1, opening_stock=15, valuation_rate=100
		)
		item_1.item_defaults = []
		item_1.append(
			"item_defaults", {"company": "_Test Company", "default_warehouse": "_Test Warehouse - _TC"}
		)
		item_1.save()
		stock = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": item_1.name},
			fields=["warehouse", "actual_qty", "valuation_rate", "stock_value"],
		)

		self.assertEqual(stock[0]["warehouse"], "_Test Warehouse - _TC")
		self.assertEqual(stock[0]["actual_qty"], 15)
		self.assertEqual(stock[0]["valuation_rate"], 100)
		self.assertEqual(stock[0]["stock_value"], 1500)

	@change_settings(
		"Stock Settings",
		{
			"use_serial_batch_fields": 1,
			"disable_serial_no_and_batch_selector": 1,
			"auto_create_serial_and_batch_bundle_for_outward": 1,
			"pick_serial_and_batch_based_on": "FIFO",
		},
	)
	def test_material_transfer_with_enable_selector_TC_SCK_090(self):
		fields = {
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ABC.##",
			"has_serial_no": 1,
			"serial_no_series": "AAB.##",
		}

		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_1 = make_item("_Test Batch Item 1", properties=fields).name
		item_2 = make_item("_Test Batch Item 2", properties=fields).name

		semr = make_stock_entry(
			item_code=item_1,
			qty=15,
			rate=100,
			target="_Test Warehouse - _TC",
			purpose="Material Receipt",
			do_not_save=True,
		)

		semr.append(
			"items",
			{"item_code": item_2, "qty": 15, "basic_rate": 150, "t_warehouse": "_Test Warehouse - _TC"},
		)

		semr.save()
		semr.submit()

		semt = make_stock_entry(
			item_code=item_1,
			qty=10,
			rate=100,
			source="_Test Warehouse - _TC",
			target="Stores - _TC",
			purpose="Material Transfer",
			do_not_save=True,
		)

		semt.append(
			"items",
			{
				"item_code": item_2,
				"qty": 10,
				"basic_rate": 150,
				"t_warehouse": "Stores - _TC",
				"s_warehouse": "_Test Warehouse - _TC",
			},
		)

		semt.save()
		semt.submit()

		sle = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": semt.name}, fields=["actual_qty", "item_code"]
		)
		sle_records = {entry["item_code"]: [] for entry in sle}

		for entry in sle:
			sle_records[entry["item_code"]].append(entry["actual_qty"])

		self.assertCountEqual(sle_records[item_1], [10, -10])
		self.assertCountEqual(sle_records[item_2], [10, -10])

	@change_settings(
		"Stock Settings",
		{
			"use_serial_batch_fields": 0,
			"disable_serial_no_and_batch_selector": 0,
			"auto_create_serial_and_batch_bundle_for_outward": 1,
			"pick_serial_and_batch_based_on": "FIFO",
		},
	)
	def test_material_transfer_with_disable_selector_TC_SCK_091(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Stock Adjustment",
			parent_account="Stock Expenses - _TC",
			company="_Test Company",
		)

		fields = {
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ABC.##",
			"has_serial_no": 1,
			"serial_no_series": "AAB.##",
		}

		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_1 = make_item("_Test Batch Item 1", properties=fields).name
		item_2 = make_item("_Test Batch Item 2", properties=fields).name

		semr = make_stock_entry(
			item_code=item_1,
			qty=15,
			rate=100,
			target="_Test Warehouse - _TC",
			purpose="Material Receipt",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)

		semr.append(
			"items",
			{
				"item_code": item_2,
				"qty": 15,
				"basic_rate": 150,
				"t_warehouse": "_Test Warehouse - _TC",
				"expense_account": "Stock Adjustment - _TC",
			},
		)

		semr.save()
		semr.submit()

		semt = make_stock_entry(
			item_code=item_1,
			qty=10,
			rate=100,
			source="_Test Warehouse - _TC",
			target="Stores - _TC",
			purpose="Material Transfer",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)

		semt.append(
			"items",
			{
				"item_code": item_2,
				"qty": 10,
				"basic_rate": 150,
				"t_warehouse": "Stores - _TC",
				"s_warehouse": "_Test Warehouse - _TC",
				"expense_account": "Stock Adjustment - _TC",
			},
		)

		semt.save()
		semt.submit()

		sle = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": semt.name}, fields=["actual_qty", "item_code"]
		)
		sle_records = {entry["item_code"]: [] for entry in sle}

		for entry in sle:
			sle_records[entry["item_code"]].append(entry["actual_qty"])

		self.assertCountEqual(sle_records[item_1], [10, -10])
		self.assertCountEqual(sle_records[item_2], [10, -10])

	@change_settings(
		"Stock Settings",
		{
			"use_serial_batch_fields": 0,
			"disable_serial_no_and_batch_selector": 0,
			"auto_create_serial_and_batch_bundle_for_outward": 0,
			"pick_serial_and_batch_based_on": "FIFO",
		},
	)
	def test_mt_with_disable_serial_batch_no_outward_TC_SCK_116(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Stock Adjustment",
			parent_account="Stock Expenses - _TC",
			company="_Test Company",
		)

		fields = {
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ABC.##",
			"has_serial_no": 1,
			"serial_no_series": "AAB.##",
		}

		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_1 = make_item("_Test Batch Item 1", properties=fields).name

		semr = make_stock_entry(
			item_code=item_1,
			qty=15,
			rate=100,
			target="_Test Warehouse - _TC",
			purpose="Material Receipt",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)
		semr.save()
		semr.submit()

		semt = make_stock_entry(
			item_code=item_1,
			qty=10,
			rate=100,
			source="_Test Warehouse - _TC",
			target="Stores - _TC",
			purpose="Material Transfer",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)
		semt.save()
		semt.submit()

		sle = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": semt.name}, fields=["actual_qty", "item_code"]
		)
		sle_records = {entry["item_code"]: [] for entry in sle}

		for entry in sle:
			sle_records[entry["item_code"]].append(entry["actual_qty"])

		self.assertCountEqual(sle_records[item_1], [10, -10])

	@change_settings(
		"Stock Settings",
		{
			"use_serial_batch_fields": 0,
			"disable_serial_no_and_batch_selector": 0,
			"auto_create_serial_and_batch_bundle_for_outward": 0,
			"pick_serial_and_batch_based_on": "FIFO",
		},
	)
	def test_mt_with_multiple_items_disable_serial_batch_no_outward_TC_SCK_117(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Stock Adjustment",
			parent_account="Stock Expenses - _TC",
			company="_Test Company",
		)

		fields = {
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ABC.##",
			"has_serial_no": 1,
			"serial_no_series": "AAB.##",
		}

		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_1 = make_item("_Test Batch Item 1", properties=fields).name
		item_2 = make_item("_Test Batch Item 2", properties=fields).name

		semr = make_stock_entry(
			item_code=item_1,
			qty=15,
			rate=100,
			target="_Test Warehouse - _TC",
			purpose="Material Receipt",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)

		semr.append(
			"items",
			{
				"item_code": item_2,
				"qty": 15,
				"basic_rate": 150,
				"t_warehouse": "_Test Warehouse - _TC",
				"expense_account": "Stock Adjustment - _TC",
			},
		)

		semr.save()
		semr.submit()

		semt = make_stock_entry(
			item_code=item_1,
			qty=10,
			rate=100,
			source="_Test Warehouse - _TC",
			target="Stores - _TC",
			purpose="Material Transfer",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)

		semt.append(
			"items",
			{
				"item_code": item_2,
				"qty": 10,
				"basic_rate": 150,
				"t_warehouse": "Stores - _TC",
				"s_warehouse": "_Test Warehouse - _TC",
				"expense_account": "Stock Adjustment - _TC",
			},
		)

		semt.save()
		semt.submit()

		sle = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": semt.name}, fields=["actual_qty", "item_code"]
		)
		sle_records = {entry["item_code"]: [] for entry in sle}

		for entry in sle:
			sle_records[entry["item_code"]].append(entry["actual_qty"])

		self.assertCountEqual(sle_records[item_1], [10, -10])
		self.assertCountEqual(sle_records[item_2], [10, -10])

	@change_settings("Stock Settings", {"default_warehouse": "_Test Warehouse - _TC"})
	def test_item_creation_TC_SCK_118(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		company = "_Test Company"
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Stock Adjustment",
			parent_account="Stock Expenses - _TC",
			company="_Test Company",
		)
		item_1 = create_item(
			item_code="_Test Item New", is_stock_item=1, opening_stock=15, valuation_rate=100
		)
		for itm in item_1.item_defaults:
			itm.expense_account = "Stock Adjustment - _TC"
		item_1.save()

		stock = frappe.get_all(
			"Stock Ledger Entry", filters={"item_code": item_1.name}, fields=["warehouse", "actual_qty"]
		)

		self.assertEqual(stock[0]["warehouse"], "_Test Warehouse - _TC")
		self.assertEqual(stock[0]["actual_qty"], 15)

	@change_settings(
		"Stock Settings",
		{
			"use_serial_batch_fields": 0,
			"disable_serial_no_and_batch_selector": 0,
			"auto_create_serial_and_batch_bundle_for_outward": 0,
			"pick_serial_and_batch_based_on": "FIFO",
		},
	)
	def test_mt_with_different_warehouse_disable_serial_batch_no_outward_TC_SCK_119(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Stock Adjustment",
			parent_account="Stock Expenses - _TC",
			company="_Test Company",
		)

		fields = {
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ABC.##",
			"has_serial_no": 1,
			"serial_no_series": "AAB.##",
		}

		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_1 = make_item("_Test Batch Item 1", properties=fields).name
		item_2 = make_item("_Test Batch Item 2", properties=fields).name

		semr = make_stock_entry(
			item_code=item_1,
			qty=15,
			rate=100,
			target="_Test Warehouse - _TC",
			purpose="Material Receipt",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)

		semr.append(
			"items",
			{
				"item_code": item_2,
				"qty": 15,
				"basic_rate": 150,
				"t_warehouse": "Stores - _TC",
				"expense_account": "Stock Adjustment - _TC",
			},
		)

		semr.save()
		semr.submit()

		semt = make_stock_entry(
			item_code=item_1,
			qty=10,
			rate=100,
			source="_Test Warehouse - _TC",
			target="Stores - _TC",
			purpose="Material Transfer",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)

		semt.append(
			"items",
			{
				"item_code": item_2,
				"qty": 10,
				"basic_rate": 150,
				"t_warehouse": "_Test Warehouse - _TC",
				"s_warehouse": "Stores - _TC",
				"expense_account": "Stock Adjustment - _TC",
			},
		)

		semt.save()
		semt.submit()

		sle = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": semt.name}, fields=["actual_qty", "item_code"]
		)
		sle_records = {entry["item_code"]: [] for entry in sle}

		for entry in sle:
			sle_records[entry["item_code"]].append(entry["actual_qty"])

		self.assertCountEqual(sle_records[item_1], [10, -10])
		self.assertCountEqual(sle_records[item_2], [10, -10])

	@change_settings(
		"Stock Settings",
		{
			"use_serial_batch_fields": 0,
			"disable_serial_no_and_batch_selector": 0,
			"auto_create_serial_and_batch_bundle_for_outward": 0,
		},
	)
	def test_mi_with_disable_batch_selector_TC_SCK_120(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Stock Adjustment",
			parent_account="Stock Expenses - _TC",
			company="_Test Company",
		)

		fields = {
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ABC.##",
			"has_serial_no": 1,
			"serial_no_series": "AAB.##",
		}

		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_1 = make_item("_Test Batch Item 1", properties=fields).name

		make_stock_entry(
			item_code=item_1,
			qty=15,
			rate=100,
			target="_Test Warehouse - _TC",
			purpose="Material Receipt",
			expense_account="Stock Adjustment - _TC",
		)

		semt = make_stock_entry(
			item_code=item_1,
			qty=10,
			rate=100,
			source="_Test Warehouse - _TC",
			target="Stores - _TC",
			purpose="Material Issue",
			expense_account="Stock Adjustment - _TC",
		)

		sle = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": semt.name}, fields=["actual_qty", "item_code"]
		)
		sle_records = {entry["item_code"]: [] for entry in sle}
		for entry in sle:
			sle_records[entry["item_code"]].append(entry["actual_qty"])

		self.assertEqual(sle_records[item_1], [-10])

	@change_settings(
		"Stock Settings",
		{
			"use_serial_batch_fields": 0,
			"disable_serial_no_and_batch_selector": 0,
			"auto_create_serial_and_batch_bundle_for_outward": 0,
			"pick_serial_and_batch_based_on": "FIFO",
		},
	)
	def test_mi_with_multiple_item_disable_batch_selector_TC_SCK_121(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Stock Adjustment",
			parent_account="Stock Expenses - _TC",
			company="_Test Company",
		)

		fields = {
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ABC.##",
			"has_serial_no": 1,
			"serial_no_series": "AAB.##",
		}

		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_1 = make_item("_Test Batch Item 1", properties=fields).name
		item_2 = make_item("_Test Batch Item 2", properties=fields).name

		semr = make_stock_entry(
			item_code=item_1,
			qty=15,
			rate=100,
			target="_Test Warehouse - _TC",
			purpose="Material Receipt",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)

		semr.append(
			"items",
			{
				"item_code": item_2,
				"qty": 15,
				"basic_rate": 150,
				"t_warehouse": "Stores - _TC",
				"expense_account": "Stock Adjustment - _TC",
			},
		)

		semr.save()
		semr.submit()

		semt = make_stock_entry(
			item_code=item_1,
			qty=10,
			rate=100,
			source="_Test Warehouse - _TC",
			target="Stores - _TC",
			purpose="Material Issue",
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)

		semt.append(
			"items",
			{
				"item_code": item_2,
				"qty": 10,
				"basic_rate": 150,
				"t_warehouse": "_Test Warehouse - _TC",
				"s_warehouse": "Stores - _TC",
				"expense_account": "Stock Adjustment - _TC",
			},
		)

		semt.save()
		semt.submit()

		sle = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": semt.name}, fields=["actual_qty", "item_code"]
		)
		sle_records = {entry["item_code"]: [] for entry in sle}

		for entry in sle:
			sle_records[entry["item_code"]].append(entry["actual_qty"])

		self.assertEqual(sle_records[item_1], [-10])
		self.assertEqual(sle_records[item_2], [-10])

	def test_single_mr_with_multiple_se_tc_sck_123(self):
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		mr = make_material_request(material_request_type="Material Transfer")

		self.assertEqual(mr.status, "Pending")

		se1 = make_mr_se(mr.name)
		se1.items[0].qty = 5
		se1.from_warehouse = "_Test Warehouse - _TC"
		se1.items[0].t_warehouse = "Stores - _TC"
		se1.insert()
		se1.submit()

		self.assertEqual(se1.stock_entry_type, "Material Transfer")
		mr.load_from_db()
		self.assertEqual(mr.status, "Partially Received")
		self.check_stock_ledger_entries(
			"Stock Entry",
			se1.name,
			[
				["_Test Item", "_Test Warehouse - _TC", -5],
				["_Test Item", "Stores - _TC", 5],
			],
		)
		se2 = make_mr_se(mr.name)
		se2.from_warehouse = "_Test Warehouse - _TC"
		se2.items[0].t_warehouse = "Stores - _TC"
		se2.insert()
		se2.submit()
		self.check_stock_ledger_entries(
			"Stock Entry",
			se2.name,
			[
				["_Test Item", "_Test Warehouse - _TC", -5],
				["_Test Item", "Stores - _TC", 5],
			],
		)
		mr.load_from_db()
		self.assertEqual(mr.status, "Transferred")

	def test_mr_to_se_with_in_transit_tc_sck_124(self):
		from erpnext.stock.doctype.material_request.material_request import make_in_transit_stock_entry
		from erpnext.stock.doctype.material_request.test_material_request import (
			get_in_transit_warehouse,
			make_material_request,
		)

		mr = make_material_request(material_request_type="Material Transfer")
		self.assertEqual(mr.status, "Pending")

		in_transit_warehouse = get_in_transit_warehouse(mr.company)
		transit_entry = make_in_transit_stock_entry(mr.name, in_transit_warehouse)
		transit_entry.items[0].s_warehouse = "_Test Warehouse - _TC"
		transit_entry.insert()
		transit_entry.submit()

		end_transit_entry = make_stock_in_entry(transit_entry.name)
		end_transit_entry.submit()

		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_no": end_transit_entry.name})
		self.assertEqual(sle.actual_qty, 10)

	def test_stock_entry_tc_sck_136(self):
		item_code = make_item(
			"_Test Item Stock Entry New", {"valuation_rate": 100, "expense_account": "Stock Adjustment - _TC"}
		)
		se = make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=1, do_not_submit=True)
		se.stock_entry_type = "Manufacture"
		se.items[0].is_finished_item = 1
		se.submit()
		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_no": se.name})
		self.assertEqual(sle.qty_after_transaction, 1)

	def test_partial_material_issue_TC_SCK_205(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		company = "_Test Company"
		get_or_create_fiscal_year("_Test Company")
		create_customer(name="_Test Customer")
		frappe.db.set_value(
			"Company",
			company,
			{"enable_perpetual_inventory": 1, "stock_adjustment_account": "Stock Adjustment - _TC"},
		)
		fields = {
			"shelf_life_in_days": 365,
			"end_of_life": "2099-12-31",
			"is_stock_item": 1,
			"has_serial_no": 1,
			"create_new_batch": 1,
			"has_expiry_date": 1,
			"serial_no_series": "Test-SL-SN.#####",
			"valuation_rate": 100,
		}
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_code = make_item("COOKIES (SL)", fields).name

		source_warehouse = "Department Store - _TC"
		target_warehouse = create_warehouse(
			warehouse_name="Department Store",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company=company,
		)
		qty = 10

		# Stock Receipt
		make_stock_entry(
			item_code=item_code,
			qty=qty,
			to_warehouse=target_warehouse,
			company=company,
		)
		cost_center = frappe.db.get_all("Cost Center", {"company": company, "is_group": 0}, "name")
		# Create Material Request
		mr = make_material_request(
			material_request_type="Material Issue",
			qty=qty,
			warehouse=target_warehouse,
			item_code=item_code,
			company=company,
			cost_center=cost_center[0].name,
			uom="Unit",
		)
		self.assertEqual(mr.status, "Pending")

		se1 = make_mr_se(mr.name)
		se1.company = company
		se1.items[0].qty = 5
		se1.s_warehouse = target_warehouse
		se1.t_warehouse = source_warehouse
		se1.items[0].expense_account = "Cost of Goods Sold - _TC"
		se1.insert()
		se1.submit()

		self.assertEqual(se1.stock_entry_type, "Material Issue")
		mr.load_from_db()
		self.assertEqual(mr.status, "Partially Ordered")

		# Check Stock Ledger Entries
		self.check_stock_ledger_entries(
			"Stock Entry",
			se1.name,
			[
				[item_code, target_warehouse, -5],
				[item_code, source_warehouse, 5],
			],
		)

		# Check GL Entries
		stock_in_hand_account = get_inventory_account(company, target_warehouse)
		cogs_account = "Cost of Goods Sold - _TC"
		self.check_gl_entries(
			"Stock Entry",
			se1.name,
			sorted(
				[
					[stock_in_hand_account, 0.0, 500.0],
					[cogs_account, 500.0, 0.0],
				]
			),
		)

	def test_partial_material_issue_TC_SCK_206(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		company = "_Test Company"
		get_or_create_fiscal_year("_Test Company")
		create_customer(name="_Test Customer")
		frappe.db.set_value(
			"Company",
			company,
			{"enable_perpetual_inventory": 1, "stock_adjustment_account": "Stock Adjustment - _TC"},
		)
		fields = {
			"shelf_life_in_days": 365,
			"end_of_life": "2099-12-31",
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"has_expiry_date": 1,
			"batch_number_series": "Test-SABBMRP-Bno.#####",
			"has_serial_no": 1,
			"serial_no_series": "Test-SL-SN.#####",
			"valuation_rate": 100,
		}
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_code = make_item("COOKIES (BT-SL)", fields).name

		source_warehouse = "Stores - _TC"
		target_warehouse = create_warehouse(
			warehouse_name="Department Store",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company=company,
		)
		qty = 10

		# Stock Receipt
		make_stock_entry(
			item_code=item_code,
			qty=qty,
			to_warehouse=target_warehouse,
			company=company,
		)
		cost_center = frappe.db.get_all("Cost Center", {"company": company, "is_group": 0}, "name")
		# Create Material Request
		mr = make_material_request(
			material_request_type="Material Issue",
			qty=qty,
			warehouse=target_warehouse,
			item_code=item_code,
			company=company,
			posting_date="2024-12-19",
			required_by_date="2024-12-20",
			cost_center=cost_center[0].name,
			uom="Unit",
		)
		self.assertEqual(mr.status, "Pending")

		se1 = make_mr_se(mr.name)
		se1.company = company
		se1.items[0].qty = 5
		se1.s_warehouse = target_warehouse
		se1.t_warehouse = source_warehouse
		se1.items[0].expense_account = "Cost of Goods Sold - _TC"
		se1.insert()
		se1.submit()

		self.assertEqual(se1.stock_entry_type, "Material Issue")
		mr.load_from_db()
		self.assertEqual(mr.status, "Partially Ordered")

		# Check Stock Ledger Entries

		self.check_stock_ledger_entries(
			"Stock Entry",
			se1.name,
			[
				[item_code, target_warehouse, -5],
				[item_code, source_warehouse, 5],
			],
		)

		# Check GL Entries
		stock_in_hand_account = get_inventory_account(company, target_warehouse)
		cogs_account = "Cost of Goods Sold - _TC"
		self.check_gl_entries(
			"Stock Entry",
			se1.name,
			sorted(
				[
					[stock_in_hand_account, 0.0, 500.0],
					[cogs_account, 500.0, 0.0],
				]
			),
		)

	def test_partial_material_transfer_TC_SCK_207(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer
		from erpnext.stock import get_warehouse_account_map
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		create_account(
			account_name="Stocks Assets",
			account_type="Fixed Asset",
			company="_Test Company",
			is_group=1,
			parent_account="Fixed Assets - _TC",
		)
		company_doc = frappe.get_doc("Company", "_Test Company")
		frappe._set_document_in_cache("Company", company_doc)
		company = "_Test Company"
		get_or_create_fiscal_year("_Test Company")
		create_customer(name="_Test Customer")
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")
		fields = {
			"shelf_life_in_days": 365,
			"end_of_life": "2099-12-31",
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"has_expiry_date": 1,
			"batch_number_series": "Test-SABBMRP-Bno.#####",
			"has_serial_no": 1,
			"serial_no_series": "Test-SL-SN.#####",
			"valuation_rate": 100,
		}
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_code = make_item("COOKIES (BT-SL)", fields).name

		source_warehouse = "Stores - _TC"
		target_warehouse = create_warehouse(
			warehouse_name="Department Store",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company=company,
		)
		qty = 10
		if frappe.db.exists("Company", "PP2 Ltd"):
			frappe.db.set_value("Company", "PP2 Ltd", "default_inventory_account", "Stock In Hand - _TC")

			if frappe.db.exists("Warehouse", "Stores - PP2 Ltd"):
				frappe.db.set_value("Warehouse", "Stores - PP2 Ltd", "account", "Stock In Hand - _TC")

		get_warehouse_account_map()
		# Stock Receipt
		make_stock_entry(
			item_code=item_code,
			qty=qty,
			to_warehouse=target_warehouse,
			company=company,
		)

		cost_center = frappe.db.get_all("Cost Center", {"company": company, "is_group": 0}, "name")
		# Create Material Request
		mr = make_material_request(
			material_request_type="Material Transfer",
			qty=qty,
			warehouse=target_warehouse,
			item_code=item_code,
			company=company,
			posting_date="2024-12-19",
			required_by_date="2024-12-20",
			cost_center=cost_center[0].name,
			uom="Unit",
		)
		self.assertEqual(mr.status, "Pending")

		se1 = make_mr_se(mr.name)
		se1.company = company
		se1.items[0].qty = 5
		se1.from_warehouse = target_warehouse
		se1.items[0].t_warehouse = source_warehouse
		se1.items[0].expense_account = "Cost of Goods Sold - _TC"
		se1.insert()
		se1.submit()

		self.assertEqual(se1.stock_entry_type, "Material Transfer")
		mr.load_from_db()
		self.assertEqual(mr.status, "Partially Received")

		# Check Stock Ledger Entries
		self.check_stock_ledger_entries(
			"Stock Entry",
			se1.name,
			[
				[item_code, target_warehouse, -5],
				[item_code, source_warehouse, 5],
			],
		)

		# Check GL Entries
		stock_in_hand_account = get_inventory_account(company, source_warehouse)
		cogs_account = "Cost of Goods Sold - _TC"
		self.check_gl_entries(
			"Stock Entry",
			se1.name,
			sorted(
				[
					[stock_in_hand_account, 500.0, 0.0],
					[cogs_account, 0.0, 500.0],
				]
			),
		)

	def test_partial_material_transfer_TC_SCK_208(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer
		from erpnext.stock import get_warehouse_account_map
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		company = "_Test Company"

		company_doc = frappe.get_doc("Company", company)
		frappe._set_document_in_cache("Company", company_doc)
		get_or_create_fiscal_year("_Test Company")
		create_customer(name="_Test Customer")
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")
		fields = {
			"shelf_life_in_days": 365,
			"end_of_life": "2099-12-31",
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"has_expiry_date": 1,
			"batch_number_series": "Test-SABBMRP-Bno.#####",
			"has_serial_no": 1,
			"serial_no_series": "Test-SL-SN.#####",
			"valuation_rate": 100,
		}
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_code = make_item("COOKIES (BT-SL)", fields).name

		source_warehouse = "Stores - _TC"
		target_warehouse = create_warehouse(
			warehouse_name="Department Store",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company=company,
		)
		qty = 10
		get_warehouse_account_map(company)
		# Stock Receipt
		make_stock_entry(
			item_code=item_code,
			qty=qty,
			to_warehouse=target_warehouse,
			company=company,
		)

		cost_center = frappe.db.get_all("Cost Center", {"company": company, "is_group": 0}, "name")
		# Create Material Request
		mr = make_material_request(
			material_request_type="Material Transfer",
			qty=qty,
			warehouse=target_warehouse,
			item_code=item_code,
			company=company,
			posting_date="2024-12-19",
			required_by_date="2024-12-20",
			cost_center=cost_center[0].name,
			uom="Unit",
		)
		self.assertEqual(mr.status, "Pending")

		se1 = make_mr_se(mr.name)
		se1.company = company
		se1.items[0].qty = 5
		se1.from_warehouse = target_warehouse
		se1.items[0].t_warehouse = source_warehouse
		se1.items[0].expense_account = "Cost of Goods Sold - _TC"
		se1.insert()
		se1.submit()

		self.assertEqual(se1.stock_entry_type, "Material Transfer")
		mr.load_from_db()
		self.assertEqual(mr.status, "Partially Received")

		# Check Stock Ledger Entries
		self.check_stock_ledger_entries(
			"Stock Entry",
			se1.name,
			[
				[item_code, target_warehouse, -5],
				[item_code, source_warehouse, 5],
			],
		)

		# Check GL Entries
		stock_in_hand_account = get_inventory_account(company, source_warehouse)
		cogs_account = "Cost of Goods Sold - _TC"
		self.check_gl_entries(
			"Stock Entry",
			se1.name,
			sorted(
				[
					[stock_in_hand_account, 500.0, 0.0],
					[cogs_account, 0.0, 500.0],
				]
			),
		)

	def test_partial_material_transfer_TC_SCK_209(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		company = "_Test Company"
		get_or_create_fiscal_year("_Test Company")
		create_customer(name="_Test Customer")
		frappe.db.set_value(
			"Company",
			company,
			{"enable_perpetual_inventory": 1, "stock_adjustment_account": "Stock Adjustment - _TC"},
		)
		fields = {
			"shelf_life_in_days": 365,
			"end_of_life": "2099-12-31",
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"has_expiry_date": 1,
			"batch_number_series": "Test-SABBMRP-Bno.#####",
			"has_serial_no": 1,
			"serial_no_series": "Test-SL-SN.#####",
			"valuation_rate": 100,
		}
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item_code = make_item("COOKIES (BT-SL)", fields).name

		source_warehouse = "Stores - _TC"

		target_warehouse = create_warehouse(
			warehouse_name="Department Store",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company=company,
		)
		qty = 10

		# Stock Receipt

		make_stock_entry(
			item_code=item_code,
			qty=qty,
			to_warehouse=target_warehouse,
			company=company,
		)
		cost_center = frappe.db.get_all("Cost Center", {"company": company, "is_group": 0}, "name")

		# Create Material Request
		mr = make_material_request(
			material_request_type="Material Transfer",
			qty=qty,
			warehouse=target_warehouse,
			item_code=item_code,
			company=company,
			posting_date="2024-12-19",
			required_by_date="2024-12-20",
			cost_center=cost_center[0].name,
			uom="Unit",
		)
		self.assertEqual(mr.status, "Pending")

		se1 = make_mr_se(mr.name)
		se1.company = company
		se1.items[0].qty = 5
		se1.from_warehouse = target_warehouse
		se1.items[0].t_warehouse = source_warehouse
		se1.items[0].expense_account = "Cost of Goods Sold - _TC"
		se1.insert()
		se1.submit()

		self.assertEqual(se1.stock_entry_type, "Material Transfer")
		mr.load_from_db()
		self.assertEqual(mr.status, "Partially Received")

		# Check Stock Ledger Entries
		self.check_stock_ledger_entries(
			"Stock Entry",
			se1.name,
			[
				[item_code, target_warehouse, -5],
				[item_code, source_warehouse, 5],
			],
		)

		# Check GL Entries
		stock_in_hand_account = get_inventory_account(company, source_warehouse)
		cogs_account = "Cost of Goods Sold - _TC"
		self.check_gl_entries(
			"Stock Entry",
			se1.name,
			sorted(
				[
					[stock_in_hand_account, 500.0, 0.0],
					[cogs_account, 0.0, 500.0],
				]
			),
		)

	def test_stock_manufacture_with_batch_serial_TC_SCK_142(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		company = "_Test Company"
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")

		get_or_create_fiscal_year(company)
		create_warehouse("_Test Warehouse Group - _TC", company=company)
		if not frappe.db.exists("Company", company):
			company_doc = frappe.new_doc("Company")
			company_doc.company_name = company
			company_doc.country = "India"
			company_doc.default_currency = "INR"
			company_doc.save()
		else:
			company_doc = frappe.get_doc("Company", company)

		item_1 = make_item("ADI-SH-W09", {"has_batch_no": 1, "create_new_batch": 1, "valuation_rate": 100})
		item_2 = make_item("LET-SC-002", {"valuation_rate": 100})

		se = make_stock_entry(purpose="Manufacture", company=company_doc.name, do_not_save=True)

		items = [
			{
				"t_warehouse": create_warehouse("Test Store 1"),
				"item_code": item_1.item_code,
				"qty": 200,
				"is_finished_item": 1,
				"conversion_factor": 1,
			},
			{
				"t_warehouse": create_warehouse("Test Store 2"),
				"item_code": item_2.item_code,
				"qty": 50,
				"is_scrap_item": 1,
				"conversion_factor": 1,
			},
		]

		se.items = []
		for item in items:
			se.append("items", item)

		se.save()
		se.submit()

		self.assertEqual(se.purpose, "Manufacture")
		self.assertEqual(se.items[0].is_finished_item, 1)
		self.assertEqual(se.items[1].is_scrap_item, 1)

		sle_entries = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": se.name}, fields=["item_code", "actual_qty"]
		)

		for sle in sle_entries:
			if sle["item_code"] == item_1.item_code:
				self.assertEqual(sle["actual_qty"], 200)
			elif sle["item_code"] == item_2.item_code:
				self.assertEqual(sle["actual_qty"], 50)

	def test_stock_manufacture_with_batch_serieal_TC_SCK_140(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		company = "_Test Company"
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")
		get_or_create_fiscal_year(company)
		create_warehouse("_Test Warehouse Group - _TC", company=company)

		if not frappe.db.exists("Company", company):
			company_doc = frappe.new_doc("Company")
			company_doc.company_name = company
			company_doc.country = "India"
			company_doc.default_currency = "INR"
			company_doc.save()
		else:
			company_doc = frappe.get_doc("Company", company)

		item = make_item(
			"ADI-SH-W11",
			{
				"valuation_rate": 100,
				"has_serial_no": 1,
				"serial_no_series": "SNO-.####",
				"has_batch_no": 1,
				"create_new_batch": 0,
				"is_stock_item": 1,
			},
		)

		if not frappe.db.exists("Batch", "BATCH-001"):
			batch = frappe.get_doc(
				{
					"doctype": "Batch",
					"item": item.name,
					"batch_id": "BATCH-001",
					"manufacturing_date": frappe.utils.nowdate(),
				}
			)
			batch.insert()
		else:
			batch = frappe.get_doc("Batch", "BATCH-001")

		serial_nos = generate_serial_nos(item_code=item.name, qty=150)
		se = make_stock_entry(
			item_code=item.name,
			purpose="Manufacture",
			company=company_doc.name,
			target=create_warehouse("Test Warehouse"),
			qty=150,
			basic_rate=100,
			do_not_save=True,
		)

		se.items[0].is_finished_item = 1
		se.items[0].serial_no = "\n".join(serial_nos)  # Assign serial numbers
		se.items[0].batch_no = batch.name
		se.save()
		se.submit()
		self.assertEqual(se.purpose, "Manufacture")
		self.assertEqual(se.items[0].is_finished_item, 1)

		serial_and_batch = run(
			"Serial and Batch Summary",
			filters={
				"company": company_doc.name,
				"from_date": se.posting_date,
				"to_date": se.posting_date,
				"voucher_type": "Stock Entry",
				"voucher_no": [se.name],
			},
		)

		result_list = serial_and_batch.get("result", [])
		self.assertEqual(len(result_list), 150)  # Expect 150 serial numbers

		sle_entries = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": se.name}, fields=["item_code", "actual_qty"]
		)
		for sle in sle_entries:
			if sle["item_code"] == item.item_code:
				self.assertEqual(sle["actual_qty"], 150)

	@change_settings("Stock Settings", {"allow_negative_stock": 1})
	def test_stock_entry_manufacture_TC_SCK_138(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		company = "_Test Company"
		create_company()
		warehouse = create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company=company,
		)
		get_or_create_fiscal_year("_Test Company")
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")
		se = make_stock_entry(
			company=company,
			purpose="Manufacture",
			expense_account="Stock Adjustment - _TC",
			do_not_submit=True,
			do_not_save=True,
		)
		item_1 = create_item(item_code="W-N-001", warehouse=warehouse, valuation_rate=100)
		item_2 = create_item(item_code="ST-N-001", warehouse=warehouse, valuation_rate=200)
		item_3 = create_item(item_code="GU-SE-001", warehouse=warehouse, valuation_rate=300)
		item_4 = create_item(item_code="SCW-N-001", warehouse=warehouse, valuation_rate=400)
		items = [
			{
				"s_warehouse": create_warehouse(
					"Test Store 1", properties={"parent_warehouse": "All Warehouses - _TC"}, company=company
				),
				"item_code": item_1.item_code,
				"qty": 10,
				"conversion_factor": 1,
			},
			{
				"s_warehouse": create_warehouse(
					"Test Store 2", properties={"parent_warehouse": "All Warehouses - _TC"}, company=company
				),
				"item_code": item_2.item_code,
				"qty": 42,
				"conversion_factor": 1,
			},
			{
				"t_warehouse": create_warehouse(
					"Test Store 3", properties={"parent_warehouse": "All Warehouses - _TC"}, company=company
				),
				"item_code": item_3.item_code,
				"qty": 8,
				"is_finished_item": 1,
				"conversion_factor": 1,
			},
			{
				"t_warehouse": create_warehouse(
					"Test Store 4", properties={"parent_warehouse": "All Warehouses - _TC"}, company=company
				),
				"item_code": item_4.item_code,
				"qty": 2,
				"conversion_factor": 1,
			},
		]
		se.items = []
		for item in items:
			se.append("items", item)
		se.save()
		se.submit()
		self.assertEqual(se.items[0].qty, 10)
		self.assertEqual(se.purpose, "Manufacture")
		self.assertEqual(se.items[2].is_finished_item, 1)
		sle_entries = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": se.name}, fields=["item_code", "actual_qty"]
		)
		for sle in sle_entries:
			if sle["item_code"] == item_1.item_code:
				self.assertEqual(sle["actual_qty"], -10)
			elif sle["item_code"] == item_2.item_code:
				self.assertEqual(sle["actual_qty"], -42)
			elif sle["item_code"] == item_3.item_code:
				self.assertEqual(sle["actual_qty"], 8)
			elif sle["item_code"] == item_4.item_code:
				self.assertEqual(sle["actual_qty"], 2)

	@change_settings("Stock Settings", {"allow_negative_stock": 1})
	def test_create_mr_se_TC_SCK_063(self):
		from erpnext.stock.doctype.material_request.material_request import (
			make_stock_entry as _make_stock_entry,
		)
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		item = make_item("_Test Item")
		target_warehouse = create_warehouse("_Test Warehouse", company="_Test Company")
		source_warehouse = create_warehouse("_Test Source Warehouse", company="_Test Company")
		mr = make_material_request(
			material_request_type="Material Transfer",
			qty=10,
			warehouse=target_warehouse,
			from_warehouse=source_warehouse,
			item=item.name,
		)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer

		create_company()
		create_customer("_Test Customer")
		item = make_item("_Test Item", properties={"valuation_rate": 100})
		get_or_create_fiscal_year("_Test Company")

		target_warehouse = create_warehouse(
			warehouse_name="_Test Warehouse",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		source_warehouse = create_warehouse(
			warehouse_name="_Test Source Warehouse",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		cost_center = frappe.db.get_all("Cost Center", {"company": "_Test Company"}, "name")
		mr = make_material_request(
			material_request_type="Material Transfer",
			qty=10,
			warehouse=target_warehouse,
			from_warehouse=source_warehouse,
			item=item.name,
			uom="Box",
			cost_center=cost_center[1]["name"],
		)
		self.assertEqual(mr.status, "Pending")
		se_1 = _make_stock_entry(mr.name)
		se_1.get("items")[0].qty = 5
		se_1.insert()
		se_1.submit()
		mr.load_from_db()
		self.assertEqual(mr.status, "Partially Received")
		self.check_stock_ledger_entries(
			"Stock Entry", se_1.name, [[item.name, target_warehouse, 5], [item.name, source_warehouse, -5]]
		)
		se_2 = _make_stock_entry(mr.name)
		se_2.get("items")[0].qty = 5
		se_2.insert()
		se_2.submit()
		mr.load_from_db()
		self.assertEqual(mr.material_request_type, "Material Transfer")
		self.assertEqual(mr.status, "Transferred")
		self.check_stock_ledger_entries(
			"Stock Entry", se_2.name, [[item.name, target_warehouse, 5], [item.name, source_warehouse, -5]]
		)

	def test_stock_manufacture_with_batch_serial_TC_SCK_141(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		company = "_Test Company"
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")
		get_or_create_fiscal_year(company)
		create_warehouse("_Test Warehouse Group - _TC", company=company)

		if not frappe.db.exists("Company", company):
			company_doc = frappe.new_doc("Company")
			company_doc.company_name = company
			company_doc.country = "India"
			company_doc.default_currency = "INR"
			company_doc.save()
		else:
			company_doc = frappe.get_doc("Company", company)
		item_1 = make_item("ADI-SH-W08", {"has_batch_no": 1, "create_new_batch": 1, "valuation_rate": 100})
		item_2 = make_item("LET-SC-002", {"valuation_rate": 100})
		se = make_stock_entry(purpose="Manufacture", company=company_doc.name, do_not_save=True)
		items = [
			{
				"t_warehouse": create_warehouse("Test Store 1"),
				"item_code": item_1.item_code,
				"qty": 200,
				"is_finished_item": 1,
				"conversion_factor": 1,
			},
			{
				"t_warehouse": create_warehouse("Test Store 2"),
				"item_code": item_2.item_code,
				"qty": 50,
				"is_scrap_item": 1,
				"conversion_factor": 1,
			},
		]
		se.items = []
		for item in items:
			se.append("items", item)
		se.save()
		se.submit()
		self.assertEqual(se.purpose, "Manufacture")
		self.assertEqual(se.items[0].is_finished_item, 1)
		self.assertEqual(se.items[1].is_scrap_item, 1)
		sle_entries = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": se.name}, fields=["item_code", "actual_qty"]
		)
		for sle in sle_entries:
			if sle["item_code"] == item_1.item_code:
				self.assertEqual(sle["actual_qty"], 200)
			elif sle["item_code"] == item_2.item_code:
				self.assertEqual(sle["actual_qty"], 50)

	def test_create_two_stock_entries_TC_SCK_230(self):
		company = create_company_se()
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _CS")
		item_1 = make_item("_Test Item 1")
		get_or_create_fiscal_year("_Test Company SE")
		warehouse_1 = create_warehouse("_Test warehouse PO", company=company)
		se_1 = make_stock_entry(
			item_code=item_1.name,
			target=warehouse_1,
			qty=10,
			purpose="Material Receipt",
			company=company,
			do_not_save=True,
		)
		se_1.save()
		se_1.items[0].allow_zero_valuation_rate = 1
		se_1.save()
		se_1.submit()
		self.assertEqual(se_1.items[0].item_code, item_1.name)
		self.assertEqual(se_1.items[0].qty, 10)
		self.check_stock_ledger_entries("Stock Entry", se_1.name, [[item_1.name, warehouse_1, 10]])
		item_2 = make_item("_Test Item")
		warehouse_2 = create_warehouse("Stores", company=company)
		se_2 = make_stock_entry(
			item_code=item_2.name,
			target=warehouse_2,
			qty=20,
			purpose="Material Receipt",
			company=company,
			do_not_save=True,
		)
		se_2.save()
		se_2.items[0].allow_zero_valuation_rate = 1
		se_2.save()
		se_2.submit()
		self.assertEqual(se_2.items[0].item_code, item_2.name)
		self.assertEqual(se_2.items[0].qty, 20)
		self.check_stock_ledger_entries("Stock Entry", se_2.name, [[item_2.name, warehouse_2, 20]])

	def test_stock_manufacture_with_batch_TC_SCK_139(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		company = "_Test Company"
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)

		create_warehouse(
			warehouse_name="Test Warehouse",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		get_or_create_fiscal_year("_Test Company")
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")
		item = make_item("ADI-SH-W07", {"has_batch_no": 1, "create_new_batch": 1, "valuation_rate": 100})
		se = make_stock_entry(
			item_code=item.name,
			purpose="Manufacture",
			company=company,
			target=create_warehouse("Test Warehouse"),
			qty=150,
			basic_rate=100,
			expense_account="Stock Adjustment - _TC",
			do_not_save=True,
		)
		se.items[0].is_finished_item = 1
		se.save()
		se.submit()
		self.assertEqual(se.purpose, "Manufacture")
		self.assertEqual(se.items[0].is_finished_item, 1)
		sle_entries = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": se.name}, fields=["item_code", "actual_qty"]
		)
		for sle in sle_entries:
			if sle["item_code"] == item.item_code:
				self.assertEqual(sle["actual_qty"], 150)

	def test_stock_ageing_TC_SCK_227(self):
		from erpnext.stock.report.stock_ageing.stock_ageing import execute

		avail_qty = 30
		company = "_Test Company"
		item_c = []
		q = []
		range1 = []
		range2 = []
		create_company(company)
		item_fields = {"item_name": "_Test Item227", "valuation_rate": 500, "is_stock_item": 1}
		item = make_item("_Test Item227", item_fields)
		make_stock_entry(
			item_code=item.name,
			purpose="Material Receipt",
			posting_date="2024-12-01",
			company=company,
			target=create_warehouse("Test Warehouse", company=company),
			qty=10,
			expense_account="Stock Adjustment - _TC",
		)
		make_stock_entry(
			item_code=item.name,
			purpose="Material Receipt",
			posting_date="2025-01-01",
			company=company,
			target=create_warehouse("Test Warehouse", company=company),
			qty=20,
			expense_account="Stock Adjustment - _TC",
		)

		filters = frappe._dict(
			{  # Convert to allow dot notation
				"company": "_Test Company",
				"to_date": "2025-01-12",
				"item_code": item.name,
				"warehouse": create_warehouse("Test Warehouse", company=company),
				"range": "30, 60, 90",
			}
		)

		columns, data, _, chart_data = execute(filters)

		item_c.append(data[0][0])
		q.append(data[0][5])
		range1.append(data[0][7])
		range2.append(data[0][9])

		item_c = set(item_c)
		item_c = list(item_c)
		range1 = set(range1)
		range1 = list(range1)
		range2 = set(range2)
		range2 = list(range2)
		self.assertTrue(filters["item_code"] == item_c[0], "Item tc failed")
		self.assertTrue(q[0] == avail_qty)

	def test_inactive_sales_items_TC_SCK_228(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.report.inactive_sales_items.inactive_sales_items import execute

		company = "_Test Company"

		# Ensure company exists
		if not frappe.db.exists("Company", company):
			company_doc = frappe.new_doc("Company")
			company_doc.company_name = company
			company_doc.country = "India"
			company_doc.default_currency = "INR"
			company_doc.insert()

		create_cost_center(cost_center_name="_Test Cost Center", company=company)
		# Create Warehouse
		target_warehouse = create_warehouse(
			warehouse_name="Test Warehouse",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company=company,
		)
		company_doc = frappe.get_doc("Company", "_Test Company")
		frappe.local.enable_perpetual_inventory = {}
		frappe.local.enable_perpetual_inventory[company_doc.name] = 0
		frappe._set_document_in_cache("Company", company_doc)
		get_or_create_fiscal_year(company)
		frappe.db.set_value("Company", company, "stock_adjustment_account", "Stock Adjustment - _TC")
		# Create items
		item_fields1 = {"item_name": "_Test Item2271", "valuation_rate": 500, "is_stock_item": 1}
		item_fields2 = {"item_name": "_Test Item2281", "valuation_rate": 500, "is_stock_item": 1}
		item1 = make_item("_Test Item2271", item_fields1)
		item2 = make_item("_Test Item2281", item_fields2)

		make_stock_entry(
			item_code=item1.name,
			purpose="Material Receipt",
			posting_date=today(),
			company=company,
			target=create_warehouse("Test Warehouse", company=company),
			qty=15,
			expense_account="Stock Adjustment - _TC",
		)
		make_stock_entry(
			item_code=item1.name,
			purpose="Material Receipt",
			posting_date=frappe.utils.add_months(today(), 1),
			company=company,
			target=create_warehouse("Test Warehouse", company=company),
			qty=25,
			expense_account="Stock Adjustment - _TC",
		)
		make_stock_entry(
			item_code=item1.name,
			set_posting_time=1,
			purpose="Material Issue",
			posting_date=frappe.utils.add_months(today(), 1),
			company=company,
			source=create_warehouse("Test Warehouse", company=company),
			qty=10,
			expense_account="Stock Adjustment - _TC",
		)
		make_stock_entry(
			item_code=item1.name,
			purpose="Material Issue",
			posting_date=frappe.utils.add_months(today(), 2),
			company=company,
			source=create_warehouse("Test Warehouse", company=company),
			qty=20,
			expense_account="Stock Adjustment - _TC",
		)

		# Create stock transactions for item1 (Active)
		make_stock_entry(
			item_code=item1.name,
			purpose="Material Receipt",
			stock_entry_type="Material Receipt",
			posting_date=nowdate(),
			company=company,
			target=target_warehouse,
			qty=15,
		)

		make_stock_entry(
			item_code=item1.name,
			purpose="Material Receipt",
			stock_entry_type="Material Receipt",
			posting_date=nowdate(),
			company=company,
			target=target_warehouse,
			qty=25,
		)
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		frappe.db.set_value("Customer", "_Test Customer", "default_currency", "INR")
		create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			item_code=item1.name,
			qty=1,
			rate=100,
			currency="INR",
		)

		# Test for Active Item
		filters = frappe._dict(
			{"territory": "India", "item": item1.name, "based_on": "Sales Invoice", "days": "30"}
		)

		columns, data = execute(filters)

		if data:
			self.assertEqual(data[0]["territory"], "India")
			self.assertEqual(data[0]["item"], item1.name)

		# Test for Inactive Item
		filters1 = frappe._dict(
			{"territory": "India", "item": item2.name, "based_on": "Sales Invoice", "days": "30"}
		)

		columns1, data1 = execute(filters1)

		if data1:
			self.assertEqual(data1[0]["territory"], "India")
			self.assertEqual(data1[0]["item"], item2.name)

	@change_settings("Stock Settings", {"allow_negative_stock": 1})
	def test_create_stock_entry_with_manufacture_purpose_TC_SCK_137(self):
		company = create_company("_Test Company")
		get_or_create_fiscal_year(company)
		item_1 = make_item(
			"W-N-001", properties={"valuation_rate": 100, "expense_account": "Stock Adjustment - _TC"}
		)
		item_2 = make_item(
			"ST-N-001", properties={"valuation_rate": 200, "expense_account": "Stock Adjustment - _TC"}
		)
		item_3 = make_item(
			"GU-SE-001", properties={"valuation_rate": 300, "expense_account": "Stock Adjustment - _TC"}
		)
		se = make_stock_entry(purpose="Manufacture", company=company, do_not_submit=True, do_not_save=True)
		items = [
			{
				"s_warehouse": create_warehouse("Test Store 1", company=company),
				"item_code": item_1.name,
				"qty": 10,
				"conversion_factor": 1,
				"expense_account": "Stock Adjustment - _TC",
			},
			{
				"s_warehouse": create_warehouse("Test Store 2", company=company),
				"item_code": item_2.name,
				"qty": 50,
				"conversion_factor": 1,
				"expense_account": "Stock Adjustment - _TC",
			},
			{
				"t_warehouse": create_warehouse("Test Store 2", company=company),
				"item_code": item_3.name,
				"qty": 10,
				"is_finished_item": 1,
				"conversion_factor": 1,
				"expense_account": "Stock Adjustment - _TC",
			},
		]
		se.items = []
		for item in items:
			se.append("items", item)
		se.save()
		se.submit()
		self.assertEqual(se.purpose, "Manufacture")
		self.assertEqual(se.items[2].is_finished_item, 1)
		sle_entries = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": se.name}, fields=["item_code", "actual_qty"]
		)
		for sle in sle_entries:
			if sle["item_code"] == item_1.name:
				self.assertEqual(sle["actual_qty"], -10)
			elif sle["item_code"] == item_2.name:
				self.assertEqual(sle["actual_qty"], -50)
			elif sle["item_code"] == item_3.name:
				self.assertEqual(sle["actual_qty"], 10)

	@change_settings(
		"Stock Settings",
		{
			"auto_create_serial_and_batch_bundle_for_outward": 1,
			"disable_serial_no_and_batch_selector": 1,
			"use_serial_batch_fields": 1,
		},
	)
	def test_material_issue_with_auto_batch_serial_TC_SCK_134(self):
		from erpnext.stock.utils import get_bin

		company = "_Test Company"
		create_company(company)
		company_doc = frappe.get_doc("Company", "_Test Company")
		frappe.local.enable_perpetual_inventory = {}
		frappe.local.enable_perpetual_inventory[company_doc.name] = 0
		frappe._set_document_in_cache("Company", company_doc)
		item_fields = {
			"item_name": "_Test Item134",
			"valuation_rate": 500,
			"has_batch_no": 1,
			"has_serial_no": 1,
			"serial_no_series": "Test-SABBMRP-Sno.#####",
			"create_new_batch": 1,
			"batch_number_series": "Test-SABBMRP-Bno.#####",
			"expense_account": "Stock Adjustment - _TC",
		}
		self.item_code = make_item("_Test Item134", item_fields).name
		self.source_warehouse = create_warehouse("Stores-test", properties=None, company="_Test Company")
		self.qty = 5
		bin = get_bin(self.item_code, self.source_warehouse)
		stock_qty = frappe.db.get_value("Bin", bin, "actual_qty")
		if not stock_qty or stock_qty < self.qty:
			# Create a stock entry to add stock if needed
			se = make_stock_entry(
				item_code=self.item_code,
				qty=10,
				to_warehouse=self.source_warehouse,
				purpose="Material Receipt",
			)
		se_req = make_stock_entry(
			item_code=self.item_code,
			qty=self.qty,
			from_warehouse=self.source_warehouse,
			purpose="Material Issue",
		)
		submitted_se = frappe.get_doc("Stock Entry", se_req.name)
		self.assertTrue(submitted_se.docstatus == 1, "Stock Entry should be submitted.")

		for item in submitted_se.items:
			self.assertTrue(item.serial_and_batch_bundle, "Batch should be auto-assigned.")
		batch_no = frappe.db.get_value(
			"Serial and Batch Entry", {"parent": submitted_se.items[0].serial_and_batch_bundle}, "batch_no"
		)

		# Validate Stock Ledger
		sle_exists = frappe.db.exists("Stock Ledger Entry", {"voucher_no": se.name})
		self.assertTrue(sle_exists, "Stock Ledger Entry should be created.")

		# Validate Serial / Batch Number tracking
		batch_exists = frappe.db.exists("Batch", {"batch_id": batch_no})
		self.assertTrue(batch_exists, "Batch should exist in the system.")

	@change_settings(
		"Stock Settings",
		{
			"auto_create_serial_and_batch_bundle_for_outward": 1,
			"disable_serial_no_and_batch_selector": 1,
			"use_serial_batch_fields": 1,
		},
	)
	def test_material_issue_with_auto_batch_serial_TC_SCK_135(self):
		from erpnext.stock.utils import get_bin

		company = "_Test Company"
		create_company(company)

		item_fields1 = {
			"item_name": "_Test Item1351",
			"valuation_rate": 500,
			"has_batch_no": 1,
			"has_serial_no": 1,
			"serial_no_series": "Test-SABBMRP-Sno.#####",
			"create_new_batch": 1,
			"batch_number_series": "Test-SABBMRP-Bno.#####",
			"expense_account": "Stock Adjustment - _TC",
		}
		item_fields2 = {
			"item_name": "_Test Item1352",
			"valuation_rate": 500,
			"has_batch_no": 1,
			"has_serial_no": 1,
			"serial_no_series": "Test1-SABBMRP-Sno.#####",
			"create_new_batch": 1,
			"batch_number_series": "Test1-SABBMRP-Bno.#####",
			"expense_account": "Stock Adjustment - _TC",
		}
		self.item_code1 = make_item("_Test Item134", item_fields1).name
		self.item_code2 = make_item("_Test Item135", item_fields2).name
		self.source_warehouse = create_warehouse("Stores-test", properties=None, company="_Test Company")
		self.qty = 5
		bin1 = get_bin(self.item_code1, self.source_warehouse)
		stock_qty1 = frappe.db.get_value("Bin", bin1, "actual_qty")
		bin2 = get_bin(self.item_code2, self.source_warehouse)
		stock_qty2 = frappe.db.get_value("Bin", bin2, "actual_qty")
		if not stock_qty1 or stock_qty1 < self.qty:
			# Create a stock entry to add stock if needed
			se = make_stock_entry(
				item_code=self.item_code1,
				qty=10,
				to_warehouse=self.source_warehouse,
				purpose="Material Receipt",
			)
		if not stock_qty2 or stock_qty2 < self.qty:
			# Create a stock entry to add stock if needed
			se = make_stock_entry(
				item_code=self.item_code2,
				qty=10,
				to_warehouse=self.source_warehouse,
				purpose="Material Receipt",
			)
		se_req = frappe.new_doc("Stock Entry")
		se_req.stock_entry_type = "Material Issue"
		se_req.posting_date = "2025-01-03"
		se_req.company = "_Test Company"
		se_req.append(
			"items", {"item_code": self.item_code1, "s_warehouse": self.source_warehouse, "qty": self.qty}
		)
		se_req.append(
			"items", {"item_code": self.item_code2, "s_warehouse": self.source_warehouse, "qty": self.qty}
		)
		se_req.insert()
		se_req.submit()
		submitted_se = frappe.get_doc("Stock Entry", se_req.name)
		self.assertTrue(submitted_se.docstatus == 1, "Stock Entry should be submitted.")

		for item in submitted_se.items:
			self.assertTrue(item.serial_and_batch_bundle, "Batch should be auto-assigned.")
		batch_no1 = frappe.db.get_value(
			"Serial and Batch Entry", {"parent": submitted_se.items[0].serial_and_batch_bundle}, "batch_no"
		)
		batch_no2 = frappe.db.get_value(
			"Serial and Batch Entry", {"parent": submitted_se.items[1].serial_and_batch_bundle}, "batch_no"
		)
		print(submitted_se.items[0].item_name, submitted_se.items[1].item_name)

		# Validate Stock Ledger
		sle_exists = frappe.db.exists("Stock Ledger Entry", {"voucher_no": se.name})
		self.assertTrue(sle_exists, "Stock Ledger Entry should be created.")

		# Validate Serial / Batch Number tracking
		batch_exists1 = frappe.db.exists("Batch", {"batch_id": batch_no1})
		self.assertTrue(batch_exists1, "Batch should exist in the system.")
		batch_exists = frappe.db.exists("Batch", {"batch_id": batch_no2})
		self.assertTrue(batch_exists, "Batch should exist in the system.")

	def test_onload_stock_entry_TC_SCK_361(self):
		warehouse = create_warehouse(warehouse_name="_Test Warehouse", company="_Test Company")

		if not frappe.db.exists("Item", "_Test Item"):
			create_item("_Test Item", warehouse=warehouse, company="_Test Company")

			# Create Stock Entry with 1 item
		se = make_stock_entry(item_code="_Test Item", target=warehouse, qty=1, basic_rate=100)

		# Simulate onload
		se.onload()

		self.assertTrue(True)

	def test_set_job_card_data_single_function_TC_SCK_362(self):
		warehouse = create_warehouse(warehouse_name="_Test Warehouse", company="_Test Company")

		# Create test item
		if not frappe.db.exists("Item", "_Test FG Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "_Test FG Item",
					"item_name": "_Test FG Item",
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"gst_hsn_code": "100111",
				}
			).insert()

			# Create BOM
		if not frappe.db.exists("BOM", {"item": "_Test FG Item"}):
			bom = frappe.get_doc(
				{
					"doctype": "BOM",
					"item": "_Test FG Item",
					"is_active": 1,
					"is_default": 1,
					"quantity": 1,
					"items": [
						{
							"item_code": "_Test FG Item",
							"qty": 1,
							"rate": 100,
						}
					],
				}
			).insert()
			bom_no = bom.name
		else:
			bom_no = frappe.get_value("BOM", {"item": "_Test FG Item"})

			# Create Work Order
		wo = frappe.get_doc(
			{
				"doctype": "Work Order",
				"production_item": "_Test FG Item",
				"bom_no": bom_no,
				"qty": 5,
				"fg_warehouse": warehouse,
				"company": "_Test Company",
			}
		).insert()

		wip_warehouse = create_warehouse(warehouse_name="WIP", company="_Test Company")

		if not frappe.db.exists("Workstation", "WS"):
			ws = frappe.get_doc(
				{
					"doctype": "Workstation",
					"workstation_name": "WS",
					"company": "_Test Company",
				}
			)
			ws.insert()

			# Create Job Card
		jc = frappe.get_doc(
			{
				"doctype": "Job Card",
				"work_order": wo.name,
				"operation": "Cutting",
				"for_quantity": 5,
				"wip_warehouse": wip_warehouse,
				"workstation": "WS",
			}
		).insert()

		# Create Stock Entry and assign job_card
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Manufacture",
				"company": "_Test Company",
				"job_card": jc.name,
			}
		)

		# Call the function to test
		se.set_job_card_data()

		# Fetch job card data for assertions
		jc_data = frappe.db.get_value(
			"Job Card", jc.name, ["for_quantity", "work_order", "bom_no"], as_dict=1
		)

		# Assertions
		assert se.fg_completed_qty == jc_data.for_quantity
		assert se.work_order == jc_data.work_order
		assert se.from_bom == 1
		assert se.bom_no == jc_data.bom_no

	def test_get_stock_and_rate_TC_SCK_363(self):
		warehouse = create_warehouse(warehouse_name="_Test Warehouse", company="_Test Company")

		if not frappe.db.exists("Item", "_Test Item"):
			create_item("_Test Item", warehouse=warehouse, company="_Test Company")

			# Create test stock entry
		se = make_stock_entry(item_code="_Test Item", target=warehouse, qty=2, basic_rate=100)

		# Call the method to test
		se.get_stock_and_rate()

		# Reload and assert
		updated_item = se.items[0]
		self.assertGreater(updated_item.basic_rate, 0)
		self.assertEqual(updated_item.amount, updated_item.basic_rate * updated_item.qty)
		self.assertGreaterEqual(updated_item.actual_qty, 2)

	@patch("assets.assets.customizations.stock.item.doc_events.validate_fixed_asset")
	def test_move_sample_to_retention_warehouse_TC_SCK_364(self, mock_validate_fixed_asset):
		frappe.set_user("Administrator")

		# Step 1: Set retention warehouse in Stock Settings
		retention_warehouse = create_warehouse("_Test Retention WH", company="_Test Company")
		frappe.db.set_value("Stock Settings", None, "sample_retention_warehouse", retention_warehouse)

		# Step 2: Create source warehouse
		source_warehouse = create_warehouse("_Test Source WH", company="_Test Company")

		# Step 3: Create item
		item = make_item("Test Item", {"stock_uom": "Nos", "is_stock_item": 1, "has_batch_no": 1})

		# Force update for gst_hsn_code if applicable
		if frappe.db.has_column("Item", "gst_hsn_code") and not item.gst_hsn_code:
			item.gst_hsn_code = "100111"

		item.is_stock_item = 1
		item.has_batch_no = 1
		item.save()

		# Also insert the corresponding batch
		if not frappe.db.exists("Batch", "TEST-BATCH-001"):
			frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": "TEST-BATCH-001",
					"item": "Test Item",
					"warehouse": source_warehouse,
					"expiry_date": add_days(nowdate(), 365),
				}
			).insert()

		stock_entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"purpose": "Material Receipt",
				"company": "_Test Company",
				"items": [
					{
						"item_code": "Test Item",
						"t_warehouse": source_warehouse,
						"qty": 10,
						"uom": "Nos",
						"stock_uom": "Nos",
						"conversion_factor": 1.0,
						"rate": 100,
						"batch_no": "TEST-BATCH-001",
					}
				],
				"docstatus": 1,
			}
		).insert()

		# Step 4: Create Serial and Batch Bundle with 1 linked Batch
		sbb = frappe.get_doc(
			{
				"doctype": "Serial and Batch Bundle",
				"item_code": "Test Item",
				"package_type": "Batch",
				"type_of_transaction": "Outward",
				"voucher_type": "Stock Entry",
				"voucher_no": stock_entry.name,
				"entries": [{"batch_no": "TEST-BATCH-001", "qty": 10}],
			}
		).insert()

		# Step 5: Prepare input data
		items = [
			{
				"item_code": "Test Item",
				"sample_quantity": 2,
				"transfer_qty": 10,
				"serial_and_batch_bundle": sbb.name,
				"t_warehouse": source_warehouse,
				"valuation_rate": 50,
				"uom": "Nos",
				"stock_uom": "Nos",
				"conversion_factor": 1.0,
			}
		]

		# Call the function
		move_sample_to_retention_warehouse("_Test Company", json.dumps(items))

	def test_get_expired_batch_items_TC_SCK_365(self):
		from erpnext.stock.doctype.stock_entry.stock_entry import get_expired_batch_items

		frappe.set_user("Administrator")
		warehouse = create_warehouse(warehouse_name="_Test Warehouse", company="_Test Company")

		# Create a unique item with batch enabled
		self.item_code = "_Test Batch Item " + frappe.generate_hash(length=5)
		if not frappe.db.exists("Item", self.item_code):
			self.item = make_item(
				self.item_code,
				{
					"is_stock_item": 1,
					"has_batch_no": 1,
					"create_new_batch": 1,
					"valuation_rate": 100,
					"stock_uom": "Nos",
				},
			)
		else:
			self.item = frappe.get_doc("Item", self.item_code)

		# Create expired batch (expired yesterday)
		self.batch_name = self.item_code + "-BATCH"
		if not frappe.db.exists("Batch", self.batch_name):
			self.batch = frappe.get_doc(
				{
					"doctype": "Batch",
					"item": self.item.name,
					"batch_id": self.batch_name,
					"expiry_date": add_days(today(), -1),
				}
			).insert(ignore_permissions=True)
		else:
			self.batch = frappe.get_doc("Batch", self.batch_name)

		# Add stock entry using this batch
		if not frappe.db.exists("Stock Ledger Entry", {"batch_no": self.batch.name}):
			make_stock_entry(
				item_code=self.item.name,
				qty=5,
				target=warehouse,
				batch_no=self.batch.name,
			)

		result = get_expired_batch_items()

		self.assertIsInstance(result, list)
		self.assertTrue(result, "Expected at least one expired batch item")

		batch_nos = [row.get("batch_no") for row in result]
		self.assertIn(self.batch.name, batch_nos, "Expired batch should be in the result")

	def test_get_expired_batches_TC_SCK_366(self):
		from erpnext.stock.doctype.stock_entry.stock_entry import get_expired_batches

		frappe.set_user("Administrator")

		# Create a unique item with batch enabled
		item_code = "_Test Expired Batch Item " + frappe.generate_hash(length=5)
		if not frappe.db.exists("Item", item_code):
			item = make_item(
				item_code,
				{
					"is_stock_item": 1,
					"has_batch_no": 1,
					"create_new_batch": 1,
					"valuation_rate": 100,
					"stock_uom": "Nos",
				},
			)
		else:
			item = frappe.get_doc("Item", item_code)

		# Create expired batch (expired yesterday)
		expired_batch_name = item_code + "-BATCH-EXPIRED"
		if not frappe.db.exists("Batch", expired_batch_name):
			expired_batch = frappe.get_doc(
				{
					"doctype": "Batch",
					"item": item.name,
					"batch_id": expired_batch_name,
					"expiry_date": add_days(today(), -1),
				}
			).insert(ignore_permissions=True)
		else:
			expired_batch = frappe.get_doc("Batch", expired_batch_name)

		# Create non-expired batch (expires in future)
		valid_batch_name = item_code + "-BATCH-VALID"
		if not frappe.db.exists("Batch", valid_batch_name):
			frappe.get_doc(
				{
					"doctype": "Batch",
					"item": item.name,
					"batch_id": valid_batch_name,
					"expiry_date": add_days(today(), 10),
				}
			).insert(ignore_permissions=True)

		# Fetch expired batches
		expired_batches = get_expired_batches()

		# Assertions
		self.assertIsInstance(expired_batches, dict)
		self.assertIn(expired_batch.name, expired_batches, "Expired batch should be included")
		self.assertNotIn(valid_batch_name, expired_batches, "Non-expired batch should not be included")

	def test_get_warehouse_details_TC_SCK_367(self):
		from frappe.utils import nowdate, nowtime

		from erpnext.stock.doctype.stock_entry.stock_entry import get_warehouse_details

		frappe.set_user("Administrator")
		warehouse = create_warehouse("_Test Warehouse WHD", company="_Test Company")

		# Create a stock item
		item_code = "_Test Item WHD " + frappe.generate_hash(length=5)
		if not frappe.db.exists("Item", item_code):
			item = make_item(item_code, {"is_stock_item": 1, "valuation_rate": 250, "stock_uom": "Nos"})
		else:
			item = frappe.get_doc("Item", item_code)

		# Add stock
		make_stock_entry(item_code=item.name, qty=10, target=warehouse, basic_rate=250)

		# Prepare args
		args = {
			"item_code": item.name,
			"warehouse": warehouse,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
		}

		# Call the function
		result = get_warehouse_details(args)

		# Assertions
		self.assertIsInstance(result, dict)
		self.assertIn("actual_qty", result)
		self.assertIn("basic_rate", result)

		self.assertEqual(result["actual_qty"], 10)
		self.assertEqual(result["basic_rate"], 250)

	def test_get_batchwise_serial_nos_TC_SCK_368(self):
		from erpnext.stock.doctype.stock_entry.stock_entry import get_batchwise_serial_nos

		frappe.set_user("Administrator")
		warehouse = create_warehouse("_Test WH BatchSerial", company="_Test Company")

		# Create serialized + batched item
		item_code = "_Test Item BSN " + frappe.generate_hash(length=5)
		if not frappe.db.exists("Item", item_code):
			item = make_item(
				item_code,
				{
					"has_serial_no": 1,
					"has_batch_no": 1,
					"create_new_batch": 1,
					"serial_no_series": "SN-BSN-.###",
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"valuation_rate": 100,
				},
			)
		else:
			item = frappe.get_doc("Item", item_code)

		# Create Stock Entry to generate Serial No and Batch
		make_stock_entry(
			item_code=item.name,
			qty=3,
			target=warehouse,
			basic_rate=100,
			is_submit=True,
			set_posting_time=True,
			serial_nos=None,  # let system auto-create
		)

		# Get the generated serial numbers and batch
		serial_nos = [
			d.serial_no
			for d in frappe.get_all(
				"Serial No",
				filters={"item_code": item.name},
				fields=["name as serial_no"],
				order_by="creation desc",
				limit=3,
			)
		]

		batch_no = frappe.get_value("Serial No", serial_nos[0], "batch_no")

		row = frappe._dict({"batches_to_be_consume": [batch_no], "serial_nos": serial_nos})
		# Function call
		result = get_batchwise_serial_nos(item.name, row)

		# Assertions
		self.assertIsInstance(result, dict)
		self.assertIn(batch_no, result)
		self.assertEqual(sorted(serial_nos), result[batch_no])

	def test_validate_work_order_status_throws_on_completed_work_order_TC_SCK_395(self):
		frappe.set_user("Administrator")

		# Create Item
		if not frappe.db.exists("Item", "Test WO Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Test WO Item",
					"is_stock_item": 1,
					"stock_uom": "Nos",
					"valuation_rate": 100,
					"gst_hsn_code": "01011010",
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Item", "Test FG Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Test FG Item",
					"is_stock_item": 1,
					"stock_uom": "Nos",
					"valuation_rate": 100,
					"gst_hsn_code": "01011010",
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		# Create BOM
		if not frappe.db.exists("BOM", {"item": "Test WO Item", "is_active": 1}):
			from erpnext.manufacturing.doctype.bom.test_bom import make_bom

			make_bom(
				item="Test WO Item",
				currency="USD",
				quantity=1,
				company="_Test Company",
				raw_materials=[
					{
						"item_code": "Test FG Item",
					}
				],
			)

		# Create Work Order and force status to Completed
		wo = frappe.get_doc(
			{
				"doctype": "Work Order",
				"production_item": "Test WO Item",
				"qty": 1,
				"bom_no": frappe.db.get_value("BOM", {"item": "Test WO Item", "is_active": 1}),
				"fg_warehouse": create_warehouse("WO FG", company="_Test Company"),
				"company": "_Test Company",
			}
		)
		wo.insert(ignore_permissions=True)
		wo.db_set("status", "Completed")

		# Create Stock Entry linked to Completed Work Order
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Manufacture",
				"company": "_Test Company",
				"work_order": wo.name,
				"items": [{"item_code": "Test WO Item", "qty": 1, "t_warehouse": wo.fg_warehouse}],
			}
		)

		# This should raise because WO is Completed
		with self.assertRaises(frappe.ValidationError, msg="Should raise for Completed Work Order"):
			se.validate_work_order_status()

	def test_validate_purpose_with_invalid_purpose_TC_SCK_396(self):
		frappe.set_user("Administrator")

		# Create basic stock entry with invalid purpose
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Invalid Type",
				"purpose": "Invalid Type",
				"company": "_Test Company",
			}
		)

		with self.assertRaises(frappe.ValidationError) as cm:
			se.validate_purpose()

		self.assertIn("Purpose must be one of", str(cm.exception))

	def test_validate_purpose_with_job_card_disallowed_purpose_TC_SCK_397(self):
		frappe.set_user("Administrator")

		# Simulate job card (no need to insert if not validated)
		job_card_name = "TEST-JC-001"

		# Use disallowed purpose with job card
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Issue",
				"purpose": "Material Issue",
				"job_card": job_card_name,
				"company": "_Test Company",
			}
		)

		with self.assertRaises(frappe.ValidationError) as cm:
			se.validate_purpose()

		self.assertIn("For job card", str(cm.exception))

	def test_delete_linked_stock_entry_removes_draft_receive_entry_TC_SCK_398(self):
		frappe.set_user("Administrator")

		item = make_test_item("__Test Stock Entry Item 112233")
		item.valuation_rate = 100
		item.save()
		source_warehouse = create_warehouse("Source WH", company="_Test Company")
		target_warehouse = create_warehouse("Target WH", company="_Test Company")

		# Step 1: Create 'Send to Warehouse' Stock Entry with temporary valid purpose
		se_send = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Issue",
				"purpose": "Material Issue",
				"company": "_Test Company",
				"items": [
					{
						"item_code": item.name,
						"qty": 1,
						"uom": "Nos",
						"s_warehouse": source_warehouse,
					}
				],
			}
		)
		se_send.insert(ignore_permissions=True)

		# Step 2: Create a draft 'Receive at Warehouse' entry linked to the above
		se_receive = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"purpose": "Receive at Warehouse",
				"outgoing_stock_entry": se_send.name,
				"company": "_Test Company",
				"items": [
					{
						"item_code": item.name,
						"qty": 1,
						"uom": "Nos",
						"t_warehouse": target_warehouse,
					}
				],
			}
		)
		se_receive.insert(ignore_permissions=True)
		se_receive.db_set("purpose", "Receive at Warehouse")
		# Confirm the linked entry exists
		self.assertTrue(frappe.db.exists("Stock Entry", se_receive.name))

		# Simulate 'Send to Warehouse' purpose
		se_send.db_set("purpose", "Send to Warehouse")

		# Call method under test
		se_send.delete_linked_stock_entry()

		# Confirm the linked draft entry was deleted
		self.assertFalse(frappe.db.exists("Stock Entry", se_receive.name))

	def test_set_transfer_qty_throws_on_zero_qty_TC_SCK_399(self):
		frappe.set_user("Administrator")

		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Transfer",
				"purpose": "Material Transfer",
				"company": "_Test Company",
				"items": [
					{
						"item_code": "Test Item",
						"qty": 0,  # <- This should trigger the first condition
						"uom": "Nos",
						"conversion_factor": 1,
						"s_warehouse": create_warehouse("ZeroQty WH", {"company": "_Test Company"}),
						"t_warehouse": create_warehouse("Target WH", {"company": "_Test Company"}),
					}
				],
			}
		)

		with self.assertRaises(frappe.ValidationError) as cm:
			se.set_transfer_qty()

		self.assertIn("Qty is mandatory", str(cm.exception))

	def test_set_transfer_qty_throws_on_missing_conversion_factor_TC_SCK_400(self):
		frappe.set_user("Administrator")

		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Transfer",
				"purpose": "Material Transfer",
				"company": "_Test Company",
				"items": [
					{
						"item_code": "Test Item",
						"qty": 2,
						"uom": "Nos",
						"conversion_factor": 0,  # <- This should trigger the second condition
						"s_warehouse": create_warehouse("ZeroQty WH", {"company": "_Test Company"}),
						"t_warehouse": create_warehouse("Target WH", {"company": "_Test Company"}),
					}
				],
			}
		)

		with self.assertRaises(frappe.ValidationError) as cm:
			se.set_transfer_qty()

		self.assertIn("UOM Conversion Factor is mandatory", str(cm.exception))

	def test_create_serial_and_batch_bundle_combined_conditions_TC_SCK_401(self):
		frappe.set_user("Administrator")
		# Setup: Create item with both serial and batch tracking
		item_code = "_Test SerialBatch Item"
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": item_code,
					"item_name": item_code,
					"has_serial_no": 1,
					"has_batch_no": 1,
					"is_stock_item": 1,
					"stock_uom": "Nos",
					"gst_hsn_code": "01011010",
					"item_group": "All Item Groups",
				}
			).insert()
		# Setup: Create warehouse
		warehouse = create_warehouse("_Test WH S+B", company="_Test Company")
		# Create batch
		batch_no = (
			frappe.get_doc({"doctype": "Batch", "item": item_code, "batch_id": "TEST-BATCH-001"})
			.insert()
			.name
		)
		# Create serial nos for that batch
		serial_nos = []
		for i in range(2):
			serial_nos.append(f"SRL-SB-{i}")
			frappe.get_doc(
				{
					"doctype": "Serial No",
					"serial_no": serial_nos[-1],
					"item_code": item_code,
					"batch_no": batch_no,
				}
			).insert()
		# Mock parent_doc and row
		parent_doc = frappe._dict({"posting_date": today(), "posting_time": "10:00:00"})
		row = frappe._dict(
			{
				"warehouse": warehouse,
				"serial_nos": serial_nos.copy(),  # pass both serial and batch
				"batches_to_be_consume": {batch_no: 2},
			}
		)
		child = frappe._dict({"item_code": item_code, "warehouse": warehouse})
		# Call function
		bundle_name = create_serial_and_batch_bundle(parent_doc, row, child)
		self.assertTrue(bundle_name)
		bundle = frappe.get_doc("Serial and Batch Bundle", bundle_name)
		# Validate both serials and batch are captured
		self.assertEqual(bundle.has_serial_no, 1)
		self.assertEqual(bundle.has_batch_no, 1)
		self.assertEqual(len(bundle.entries), 2)

	def test_create_serial_bundle_only_serials_TC_SCK_402(self):
		frappe.set_user("Administrator")

		# Step 1: Setup Item with Serial No
		item_code = "_Test Serial Item"
		if not frappe.db.exists("Item", item_code):
			item = frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": item_code,
					"item_name": item_code,
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"has_serial_no": 1,
					"gst_hsn_code": "01011010",
					"serial_no_series": "SRL-TEST-.#####",
					"item_group": "All Item Groups",
				}
			)
			item.insert()

		# Step 2: Create Stock Entry to auto-generate Serial No
		warehouse = create_warehouse("_Test Serial WH", company="_Test Company")
		se = make_stock_entry(
			item_code=item_code, qty=1, target=warehouse, basic_rate=100, stock_entry_type="Material Receipt"
		)

		serial_no = frappe.get_value("Serial No", {"item_code": item_code}, "name")
		self.assertIsNotNone(serial_no)

		# Step 3: Prepare dummy parent_doc and row to simulate stock entry context

		parent_doc = frappe._dict({"posting_date": se.posting_date, "posting_time": se.posting_time})

		row = frappe._dict({"serial_nos": [serial_no], "warehouse": warehouse})

		child = frappe._dict({"item_code": item_code})

		# Step 4: Call the function and verify
		bundle_name = create_serial_and_batch_bundle(parent_doc, row, child)
		self.assertTrue(bundle_name)

		bundle_doc = frappe.get_doc("Serial and Batch Bundle", bundle_name)
		self.assertEqual(bundle_doc.has_serial_no, 1)
		self.assertEqual(len(bundle_doc.entries), 1)
		self.assertEqual(bundle_doc.entries[0].serial_no, serial_no)

	def test_get_items_from_subcontract_order_TC_SCK_403(self):
		frappe.set_user("Administrator")

		# Create required warehouses
		default_wh = create_warehouse("_Test Warehouse", company="_Test Company")
		subcontract_wh = create_warehouse("_Test Subcontract WH", company="_Test Company")

		# Now create it fresh with correct attributes
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "Subcontracted FG",
				"item_name": "Subcontracted FG",
				"is_stock_item": 0,
				"is_sub_contracted_item": 1,
				"stock_uom": "Nos",
				"default_warehouse": default_wh,
				"gst_hsn_code": "01011010",
				"include_item_in_manufacturing": 1,
				"item_group": "All Item Groups",
			}
		).insert(ignore_permissions=True)

		# Create the raw material item manually
		if not frappe.db.exists("Item", "Sub Raw Bom Mat"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Sub Raw Bom Mat",
					"item_name": "Sub Raw Bom Mat",
					"is_stock_item": 1,
					"is_sub_contracted_item": 1,
					"stock_uom": "Nos",
					"default_warehouse": default_wh,
					"gst_hsn_code": "01011010",
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		# Create the raw material item manually
		if not frappe.db.exists("Item", "_Test Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "_Test Item",
					"item_name": "_Test Item",
					"is_stock_item": 1,
					"gst_hsn_code": "01011010",
					"valuation_rate": 100,
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		# Create the raw material item manually
		if not frappe.db.exists("Item", "Sub Raw Mat"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Sub Raw Mat",
					"item_name": "Sub Raw Mat",
					"is_stock_item": 1,
					"stock_uom": "Nos",
					"default_warehouse": default_wh,
					"gst_hsn_code": "01011010",
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("BOM", {"item": "Sub Raw Bom Mat", "is_active": 1}):
			bom = frappe.get_doc(
				{
					"doctype": "BOM",
					"item": "Sub Raw Bom Mat",
					"company": "_Test Company",
					"is_active": 1,
					"is_default": 1,
					"quantity": 1,
					"items": [{"item_code": "Sub Raw Mat", "qty": 2}],
				}
			).insert()
			bom.submit()
		if not frappe.db.exists("Supplier", "_Test Supplier"):
			frappe.get_doc(
				{"doctype": "Supplier", "supplier_name": "_Test Supplier", "supplier_type": "Company"}
			).insert()

		# Create a Purchase Order to be used for Subcontracting Order
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": "_Test Supplier",
				"company": "_Test Company",
				"schedule_date": frappe.utils.nowdate(),
				"is_subcontracted": 1,
				"subcontracting_type": "Raw Material Supplied",
				"supplier_warehouse": subcontract_wh,
				"items": [
					{
						"fg_item": "Sub Raw Bom Mat",
						"item_code": "Subcontracted FG",
						"qty": 5,
						"rate": 100,
						"warehouse": default_wh,
						"is_finished_item": 1,
					}
				],
				"supplied_items": [
					{
						"main_item_code": "Subcontracted FG",
						"rm_item_code": "Sub Raw Mat",
						"required_qty": 10,
						"warehouse": default_wh,
					}
				],
			}
		).insert()
		po.submit()

		# Create Subcontracting Order
		from erpnext.subcontracting.doctype.subcontracting_order.test_subcontracting_order import (
			create_subcontracting_order,
		)

		sco = create_subcontracting_order(po_name=po.name, supplier_warehouse=subcontract_wh)

		# Create target_doc (empty Stock Entry)
		stock_entry = make_stock_entry(
			item_code="_Test Item",
			qty=1,
			source=default_wh,
			target=default_wh,
			purpose="Material Transfer",
			company="_Test Company",
			purchase_order=po.name,
		)

		stock_entry_json = frappe.as_json(stock_entry)

		# Call the function under test
		result_doc = get_items_from_subcontract_order(sco.name, stock_entry_json)

		# Assertions
		self.assertEqual(result_doc.doctype, "Stock Entry")
		self.assertGreater(len(result_doc.items), 0)
		self.assertEqual(result_doc.items[0].item_code, "Sub Raw Mat")

	def test_get_valuation_rate_for_finished_good_entry_TC_SCK_408(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)

		fg_warehouse = create_warehouse("_Test FG WH", company="_Test Company")
		wip_warehouse = create_warehouse("_Test WIP WH", company="_Test Company")
		test_warehouse = create_warehouse("_Test Warehouse", company="_Test Company")

		if not frappe.db.exists("Item", "Sub Raw Mat"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Sub Raw Mat",
					"item_name": "Sub Raw Mat",
					"is_stock_item": 1,
					"stock_uom": "Nos",
					"default_warehouse": "_Test Warehouse - _TC",
					"gst_hsn_code": "01011010",
					"item_group": "All Item Groups",
					"valuation_rate": 100,
				}
			).insert(ignore_permissions=True)

		# Then pass it into create_item
		if not frappe.db.exists("Item", "Valuation FG"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Valuation FG",
					"item_name": "Valuation FG",
					"is_stock_item": 1,
					"stock_uom": "Nos",
					"default_warehouse": "_Test Warehouse - _TC",
					"gst_hsn_code": "01011010",
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		# Create a Material Receipt to stock 'Sub Raw Mat' in the source warehouse
		frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"purpose": "Material Receipt",
				"company": "_Test Company",
				"items": [
					{
						"item_code": "Sub Raw Mat",
						"t_warehouse": test_warehouse,
						"qty": 5,
						"uom": "Nos",
						"stock_uom": "Nos",
						"conversion_factor": 1.0,
						"rate": 100,
					}
				],
				"docstatus": 1,
			}
		).insert()

		if not frappe.db.exists("BOM", {"item": "Valuation FG", "is_active": 1}):
			bom = frappe.get_doc(
				{
					"doctype": "BOM",
					"item": "Valuation FG",
					"quantity": 1,
					"is_active": 1,
					"is_default": 1,
					"company": "_Test Company",
					"items": [
						{
							"item_code": "Sub Raw Mat",  # or any raw material
							"qty": 2,
						}
					],
				}
			).insert()
		else:
			bom = frappe.get_doc("BOM", {"item": "Valuation FG", "is_active": 1})

		work_order = frappe.get_doc(
			{
				"doctype": "Work Order",
				"production_item": "Valuation FG",
				"qty": 10,
				"material_transferred_for_manufacturing": 5,
				"fg_warehouse": fg_warehouse,
				"wip_warehouse": wip_warehouse,
				"bom_no": bom.name,
				"stock_uom": "Nos",
				"company": "_Test Company",
			}
		).insert()

		work_order.submit()
		# Create Stock Entry for the Work Order
		frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"purpose": "Material Transfer for Manufacture",
				"stock_entry_type": "Material Transfer for Manufacture",
				"work_order": work_order.name,
				"company": "_Test Company",
				"items": [
					{
						"item_code": "Sub Raw Mat",
						"s_warehouse": test_warehouse,  # your source warehouse
						"t_warehouse": wip_warehouse,  # transfer to WIP
						"qty": 5,
						"uom": "Nos",
						"stock_uom": "Nos",
						"conversion_factor": 1,
						"rate": 100,
						"Allow Zero Valuation Rate": 1,
					}
				],
				"total_outgoing_value": 500,
				"docstatus": 1,
			}
		).insert()

		# Function under test
		from erpnext.stock.doctype.stock_entry.stock_entry import get_valuation_rate_for_finished_good_entry

		valuation_rate = get_valuation_rate_for_finished_good_entry(work_order.name)

		# Assertion: 500 (value) / 5 (qty) = 100
		self.assertEqual(valuation_rate, 100)

	def test_set_items_for_stock_in_TC_SCK_409(self):
		frappe.set_user("Administrator")

		# Step 1: Create source and target warehouses
		source_warehouse = create_warehouse("_Test Source WH", company="_Test Company")
		target_warehouse = create_warehouse("_Test Target WH", company="_Test Company")

		# Step 2: Create item
		item_code = "Test Stock Transfer Item"
		make_item(item_code, {"is_stock_item": 1, "valuation_rate": 100})

		# Step 2.5: Add stock to source warehouse
		frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": "_Test Company",
				"items": [
					{
						"item_code": item_code,
						"t_warehouse": source_warehouse,
						"qty": 10,
						"uom": "Nos",
						"stock_uom": "Nos",
						"conversion_factor": 1.0,
						"rate": 100,
					}
				],
			}
		).insert().submit()

		# Step 3: Create outgoing stock entry (Material Transfer)
		outgoing_entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Transfer",
				"purpose": "Material Transfer",
				"company": "_Test Company",
				"items": [
					{
						"item_code": item_code,
						"s_warehouse": source_warehouse,
						"t_warehouse": target_warehouse,
						"qty": 5,
						"uom": "Nos",
						"stock_uom": "Nos",
						"conversion_factor": 1.0,
					}
				],
				"docstatus": 1,
			}
		).insert()

		# Step 4: Create new incoming stock entry to simulate receipt
		incoming_entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"purpose": "Material Transfer",
				"stock_entry_type": "Material Transfer",
				"company": "_Test Company",
				"outgoing_stock_entry": outgoing_entry.name,
			}
		)

		# Step 5: Call method under test
		incoming_entry.set_items_for_stock_in()

		# Step 6: Assertions
		self.assertEqual(len(incoming_entry.items), 1)
		item = incoming_entry.items[0]
		self.assertEqual(item.item_code, item_code)
		self.assertEqual(item.s_warehouse, target_warehouse)
		self.assertEqual(item.against_stock_entry, outgoing_entry.name)
		self.assertEqual(item.qty, 5)

	def test_make_serial_and_batch_bundle_for_transfer_TC_SCK_410(self):
		frappe.set_user("Administrator")

		# Create warehouses
		source_wh = create_warehouse("_Test Source WH", company="_Test Company")
		target_wh = create_warehouse("_Test Target WH", company="_Test Company")

		# Create item
		item_code = "Batch Transfer Item"
		make_item(item_code, {"is_stock_item": 1, "has_batch_no": 1, "valuation_rate": 100})

		if not frappe.db.exists("Batch", "TEST-BATCH-001"):
			frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": "TEST-BATCH-001",
					"item": item_code,
					"warehouse": source_wh,
					"expiry_date": add_days(nowdate(), 365),
				}
			).insert()

		frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"purpose": "Material Receipt",
				"company": "_Test Company",
				"items": [
					{
						"item_code": item_code,
						"t_warehouse": source_wh,
						"qty": 5,
						"uom": "Nos",
						"stock_uom": "Nos",
						"conversion_factor": 1.0,
						"rate": 100,
						"batch_no": "TEST-BATCH-001",
					}
				],
				"docstatus": 1,
			}
		).insert()

		outgoing_entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"purpose": "Material Transfer",
				"stock_entry_type": "Material Transfer",
				"company": "_Test Company",
				"items": [
					{
						"item_code": item_code,
						"s_warehouse": source_wh,
						"t_warehouse": target_wh,
						"qty": 5,
						"uom": "Nos",
						"stock_uom": "Nos",
						"conversion_factor": 1.0,
						"batch_no": "TEST-BATCH-001",
					}
				],
				"docstatus": 1,
			}
		).insert()

		frappe.get_doc(
			{
				"doctype": "Serial and Batch Bundle",
				"item_code": item_code,
				"package_type": "Batch",
				"type_of_transaction": "Outward",
				"voucher_type": "Stock Entry",
				"voucher_no": outgoing_entry.name,
				"entries": [{"batch_no": "TEST-BATCH-001", "qty": 5}],
			}
		).insert()

		ste_detail_name = outgoing_entry.items[0].name

		# Create receiving Stock Entry referencing outgoing entry
		receiving_entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"purpose": "Material Transfer",
				"stock_entry_type": "Material Transfer",
				"company": "_Test Company",
				"outgoing_stock_entry": outgoing_entry.name,
				"items": [
					{
						"item_code": item_code,
						"s_warehouse": target_wh,
						"t_warehouse": source_wh,
						"qty": 5,
						"uom": "Nos",
						"stock_uom": "Nos",
						"conversion_factor": 1.0,
						"ste_detail": ste_detail_name,
					}
				],
			}
		)

		# Mock make_package_for_transfer to return new bundle name
		def mock_make_package(bundle, wh, direction, do_not_submit):
			return "NEW-SBB-001"

		receiving_entry.make_package_for_transfer = mock_make_package

		# Call function under test
		receiving_entry.make_serial_and_batch_bundle_for_transfer()

		# Assert that new bundle was assigned to item
		self.assertEqual(receiving_entry.items[0].serial_and_batch_bundle, "NEW-SBB-001")


def create_bom(bom_item, rm_items, company=None, qty=None, properties=None):
	bom = frappe.new_doc("BOM")
	bom.update(
		{
			"item": bom_item or "_Test Item",
			"company": company or "_Test Company",
			"quantity": qty or 1,
		}
	)
	if properties:
		bom.update(properties)

	for item in rm_items:
		item_args = {}

		item_args.update(
			{
				"item_code": item.get("item_code"),
				"qty": item.get("qty"),
				"uom": item.get("uom"),
				"rate": item.get("rate"),
			}
		)

		bom.append("items", item_args)

	bom.save(ignore_permissions=True)
	bom.submit()

	return bom


def make_serialized_item(**args):
	args = frappe._dict(args)
	se = frappe.copy_doc(test_records[0])

	if args.company:
		se.company = args.company

	if args.target_warehouse:
		se.get("items")[0].t_warehouse = args.target_warehouse

	se.get("items")[0].item_code = args.item_code or "_Test Serialized Item With Series"

	if args.serial_no:
		serial_nos = args.serial_no
		if isinstance(serial_nos, str):
			serial_nos = [serial_nos]

		se.get("items")[0].serial_and_batch_bundle = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": se.get("items")[0].item_code,
					"warehouse": se.get("items")[0].t_warehouse,
					"company": se.company,
					"qty": 2,
					"voucher_type": "Stock Entry",
					"serial_nos": serial_nos,
					"posting_date": today(),
					"posting_time": nowtime(),
					"do_not_submit": True,
				}
			)
		).name

	if args.cost_center:
		se.get("items")[0].cost_center = args.cost_center

	if args.expense_account:
		se.get("items")[0].expense_account = args.expense_account

	se.get("items")[0].qty = 2
	se.get("items")[0].transfer_qty = 2

	se.set_stock_entry_type()
	se.insert()
	se.submit()

	se.load_from_db()
	return se


def get_qty_after_transaction(**args):
	args = frappe._dict(args)
	last_sle = get_previous_sle(
		{
			"item_code": args.item_code or "_Test Item",
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"posting_date": args.posting_date or nowdate(),
			"posting_time": args.posting_time or nowtime(),
		}
	)
	return flt(last_sle.get("qty_after_transaction"))


def get_multiple_items():
	return [
		{
			"conversion_factor": 1.0,
			"cost_center": "Main - TCP1",
			"doctype": "Stock Entry Detail",
			"expense_account": "Stock Adjustment - TCP1",
			"basic_rate": 100,
			"item_code": "_Test Item",
			"qty": 50.0,
			"s_warehouse": "Stores - TCP1",
			"stock_uom": "_Test UOM",
			"transfer_qty": 50.0,
			"uom": "_Test UOM",
		},
		{
			"conversion_factor": 1.0,
			"cost_center": "Main - TCP1",
			"doctype": "Stock Entry Detail",
			"expense_account": "Stock Adjustment - TCP1",
			"basic_rate": 5000,
			"item_code": "_Test Item Home Desktop 100",
			"qty": 1,
			"stock_uom": "_Test UOM",
			"t_warehouse": "Stores - TCP1",
			"transfer_qty": 1,
			"uom": "_Test UOM",
		},
	]


test_records = frappe.get_test_records("Stock Entry")


def initialize_records_for_future_negative_sle_test(
	item_code, batch_no, warehouses, opening_qty, posting_date
):
	from erpnext.stock.doctype.batch.test_batch import TestBatch, make_new_batch
	from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
		create_stock_reconciliation,
	)
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	TestBatch.make_batch_item(item_code)
	make_new_batch(item_code=item_code, batch_id=batch_no)
	warehouse_names = [create_warehouse(w) for w in warehouses]
	create_stock_reconciliation(
		purpose="Opening Stock",
		posting_date=posting_date,
		posting_time="20:00:20",
		item_code=item_code,
		warehouse=warehouse_names[0],
		valuation_rate=100,
		qty=opening_qty,
		batch_no=batch_no,
	)
	return warehouse_names


def create_stock_entries(sequence_of_entries):
	for entry_detail in sequence_of_entries:
		make_stock_entry(**entry_detail)


def create_company(company):
	if not frappe.db.exists("Company", company):
		company = frappe.new_doc("Company")
		company.company_name = company
		company.default_currency = "INR"
		company.insert()


def generate_serial_nos(item_code, qty):
	"""Generate and insert serial numbers for an item."""
	serial_nos = []
	for _ in range(qty):
		serial_no = f"SNO-{frappe.generate_hash(length=8)}"
		serial_nos.append(serial_no)

		# Create Serial No record
		frappe.get_doc(
			{
				"doctype": "Serial No",
				"serial_no": serial_no,
				"item_code": item_code,
				"company": "_Test Company",
				"status": "Active",
			}
		).insert(ignore_permissions=True)

	return serial_nos


def create_company_se():
	company_name = "_Test Company SE"
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


def custom_create_serial_and_batch_bundle():
	# Create Item Group if needed
	if not frappe.db.exists("Item Group", "Test Group"):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": "Test Group", "is_group": 0}).insert()

	# Create Item with batch enabled
	if not frappe.db.exists("Item", "_Test Item"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_Test Item",
				"item_name": "Test Item",
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"stock_uom": "Nos",
				"item_group": "Test Group",
			}
		).insert()

	# Create Batch
	batch = frappe.get_doc({"doctype": "Batch", "item": "_Test Item", "batch_id": "BATCH-001"}).insert()

	# Create Serial and Batch Bundle
	sbb = frappe.get_doc(
		{
			"doctype": "Serial and Batch Bundle",
			"type_of_transaction": "Inward",
			"voucher_type": "Stock Entry",
			"item_code": "_Test Item",
			"entries": [{"batch_no": batch.name, "qty": 5, "uom": "Nos"}],
		}
	)
	sbb.insert()
	return sbb.name


def setup_defaults_data():
	from erpnext.accounts.doctype.account.test_account import create_account
	from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
	from erpnext.stock import get_warehouse_account_map

	create_company()
	acc = create_account(
		account_name="Stock Assets",
		account_type="Stock",
		company="_Test Company",
		is_group=1,
		parent_account="Current Assets - _TC",
		account_currency="INR",
		do_not_save=True,
	)
	acc.report_type = "Balance Sheet"
	acc.root_type = "Asset"
	acc.save()
	company_doc = frappe.get_doc("Company", "_Test Company")
	frappe._set_document_in_cache("Company", company_doc)
	get_warehouse_account_map(company=company_doc.name)
