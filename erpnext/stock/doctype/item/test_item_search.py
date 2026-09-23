import sqlite3
from unittest.mock import MagicMock, patch

import frappe
from frappe.search.sqlite_search import get_search_classes, index_docs_in_queue, update_doc_index

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


class TestItemSearchSetting(ERPNextTestSuite):
	def test_the_global_defaults_checkbox_drives_the_index(self):
		with self.change_settings("Global Defaults", enable_item_search_index=0):
			self.assertFalse(ItemSearch().is_search_enabled())

		with self.change_settings("Global Defaults", enable_item_search_index=1):
			self.assertTrue(ItemSearch().is_search_enabled())


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

	def test_a_barcode_added_after_the_build_is_searchable(self):
		"""A barcode edit changes no Item field, so the Item save is the only signal there is."""
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "ZZ-BARCODE-PROBE",
				"item_name": "Barcode Probe",
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": frappe.db.get_value("UOM", {}, "name"),
			}
		).insert()
		self.assertIn("barcodes", self.search.schema["text_fields"])

		item.append("barcodes", {"barcode": "8809988776655"})
		item.save()
		index_docs_in_queue()

		self.assertIn("ZZ-BARCODE-PROBE", self.candidates("8809988776655"))
		self.assertEqual(self.run_query("8809988776655", None), self.run_query("8809988776655", None, False))

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
		update_doc_index(item)

		self.assertIn("ZZ-QUEUE-PROBE-4471", self.candidates("4471"))
		self.assertEqual(self.run_query("4471", None), self.run_query("4471", None, False))

	def test_vocabulary_is_not_built(self):
		"""item_query matches search_fts directly and never asks for a spelling correction."""
		self.assertFalse(ItemSearch.BUILD_VOCABULARY)
		connection = self.search._get_connection(read_only=True)
		try:
			self.assertEqual(connection.execute("SELECT count(*) FROM search_vocabulary").fetchone()[0], 0)
			self.assertEqual(connection.execute("SELECT count(*) FROM search_trigrams").fetchone()[0], 0)
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

		self.assertIn("ZZ-CAFÉ-7781", self.candidates("CAFE-7781"))
		self.assertEqual(self.run_query("CAFE-7781", None), self.run_query("CAFE-7781", None, False))

	def test_a_broken_index_falls_back_to_the_scan(self):
		"""An unreadable index must not answer 'nothing matches' and hide every row."""
		broken = MagicMock()
		broken.execute.side_effect = sqlite3.DatabaseError("database disk image is malformed")
		with patch.object(ItemSearch, "_get_connection", return_value=broken):
			self.assertIsNone(self.candidates("Test"))

	def drifted_search(self) -> ItemSearch:
		extra = [*self.search.schema["text_fields"], "a_new_custom_search_field"]

		class DriftedItemSearch(ItemSearch):
			def __init__(self, *args, **kwargs):
				super().__init__(*args, **kwargs)
				self.schema["text_fields"] = extra

		return DriftedItemSearch()

	def test_an_item_without_barcodes_is_still_indexed(self):
		"""A text column left unset drops the document from the index entirely."""
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "ZZ-NO-BARCODE-3312",
				"item_name": "No Barcode Probe",
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": frappe.db.get_value("UOM", {}, "name"),
			}
		).insert()
		index_docs_in_queue()

		self.assertIn("ZZ-NO-BARCODE-3312", self.candidates("3312"))

	def test_a_drifted_schema_reports_the_index_as_absent(self):
		"""A site that adds an Item search field leaves the built table a column short."""
		self.assertTrue(self.search.index_exists())
		self.assertFalse(self.drifted_search().index_exists())

	def test_a_search_field_outside_the_index_is_refused(self):
		"""A caller may pass any Item field as searchfield, and the index carries only some."""
		outside = "stock_uom"
		self.assertNotIn(outside, self.search.indexed_fieldnames)

		self.assertIsNone(self.candidates("Test", ["name", outside]))
		self.assertIsNotNone(self.candidates("Test", ["name", "item_code"]))

	def test_item_query_with_an_unindexed_searchfield_matches_the_scan(self):
		"""Narrowing on a field the index does not carry would drop rows the scan returns."""
		self.assertEqual(
			self.run_query("Test", None, searchfield="stock_uom"),
			self.run_query("Test", None, False, searchfield="stock_uom"),
		)

	def test_a_renamed_item_is_searchable_under_the_new_name(self):
		"""A rename writes the new name without saving the Item, so on_update never fires."""
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "ZZ-RENAME-FROM-5521",
				"item_name": "Rename Probe",
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": frappe.db.get_value("UOM", {}, "name"),
			}
		).insert()
		index_docs_in_queue()
		self.assertIn("ZZ-RENAME-FROM-5521", self.candidates("5521"))

		frappe.rename_doc("Item", item.name, "ZZ-RENAME-TO-5521", force=True)
		index_docs_in_queue()

		self.assertIn("ZZ-RENAME-TO-5521", self.candidates("5521"))
		self.assertNotIn("ZZ-RENAME-FROM-5521", self.candidates("5521"))

	def test_repeated_spaces_and_urls_match_the_scan(self):
		"""Values are indexed verbatim: cleaning them would lose rows the LIKE still matches."""
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "ZZ-VERBATIM-6612",
				"item_name": "Valve  3 MM see https://example.com/spec",
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": frappe.db.get_value("UOM", {}, "name"),
			}
		).insert()
		index_docs_in_queue()

		for txt in ("Valve  3", "example.com"):
			with self.subTest(txt=txt):
				self.assertEqual(self.run_query(txt, None), self.run_query(txt, None, False))

	def test_an_index_write_failure_saves_the_item_and_drops_the_index(self):
		"""The save must survive, and the index must stop answering: nothing recorded the Item as
		stale, so its candidate list would hide a row the scan returns."""
		with (
			patch.object(ItemSearch, "index_doc", side_effect=sqlite3.OperationalError("disk I/O error")),
			patch.object(frappe, "log_error") as logged,
		):
			item = frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "ZZ-WRITE-FAILURE-3390",
					"item_name": "Write Failure Probe",
					"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
					"stock_uom": frappe.db.get_value("UOM", {}, "name"),
				}
			).insert()

		self.assertTrue(frappe.db.exists("Item", item.name))
		logged.assert_called()
		self.assertFalse(self.search.index_exists())
		self.assertIsNone(self.candidates("3390"), "a dropped index must force the scan")

		self.search.build_index()

	def test_candidates_are_a_superset_of_the_scan(self):
		"""The query re-filters, so extra candidates are safe but missing ones are not."""
		for txt in ("Test", "Item", "est", "_Test"):
			candidates = self.candidates(txt)
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
		candidates = self.candidates("_Test Item")
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

	def candidates(self, txt, searched_fields=None):
		return self.search.get_candidate_item_codes(
			txt, searched_fields or ["name", "item_code", "item_name"]
		)

	def run_query(self, txt, filters, use_index=True, page_len=20, start=0, searchfield="name"):
		if use_index:
			return queries.item_query("Item", txt, searchfield, start, page_len, filters, as_dict=True)

		with patch.object(queries, "get_item_search_candidates", return_value=None):
			return queries.item_query("Item", txt, searchfield, start, page_len, filters, as_dict=True)
