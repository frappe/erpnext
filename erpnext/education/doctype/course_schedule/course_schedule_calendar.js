frappe.views.calendar["Course Schedule"] = {
	field_map: {
		"start": "from_time",
		"end": "to_time",
		"id": "name",
		"title": "course",
		"allDay": "allDay",
	},
	gantt: false,
	order_by: "schedule_date",
	filters: [
		{
			"fieldtype": "Link",
			"fieldname": "student_group",
			"options": "Student Group",
			"label": __("Student Group")
		},
		{
			"fieldtype": "Link",
			"fieldname": "course",
			"options": "Course",
			"label": __("Course")
		},
		{
			"fieldtype": "Link",
			"fieldname": "instructor",
			"options": "Instructor",
			"label": __("Instructor")
		},
		{
			"fieldtype": "Link",
			"fieldname": "room",
			"options": "Room",
			"label": __("Room")
		}
	],
	get_events_method: "erpnext.education.api.get_course_schedule_events"
}
