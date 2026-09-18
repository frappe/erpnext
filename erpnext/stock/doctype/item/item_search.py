import re
import sqlite3
from collections import defaultdict

import frappe
from frappe.search.sqlite_search import SQLiteSearch

MINIMUM_TERM_LENGTH = 3
CANDIDATE_LIMIT = 25000
LIKE_WILDCARDS = r"[%_]"


def get_searched_fieldnames() -> list[str]:
	"""Item fields that item_query matches the search term against."""
	meta = frappe.get_meta("Item", cached=True)
	searchfields = meta.get_search_fields()
	extras = [f for f in ("item_code", "item_group", "item_name") if f not in searchfields]
	db_fieldnames = {field.fieldname for field in meta.fields}
	return [f for f in [*searchfields, *extras] if f in db_fieldnames]


class ItemSearch(SQLiteSearch):
	"""FTS5 trigram index over Item, for substring search on large catalogues."""

	INDEX_NAME = "item_search.db"

	def __init__(self, db_name=None):
		fieldnames = get_searched_fieldnames()
		self.INDEXABLE_DOCTYPES = {
			"Item": {
				"fields": ["name", *fieldnames, {"title": "item_code", "content": "item_name"}],
				"filters": {"disabled": 0, "has_variants": 0},
			}
		}
		self.INDEX_SCHEMA = {
			"tokenizer": "trigram",
			"text_fields": ["title", "content", *self._extra_text_fields(fieldnames), "barcode"],
		}
		self.barcode_cache = None
		super().__init__(db_name)

	@staticmethod
	def _extra_text_fields(fieldnames: list[str]) -> list[str]:
		return [f for f in fieldnames if f not in ("item_code", "item_name")]

	def is_search_enabled(self) -> bool:
		return bool(frappe.conf.get("enable_item_search_index"))

	def get_search_filters(self) -> dict:
		return {}

	def get_documents_paginated(
		self, doctype, limit=1000, last_indexed_modified=None, last_indexed_name=None
	):
		"""Preload the batch's barcodes so prepare_document does not query per item."""
		docs = super().get_documents_paginated(doctype, limit, last_indexed_modified, last_indexed_name)
		self.barcode_cache = self.get_barcode_map([doc.name for doc in docs])
		return docs

	def prepare_document(self, doc):
		document = super().prepare_document(doc)
		if document is not None:
			document["barcode"] = self.get_barcode_text(doc.name)
		return document

	def get_barcode_text(self, item_code: str) -> str:
		if self.barcode_cache is not None:
			return self.barcode_cache.get(item_code, "")
		return self.get_barcode_map([item_code]).get(item_code, "")

	def get_barcode_map(self, item_codes: list[str]) -> dict[str, str]:
		if not item_codes:
			return {}

		rows = frappe.get_all(
			"Item Barcode", filters={"parent": ("in", item_codes)}, fields=["parent", "barcode"]
		)
		grouped = defaultdict(list)
		for row in rows:
			if row.barcode:
				grouped[row.parent].append(row.barcode)
		return {parent: " ".join(barcodes) for parent, barcodes in grouped.items()}

	def get_candidate_item_codes(self, txt: str) -> list[str] | None:
		"""Item codes that can match txt, a superset the caller must still recheck with LIKE."""
		if not self.is_search_enabled() or not self.index_exists():
			return None

		match_query = build_match_query(txt)
		if match_query is None:
			return None

		names = self.run_match(match_query)
		return None if len(names) >= CANDIDATE_LIMIT else names

	def run_match(self, match_query: str) -> list[str]:
		connection = self._get_connection(read_only=True)
		try:
			rows = connection.execute(
				"SELECT name FROM search_fts WHERE search_fts MATCH ? LIMIT ?",
				(match_query, CANDIDATE_LIMIT),
			).fetchall()
			return [row["name"] for row in rows]
		except sqlite3.Error:
			frappe.log_error("Item search index lookup failed")
			return []
		finally:
			connection.close()


def build_match_query(txt: str) -> str | None:
	"""FTS5 query matching a superset of LIKE %txt%, or None when it cannot narrow the scan."""
	if "\\" in txt:
		return None

	fragments = [fragment.strip() for fragment in re.split(LIKE_WILDCARDS, txt)]
	usable = [fragment for fragment in fragments if len(fragment) >= MINIMUM_TERM_LENGTH]
	if not usable:
		return None

	return " AND ".join(quote_fragment(fragment) for fragment in usable)


def quote_fragment(fragment: str) -> str:
	escaped = fragment.replace('"', '""')
	return f'"{escaped}"'


def get_item_search_candidates(txt: str) -> list[str] | None:
	try:
		return ItemSearch().get_candidate_item_codes(txt)
	except Exception:
		frappe.log_error("Item search index unavailable")
		return None
