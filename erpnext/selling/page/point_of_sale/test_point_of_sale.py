# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import random_string

from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.selling.page.point_of_sale.point_of_sale import get_items
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestPointOfSaleGetItems(ERPNextTestSuite):
	"""Covers the raw-SQL -> frappe.qb conversion of point_of_sale.get_items."""

	def setUp(self):
		super().setUp()
		# Reuse the bootstrap leaf item group; an item assigned directly to it
		# falls inside its own (lft, rgt) subtree, which is what get_items filters on.
		self.item_group = "_Test Item Group"

		# A non-stock sales item keeps get_stock_availability cheap (no Bin needed)
		# and keeps the item out of the hide_unavailable_items branch.
		self.item_code = "_Test POS Item " + random_string(10)
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": self.item_code,
				"item_name": self.item_code,
				"item_group": self.item_group,
				"stock_uom": "_Test UOM",
				"is_stock_item": 0,
				"is_sales_item": 1,
				"is_fixed_asset": 0,
				"has_variants": 0,
				"disabled": 0,
			}
		)
		item.insert()
		self.item = item

		# make_pos_profile builds "_Test POS Profile" (hide_unavailable_items unset,
		# no item_groups restriction). Rolled back by tearDown.
		self.pos_profile = make_pos_profile().name

	def _get_item_codes(self, search_term):
		result = get_items(
			start=0,
			page_length=100,
			price_list="Standard Selling",
			item_group=self.item_group,
			pos_profile=self.pos_profile,
			search_term=search_term,
		)
		# get_items returns {"items": [...]} when the qb query yields rows,
		# and a bare (empty) list when nothing matches.
		items = result["items"] if isinstance(result, dict) else result
		return [row.get("item_code") for row in items]

	def _make_stock_item(self):
		# Fresh stock item in the filtered item group so it passes the
		# item_group.isin(subquery) clause and reaches the Bin left-join.
		item_code = "_Test POS Stock Item " + random_string(10)
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": self.item_group,
				"stock_uom": "_Test UOM",
				"is_stock_item": 1,
				"is_sales_item": 1,
				"is_fixed_asset": 0,
				"has_variants": 0,
				"disabled": 0,
			}
		).insert()
		return item_code

	def test_matching_search_term_returns_item(self):
		# search_term matches Item.name / Item.item_name via the LIKE OR-condition;
		# scan_barcode finds nothing for this value, so the converted qb query runs.
		item_codes = self._get_item_codes(self.item_code)
		self.assertIn(self.item_code, item_codes)

	def test_non_matching_search_term_excludes_item(self):
		non_matching = "zzz_no_such_item_" + random_string(10)
		item_codes = self._get_item_codes(non_matching)
		self.assertNotIn(self.item_code, item_codes)

	def test_partial_search_term_matches_on_item_name(self):
		# A substring of the item code must still match (LIKE %term%),
		# proving the OR/LIKE clause survived the SQL->qb conversion.
		partial = self.item_code.split(" ")[-1]
		item_codes = self._get_item_codes(partial)
		self.assertIn(self.item_code, item_codes)

	def test_disabled_item_is_excluded(self):
		# disabled == 0 is part of the converted WHERE clause; flipping it
		# must drop the item even when the search term matches.
		frappe.db.set_value("Item", self.item_code, "disabled", 1)
		item_codes = self._get_item_codes(self.item_code)
		self.assertNotIn(self.item_code, item_codes)

	def test_pos_profile_item_group_restriction_returns_items(self):
		# get_item_groups() returns Item Group names that the callers parameterize via
		# item.item_group.isin(...) / frappe.get_all, which escapes them once. The names must be RAW;
		# pre-escaping them double-escaped to `item_group IN ('''X''')`, so a POS Profile restricting
		# item groups matched nothing and returned ZERO items on both engines.
		from erpnext.accounts.doctype.pos_profile.pos_profile import get_item_groups

		restricted = make_pos_profile(name="_Test POS Profile IG Restricted")
		restricted.append("item_groups", {"item_group": self.item_group})
		restricted.save()

		# the helper must hand back the real (raw) group name, not an escaped literal
		self.assertIn(self.item_group, get_item_groups(restricted.name))

		# end-to-end: the restricted profile must still surface its in-group items
		result = get_items(
			start=0,
			page_length=100,
			price_list="Standard Selling",
			item_group=self.item_group,
			pos_profile=restricted.name,
			search_term="",
		)
		items = result["items"] if isinstance(result, dict) else result
		self.assertIn(self.item_code, [row.get("item_code") for row in items])

	def test_non_sales_item_is_excluded(self):
		# is_sales_item == 1 is part of the converted WHERE clause.
		frappe.db.set_value("Item", self.item_code, "is_sales_item", 0)
		item_codes = self._get_item_codes(self.item_code)
		self.assertNotIn(self.item_code, item_codes)

	def test_hide_unavailable_items_filters_on_bin_actual_qty(self):
		# Covers the hide_unavailable_items branch: the Bin left-join only keeps a
		# stock item when bin.warehouse == profile warehouse AND bin.actual_qty > 0.
		# A second stock item with no Bin row (no stock) must be hidden.
		warehouse = frappe.db.get_value("POS Profile", self.pos_profile, "warehouse")
		frappe.db.set_value("POS Profile", self.pos_profile, "hide_unavailable_items", 1)

		in_stock_item = self._make_stock_item()
		out_of_stock_item = self._make_stock_item()

		# Material Receipt gives in_stock_item actual_qty > 0 in the profile warehouse;
		# out_of_stock_item gets no Bin row at all.
		make_stock_entry(item_code=in_stock_item, target=warehouse, qty=5, basic_rate=100)

		# Sanity-check the precondition the branch keys off of.
		self.assertGreater(
			frappe.db.get_value("Bin", {"item_code": in_stock_item, "warehouse": warehouse}, "actual_qty")
			or 0,
			0,
		)
		self.assertFalse(frappe.db.exists("Bin", {"item_code": out_of_stock_item}))

		in_stock_codes = self._get_item_codes(in_stock_item)
		self.assertIn(in_stock_item, in_stock_codes)

		out_of_stock_codes = self._get_item_codes(out_of_stock_item)
		self.assertNotIn(out_of_stock_item, out_of_stock_codes)
