// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Purchase Invoice'] = {
	add_fields: ["supplier", "supplier_name", "base_grand_total", "outstanding_amount", "due_date", "company",
		"currency", "is_return", "release_date", "on_hold"],
	get_indicator: function(doc) {
		if(flt(doc.outstanding_amount) > 0 && doc.docstatus==1) {
			if(cint(doc.on_hold) && !doc.release_date) {
				return [__("On Hold"), "darkgrey"];
			} else if(cint(doc.on_hold) && doc.release_date && frappe.datetime.get_diff(doc.release_date, frappe.datetime.nowdate()) > 0) {
				return [__("Temporarily on Hold"), "darkgrey"];
			}
		}
		let status_color = {
			"Return": "darkgrey",
			"Paid": "green",
			"Unpaid": "red",
			"Debit Note Issued": "darkgrey",
			"Overdue": "orange",
		};
		return [__(status), status_color[status], "status,=" + status];
	}
};
