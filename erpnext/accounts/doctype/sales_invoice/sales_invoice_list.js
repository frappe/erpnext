// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Sales Invoice'] = {
	add_fields: ["customer", "customer_name", "grand_total", "outstanding_amount", "due_date", "company",
		"currency"],
	filters: [["outstanding_amount", ">", "0"]],
	get_indicator: function(doc) {
		if(doc.outstanding_amount==0) {
			return [__("Paid"), "green", "oustanding_amount,=,0"]
		} else if (doc.outstanding_amount > 0 && doc.due_date > frappe.datetime.get_today()) {
			return [__("Unpaid"), "orange", "oustanding_amount,>,0|due_date,>,Today"]
		} else if (doc.outstanding_amount > 0 && doc.due_date <= frappe.datetime.get_today()) {
			return [__("Overdue"), "red", "oustanding_amount,>,0|due_date,<=,Today"]
		}
	},
	right_column: "grand_total_export"
};
