// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.views.calendar["Production Order"] = {
	field_map: {
		"start": "start_date",
		"end": "end_date",
		"id": "name",
		"title": "production_item",
		"allDay": "allDay"
	},
	gantt: true,
	get_events_method: "erpnext.manufacturing.doctype.production_order.production_order.get_events"
}