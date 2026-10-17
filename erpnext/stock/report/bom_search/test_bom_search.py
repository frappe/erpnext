# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.report.bom_search.bom_search import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestBomSearch(ERPNextTestSuite):
	def test_only_submitted_boms_are_returned(self):
		bom = frappe.get_doc(doctype="BOM", item="_Test FG Item", company="_Test Company", currency="INR")
		bom.append("items", {"item_code": "_Test Item", "qty": 1})
		bom.insert()

		for status in (0, 1, 2):
			if status == 1:
				bom.submit()
			elif status == 2:
				bom.cancel()

			for exploded in (0, 1):
				with self.subTest(status=status, exploded=exploded):
					rows = self.run_report(item1="_Test Item", search_sub_assemblies=exploded)
					self.assertEqual((bom.name, "BOM") in rows, status == 1)

	def test_non_submittable_product_bundle_is_returned(self):
		from erpnext.stock.doctype.item.test_item import make_item

		bundle = frappe.get_doc(
			doctype="Product Bundle", new_item_code=make_item(properties={"is_stock_item": 0}).name
		)
		bundle.append("items", {"item_code": "_Test Item", "qty": 1})
		bundle.insert()
		for exploded in (0, 1):
			with self.subTest(exploded=exploded):
				rows = self.run_report(item1="_Test Item", search_sub_assemblies=exploded)
				self.assertIn((bundle.name, "Product Bundle"), rows)

	def run_report(self, **extra):
		filters = frappe._dict({"search_sub_assemblies": 0})
		filters.update(extra)
		return execute(filters)[1]

	def test_bom_found_by_contained_item(self):
		raw_material = "_Test Item"
		finished_good = "_Test FG Item"

		bom = frappe.get_doc(doctype="BOM", item=finished_good, company="_Test Company", currency="INR")
		bom.append("items", {"item_code": raw_material, "qty": 1})
		bom.insert()
		bom.submit()

		rows = self.run_report(item1=raw_material)
		bom_names = [row[0] for row in rows]
		self.assertIn(bom.name, bom_names)

	def test_search_sub_assemblies_finds_top_level_bom(self):
		raw_material = "_Test Item"
		sub_assembly = "_Test FG Item"
		finished_good = "_Test FG Item 2"

		sub_bom = frappe.get_doc(doctype="BOM", item=sub_assembly, company="_Test Company", currency="INR")
		sub_bom.append("items", {"item_code": raw_material, "qty": 1})
		sub_bom.insert()
		sub_bom.submit()
		top_bom = frappe.get_doc(doctype="BOM", item=finished_good, company="_Test Company", currency="INR")
		top_bom.append("items", {"item_code": sub_assembly, "qty": 1, "bom_no": sub_bom.name})
		top_bom.insert()
		top_bom.submit()

		# search_sub_assemblies=1 scans the exploded tree, so the raw material buried in the
		# sub-assembly surfaces the top-level BOM
		deep = [row[0] for row in self.run_report(search_sub_assemblies=1, item1=raw_material)]
		self.assertIn(top_bom.name, deep)

		for filters in (
			{"item1": sub_assembly},
			{"item1": sub_assembly, "item2": raw_material},
		):
			with self.subTest(filters=filters):
				rows = self.run_report(search_sub_assemblies=1, **filters)
				self.assertEqual(rows.count((top_bom.name, "BOM")), 1)

		# search_sub_assemblies=0 scans only direct BOM Items, so the top-level BOM (which lists
		# the sub-assembly, not the raw material) is not returned for the raw material
		direct = [row[0] for row in self.run_report(search_sub_assemblies=0, item1=raw_material)]
		self.assertNotIn(top_bom.name, direct)
