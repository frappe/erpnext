// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.views.calendar["Time Log"] = {
	field_map: {
		"start": "from_time",
		"end": "to_time",
		"id": "name",
		"title": "title",
		"allDay": "allDay"
	},
	gantt: true,
	filters: [
		{
			"fieldtype": "Link",
			"fieldname": "workstation",
			"options": "Workstation",
			"label": __("Workstation")
		},
	],
	get_events_method: "erpnext.projects.doctype.time_log.time_log.get_events"
}