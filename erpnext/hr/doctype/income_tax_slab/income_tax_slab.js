// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Income Tax Slab', {
	setup: function(frm, cdt, cdn) {
		frm.set_query("salary_component", "other_taxes_and_charges", function() {
			return {
				filters: {
					type: "Deduction"
				}
			}
		});
	}
});
