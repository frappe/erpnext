# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from dataclasses import dataclass, field

from frappe.utils import cint

from erpnext.accounts.services.pricing.pricing_trace import PricingTrace


@dataclass
class SchemeMatch:
	"""A scheme that matched, with its selected tier and target lines."""

	scheme: object
	tier: object
	benefit_line_keys: tuple[str, ...]
	basis_qty: float = 0.0
	basis_amount: float = 0.0
	trigger_line_keys: tuple[str, ...] = field(default_factory=tuple)


def resolve_winners(matches: list[SchemeMatch], trace: PricingTrace) -> list[SchemeMatch]:
	"""Within a stacking group exactly one scheme wins (highest priority);
	across groups all winners compose. Equal-priority ties are broken
	deterministically by scheme name — authoring-time validation is meant
	to prevent them; the engine never throws at data entry.
	"""
	by_group: dict[str, list[SchemeMatch]] = {}
	for match in matches:
		by_group.setdefault(match.scheme.stacking_group, []).append(match)

	winners: list[SchemeMatch] = []
	for group_matches in by_group.values():
		winners.extend(_group_winner(group_matches, trace))
	return winners


def _group_winner(group_matches: list[SchemeMatch], trace: PricingTrace) -> list[SchemeMatch]:
	def rank(match: SchemeMatch) -> tuple[int, str]:
		return (-cint(match.scheme.priority), match.scheme.name)

	winning_scheme = min(group_matches, key=rank).scheme
	for match in group_matches:
		if match.scheme.name != winning_scheme.name:
			trace.shadowed(match.scheme.name, by=winning_scheme.name)
	return [match for match in group_matches if match.scheme.name == winning_scheme.name]
