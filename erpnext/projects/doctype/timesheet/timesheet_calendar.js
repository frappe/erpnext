frappe.views.calendar["Timesheet"] = {
	field_map: {
		"start": "from_time",
		"end": "to_time",
		"name": "parent",
		"id": "parent",
		"title": "activity_type",
		"allDay": "allDay",
		"child_name": "name"
	},
	gantt: true,
	filters: [
		{
			"fieldtype": "Link",
			"fieldname": "project",
			"options": "Project",
			"label": __("Project")
		},
		{
			"fieldtype": "Link",
			"fieldname": "employee",
			"options": "Employee",
			"label": __("Employee")
		}
	],
	get_events_method: "erpnext.projects.doctype.timesheet.timesheet.get_events"
}