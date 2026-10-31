# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Loyalty program helpers for Sales Invoice."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate

from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
	get_loyalty_program_details_with_points,
)

NO_EXPIRY_DATE = "9999-12-31"


class LoyaltyService:
	def __init__(self, doc):
		self.doc = doc

	def make_loyalty_point_entry(self) -> None:
		doc = self.doc
		lp_details, points_earned, eligible_amount = self._get_points_earned()
		if lp_details:
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
					"expiry_date": add_days(doc.posting_date, lp_details.expiry_duration)
					if lp_details.expiry_duration
					else NO_EXPIRY_DATE,
					"posting_date": doc.posting_date,
				}
			)
			entry.flags.ignore_permissions = 1
			entry.save()
			self._set_loyalty_program_tier()

	def update_loyalty_point_entry_on_return(self) -> None:
		"""Recompute the points of this invoice after a return is submitted or cancelled.

		When points of the earning entry are already redeemed, the entry is updated in place,
		so that the redemptions keep their link to it."""
		doc = self.doc
		lp_entry = frappe.db.get_value(
			"Loyalty Point Entry",
			{"invoice_type": doc.doctype, "invoice": doc.name, "loyalty_points": (">", 0)},
			"name",
		)
		redeemed = lp_entry and -flt(
			frappe.get_all(
				"Loyalty Point Entry",
				filters={"redeem_against": lp_entry},
				fields=[{"SUM": "loyalty_points", "as": "loyalty_points"}],
			)[0].loyalty_points
		)
		if not redeemed:
			self.delete_loyalty_point_entry()
			self.make_loyalty_point_entry()
			return

		_lp_details, points_earned, eligible_amount = self._get_points_earned()
		if points_earned < redeemed:
			frappe.throw(
				_(
					"Cannot return against {0} {1}: its loyalty points would become {2}, "
					"but {3} of its points are already redeemed."
				).format(doc.doctype, doc.name, points_earned, redeemed)
			)

		frappe.db.set_value(
			"Loyalty Point Entry",
			lp_entry,
			{"loyalty_points": points_earned, "purchase_amount": eligible_amount},
		)
		self._set_loyalty_program_tier()

	def _get_points_earned(self) -> tuple:
		"""The program details, points earned and eligible amount of this invoice, net of returns.
		The details are None when no program applies on the posting date."""
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
			return lp_details, cint(eligible_amount / collection_factor), eligible_amount
		return None, 0, eligible_amount

	def delete_loyalty_point_entry(self) -> None:
		doc = self.doc
		lp_entry = frappe.db.get_all(
			"Loyalty Point Entry",
			filters={"invoice_type": doc.doctype, "invoice": doc.name, "loyalty_points": (">", 0)},
			fields=["name"],
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
					"{0} cannot be cancelled since the Loyalty Points earned has been redeemed. "
					"First cancel the {1} No {2}"
				).format(doc.doctype, doc.doctype, invoice_list)
			)
		else:
			frappe.db.delete(
				"Loyalty Point Entry", filters={"invoice_type": doc.doctype, "invoice": doc.name}
			)
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
			if lp_entry.invoice == doc.name:
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
					"purchase_amount": 0,
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
