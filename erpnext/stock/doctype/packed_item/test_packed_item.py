# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.utils import add_to_date, nowdate

from erpnext.selling.doctype.sales_order.mapper import make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import get_gl_entries
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


def create_product_bundle(
	quantities: list[int] | None = None, warehouse: str | None = None
) -> tuple[str, list[str]]:
	"""Get a new product_bundle for use in tests.

	Create 10x required stock if warehouse is specified.
	"""
	if not quantities:
		quantities = [2, 2]

	bundle = make_item(properties={"is_stock_item": 0}).name

	bundle_doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": bundle})

	components = []
	for qty in quantities:
		compoenent = make_item().name
		components.append(compoenent)
		bundle_doc.append("items", {"item_code": compoenent, "qty": qty})
		if warehouse:
			make_stock_entry(item=compoenent, to_warehouse=warehouse, qty=10 * qty, rate=100)

	bundle_doc.insert()
	bundle_doc.submit()

	return bundle, components


class TestPackedItem(ERPNextTestSuite):
	"Test impact on Packed Items table in various scenarios."

	def setUp(self) -> None:
		self.warehouse = "_Test Warehouse - _TC"

		self.bundle, self.bundle_items = create_product_bundle(warehouse=self.warehouse)
		self.bundle2, self.bundle2_items = create_product_bundle(warehouse=self.warehouse)

		self.normal_item = make_item().name

	def test_adding_bundle_item(self):
		"Test impact on packed items if bundle item row is added."
		so = make_sales_order(item_code=self.bundle, qty=1, do_not_submit=True)

		self.assertEqual(so.items[0].qty, 1)
		self.assertEqual(len(so.packed_items), 2)
		self.assertEqual(so.packed_items[0].item_code, self.bundle_items[0])
		self.assertEqual(so.packed_items[0].qty, 2)

	def test_updating_bundle_item(self):
		"Test impact on packed items if bundle item row is updated."
		so = make_sales_order(item_code=self.bundle, qty=1, do_not_submit=True)

		so.items[0].qty = 2  # change qty
		so.save()

		self.assertEqual(so.packed_items[0].qty, 4)
		self.assertEqual(so.packed_items[1].qty, 4)

		# change item code to non bundle item
		so.items[0].item_code = self.normal_item
		so.save()

		self.assertEqual(len(so.packed_items), 0)

	def test_item_and_packed_rows_record_bundle_version(self):
		"The item row and its packed items record the resolved Product Bundle version."
		from erpnext.selling.doctype.product_bundle.product_bundle import get_active_product_bundle

		version = get_active_product_bundle(self.bundle)
		self.assertTrue(version and version.startswith("PB-"))

		so = make_sales_order(item_code=self.bundle, qty=1, warehouse=self.warehouse)
		self.assertEqual(so.items[0].product_bundle, version)
		self.assertEqual(so.items[0].is_product_bundle, 1)
		self.assertEqual(len(so.packed_items), 2)
		for pi in so.packed_items:
			self.assertEqual(pi.product_bundle, version)

		# the version carries onto a Delivery Note mapped from the Sales Order
		dn = make_delivery_note(so.name)
		self.assertEqual(dn.items[0].product_bundle, version)
		for pi in dn.packed_items:
			self.assertEqual(pi.product_bundle, version)

	def test_clearing_version_keeps_bundle_flag_and_redefaults(self):
		"Clearing the version must not lose the bundle flag (keeps the field visible)."
		so = make_sales_order(item_code=self.bundle, qty=1, warehouse=self.warehouse, do_not_submit=True)
		version = so.items[0].product_bundle
		self.assertEqual(so.items[0].is_product_bundle, 1)

		# user blanks the version field
		so.items[0].product_bundle = None
		so.save()

		# the flag stays set (so depends_on keeps the field visible) and the value
		# re-defaults to the active version
		self.assertEqual(so.items[0].is_product_bundle, 1)
		self.assertEqual(so.items[0].product_bundle, version)

	def test_backfill_patch_stamps_existing_rows(self):
		"The backfill patch stamps the version on rows that predate the field."
		from erpnext.patches.v16_0.submit_existing_product_bundles import (
			stamp_versions_on_transactions as stamp_versions,
		)
		from erpnext.selling.doctype.product_bundle.product_bundle import get_active_product_bundle

		version = get_active_product_bundle(self.bundle)
		so = make_sales_order(item_code=self.bundle, qty=1, do_not_submit=True)

		# simulate pre-migration rows with no version recorded and no bundle flag
		frappe.db.set_value("Sales Order Item", so.items[0].name, "product_bundle", None)
		frappe.db.set_value("Sales Order Item", so.items[0].name, "is_product_bundle", 0)
		for pi in so.packed_items:
			frappe.db.set_value("Packed Item", pi.name, "product_bundle", None)

		stamp_versions()

		self.assertEqual(frappe.db.get_value("Sales Order Item", so.items[0].name, "product_bundle"), version)
		self.assertEqual(frappe.db.get_value("Sales Order Item", so.items[0].name, "is_product_bundle"), 1)
		for pi in so.packed_items:
			self.assertEqual(frappe.db.get_value("Packed Item", pi.name, "product_bundle"), version)

	def test_choosing_an_older_version_packs_its_components(self):
		"Default picks the active version; choosing an older version re-packs its components."
		from erpnext.selling.doctype.product_bundle.product_bundle import (
			get_active_product_bundle,
			make_new_version,
		)

		v1 = get_active_product_bundle(self.bundle)

		# new version with a different component becomes the active one
		new_component = make_item().name
		make_stock_entry(item=new_component, to_warehouse=self.warehouse, qty=50, rate=100)
		v2 = make_new_version(v1)
		v2.items = []
		v2.append("items", {"item_code": new_component, "qty": 1})
		v2.insert()
		v2.submit()
		self.assertEqual(get_active_product_bundle(self.bundle), v2.name)

		# default: the active version (v2) and its component
		so = make_sales_order(item_code=self.bundle, qty=1, warehouse=self.warehouse, do_not_submit=True)
		self.assertEqual(so.items[0].product_bundle, v2.name)
		self.assertEqual([pi.item_code for pi in so.packed_items], [new_component])

		# choose the older version -> its components are packed instead
		so.items[0].product_bundle = v1
		so.save()
		self.assertEqual(so.items[0].product_bundle, v1)
		self.assertEqual(sorted(pi.item_code for pi in so.packed_items), sorted(self.bundle_items))

	def test_disabled_bundle_blocks_transaction(self):
		"A row that explicitly references a disabled version cannot be saved."
		from erpnext.selling.doctype.product_bundle.product_bundle import get_active_product_bundle

		version = get_active_product_bundle(self.bundle)
		so = make_sales_order(item_code=self.bundle, qty=1, warehouse=self.warehouse, do_not_submit=True)
		self.assertEqual(so.items[0].product_bundle, version)

		frappe.db.set_value("Product Bundle", version, "disabled", 1)
		self.assertRaises(frappe.ValidationError, so.save)

	def test_disabled_bundle_is_not_packed(self):
		"Without an explicit version, a disabled bundle is not treated as a bundle at all."
		from erpnext.selling.doctype.product_bundle.product_bundle import get_active_product_bundle

		version = get_active_product_bundle(self.bundle2)
		frappe.db.set_value("Product Bundle", version, "disabled", 1)

		so = make_sales_order(item_code=self.bundle2, qty=1, warehouse=self.warehouse, do_not_submit=True)
		self.assertEqual(so.items[0].is_product_bundle, 0)
		self.assertFalse(so.items[0].product_bundle)
		self.assertFalse(so.get("packed_items"))

	def test_get_items_from_product_bundle_endpoint(self):
		"The buying dialog passes the chosen version by document name (legacy: parent item code)."
		import json

		from erpnext.selling.doctype.product_bundle.product_bundle import get_active_product_bundle
		from erpnext.stock.doctype.packed_item.packed_item import get_items_from_product_bundle

		ctx = {
			"quantity": 2,
			"doctype": "Purchase Order",
			"parenttype": "Purchase Order",
			"company": "_Test Company",
			"currency": "INR",
			"conversion_rate": 1,
			"transaction_date": nowdate(),
		}

		# by document name, as the buying dialog sends it (bundle names are PB-prefixed
		# since versioning, so they no longer double as the parent item code)
		version = get_active_product_bundle(self.bundle)
		items = get_items_from_product_bundle(json.dumps({"product_bundle": version, **ctx}))
		self.assertEqual(sorted(i.item_code for i in items), sorted(self.bundle_items))
		self.assertEqual([i.qty for i in items], [4, 4])

		# legacy contract: the parent item code resolves to its active version
		items = get_items_from_product_bundle(json.dumps({"item_code": self.bundle, **ctx}))
		self.assertEqual(sorted(i.item_code for i in items), sorted(self.bundle_items))

		# an unsubmitted version is rejected
		draft = frappe.get_doc(
			{
				"doctype": "Product Bundle",
				"new_item_code": make_item(properties={"is_stock_item": 0}).name,
				"items": [{"item_code": self.bundle_items[0], "qty": 1}],
			}
		).insert()
		self.assertRaises(
			frappe.ValidationError,
			get_items_from_product_bundle,
			json.dumps({"product_bundle": draft.name, **ctx}),
		)

		# a disabled version is rejected
		frappe.db.set_value("Product Bundle", version, "disabled", 1)
		self.addCleanup(frappe.db.set_value, "Product Bundle", version, "disabled", 0)
		self.assertRaises(
			frappe.ValidationError,
			get_items_from_product_bundle,
			json.dumps({"product_bundle": version, **ctx}),
		)

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	def test_recurring_bundle_item(self):
		"Test impact on packed items if same bundle item is added and removed."
		so_items = []
		for qty in [2, 4, 6, 8]:
			so_items.append(
				{"item_code": self.bundle, "qty": qty, "rate": 400, "warehouse": "_Test Warehouse - _TC"}
			)

		# create SO with recurring bundle item
		so = make_sales_order(item_list=so_items, do_not_submit=True)

		# check alternate rows for qty
		self.assertEqual(len(so.packed_items), 8)
		self.assertEqual(so.packed_items[1].item_code, self.bundle_items[1])
		self.assertEqual(so.packed_items[1].qty, 4)
		self.assertEqual(so.packed_items[3].qty, 8)
		self.assertEqual(so.packed_items[5].qty, 12)
		self.assertEqual(so.packed_items[7].qty, 16)

		# delete intermediate row (2nd)
		del so.items[1]
		so.save()

		# check alternate rows for qty
		self.assertEqual(len(so.packed_items), 6)
		self.assertEqual(so.packed_items[1].qty, 4)
		self.assertEqual(so.packed_items[3].qty, 12)
		self.assertEqual(so.packed_items[5].qty, 16)

		# delete last row
		del so.items[2]
		so.save()

		# check alternate rows for qty
		self.assertEqual(len(so.packed_items), 4)
		self.assertEqual(so.packed_items[1].qty, 4)
		self.assertEqual(so.packed_items[3].qty, 12)

	@ERPNextTestSuite.change_settings("Selling Settings", {"editable_bundle_item_rates": 1})
	def test_bundle_item_cumulative_price(self):
		"Test if Bundle Item rate is cumulative from packed items."
		so = make_sales_order(item_code=self.bundle, qty=2, do_not_submit=True)

		so.packed_items[0].rate = 150
		so.packed_items[1].rate = 200
		so.save()

		self.assertEqual(so.items[0].rate, 700)
		self.assertEqual(so.items[0].amount, 1400)

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	def test_newly_mapped_doc_packed_items(self):
		"Test impact on packed items in newly mapped DN from SO."
		so_items = []
		for qty in [2, 4]:
			so_items.append(
				{"item_code": self.bundle, "qty": qty, "rate": 400, "warehouse": "_Test Warehouse - _TC"}
			)

		# create SO with recurring bundle item
		so = make_sales_order(item_list=so_items)

		dn = make_delivery_note(so.name)
		dn.items[1].qty = 3  # change second row qty for inserting doc
		dn.save()

		self.assertEqual(len(dn.packed_items), 4)
		self.assertEqual(dn.packed_items[2].qty, 6)
		self.assertEqual(dn.packed_items[3].qty, 6)

	def test_reposting_packed_items(self):
		warehouse = "Stores - TCP1"
		company = "_Test Company with perpetual inventory"

		today = nowdate()
		yesterday = add_to_date(today, days=-1, as_string=True)

		for item in self.bundle_items:
			make_stock_entry(item_code=item, to_warehouse=warehouse, qty=10, rate=100, posting_date=today)

		so = make_sales_order(item_code=self.bundle, qty=1, company=company, warehouse=warehouse)

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		gles = get_gl_entries(dn.doctype, dn.name)
		credit_before_repost = sum(gle.credit for gle in gles)

		# backdated stock entry
		for item in self.bundle_items:
			make_stock_entry(item_code=item, to_warehouse=warehouse, qty=10, rate=200, posting_date=yesterday)

		# assert correct reposting
		gles = get_gl_entries(dn.doctype, dn.name)
		credit_after_reposting = sum(gle.credit for gle in gles)
		self.assertNotEqual(credit_before_repost, credit_after_reposting)
		self.assertAlmostEqual(credit_after_reposting, 2 * credit_before_repost)

	def assertReturns(self, original, returned):
		self.assertEqual(len(original), len(returned))

		def sort_function(p):
			return p.parent_item, p.item_code, p.qty

		for sent_item, returned_item in zip(
			sorted(original, key=sort_function), sorted(returned, key=sort_function), strict=False
		):
			self.assertEqual(sent_item.item_code, returned_item.item_code)
			self.assertEqual(sent_item.parent_item, returned_item.parent_item)
			self.assertEqual(sent_item.qty, -1 * returned_item.qty)

	def test_returning_full_bundles(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return

		item_list = [
			{
				"item_code": self.bundle,
				"warehouse": self.warehouse,
				"qty": 1,
				"rate": 100,
			},
			{
				"item_code": self.bundle2,
				"warehouse": self.warehouse,
				"qty": 1,
				"rate": 100,
			},
		]
		so = make_sales_order(item_list=item_list, warehouse=self.warehouse)

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		# create return
		dn_ret = make_sales_return(dn.name)
		dn_ret.save()
		dn_ret.submit()
		self.assertReturns(dn.packed_items, dn_ret.packed_items)

	def test_returning_partial_bundles(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return

		item_list = [
			{
				"item_code": self.bundle,
				"warehouse": self.warehouse,
				"qty": 1,
				"rate": 100,
			},
			{
				"item_code": self.bundle2,
				"warehouse": self.warehouse,
				"qty": 1,
				"rate": 100,
			},
		]
		so = make_sales_order(item_list=item_list, warehouse=self.warehouse)

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		# create return
		dn_ret = make_sales_return(dn.name)
		# remove bundle 2
		dn_ret.items.pop()

		dn_ret.save()
		dn_ret.submit()
		dn_ret.reload()

		self.assertTrue(all(d.parent_item == self.bundle for d in dn_ret.packed_items))

		expected_returns = [d for d in dn.packed_items if d.parent_item == self.bundle]
		self.assertReturns(expected_returns, dn_ret.packed_items)

	def test_returning_partial_bundle_qty(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return

		so = make_sales_order(item_code=self.bundle, warehouse=self.warehouse, qty=2)

		dn = make_delivery_note(so.name)
		dn.save()
		dn.submit()

		# create return
		dn_ret = make_sales_return(dn.name)
		# halve the qty
		dn_ret.items[0].qty = -1
		dn_ret.save()
		dn_ret.submit()

		expected_returns = dn.packed_items
		for d in expected_returns:
			d.qty /= 2
		self.assertReturns(expected_returns, dn_ret.packed_items)
