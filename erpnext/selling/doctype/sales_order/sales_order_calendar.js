// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.views.calendar["Sales Order"] = {
	field_map: {
		"start": "delivery_date",
		"end": "delivery_date",
		"id": "name",
		"title": "customer_name",
		"allDay": "allDay"
	},
	gantt: true,
	filters: [
		{
			"fieldtype": "Link",
			"fieldname": "customer",
			"options": "Customer",
			"label": __("Customer")
		},
		{
			"fieldtype": "Select",
			"fieldname": "delivery_status",
			"options": "Not Delivered\nFully Delivered\nPartly Delivered\nClosed\nNot Applicable",
			"label": __("Delivery Status")
		},
		{
			"fieldtype": "Select",
			"fieldname": "billing_status",
			"options": "Not Billed\nFully Billed\nPartly Billed\nClosed",
			"label": __("Billing Status")
		},
	],
	get_events_method: "erpnext.selling.doctype.sales_order.sales_order.get_events",
	get_css_class: function(data) {
		if(data.status=="Closed") {
			return "success";
		} if(data.delivery_status=="Not Delivered") {
			return "danger";
		} else if(data.delivery_status=="Partly Delivered") {
			return "warning";
		} else if(data.delivery_status=="Fully Delivered") {
			return "success";
		}
	}
}
