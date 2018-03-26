# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

exclude_from_linked_with = True

class LoyaltyPointEntry(Document):
	pass


def redeem_loyalty_points(customer, points_to_redeem, loyalty_program, date, company, sales_invoice):
	loyalty_point_entries = get_loyalty_point_entries(customer, loyalty_program, date, company)

	for entry in loyalty_point_entries:
		doc = frappe.get_doc("Loyalty Point Entry", entry.name)
		if entry.points_earned >= points_to_redeem:
			redeemed_points = points_to_redeem
		else:
			redeemed_points = entry.points_earned
		points_to_redeem -= redeemed_points
		doc.append("redemption", {
			"redeemed_points": redeemed_points,
			"redemption_date": date,
			"sales_invoice": sales_invoice
		})
		doc.remaining_points = doc.remaining_points - redeemed_points
		doc.save()
		if points_to_redeem < 1:
			break

def get_loyalty_point_entries(customer, loyalty_program=None, date=None, company=None):
	if not date:
		date = today()
	args_list = [customer, loyalty_program, date]
	condition = ''
	if company:
		condition = " and company=%s "
		args_list.append(company)
	loyalty_point_details = frappe.db.sql('''select name, points_earned from `tabLoyalty Point Entry`
		where customer=%s and loyalty_program=%s and expiry_date>=%s {condition} order by expiry_date'''
		.format(condition=condition), tuple(args_list), as_dict=1)
	return loyalty_point_details
