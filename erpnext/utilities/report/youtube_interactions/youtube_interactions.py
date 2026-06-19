# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


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
		{"label": _("Published Date"), "fieldname": "publish_date", "fieldtype": "Date", "width": 100},
		{"label": _("Title"), "fieldname": "title", "fieldtype": "Data", "width": 200},
		{"label": _("Duration"), "fieldname": "duration", "fieldtype": "Duration", "width": 100},
		{"label": _("Views"), "fieldname": "view_count", "fieldtype": "Float", "width": 200},
		{"label": _("Likes"), "fieldname": "like_count", "fieldtype": "Float", "width": 200},
		{"label": _("Dislikes"), "fieldname": "dislike_count", "fieldtype": "Float", "width": 100},
		{"label": _("Comments"), "fieldname": "comment_count", "fieldtype": "Float", "width": 100},
	]


def get_data(filters):
	video = frappe.qb.DocType("Video")
	return (
		frappe.qb.from_(video)
		.select(
			video.publish_date,
			video.title,
			video.provider,
			video.duration,
			video.view_count,
			video.like_count,
			video.dislike_count,
			video.comment_count,
		)
		.where(video.view_count.isnotnull())
		.where(video.publish_date[filters.get("from_date") : filters.get("to_date")])
		.orderby(video.view_count, order=frappe.qb.desc)
	).run(as_dict=True)


def get_chart_summary_data(data):
	labels, likes, views = [], [], []
	total_views = 0

	for row in data:
		labels.append(row.get("title"))
		likes.append(row.get("like_count"))
		views.append(row.get("view_count"))
		total_views += flt(row.get("view_count"))

	chart_data = {
		"data": {
			"labels": labels,
			"datasets": [{"name": "Likes", "values": likes}, {"name": "Views", "values": views}],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}

	summary = [
		{
			"value": total_views,
			"indicator": "Blue",
			"label": _("Total Views"),
			"datatype": "Float",
		}
	]
	return chart_data, summary
