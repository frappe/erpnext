# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt, today


class LoyaltyProgram(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.loyalty_program_collection.loyalty_program_collection import (
			LoyaltyProgramCollection,
		)

		auto_opt_in: DF.Check
		collection_rules: DF.Table[LoyaltyProgramCollection]
		company: DF.Link | None
		conversion_factor: DF.Float
		cost_center: DF.Link | None
		customer_group: DF.Link | None
		customer_territory: DF.Link | None
		expense_account: DF.Link | None
		expiry_duration: DF.Int
		from_date: DF.Date
		loyalty_program_name: DF.Data
		loyalty_program_type: DF.Literal["Single Tier Program", "Multiple Tier Program"]
		to_date: DF.Date | None
	# end: auto-generated types

	def validate(self):
		self.validate_lowest_tier()

	def validate_lowest_tier(self):
		tiers = sorted(self.collection_rules, key=lambda x: x.min_spent)
		if tiers and tiers[0].min_spent != 0:
			frappe.throw(
				_(
					"The lowest tier must have a minimum spent amount of 0. Customers need to be part of a tier as soon as they are enrolled in the program."
				)
			)


def get_loyalty_details(
	customer, loyalty_program, expiry_date=None, company=None, include_expired_entry=False
):
	if not expiry_date:
		expiry_date = today()

	LoyaltyPointEntry = frappe.qb.DocType("Loyalty Point Entry")

	query = (
		frappe.qb.from_(LoyaltyPointEntry)
		.select(
			Sum(LoyaltyPointEntry.loyalty_points).as_("loyalty_points"),
			Sum(LoyaltyPointEntry.purchase_amount).as_("total_spent"),
		)
		.where(
			(LoyaltyPointEntry.customer == customer)
			& (LoyaltyPointEntry.loyalty_program == loyalty_program)
			& (LoyaltyPointEntry.posting_date <= expiry_date)
		)
		.groupby(LoyaltyPointEntry.customer)
	)

	if company:
		query = query.where(LoyaltyPointEntry.company == company)

	if not include_expired_entry:
		query = query.where(LoyaltyPointEntry.expiry_date >= expiry_date)

	loyalty_point_details = query.run(as_dict=True)

	if loyalty_point_details:
		return loyalty_point_details[0]
	else:
		return {"loyalty_points": 0, "total_spent": 0}


@frappe.whitelist()
def get_loyalty_program_details_with_points(
	customer,
	loyalty_program=None,
	expiry_date=None,
	company=None,
	silent=False,
	include_expired_entry=False,
	current_transaction_amount=0,
):
	lp_details = get_loyalty_program_details(customer, loyalty_program, company=company, silent=silent)
	loyalty_program = frappe.get_doc("Loyalty Program", loyalty_program)
	loyalty_details = get_loyalty_details(
		customer, loyalty_program.name, expiry_date, company, include_expired_entry
	)
	lp_details.update(loyalty_details)

	tier_spent_level = sorted(
		[d.as_dict() for d in loyalty_program.collection_rules],
		key=lambda rule: rule.min_spent,
	)
	for i, d in enumerate(tier_spent_level):
		if i == 0 or (lp_details.total_spent + current_transaction_amount) >= d.min_spent:
			lp_details.tier_name = d.tier_name
			lp_details.collection_factor = d.collection_factor
		else:
			break

	return lp_details


@frappe.whitelist()
def get_loyalty_program_details(
	customer,
	loyalty_program=None,
	expiry_date=None,
	company=None,
	silent=False,
	include_expired_entry=False,
):
	lp_details = frappe._dict()

	if not loyalty_program:
		loyalty_program = frappe.db.get_value("Customer", customer, "loyalty_program")

		if not loyalty_program and not silent:
			frappe.throw(_("Customer isn't enrolled in any Loyalty Program"))
		elif silent and not loyalty_program:
			return frappe._dict({"loyalty_programs": None})

	if not company:
		company = frappe.db.get_default("company") or frappe.get_all("Company")[0].name

	loyalty_program = frappe.get_doc("Loyalty Program", loyalty_program)
	lp_details.update({"loyalty_program": loyalty_program.name})
	lp_details.update(loyalty_program.as_dict())
	return lp_details


@frappe.whitelist()
def get_redeemption_factor(loyalty_program=None, customer=None):
	customer_loyalty_program = None
	if not loyalty_program:
		customer_loyalty_program = frappe.db.get_value("Customer", customer, "loyalty_program")
		loyalty_program = customer_loyalty_program
	if loyalty_program:
		return frappe.db.get_value("Loyalty Program", loyalty_program, "conversion_factor")
	else:
		frappe.throw(_("Customer isn't enrolled in any Loyalty Program"))


def validate_loyalty_points(ref_doc, points_to_redeem):
	loyalty_program = None
	posting_date = None

	if ref_doc.doctype == "Sales Invoice":
		posting_date = ref_doc.posting_date
	else:
		posting_date = today()

	if hasattr(ref_doc, "loyalty_program") and ref_doc.loyalty_program:
		loyalty_program = ref_doc.loyalty_program
	else:
		loyalty_program = frappe.db.get_value("Customer", ref_doc.customer, ["loyalty_program"])

	if (
		loyalty_program
		and frappe.db.get_value("Loyalty Program", loyalty_program, ["company"]) != ref_doc.company
	):
		frappe.throw(_("The Loyalty Program isn't valid for the selected company"))

	if loyalty_program and points_to_redeem:
		loyalty_program_details = get_loyalty_program_details_with_points(
			ref_doc.customer, loyalty_program, posting_date, ref_doc.company
		)

		if points_to_redeem > loyalty_program_details.loyalty_points:
			frappe.throw(_("You don't have enough Loyalty Points to redeem"))

		loyalty_amount = flt(points_to_redeem * loyalty_program_details.conversion_factor)

		total_amount = ref_doc.grand_total if ref_doc.is_rounded_total_disabled() else ref_doc.rounded_total
		if loyalty_amount > total_amount:
			frappe.throw(_("You can't redeem Loyalty Points having more value than the Total Amount."))

		if not ref_doc.loyalty_amount and ref_doc.loyalty_amount != loyalty_amount:
			ref_doc.loyalty_amount = loyalty_amount
		if not ref_doc.loyalty_points and ref_doc.loyalty_points != points_to_redeem:
			ref_doc.loyalty_points = points_to_redeem

		if ref_doc.doctype == "Sales Invoice":
			ref_doc.loyalty_program = loyalty_program
			if not ref_doc.loyalty_redemption_account:
				ref_doc.loyalty_redemption_account = loyalty_program_details.expense_account

			if not ref_doc.loyalty_redemption_cost_center:
				ref_doc.loyalty_redemption_cost_center = loyalty_program_details.cost_center

		elif ref_doc.doctype == "Sales Order":
			return loyalty_amount
