# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today

class LoyaltyProgram(Document):
	pass


def get_loyalty_details(customer, loyalty_program):
	return frappe.db.sql('''select sum(points_earned) as loyalty_point,
		sum(purchase_amount) as total_spent from `tabLoyalty Point Entry`
		where customer=%s and loyalty_program=%s and expiry_date>=%s group by customer''',
		(customer, loyalty_program, today()), as_dict=1)[0]

def get_loyalty_program_tier(customer, loyalty_program):
	tier = frappe._dict()
	loyalty_details = get_loyalty_details(customer, loyalty_program)

	loyalty_program = frappe.get_doc("Loyalty Program", loyalty_program)
	tier.expiry_duration = loyalty_program.expiry_duration
	tier_spent_level = sorted([d.as_dict() for d in loyalty_program.collection_rules], key=lambda rule:rule.min_spent, reverse=True)
	for d in tier_spent_level:
		if loyalty_details.total_spent > d.min_spent:
			tier.tier_name = d.tier_name
			tier.min_spent = d.min_spent
			tier.collection_factor = d.collection_factor
			break
	return tier
