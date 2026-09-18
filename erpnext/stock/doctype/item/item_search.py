import os
import re
import sqlite3

import frappe
from frappe.search.sqlite_search import SQLiteSearch, SQLiteSearchIndexMissingError, build_index
from frappe.utils import now_datetime

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

	Requires a single app server. The index and its pending queue are files under the site
	path, so every host builds and updates its own copy. A host whose copy is behind omits
	committed Items from its candidate list, and item_query then filters those valid rows
	out, making results depend on which host answered. Leave Stock Settings' Enable Item
	Search Index off wherever the bench runs more than one app server.
	"""

	INDEX_NAME = "item_search.db"

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
			"text_fields": ["title", "content", *self._extra_text_fields(fieldnames)],
		}
		super().__init__(db_name)

	@staticmethod
	def _extra_text_fields(fieldnames: list[str]) -> list[str]:
		return [f for f in fieldnames if f not in ("item_code", "item_name")]

	def is_search_enabled(self) -> bool:
		"""Off unless Stock Settings opts in. Single app server only, see the class docstring."""
		return bool(frappe.get_single_value("Stock Settings", "enable_item_search_index"))

	def get_search_filters(self) -> dict:
		return {}

	def _build_vocabulary_incremental(self):
		"""Spelling correction is unused: item_query matches search_fts directly."""

	def get_candidate_item_codes(self, txt: str) -> list[str] | None:
		"""Item codes that can match txt, a superset the caller must still recheck with LIKE."""
		if not self.is_search_enabled() or not self.index_exists():
			return None

		match_query = build_match_query(txt)
		if match_query is None:
			return None

		names = self.run_match(match_query)
		if names is None:
			return None

		names += get_item_codes_by_barcode(txt)
		return None if len(names) >= CANDIDATE_LIMIT else names

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

	def index_exists(self) -> bool:
		"""Also false once the built columns stop covering the searched fields.

		The scheduled builder only rebuilds an index it considers missing, and it creates the
		table with IF NOT EXISTS, so reporting a drifted index as present would strand the site
		on the full scan until someone deleted the file by hand.
		"""
		return super().index_exists() and self.has_current_schema()

	def has_current_schema(self) -> bool:
		"""Whether the built table still carries every field the search term is matched against."""
		try:
			connection = self._get_connection(read_only=True)
		except SQLiteSearchIndexMissingError:
			return False

		try:
			columns = {row["name"] for row in connection.execute("PRAGMA table_info(search_fts)")}
		except sqlite3.Error:
			return False
		finally:
			connection.close()

		return set(self.schema["text_fields"]) <= columns


def get_item_codes_by_barcode(txt: str) -> list[str]:
	"""Item codes whose barcode contains txt.

	Barcodes are searched by item_query but deliberately stay out of the index. They live in a
	child table, and update_doc_index only reindexes when a watched Item field changed, which a
	barcode edit never does, so an indexed copy would go stale the moment a barcode was added.
	"""
	return frappe.get_all(
		"Item Barcode",
		filters={"barcode": ("like", f"%{txt}%")},
		pluck="parent",
		limit=CANDIDATE_LIMIT,
	)


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


def build_index_if_missing():
	"""Build the index when it is absent or its columns have drifted, then reconcile it.

	frappe's scheduled builder also builds a missing index as of frappe#42968, but it does not
	queue the Items saved while it ran. Building here keeps the build and that reconciliation
	together. A build already in progress leaves a temp database behind, and frappe resumes that
	one, so leave it alone.
	"""
	search = ItemSearch()
	if not search.is_search_enabled() or search.index_exists():
		return

	if os.path.exists(search._get_db_path(is_temp=True)):
		return

	started_at = now_datetime()
	build_index(ItemSearch, force=True)
	queue_items_changed_during_build(started_at)


def queue_items_changed_during_build(started_at):
	"""Re-queue Items saved while the index was building.

	A build reads each Item once, and frappe skips the doc_events sync for an index it
	considers absent, which it does throughout a build. An Item saved after its row was read
	therefore lands in the new index with stale text. Queueing it makes it a candidate again
	straight away, and the scheduled drain reindexes it.
	"""
	search = ItemSearch()
	if not search.index_exists():
		return

	names = frappe.get_all("Item", filters={"modified": (">=", started_at)}, pluck="name")
	for name in names:
		search.index_doc("Item", name)


def get_item_search_candidates(txt: str) -> list[str] | None:
	try:
		return ItemSearch().get_candidate_item_codes(txt)
	except Exception:
		frappe.log_error("Item search index unavailable")
		return None
