# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from dataclasses import dataclass

from frappe.utils import flt


@dataclass(frozen=True)
class PricingEffect:
	"""Base class for typed engine outputs. Effects are values, never document writes."""

	scheme: str
	stacking_group: str


@dataclass(frozen=True)
class RateOverride(PricingEffect):
	line_key: str
	rate: float
	currency: str | None = None


@dataclass(frozen=True)
class MarginEffect(PricingEffect):
	line_key: str
	margin_type: str
	value: float
	currency: str | None = None


@dataclass(frozen=True)
class PercentDiscount(PricingEffect):
	line_key: str
	percentage: float


@dataclass(frozen=True)
class AmountDiscount(PricingEffect):
	line_key: str
	amount: float
	currency: str | None = None


@dataclass(frozen=True)
class FreeItemEffect(PricingEffect):
	item_code: str
	qty: float
	uom: str | None
	rate: float
	source_line_key: str | None = None


@dataclass(frozen=True)
class HeaderDiscount(PricingEffect):
	percentage: float
	amount: float
	apply_discount_on: str


def compose_line_rate(
	base_rate: float,
	effects: list[PricingEffect],
	composition: str = "Compound",
	conversion_rate: float = 1.0,
	document_currency: str | None = None,
) -> float:
	"""Fold a line's effects into a final rate — the pure math of section 6.2.

	Pipeline: RateOverride -> Margin -> percentages (compound or additive)
	-> amount discounts (currency-converted). Free items and header
	discounts do not change the line rate. Both percentage folds are
	commutative; in Additive mode percentage margins fold into the common
	base as signed terms and the summed percentage is clamped at 100.
	"""
	rate = _apply_rate_overrides(base_rate, effects, conversion_rate, document_currency)
	if composition == "Additive":
		rate = _fold_additive(rate, effects)
	else:
		rate = _fold_compound(rate, effects)
	return max(rate - _amount_discount_per_unit(effects, conversion_rate, document_currency), 0.0)


def _apply_rate_overrides(
	base_rate: float,
	effects: list[PricingEffect],
	conversion_rate: float,
	document_currency: str | None,
) -> float:
	overrides = [e for e in effects if isinstance(e, RateOverride)]
	if not overrides:
		return base_rate
	last = overrides[-1]
	return _convert(flt(last.rate), last.currency, document_currency, conversion_rate)


def _fold_compound(rate: float, effects: list[PricingEffect]) -> float:
	for effect in effects:
		if isinstance(effect, MarginEffect):
			rate = _apply_margin(rate, effect)
	for effect in effects:
		if isinstance(effect, PercentDiscount):
			rate *= 1 - flt(effect.percentage) / 100
	return rate


def _fold_additive(rate: float, effects: list[PricingEffect]) -> float:
	"""Sum all signed percentages on the common base; amount margins keep their stage."""
	net_percent = 0.0
	for effect in effects:
		if isinstance(effect, PercentDiscount):
			net_percent += flt(effect.percentage)
		elif isinstance(effect, MarginEffect) and effect.margin_type == "Percentage":
			net_percent -= flt(effect.value)
		elif isinstance(effect, MarginEffect):
			rate = _apply_margin(rate, effect)
	return rate * (1 - min(net_percent, 100.0) / 100)


def _apply_margin(rate: float, effect: MarginEffect) -> float:
	if effect.margin_type == "Percentage":
		return rate * (1 + flt(effect.value) / 100)
	return rate + flt(effect.value)


def _amount_discount_per_unit(
	effects: list[PricingEffect], conversion_rate: float, document_currency: str | None
) -> float:
	total = 0.0
	for effect in effects:
		if isinstance(effect, AmountDiscount):
			total += _convert(flt(effect.amount), effect.currency, document_currency, conversion_rate)
	return total


def _convert(
	amount: float, from_currency: str | None, to_currency: str | None, conversion_rate: float
) -> float:
	if not from_currency or not to_currency or from_currency == to_currency:
		return amount
	# scheme amounts are authored in base currency; document currency = base / conversion_rate
	return amount / (flt(conversion_rate) or 1.0)
