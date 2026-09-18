import sqlite3
from unittest.mock import MagicMock, patch

import frappe
from frappe.search.sqlite_search import get_search_classes, index_docs_in_queue, update_doc_index

from erpnext.controllers import queries
from erpnext.stock.doctype.item import item_search
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

	def test_item_search_is_registered_for_the_lifecycle(self):
		"""Without the sqlite_search hook nothing syncs the index and it silently rots."""
		self.assertIn(ItemSearch, get_search_classes())

	def test_a_new_item_is_searchable_before_the_queue_drains(self):
		"""index_doc only queues, and the scheduler drains every 5 minutes."""
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "ZZ-QUEUE-PROBE-4471",
				"item_name": "Queue Probe",
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": frappe.db.get_value("UOM", {}, "name"),
			}
		).insert()
		self.addCleanup(index_docs_in_queue)
		update_doc_index(item)

		self.assertIn("ZZ-QUEUE-PROBE-4471", self.search.get_candidate_item_codes("4471"))
		self.assertEqual(self.run_query("4471", None), self.run_query("4471", None, False))

	def test_vocabulary_is_not_built(self):
		"""Guards a no-op override of a private base method: a rename there would silently
		restore the pass, which costs a third of the build and nothing reads its output."""
		connection = self.search._get_connection(read_only=True)
		try:
			for table in ("search_vocabulary", "search_trigrams"):
				count = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
				self.assertEqual(count, 0, table)
		finally:
			connection.close()

	def test_tokenizer_folds_accents(self):
		"""MariaDB's utf8mb4_unicode_ci LIKE is accent insensitive, so the index must be too."""
		self.assertEqual(self.search.schema["tokenizer"], "trigram remove_diacritics 1")

	def test_an_accented_item_is_found_by_an_unaccented_term(self):
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "ZZ-CAFÉ-7781",
				"item_name": "Café Filter",
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": frappe.db.get_value("UOM", {}, "name"),
			}
		).insert()
		update_doc_index(item)
		self.addCleanup(index_docs_in_queue)

		self.assertIn("ZZ-CAFÉ-7781", self.search.get_candidate_item_codes("CAFE-7781"))
		self.assertEqual(self.run_query("CAFE-7781", None), self.run_query("CAFE-7781", None, False))

	def test_a_broken_index_falls_back_to_the_scan(self):
		"""An unreadable index must not answer 'nothing matches' and hide every row."""
		broken = MagicMock()
		broken.execute.side_effect = sqlite3.DatabaseError("database disk image is malformed")
		with patch.object(ItemSearch, "_get_connection", return_value=broken):
			self.assertIsNone(self.search.get_candidate_item_codes("Test"))

	def test_a_changed_search_field_set_falls_back(self):
		"""The built table lags a search-field change and would miss matches on the new field."""
		self.assertIsNone(self.drifted_search().get_candidate_item_codes("Test"))

	def test_the_builder_recovers_from_a_search_field_change(self):
		"""Falling back is only safe if something rebuilds; frappe's own builder does not."""
		drifted = self.drifted_search()
		self.assertFalse(drifted.index_exists())

		with patch.object(item_search, "ItemSearch", type(drifted)):
			item_search.build_index_if_missing()
		self.addCleanup(self.search.build_index)

		rebuilt = self.drifted_search()
		self.assertTrue(rebuilt.index_exists())
		self.assertIsNotNone(rebuilt.get_candidate_item_codes("Test"))

	def drifted_search(self) -> ItemSearch:
		extra = [*self.search.schema["text_fields"], "a_new_custom_search_field"]

		class DriftedItemSearch(ItemSearch):
			def __init__(self, *args, **kwargs):
				super().__init__(*args, **kwargs)
				self.schema["text_fields"] = extra

		return DriftedItemSearch()

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
			self.assertEqual(queries.item_query("Item", "Test", "name", 0, 20, None), ())
			self.assertEqual(queries.item_query("Item", "Test", "name", 0, 20, None, as_dict=True), [])

	def test_empty_result_matches_the_scan_shape(self):
		"""The early return must give back what the query itself would, tuple or list."""
		for as_dict in (False, True):
			with self.subTest(as_dict=as_dict):
				with patch.object(queries, "get_item_search_candidates", return_value=[]):
					early = queries.item_query("Item", "ZZQQNOTHING", "name", 0, 20, None, as_dict=as_dict)
				with patch.object(queries, "get_item_search_candidates", return_value=None):
					scanned = queries.item_query("Item", "ZZQQNOTHING", "name", 0, 20, None, as_dict=as_dict)
				self.assertEqual(early, scanned)
				self.assertIs(type(early), type(scanned))

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
