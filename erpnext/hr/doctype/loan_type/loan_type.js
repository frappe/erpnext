// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Type', {
	onload: function(frm) {
		frm.set_query("deduction_type", function() {
			return {
				filters: {
					type: "deduction"
				}
			}
		})
	}
});
