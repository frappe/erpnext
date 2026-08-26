# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.report.purchase_analytics.purchase_analytics import execute
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
SUPPLIER = "_Test Supplier"
SUPPLIER_GROUP = "_Test Supplier Group"
# A historical window that ordinary test fixtures don't post into.
FROM_DATE = "2019-04-01"
TO_DATE = "2019-06-30"


class TestPurchaseAnalytics(ERPNextTestSuite):
	"""purchase_analytics reuses the shared Analytics engine; these tests lock its
	wiring (doc_type=Purchase Order) across the Supplier Group / Item Group trees."""

	def setUp(self):
		frappe.set_user("Administrator")

	def _filters(self, **overrides):
		filters = {
			"doc_type": "Purchase Order",
			"value_quantity": "Value",
			"range": "Monthly",
			"company": COMPANY,
			"from_date": FROM_DATE,
			"to_date": TO_DATE,
		}
		filters.update(overrides)
		return frappe._dict(filters)

	def _rows(self, filters):
		return {row["entity"]: row for row in execute(filters)[1]}

	def make_po(self, qty=4, rate=250):
		return create_purchase_order(
			company=COMPANY, supplier=SUPPLIER, qty=qty, rate=rate, transaction_date="2019-04-10"
		)

	def test_supplier_entity_filter(self):
		filters = self._filters(tree_type="Supplier", entity=[SUPPLIER], curves="all")
		base_total = flt(self._rows(filters).get(SUPPLIER, {}).get("total", 0.0))

		po = self.make_po()
		columns, data, _message, chart, *_rest = execute(filters)

		self.assertTrue(columns)
		self.assertEqual({row["entity"] for row in data}, {SUPPLIER})
		self.assertAlmostEqual(data[0]["total"] - base_total, flt(po.base_net_total), places=2)

		supplier_name = frappe.db.get_value("Supplier", SUPPLIER, "supplier_name")
		self.assertEqual({dataset["name"] for dataset in chart["data"]["datasets"]}, {supplier_name})

	def test_parent_supplier_group_filter_preserves_rollup(self):
		self.make_po()
		filters = self._filters(tree_type="Supplier Group")
		unfiltered = self._rows(filters)
		filtered = self._rows(self._filters(tree_type="Supplier Group", entity=["All Supplier Groups"]))

		self.assertEqual(set(filtered), {"All Supplier Groups"})
		self.assertAlmostEqual(
			filtered["All Supplier Groups"]["total"],
			unfiltered["All Supplier Groups"]["total"],
			places=2,
		)

	def test_supplier_group_entity_filter(self):
		self.make_po()
		unfiltered = self._rows(self._filters(tree_type="Supplier Group"))
		filtered = self._rows(self._filters(tree_type="Supplier Group", entity=[SUPPLIER_GROUP]))

		self.assertEqual(set(filtered), {SUPPLIER_GROUP})
		self.assertEqual(filtered[SUPPLIER_GROUP]["indent"], 0)
		self.assertAlmostEqual(
			filtered[SUPPLIER_GROUP]["total"], unfiltered[SUPPLIER_GROUP]["total"], places=2
		)

	def test_supplier_group_tree_rolls_up_to_root(self):
		filters = self._filters(tree_type="Supplier Group")
		base = self._rows(filters)
		base_group = flt(base.get(SUPPLIER_GROUP, {}).get("total", 0.0))

		po = self.make_po(qty=4, rate=250)
		rows = self._rows(filters)

		# supplier is remapped to its group; the root sits at indent 0
		self.assertIn(SUPPLIER_GROUP, rows)
		self.assertIn("All Supplier Groups", rows)
		self.assertNotIn(SUPPLIER, rows)
		self.assertEqual(rows["All Supplier Groups"]["indent"], 0)

		self.assertAlmostEqual(rows[SUPPLIER_GROUP]["total"] - base_group, flt(po.base_net_total), places=2)
		self.assertGreaterEqual(flt(rows["All Supplier Groups"]["total"]), flt(po.base_net_total))

	def test_item_group_tree_rolls_up_to_root(self):
		item_group = frappe.db.get_value("Item", "_Test Item", "item_group")
		filters = self._filters(tree_type="Item Group")
		base = self._rows(filters)
		base_group = flt(base.get(item_group, {}).get("total", 0.0))

		po = self.make_po(qty=4, rate=250)
		rows = self._rows(filters)

		self.assertIn(item_group, rows)
		self.assertIn("All Item Groups", rows)
		# the raw item code must not leak as its own entity; the root sits at indent 0
		self.assertNotIn("_Test Item", rows)
		self.assertEqual(rows["All Item Groups"]["indent"], 0)
		self.assertAlmostEqual(rows[item_group]["total"] - base_group, flt(po.base_net_total), places=2)
		self.assertGreaterEqual(flt(rows["All Item Groups"]["total"]), flt(po.base_net_total))

	def test_supplier_group_by_quantity(self):
		filters = self._filters(tree_type="Supplier Group", value_quantity="Quantity")
		base = self._rows(filters)
		base_qty = flt(base.get(SUPPLIER_GROUP, {}).get("total", 0.0))
		base_root_qty = flt(base.get("All Supplier Groups", {}).get("total", 0.0))

		po = self.make_po(qty=7, rate=100)
		rows = self._rows(filters)

		self.assertAlmostEqual(rows[SUPPLIER_GROUP]["total"] - base_qty, flt(po.total_qty), places=2)
		# the quantity must roll up to the root too, not just the leaf group
		self.assertAlmostEqual(
			rows["All Supplier Groups"]["total"] - base_root_qty, flt(po.total_qty), places=2
		)
