// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Workshop', {
	setup: function(frm) {
		frm.set_query('cost_center', 'default_cost_centers', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			var filters = {
				'company': d.company,
				"is_group": 0
			};
			return {
				filters: filters
			}
		});
	}
});
