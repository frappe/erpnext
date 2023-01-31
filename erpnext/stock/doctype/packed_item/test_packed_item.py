# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from typing import List, Optional, Tuple

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_to_date, nowdate

from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import get_gl_entries
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


def create_product_bundle(
	quantities: Optional[List[int]] = None, warehouse: Optional[str] = None
) -> Tuple[str, List[str]]:
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

	return bundle, components


class TestPackedItem(FrappeTestCase):
	"Test impact on Packed Items table in various scenarios."

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		cls.warehouse = "_Test Warehouse - _TC"

		cls.bundle, cls.bundle_items = create_product_bundle(warehouse=cls.warehouse)
		cls.bundle2, cls.bundle2_items = create_product_bundle(warehouse=cls.warehouse)

		cls.normal_item = make_item().name

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

	@change_settings("Selling Settings", {"editable_bundle_item_rates": 1})
	def test_bundle_item_cumulative_price(self):
		"Test if Bundle Item rate is cumulative from packed items."
		so = make_sales_order(item_code=self.bundle, qty=2, do_not_submit=True)

		so.packed_items[0].rate = 150
		so.packed_items[1].rate = 200
		so.save()

		self.assertEqual(so.items[0].rate, 700)
		self.assertEqual(so.items[0].amount, 1400)

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
			make_stock_entry(
				item_code=item, to_warehouse=warehouse, qty=10, rate=200, posting_date=yesterday
			)

		# assert correct reposting
		gles = get_gl_entries(dn.doctype, dn.name)
		credit_after_reposting = sum(gle.credit for gle in gles)
		self.assertNotEqual(credit_before_repost, credit_after_reposting)
		self.assertAlmostEqual(credit_after_reposting, 2 * credit_before_repost)

	def assertReturns(self, original, returned):
		self.assertEqual(len(original), len(returned))

		sort_function = lambda p: (p.parent_item, p.item_code, p.qty)

		for sent, returned in zip(
			sorted(original, key=sort_function), sorted(returned, key=sort_function)
		):
			self.assertEqual(sent.item_code, returned.item_code)
			self.assertEqual(sent.parent_item, returned.parent_item)
			self.assertEqual(sent.qty, -1 * returned.qty)

	def test_returning_full_bundles(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

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
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

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
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

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
