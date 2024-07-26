// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.views.calendar["Work Order"] = {
	fields: ["planned_start_date", "planned_end_date", "status", "produced_qty", "qty", "name", "name"],
	field_map: {
		start: "planned_start_date",
		end: "planned_end_date",
		id: "name",
		title: "name",
		status: "status",
		allDay: "allDay",
		progress: function (data) {
			return (flt(data.produced_qty) / data.qty) * 100;
		},
	},
	gantt: true,
	get_css_class: function (data) {
		if (data.status === "Completed") {
			return "success";
		} else if (data.status === "In Process") {
			return "warning";
		} else {
			return "danger";
		}
	},
	filters: [
		{
			fieldtype: "Link",
			fieldname: "sales_order",
			options: "Sales Order",
			label: __("Sales Order"),
		},
		{
			fieldtype: "Link",
			fieldname: "production_item",
			options: "Item",
			label: __("Production Item"),
		},
		{
			fieldtype: "Link",
			fieldname: "wip_warehouse",
			options: "Warehouse",
			label: __("WIP Warehouse"),
		},
	],
	get_events_method: "frappe.desk.calendar.get_events",
};
