# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

from erpnext.accounts.services.pricing.pricing_context import build_pricing_context, is_inherited_row
from erpnext.accounts.services.pricing.pricing_effects import (
	FreeItemEffect,
	HeaderDiscount,
	compose_line_rate,
)
from erpnext.accounts.services.pricing.pricing_engine import PricingEngine, PricingResult

SELLING_DOCTYPES = ("Quotation", "Sales Order", "Delivery Note", "Sales Invoice")


class EffectApplier:
	"""Map a PricingResult onto a document — the only place the engine touches fields.

	Invariants (spec section 6.3): always recomputes from baseline (price
	list rate + user-owned discounts), never from previously applied
	values; writes only engine-owned fields plus the derived ``rate``;
	free rows are reconciled derived state. Lines without current or
	prior engine effects are left completely untouched, preserving
	manually negotiated rates.
	"""

	def __init__(self, doc, result: PricingResult):
		self.doc = doc
		self.result = result

	def apply(self) -> bool:
		changed = self._apply_line_effects()
		changed = self._reconcile_free_items() or changed
		changed = self._apply_header_discount() or changed
		return changed

	def _apply_line_effects(self) -> bool:
		changed = False
		for item in self.doc.get("items"):
			if item.get("is_free_item") or is_inherited_row(item):
				continue  # free rows are reconciled; inherited lines keep upstream pricing
			effects = self.result.effects_for_line(item.name) if item.name else []
			if not effects and not flt(item.get("scheme_discount_amount")):
				continue
			changed = self._set_line_rate(item, effects) or changed
		return changed

	def _set_line_rate(self, item, effects: list) -> bool:
		baseline = self._baseline_rate(item)
		rate = compose_line_rate(
			baseline,
			effects,
			composition=self.result.composition,
			conversion_rate=flt(self.doc.get("conversion_rate")) or 1.0,
			document_currency=self.doc.currency,
		)
		discount = flt(baseline - rate, item.precision("rate"))
		if flt(item.get("scheme_discount_amount")) == discount and flt(item.rate) == flt(
			baseline - discount, item.precision("rate")
		):
			return False
		item.scheme_discount_amount = discount
		item.rate = flt(baseline - discount, item.precision("rate"))
		return True

	def _baseline_rate(self, item) -> float:
		"""Price list rate after user-owned discounts — engine effects never feed back."""
		if flt(item.price_list_rate):
			if flt(item.discount_percentage):
				# discount_amount is the framework-derived mirror of the percentage
				return flt(item.price_list_rate) * (1 - flt(item.discount_percentage) / 100)
			return flt(item.price_list_rate) - flt(item.discount_amount)
		# no catalog rate: the current rate plus prior engine discount is already post-manual
		return flt(item.rate) + flt(item.get("scheme_discount_amount"))

	def _reconcile_free_items(self) -> bool:
		desired = {
			(e.scheme, e.item_code, e.source_line_key or ""): e
			for e in self.result.effects
			if isinstance(e, FreeItemEffect)
		}
		changed = self._remove_stale_free_rows(desired)
		for key, effect in desired.items():
			row = self._find_free_row(key)
			if row:
				changed = self._update_free_row(row, effect) or changed
			else:
				self._append_free_row(effect)
				changed = True
		return changed

	def _remove_stale_free_rows(self, desired: dict) -> bool:
		stale = [
			row
			for row in self.doc.get("items")
			if row.get("is_free_item")
			and row.get("pricing_scheme")
			and (row.pricing_scheme, row.item_code, row.get("pricing_scheme_source_line") or "")
			not in desired
		]
		for row in stale:
			self.doc.remove(row)
		return bool(stale)

	def _find_free_row(self, key: tuple):
		for row in self.doc.get("items"):
			if (
				row.get("is_free_item")
				and (row.get("pricing_scheme"), row.item_code, row.get("pricing_scheme_source_line") or "")
				== key
			):
				return row
		return None

	def _update_free_row(self, row, effect: FreeItemEffect) -> bool:
		if flt(row.qty) == flt(effect.qty) and flt(row.rate) == flt(effect.rate):
			return False
		row.qty = effect.qty
		row.rate = row.price_list_rate = effect.rate
		return True

	def _append_free_row(self, effect: FreeItemEffect) -> None:
		item = frappe.get_cached_value(
			"Item", effect.item_code, ("item_name", "description", "stock_uom"), as_dict=True
		)
		self.doc.append(
			"items",
			{
				"item_code": effect.item_code,
				"item_name": item.item_name,
				"description": item.description,
				"qty": effect.qty,
				"uom": effect.uom or item.stock_uom,
				"stock_uom": item.stock_uom,
				"conversion_factor": 1.0,
				"rate": effect.rate,
				"price_list_rate": effect.rate,
				"discount_percentage": 0,
				"is_free_item": 1,
				"pricing_scheme": effect.scheme,
				"pricing_scheme_source_line": effect.source_line_key,
				"warehouse": self._default_warehouse(effect),
				"delivery_date": self.doc.get("delivery_date"),
			},
		)

	def _default_warehouse(self, effect: FreeItemEffect) -> str | None:
		source = next((row for row in self.doc.get("items") if row.name == effect.source_line_key), None)
		return (source and source.get("warehouse")) or self.doc.get("set_warehouse")

	def _apply_header_discount(self) -> bool:
		headers = [e for e in self.result.effects if isinstance(e, HeaderDiscount)]
		if not headers:
			return False
		total = min(sum(flt(e.percentage) for e in headers), 100.0)
		self.doc.apply_discount_on = headers[0].apply_discount_on
		self.doc.additional_discount_percentage = total
		return True


def apply_pricing_schemes(doc) -> None:
	"""Validate-time entry point: resolve and apply. No-op unless the site
	runs the Pricing Scheme engine and the document participates."""
	if not should_apply(doc):
		return
	context = build_pricing_context(doc)
	result = PricingEngine(context, doc=doc).resolve()
	if EffectApplier(doc, result).apply():
		doc.calculate_taxes_and_totals()


def should_apply(doc) -> bool:
	if doc.doctype not in SELLING_DOCTYPES or doc.get("is_return"):
		return False
	if doc.get("ignore_pricing_rule"):
		return False
	return is_pricing_scheme_engine_enabled()


def is_pricing_scheme_engine_enabled() -> bool:
	return frappe.get_cached_value("Accounts Settings", None, "pricing_engine") == "Pricing Scheme"
