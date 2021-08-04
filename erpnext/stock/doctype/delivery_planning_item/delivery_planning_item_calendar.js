// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
var date1 = new Date()
frappe.views.calendar["Delivery Planning Item"] = {
    
	field_map: {
		"start": "delivery_date",
        "end": "delivery_date",
		"id": "name",
		"title": "customer_name",
		"allDay": "allDay",
		// "progress": "progress"
	},
	gantt: true,
	filters: [
		{
			"fieldtype": "Link",
			"fieldname": "related_delivey_planning",
			"options": "Delivery Planning",
			"label": __("Project")
		}
	],
	get_events_method: "frappe.desk.calendar.get_events"
}
