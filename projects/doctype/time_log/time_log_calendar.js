// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

wn.views.calendar["Time Log"] = {
	field_map: {
		"start": "from_time",
		"end": "to_time",
		"id": "name",
		"title": w._("title"),
		"allDay": "allDay"
	},
	get_events_method: "projects.doctype.time_log.time_log.get_events"
}