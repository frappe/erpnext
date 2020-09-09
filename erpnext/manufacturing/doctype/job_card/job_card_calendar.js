frappe.views.calendar["Job Card"] = {
	field_map: {
		"start": "started_time",
		"end": "started_time",
		"id": "name",
		"title": "subject",
		"color": "color",
		"allDay": "allDay",
		"progress": "progress"
	},
	gantt: true,
	filters: [
		{
			"fieldtype": "Link",
			"fieldname": "employee",
			"options": "Employee",
			"label": __("Employee")
		}
	],
	get_events_method: "erpnext.manufacturing.doctype.job_card.job_card.get_job_details"
};
