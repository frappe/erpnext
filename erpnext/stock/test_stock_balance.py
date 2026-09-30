# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from erpnext.stock.stock_balance import get_indented_qty, get_reserved_qty
from erpnext.tests.utils import ERPNextTestSuite


class TestStockBalance(ERPNextTestSuite):
	def test_get_reserved_qty_for_sales_order_item(self):
		"""get_reserved_qty (converted from a UNION of correlated subqueries) must add a submitted
		Sales Order's open qty for the direct SO-item branch. No delivery, so it stays clear of the
		unrelated #39 SLE-repost path and runs on Postgres."""
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		item_code, warehouse = "_Test Item", "_Test Warehouse - _TC"
		before = get_reserved_qty(item_code, warehouse)

		make_sales_order(item_code=item_code, qty=10, warehouse=warehouse)  # submitted

		self.assertEqual(get_reserved_qty(item_code, warehouse), before + 10)

	def test_get_reserved_qty_for_packed_bundle_item(self):
		"""The packed-item branch of get_reserved_qty (the correlated-subquery -> inner_join rewrite)
		must reserve the bundle component qty against an open Sales Order: 2 bundles x 3 per bundle = 6."""
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item

		warehouse = "_Test Warehouse - _TC"
		bundle = make_item(properties={"is_stock_item": 0}).name
		component = make_item(properties={"is_stock_item": 1}).name
		make_product_bundle(bundle, [component], qty=3)

		before = get_reserved_qty(component, warehouse)

		make_sales_order(item_code=bundle, qty=2, warehouse=warehouse)  # 2 x 3 = 6 component packed

		self.assertEqual(get_reserved_qty(component, warehouse), before + 6)

	def test_get_indented_qty_for_material_request(self):
		"""get_indented_qty inward branch (comma-join -> qb inner_join) must reflect a submitted
		Purchase Material Request's not-yet-ordered qty."""
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		item_code, warehouse = "_Test Item", "_Test Warehouse - _TC"
		before = get_indented_qty(item_code, warehouse)

		make_material_request(item_code=item_code, qty=7, warehouse=warehouse)  # Purchase, submitted

		self.assertEqual(get_indented_qty(item_code, warehouse), before + 7)
