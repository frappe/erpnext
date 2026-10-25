# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.report.bom_search.bom_search import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestBomSearch(ERPNextTestSuite):
	def test_only_submitted_documents_are_returned(self):
		from erpnext.stock.doctype.item.test_item import make_item

		bundle_item = make_item(properties={"is_stock_item": 0}).name
		for doctype, fields in (
			("BOM", {"item": "_Test FG Item", "company": "_Test Company", "currency": "INR"}),
			("Product Bundle", {"new_item_code": bundle_item}),
		):
			doc = frappe.get_doc({"doctype": doctype, **fields})
			doc.append("items", {"item_code": "_Test Item", "qty": 1})
			doc.insert()

			for status in (0, 1, 2):
				if status == 1:
					doc.submit()
				elif status == 2:
					doc.cancel()

				for search_sub_assemblies in (0, 1):
					with self.subTest(doctype=doctype, status=status, exploded=search_sub_assemblies):
						rows = self.run_report(
							item1="_Test Item", search_sub_assemblies=search_sub_assemblies
						)
						self.assertEqual((doc.name, doctype) in rows, status == 1)

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
		sub_assembly = "_Test FG Item"  # its default BOM contains _Test Item
		finished_good = "_Test FG Item 2"

		# top-level BOM uses the sub-assembly (it does NOT list the raw material directly).
		# the bootstrap sub-assembly BOM is in USD, so match its currency.
		top_bom = frappe.get_doc(
			doctype="BOM", item=finished_good, company="_Test Company", currency="USD", conversion_rate=1
		)
		top_bom.append("items", {"item_code": sub_assembly, "qty": 1})
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
