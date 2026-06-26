# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt, random_string

from erpnext.selling.report.available_stock_for_packing_items.available_stock_for_packing_items import (
	execute,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "_Test Warehouse - _TC"


class TestAvailableStockForPackingItems(ERPNextTestSuite):
	"""Cover the MIN-over-components / per-warehouse logic of the rewritten report.

	The report computes, for each (active Product Bundle, warehouse):
	    packable bundles = MIN over components of (Bin.projected_qty / qty per bundle)
	and drops rows where that MIN is 0. We use freshly created component items so the
	only Bin rows and the only bundle referencing them are the ones built here -- this
	keeps the asserted number exact and makes the test fail if the conversion breaks.
	"""

	def make_component(self):
		return make_item(
			f"_Test Packing Component {random_string(10)}",
			{"is_stock_item": 1},
		).name

	def make_bundle_parent(self):
		return make_item(
			f"_Test Packing Bundle {random_string(10)}",
			{"is_stock_item": 0, "is_sales_item": 1},
		).name

	def set_bin_projected_qty(self, item_code, warehouse, projected_qty):
		"""Create (if needed) the Bin for (item, warehouse) and pin projected_qty.

		Bin recomputes projected_qty from actual/ordered/... on save, so after the
		Bin exists we force the exact value with db.set_value (no controller recompute).
		This is precisely the column the report reads back.
		"""
		name = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse})
		if not name:
			bin_doc = frappe.get_doc(doctype="Bin", item_code=item_code, warehouse=warehouse)
			bin_doc.flags.ignore_permissions = True
			bin_doc.insert()
			name = bin_doc.name
		frappe.db.set_value("Bin", name, "projected_qty", projected_qty)
		return name

	def make_active_bundle(self, parent, components):
		"""components: list of (item_code, qty_per_bundle). Submitted => is_active, docstatus 1."""
		bundle = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": parent})
		for item_code, qty in components:
			bundle.append("items", {"item_code": item_code, "qty": qty})
		bundle.insert()
		bundle.submit()
		return bundle

	def report_rows_for(self, parent):
		"""Run the report and return the data rows whose Item Code == parent (drops Total rows)."""
		_columns, data = execute(filters=None)
		return [row for row in data if row and row[0] == parent]

	def test_min_over_components_binds(self):
		comp_a = self.make_component()
		comp_b = self.make_component()
		parent = self.make_bundle_parent()

		# comp_a: 2 per bundle, projected 10 -> 5 bundles; comp_b: 1 per bundle, projected 3 -> 3 bundles
		self.set_bin_projected_qty(comp_a, WAREHOUSE, 10)
		self.set_bin_projected_qty(comp_b, WAREHOUSE, 3)
		self.make_active_bundle(parent, [(comp_a, 2), (comp_b, 1)])

		rows = self.report_rows_for(parent)

		# Exactly one (bundle, warehouse) row, and packable == MIN(5, 3) == 3.
		self.assertEqual(len(rows), 1)
		row = rows[0]
		# row shape: [item_code, item_name, description, uom, warehouse, quantity]
		self.assertEqual(row[4], WAREHOUSE)
		self.assertEqual(flt(row[5]), 3.0)

	def test_per_warehouse_grouping(self):
		comp_a = self.make_component()
		comp_b = self.make_component()
		parent = self.make_bundle_parent()

		other_wh = self.make_secondary_warehouse()

		# _Test Warehouse: comp_a 8/2=4, comp_b 6/1=6 -> MIN 4
		self.set_bin_projected_qty(comp_a, WAREHOUSE, 8)
		self.set_bin_projected_qty(comp_b, WAREHOUSE, 6)
		# other warehouse: comp_a 4/2=2, comp_b 9/1=9 -> MIN 2
		self.set_bin_projected_qty(comp_a, other_wh, 4)
		self.set_bin_projected_qty(comp_b, other_wh, 9)

		self.make_active_bundle(parent, [(comp_a, 2), (comp_b, 1)])

		rows = self.report_rows_for(parent)
		by_warehouse = {row[4]: flt(row[5]) for row in rows}

		self.assertEqual(by_warehouse.get(WAREHOUSE), 4.0)
		self.assertEqual(by_warehouse.get(other_wh), 2.0)

	def test_starved_component_drops_row(self):
		comp_a = self.make_component()
		comp_b = self.make_component()
		parent = self.make_bundle_parent()

		# comp_a is plentiful, comp_b is absent in the warehouse (no Bin) -> MIN == 0 -> dropped.
		self.set_bin_projected_qty(comp_a, WAREHOUSE, 50)
		self.make_active_bundle(parent, [(comp_a, 2), (comp_b, 1)])

		self.assertEqual(self.report_rows_for(parent), [])

	def test_zero_projected_component_drops_row(self):
		comp_a = self.make_component()
		comp_b = self.make_component()
		parent = self.make_bundle_parent()

		# comp_b present but with projected 0 -> 0/1 == 0 -> MIN == 0 -> row dropped.
		self.set_bin_projected_qty(comp_a, WAREHOUSE, 20)
		self.set_bin_projected_qty(comp_b, WAREHOUSE, 0)
		self.make_active_bundle(parent, [(comp_a, 2), (comp_b, 1)])

		self.assertEqual(self.report_rows_for(parent), [])

	def test_inactive_bundle_excluded(self):
		comp_a = self.make_component()
		parent = self.make_bundle_parent()

		self.set_bin_projected_qty(comp_a, WAREHOUSE, 10)
		bundle = self.make_active_bundle(parent, [(comp_a, 1)])

		# Sanity: while active it shows up...
		self.assertTrue(self.report_rows_for(parent))

		# ...and disappears once cancelled (is_active cleared, docstatus 2).
		bundle.cancel()
		self.assertEqual(self.report_rows_for(parent), [])

	def make_secondary_warehouse(self):
		"""A second leaf warehouse under _Test Company so two warehouses can be asserted."""
		name = f"_Test Pack WH {random_string(6)}"
		full_name = f"{name} - _TC"
		if frappe.db.exists("Warehouse", full_name):
			return full_name
		wh = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": name,
				"company": "_Test Company",
			}
		)
		wh.insert()
		return wh.name
