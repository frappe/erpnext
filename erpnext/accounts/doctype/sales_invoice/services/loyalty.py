# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Loyalty program helpers for Sales Invoice."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate

from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
	get_loyalty_program_details_with_points,
)


class LoyaltyService:
	def __init__(self, doc):
		self.doc = doc

	def make_loyalty_point_entry(self) -> None:
		doc = self.doc
		returned_amount = self._get_returned_amount()
		current_amount = flt(doc.grand_total) - cint(doc.loyalty_amount)
		eligible_amount = current_amount - returned_amount
		lp_details = get_loyalty_program_details_with_points(
			doc.customer,
			company=doc.company,
			current_transaction_amount=current_amount,
			loyalty_program=doc.loyalty_program,
			expiry_date=doc.posting_date,
			include_expired_entry=True,
		)
		if (
			lp_details
			and getdate(lp_details.from_date) <= getdate(doc.posting_date)
			and (not lp_details.to_date or getdate(lp_details.to_date) >= getdate(doc.posting_date))
		):
			collection_factor = lp_details.collection_factor if lp_details.collection_factor else 1.0
			points_earned = cint(eligible_amount / collection_factor)

			entry = frappe.get_doc(
				{
					"doctype": "Loyalty Point Entry",
					"company": doc.company,
					"loyalty_program": lp_details.loyalty_program,
					"loyalty_program_tier": lp_details.tier_name,
					"customer": doc.customer,
					"invoice_type": doc.doctype,
					"invoice": doc.name,
					"loyalty_points": points_earned,
					"purchase_amount": eligible_amount,
					"expiry_date": add_days(doc.posting_date, lp_details.expiry_duration),
					"posting_date": doc.posting_date,
				}
			)
			entry.flags.ignore_permissions = 1
			entry.save()
			self._set_loyalty_program_tier()

	def delete_loyalty_point_entry(self) -> None:
		doc = self.doc
		lp_entry = frappe.db.get_all(
			"Loyalty Point Entry", filters={"invoice": doc.name, "loyalty_points": (">", 0)}, fields=["name"]
		)

		if not lp_entry:
			return

		against_lp_entry = frappe.db.get_all(
			"Loyalty Point Entry",
			filters={"redeem_against": lp_entry[0].name},
			fields=["name", "invoice"],
		)

		if against_lp_entry:
			invoice_list = ", ".join([d.invoice for d in against_lp_entry])
			frappe.throw(
				_(
					"{} can't be cancelled since the Loyalty Points earned has been redeemed. "
					"First cancel the {} No {}"
				).format(doc.doctype, doc.doctype, invoice_list)
			)
		else:
			frappe.db.delete("Loyalty Point Entry", filters={"invoice": doc.name})
			self._set_loyalty_program_tier()

	def apply_loyalty_points(self) -> None:
		from erpnext.accounts.doctype.loyalty_point_entry.loyalty_point_entry import (
			get_loyalty_point_entries,
			get_redemption_details,
		)

		doc = self.doc
		loyalty_point_entries = get_loyalty_point_entries(
			doc.customer, doc.loyalty_program, doc.company, doc.posting_date
		)
		redemption_details = get_redemption_details(doc.customer, doc.loyalty_program, doc.company)

		points_to_redeem = doc.loyalty_points
		for lp_entry in loyalty_point_entries:
			if lp_entry.invoice_type != doc.doctype or lp_entry.invoice == doc.name:
				continue
			available_points = lp_entry.loyalty_points - flt(redemption_details.get(lp_entry.name))
			redeemed_points = min(available_points, points_to_redeem)
			entry = frappe.get_doc(
				{
					"doctype": "Loyalty Point Entry",
					"company": doc.company,
					"loyalty_program": doc.loyalty_program,
					"loyalty_program_tier": lp_entry.loyalty_program_tier,
					"customer": doc.customer,
					"invoice_type": doc.doctype,
					"invoice": doc.name,
					"redeem_against": lp_entry.name,
					"loyalty_points": -1 * redeemed_points,
					"purchase_amount": doc.grand_total,
					"expiry_date": lp_entry.expiry_date,
					"posting_date": doc.posting_date,
				}
			)
			entry.flags.ignore_permissions = 1
			entry.save()
			points_to_redeem -= redeemed_points
			if points_to_redeem < 1:
				break

	def _set_loyalty_program_tier(self) -> None:
		doc = self.doc
		lp_details = get_loyalty_program_details_with_points(
			doc.customer,
			company=doc.company,
			loyalty_program=doc.loyalty_program,
			include_expired_entry=True,
		)
		customer = frappe.get_doc("Customer", doc.customer)
		customer.db_set("loyalty_program_tier", lp_details.tier_name)

	def _get_returned_amount(self) -> float:
		from frappe.query_builder.functions import Sum

		doc = frappe.qb.DocType(self.doc.doctype)
		returned_amount = (
			frappe.qb.from_(doc)
			.select(Sum(doc.grand_total))
			.where((doc.docstatus == 1) & (doc.is_return == 1) & (doc.return_against == self.doc.name))
		).run()

		return abs(returned_amount[0][0]) if returned_amount[0][0] else 0


def get_loyalty_programs(customer: str) -> list:
	"""Return applicable loyalty programs for the customer."""
	from erpnext.selling.doctype.customer.customer import get_loyalty_programs as _get

	customer_doc = frappe.get_doc("Customer", customer)
	if customer_doc.loyalty_program:
		return [customer_doc.loyalty_program]

	lp_details = _get(customer_doc)

	if len(lp_details) == 1:
		customer_doc.db_set("loyalty_program", lp_details[0])

	return lp_details
