// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.views.calendar["Over Time"] = {
	field_map: {
		"start": "from_date",
		"end": "to_date",
		"id": "name",
		"title": "title",
		"status": "status",
	},
	options: {
		defaultView: 'agendaDay',
		header: {
			left: 'prev,next today',
			center: 'title',
			right: 'agendaDay'
		}
	},
	// get_events_method: "erpnext.hr.doctype.leave_application.leave_application.get_events"
}