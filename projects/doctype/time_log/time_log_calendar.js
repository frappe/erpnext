wn.views.calendar["Time Log"] = wn.views.Calendar.extend({
	field_map: {
		"start": "from_time",
		"end": "to_time",
		"id": "name",
		"title": "title",
		"allDay": "allDay"
	},
	get_events_method: "projects.doctype.time_log.time_log.get_events"
})