# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import today

exclude_from_linked_with = True


class LoyaltyPointEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link
		customer: DF.Link
		discretionary_reason: DF.Data | None
		expiry_date: DF.Date
		invoice: DF.DynamicLink | None
		invoice_type: DF.Link
		loyalty_points: DF.Int
		loyalty_program: DF.Link
		loyalty_program_tier: DF.Data | None
		posting_date: DF.Date
		purchase_amount: DF.Currency
		redeem_against: DF.Link | None
	# end: auto-generated types

	pass


def get_loyalty_point_entries(customer, loyalty_program, company, expiry_date=None):
	if not expiry_date:
		expiry_date = today()

	LPEntry = frappe.qb.DocType("Loyalty Point Entry")

	return (
		frappe.qb.from_(LPEntry)
		.select(
			LPEntry.name,
			LPEntry.loyalty_points,
			LPEntry.expiry_date,
			LPEntry.loyalty_program_tier,
			LPEntry.invoice_type,
			LPEntry.invoice,
		)
		.where(
			(LPEntry.customer == customer)
			& (LPEntry.loyalty_program == loyalty_program)
			& (LPEntry.expiry_date >= expiry_date)
			& (LPEntry.loyalty_points > 0)
			& (LPEntry.company == company)
		)
		.run(as_dict=True)
	)


def get_redemption_details(customer, loyalty_program, company):
	LPEntry = frappe.qb.DocType("Loyalty Point Entry")

	return (
		frappe.qb.from_(LPEntry)
		.select(LPEntry.redeem_against, Sum(LPEntry.loyalty_points).as_("loyalty_points"))
		.where(
			(LPEntry.customer == customer)
			& (LPEntry.loyalty_program == loyalty_program)
			& (LPEntry.loyalty_points < 0)
			& (LPEntry.company == company)
		)
		.groupby(LPEntry.redeem_against)
		.run(as_dict=True)
	)
