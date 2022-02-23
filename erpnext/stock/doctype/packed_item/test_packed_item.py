# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestCase, change_settings


class TestPackedItem(ERPNextTestCase):
	"Test impact on Packed Items table in various scenarios."
	@classmethod
	def setUpClass(cls) -> None:
		make_item("_Test Product Bundle X", {"is_stock_item": 0})
		make_item("_Test Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Bundle Item 2", {"is_stock_item": 1})
		make_item("_Test Normal Stock Item", {"is_stock_item": 1})

		make_product_bundle(
			"_Test Product Bundle X",
			["_Test Bundle Item 1", "_Test Bundle Item 2"],
			qty=2
		)

	def test_adding_bundle_item(self):
		"Test impact on packed items if bundle item row is added."
		so = make_sales_order(item_code = "_Test Product Bundle X", qty=1,
			do_not_submit=True)

		self.assertEqual(so.items[0].qty, 1)
		self.assertEqual(len(so.packed_items), 2)
		self.assertEqual(so.packed_items[0].item_code, "_Test Bundle Item 1")
		self.assertEqual(so.packed_items[0].qty, 2)

	def test_updating_bundle_item(self):
		"Test impact on packed items if bundle item row is updated."
		so = make_sales_order(item_code = "_Test Product Bundle X", qty=1,
			do_not_submit=True)

		so.items[0].qty = 2 # change qty
		so.save()

		self.assertEqual(so.packed_items[0].qty, 4)
		self.assertEqual(so.packed_items[1].qty, 4)

		# change item code to non bundle item
		so.items[0].item_code = "_Test Normal Stock Item"
		so.save()

		self.assertEqual(len(so.packed_items), 0)

	def test_recurring_bundle_item(self):
		"Test impact on packed items if same bundle item is added and removed."
		so_items = []
		for qty in [2, 4, 6, 8]:
			so_items.append({
				"item_code": "_Test Product Bundle X",
				"qty": qty,
				"rate": 400,
				"warehouse": "_Test Warehouse - _TC"
			})

		# create SO with recurring bundle item
		so = make_sales_order(item_list=so_items, do_not_submit=True)

		# check alternate rows for qty
		self.assertEqual(len(so.packed_items), 8)
		self.assertEqual(so.packed_items[1].item_code, "_Test Bundle Item 2")
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
		so = make_sales_order(item_code = "_Test Product Bundle X", qty=2,
			do_not_submit=True)

		so.packed_items[0].rate = 150
		so.packed_items[1].rate = 200
		so.save()

		self.assertEqual(so.items[0].rate, 350)
		self.assertEqual(so.items[0].amount, 700)

	def test_newly_mapped_doc_packed_items(self):
		"Test impact on packed items in newly mapped DN from SO."
		so_items = []
		for qty in [2, 4]:
			so_items.append({
				"item_code": "_Test Product Bundle X",
				"qty": qty,
				"rate": 400,
				"warehouse": "_Test Warehouse - _TC"
			})

		# create SO with recurring bundle item
		so = make_sales_order(item_list=so_items)

		dn = make_delivery_note(so.name)
		dn.items[1].qty = 3 # change second row qty for inserting doc
		dn.save()

		self.assertEqual(len(dn.packed_items), 4)
		self.assertEqual(dn.packed_items[2].qty, 6)
		self.assertEqual(dn.packed_items[3].qty, 6)