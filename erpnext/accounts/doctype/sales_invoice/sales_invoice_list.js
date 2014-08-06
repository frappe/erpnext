// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Sales Invoice'] = {
	add_fields: ["customer", "customer_name", "grand_total", "outstanding_amount", "due_date", "company",
		"currency"],
	filters: [["outstanding_amount", ">", "0"]]
};
