# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from dataclasses import dataclass, field

from frappe.utils import flt

from erpnext.accounts.services.pricing.pricing_candidates import (
	CandidateRepository,
	get_accrued_basis,
	get_cap_usage,
)
from erpnext.accounts.services.pricing.pricing_context import LineContext, PricingContext
from erpnext.accounts.services.pricing.pricing_effects import (
	AmountDiscount,
	FreeItemEffect,
	HeaderDiscount,
	MarginEffect,
	PercentDiscount,
	PricingEffect,
	RateOverride,
)
from erpnext.accounts.services.pricing.pricing_matching import (
	evaluate_condition,
	item_in_scope,
	party_in_scope,
	select_tier,
)
from erpnext.accounts.services.pricing.pricing_resolution import SchemeMatch, resolve_winners
from erpnext.accounts.services.pricing.pricing_trace import PricingTrace


@dataclass
class PricingResult:
	effects: list[PricingEffect] = field(default_factory=list)
	trace: PricingTrace = field(default_factory=PricingTrace)
	composition: str = "Compound"

	def effects_for_line(self, line_key: str) -> list[PricingEffect]:
		return [e for e in self.effects if getattr(e, "line_key", None) == line_key]


class PricingEngine:
	"""resolve(context) -> PricingResult. Pure: no document writes, no cached-doc mutation."""

	def __init__(self, context: PricingContext, doc=None):
		self.context = context
		self.doc = doc
		self.trace = PricingTrace()

	def resolve(self) -> PricingResult:
		matches: list[SchemeMatch] = []
		for scheme in CandidateRepository().fetch(self.context):
			matches.extend(self._match_scheme(scheme))

		effects: list[PricingEffect] = []
		for match in resolve_winners(matches, self.trace):
			effects.extend(self._compute_effects(match))
			self.trace.matched(match.scheme.name, tier_idx=match.tier.idx)
		return PricingResult(effects=effects, trace=self.trace, composition=self.context.composition)

	def _match_scheme(self, scheme) -> list[SchemeMatch]:
		if not self._passes_gates(scheme):
			return []

		trigger_lines = [
			line for line in self.context.priceable_lines() if item_in_scope(line, scheme.trigger_scope)
		]
		if not trigger_lines:
			self.trace.rejected(scheme.name, "no lines in trigger scope")
			return []

		benefit_keys = self._benefit_line_keys(scheme, trigger_lines)
		if scheme.aggregation == "Per Line" and not scheme.benefit_scope:
			return self._per_line_matches(scheme, trigger_lines)
		return self._aggregate_match(scheme, trigger_lines, benefit_keys)

	def _passes_gates(self, scheme) -> bool:
		if not party_in_scope(self.context, scheme.party_scope):
			self.trace.rejected(scheme.name, "party not in scope")
			return False
		ok, error = evaluate_condition(scheme, self.doc)
		if error:
			self.trace.error(scheme.name, f"condition error: {error}")
			return False
		if not ok:
			self.trace.rejected(scheme.name, "condition evaluated false")
			return False
		return self._passes_caps(scheme)

	def _passes_caps(self, scheme) -> bool:
		if not (scheme.cap_total_applications or scheme.cap_total_discount_amount):
			return True
		applications, spend = get_cap_usage(scheme)
		if scheme.cap_total_applications and applications >= scheme.cap_total_applications:
			self.trace.rejected(scheme.name, f"application cap reached ({applications})")
			return False
		if scheme.cap_total_discount_amount and spend >= flt(scheme.cap_total_discount_amount):
			self.trace.rejected(scheme.name, f"discount budget exhausted ({spend})")
			return False
		return True

	def _per_line_matches(self, scheme, trigger_lines: list[LineContext]) -> list[SchemeMatch]:
		matches = []
		for line in trigger_lines:
			tier = select_tier(scheme.tiers, line.stock_qty, line.base_amount)
			if tier:
				matches.append(
					SchemeMatch(
						scheme=scheme,
						tier=tier,
						benefit_line_keys=(line.key,),
						basis_qty=line.stock_qty,
						basis_amount=line.base_amount,
						trigger_line_keys=(line.key,),
					)
				)
		if not matches:
			self.trace.rejected(scheme.name, "no tier matched any line")
		return matches

	def _aggregate_match(self, scheme, trigger_lines, benefit_keys) -> list[SchemeMatch]:
		qty = sum(line.stock_qty for line in trigger_lines)
		amount = sum(line.base_amount for line in trigger_lines)
		if scheme.aggregation == "Per Period":
			accrued_qty, accrued_amount = get_accrued_basis(scheme, self.context)
			qty, amount = qty + accrued_qty, amount + accrued_amount

		tier = select_tier(scheme.tiers, qty, amount)
		if not tier:
			self.trace.rejected(scheme.name, f"no tier for basis qty {qty}, amount {amount}")
			return []
		return [
			SchemeMatch(
				scheme=scheme,
				tier=tier,
				benefit_line_keys=benefit_keys,
				basis_qty=qty,
				basis_amount=amount,
				trigger_line_keys=tuple(line.key for line in trigger_lines),
			)
		]

	def _benefit_line_keys(self, scheme, trigger_lines) -> tuple[str, ...]:
		if not scheme.benefit_scope:
			return tuple(line.key for line in trigger_lines)
		return tuple(
			line.key for line in self.context.priceable_lines() if item_in_scope(line, scheme.benefit_scope)
		)

	def _compute_effects(self, match: SchemeMatch) -> list[PricingEffect]:
		scheme, tier = match.scheme, match.tier
		if scheme.effect_type == "Free Item":
			return self._free_item_effects(match)
		if scheme.effect_type == "Header Discount":
			return [
				HeaderDiscount(
					scheme=scheme.name,
					stacking_group=scheme.stacking_group,
					percentage=flt(tier.value),
					amount=0.0,
					apply_discount_on=scheme.apply_discount_on or "Grand Total",
				)
			]
		return [self._line_effect(scheme, tier, key) for key in match.benefit_line_keys]

	def _line_effect(self, scheme, tier, line_key: str) -> PricingEffect:
		common = {"scheme": scheme.name, "stacking_group": scheme.stacking_group, "line_key": line_key}
		if scheme.effect_type == "Rate":
			return RateOverride(rate=flt(tier.value), currency=scheme.currency, **common)
		if scheme.effect_type == "Margin":
			return MarginEffect(
				margin_type=tier.margin_type, value=flt(tier.value), currency=scheme.currency, **common
			)
		if scheme.effect_type == "Discount Amount":
			return AmountDiscount(amount=flt(tier.value), currency=scheme.currency, **common)
		return PercentDiscount(percentage=flt(tier.value), **common)

	def _free_item_effects(self, match: SchemeMatch) -> list[PricingEffect]:
		tier = match.tier
		free_qty = _recurring_free_qty(tier, match.basis_qty)
		if not free_qty:
			return []
		if tier.free_item:
			return [self._free_effect(match, tier.free_item, free_qty, None)]
		return [
			self._free_effect(match, self._line_by_key(key).item_code, free_qty, key)
			for key in match.trigger_line_keys
		]

	def _free_effect(self, match: SchemeMatch, item_code: str, qty: float, source_key: str | None):
		tier = match.tier
		return FreeItemEffect(
			scheme=match.scheme.name,
			stacking_group=match.scheme.stacking_group,
			item_code=item_code,
			qty=qty,
			uom=tier.free_item_uom,
			rate=flt(tier.free_item_rate),
			source_line_key=source_key,
		)

	def _line_by_key(self, key: str) -> LineContext:
		return next(line for line in self.context.lines if line.key == key)


def _recurring_free_qty(tier, basis_qty: float) -> float:
	if not flt(tier.recurrence_qty):
		return flt(tier.free_qty)
	units = flt(basis_qty) / flt(tier.recurrence_qty)
	if tier.round_down_recurrence:
		units = int(units)
	return units * flt(tier.free_qty)
