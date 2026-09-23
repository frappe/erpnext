import os
import re
import sqlite3

import frappe
from frappe.search.sqlite_search import SQLiteSearch, SQLiteSearchIndexMissingError

MINIMUM_TERM_LENGTH = 3
CANDIDATE_LIMIT = 25000
LIKE_WILDCARDS = r"[%_]"
QUEUE_PREFIX = "Item:"
BARCODE_COLUMN = "barcodes"
TOKENIZER = "trigram remove_diacritics 1"


def get_searched_fieldnames() -> list[str]:
	"""Item fields that item_query matches the search term against."""
	meta = frappe.get_meta("Item", cached=True)
	searchfields = meta.get_search_fields()
	extras = [f for f in ("item_code", "item_group", "item_name") if f not in searchfields]
	db_fieldnames = {field.fieldname for field in meta.fields}
	return [f for f in [*searchfields, *extras] if f in db_fieldnames]


class ItemSearch(SQLiteSearch):
	"""FTS5 trigram index over Item, for substring search on large catalogues.

	A host whose copy is behind drops valid Items from its candidate list, so results depend on
	which host answered. Switched on per site from Global Defaults, which carries that warning.
	"""

	INDEX_NAME = "item_search.db"
	BUILD_VOCABULARY = False

	def __init__(self, db_name=None):
		fieldnames = get_searched_fieldnames()
		mapped = {"title": "item_code", "content": "item_name"}
		plain = [f for f in dict.fromkeys(["name", *fieldnames]) if f not in mapped.values()]
		self.INDEXABLE_DOCTYPES = {
			"Item": {
				"fields": [*plain, mapped],
				"filters": {"disabled": 0, "has_variants": 0},
			}
		}
		self.INDEX_SCHEMA = {
			"tokenizer": TOKENIZER,
			"text_fields": [
				"title",
				"content",
				BARCODE_COLUMN,
				*self._extra_text_fields(fieldnames),
			],
		}
		self.indexed_fieldnames = {"name", *fieldnames}
		self._barcodes = {}
		super().__init__(db_name)

	@staticmethod
	def _extra_text_fields(fieldnames: list[str]) -> list[str]:
		return [f for f in fieldnames if f not in ("item_code", "item_name")]

	def index_exists(self) -> bool:
		"""A table missing a searched column cannot answer for it, so it reports itself absent.

		The searched fields come from the Item meta, so a site that adds one leaves an older table
		short. Callers fall back and the builder replaces it. One connection: this runs on every save.
		"""
		if not os.path.exists(self.db_path):
			return False

		return set(self.schema["text_fields"]) <= self.get_indexed_columns()

	def get_indexed_columns(self) -> set[str]:
		"""Columns the built table carries, empty when there is no table."""
		try:
			connection = self._get_connection(read_only=True)
		except SQLiteSearchIndexMissingError:
			return set()

		try:
			return {row["name"] for row in connection.execute("PRAGMA table_info(search_fts)")}
		except sqlite3.Error:
			return set()
		finally:
			connection.close()

	def get_documents_paginated(self, doctype, *args, **kwargs):
		"""Preload the batch's barcodes: reading them per document would be one query each."""
		documents = super().get_documents_paginated(doctype, *args, **kwargs)
		self._barcodes = get_barcodes_by_item([document.name for document in documents])
		return documents

	def index_documents_by_name(self, doctype, names: list[str]):
		"""Preload this batch: the catch-up skips get_documents_paginated, and the barcodes left
		from the last build batch may since have moved."""
		self._barcodes = get_barcodes_by_item(names)
		super().index_documents_by_name(doctype, names)

	def prepare_document(self, doc):
		document = super().prepare_document(doc)
		if document is None:
			return None

		document[BARCODE_COLUMN] = self.get_barcode_text(doc.name)
		return document

	def _process_content(self, content):
		"""Store values verbatim.

		item_query rechecks every candidate with LIKE against the column in MariaDB, so the
		indexed text has to be what that column holds. The framework's cleaning collapses
		whitespace and replaces a URL with "[link]", which would lose those rows.
		"""
		return "" if content is None else str(content)

	def get_barcode_text(self, item_code: str) -> str:
		"""Always a string: a text column left unset drops the document from the index entirely."""
		if item_code in self._barcodes:
			return self._barcodes[item_code]

		return get_barcodes_by_item([item_code]).get(item_code, "")

	def is_search_enabled(self) -> bool:
		"""Off unless Global Defaults opts in: building reads every Item, which is not free."""
		return bool(frappe.get_single_value("Global Defaults", "enable_item_search_index"))

	def get_search_filters(self) -> dict:
		return {}

	def get_candidate_item_codes(self, txt: str, searched_fields: list[str]) -> list[str] | None:
		"""Item codes that can match txt, a superset the caller must still recheck with LIKE.

		Covers barcodes, which item_query also searches: an Item left out is filtered away even
		when its barcode matches. Answers only when the index carries every field the query
		searches, because a caller may pass any Item field as searchfield. `name` counts as
		indexed: Item.autoname assigns it from item_code.
		"""
		if not self.is_search_enabled() or not self.index_exists():
			return None

		if not set(searched_fields) <= self.indexed_fieldnames:
			return None

		match_query = build_match_query(txt)
		if match_query is None:
			return None

		names = self.run_match(match_query)
		if names is None or len(names) >= CANDIDATE_LIMIT:
			return None

		return names

	def run_match(self, match_query: str) -> list[str] | None:
		"""None means the index cannot answer. An empty list means it answered: nothing matches."""
		connection = self._get_connection(read_only=True)
		try:
			matched = connection.execute(
				"SELECT name FROM search_fts WHERE search_fts MATCH ? LIMIT ?",
				(match_query, CANDIDATE_LIMIT),
			).fetchall()
			queued = connection.execute(
				"SELECT doc_id FROM search_index_queue LIMIT ?", (CANDIDATE_LIMIT,)
			).fetchall()
		except sqlite3.Error:
			frappe.log_error("Item search index lookup failed")
			return None
		finally:
			connection.close()

		names = [row["name"] for row in matched]
		return names + [doc_id.removeprefix(QUEUE_PREFIX) for doc_id in queued_item_ids(queued)]


def queued_item_ids(rows) -> list[str]:
	"""Items waiting to be re-indexed. Their indexed text is stale or absent, so they stay candidates."""
	return [row["doc_id"] for row in rows if row["doc_id"].startswith(QUEUE_PREFIX)]


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


def get_barcodes_by_item(item_codes: list[str]) -> dict[str, str]:
	"""Barcodes of each item, joined into the one string the index column holds."""
	if not item_codes:
		return {}

	rows = frappe.get_all(
		"Item Barcode",
		filters={"parent": ("in", item_codes), "parentfield": BARCODE_COLUMN},
		fields=["parent", "barcode"],
	)

	barcodes = {}
	for row in rows:
		barcodes[row.parent] = f"{barcodes.get(row.parent, '')} {row.barcode}".strip()

	return barcodes


def reindex_item(doc, method=None):
	"""Queue an Item on every save.

	Item Barcode rows raise no document events, so the Item save is the only signal one moved, and
	no indexed field of the Item need have changed.
	"""
	queue_item(doc.name)


def queue_item(item_code: str, drop: str | None = None):
	"""Queue one Item, and drop another name first when a rename replaced it.

	A failed index write must not fail the Item save: the index is an optimisation that every
	caller already falls back from, so the error is logged rather than raised.
	"""
	search = ItemSearch()
	if not (search.is_search_enabled() and search.index_exists()):
		return

	try:
		if drop:
			search.remove_doc("Item", drop)

		search.index_doc("Item", item_code)
	except Exception:
		frappe.log_error("Item search index update failed")


def get_item_search_candidates(txt: str, searched_fields: list[str]) -> list[str] | None:
	try:
		return ItemSearch().get_candidate_item_codes(txt, searched_fields)
	except Exception:
		frappe.log_error("Item search index unavailable")
		return None
