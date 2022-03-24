// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Additional Salary', {
	before_load: function(frm) {
		frm.events.confidential(frm);
	},

	confidential: function(frm) {
		return frappe.call({
			method: "confidentials",
			doc: frm.doc
		});
	},
	
	setup: function(frm) {
		frm.add_fetch("salary_component", "deduct_full_tax_on_selected_payroll_date", "deduct_full_tax_on_selected_payroll_date");

		frm.set_query("employee", function() {
			return {
				filters: {
					company: frm.doc.company
				}
			};
		});
	}
});
