# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate

from erpnext.accounts.services.pricing.pricing_context import PricingContext


def coupon_gate(scheme, context: PricingContext) -> tuple[bool, str | None]:
	"""Gate for coupon_required schemes: (ok, rejection reason).

	Checks that the document carries an active coupon whose campaign
	links this scheme, within campaign validity, with redemption limits
	not exhausted, all against the Coupon Redemption ledger.
	"""
	if not context.coupon_code:
		return False, "coupon required but none on document"

	coupon = _get_active_coupon(context.coupon_code)
	if not coupon:
		return False, f"coupon {context.coupon_code} is missing or disabled"

	campaign = frappe.get_cached_doc("Coupon Campaign", coupon.campaign)
	if campaign.pricing_scheme != scheme.name:
		return False, f"coupon belongs to campaign {campaign.name} for a different scheme"
	if campaign.disabled:
		return False, f"campaign {campaign.name} is disabled"
	if not _campaign_date_valid(campaign, context.transaction_date):
		return False, f"campaign {campaign.name} not valid on {context.transaction_date}"
	return _within_limits(campaign, context)


def record_redemption(doc, coupon_name: str) -> None:
	"""Write (or revive) the redemption for this document's chain root.

	The redemption name is ``{coupon}::{root}``: an amended document
	inherits its root, so its submit revives the cancelled row instead
	of inserting; a concurrent duplicate insert fails on the primary key.
	"""
	root = get_order_chain_root(doc)
	existing = frappe.db.exists("Coupon Redemption", f"{coupon_name}::{root}")
	if existing:
		frappe.db.set_value("Coupon Redemption", existing, "status", "Redeemed")
		return

	frappe.get_doc(
		{
			"doctype": "Coupon Redemption",
			"coupon": coupon_name,
			"campaign": frappe.get_cached_value("Coupon", coupon_name, "campaign"),
			"order_chain_root": root,
			"voucher_type": doc.doctype,
			"voucher_no": doc.name,
			"party_type": "Customer" if doc.get("customer") else None,
			"party": doc.get("customer"),
			"posting_date": doc.get("transaction_date") or doc.get("posting_date") or nowdate(),
		}
	).insert(ignore_permissions=True)


def cancel_redemptions(doc) -> None:
	for name in frappe.get_all(
		"Coupon Redemption",
		filters={"voucher_type": doc.doctype, "voucher_no": doc.name, "status": "Redeemed"},
		pluck="name",
	):
		frappe.db.set_value("Coupon Redemption", name, "status", "Cancelled")


def get_order_chain_root(doc) -> str:
	"""The originating document name; amendments inherit their original's root."""
	name, amended_from = doc.name, doc.get("amended_from")
	while amended_from:
		name = amended_from
		amended_from = frappe.db.get_value(doc.doctype, name, "amended_from")
	return name


def _get_active_coupon(coupon_name: str):
	coupon = frappe.get_cached_value("Coupon", coupon_name, ("name", "campaign", "status"), as_dict=True)
	if not coupon or coupon.status != "Active":
		return None
	return coupon


def _campaign_date_valid(campaign, transaction_date: str) -> bool:
	date = getdate(transaction_date)
	if campaign.valid_from and date < getdate(campaign.valid_from):
		return False
	if campaign.valid_upto and date > getdate(campaign.valid_upto):
		return False
	return True


def _within_limits(campaign, context: PricingContext) -> tuple[bool, str | None]:
	if campaign.max_uses_total and _redemption_count(campaign.name) >= campaign.max_uses_total:
		return False, f"campaign {campaign.name} redemption limit reached"
	if (
		campaign.max_uses_per_customer
		and context.party
		and _redemption_count(campaign.name, context.party) >= campaign.max_uses_per_customer
	):
		return False, f"per-customer redemption limit reached for {context.party}"
	return True, None


def _redemption_count(campaign: str, party: str | None = None) -> int:
	filters = {"campaign": campaign, "status": "Redeemed"}
	if party:
		filters["party"] = party
	return frappe.db.count("Coupon Redemption", filters)
