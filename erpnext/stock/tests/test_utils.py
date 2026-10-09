import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, nowtime

from erpnext.stock.dashboard.warehouse_capacity_dashboard import get_data
from erpnext.stock.doctype.putaway_rule.putaway_rule import (
	apply_putaway_rule,
	get_available_putaway_capacity,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_items, get_stock_balance_for
from erpnext.stock.utils import _get_stock_balance, get_stock_balance, scan_barcode
from erpnext.tests.permission_test_utils import (
	as_user,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	make_fenced_user,
)

WAREHOUSE = "Stores - _TC"
OTHER_WAREHOUSE = "Finished Goods - _TC"


class StockTestMixin:
	"""Mixin to simplfy stock ledger tests, useful for all stock transactions."""

	def make_item(self, item_code=None, properties=None, *args, **kwargs):
		from erpnext.stock.doctype.item.test_item import make_item

		return make_item(item_code, properties, *args, **kwargs)

	def assertSLEs(self, doc, expected_sles, sle_filters=None):
		"""Compare sorted SLEs, useful for vouchers that create multiple SLEs for same line"""

		filters = {"voucher_no": doc.name, "voucher_type": doc.doctype, "is_cancelled": 0}
		if sle_filters:
			filters.update(sle_filters)
		sles = frappe.get_all(
			"Stock Ledger Entry",
			fields=["*"],
			filters=filters,
			order_by="timestamp(posting_date, posting_time), creation",
		)
		self.assertGreaterEqual(len(sles), len(expected_sles))

		for exp_sle, act_sle in zip(expected_sles, sles, strict=False):
			for k, v in exp_sle.items():
				act_value = act_sle[k]
				if k == "stock_queue":
					act_value = json.loads(act_value)
					if act_value and act_value[0][0] == 0:
						# ignore empty fifo bins
						continue

				self.assertEqual(v, act_value, msg=f"{k} doesn't match \n{exp_sle}\n{act_sle}")

	def assertGLEs(self, doc, expected_gles, gle_filters=None, order_by=None):
		filters = {"voucher_no": doc.name, "voucher_type": doc.doctype, "is_cancelled": 0}

		if gle_filters:
			filters.update(gle_filters)
		actual_gles = frappe.get_all(
			"GL Entry",
			fields=["*"],
			filters=filters,
			order_by=order_by or "posting_date, creation",
		)
		self.assertGreaterEqual(len(actual_gles), len(expected_gles))
		for exp_gle, act_gle in zip(expected_gles, actual_gles, strict=False):
			for k, exp_value in exp_gle.items():
				act_value = act_gle[k]
				self.assertEqual(exp_value, act_value, msg=f"{k} doesn't match \n{exp_gle}\n{act_gle}")


class TestStockUtilities(FrappeTestCase, StockTestMixin):
	def test_barcode_scanning(self):
		simple_item = self.make_item(properties={"barcodes": [{"barcode": "12399"}]})
		self.assertEqual(scan_barcode("12399")["item_code"], simple_item.name)

		batch_item = self.make_item(properties={"has_batch_no": 1, "create_new_batch": 1})
		batch = frappe.get_doc(doctype="Batch", item=batch_item.name).insert()

		batch_scan = scan_barcode(batch.name)
		self.assertEqual(batch_scan["item_code"], batch_item.name)
		self.assertEqual(batch_scan["batch_no"], batch.name)
		self.assertEqual(batch_scan["has_batch_no"], 1)
		self.assertEqual(batch_scan["has_serial_no"], 0)

		serial_item = self.make_item(properties={"has_serial_no": 1})
		serial = frappe.get_doc(
			doctype="Serial No", item_code=serial_item.name, serial_no=frappe.generate_hash()
		).insert()

		serial_scan = scan_barcode(serial.name)
		self.assertEqual(serial_scan["item_code"], serial_item.name)
		self.assertEqual(serial_scan["serial_no"], serial.name)
		self.assertEqual(serial_scan["has_batch_no"], 0)
		self.assertEqual(serial_scan["has_serial_no"], 1)

	def test_barcode_scanning_of_warehouse(self):
		warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Test Warehouse for Barcode",
				"company": "_Test Company",
			}
		).insert()

		warehouse_2 = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Test Warehouse for Barcode 2",
				"company": "_Test Company",
			}
		).insert()

		warehouse_scan = scan_barcode(warehouse.name)
		self.assertEqual(warehouse_scan["warehouse"], warehouse.name)

		item_with_warehouse = self.make_item(
			properties={
				"item_defaults": [{"company": "_Test Company", "default_warehouse": warehouse.name}],
				"barcodes": [{"barcode": "w12345"}],
			}
		)

		item_scan = scan_barcode("w12345")
		self.assertEqual(item_scan["item_code"], item_with_warehouse.name)
		self.assertEqual(item_scan.get("default_warehouse"), None)

		ctx = {"company": "_Test Company"}
		item_scan_with_ctx = scan_barcode("w12345", ctx=ctx)
		self.assertEqual(item_scan_with_ctx["item_code"], item_with_warehouse.name)
		self.assertEqual(item_scan_with_ctx["default_warehouse"], warehouse.name)

		ctx = {"company": "_Test Company", "set_warehouse": warehouse_2.name}
		item_scan_with_ctx = scan_barcode("w12345", ctx=ctx)
		self.assertEqual(item_scan_with_ctx["item_code"], item_with_warehouse.name)
		self.assertEqual(item_scan_with_ctx["default_warehouse"], warehouse_2.name)


class TestStockBalancePermissions(FrappeTestCase, StockTestMixin):
	def setUp(self):
		self.item = self.make_item().name
		self.other_item = self.make_item().name
		make_stock_entry(item_code=self.item, to_warehouse=WAREHOUSE, qty=7, rate=123.17)
		make_stock_entry(item_code=self.item, to_warehouse=OTHER_WAREHOUSE, qty=3, rate=50.31)
		make_stock_entry(item_code=self.other_item, to_warehouse=OTHER_WAREHOUSE, qty=2, rate=40.73)

	def user(self, role, user_permissions=None):
		email = f"test_stock_balance_{frappe.scrub(role)}@example.com"
		return make_fenced_user(email, [role], user_permissions)

	def balance(self, warehouse, item=None):
		return get_stock_balance(item or self.item, warehouse, with_valuation_rate=True)

	def warehouse_kwargs(self, name):
		return {"item_code": self.item, "warehouse": name}

	def rows(self, item):
		return [
			{
				"doctype": "Stock Entry Detail",
				"item_code": item,
				"qty": 2,
				"transfer_qty": 2,
				"uom": "_Test UOM",
				"t_warehouse": OTHER_WAREHOUSE,
			}
		]

	def make_putaway_rule(self):
		rule = frappe.get_doc(
			{
				"doctype": "Putaway Rule",
				"company": "_Test Company",
				"item_code": self.item,
				"warehouse": WAREHOUSE,
				"capacity": 10,
				"stock_capacity": 10,
				"uom": frappe.db.get_value("Item", self.item, "stock_uom"),
				"conversion_factor": 1,
			}
		)
		return rule.insert().name

	def test_get_stock_balance_applies_user_permissions(self):
		with as_user(self.user("Stock User", [("Warehouse", OTHER_WAREHOUSE)])):
			assert_refused_without(self, [123.17], self.balance, WAREHOUSE)
			self.assertEqual(self.balance(OTHER_WAREHOUSE), (3.0, 50.31))
			internal = _get_stock_balance(self.item, WAREHOUSE, with_valuation_rate=True)
			self.assertEqual(internal, (7.0, 123.17))

		with as_user(self.user("Stock User", [("Item", self.item)])):
			assert_refused_without(self, [40.73], self.balance, OTHER_WAREHOUSE, self.other_item)
			self.assertEqual(self.balance(OTHER_WAREHOUSE), (3.0, 50.31))

		with as_user(self.user("Stock User", [("Company", "_Test Company 1")])):
			assert_refused_without(self, [123.17], self.balance, WAREHOUSE)

		with as_user(self.user("Stock User")):
			assert_refused(self, get_stock_balance, self.item, None)
			assert_refused(self, get_stock_balance, self.item, "")
			assert_refused_for_names(self, get_stock_balance, self.warehouse_kwargs, [], type_gated=True)
			self.assertEqual(self.balance(WAREHOUSE), (7.0, 123.17))

		with as_user(self.user("Stock Manager")):
			self.assertEqual(self.balance(WAREHOUSE), (7.0, 123.17))

		with as_user(self.user("Desk User")):
			self.assertRaises(frappe.PermissionError, _get_stock_balance, self.item, WAREHOUSE)

	def test_stock_balance_callers_require_item_read(self):
		rule = self.make_putaway_rule()
		args = (WAREHOUSE, nowdate(), nowtime(), "_Test Company", self.item)
		batch_item = self.make_item(
			properties={"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "TSBP-.#####"}
		).name
		make_stock_entry(item_code=batch_item, to_warehouse=WAREHOUSE, qty=4, rate=61.29)

		with as_user(self.user("Desk User")):
			self.assertRaises(frappe.PermissionError, get_items, *args)
			self.assertRaises(frappe.PermissionError, get_available_putaway_capacity, rule)
			self.assertRaises(frappe.PermissionError, get_data, item_code=self.item)
			has_permission = frappe.has_permission
			with patch.object(
				frappe,
				"has_permission",
				lambda doctype, *a, **kw: doctype in ("Stock Reconciliation", "Warehouse")
				or has_permission(doctype, *a, **kw),
			):
				self.assertRaises(
					frappe.PermissionError, get_stock_balance_for, self.item, WAREHOUSE, *args[1:3]
				)
				self.assertRaises(frappe.PermissionError, get_items, *args[:4], batch_item)

		with as_user(self.user("Stock User")):
			self.assertRaises(frappe.PermissionError, get_items, *args)
			self.assertEqual(get_available_putaway_capacity(rule), 3)
			self.assertEqual(get_data(item_code=self.item)[0]["actual_qty"], 7)

		with as_user(self.user("Stock User", [("Warehouse", OTHER_WAREHOUSE)])):
			self.assertRaises(frappe.PermissionError, get_available_putaway_capacity, rule)

		with as_user(self.user("Stock Manager", [("Warehouse", OTHER_WAREHOUSE)])):
			self.assertRaises(frappe.PermissionError, get_items, *args)
			self.assertEqual(get_items(OTHER_WAREHOUSE, *args[1:])[0]["qty"], 3)

		with as_user(self.user("Stock Manager", [("Warehouse", "All Warehouses - _TC", 1)])):
			self.assertRaises(frappe.PermissionError, get_items, "All Warehouses - _TC", *args[1:])

		with as_user(self.user("Stock Manager")):
			self.assertEqual(get_items(*args)[0]["qty"], 7)

	def test_apply_putaway_rule_requires_form_write(self):
		rule = self.make_putaway_rule()

		with as_user(self.user("Manufacturing Manager")):
			self.assertIsNone(
				apply_putaway_rule(
					"Stock Entry", self.rows(self.item), "_Test Company", "1", "Material Receipt"
				)
			)

		with as_user(self.user("Stock User")):
			allocated = apply_putaway_rule(
				"Stock Entry", self.rows(self.item), "_Test Company", "1", "Material Receipt"
			)
			unallocated = apply_putaway_rule(
				"Stock Entry", self.rows(self.other_item), "_Test Company", "1", "Material Receipt"
			)

		self.assertEqual(allocated[0]["putaway_rule"], rule)
		self.assertEqual(allocated[0]["t_warehouse"], WAREHOUSE)
		self.assertFalse(unallocated[0].get("putaway_rule"))
		self.assertEqual(unallocated[0]["t_warehouse"], OTHER_WAREHOUSE)

		for role, doctypes in (
			("Desk User", ("Stock Entry", "Purchase Receipt")),
			("Delivery User", ("Stock Entry", "Purchase Receipt")),
			("Quality Manager", ("Stock Entry", "Purchase Receipt")),
			("Accounts User", ("Purchase Receipt",)),
		):
			with as_user(self.user(role)):
				for doctype in doctypes:
					self.assertRaises(
						frappe.PermissionError,
						apply_putaway_rule,
						doctype,
						self.rows(self.item),
						"_Test Company",
						"1",
					)

		with as_user(self.user("Stock Manager")):
			for doctype in ("Item", "Stock Reconciliation"):
				assert_refused(self, apply_putaway_rule, doctype, self.rows(self.item), "_Test Company", "1")

		with as_user(self.user("Stock User", [("Company", "_Test Company 1")])):
			assert_refused(
				self, apply_putaway_rule, "Stock Entry", self.rows(self.item), "_Test Company", "1"
			)

		frappe.db.set_value("Company", "_Test Company", "default_in_transit_warehouse", WAREHOUSE)
		with as_user(self.user("Stock User", [("Warehouse", OTHER_WAREHOUSE)])):
			fenced = apply_putaway_rule(
				"Stock Entry", self.rows(self.item), "_Test Company", "1", "Material Receipt"
			)

		self.assertEqual(fenced[0]["putaway_rule"], rule)

	def test_manufacturing_manager_saves_stock_entry_without_putaway_rules(self):
		row = {"item_code": self.item, "t_warehouse": WAREHOUSE, "qty": 1, "basic_rate": 100}
		entry = {
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": "_Test Company",
			"apply_putaway_rule": 1,
			"items": [row],
		}

		with as_user(self.user("Manufacturing Manager")):
			saved = frappe.get_doc(entry).insert()

		self.assertEqual(saved.items[0].t_warehouse, WAREHOUSE)

		self.make_putaway_rule()
		row.update({"qty": 5, "transfer_qty": 5, "conversion_factor": 1})
		frappe.local.message_log = []
		with as_user(self.user("Manufacturing Manager")):
			self.assertRaises(frappe.PermissionError, frappe.get_doc(entry).insert)

		self.assertNotIn("Unassigned", str(frappe.local.message_log))

		row.update({"qty": 2, "transfer_qty": 2})
		with as_user(self.user("Manufacturing User")):
			saved = frappe.get_doc(entry).insert()

		self.assertEqual(saved.items[0].t_warehouse, WAREHOUSE)
