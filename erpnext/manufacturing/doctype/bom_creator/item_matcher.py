# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.utils import strip_html
from rapidfuzz import fuzz, process
from rapidfuzz.utils import default_process

HIGH_SCORE = 90
MIN_SCORE = 70
CANDIDATE_SCORE = 50
CANDIDATE_LIMIT = 5


class ItemMatcher:
	def __init__(self, parts: list):
		self.parts = [part for part in parts if part.part_number or part.part_name]

	def get_matches(self) -> dict[str, dict]:
		if not self.parts:
			return {}

		self.set_items()
		earlier_items = self.get_earlier_items()
		parts = {get_part_key(part): part for part in self.parts}
		known = {key: self.get_known_match(part, earlier_items) for key, part in parts.items()}
		candidates = {key: self.get_candidates(part) for key, part in parts.items() if not known[key]}
		self.descriptions = self.get_descriptions(candidates)

		matches = {
			key: known[key] or self.get_best_match(part, candidates[key]) for key, part in parts.items()
		}
		return {part.name: matches[get_part_key(part)] for part in self.parts if matches[get_part_key(part)]}

	def set_items(self):
		items = frappe.get_all(
			"Item", filters={"disabled": 0, "has_variants": 0}, fields=["name", "item_name"]
		)
		self.item_codes = {item.name for item in items}
		self.codes = ([item.name for item in items], [get_code_key(item.name) for item in items])
		named_items = [item for item in items if item.item_name]
		self.names = (
			[item.name for item in named_items],
			[get_name_key(item.item_name) for item in named_items],
		)

	def get_earlier_items(self) -> dict[str, str]:
		part_numbers = [row.part_number for row in self.parts if row.part_number]
		if not part_numbers:
			return {}

		part = frappe.qb.DocType("BOM Creator Item")
		design = frappe.qb.DocType("BOM Creator")
		rows = (
			frappe.qb.from_(part)
			.join(design)
			.on(design.name == part.parent)
			.select(part.part_number, part.item_code)
			.where(part.parenttype == "BOM Creator")
			.where(part.part_number.isin(part_numbers))
			.where(part.item_code.isnotnull() & (part.item_code != ""))
			.where(design.docstatus < 2)
			.orderby(design.modified)
			.run(as_dict=True)
		)
		return {row.part_number: row.item_code for row in rows if row.item_code in self.item_codes}

	def get_known_match(self, part, earlier_items: dict) -> dict | None:
		if part.part_number in earlier_items:
			return get_match(earlier_items[part.part_number], 100, "Earlier Design", True)

		if part.part_number in self.item_codes:
			return get_match(part.part_number, 100, "Item Code", True)

	def get_candidates(self, part) -> dict[str, tuple[float, str]]:
		candidates = {}
		code_key = get_code_key(part.part_number)
		for item_code, score in self.get_closest(code_key, self.codes, fuzz.ratio):
			candidates[item_code] = (score, "Item Code")

		name_key = get_name_key(part.part_name)
		for item_code, score in self.get_closest(name_key, self.names, fuzz.ratio):
			if score > candidates.get(item_code, (0,))[0]:
				candidates[item_code] = (score, "Item Name")

		return candidates

	def get_closest(self, query: str, choices: tuple[list, list], scorer) -> list[tuple[str, float]]:
		if not query:
			return []

		item_codes, keys = choices
		results = process.extract(
			query, keys, scorer=scorer, limit=CANDIDATE_LIMIT, score_cutoff=CANDIDATE_SCORE
		)
		numbers = get_numbers(query)
		return [
			(item_codes[index], score if get_numbers(key) == numbers else min(score, HIGH_SCORE - 1))
			for key, score, index in results
		]

	def get_descriptions(self, candidates: dict) -> dict[str, str]:
		item_codes = list({item_code for rows in candidates.values() for item_code in rows})
		if not item_codes:
			return {}

		items = frappe.get_all("Item", filters={"name": ("in", item_codes)}, fields=["name", "description"])
		return {item.name: strip_html(item.description or "") for item in items}

	def get_best_match(self, part, candidates: dict) -> dict | None:
		part_text = " ".join(filter(None, [part.part_name, strip_html(part.description or "")]))
		scores = []
		for item_code, (score, matched_on) in candidates.items():
			description_score = self.get_description_score(part_text, item_code)
			if description_score > score:
				score, matched_on = description_score, "Description"

			scores.append((score, item_code, matched_on))

		scores.sort(reverse=True)
		if not scores or scores[0][0] < MIN_SCORE:
			return None

		score, item_code, matched_on = scores[0]
		is_unique = len(scores) == 1 or scores[1][0] < score
		return get_match(item_code, score, matched_on, score >= HIGH_SCORE and is_unique)

	def get_description_score(self, part_text: str, item_code: str) -> float:
		description = self.descriptions.get(item_code)
		if not part_text or not description:
			return 0

		score = fuzz.token_set_ratio(part_text, description, processor=default_process)
		return min(score, HIGH_SCORE - 1)


def get_match(item_code: str, score: float, matched_on: str, is_selected: bool) -> dict:
	return {
		"item_code": item_code,
		"score": round(score),
		"matched_on": matched_on,
		"is_selected": is_selected,
	}


def get_part_key(part) -> tuple:
	return (part.part_number, part.part_name, part.description)


def get_code_key(value: str | None) -> str:
	return re.sub(r"[^0-9a-z]", "", (value or "").lower())


def get_name_key(value: str | None) -> str:
	words = re.sub(r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)", " ", default_process(value or ""))
	return " ".join(sorted(words.split()))


def get_numbers(value: str) -> list[str]:
	return sorted(number.lstrip("0") or "0" for number in re.findall(r"\d+", value))
