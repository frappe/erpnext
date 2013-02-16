wn.views.calendar["Leave Application"] = wn.views.Calendar.extend({
	field_map: {
		"start": "from_date",
		"end": "to_date",
		"id": "name",
		"title": "title",
		"status": "status",
	},
	get_events_method: "hr.doctype.leave_application.leave_application.get_events"
})