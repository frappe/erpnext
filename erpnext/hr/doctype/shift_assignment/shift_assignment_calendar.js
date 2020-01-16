// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.views.calendar["Shift Assignment"] = {
	field_map: {
		"start": "date",
		"end": "date",
		"id": "name",
		"docstatus": 1
	},
	options: {
		header: {
			left: 'prev,next today',
			center: 'title',
			right: 'month'
		}
	},
	get_events_method: "erpnext.hr.doctype.shift_assignment.shift_assignment.get_events"
}