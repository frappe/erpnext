# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from dataclasses import dataclass, field

import frappe
from frappe.utils import flt, getdate, nowdate


@dataclass(frozen=True)
class LineContext:
	"""One transaction line, normalized once: qty in stock UOM, amount in base currency."""

	key: str
	item_code: str
	item_group: str
	brand: str | None = None
	variant_of: str | None = None
	qty: float = 0.0
	stock_qty: float = 0.0
	uom: str | None = None
	price_list_rate: float = 0.0
	base_amount: float = 0.0
	warehouse: str | None = None
	is_free_item: bool = False
	inherited: bool = False
	ignore_pricing_scheme: bool = False

	@property
	def priceable(self) -> bool:
		return not (self.is_free_item or self.inherited or self.ignore_pricing_scheme)


@dataclass(frozen=True)
class PricingContext:
	"""Frozen input to the engine, built once per document and never mutated."""

	company: str
	currency: str
	transaction_type: str
	transaction_date: str
	conversion_rate: float = 1.0
	party_type: str | None = None
	party: str | None = None
	customer_group: str | None = None
	territory: str | None = None
	supplier_group: str | None = None
	sales_partner: str | None = None
	campaign: str | None = None
	price_list: str | None = None
	coupon_code: str | None = None
	composition: str = "Compound"
	lines: tuple[LineContext, ...] = field(default_factory=tuple)

	def priceable_lines(self) -> tuple[LineContext, ...]:
		return tuple(line for line in self.lines if line.priceable)


def build_pricing_context(doc) -> PricingContext:
	"""Build the frozen context from a transaction document."""
	party_type, party = _get_party(doc)
	return PricingContext(
		company=doc.company,
		currency=doc.currency,
		transaction_type=_get_transaction_type(doc),
		transaction_date=str(doc.get("transaction_date") or doc.get("posting_date") or nowdate()),
		conversion_rate=flt(doc.get("conversion_rate")) or 1.0,
		party_type=party_type,
		party=party,
		customer_group=_get_cached(party_type, party, "customer_group"),
		territory=_get_cached(party_type, party, "territory"),
		supplier_group=_get_cached(party_type, party, "supplier_group"),
		sales_partner=doc.get("sales_partner"),
		campaign=doc.get("campaign"),
		price_list=doc.get("selling_price_list") or doc.get("buying_price_list"),
		coupon_code=doc.get("pricing_coupon"),
		composition=get_discount_composition(),
		lines=tuple(_build_line(row, doc) for row in doc.get("items") or []),
	)


def get_discount_composition() -> str:
	return frappe.get_cached_value("Accounts Settings", None, "discount_composition") or "Compound"


def _build_line(row, doc) -> LineContext:
	item = frappe.get_cached_value("Item", row.item_code, ("item_group", "brand", "variant_of"), as_dict=True)
	# row.stock_qty is stale mid-validate after a qty edit, so always derive
	stock_qty = flt(row.get("qty")) * (flt(row.get("conversion_factor")) or 1.0)
	base_amount = (
		flt(row.get("price_list_rate")) * flt(row.get("qty")) * (flt(doc.get("conversion_rate")) or 1.0)
	)
	return LineContext(
		key=row.name or f"row-{row.idx}",
		item_code=row.item_code,
		item_group=item.item_group,
		brand=item.brand,
		variant_of=item.variant_of,
		qty=flt(row.get("qty")),
		stock_qty=stock_qty,
		uom=row.get("uom"),
		price_list_rate=flt(row.get("price_list_rate")),
		base_amount=base_amount,
		warehouse=row.get("warehouse"),
		is_free_item=bool(row.get("is_free_item")),
		inherited=is_inherited_row(row),
		ignore_pricing_scheme=bool(row.get("ignore_pricing_scheme")),
	)


def is_inherited_row(row) -> bool:
	"""A line mapped from an upstream document inherits its pricing (chain stability)."""
	upstream_fields = (
		"so_detail",
		"dn_detail",
		"sales_order_item",
		"delivery_note_item",
		"purchase_order_item",
		"po_detail",
		"pr_detail",
	)
	return any(row.get(field) for field in upstream_fields)


def _get_transaction_type(doc) -> str:
	selling_doctypes = ("Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "POS Invoice")
	return "Selling" if doc.doctype in selling_doctypes else "Buying"


def _get_party(doc) -> tuple[str | None, str | None]:
	if doc.get("customer"):
		return "Customer", doc.customer
	if doc.get("supplier"):
		return "Supplier", doc.supplier
	return None, None


def _get_cached(party_type: str | None, party: str | None, fieldname: str) -> str | None:
	if not party:
		return None
	source_doctype = {"customer_group": "Customer", "territory": "Customer", "supplier_group": "Supplier"}
	if party_type != source_doctype.get(fieldname):
		return None
	return frappe.get_cached_value(party_type, party, fieldname)
