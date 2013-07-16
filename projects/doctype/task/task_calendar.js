wn.views.calendar["Task"] = {
	field_map: {
		"start": "exp_start_date",
		"end": "exp_end_date",
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
			"label": "Project"
		}
	],
	get_events_method: "projects.doctype.task.task.get_events"
}