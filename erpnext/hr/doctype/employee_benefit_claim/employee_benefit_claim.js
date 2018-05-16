// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Benefit Claim', {
	setup: function(frm) {
		frm.set_query("earning_component", function() {
			return {
				filters: {
					type: "Earning",
					is_flexible_benefit: true,
					disabled: false
				}
			};
		});
	}
});
