// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.views.calendar["Production Plan Schedule"] = {
	field_map: {
		start: "from_time",
		end: "to_time",
		id: "name",
		title: "subject",
		allDay: "allDay",
	},
	order_by: "from_time",
	filters: [
		{
			fieldtype: "Link",
			fieldname: "production_plan",
			options: "Production Plan",
			label: __("Production Plan"),
		},
		{
			fieldtype: "Link",
			fieldname: "workstation",
			options: "Workstation",
			label: __("Workstation"),
		},
		{
			fieldtype: "Link",
			fieldname: "item_code",
			options: "Item",
			label: __("Item"),
		},
	],
	get_events_method: "frappe.desk.calendar.get_events",
};
