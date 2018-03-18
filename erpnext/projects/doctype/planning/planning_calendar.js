// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.views.calendar["Planning"] = {
	field_map: {
		"start": "start_date",
		"end": "end_date",
		"id": "name",
		"title": "subject",
		"allDay": "allDay"
	},
	gantt: true,
	filters: [
		{
			"fieldtype": "Link",
			"fieldname": "project",
			"options": "Project",
			"label": __("Project")
		}
	],
	get_events_method: "erpnext.projects.doctype.planning.planning.get_events"
}
