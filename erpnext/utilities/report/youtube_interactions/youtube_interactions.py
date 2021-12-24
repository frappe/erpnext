# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	if not frappe.db.get_single_value("Video Settings", "enable_youtube_tracking") or not filters:
		return [], []

	columns = get_columns()
	data = get_data(filters)
	chart_data, summary = get_chart_summary_data(data)
	return columns, data, None, chart_data, summary

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
			"width": 200
		},
		{
			"label": _("Duration"),
			"fieldname": "duration",
			"fieldtype": "Duration",
			"width": 100
		},
		{
			"label": _("Views"),
			"fieldname": "view_count",
			"fieldtype": "Float",
			"width": 200
		},
		{
			"label": _("Likes"),
			"fieldname": "like_count",
			"fieldtype": "Float",
			"width": 200
		},
		{
			"label": _("Dislikes"),
			"fieldname": "dislike_count",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Comments"),
			"fieldname": "comment_count",
			"fieldtype": "Float",
			"width": 100
		}
	]

def get_data(filters):
	return frappe.db.sql("""
		SELECT
			publish_date, title, provider, duration,
			view_count, like_count, dislike_count, comment_count
		FROM `tabVideo`
		WHERE view_count is not null
			and publish_date between %(from_date)s and %(to_date)s
		ORDER BY view_count desc""", filters, as_dict=1)

def get_chart_summary_data(data):
	labels, likes, views = [], [], []
	total_views = 0

	for row in data:
		labels.append(row.get('title'))
		likes.append(row.get('like_count'))
		views.append(row.get('view_count'))
		total_views += flt(row.get('view_count'))


	chart_data = {
		"data" : {
			"labels" : labels,
			"datasets" : [
				{
					"name" : "Likes",
					"values" : likes
				},
				{
					"name" : "Views",
					"values" : views
				}
			]
		},
		"type": "bar",
		"barOptions": {
			"stacked": 1
		},
	}

	summary = [
		{
			"value": total_views,
			"indicator": "Blue",
			"label": "Total Views",
			"datatype": "Float",
		}
	]
	return chart_data, summary
