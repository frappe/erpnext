// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Purchase Invoice'] = {
	add_fields: ["supplier", "supplier_name", "grand_total", "outstanding_amount", "due_date", "company",
		"currency"],
	get_indicator: function(doc) {
		if(doc.outstanding_amount > 0 && doc.docstatus==1) {
			if(frappe.datetime.get_diff(doc.due_date) < 0) {
				return [__("Overdue"), "red", "outstanding_amount,>,0|due_date,<,Today"];
			} else {
				return [__("Unpaid"), "orange", "outstanding_amount,>,0|due,>=,Today"];
			}
		} else if(doc.outstanding_amount==0 && doc.docstatus==1) {
			return [__("Paid"), "green", "outstanding_amount,=,0"];
		}
	}
};
