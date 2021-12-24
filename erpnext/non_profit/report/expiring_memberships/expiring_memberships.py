# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters):
	return [
			_("Membership Type") + ":Link/Membership Type:100", _("Membership ID") + ":Link/Membership:140",
			_("Member ID") + ":Link/Member:140",  _("Member Name") + ":Data:140", _("Email") + ":Data:140",
	 		_("Expiring On") + ":Date:120"
	]

def get_data(filters):

	filters["month"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(filters.month) + 1

	return frappe.db.sql("""
		select ms.membership_type,ms.name,m.name,m.member_name,m.email,ms.max_membership_date
		from `tabMember` m
		inner join (select name,membership_type,max(to_date) as max_membership_date,member
					from `tabMembership`
					where paid = 1
					group by member
					order by max_membership_date asc) ms
		on m.name = ms.member
		where month(max_membership_date) = %(month)s and year(max_membership_date) = %(year)s """,{'month': filters.get('month'),'year':filters.get('fiscal_year')})
