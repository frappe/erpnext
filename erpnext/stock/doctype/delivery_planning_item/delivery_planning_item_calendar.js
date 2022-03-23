// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.views.calendar["Delivery Planning Item"] = {
	field_map: {
		"start": "planned_date",
        "end": "planned_date",
		"id": "name",
		"title": "full_dname",		
	},
	filters: [
	{
		"fieldtype": "Select",
		"fieldname": "docstatus",
		"options": "Submitted\nDraft\nCancelled",
		"label": __("Status")
	},],

	gantt: true,
	
	get_events_method: "frappe.desk.calendar.get_events",

}
