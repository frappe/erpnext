// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.views.calendar["Shift Assignment"] = {
	field_map: {
		"start": "start_date",
		"end": "end_date",
		"id": "name",
		"docstatus": 1,
		"allDay": "allDay",
	},
	get_events_method: "erpnext.hr.doctype.shift_assignment.shift_assignment.get_events"
}
