# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

APPLY_ON_TABLES = {
	"Item Code": ("items", "item_code", "Item"),
	"Item Group": ("item_groups", "item_group", "Item Group"),
	"Brand": ("brands", "brand", "Brand"),
}
PARTY_FIELDS = {
	"Customer": "customer",
	"Customer Group": "customer_group",
	"Territory": "territory",
	"Sales Partner": "sales_partner",
	"Campaign": "campaign",
	"Supplier": "supplier",
	"Supplier Group": "supplier_group",
}


class PricingRuleConverter:
	"""Converts one legacy Pricing Rule into Pricing Scheme document dicts,
	classifying the conversion per spec section 13.3: clean / behavior
	change / needs review. Preserves observed behavior; rules whose legacy
	behavior cannot be reproduced faithfully are flagged, never silently
	reinterpreted.
	"""

	def __init__(self, rule, stacking_group: str):
		self.rule = rule
		self.stacking_group = stacking_group
		self.notes: list[str] = []
		self.classification = "clean"

	def convert(self) -> list[dict]:
		schemes = []
		for direction in self._directions():
			for effect_type, tier in self._effects():
				schemes.append(self._build_scheme(direction, effect_type, tier))
		self._classify()
		return schemes

	def _directions(self) -> list[str]:
		directions = []
		if self.rule.selling:
			directions.append("Selling")
		if self.rule.buying:
			directions.append("Buying")
		if len(directions) == 2:
			self._note("applies to both selling and buying, split into two schemes")
		return directions

	def _effects(self) -> list[tuple[str, dict]]:
		effects = []
		if self.rule.price_or_product_discount == "Product":
			effects.append(("Free Item", self._free_item_tier()))
		elif self.rule.apply_on == "Transaction":
			effects.append(("Header Discount", self._tier(value=flt(self.rule.discount_percentage))))
			if self.rule.rate_or_discount == "Discount Amount":
				self._review("amount-based transaction discount is percentage-only in v1")
		else:
			effects.append(self._price_effect())
		if self.rule.margin_type and flt(self.rule.margin_rate_or_amount) and effects[0][0] != "Margin":
			effects.append(
				(
					"Margin",
					self._tier(value=flt(self.rule.margin_rate_or_amount), margin_type=self.rule.margin_type),
				)
			)
			self._note("margin and discount split into two composing schemes")
		return effects

	def _price_effect(self) -> tuple[str, dict]:
		kind = self.rule.rate_or_discount
		if kind == "Rate":
			return ("Rate", self._tier(value=flt(self.rule.rate)))
		if kind == "Discount Amount":
			return ("Discount Amount", self._tier(value=flt(self.rule.discount_amount)))
		return ("Discount Percentage", self._tier(value=flt(self.rule.discount_percentage)))

	def _tier(self, **kwargs) -> dict:
		return {
			"min_qty": flt(self.rule.min_qty),
			"max_qty": flt(self.rule.max_qty),
			"min_amount": flt(self.rule.min_amt),
			"max_amount": flt(self.rule.max_amt),
			**kwargs,
		}

	def _free_item_tier(self) -> dict:
		tier = self._tier(
			free_item=None if self.rule.same_item else self.rule.free_item,
			free_qty=flt(self.rule.free_qty) or 1,
			free_item_uom=self.rule.free_item_uom,
			free_item_rate=flt(self.rule.free_item_rate),
		)
		if self.rule.is_recursive:
			tier["recurrence_qty"] = flt(self.rule.recurse_for)
			tier["round_down_recurrence"] = cint(self.rule.round_free_qty)
			if flt(self.rule.apply_recursion_over):
				self._review("apply_recursion_over has no direct equivalent; recurrence approximated")
		return tier

	def _build_scheme(self, direction: str, effect_type: str, tier: dict) -> dict:
		return {
			"doctype": "Pricing Scheme",
			"title": self._title(direction, effect_type),
			"legacy_pricing_rule": self.rule.name,
			"effect_type": effect_type,
			"transaction_type": direction,
			"company": self.rule.company,
			"currency": self.rule.currency,
			"price_list": self.rule.for_price_list,
			"warehouse": self.rule.warehouse,
			"valid_from": self.rule.valid_from,
			"valid_upto": self.rule.valid_upto,
			"disabled": cint(self.rule.disable or self.rule.validate_applied_rule),
			"stacking_group": self.stacking_group if effect_type not in ("Rate", "Margin") else "Default",
			"priority": cint(self.rule.priority) or 1,
			"aggregation": self._aggregation(),
			"period_window": "Validity Period" if self.rule.is_cumulative else None,
			"apply_discount_on": self.rule.apply_discount_on or "Grand Total",
			"coupon_required": cint(self.rule.coupon_code_based),
			"condition": self.rule.condition,
			"applies_to": "All Items" if self.rule.apply_on == "Transaction" else "Specific Items",
			"trigger_scope": self._trigger_scope(),
			"benefit_scope": self._benefit_scope(),
			"party_scope": self._party_scope(),
			"tiers": [tier],
		}

	def _title(self, direction: str, effect_type: str) -> str:
		base = self.rule.title or self.rule.name
		suffix = f" ({effect_type})" if effect_type == "Margin" else ""
		direction_suffix = f" [{direction}]" if self.rule.selling and self.rule.buying else ""
		return f"{base}{suffix}{direction_suffix}"

	def _aggregation(self) -> str:
		if self.rule.is_cumulative:
			return "Per Period"
		if self.rule.mixed_conditions:
			return "Per Document"
		return "Per Line Item"

	def _trigger_scope(self) -> list[dict]:
		if self.rule.apply_on == "Transaction":
			return []
		table, field, scope_type = APPLY_ON_TABLES[self.rule.apply_on]
		return [
			{"scope_type": scope_type, "value": row.get(field), "uom": row.get("uom")}
			for row in self.rule.get(table)
			if row.get(field)
		]

	def _benefit_scope(self) -> list[dict]:
		if not self.rule.apply_rule_on_other:
			return []
		scope_type = self.rule.apply_rule_on_other
		value = self.rule.get("other_" + frappe.scrub(scope_type))
		return (
			[{"scope_type": "Item" if scope_type == "Item Code" else scope_type, "value": value}]
			if value
			else []
		)

	def _party_scope(self) -> list[dict]:
		party_type = self.rule.applicable_for
		if not party_type or party_type not in PARTY_FIELDS:
			return []
		value = self.rule.get(PARTY_FIELDS[party_type])
		return [{"party_type": party_type, "value": value}] if value else []

	def _classify(self) -> None:
		if self.rule.validate_applied_rule:
			self._review(
				"validation-only rule; Pricing Scheme always applies its effect, so this is inserted disabled"
			)
		if self.rule.promotional_scheme:
			self._review("generated by Promotional Scheme; consolidate slabs into one scheme's tiers")
		if self.rule.coupon_code_based:
			self._review("coupon-based; create a Coupon Campaign and link the codes")
		if self.rule.apply_multiple_pricing_rules and self.rule.rate_or_discount == "Discount Percentage":
			self._change(
				"stacked percentages: composition now follows the site-level Discount Composition setting"
			)
		if self.rule.is_cumulative:
			self._change("cumulative accrual is now scoped per party/company (was unscoped)")
		if flt(self.rule.min_amt) or flt(self.rule.max_amt):
			self._change("amount bands now measured in base currency, pre-discount")
		if self.rule.apply_discount_on_rate:
			self._change("discount-on-discounted-rate now follows the composition setting")
		if self.rule.threshold_percentage:
			self._note("threshold suggestion dropped; near-miss nudges are computed from tiers")

	def _note(self, message: str) -> None:
		self.notes.append(message)

	def _change(self, message: str) -> None:
		self.notes.append(message)
		if self.classification == "clean":
			self.classification = "behavior change"

	def _review(self, message: str) -> None:
		self.notes.append(message)
		self.classification = "needs review"


@frappe.whitelist()
def convert_legacy_pricing_rules(dry_run: int = 1) -> dict:
	"""Convert every not-yet-converted legacy Pricing Rule. Idempotent:
	rules already linked from a Pricing Scheme are skipped. Conflicting
	conversions are inserted disabled and flagged for review: disabling
	a live discount silently would itself be a behavior change, but so
	would letting two same-priority schemes race (spec section 13.1)."""
	dry_run = cint(dry_run)
	rules = _pending_rules()
	_ensure_stacking_groups(rules, dry_run)

	report = {"converted": [], "skipped": _converted_rule_names(), "composition": None}
	stack_counter = 0
	for rule in rules:
		stacking_group = "Default"
		if rule.apply_multiple_pricing_rules and rule.price_or_product_discount != "Product":
			stack_counter += 1
			stacking_group = f"Legacy Stack {stack_counter}"
		report["converted"].append(_convert_one(rule, stacking_group, dry_run))

	report["composition"] = _apply_composition_mode(rules, dry_run)
	return report


def _convert_one(rule, stacking_group: str, dry_run: int) -> dict:
	converter = PricingRuleConverter(rule, stacking_group)
	schemes = converter.convert()
	inserted = []
	for scheme_dict in schemes:
		if dry_run:
			inserted.append(scheme_dict["title"])
			continue
		inserted.append(_insert_scheme(scheme_dict, converter))
	return {
		"rule": rule.name,
		"schemes": inserted,
		"classification": converter.classification,
		"notes": converter.notes,
	}


def _insert_scheme(scheme_dict: dict, converter: PricingRuleConverter) -> str:
	doc = frappe.get_doc(scheme_dict)
	try:
		doc.insert(ignore_permissions=True)
	except frappe.ValidationError:
		doc.disabled = 1
		doc.insert(ignore_permissions=True)
		converter._review("conflicts with another converted scheme; inserted disabled, resolve priority")
	return doc.name


def _pending_rules() -> list:
	converted = _converted_rule_names()
	names = frappe.get_all(
		"Pricing Rule",
		filters={"name": ("not in", converted or [""])},
		order_by="creation asc",
		pluck="name",
	)
	return [frappe.get_doc("Pricing Rule", name) for name in names]


def _converted_rule_names() -> list[str]:
	return frappe.get_all(
		"Pricing Scheme",
		filters={"legacy_pricing_rule": ("is", "set")},
		pluck="legacy_pricing_rule",
		distinct=True,
	)


def _ensure_stacking_groups(rules: list, dry_run: int) -> None:
	needed = sum(
		1 for r in rules if r.apply_multiple_pricing_rules and r.price_or_product_discount != "Product"
	)
	if dry_run or not needed:
		return
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	meta_options = (frappe.get_meta("Pricing Scheme").get_field("stacking_group").options or "").split("\n")
	options = list(dict.fromkeys(meta_options + [f"Legacy Stack {i}" for i in range(1, needed + 1)]))
	make_property_setter("Pricing Scheme", "stacking_group", "options", "\n".join(options), "Text")
	frappe.clear_cache(doctype="Pricing Scheme")


def _apply_composition_mode(rules: list, dry_run: int) -> str:
	"""Preserve observed behavior: legacy stacked percentages composed additively."""
	stacked_percent = any(
		r.apply_multiple_pricing_rules and r.rate_or_discount == "Discount Percentage" for r in rules
	)
	mode = "Additive" if stacked_percent else "Compound"
	if not dry_run and stacked_percent:
		frappe.db.set_single_value("Accounts Settings", "discount_composition", "Additive")
	return mode


@frappe.whitelist()
def replay_recent_documents(days: int = 90, limit: int = 100) -> dict:
	"""Re-price recent submitted documents under the new engine, read-only,
	and diff against their stored rates: the only reliable detector for
	combination-dependent legacy behavior (spec section 13.3). Run after
	conversion, before cutover.
	"""
	from erpnext.accounts.services.pricing.pricing_applier import baseline_rate
	from erpnext.accounts.services.pricing.pricing_context import build_pricing_context
	from erpnext.accounts.services.pricing.pricing_effects import compose_line_rate
	from erpnext.accounts.services.pricing.pricing_engine import PricingEngine

	report = {"documents_checked": 0, "lines_checked": 0, "lines_changed": 0, "total_delta": 0.0, "diffs": []}
	for doctype, docname in _recent_documents(cint(days), cint(limit)):
		doc = frappe.get_doc(doctype, docname)
		context = build_pricing_context(doc)
		result = PricingEngine(context, doc=doc).resolve()
		report["documents_checked"] += 1
		_diff_document(doc, context, result, report, compose_line_rate, baseline_rate)

	report["diffs"] = sorted(report["diffs"], key=lambda d: abs(d["delta"]), reverse=True)[:20]
	report["total_delta"] = flt(report["total_delta"], 2)
	return report


def _recent_documents(days: int, limit: int) -> list[tuple[str, str]]:
	from frappe.utils import add_days, nowdate

	cutoff = add_days(nowdate(), -days)
	documents = []
	for doctype, date_field in (("Sales Order", "transaction_date"), ("Sales Invoice", "posting_date")):
		filters = {"docstatus": 1, date_field: (">=", cutoff)}
		if frappe.get_meta(doctype).has_field("is_return"):
			filters["is_return"] = 0
		names = frappe.get_all(
			doctype,
			filters=filters,
			order_by=f"{date_field} desc",
			limit=limit,
			pluck="name",
		)
		documents.extend((doctype, name) for name in names)
	return documents[: limit * 2]


def _diff_document(doc, context, result, report: dict, compose_line_rate, baseline_rate) -> None:
	priceable_keys = {line.key for line in context.priceable_lines()}
	for item in doc.get("items"):
		if item.name not in priceable_keys:
			continue
		report["lines_checked"] += 1
		new_rate = flt(
			compose_line_rate(
				baseline_rate(item),
				result.effects_for_line(item.name),
				composition=result.composition,
				conversion_rate=flt(doc.get("conversion_rate")) or 1.0,
				document_currency=doc.currency,
			),
			item.precision("rate"),
		)
		if new_rate == flt(item.rate):
			continue
		report["lines_changed"] += 1
		delta = flt((new_rate - flt(item.rate)) * flt(item.qty), 2)
		report["total_delta"] += delta
		report["diffs"].append(
			{
				"voucher_type": doc.doctype,
				"voucher_no": doc.name,
				"item_code": item.item_code,
				"old_rate": flt(item.rate),
				"new_rate": new_rate,
				"delta": delta,
			}
		)
