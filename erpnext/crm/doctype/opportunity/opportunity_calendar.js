// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.views.calendar["Opportunity"] = {
	field_map: {
		"start": "schedule_date",
		"end": "schedule_date",
		"id": "name",
		"title": "customer_name",
		"allDay": "allDay"
	},
	gantt: false,
	get_events_method: "erpnext.crm.doctype.opportunity.opportunity.get_events",
	get_css_class: function(doc) {
		if (doc.status == "Open") {
			return "danger";
		} else if (doc.status == "Closed") {
			return "success";
		} else if (doc.status == "Lost") {
			return "secondary";
		} else if (doc.status == "Quotation") {
			return "info";
		} else if (doc.status == "Converted") {
			return "success";
		}
	}
}
