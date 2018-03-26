# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today

class LoyaltyProgram(Document):
	pass


def get_loyalty_details(customer, loyalty_program=None, till_date=None, company=None):
	if not till_date:
		till_date = today()
	args_list = [customer, loyalty_program, till_date]
	condition = ''
	if company:
		condition = " and company=%s "
		args_list.append(company)
	loyalty_point_details = frappe.db.sql('''select sum(points_earned) as loyalty_points,
		sum(purchase_amount) as total_spent from `tabLoyalty Point Entry`
		where customer=%s and loyalty_program=%s and expiry_date>=%s {condition} group by customer'''
		.format(condition=condition), tuple(args_list), as_dict=1)
	if loyalty_point_details:
		return loyalty_point_details[0]
	else:
		return {"loyalty_points": 0, "total_spent": 0}

@frappe.whitelist()
def get_loyalty_program_details(customer, loyalty_program=None, till_date=None, company=None):
	lp_details = frappe._dict()
	if not loyalty_program:
		loyalty_program = frappe.db.get_value("Customer", customer, "loyalty_program")
	if not company:
		company = frappe.db.get_default("company") or frappe.get_all("Company")[0].name

	lp_details.update(get_loyalty_details(customer, loyalty_program, till_date, company))

	lp_details.update({"loyalty_program": loyalty_program})
	loyalty_program = frappe.get_doc("Loyalty Program", lp_details.loyalty_program)

	lp_details.expiry_duration = loyalty_program.expiry_duration
	lp_details.conversion_factor = loyalty_program.conversion_factor
	lp_details.expense_account = loyalty_program.expense_account
	lp_details.cost_center = loyalty_program.cost_center
	lp_details.company = loyalty_program.company

	tier_spent_level = sorted([d.as_dict() for d in loyalty_program.collection_rules], key=lambda rule:rule.min_spent, reverse=True)
	for d in tier_spent_level:
		if lp_details.total_spent > d.min_spent:
			lp_details.tier_name = d.tier_name
			lp_details.collection_factor = d.collection_factor
			break
	return lp_details

@frappe.whitelist()
def get_redeemption_factor(loyalty_program):
	x = frappe.db.get_value("Loyalty Program", loyalty_program, "conversion_factor")
	print ("==================", x)
	return x

