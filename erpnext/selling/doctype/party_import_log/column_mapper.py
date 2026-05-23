# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Best-effort mapping from source spreadsheet columns to target party fields.

Three layers, applied in order of confidence:

* a curated synonym table (exact normalized match) — so "GSTIN" maps to
  ``tax_id`` even though the strings share no characters,
* substring containment between the source column and the target's
  fieldname / label / known aliases — inspired by the bank-statement
  importer, which uses the same idea to pin down "Transaction Date" -> Date,
* fuzzy similarity (``difflib.SequenceMatcher``) above a confidence
  threshold — catches typos and minor wording differences.

Across the whole sheet we greedily assign the highest-confidence
matches first so two source columns can't both auto-map to the same
target. Anything below threshold is left for the user to map manually.
"""

import re
from difflib import SequenceMatcher

SYNONYMS = {
	"companyname": "customer_name",
	"company": "customer_name",
	"name": "customer_name",
	"accountname": "customer_name",
	"customername": "customer_name",
	"suppliername": "supplier_name",
	"vendor": "supplier_name",
	"vendorname": "supplier_name",
	"phone": "primary_mobile",
	"phonenumber": "primary_mobile",
	"mobile": "primary_mobile",
	"mobileno": "primary_mobile",
	"email": "primary_email",
	"emailaddress": "primary_email",
	"emailid": "primary_email",
	"firstname": "primary_first_name",
	"lastname": "primary_last_name",
	"address": "billing_address_line1",
	"addressline1": "billing_address_line1",
	"street": "billing_address_line1",
	"city": "billing_city",
	"state": "billing_state",
	"country": "billing_country",
	"postcode": "billing_pincode",
	"postalcode": "billing_pincode",
	"pincode": "billing_pincode",
	"zipcode": "billing_pincode",
	"zip": "billing_pincode",
	"website": "website",
	"url": "website",
	"taxid": "tax_id",
	"gstin": "tax_id",
	"gstnumber": "tax_id",
	"vat": "tax_id",
	"creditlimit": "credit_limit",
	"credit": "credit_limit",
	"group": "customer_group",
	"customergroup": "customer_group",
	"suppliergroup": "supplier_group",
	"territory": "territory",
	"region": "territory",
	"industry": "industry",
	"segment": "market_segment",
	"currency": "default_currency",
	"pricelist": "default_price_list",
	"paymentterms": "payment_terms",
	"language": "language",
	"notes": "notes",
	"description": "notes",
}

# Tokens shorter than this aren't matched as substrings — avoids "id" or
# "no" pulling unrelated columns into the wrong target.
MIN_SUBSTRING_LENGTH = 4

# Minimum confidence for a non-synonym match. Tuned to balance recall
# against false positives; lower it and noise creeps in.
FUZZY_THRESHOLD = 0.82

# Synonym matches outscore everything else so they always win during
# greedy assignment, even when a weaker fuzzy match exists elsewhere.
SYNONYM_SCORE = 1.5


class ColumnMapper:
	"""Suggests target-field mappings for a list of source columns.

	``template_synonyms`` is an optional ``{normalized_source: target_field}`` map
	from a known source system (see :mod:`templates`). It's checked alongside the
	generic ``SYNONYMS`` table — the template wins if both define the same key,
	since the user has explicitly told us which source system the file came from.
	"""

	def __init__(self, target_fields: list[tuple], template_synonyms: dict[str, str] | None = None):
		self.target_fields = target_fields
		self.target_keys = {field[0] for field in target_fields}
		self.template_synonyms = template_synonyms or {}
		self._candidates_by_target = self._build_candidate_index()

	def suggest(self, source_columns: list[str]) -> dict[str, str]:
		"""Return a {source_column: target_field} map for confidently-matched columns."""
		ranked = self._rank_candidates(source_columns)
		return self._greedy_assign(ranked)

	def _rank_candidates(self, source_columns: list[str]) -> list[tuple[float, str, str]]:
		"""Score every (source_column, target_field) pair worth considering."""
		ranked: list[tuple[float, str, str]] = []
		for column in source_columns:
			normalized = normalize(column)
			if not normalized:
				continue
			synonym = self.template_synonyms.get(normalized) or SYNONYMS.get(normalized)
			if synonym and synonym in self.target_keys:
				ranked.append((SYNONYM_SCORE, column, synonym))
				continue
			for target in self.target_fields:
				score = self._score(normalized, self._candidates_by_target[target[0]])
				if score >= FUZZY_THRESHOLD:
					ranked.append((score, column, target[0]))
		return ranked

	def _greedy_assign(self, ranked: list[tuple[float, str, str]]) -> dict[str, str]:
		"""Assign best matches first; each source and target is used at most once."""
		ranked.sort(key=lambda candidate: -candidate[0])
		assignments: dict[str, str] = {}
		used_targets: set[str] = set()
		for _score, column, target in ranked:
			if column in assignments or target in used_targets:
				continue
			assignments[column] = target
			used_targets.add(target)
		return assignments

	def _score(self, normalized_source: str, candidates: set[str]) -> float:
		best = 0.0
		for candidate in candidates:
			if len(candidate) < MIN_SUBSTRING_LENGTH:
				continue
			score = fuzzy_score(normalized_source, candidate)
			if score > best:
				best = score
		return best

	def _build_candidate_index(self) -> dict[str, set[str]]:
		"""For each target, gather its normalized fieldname, label, and reverse-synonyms."""
		reverse_synonyms: dict[str, set[str]] = {}
		for source_key, target in SYNONYMS.items():
			reverse_synonyms.setdefault(target, set()).add(source_key)
		index: dict[str, set[str]] = {}
		for fieldname, label, _group, _required in self.target_fields:
			terms = {normalize(fieldname), normalize(label)} | reverse_synonyms.get(fieldname, set())
			terms.discard("")
			index[fieldname] = terms
		return index


def normalize(value: str) -> str:
	"""Lowercase + strip non-alphanumerics — used for loose string comparison."""
	return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def fuzzy_score(source: str, candidate: str) -> float:
	"""Score a (source, candidate) pair on the 0..1 scale.

	Tiers, in order: exact equality (1.0), substring containment in either
	direction (0.85..1.0 by length ratio), then ``SequenceMatcher.ratio``
	as the typo-tolerant fallback. Both inputs should already be normalized.
	"""
	if source == candidate:
		return 1.0
	if candidate in source:
		return 0.85 + 0.15 * (len(candidate) / len(source))
	if source in candidate:
		return 0.85 + 0.15 * (len(source) / len(candidate))
	return SequenceMatcher(None, candidate, source).ratio()
