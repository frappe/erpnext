import re
import sqlite3

import frappe
from frappe.search.sqlite_search import SQLiteSearch

MINIMUM_TERM_LENGTH = 3
CANDIDATE_LIMIT = 25000
LIKE_WILDCARDS = r"[%_]"
QUEUE_PREFIX = "Item:"
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

	A host whose copy of the index is behind leaves committed Items out of its candidate list,
	and item_query then filters those valid rows away, so results depend on which host answered.
	Switched on per site from its Search Index record, which carries that warning.
	"""

	INDEX_NAME = "item_search.db"
	ENABLED_BY_DEFAULT = False
	BUILD_VOCABULARY = False

	def __init__(self, db_name=None):
		fieldnames = get_searched_fieldnames()
		mapped = {"title": "item_code", "content": "item_name"}
		plain = [f for f in dict.fromkeys(["name", *fieldnames]) if f not in mapped.values()]
		self.INDEXABLE_DOCTYPES = {
			"Item": {
				"fields": [*plain, mapped],
				"child_fields": {"barcodes": ["barcode"]},
				"filters": {"disabled": 0, "has_variants": 0},
			}
		}
		self.INDEX_SCHEMA = {
			"tokenizer": TOKENIZER,
			"text_fields": ["title", "content", *self._extra_text_fields(fieldnames)],
		}
		super().__init__(db_name)

	@staticmethod
	def _extra_text_fields(fieldnames: list[str]) -> list[str]:
		return [f for f in fieldnames if f not in ("item_code", "item_name")]

	def get_search_filters(self) -> dict:
		return {}

	def get_candidate_item_codes(self, txt: str) -> list[str] | None:
		"""Item codes that can match txt, a superset the caller must still recheck with LIKE.

		Covers barcodes, declared as a child table source, so the framework reads them through
		Item Barcode and reindexes the Item when one of them moves.
		"""
		if not self.is_search_enabled() or not self.index_exists():
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


def get_item_search_candidates(txt: str) -> list[str] | None:
	try:
		return ItemSearch().get_candidate_item_codes(txt)
	except Exception:
		frappe.log_error("Item search index unavailable")
		return None
