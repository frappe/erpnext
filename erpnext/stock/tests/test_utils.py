import json
from unittest.mock import patch

import frappe
from frappe.query_builder.functions import CombineDatetime
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
from erpnext.tests.utils import ERPNextTestSuite

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

		sle = frappe.qb.DocType("Stock Ledger Entry")
		query = (
			frappe.qb.from_(sle)
			.select("*")
			.where(sle.voucher_no == doc.name)
			.where(sle.voucher_type == doc.doctype)
			.where(sle.is_cancelled == 0)
		)
		if sle_filters:
			for key, value in sle_filters.items():
				query = query.where(sle[key] == value)

		sles = (
			query.orderby(CombineDatetime(sle.posting_date, sle.posting_time))
			.orderby(sle.creation)
			.run(as_dict=True)
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


class TestStockUtilities(ERPNextTestSuite, StockTestMixin):
	def test_barcode_scanning(self):
		simple_item = self.make_item(properties={"barcodes": [{"barcode": "12399"}]})
		self.assertEqual(scan_barcode("12399")["item_code"], simple_item.name)

		batch_item = self.make_item(properties={"has_batch_no": 1, "create_new_batch": 1})
		batch = frappe.get_doc(doctype="Batch", item=batch_item.name).insert()

		batch_scan = scan_barcode(batch.batch_id)
		self.assertEqual(batch_scan["item_code"], batch_item.name)
		self.assertEqual(batch_scan["batch_no"], batch.name)
		self.assertEqual(batch_scan["has_batch_no"], 1)
		self.assertEqual(batch_scan["has_serial_no"], 0)

		serial_item = self.make_item(properties={"has_serial_no": 1})
		serial = frappe.get_doc(
			doctype="Serial No",
			item_code=serial_item.name,
			serial_no=frappe.generate_hash(),
			company="_Test Company",
		).insert()

		serial_scan = scan_barcode(serial.serial_no)
		self.assertEqual(serial_scan["item_code"], serial_item.name)
		self.assertEqual(serial_scan["serial_no"], serial.serial_no)
		self.assertEqual(serial_scan["serial_no_id"], serial.name)
		self.assertEqual(serial_scan["has_batch_no"], 0)
		self.assertEqual(serial_scan["has_serial_no"], 1)

	def test_shared_serial_scan_returns_candidates_and_respects_item(self):
		first = self.make_item(properties={"has_serial_no": 1})
		second = self.make_item(properties={"has_serial_no": 1})
		number = f"Scan-{frappe.generate_hash()}"
		first_serial = frappe.get_doc(
			doctype="Serial No", item_code=first.name, serial_no=number, company="_Test Company"
		).insert()
		self.assertEqual(scan_barcode(number)["serial_no_id"], first_serial.name)
		second_serial = frappe.get_doc(
			doctype="Serial No", item_code=second.name, serial_no=number, company="_Test Company"
		).insert()

		candidates = scan_barcode(number.lower())["candidates"]
		self.assertEqual({row["item_code"] for row in candidates}, {first.name, second.name})
		selected = scan_barcode(number, item_code=second.name)
		self.assertEqual(selected["serial_no_id"], second_serial.name)
		self.assertEqual(selected["serial_no"], number)
		self.assertEqual(scan_barcode(first_serial.name), {})

	def test_shared_batch_scan_returns_internal_links(self):
		items = [self.make_item(properties={"has_batch_no": 1}) for _ in range(2)]
		number = f"Lot-{frappe.generate_hash()}"
		batches = [
			frappe.get_doc(doctype="Batch", item=item.name, batch_id=number).insert() for item in items
		]
		candidates = scan_barcode(number.lower())["candidates"]
		self.assertEqual({row["batch_no"] for row in candidates}, {batch.name for batch in batches})
		selected = scan_barcode(number, item_code=items[0].name)
		self.assertEqual(selected["batch_no"], batches[0].name)
		self.assertEqual(selected["batch_id"], number)

	def test_scan_returns_all_record_types_for_the_same_item(self):
		item = self.make_item(properties={"has_batch_no": 1, "has_serial_no": 1})
		number = f"Shared-{frappe.generate_hash()}"
		batch = frappe.get_doc(doctype="Batch", item=item.name, batch_id=number).insert()
		frappe.get_doc(
			doctype="Serial No",
			item_code=item.name,
			serial_no=number,
			batch_no=batch.name,
			company="_Test Company",
		).insert()
		candidates = scan_barcode(number, item_code=item.name)["candidates"]
		self.assertEqual({row["record_type"] for row in candidates}, {"Serial No", "Batch"})

	def test_item_barcode_does_not_hide_a_matching_serial(self):
		number = f"Barcode-{frappe.generate_hash()}"
		barcode_item = self.make_item(properties={"barcodes": [{"barcode": number}]})
		serial_item = self.make_item(properties={"has_serial_no": 1})
		frappe.get_doc(
			doctype="Serial No", item_code=serial_item.name, serial_no=number, company="_Test Company"
		).insert()
		candidates = scan_barcode(number)["candidates"]
		self.assertEqual({row["item_code"] for row in candidates}, {barcode_item.name, serial_item.name})

	def test_unknown_scan_does_not_create_records(self):
		item = self.make_item(properties={"has_serial_no": 1, "has_batch_no": 1})
		number = f"Missing-{frappe.generate_hash()}"
		self.assertEqual(scan_barcode(number, item_code=item.name), {})
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item.name, "serial_no": number}))
		self.assertFalse(frappe.db.exists("Batch", {"item": item.name, "batch_id": number}))

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

	def test_get_latest_stock_qty(self):
		"""get_latest_stock_qty (Sum(actual_qty) over Bin; the warehouse-subtree EXISTS converted to
		a qb subquery) must reflect received stock for a non-group warehouse."""
		from frappe.utils import flt

		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.utils import get_latest_stock_qty

		warehouse = "_Test Warehouse - _TC"
		item = self.make_item(properties={"is_stock_item": 1}).name
		before = flt(get_latest_stock_qty(item, warehouse))

		make_stock_entry(item_code=item, target=warehouse, qty=8, basic_rate=100)

		self.assertEqual(flt(get_latest_stock_qty(item, warehouse)), before + 8)

	def test_get_stock_value_from_bin(self):
		"""get_stock_value_from_bin (comma-join -> inner_join, `ifnull(disabled,0)=0` ->
		`disabled==0 | isnull`) must sum the Bin stock_value for an item."""
		from frappe.utils import flt

		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.utils import get_stock_value_from_bin

		warehouse = "_Test Warehouse - _TC"
		item = self.make_item(properties={"is_stock_item": 1}).name

		make_stock_entry(item_code=item, target=warehouse, qty=5, basic_rate=50)

		# returns a single-row result set: [(stock_value,)]
		self.assertEqual(flt(get_stock_value_from_bin(item_code=item)[0][0]), 5 * 50)

	def test_get_avg_purchase_rate(self):
		"""get_avg_purchase_rate must average Serial No purchase_rate via the dict-`AVG` get_all
		field (frappe compiles `[{"AVG": "purchase_rate"}]` to `AVG(purchase_rate)` on both engines)."""
		from frappe.utils import flt, random_string

		from erpnext.stock.utils import get_avg_purchase_rate

		item = self.make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		serial_nos = []
		for rate in (10, 30):
			sn = "_TAVG" + random_string(8)
			serial = frappe.get_doc(
				{
					"doctype": "Serial No",
					"serial_no": sn,
					"item_code": item,
					"company": "_Test Company",
					"purchase_rate": rate,
				}
			).insert()
			serial_nos.append(serial.name)

		self.assertEqual(flt(get_avg_purchase_rate("\n".join(serial_nos))), 20.0)


class TestStockBalancePermissions(ERPNextTestSuite, StockTestMixin):
	def setUp(self):
		self.item = self.make_item().name
		self.other_item = self.make_item().name
		make_stock_entry(item_code=self.item, to_warehouse=WAREHOUSE, qty=7, rate=123.17)
		make_stock_entry(item_code=self.item, to_warehouse=OTHER_WAREHOUSE, qty=3, rate=50.31)
		make_stock_entry(item_code=self.other_item, to_warehouse=OTHER_WAREHOUSE, qty=2, rate=40.73)

	def user(self, role, user_permissions=None):
		email = f"test_stock_balance_{frappe.scrub(role)}@example.com"
		return make_fenced_user(email, [role], user_permissions)

	def scoped_user(self, role, allow, for_value, applicable_for, hide_descendants=0):
		email = self.user(role)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": email,
				"allow": allow,
				"for_value": for_value,
				"apply_to_all_doctypes": 0,
				"applicable_for": applicable_for,
				"hide_descendants": hide_descendants,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=email)
		return email

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
		batch_warehouse = (
			frappe.get_doc(
				{"doctype": "Warehouse", "warehouse_name": "TSBP Store", "company": "_Test Company"}
			)
			.insert()
			.name
		)
		make_stock_entry(item_code=batch_item, to_warehouse=batch_warehouse, qty=4, rate=61.29)

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
				self.assertRaises(frappe.PermissionError, get_items, batch_warehouse, *args[1:4])

		with as_user(self.user("Stock User")):
			self.assertRaises(frappe.PermissionError, get_items, *args)
			self.assertEqual(get_available_putaway_capacity(rule), 3)
			self.assertEqual(get_data(item_code=self.item)[0]["actual_qty"], 7)

		with as_user(self.user("Stock User", [("Warehouse", OTHER_WAREHOUSE)])):
			self.assertRaises(frappe.PermissionError, get_available_putaway_capacity, rule)

		with as_user(self.user("Stock Manager", [("Warehouse", OTHER_WAREHOUSE)])):
			self.assertRaises(frappe.PermissionError, get_items, *args)
			self.assertEqual(get_items(OTHER_WAREHOUSE, *args[1:])[0]["qty"], 3)
			self.assertRaises(frappe.PermissionError, get_stock_balance_for, self.item, WAREHOUSE, *args[1:3])
			self.assertEqual(get_stock_balance_for(self.item, OTHER_WAREHOUSE, *args[1:3])["qty"], 3)

		with as_user(self.scoped_user("Stock Manager", "Company", "_Test Company 1", "Item")):
			self.assertRaises(frappe.PermissionError, get_stock_balance_for, self.item, WAREHOUSE, *args[1:3])
			reconciliation = frappe.get_doc(
				{
					"doctype": "Stock Reconciliation",
					"company": "_Test Company",
					"purpose": "Stock Reconciliation",
					"items": [{"item_code": self.item, "warehouse": WAREHOUSE, "qty": 9}],
				}
			).insert()

		self.assertEqual(reconciliation.items[0].current_qty, 7)

		with as_user(self.user("Stock Manager", [("Item", self.item)])):
			self.assertRaises(
				frappe.PermissionError, get_stock_balance_for, self.other_item, OTHER_WAREHOUSE, *args[1:3]
			)
			self.assertRaises(frappe.PermissionError, get_items, OTHER_WAREHOUSE, *args[1:4], self.other_item)
			fenced_items = []
			for row in get_items(OTHER_WAREHOUSE, *args[1:4]):
				fenced_items.append(row["item_code"])

		with as_user(self.user("Stock Manager", [("Warehouse", "All Warehouses - _TC", 1)])):
			self.assertRaises(frappe.PermissionError, get_items, "All Warehouses - _TC", *args[1:])

		with as_user(self.user("Stock Manager")):
			self.assertEqual(get_items(*args)[0]["qty"], 7)
			all_items = []
			for row in get_items(OTHER_WAREHOUSE, *args[1:4]):
				all_items.append(row["item_code"])

		self.assertIn(self.item, fenced_items)
		self.assertNotIn(self.other_item, fenced_items)
		self.assertIn(self.item, all_items)
		self.assertIn(self.other_item, all_items)

	def test_reconciliation_lookups_apply_scoped_user_permissions(self):
		args = (nowdate(), nowtime())
		grouped_item = self.make_item(properties={"item_group": "_Test Item Group Desktops"}).name
		make_stock_entry(item_code=grouped_item, to_warehouse=OTHER_WAREHOUSE, qty=1, rate=10)

		def listed(warehouse):
			item_codes = []
			for row in get_items(warehouse, *args, "_Test Company"):
				item_codes.append(row["item_code"])
			return item_codes

		with as_user(self.scoped_user("Stock Manager", "Item", self.item, "Stock Reconciliation")):
			assert_refused(self, get_stock_balance_for, self.other_item, OTHER_WAREHOUSE, *args)
			assert_refused(self, get_items, OTHER_WAREHOUSE, *args, "_Test Company", self.other_item)
			item_scoped = listed(OTHER_WAREHOUSE)

		with as_user(self.scoped_user("Stock Manager", "Warehouse", OTHER_WAREHOUSE, "Stock Reconciliation")):
			assert_refused(self, get_stock_balance_for, self.item, WAREHOUSE, *args)
			assert_refused(self, get_items, WAREHOUSE, *args, "_Test Company", self.item)

		group_user = self.scoped_user(
			"Stock Manager", "Warehouse", "All Warehouses - _TC", "Stock Reconciliation", hide_descendants=1
		)
		with as_user(group_user):
			assert_refused(self, get_items, "All Warehouses - _TC", *args, "_Test Company")

		with as_user(self.scoped_user("Stock Manager", "Warehouse", OTHER_WAREHOUSE, "Warehouse")):
			self.assertRaises(frappe.PermissionError, get_stock_balance_for, self.item, WAREHOUSE, *args)

		with as_user(self.scoped_user("Stock Manager", "Item", self.item, "Sales Order")):
			self.assertEqual(get_stock_balance_for(self.other_item, OTHER_WAREHOUSE, *args)["qty"], 2)

		item_group = frappe.db.get_value("Item", self.item, "item_group")
		with as_user(self.user("Stock Manager", [("Item Group", item_group)])):
			group_scoped = listed(OTHER_WAREHOUSE)
			self.assertRaises(
				frappe.PermissionError, get_stock_balance_for, grouped_item, OTHER_WAREHOUSE, *args
			)
			self.assertRaises(
				frappe.PermissionError, get_items, OTHER_WAREHOUSE, *args, "_Test Company", grouped_item
			)

		self.assertIn(self.item, item_scoped)
		self.assertNotIn(self.other_item, item_scoped)
		self.assertIn(self.item, group_scoped)
		self.assertNotIn(grouped_item, group_scoped)

	def reconciliation_manager(self, allow, for_value, applicable_for):
		if applicable_for:
			return self.scoped_user("Stock Manager", allow, for_value, applicable_for)
		return self.user("Stock Manager", [(allow, for_value)])

	def make_batch(self, item_code, warehouse, qty, rate):
		batch = frappe.get_doc(
			{"doctype": "Batch", "batch_id": frappe.generate_hash(length=10), "item": item_code}
		)
		batch.insert()
		make_stock_entry(item_code=item_code, to_warehouse=warehouse, qty=qty, rate=rate, batch_no=batch.name)
		return batch.name

	def listed_rows(self, warehouse, company="_Test Company"):
		rows = []
		for row in get_items(warehouse, nowdate(), nowtime(), company):
			rows.append((row["item_code"], row["warehouse"], row["batch_no"]))
		return rows

	def test_reconciliation_lookups_follow_reconciliation_user_permissions(self):
		other_company_warehouse = "Stores - _TC1"
		make_stock_entry(item_code=self.item, to_warehouse=other_company_warehouse, qty=4, rate=77)
		grouped_item = self.make_item(properties={"item_group": "_Test Item Group Desktops"}).name
		make_stock_entry(item_code=grouped_item, to_warehouse=WAREHOUSE, qty=1, rate=10)
		uom_item = self.make_item(properties={"stock_uom": "_Test UOM 1"}).name
		make_stock_entry(item_code=uom_item, to_warehouse=WAREHOUSE, qty=1, rate=10)
		batch_item = self.make_item(properties={"has_batch_no": 1}).name
		batch = self.make_batch(batch_item, WAREHOUSE, 4, 17)
		other_batch = self.make_batch(batch_item, WAREHOUSE, 6, 19)
		item_group, stock_uom = frappe.db.get_value("Item", self.item, ["item_group", "stock_uom"])
		args = (nowdate(), nowtime())

		cells = [
			("Company", "_Test Company", (self.item, WAREHOUSE), (self.item, other_company_warehouse)),
			("Warehouse", WAREHOUSE, (self.item, WAREHOUSE), (self.item, OTHER_WAREHOUSE)),
			("Item", self.item, (self.item, WAREHOUSE), (self.other_item, OTHER_WAREHOUSE)),
			("Item Group", item_group, (self.item, WAREHOUSE), (grouped_item, WAREHOUSE)),
			("UOM", stock_uom, (self.item, WAREHOUSE), (uom_item, WAREHOUSE)),
		]
		for allow, for_value, permitted, outside in cells:
			for applicable_for in (None, "Stock Reconciliation", "Sales Order"):
				with self.subTest(allow=allow, applicable_for=applicable_for):
					with as_user(self.reconciliation_manager(allow, for_value, applicable_for)):
						self.assertEqual(get_stock_balance_for(*permitted, *args)["qty"], 7)
						self.assertEqual(
							get_items(permitted[1], *args, "_Test Company", permitted[0])[0]["qty"], 7
						)
						company = frappe.db.get_value("Warehouse", outside[1], "company")
						if applicable_for == "Sales Order":
							get_stock_balance_for(*outside, *args)
							get_items(outside[1], *args, company, outside[0])
						elif applicable_for:
							assert_refused(self, get_stock_balance_for, *outside, *args)
							assert_refused(self, get_items, outside[1], *args, company, outside[0])
						else:
							self.assertRaises(frappe.PermissionError, get_stock_balance_for, *outside, *args)
							self.assertRaises(
								frappe.PermissionError, get_items, outside[1], *args, company, outside[0]
							)

		for applicable_for in (None, "Stock Reconciliation", "Sales Order"):
			with self.subTest(allow="Batch", applicable_for=applicable_for):
				with as_user(self.reconciliation_manager("Batch", batch, applicable_for)):
					self.assertEqual(get_stock_balance_for(batch_item, WAREHOUSE, *args, batch)["qty"], 4)
					rows = self.listed_rows(WAREHOUSE)
					self.assertIn((batch_item, WAREHOUSE, batch), rows)
					if applicable_for == "Sales Order":
						self.assertEqual(
							get_stock_balance_for(batch_item, WAREHOUSE, *args, other_batch)["qty"], 6
						)
						self.assertIn((batch_item, WAREHOUSE, other_batch), rows)
					else:
						assert_refused(self, get_stock_balance_for, batch_item, WAREHOUSE, *args, other_batch)
						self.assertNotIn((batch_item, WAREHOUSE, other_batch), rows)

		for allow, for_value, outside in (
			("Item Group", item_group, grouped_item),
			("UOM", stock_uom, uom_item),
		):
			with self.subTest(allow=allow, listed=True):
				with as_user(self.reconciliation_manager(allow, for_value, "Stock Reconciliation")):
					rows = self.listed_rows(WAREHOUSE)
				with as_user(self.reconciliation_manager(allow, for_value, "Sales Order")):
					unrestricted_rows = self.listed_rows(WAREHOUSE)
				self.assertIn((self.item, WAREHOUSE, None), rows)
				self.assertNotIn((outside, WAREHOUSE, None), rows)
				self.assertIn((outside, WAREHOUSE, None), unrestricted_rows)

		with as_user(self.user("Stock Manager")):
			self.assertEqual(get_stock_balance_for(self.item, other_company_warehouse, *args)["qty"], 4)
			self.assertEqual(get_stock_balance_for(batch_item, WAREHOUSE, *args, other_batch)["qty"], 6)
			rows = self.listed_rows(WAREHOUSE)
			for item_code in (self.item, grouped_item, uom_item):
				self.assertIn((item_code, WAREHOUSE, None), rows)
			self.assertIn((batch_item, WAREHOUSE, other_batch), rows)

	def test_reconciliation_lookups_check_the_entry_company(self):
		other_company_warehouse = "Stores - _TC1"
		make_stock_entry(item_code=self.item, to_warehouse=other_company_warehouse, qty=4, rate=77)
		group = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "TSBP Group",
				"company": "_Test Company",
				"is_group": 1,
			}
		).insert()
		child = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "TSBP Child",
				"company": "_Test Company 1",
				"parent_warehouse": group.name,
			}
		).insert()
		make_stock_entry(item_code=self.item, to_warehouse=child.name, qty=5, rate=31)
		args = (nowdate(), nowtime())

		for applicable_for in ("Stock Reconciliation", "Sales Order"):
			with self.subTest(applicable_for=applicable_for):
				with as_user(self.reconciliation_manager("Company", "_Test Company", applicable_for)):
					self.assertEqual(
						get_stock_balance_for(self.item, WAREHOUSE, *args, company="_Test Company")["qty"], 7
					)
					calls = [
						(
							get_stock_balance_for,
							(self.item, WAREHOUSE, *args),
							{"company": "_Test Company 1"},
						),
						(get_stock_balance_for, (self.item, other_company_warehouse, *args), {}),
						(
							get_stock_balance_for,
							(self.item, other_company_warehouse, *args),
							{"company": "_Test Company"},
						),
						(get_items, (WAREHOUSE, *args, "_Test Company 1"), {}),
						(get_items, (group.name, *args, "_Test Company"), {}),
					]
					for fn, fn_args, kwargs in calls:
						if applicable_for == "Sales Order":
							fn(*fn_args, **kwargs)
						else:
							assert_refused(self, fn, *fn_args, **kwargs)

		with as_user(self.user("Stock Manager")):
			self.assertIn((self.item, child.name, None), self.listed_rows(group.name))

	def test_reconciliation_balance_checks_the_row_it_is_given(self):
		batch_item = self.make_item(properties={"has_batch_no": 1}).name
		batch = self.make_batch(batch_item, WAREHOUSE, 4, 17)
		other_batch = self.make_batch(batch_item, WAREHOUSE, 6, 19)
		args = (nowdate(), nowtime())

		def balance(row_batch):
			row = {
				"item_code": batch_item,
				"warehouse": WAREHOUSE,
				"batch_no": row_batch,
				"use_serial_batch_fields": 1,
				"current_qty": 1,
			}
			return get_stock_balance_for(batch_item, WAREHOUSE, *args, batch, row=row)

		for applicable_for in (None, "Stock Reconciliation"):
			with as_user(self.reconciliation_manager("Batch", batch, applicable_for)):
				self.assertEqual(balance(batch)["rate"], 17)
				assert_refused(self, balance, other_batch)

		with as_user(self.user("Stock Manager")):
			self.assertEqual(balance(other_batch)["rate"], 19)

		item_group = frappe.db.get_value("Item", self.item, "item_group")
		self.make_item(properties={"item_group": "_Test Item Group Desktops"})
		with as_user(self.reconciliation_manager("Item Group", item_group, "Stock Reconciliation")):
			row = {"item_code": {"item_group": "_Test Item Group Desktops"}, "warehouse": WAREHOUSE}
			self.assertEqual(get_stock_balance_for(self.item, WAREHOUSE, *args, row=row)["qty"], 7)

		with as_user(self.reconciliation_manager("Company", "_Test Company", "Stock Reconciliation")):
			row = {"item_code": self.item, "warehouse": {"company": "_Test Company 1"}}
			self.assertEqual(get_stock_balance_for(self.item, WAREHOUSE, *args, row=row)["qty"], 7)

		with as_user(self.reconciliation_manager("Item", self.item, "Stock Reconciliation")):
			row = {"item_code": self.item, "warehouse": OTHER_WAREHOUSE}
			assert_refused(self, get_stock_balance_for, self.other_item, OTHER_WAREHOUSE, *args, row=row)

	def test_reconciliation_lookups_follow_strict_user_permissions(self):
		batch_item = self.make_item(properties={"has_batch_no": 1}).name
		batch = self.make_batch(batch_item, WAREHOUSE, 4, 17)
		args = (nowdate(), nowtime())

		frappe.db.set_single_value("System Settings", "apply_strict_user_permissions", 1)
		self.addCleanup(frappe.db.set_single_value, "System Settings", "apply_strict_user_permissions", 0)

		with as_user(self.reconciliation_manager("Batch", batch, "Stock Reconciliation")):
			assert_refused(self, get_stock_balance_for, self.item, WAREHOUSE, *args)
			self.assertEqual(get_stock_balance_for(batch_item, WAREHOUSE, *args, batch)["qty"], 4)

		with as_user(self.reconciliation_manager("Batch", batch, None)):
			self.assertEqual(get_stock_balance_for(self.item, WAREHOUSE, *args)["qty"], 7)

		user = self.reconciliation_manager("Item", self.item, "Stock Reconciliation")
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Item",
				"for_value": self.other_item,
				"apply_to_all_doctypes": 0,
				"applicable_for": "Stock Reconciliation",
			}
		).insert(ignore_permissions=True)
		with as_user(user):
			listed = set()
			for row in get_items(OTHER_WAREHOUSE, *args, "_Test Company"):
				listed.add(row["item_code"])
		self.assertEqual(listed, {self.item, self.other_item})

	def test_reconciliation_balance_checks_inventory_dimensions(self):
		from erpnext.stock.doctype.inventory_dimension.test_inventory_dimension import (
			create_inventory_dimension,
		)

		if not frappe.db.exists("DocType", "Plant"):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": "Plant",
					"module": "Stock",
					"custom": 1,
					"fields": [
						{"fieldname": "plant_name", "fieldtype": "Data", "label": "Plant Name", "reqd": 1}
					],
					"autoname": "field:plant_name",
				}
			).insert(ignore_permissions=True)
		dimension = create_inventory_dimension(dimension_name="ID-Plant", reference_document="Plant")
		plants = []
		for name in ("TSBP Plant A", "TSBP Plant B"):
			frappe.get_doc({"doctype": "Plant", "plant_name": name}).insert(ignore_permissions=True)
			plants.append(name)
		args = (nowdate(), nowtime())

		for applicable_for in (None, "Stock Reconciliation", "Sales Order"):
			with self.subTest(applicable_for=applicable_for):
				with as_user(self.reconciliation_manager("Plant", plants[0], applicable_for)):
					get_stock_balance_for(
						self.item,
						WAREHOUSE,
						*args,
						inventory_dimensions_dict={dimension.target_fieldname: plants[0]},
					)
					outside = {dimension.target_fieldname: plants[1]}
					if applicable_for == "Sales Order":
						get_stock_balance_for(self.item, WAREHOUSE, *args, inventory_dimensions_dict=outside)
					else:
						assert_refused(
							self,
							get_stock_balance_for,
							self.item,
							WAREHOUSE,
							*args,
							inventory_dimensions_dict=outside,
						)

		frappe.get_doc({"doctype": "Plant", "plant_name": "TSBP Plant C"}).insert(ignore_permissions=True)
		frappe.db.set_single_value("System Settings", "apply_strict_user_permissions", 1)
		self.addCleanup(frappe.db.set_single_value, "System Settings", "apply_strict_user_permissions", 0)
		user = self.reconciliation_manager("Plant", plants[0], "Stock Reconciliation")
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Plant",
				"for_value": plants[1],
				"apply_to_all_doctypes": 0,
				"applicable_for": "Stock Reconciliation",
			}
		).insert(ignore_permissions=True)

		def form_balance(plant):
			row = {"item_code": self.item, "warehouse": WAREHOUSE, dimension.source_fieldname: plant}
			return get_stock_balance_for(self.item, WAREHOUSE, *args, None, row=row, company="_Test Company")

		with as_user(user):
			self.assertEqual(form_balance(plants[0])["qty"], 7)
			self.assertEqual(form_balance(plants[1])["qty"], 7)
			assert_refused(self, form_balance, "TSBP Plant C")

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

		frappe.db.set_value("Company", "_Test Company", "default_warehouse", WAREHOUSE)
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
