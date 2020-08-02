# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data()
	return columns, data

def get_columns():
	return [
		{
			"label": _("Published Date"),
			"fieldname": "publish_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Title"),
			"fieldname": "title",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Provider"),
			"fieldname": "provider",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Views"),
			"fieldname": "view_count",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Likes"),
			"fieldname": "like_count",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Dislikes"),
			"fieldname": "dislike_count",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Views"),
			"fieldname": "view_count",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Like:Dislike Ratio"),
			"fieldname": "ratio",
			"fieldtype": "Data",
			"width": 100
		}
	]

def get_data():
	return frappe.db.sql("""
		SELECT
			publish_date, title, provider,
			view_count, like_count, dislike_count, comment_count
		FROM `tabVideo`
		WHERE view_count is not null
		ORDER BY view_count desc""")