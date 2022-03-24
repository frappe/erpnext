// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
frappe.views.calendar["Opportunity"] = {
	field_map: {
		"start": "contact_date",
		"end": "contact_date",
		"id": "name",
		"title": "customer_name",
		"allDay": "allDay"
    },
	options: {
		header: {
			left: 'prev,next today',
			center: 'title',
			right: 'month'
		}
    },
    get_events_method: 'erpnext.crm.doctype.opportunity.opportunity.get_events'
}
