from unittest.mock import patch

import frappe

from erpnext.controllers import queries
from erpnext.stock.doctype.item.item_search import ItemSearch, build_match_query
from erpnext.tests.utils import ERPNextTestSuite


class TestBuildMatchQuery(ERPNextTestSuite):
	def test_quotes_the_term(self):
		self.assertEqual(build_match_query("widget"), '"widget"')

	def test_escapes_embedded_quotes(self):
		self.assertEqual(build_match_query('say "hi"'), '"say ""hi"""')

	def test_skips_terms_shorter_than_a_trigram(self):
		for txt in ("", "a", "ab", "  b "):
			self.assertIsNone(build_match_query(txt), txt)

	def test_splits_on_like_wildcards(self):
		"""A wildcard splits the term, the fragments narrow, and the caller rechecks with LIKE."""
		self.assertEqual(build_match_query("RAW_MAT_000123"), '"RAW" AND "MAT" AND "000123"')
		self.assertEqual(build_match_query("abc%def"), '"abc" AND "def"')

	def test_skips_terms_with_no_usable_fragment(self):
		for txt in ("ab%cd", "ab_cd", "a%b%c"):
			self.assertIsNone(build_match_query(txt), txt)

	def test_skips_escaped_terms(self):
		"""Backslash escapes the next LIKE wildcard, so the split would be wrong."""
		self.assertIsNone(build_match_query("ab\\_cd"))


class TestItemSearchIndex(ERPNextTestSuite):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.enabled = patch.object(ItemSearch, "is_search_enabled", return_value=True)
		cls.enabled.start()
		cls.search = ItemSearch()
		if cls.search.index_exists():
			cls.search.drop_index()
		cls.search.build_index()

	@classmethod
	def tearDownClass(cls):
		cls.search.drop_index()
		cls.enabled.stop()
		super().tearDownClass()

	def test_index_uses_the_trigram_tokenizer(self):
		self.assertEqual(self.search.schema["tokenizer"], "trigram")

	def test_candidates_are_a_superset_of_the_scan(self):
		"""The query re-filters, so extra candidates are safe but missing ones are not."""
		for txt in ("Test", "Item", "est", "_Test"):
			candidates = self.search.get_candidate_item_codes(txt)
			self.assertIsNotNone(candidates, txt)
			matched = frappe.get_all(
				"Item",
				filters={"name": ("like", f"%{txt}%"), "disabled": 0, "has_variants": 0},
				pluck="name",
			)
			self.assertTrue(set(matched) <= set(candidates), txt)

	def test_item_query_output_is_unchanged(self):
		cases = [
			("Test", None),
			("Item", None),
			("EST", None),
			("Test", {"is_stock_item": 1}),
			("_Test", None),
			("ab", None),
			("%est", None),
			("", None),
		]
		for txt, filters in cases:
			with self.subTest(txt=txt, filters=filters):
				self.assertEqual(self.run_query(txt, filters), self.run_query(txt, filters, False))

	def test_underscore_in_the_term_still_narrows(self):
		"""_ is a LIKE wildcard, but the fragments around it are still indexable."""
		candidates = self.search.get_candidate_item_codes("_Test Item")
		self.assertIsNotNone(candidates)
		matched = frappe.get_all(
			"Item",
			filters={"name": ("like", "%_Test Item%"), "disabled": 0, "has_variants": 0},
			pluck="name",
		)
		self.assertTrue(set(matched) <= set(candidates))

	def test_no_candidates_returns_no_rows(self):
		"""An empty candidate list must not reach the query, IN () is a syntax error."""
		with patch.object(queries, "get_item_search_candidates", return_value=[]):
			self.assertEqual(queries.item_query("Item", "Test", "name", 0, 20, None), [])

	def test_item_query_paging_is_unchanged(self):
		for start in (0, 3, 6):
			with self.subTest(start=start):
				indexed = self.run_query("Test", None, page_len=3, start=start)
				scanned = self.run_query("Test", None, False, page_len=3, start=start)
				self.assertEqual(indexed, scanned)

	def run_query(self, txt, filters, use_index=True, page_len=20, start=0):
		if use_index:
			return queries.item_query("Item", txt, "name", start, page_len, filters, as_dict=True)

		with patch.object(queries, "get_item_search_candidates", return_value=None):
			return queries.item_query("Item", txt, "name", start, page_len, filters, as_dict=True)
