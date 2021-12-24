# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class LoyaltyProgram(Document):
	pass


def get_loyalty_details(customer, loyalty_program, expiry_date=None, company=None, include_expired_entry=False):
	if not expiry_date:
		expiry_date = today()

	condition = ''
	if company:
		condition = " and company=%s " % frappe.db.escape(company)
	if not include_expired_entry:
		condition += " and expiry_date>='%s' " % expiry_date

	loyalty_point_details = frappe.db.sql('''select sum(loyalty_points) as loyalty_points,
		sum(purchase_amount) as total_spent from `tabLoyalty Point Entry`
		where customer=%s and loyalty_program=%s and posting_date <= %s
		{condition}
		group by customer'''.format(condition=condition),
		(customer, loyalty_program, expiry_date), as_dict=1)

	if loyalty_point_details:
		return loyalty_point_details[0]
	else:
		return {"loyalty_points": 0, "total_spent": 0}

@frappe.whitelist()
def get_loyalty_program_details_with_points(customer, loyalty_program=None, expiry_date=None, company=None, \
		silent=False, include_expired_entry=False, current_transaction_amount=0):
	lp_details = get_loyalty_program_details(customer, loyalty_program, company=company, silent=silent)
	loyalty_program = frappe.get_doc("Loyalty Program", loyalty_program)
	lp_details.update(get_loyalty_details(customer, loyalty_program.name, expiry_date, company, include_expired_entry))

	tier_spent_level = sorted([d.as_dict() for d in loyalty_program.collection_rules],
		key=lambda rule:rule.min_spent, reverse=True)
	for i, d in enumerate(tier_spent_level):
		if i==0 or (lp_details.total_spent+current_transaction_amount) <= d.min_spent:
			lp_details.tier_name = d.tier_name
			lp_details.collection_factor = d.collection_factor
		else:
			break

	return lp_details

@frappe.whitelist()
def get_loyalty_program_details(customer, loyalty_program=None, expiry_date=None, company=None, silent=False, include_expired_entry=False):
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

	if loyalty_program and frappe.db.get_value("Loyalty Program", loyalty_program, ["company"]) !=\
		ref_doc.company:
		frappe.throw(_("The Loyalty Program isn't valid for the selected company"))

	if loyalty_program and points_to_redeem:
		loyalty_program_details = get_loyalty_program_details_with_points(ref_doc.customer, loyalty_program,
			posting_date, ref_doc.company)

		if points_to_redeem > loyalty_program_details.loyalty_points:
			frappe.throw(_("You don't have enought Loyalty Points to redeem"))

		loyalty_amount = flt(points_to_redeem * loyalty_program_details.conversion_factor)

		if loyalty_amount > ref_doc.grand_total:
			frappe.throw(_("You can't redeem Loyalty Points having more value than the Grand Total."))

		if not ref_doc.loyalty_amount and ref_doc.loyalty_amount != loyalty_amount:
			ref_doc.loyalty_amount = loyalty_amount

		if ref_doc.doctype == "Sales Invoice":
			ref_doc.loyalty_program = loyalty_program
			if not ref_doc.loyalty_redemption_account:
				ref_doc.loyalty_redemption_account = loyalty_program_details.expense_account

			if not ref_doc.loyalty_redemption_cost_center:
				ref_doc.loyalty_redemption_cost_center = loyalty_program_details.cost_center

		elif ref_doc.doctype == "Sales Order":
			return loyalty_amount
