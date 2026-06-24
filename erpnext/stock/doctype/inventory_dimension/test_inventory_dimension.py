# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import (
	CanNotBeChildDoc,
	CanNotBeDefaultDimension,
	InventoryDimensionNotEnabled,
	delete_dimension,
)
from erpnext.stock.doctype.inventory_dimension_bundle.inventory_dimension_bundle import (
	InventoryDimensionNegativeStockError,
	get_dimension_sub_ledger_balance,
)
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.services.inventory_dimension_bundle_service import InventoryDimensionBundleService
from erpnext.tests.utils import ERPNextTestSuite

ENTRY_DOCTYPE = "Inventory Dimension Entry"


class TestInventoryDimension(ERPNextTestSuite):
	def setUp(self):
		# Enable the feature via a flag (not the committed Stock Settings single) so it can never
		# leak into unrelated test modules. Dimension Custom Fields are committed (DDL), so dimension
		# records and their reqd / validate_negative_stock flags survive the per-test rollback; reset
		# them so a sibling test's flag cannot make this one fail.
		frappe.flags.enable_inventory_dimension = 1
		reset_inventory_dimension_flags()

	def tearDown(self):
		frappe.flags.enable_inventory_dimension = None
		super().tearDown()
		clear_dimension_cache()

	def test_inventory_dimension_requires_stock_setting(self):
		# With the feature off, creating a dimension must be blocked.
		frappe.flags.enable_inventory_dimension = 0

		inv_dim = create_inventory_dimension(
			reference_document="Shelf",
			dimension_name="From Shelf",
			apply_to_all_doctypes=1,
			do_not_save=True,
		)
		self.assertRaises(InventoryDimensionNotEnabled, inv_dim.insert)

	def test_validate_inventory_dimension(self):
		# The reference document can not be a child table.
		inv_dim1 = create_inventory_dimension(
			reference_document="Stock Entry Detail",
			type_of_transaction="Outward",
			dimension_name="Stock Entry",
			apply_to_all_doctypes=0,
			istable=0,
			document_type="Stock Entry",
			do_not_save=True,
		)
		self.assertRaises(CanNotBeChildDoc, inv_dim1.insert)

		# The reference document can not be one of the built-in dimensions.
		inv_dim1 = create_inventory_dimension(
			reference_document="Batch",
			type_of_transaction="Outward",
			dimension_name="Batch",
			apply_to_all_doctypes=0,
			document_type="Stock Entry Detail",
			do_not_save=True,
		)
		self.assertRaises(CanNotBeDefaultDimension, inv_dim1.insert)

	def test_dimension_creates_and_drops_subledger_column(self):
		"""A dimension adds a single column to the quantity sub-ledger - not to every stock doctype."""
		inv_dim = create_inventory_dimension(
			reference_document="Shelf",
			dimension_name="From Shelf",
			apply_to_all_doctypes=1,
		)

		# One Link column is added to Inventory Dimension Entry.
		self.assertTrue(frappe.db.get_value("Custom Field", {"dt": ENTRY_DOCTYPE, "fieldname": "from_shelf"}))

		# No per-doctype custom field is created on the stock transaction doctypes anymore.
		self.assertFalse(
			frappe.db.get_value("Custom Field", {"dt": "Stock Entry Detail", "fieldname": "from_shelf"})
		)

		delete_dimension(inv_dim.name)
		self.assertFalse(
			frappe.db.get_value("Custom Field", {"dt": ENTRY_DOCTYPE, "fieldname": "from_shelf"})
		)

	def test_inventory_dimension_subledger_posting(self):
		"""Submitting a voucher posts its bundle to the sub-ledger; cancelling reverses it."""
		create_inventory_dimension(
			reference_document="Shelf", dimension_name="Shelf", apply_to_all_doctypes=1
		)

		warehouse = create_warehouse("Shelf Warehouse")
		item_code = "_Test Item"

		se = make_stock_entry(item_code=item_code, target=warehouse, qty=5, basic_rate=10, do_not_save=True)
		bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 5, "shelf": "Shelf 1"}])
		se.items[0].inventory_dimension_bundle = bundle
		se.submit()

		# The Stock Ledger Entry links the single bundle.
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_no": se.name, "is_cancelled": 0},
				"inventory_dimension_bundle",
			),
			bundle,
		)

		# The dimension value lives on the sub-ledger entry, not on the SLE.
		entry = frappe.get_all(
			ENTRY_DOCTYPE, filters={"parent": bundle}, fields=["shelf", "qty", "is_outward"]
		)[0]
		self.assertEqual(entry.shelf, "Shelf 1")
		self.assertEqual(entry.is_outward, 0)

		self.assertEqual(
			get_dimension_sub_ledger_balance(item_code, warehouse, {"shelf": "Shelf 1"}, inclusive=True),
			5,
		)

		# Cancelling the voucher cancels the bundle and removes the qty from the sub-ledger.
		se.cancel()
		self.assertEqual(
			get_dimension_sub_ledger_balance(item_code, warehouse, {"shelf": "Shelf 1"}, inclusive=True),
			0,
		)

	def test_outward_bundle_stores_signed_qty(self):
		"""An outward bundle stores qty negative + is_outward set (mirrors SLE actual_qty)."""
		create_inventory_dimension(reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1)

		item_code = "Test Signed Qty Item"
		create_item(item_code)
		warehouse = create_warehouse("Signed Qty Warehouse")

		# Receive 50 first so the outward issue has stock to draw from.
		se_in = make_stock_entry(
			item_code=item_code, target=warehouse, qty=50, basic_rate=10, do_not_save=True
		)
		se_in.items[0].inventory_dimension_bundle = make_inventory_dimension_bundle(
			item_code, warehouse, [{"qty": 50, "rack": "Rack 1"}]
		)
		se_in.submit()

		# Issue 10: the bundle is stamped Outward on submit, so its entry qty is signed negative.
		se_out = make_stock_entry(item_code=item_code, source=warehouse, qty=10, do_not_save=True)
		bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 10, "rack": "Rack 1"}])
		se_out.items[0].inventory_dimension_bundle = bundle
		se_out.submit()

		doc = frappe.get_doc("Inventory Dimension Bundle", bundle)
		self.assertEqual(doc.type_of_transaction, "Outward")
		self.assertEqual(doc.entries[0].is_outward, 1)
		self.assertEqual(doc.entries[0].qty, -10)
		self.assertEqual(doc.total_qty, -10)

		# The signed sub-ledger nets to 40 (50 in - 10 out).
		self.assertEqual(
			get_dimension_sub_ledger_balance(item_code, warehouse, {"rack": "Rack 1"}, inclusive=True), 40
		)

	def test_material_transfer_posts_both_legs(self):
		"""A Stock Entry transfer posts the dimension out of the source and into the target warehouse."""
		create_inventory_dimension(reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1)

		item_code = "Test Transfer Item"
		create_item(item_code)
		wh_a = create_warehouse("Transfer Source Warehouse")
		wh_b = create_warehouse("Transfer Target Warehouse")

		# Receive 10 into the source warehouse / Rack 1.
		se_in = make_stock_entry(item_code=item_code, target=wh_a, qty=10, basic_rate=100, do_not_save=True)
		se_in.items[0].inventory_dimension_bundle = make_inventory_dimension_bundle(
			item_code, wh_a, [{"qty": 10, "rack": "Rack 1"}]
		)
		se_in.submit()

		# Transfer 4 from source to target: the outward leg draws Rack 1 down at the source and the
		# inward leg posts it into the target (the bug was the inward leg being lost).
		se_t = make_stock_entry(item_code=item_code, source=wh_a, target=wh_b, qty=4, do_not_save=True)
		se_t.items[0].inventory_dimension_bundle = make_inventory_dimension_bundle(
			item_code, wh_a, [{"qty": 4, "rack": "Rack 1"}]
		)
		se_t.submit()

		self.assertEqual(
			get_dimension_sub_ledger_balance(item_code, wh_a, {"rack": "Rack 1"}, inclusive=True), 6
		)
		self.assertEqual(
			get_dimension_sub_ledger_balance(item_code, wh_b, {"rack": "Rack 1"}, inclusive=True), 4
		)

		# Cancelling the transfer reverses both legs (including the target's inward bundle).
		se_t.reload()
		se_t.cancel()
		self.assertEqual(
			get_dimension_sub_ledger_balance(item_code, wh_a, {"rack": "Rack 1"}, inclusive=True), 10
		)
		self.assertEqual(
			get_dimension_sub_ledger_balance(item_code, wh_b, {"rack": "Rack 1"}, inclusive=True), 0
		)

	def test_delivery_note_dimension_bundle_posts_to_sle(self):
		"""A dimension bundle assigned to a Delivery Note row must reach the Stock Ledger Entry.

		Regression: the selling controller rebuilt each row via get_item_list() and dropped
		inventory_dimension_bundle, so the SLE was posted without it and the mandatory-dimension
		check spuriously failed.
		"""
		create_inventory_dimension(reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1)

		item_code = "Test DN Dimension Item"
		create_item(item_code, is_stock_item=1)
		warehouse = create_warehouse("DN Dimension Warehouse")
		company = frappe.db.get_value("Warehouse", warehouse, "company")

		# Stock the item so there is something to deliver.
		se = make_stock_entry(item_code=item_code, target=warehouse, qty=10, basic_rate=100, do_not_save=True)
		se.items[0].inventory_dimension_bundle = make_inventory_dimension_bundle(
			item_code, warehouse, [{"qty": 10, "rack": "Rack 1"}]
		)
		se.submit()

		dn = frappe.new_doc("Delivery Note")
		dn.company = company
		dn.customer = "_Test Customer"
		dn.append(
			"items",
			{"item_code": item_code, "warehouse": warehouse, "qty": 4, "rate": 150},
		)
		dn.insert()
		dn.items[0].inventory_dimension_bundle = make_inventory_dimension_bundle(
			item_code, warehouse, [{"qty": 4, "rack": "Rack 1"}]
		)
		dn.save()
		dn.submit()

		# The Stock Ledger Entry carries the bundle (no mandatory-dimension error was raised).
		sle_bundle = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": dn.name, "is_cancelled": 0}, "inventory_dimension_bundle"
		)
		self.assertTrue(sle_bundle)

		# The outward delivery draws Rack 1 down from 10 to 6.
		self.assertEqual(
			get_dimension_sub_ledger_balance(item_code, warehouse, {"rack": "Rack 1"}, inclusive=True), 6
		)

	def test_product_bundle_packed_item_dimension_bundle_is_submitted(self):
		"""A dimension bundle on a Product Bundle's packed item must be submitted with the voucher."""
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle

		create_inventory_dimension(reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1)

		parent_item = "Test PB Parent Item"
		child_item = "Test PB Child Item"
		create_item(parent_item, is_stock_item=0)
		create_item(child_item, is_stock_item=1)
		make_product_bundle(parent_item, [child_item])

		warehouse = create_warehouse("PB Dimension Warehouse")
		company = frappe.db.get_value("Warehouse", warehouse, "company")

		# Stock the child item into Rack 1.
		se = make_stock_entry(
			item_code=child_item, target=warehouse, qty=10, basic_rate=100, do_not_save=True
		)
		se.items[0].inventory_dimension_bundle = make_inventory_dimension_bundle(
			child_item, warehouse, [{"qty": 10, "rack": "Rack 1"}]
		)
		se.submit()

		dn = frappe.new_doc("Delivery Note")
		dn.company = company
		dn.customer = "_Test Customer"
		dn.append("items", {"item_code": parent_item, "warehouse": warehouse, "qty": 3, "rate": 150})
		dn.insert()  # packed_items are generated for the product bundle's child

		packed = dn.packed_items[0]
		bundle = make_inventory_dimension_bundle(
			child_item, packed.warehouse, [{"qty": packed.qty, "rack": "Rack 1"}]
		)
		packed.inventory_dimension_bundle = bundle
		dn.save()
		dn.submit()

		# The packed item's bundle is submitted (posted to the sub-ledger), not left a draft.
		self.assertEqual(frappe.db.get_value("Inventory Dimension Bundle", bundle, "docstatus"), 1)

		# Rack 1 was drawn down by the delivered packed qty (10 received - 3 delivered).
		self.assertEqual(
			get_dimension_sub_ledger_balance(child_item, warehouse, {"rack": "Rack 1"}, inclusive=True),
			10 - packed.qty,
		)

	def test_manual_bundle_infers_direction_from_voucher(self):
		"""A bundle created/linked manually for a Delivery Note is stamped Outward on save."""
		create_inventory_dimension(reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1)

		item_code = "Test Manual Direction Item"
		create_item(item_code)
		warehouse = create_warehouse("Manual Direction Warehouse")
		company = frappe.db.get_value("Warehouse", warehouse, "company")

		doc = frappe.new_doc("Inventory Dimension Bundle")
		doc.company = company
		doc.item_code = item_code
		doc.warehouse = warehouse
		doc.voucher_type = "Delivery Note"
		doc.append("entries", {"qty": 5, "rack": "Rack 1", "warehouse": warehouse})
		doc.flags.ignore_permissions = True
		doc.save()

		# Direction inferred from the voucher type while still a draft (no voucher submit yet).
		self.assertEqual(doc.type_of_transaction, "Outward")
		self.assertEqual(doc.entries[0].is_outward, 1)
		self.assertEqual(doc.entries[0].qty, -5)

	def test_bundle_cannot_be_submitted_manually(self):
		"""The bundle is submitted only by its voucher; a manual submit must be blocked."""
		create_inventory_dimension(reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1)

		item_code = "Test Manual Submit Item"
		create_item(item_code)
		warehouse = create_warehouse("Manual Submit Warehouse")
		bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 5, "rack": "Rack 1"}])

		doc = frappe.get_doc("Inventory Dimension Bundle", bundle)
		self.assertRaises(frappe.ValidationError, doc.submit)

	def test_bundle_cannot_be_cancelled_manually(self):
		"""The bundle is cancelled only by its voucher; a manual cancel must be blocked."""
		create_inventory_dimension(reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1)

		item_code = "Test Manual Cancel Item"
		create_item(item_code)
		warehouse = create_warehouse("Manual Cancel Warehouse")

		# Submit a bundle the only legitimate way - through its voucher.
		se = make_stock_entry(item_code=item_code, target=warehouse, qty=5, basic_rate=10, do_not_save=True)
		bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 5, "rack": "Rack 1"}])
		se.items[0].inventory_dimension_bundle = bundle
		se.submit()

		doc = frappe.get_doc("Inventory Dimension Bundle", bundle)
		self.assertRaises(frappe.ValidationError, doc.cancel)

	def test_cancelling_voucher_unlinks_bundle(self):
		"""Cancelling a voucher detaches its now-cancelled bundle so the voucher can be amended."""
		create_inventory_dimension(reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1)

		item_code = "Test Unlink Item"
		create_item(item_code)
		warehouse = create_warehouse("Unlink Warehouse")

		se = make_stock_entry(item_code=item_code, target=warehouse, qty=10, basic_rate=100, do_not_save=True)
		bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 10, "rack": "Rack 1"}])
		se.items[0].inventory_dimension_bundle = bundle
		se.submit()

		se.reload()
		se.cancel()

		# The bundle is cancelled and detached from the voucher row.
		self.assertEqual(frappe.db.get_value("Inventory Dimension Bundle", bundle, "docstatus"), 2)
		self.assertFalse(
			frappe.db.get_value("Stock Entry Detail", se.items[0].name, "inventory_dimension_bundle")
		)

		# Amending the cancelled voucher saves without a "Cannot link cancelled document" error.
		amended = frappe.copy_doc(se)
		amended.amended_from = se.name
		amended.docstatus = 0
		amended.save()
		self.assertFalse(amended.items[0].inventory_dimension_bundle)

	def test_dimension_wise_stock_balance_report(self):
		"""The Stock Balance report splits an item/warehouse row by dimension from the sub-ledger."""
		from frappe.utils import add_days, today

		from erpnext.stock.report.stock_balance.stock_balance import execute

		create_inventory_dimension(reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1)

		item_code = "Test Dimension Balance Item"
		create_item(item_code)
		warehouse = create_warehouse("Dimension Balance Warehouse")
		company = frappe.db.get_value("Warehouse", warehouse, "company")

		# Receive 30 into Rack 1 and 20 into Rack 2 (same item + warehouse).
		for rack, qty in [("Rack 1", 30), ("Rack 2", 20)]:
			se = make_stock_entry(
				item_code=item_code, target=warehouse, qty=qty, basic_rate=10, do_not_save=True
			)
			bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": qty, "rack": rack}])
			se.items[0].inventory_dimension_bundle = bundle
			se.submit()

		filters = frappe._dict(
			company=company,
			from_date=add_days(today(), -1),
			to_date=today(),
			item_code=[item_code],
			warehouse=[warehouse],
			show_dimension_wise_stock=1,
		)

		_columns, data = execute(filters)
		rack_balances = {
			row.get("rack"): row.get("bal_qty") for row in data if row.get("item_code") == item_code
		}

		# One row per rack, each carrying only its own balance (no residual since all 50 is captured).
		self.assertEqual(rack_balances.get("Rack 1"), 30)
		self.assertEqual(rack_balances.get("Rack 2"), 20)
		self.assertNotIn(None, rack_balances)
		self.assertEqual(sum(rack_balances.values()), 50)

	def test_dimension_wise_stock_ledger_report(self):
		"""Filtering the Stock Ledger report by a dimension shows that dimension's ledger only."""
		from frappe.utils import add_days, today

		from erpnext.stock.report.stock_ledger.stock_ledger import execute

		create_inventory_dimension(reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1)

		item_code = "Test Dimension Ledger Item"
		create_item(item_code)
		warehouse = create_warehouse("Dimension Ledger Warehouse")
		company = frappe.db.get_value("Warehouse", warehouse, "company")

		# Receive 30 into Rack 1 and 20 into Rack 2, then issue 10 from Rack 1.
		for rack, qty in [("Rack 1", 30), ("Rack 2", 20)]:
			se = make_stock_entry(
				item_code=item_code, target=warehouse, qty=qty, basic_rate=10, do_not_save=True
			)
			bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": qty, "rack": rack}])
			se.items[0].inventory_dimension_bundle = bundle
			se.submit()

		se = make_stock_entry(item_code=item_code, source=warehouse, qty=10, do_not_save=True)
		bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 10, "rack": "Rack 1"}])
		se.items[0].inventory_dimension_bundle = bundle
		se.submit()

		filters = frappe._dict(
			company=company,
			from_date=add_days(today(), -1),
			to_date=today(),
			item_code=[item_code],
			warehouse=[warehouse],
			rack=["Rack 1"],
		)

		_columns, data = execute(filters)
		rows = [row for row in data if row.get("item_code") == item_code]

		# Only Rack 1 movements: a +30 receipt and a -10 issue (Rack 2 is excluded).
		self.assertEqual(len(rows), 2)
		self.assertTrue(all(row.get("rack") == "Rack 1" for row in rows))
		self.assertEqual([row.get("actual_qty") for row in rows], [30, -10])
		# Running balance for Rack 1 ends at 20.
		self.assertEqual(rows[-1].get("qty_after_transaction"), 20)

		# Without a dimension filter, each row still shows its bundle's dimension value in the column.
		unfiltered = frappe._dict(
			company=company,
			from_date=add_days(today(), -1),
			to_date=today(),
			item_code=[item_code],
			warehouse=[warehouse],
		)
		_columns, data = execute(unfiltered)
		rack_values = {row.get("rack") for row in data if row.get("voucher_type") == "Stock Entry"}
		self.assertEqual(rack_values, {"Rack 1", "Rack 2"})

		# With the feature disabled, the report must not fetch any sub-ledger dimension data.
		frappe.flags.enable_inventory_dimension = 0
		_columns, data = execute(unfiltered)
		self.assertTrue(all(not row.get("rack") for row in data))

	def test_dimension_ledger_running_balance_is_per_item_warehouse(self):
		"""A dimension filter spanning warehouses keeps a separate running balance per warehouse."""
		from frappe.utils import add_days, today

		from erpnext.stock.report.stock_ledger.stock_ledger import execute

		frappe.flags.enable_inventory_dimension = 1
		create_inventory_dimension(reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1)

		item_code = "Test Dimension Multi WH Item"
		create_item(item_code)
		wh_a = create_warehouse("Dimension WH A")
		wh_b = create_warehouse("Dimension WH B")
		company = frappe.db.get_value("Warehouse", wh_a, "company")

		# Receive Rack 1: 30 into WH A and 50 into WH B.
		for warehouse, qty in [(wh_a, 30), (wh_b, 50)]:
			se = make_stock_entry(
				item_code=item_code, target=warehouse, qty=qty, basic_rate=10, do_not_save=True
			)
			bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": qty, "rack": "Rack 1"}])
			se.items[0].inventory_dimension_bundle = bundle
			se.submit()

		# Filter by Rack 1 only (no warehouse restriction): each warehouse keeps its own balance.
		filters = frappe._dict(
			company=company,
			from_date=add_days(today(), -1),
			to_date=today(),
			item_code=[item_code],
			rack=["Rack 1"],
		)
		_columns, data = execute(filters)
		balances = {
			row.get("warehouse"): row.get("qty_after_transaction")
			for row in data
			if row.get("voucher_type") == "Stock Entry"
		}
		self.assertEqual(balances.get(wh_a), 30)
		self.assertEqual(balances.get(wh_b), 50)

	def test_mandatory_dimension_for_stock_item(self):
		"""A mandatory dimension is enforced for stock rows at submit (gated on is_stock_item)."""
		item_code = "_Test Item"
		dimension = create_inventory_dimension(
			reference_document="Pallet", dimension_name="Pallet", apply_to_all_doctypes=1
		)
		dimension.db_set("reqd", 1)
		clear_dimension_cache()

		if not frappe.db.exists("Pallet", "Pallet 1"):
			frappe.get_doc({"doctype": "Pallet", "pallet_name": "Pallet 1"}).insert(ignore_permissions=True)

		warehouse = create_warehouse("Pallet Warehouse")

		try:
			# No bundle attached -> the SLE requires the bundle (req #1).
			se = make_stock_entry(
				item_code=item_code, target=warehouse, qty=5, basic_rate=10, do_not_save=True
			)
			se.save()
			self.assertRaises(frappe.ValidationError, se.submit)

			# Bundle attached but missing the mandatory dimension value -> the entry requires it (req #2).
			se = make_stock_entry(
				item_code=item_code, target=warehouse, qty=5, basic_rate=10, do_not_save=True
			)
			bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 5}])
			se.items[0].inventory_dimension_bundle = bundle
			self.assertRaises(frappe.ValidationError, se.submit)

			# With the dimension captured in a bundle, the voucher submits fine.
			se = make_stock_entry(
				item_code=item_code, target=warehouse, qty=5, basic_rate=10, do_not_save=True
			)
			bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 5, "pallet": "Pallet 1"}])
			se.items[0].inventory_dimension_bundle = bundle
			se.submit()
			self.assertEqual(se.docstatus, 1)
		finally:
			dimension.db_set("reqd", 0)
			clear_dimension_cache()

	def test_bundle_cannot_be_shared_across_vouchers(self):
		"""One Inventory Dimension Bundle may back only a single voucher's stock ledger."""
		create_inventory_dimension(
			reference_document="Shelf", dimension_name="Shelf", apply_to_all_doctypes=1
		)
		warehouse = create_warehouse("Shelf Share Warehouse")
		item_code = "_Test Item"

		se = make_stock_entry(item_code=item_code, target=warehouse, qty=5, basic_rate=10, do_not_save=True)
		bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 5, "shelf": "Shelf 1"}])
		se.items[0].inventory_dimension_bundle = bundle
		se.submit()

		# Re-using the same bundle on a different voucher must be rejected.
		other = make_stock_entry(
			item_code=item_code, target=warehouse, qty=5, basic_rate=10, do_not_save=True
		)
		other.items[0].inventory_dimension_bundle = bundle
		self.assertRaises(frappe.ValidationError, other.submit)

	def test_rejected_inventory_dimension_bundle(self):
		"""The rejected-qty bundle posts to the rejected warehouse's dimension sub-ledger."""
		item_code = "_Test Item"
		create_inventory_dimension(
			reference_document="Shelf", dimension_name="Shelf", apply_to_all_doctypes=1
		)
		warehouse = create_warehouse("PR Accepted Warehouse")
		rejected_warehouse = create_warehouse("PR Rejected Warehouse")

		pr = make_purchase_receipt(
			item_code=item_code,
			warehouse=warehouse,
			qty=10,
			rejected_qty=4,
			rate=100,
			rejected_warehouse=rejected_warehouse,
			do_not_submit=True,
		)
		pr.items[0].inventory_dimension_bundle = make_inventory_dimension_bundle(
			item_code, warehouse, [{"qty": 10, "shelf": "Shelf 1"}]
		)
		pr.items[0].rejected_inventory_dimension_bundle = make_inventory_dimension_bundle(
			item_code, rejected_warehouse, [{"qty": 4, "shelf": "Shelf 2"}]
		)
		pr.submit()

		self.assertEqual(
			get_dimension_sub_ledger_balance(item_code, warehouse, {"shelf": "Shelf 1"}, inclusive=True),
			10,
		)
		self.assertEqual(
			get_dimension_sub_ledger_balance(
				item_code, rejected_warehouse, {"shelf": "Shelf 2"}, inclusive=True
			),
			4,
		)

	def test_mandatory_dimension_validates_each_qty_leg(self):
		"""Mandatory coverage is enforced per leg: the accepted leg uses ``inventory_dimension_bundle``
		and the rejected leg uses ``rejected_inventory_dimension_bundle``. A row that captured its
		dimension on the rejected bundle alone must pass, and an uncovered rejected leg must be caught."""
		item_code = "_Test Item"
		dimension = create_inventory_dimension(
			reference_document="Shelf", dimension_name="Shelf", apply_to_all_doctypes=1
		)
		dimension.db_set("reqd", 1)
		clear_dimension_cache()

		warehouse = create_warehouse("Reqd Leg Accepted Warehouse")
		rejected_warehouse = create_warehouse("Reqd Leg Rejected Warehouse")

		accepted_bundle = make_inventory_dimension_bundle(
			item_code, warehouse, [{"qty": 10, "shelf": "Shelf 1"}]
		)
		rejected_bundle = make_inventory_dimension_bundle(
			item_code, rejected_warehouse, [{"qty": 4, "shelf": "Shelf 2"}]
		)

		service = InventoryDimensionBundleService(frappe.new_doc("Purchase Receipt"))

		def _check(row):
			service.doc.set("items", [frappe._dict(idx=1, item_code=item_code, **row)])
			service.validate_inventory_dimension_bundle()

		# Rejected-only row (qty=0): the dimension is captured on the rejected bundle, so the row is
		# fully covered. Previously the check only inspected the accepted bundle and falsely threw.
		_check({"qty": 0, "rejected_qty": 4, "rejected_inventory_dimension_bundle": rejected_bundle})

		# Both legs move stock but the rejected bundle is missing: the rejected leg must be caught.
		# Previously the rejected bundle was never fetched, so this gap was silently skipped.
		self.assertRaises(
			frappe.ValidationError,
			_check,
			{"qty": 10, "rejected_qty": 4, "inventory_dimension_bundle": accepted_bundle},
		)

		# Both legs covered on their own bundles -> passes.
		_check(
			{
				"qty": 10,
				"rejected_qty": 4,
				"inventory_dimension_bundle": accepted_bundle,
				"rejected_inventory_dimension_bundle": rejected_bundle,
			}
		)

	def test_service_item_skips_dimension(self):
		"""Non-stock (service) rows never require a dimension - they are skipped entirely."""
		service_item = "Test Service Dimension Item"
		if not frappe.db.exists("Item", service_item):
			create_item(service_item)
		frappe.db.set_value("Item", service_item, "is_stock_item", 0)

		service = InventoryDimensionBundleService(frappe.new_doc("Delivery Note"))

		# Service / non-stock row -> skipped (no dimension demanded).
		self.assertFalse(service.row_has_dimension_qty(frappe._dict(item_code=service_item, qty=5)))

		# A stock row with qty -> participates.
		self.assertTrue(service.row_has_dimension_qty(frappe._dict(item_code="_Test Item", qty=5)))

	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_negative_stock": 1})
	def test_validate_negative_stock_for_inventory_dimension(self):
		item_code = "Test Negative Inventory Dimension Item"
		create_item(item_code)

		inv_dimension = create_inventory_dimension(
			apply_to_all_doctypes=1,
			dimension_name="Inv Site",
			reference_document="Inv Site",
			validate_negative_stock=1,
		)
		inv_dimension.db_set("validate_negative_stock", 1)
		clear_dimension_cache()

		warehouse = create_warehouse("Negative Stock Warehouse")

		# Issue 10 against Site 1 with no stock -> blocked on the dimension.
		se = make_stock_entry(item_code=item_code, source=warehouse, qty=10, do_not_save=True)
		bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 10, "inv_site": "Site 1"}])
		se.items[0].inventory_dimension_bundle = bundle
		self.assertRaises(InventoryDimensionNegativeStockError, se.submit)

		# Receive 10 against Site 1.
		se = make_stock_entry(item_code=item_code, target=warehouse, qty=10, basic_rate=10, do_not_save=True)
		bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 10, "inv_site": "Site 1"}])
		se.items[0].inventory_dimension_bundle = bundle
		se.submit()
		self.assertEqual(
			get_dimension_sub_ledger_balance(item_code, warehouse, {"inv_site": "Site 1"}, inclusive=True),
			10,
		)

		# Receive another 100 with no dimension (general warehouse stock).
		make_stock_entry(item_code=item_code, target=warehouse, qty=100, basic_rate=10)

		# Issue 100 against Site 1: warehouse has 110 but Site 1 only has 10 -> blocked.
		se = make_stock_entry(item_code=item_code, source=warehouse, qty=100, do_not_save=True)
		bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 100, "inv_site": "Site 1"}])
		se.items[0].inventory_dimension_bundle = bundle
		self.assertRaises(InventoryDimensionNegativeStockError, se.submit)

		# Disable the check on the dimension -> the same issue now goes through.
		inv_dimension.reload()
		inv_dimension.db_set("validate_negative_stock", 0)
		clear_dimension_cache()

		se = make_stock_entry(item_code=item_code, source=warehouse, qty=100, do_not_save=True)
		bundle = make_inventory_dimension_bundle(item_code, warehouse, [{"qty": 100, "inv_site": "Site 1"}])
		se.items[0].inventory_dimension_bundle = bundle
		se.submit()
		self.assertEqual(se.docstatus, 1)

	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_negative_stock": 1})
	def test_negative_stock_per_dimension_method(self):
		"""Per Dimension: each dimension is validated independently (combination may be short)."""
		item_code = "Test ND Per Dimension Item"
		create_item(item_code)
		self._setup_two_dimensions("Per Dimension")
		warehouse = create_warehouse("ND Per Dimension Warehouse")

		# Balances after receipts: Site 1 = 30, Site 2 = 55, Rack 1 = 60, Rack 2 = 25.
		self._receive(
			item_code,
			warehouse,
			[("Site 1", "Rack 1", 30), ("Site 2", "Rack 1", 30), ("Site 2", "Rack 2", 25)],
		)

		# Issue 35 from Site 2 + Rack 1. Per dimension both are sufficient (55, 60) even though the
		# exact combination Site 2 + Rack 1 only has 30 -> allowed.
		se = make_stock_entry(item_code=item_code, source=warehouse, qty=35, do_not_save=True)
		bundle = make_inventory_dimension_bundle(
			item_code, warehouse, [{"qty": 35, "inv_site": "Site 2", "rack": "Rack 1"}]
		)
		se.items[0].inventory_dimension_bundle = bundle
		se.submit()
		self.assertEqual(se.docstatus, 1)

		# Issue 30 from Rack 2 (only 25 available on that single dimension) -> blocked.
		se = make_stock_entry(item_code=item_code, source=warehouse, qty=30, do_not_save=True)
		bundle = make_inventory_dimension_bundle(
			item_code, warehouse, [{"qty": 30, "inv_site": "Site 2", "rack": "Rack 2"}]
		)
		se.items[0].inventory_dimension_bundle = bundle
		self.assertRaises(InventoryDimensionNegativeStockError, se.submit)

	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_negative_stock": 1})
	def test_negative_stock_combined_method(self):
		"""Combined: the exact combination of all combined-method dimensions is validated together."""
		item_code = "Test ND Combined Item"
		create_item(item_code)
		self._setup_two_dimensions("Combined")
		warehouse = create_warehouse("ND Combined Warehouse")

		# Same balances: Site 2 = 55, Rack 1 = 60, but the combination Site 2 + Rack 1 = 30.
		self._receive(
			item_code,
			warehouse,
			[("Site 1", "Rack 1", 30), ("Site 2", "Rack 1", 30), ("Site 2", "Rack 2", 25)],
		)

		# Issue 35 from Site 2 + Rack 1: the combination only has 30 -> blocked.
		se = make_stock_entry(item_code=item_code, source=warehouse, qty=35, do_not_save=True)
		bundle = make_inventory_dimension_bundle(
			item_code, warehouse, [{"qty": 35, "inv_site": "Site 2", "rack": "Rack 1"}]
		)
		se.items[0].inventory_dimension_bundle = bundle
		self.assertRaises(InventoryDimensionNegativeStockError, se.submit)

		# Issue 30 from Site 2 + Rack 1 (exactly the combination balance) -> allowed.
		se = make_stock_entry(item_code=item_code, source=warehouse, qty=30, do_not_save=True)
		bundle = make_inventory_dimension_bundle(
			item_code, warehouse, [{"qty": 30, "inv_site": "Site 2", "rack": "Rack 1"}]
		)
		se.items[0].inventory_dimension_bundle = bundle
		se.submit()
		self.assertEqual(se.docstatus, 1)

	# ------------------------------------------------------------------ helpers

	def _setup_two_dimensions(self, method):
		for name, reference in [("Inv Site", "Inv Site"), ("Rack", "Rack")]:
			dimension = create_inventory_dimension(
				apply_to_all_doctypes=1,
				dimension_name=name,
				reference_document=reference,
				validate_negative_stock=1,
			)
			dimension.db_set("validate_negative_stock", 1)
			dimension.db_set("negative_stock_validation_method", method)
		clear_dimension_cache()

	def _receive(self, item_code, warehouse, allocations):
		for site, rack, qty in allocations:
			se = make_stock_entry(
				item_code=item_code, target=warehouse, qty=qty, basic_rate=10, do_not_save=True
			)
			bundle = make_inventory_dimension_bundle(
				item_code, warehouse, [{"qty": qty, "inv_site": site, "rack": rack}]
			)
			se.items[0].inventory_dimension_bundle = bundle
			se.submit()


def make_inventory_dimension_bundle(item_code, warehouse, entries):
	"""Build and save a draft Inventory Dimension Bundle (the dialog's job in the UI).

	``entries`` is a list of dicts: ``{"qty": <qty>, "<dimension_source_fieldname>": <value>, ...}``.
	"""
	company = frappe.db.get_value("Warehouse", warehouse, "company")

	doc = frappe.new_doc("Inventory Dimension Bundle")
	doc.company = company
	doc.item_code = item_code
	doc.warehouse = warehouse
	for entry in entries:
		row = {"qty": entry["qty"], "warehouse": entry.get("warehouse") or warehouse}
		for key, value in entry.items():
			if key not in ("qty", "warehouse"):
				row[key] = value
		doc.append("entries", row)

	doc.flags.ignore_permissions = True
	doc.save()
	return doc.name


def reset_inventory_dimension_flags():
	"""Clear ``reqd`` / ``validate_negative_stock`` on every dimension so leaked records from a
	committed Custom Field DDL cannot impose mandatory/negative-stock validation on other tests."""
	for name in frappe.get_all("Inventory Dimension", pluck="name"):
		frappe.db.set_value(
			"Inventory Dimension", name, {"reqd": 0, "validate_negative_stock": 0}, update_modified=False
		)
	clear_dimension_cache()


def clear_dimension_cache():
	"""Reset the per-request caches so dimension config changes are picked up mid-test.

	``get_inventory_dimensions`` / ``get_document_wise_inventory_dimensions`` are ``@request_cache``d;
	clear the request cache in place (it is a ``defaultdict(dict)``, so it must not be replaced).
	"""
	frappe.clear_cache(doctype="Inventory Dimension")
	if getattr(frappe.local, "request_cache", None) is not None:
		frappe.local.request_cache.clear()


def create_inventory_dimension(**args):
	args = frappe._dict(args)

	if frappe.db.exists("Inventory Dimension", args.dimension_name):
		return frappe.get_doc("Inventory Dimension", args.dimension_name)

	doc = frappe.new_doc("Inventory Dimension")
	doc.update(args)

	if not args.do_not_save:
		doc.insert(ignore_permissions=True)

	return doc
