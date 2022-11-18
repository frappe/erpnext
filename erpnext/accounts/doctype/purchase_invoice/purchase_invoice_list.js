// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Purchase Invoice'] = {
	add_fields: [
		"supplier", "supplier_name",
		"base_grand_total", "outstanding_amount", "due_date", "company",
		"currency", "is_return", "release_date", "on_hold"
	],

	get_indicator: function(doc) {
		// Debit Note Issued
		if(doc.status == 'Debit Note Issued') {
			return [__("Debit Note Issued"), "grey", "status,=,Debit Note Issued"];

		// Outstanding Amount Positive
		} else if(flt(doc.outstanding_amount) > 0) {

			// On Hold Without Release Date
			if(cint(doc.on_hold) && !doc.release_date) {
				return [__("On Hold"), "light-grey", "status,=,On Hold"];

			// Temporarily On Hold
			} else if(cint(doc.on_hold) && doc.release_date && frappe.datetime.get_diff(doc.release_date, frappe.datetime.nowdate()) > 0) {
				return [__("Temporarily On Hold"), "light-grey", "status,=,On Hold|release_date,is,set"];

			// Overdue Unpaid
			} else if(frappe.datetime.get_diff(doc.due_date) < 0) {
				return [__("Overdue"), "red",
					"outstanding_amount,>,0|due_date,<,Today|docstatus,=,1"];

			// Unpaid
			} else {
				return [__("Unpaid"), "orange",
					"outstanding_amount,>,0|docstatus,=,1"];
			}

		// Return
		} else if(cint(doc.is_return)) {
			return [__("Return"), "grey", "is_return,=,Yes|docstatus,=,1"];

		// Paid
		} else if(flt(doc.outstanding_amount) == 0) {
			return [__("Paid"), "green",
				"outstanding_amount,=,0|docstatus,=,1"];
		}
	}
};
