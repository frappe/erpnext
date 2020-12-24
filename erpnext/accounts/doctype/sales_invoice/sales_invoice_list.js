// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Sales Invoice'] = {
	add_fields: ["customer", "customer_name", "base_grand_total", "outstanding_amount", "due_date", "company",
		"currency", "is_return"],
	get_indicator: function(doc) {
		var status_color = {
			"Draft": "grey",
			"Unpaid": "orange",
			"Paid": "green",
			"Return": "gray",
			"Credit Note Issued": "gray",
			"Unpaid and Discounted": "orange",
			"Overdue and Discounted": "red",
			"Overdue": "red",
			"Internal Transfer": "darkgrey"
		};
		return [__(doc.status), status_color[doc.status], "status,=,"+doc.status];
	},
	right_column: "grand_total"
};
