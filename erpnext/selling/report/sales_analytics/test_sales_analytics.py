# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.utils import flt

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.report.sales_analytics.sales_analytics import execute
from erpnext.tests.utils import ERPNextTestSuite

# Bootstrap masters reused as-is (see erpnext/tests/utils.py):
#   "_Test Customer" -> customer_group "_Test Customer Group", territory "_Test Territory"
#   "_Test Supplier" -> supplier_group "_Test Supplier Group" (child of "All Supplier Groups")
#   Sales Order.order_type defaults to "Sales" (reqd Select field)
COMPANY = "_Test Company"
CUSTOMER = "_Test Customer"
CUSTOMER_GROUP = "_Test Customer Group"
TERRITORY = "_Test Territory"
SUPPLIER = "_Test Supplier"
SUPPLIER_GROUP = "_Test Supplier Group"
FROM_DATE = "2019-04-01"
TO_DATE = "2019-06-30"


class TestSalesAnalytics(ERPNextTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		# Two submitted Sales Orders for the bootstrap customer inside the report window.
		# These roll up into the tree roots the converted tree/order-type queries build.
		self.orders = [
			make_sales_order(
				company=COMPANY,
				customer=CUSTOMER,
				qty=5,
				rate=100,
				transaction_date="2019-04-10",
			),
			make_sales_order(
				company=COMPANY,
				customer=CUSTOMER,
				qty=3,
				rate=100,
				transaction_date="2019-05-15",
			),
		]

	def _base_filters(self, **overrides):
		filters = {
			"doc_type": "Sales Order",
			"value_quantity": "Value",
			"range": "Monthly",
			"company": COMPANY,
			"from_date": FROM_DATE,
			"to_date": TO_DATE,
		}
		filters.update(overrides)
		return filters

	def _expected_value_total(self):
		return sum(flt(so.base_net_total) for so in self.orders)

	def _expected_qty_total(self):
		return sum(flt(so.total_qty) for so in self.orders)

	def _row_by_entity(self, data):
		return {row["entity"]: row for row in data}

	def test_customer_entity_filter(self):
		_columns, data, _message, chart, *_rest = execute(
			self._base_filters(tree_type="Customer", entity=[CUSTOMER], curves="all")
		)

		self.assertEqual({row["entity"] for row in data}, {CUSTOMER})
		self.assertAlmostEqual(data[0]["total"], self._expected_value_total(), places=2)
		self.assertEqual({dataset["name"] for dataset in chart["data"]["datasets"]}, {CUSTOMER})

	def test_parent_customer_group_filter_preserves_rollup(self):
		_columns, unfiltered_data, *_rest = execute(self._base_filters(tree_type="Customer Group"))
		_columns, filtered_data, *_rest = execute(
			self._base_filters(tree_type="Customer Group", entity=["All Customer Groups"])
		)

		unfiltered = self._row_by_entity(unfiltered_data)
		filtered = self._row_by_entity(filtered_data)
		self.assertEqual(set(filtered), {"All Customer Groups"})
		self.assertAlmostEqual(
			filtered["All Customer Groups"]["total"],
			unfiltered["All Customer Groups"]["total"],
			places=2,
		)

	def test_customer_group_entity_filter(self):
		_columns, unfiltered_data, *_rest = execute(self._base_filters(tree_type="Customer Group"))
		_columns, filtered_data, *_rest = execute(
			self._base_filters(tree_type="Customer Group", entity=[CUSTOMER_GROUP])
		)

		unfiltered = self._row_by_entity(unfiltered_data)
		filtered = self._row_by_entity(filtered_data)
		self.assertEqual(set(filtered), {CUSTOMER_GROUP})
		self.assertEqual(filtered[CUSTOMER_GROUP]["indent"], 0)
		self.assertAlmostEqual(
			filtered[CUSTOMER_GROUP]["total"], unfiltered[CUSTOMER_GROUP]["total"], places=2
		)

	def test_customer_group_tree_rolls_up_to_root(self):
		"""tree_type='Customer Group' drives get_groups (tree get_all ordered by lft)
		and get_rows_by_group, rolling child values up to the 'All Customer Groups' root."""
		columns, data, *_ = execute(self._base_filters(tree_type="Customer Group"))

		self.assertTrue(columns)
		self.assertTrue(data)

		rows = self._row_by_entity(data)
		# The whole tree is returned, so both the root and the customer's own group appear.
		self.assertIn("All Customer Groups", rows)
		self.assertIn(CUSTOMER_GROUP, rows)

		expected = self._expected_value_total()
		self.assertGreater(expected, 0)
		# Leaf group holds the orders; root receives the same total via roll-up.
		self.assertAlmostEqual(rows[CUSTOMER_GROUP]["total"], expected, places=2)
		self.assertAlmostEqual(rows["All Customer Groups"]["total"], expected, places=2)
		# Roots of a tree report sit at indent 0.
		self.assertEqual(rows["All Customer Groups"]["indent"], 0)

	def test_territory_tree_rolls_up_to_root(self):
		"""tree_type='Territory' exercises the same tree path against the Territory tree."""
		columns, data, *_ = execute(self._base_filters(tree_type="Territory"))

		self.assertTrue(columns)
		rows = self._row_by_entity(data)
		self.assertIn("All Territories", rows)
		self.assertIn(TERRITORY, rows)

		expected = self._expected_value_total()
		self.assertAlmostEqual(rows[TERRITORY]["total"], expected, places=2)
		self.assertAlmostEqual(rows["All Territories"]["total"], expected, places=2)

	def test_order_type_synthetic_tree(self):
		"""tree_type='Order Type' drives get_teams: distinct order_type rebuilt in Python
		under a synthetic 'Order Types' root, then rolled up via get_rows_by_group."""
		columns, data, _message, _chart, _extra, skip_total_row = execute(
			self._base_filters(tree_type="Order Type")
		)

		self.assertTrue(columns)
		rows = self._row_by_entity(data)
		# Synthetic root plus the default order_type the bootstrap Sales Orders carry.
		self.assertIn("Order Types", rows)
		self.assertIn("Sales", rows)
		self.assertEqual(rows["Order Types"]["indent"], 0)

		expected = self._expected_value_total()
		self.assertAlmostEqual(rows["Sales"]["total"], expected, places=2)
		self.assertAlmostEqual(rows["Order Types"]["total"], expected, places=2)
		# The 'Order Types' root already carries the grand total, so the framework total row is skipped.
		self.assertEqual(skip_total_row, 1)

	def _make_payment(self, **args):
		pe = create_payment_entry(**args)
		pe.posting_date = pe.reference_date = args.get("posting_date") or "2019-04-20"
		pe.save().submit()
		return pe

	def _payment_filters(self, **overrides):
		return self._base_filters(doc_type="Payment Entry", **overrides)

	def test_payment_entry_scopes_party_type_and_signs_refunds(self):
		"""doc_type='Payment Entry' must restrict each tree to its own party type and net refunds:
		Receive adds and Pay (a refund) subtracts for a customer, mirrored for suppliers."""
		base_customer = self._row_by_entity(execute(self._payment_filters(tree_type="Customer"))[1])
		base_supplier = self._row_by_entity(execute(self._payment_filters(tree_type="Supplier"))[1])
		base_cust_total = flt(base_customer.get(CUSTOMER, {}).get("total", 0.0))
		base_supp_total = flt(base_supplier.get(SUPPLIER, {}).get("total", 0.0))

		self._make_payment(
			payment_type="Receive",
			party_type="Customer",
			party=CUSTOMER,
			paid_from="Debtors - _TC",
			paid_to="_Test Bank - _TC",
			paid_amount=1000,
		)
		self._make_payment(
			payment_type="Pay",
			party_type="Customer",
			party=CUSTOMER,
			paid_from="_Test Bank - _TC",
			paid_to="Debtors - _TC",
			paid_amount=300,
			posting_date="2019-05-20",
		)
		self._make_payment(
			payment_type="Pay",
			party_type="Supplier",
			party=SUPPLIER,
			paid_from="_Test Bank - _TC",
			paid_to="Creditors - _TC",
			paid_amount=5000,
		)

		customer_rows = self._row_by_entity(execute(self._payment_filters(tree_type="Customer"))[1])
		self.assertNotIn(SUPPLIER, customer_rows)
		self.assertAlmostEqual(flt(customer_rows[CUSTOMER]["total"]) - base_cust_total, 1000 - 300, places=2)

		supplier_rows = self._row_by_entity(execute(self._payment_filters(tree_type="Supplier"))[1])
		self.assertNotIn(CUSTOMER, supplier_rows)
		self.assertAlmostEqual(flt(supplier_rows[SUPPLIER]["total"]) - base_supp_total, 5000, places=2)

	def test_order_type_leaf_rows_in_sorted_order(self):
		"""get_teams fetches distinct order_types; frappe drops the SQL ORDER BY for distinct queries on
		postgres, so the report sorts the order-type rows in python (key=str.casefold) to keep them in a
		deterministic, case-insensitive order identical on both engines."""
		for order_type in ("Shopping Cart", "Maintenance", "Sales"):  # created out of sorted order
			so = make_sales_order(
				company=COMPANY,
				customer=CUSTOMER,
				qty=1,
				rate=100,
				transaction_date="2019-04-12",
				do_not_submit=True,
			)
			so.order_type = order_type
			so.submit()

		columns, data, *_ = execute(self._base_filters(tree_type="Order Type"))

		mine = {"Sales", "Maintenance", "Shopping Cart"}
		leaves = [row["entity"] for row in data if row.get("entity") in mine]
		# the order-type rows must appear in casefold-sorted order on both engines
		self.assertEqual(leaves, sorted(leaves, key=str.casefold))
		self.assertEqual(set(leaves), mine)

	def test_customer_group_by_quantity(self):
		"""value_quantity='Quantity' switches the selected value column (total_qty)."""
		_columns, data, *_ = execute(
			self._base_filters(tree_type="Customer Group", value_quantity="Quantity")
		)

		rows = self._row_by_entity(data)
		self.assertIn(CUSTOMER_GROUP, rows)

		expected_qty = self._expected_qty_total()
		self.assertGreater(expected_qty, 0)
		self.assertAlmostEqual(rows[CUSTOMER_GROUP]["total"], expected_qty, places=2)
		self.assertAlmostEqual(rows["All Customer Groups"]["total"], expected_qty, places=2)

	def test_supplier_group_tree_maps_supplier_to_group(self):
		"""tree_type='Supplier Group' (doc_type='Purchase Order') exercises
		get_supplier_parent_child_map: the query selects 'supplier' as entity, then
		get_periodic_data remaps each supplier to its group via the parent->child map
		built by frappe.get_all('Supplier', ['name', 'supplier_group'], as_list=True).
		The group total then rolls up into the 'All Supplier Groups' root."""
		# Baseline the report before adding our Purchase Order so the assertion is
		# robust to any pre-existing rows in the historical window.
		base_filters = self._base_filters(tree_type="Supplier Group", doc_type="Purchase Order")
		_columns, base_data, *_ = execute(base_filters)
		base_rows = self._row_by_entity(base_data)
		base_group_total = flt(base_rows.get(SUPPLIER_GROUP, {}).get("total", 0.0))

		po = create_purchase_order(
			company=COMPANY,
			supplier=SUPPLIER,
			qty=4,
			rate=250,
			transaction_date="2019-04-10",
		)
		po_value = flt(po.base_net_total)
		self.assertGreater(po_value, 0)

		columns, data, *_ = execute(base_filters)

		self.assertTrue(columns)
		self.assertTrue(data)

		rows = self._row_by_entity(data)
		# The supplier was remapped to its group; both the leaf group and the tree
		# root appear as entities (no raw supplier name leaks into the output).
		self.assertIn(SUPPLIER_GROUP, rows)
		self.assertIn("All Supplier Groups", rows)
		self.assertNotIn(SUPPLIER, rows)
		# Roots of a tree report sit at indent 0.
		self.assertEqual(rows["All Supplier Groups"]["indent"], 0)

		# The new PO lands in the supplier's group via the parent->child map.
		self.assertAlmostEqual(rows[SUPPLIER_GROUP]["total"] - base_group_total, po_value, places=2)
		# Roll-up: the root aggregates every group, so it covers at least this PO.
		self.assertGreaterEqual(flt(rows["All Supplier Groups"]["total"]), po_value)
