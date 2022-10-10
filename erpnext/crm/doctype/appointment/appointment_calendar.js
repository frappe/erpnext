// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.views.calendar["Appointment"] = {
	field_map: {
		"start": "scheduled_dt",
		"end": "end_dt",
		"id": "name",
		"title": "customer_name",
		"allDay": "allDay"
	},
	gantt: false,
	get_events_method: "erpnext.crm.doctype.appointment.appointment.get_events",
	get_css_class: function(doc) {
		if (doc.status == "Open") {
			return "warning";
		} else if (doc.status == "Rescheduled") {
			return "info";
		} else if (doc.status == "Missed") {
			return "secondary";
		} else if (doc.status == "Closed") {
			return "success";
		}
	}
}
