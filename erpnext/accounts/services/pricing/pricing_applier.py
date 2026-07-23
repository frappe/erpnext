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
BUYING_DOCTYPES = ("Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice")
TRANSACTION_DOCTYPES = SELLING_DOCTYPES + BUYING_DOCTYPES


class EffectApplier:
	"""Map a PricingResult onto a document: the only place the engine touches fields.

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
		return baseline_rate(item)

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
				row = self._append_free_row(effect)
				changed = True
			self._inherit_source_line_values(row, effect)
			self._set_missing_row_details(row)
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

	def _append_free_row(self, effect: FreeItemEffect):
		item = frappe.get_cached_value(
			"Item", effect.item_code, ("item_name", "description", "stock_uom"), as_dict=True
		)
		return self.doc.append(
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
				"schedule_date": self.doc.get("schedule_date"),
			},
		)

	def _inherit_source_line_values(self, row, effect: FreeItemEffect) -> None:
		"""The freebie belongs to the sale that earned it: accounting and
		inventory dimensions and mandatory custom fields carry over from
		the trigger line."""
		source = self._source_row(effect)
		if not source:
			return
		for fieldname in _inheritable_fieldnames(row):
			if row.get(fieldname) is None and source.get(fieldname) is not None:
				row.set(fieldname, source.get(fieldname))

	def _set_missing_row_details(self, row) -> None:
		"""Fill the accounting defaults (income and expense account, cost
		center, tax template) that the controller's enrichment pass had
		already run for user-entered rows before this row existed."""
		from erpnext.stock.get_item_details import get_item_details

		context = frappe._dict(
			{fieldname: self.doc.get(fieldname) for fieldname in self.doc.meta.get_valid_columns()}
		)
		context.update(row.as_dict())
		context.update(
			{
				"doctype": self.doc.doctype,
				"name": self.doc.name,
				"child_doctype": row.doctype,
				"child_docname": row.name,
				"transaction_date": context.transaction_date or context.posting_date,
			}
		)
		if self.doc.doctype in SELLING_DOCTYPES:
			context.document_type = f"{self.doc.doctype} Item"
		details = get_item_details(context, self.doc, for_validate=True, overwrite_warehouse=False)
		for fieldname, value in details.items():
			if row.meta.get_field(fieldname) and value is not None and row.get(fieldname) is None:
				row.set(fieldname, value)

	def _default_warehouse(self, effect: FreeItemEffect) -> str | None:
		source = self._source_row(effect)
		return (source and source.get("warehouse")) or self.doc.get("set_warehouse")

	def _source_row(self, effect: FreeItemEffect):
		"""The trigger line the freebie came from. Free rows never qualify:
		an unsaved appended row has no name and would match a missing
		source_line_key as None == None."""
		return next(
			(
				row
				for row in self.doc.get("items")
				if not row.get("is_free_item") and row.name and row.name == effect.source_line_key
			),
			None,
		)

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
	if doc.doctype not in TRANSACTION_DOCTYPES or doc.get("is_return"):
		return False
	if doc.get("ignore_pricing_rule"):
		return False
	return is_pricing_scheme_engine_enabled()


def is_pricing_scheme_engine_enabled() -> bool:
	return frappe.get_cached_value("Accounts Settings", None, "pricing_engine") == "Pricing Scheme"


def _inheritable_fieldnames(row) -> set[str]:
	from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
		get_accounting_dimensions,
	)
	from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions

	fieldnames = {"cost_center", "project"}
	fieldnames.update(get_accounting_dimensions())
	fieldnames.update(dimension.source_fieldname for dimension in get_inventory_dimensions())
	fieldnames.update(field.fieldname for field in row.meta.get_custom_fields() if field.reqd)
	return {fieldname for fieldname in fieldnames if row.meta.has_field(fieldname)}


def baseline_rate(item) -> float:
	"""Price list rate after user-owned discounts; engine effects never feed back."""
	if flt(item.price_list_rate):
		if flt(item.discount_percentage):
			# discount_amount is the framework-derived mirror of the percentage
			return flt(item.price_list_rate) * (1 - flt(item.discount_percentage) / 100)
		return flt(item.price_list_rate) - flt(item.discount_amount)
	# no catalog rate: the current rate plus prior engine discount is already post-manual
	return flt(item.rate) + flt(item.get("scheme_discount_amount"))
