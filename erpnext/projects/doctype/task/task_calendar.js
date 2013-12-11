// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.views.calendar["Task"] = {
	field_map: {
		"start": "exp_start_date",
		"end": "exp_end_date",
		"id": "name",
		"title": wn._("subject"),
		"allDay": "allDay"
	},
	gantt: true,
	filters: [
		{
			"fieldtype": "Link", 
			"fieldname": "project", 
			"options": "Project", 
			"label": wn._("Project")
		}
	],
	get_events_method: "projects.doctype.task.task.get_events"
}