# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Decisions about how to handle master-data values referenced in the file.

For each distinct value found in a dependency column (e.g. a Customer
Group), the wizard captures one of four actions: ``use`` it as-is,
``map`` it to an existing master, ``create`` a new master, or ``skip``
rows that contain it. This module turns that decision tree into:

* the analyzer that the wizard's "Resolve" step renders, and
* the runtime resolver consulted by the importer on every row.
"""

import frappe

from erpnext.selling.doctype.party_import_log.column_mapper import fuzzy_score, normalize
from erpnext.selling.doctype.party_import_log.schema import NON_CREATABLE_MASTERS

# Stricter than ColumnMapper's threshold: a wrong master suggestion can quietly
# miscategorize data if the user clicks through, so we err on the side of "no
# suggestion" and let them resolve manually.
MASTER_FUZZY_THRESHOLD = 0.85


class DependencyAnalyzer:
	"""Builds the per-master payload the wizard's Resolve step renders."""

	def __init__(self, dependency_fields: dict[str, tuple[str, bool]], mappings: dict[str, str]):
		self.dependency_fields = dependency_fields
		self.mappings = mappings
		self._cache: dict[str, list[str]] = {}

	def analyze(self, rows: list[dict]) -> dict:
		"""Return master_doctype -> {master, is_tree, creatable, values}."""
		target_to_source = invert_mappings(self.mappings)
		result: dict[str, dict] = {}
		for target_field, (master_doctype, is_tree) in self.dependency_fields.items():
			source_column = target_to_source.get(target_field)
			if not source_column:
				continue
			counts = count_values(rows, source_column)
			if not counts:
				continue
			values = [self._describe(master_doctype, value, count) for value, count in counts]
			self._merge_into(result, master_doctype, is_tree, values)
		return result

	def _describe(self, master_doctype: str, value: str, count: int) -> dict:
		exists = bool(frappe.db.exists(master_doctype, value))
		return {
			"value": value,
			"count": count,
			"exists": exists,
			"suggestion": None if exists else self._suggest_match(master_doctype, value),
		}

	def _suggest_match(self, master_doctype: str, value: str) -> str | None:
		"""Pick the existing master record closest to ``value``, or None.

		Scores every record using exact / substring / fuzzy tiers and picks
		the highest above ``MASTER_FUZZY_THRESHOLD``. An exact-normalized
		match short-circuits the scan.
		"""
		normalized = normalize(value)
		if not normalized:
			return None
		best_record, best_score = None, 0.0
		for record in self._records_for(master_doctype):
			normalized_record = normalize(record)
			if not normalized_record:
				continue
			score = fuzzy_score(normalized, normalized_record)
			if score == 1.0:
				return record
			if score > best_score:
				best_record, best_score = record, score
		return best_record if best_score >= MASTER_FUZZY_THRESHOLD else None

	def _records_for(self, master_doctype: str) -> list[str]:
		if master_doctype not in self._cache:
			self._cache[master_doctype] = frappe.get_all(master_doctype, pluck="name")
		return self._cache[master_doctype]

	def _merge_into(self, result: dict, master_doctype: str, is_tree: bool, new_values: list[dict]) -> None:
		if master_doctype not in result:
			result[master_doctype] = {
				"master": master_doctype,
				"is_tree": is_tree,
				"creatable": master_doctype not in NON_CREATABLE_MASTERS,
				"values": new_values,
			}
			return
		existing = {entry["value"]: entry for entry in result[master_doctype]["values"]}
		for entry in new_values:
			if entry["value"] in existing:
				existing[entry["value"]]["count"] += entry["count"]
			else:
				existing[entry["value"]] = entry
		result[master_doctype]["values"] = list(existing.values())


class DependencyResolver:
	"""Runtime lookups: given a value, return the final master record name to use."""

	def __init__(self, resolutions: dict):
		self.lookup = self._build_lookup(resolutions)

	def resolve(self, master_doctype: str, value: str) -> str | None:
		"""Apply the user's stored decision; fall back to as-is when the value exists."""
		if not value:
			return None
		action = self.lookup.get(master_doctype, {}).get(value)
		if not action:
			return value if frappe.db.exists(master_doctype, value) else None
		action_type = action["action"]
		if action_type == "use":
			return value
		if action_type == "map":
			return action.get("map_to") or None
		if action_type == "create":
			parts = split_tree_path(value)
			return parts[-1] if parts else value
		if action_type == "skip":
			return None
		return value

	def should_skip_row(
		self, row: dict, mappings: dict, dependency_fields: dict[str, tuple[str, bool]]
	) -> bool:
		"""True if any dependency value in this row carries a 'skip' resolution."""
		for target_field, (master_doctype, _is_tree) in dependency_fields.items():
			source_column = source_for_target(mappings, target_field)
			if not source_column:
				continue
			value = (row.get(source_column) or "").strip()
			if not value:
				continue
			action = self.lookup.get(master_doctype, {}).get(value)
			if action and action.get("action") == "skip":
				return True
		return False

	def masters_to_create(self) -> dict[str, list[str]]:
		"""Group all 'create' actions by master DocType — used in dry-run side-effects."""
		grouped: dict[str, list[str]] = {}
		for master_doctype, by_value in self.lookup.items():
			for value, action in by_value.items():
				if action.get("action") == "create":
					grouped.setdefault(master_doctype, []).append(value)
		return grouped

	def _build_lookup(self, resolutions: dict) -> dict[str, dict[str, dict]]:
		lookup: dict[str, dict[str, dict]] = {}
		for master_doctype, payload in resolutions.items():
			lookup[master_doctype] = {}
			for entry in payload.get("values", []):
				lookup[master_doctype][entry["value"]] = {
					"action": entry.get("action", "use"),
					"map_to": entry.get("map_to"),
				}
		return lookup


def invert_mappings(mappings: dict[str, str]) -> dict[str, str]:
	"""Flip {source: target} to {target: source}; drops blank targets."""
	return {target: source for source, target in mappings.items() if target}


def source_for_target(mappings: dict[str, str], target_field: str) -> str | None:
	"""Return the source column mapped to a given target field, or None."""
	for source, target in mappings.items():
		if target == target_field:
			return source
	return None


def count_values(rows: list[dict], source_column: str) -> list[tuple[str, int]]:
	"""Return [(value, count), ...] sorted by descending count."""
	counts: dict[str, int] = {}
	for row in rows:
		value = (row.get(source_column) or "").strip()
		if not value:
			continue
		counts[value] = counts.get(value, 0) + 1
	return sorted(counts.items(), key=lambda item: -item[1])


def split_tree_path(value: str) -> list[str]:
	"""Split 'Parent / Child / Grandchild' into trimmed segments."""
	return [part.strip() for part in value.split("/") if part.strip()]
