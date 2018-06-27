# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today

exclude_from_linked_with = True

class LoyaltyPointEntry(Document):
	pass


def get_loyalty_point_entries(customer, loyalty_program, expiry_date=None, company=None):
	if not expiry_date:
		date = today()
	args_list = [customer, loyalty_program, expiry_date]
	condition = ''
	if company:
		condition = " and company=%s "
		args_list.append(company)
	loyalty_point_details = frappe.db.sql('''select name, loyalty_points, expiry_date, loyalty_program_tier
		from `tabLoyalty Point Entry` where customer=%s and loyalty_program=%s and expiry_date>=%s and loyalty_points>0
		{condition} order by expiry_date'''.format(condition=condition), tuple(args_list), as_dict=1)
	return loyalty_point_details
