// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.views.calendar["Time Log"] = {
	field_map: {
		"start": "from_time",
		"end": "to_time",
		"id": "name",
		"title": "title",
		"allDay": "allDay"
	},
	get_events_method: "erpnext.projects.doctype.time_log.time_log.get_events"
}