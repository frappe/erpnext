// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salary Component', {
	setup: function(frm) {
		frm.set_query("default_account", "accounts", function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			var root_types = ["Expense", "Liability"];
			return {
				filters: {
					"root_type": ["in", root_types],
					"is_group": 0,
					"company": d.company
				}
			};
		});
		frm.set_query("earning_component_group", function(frm) {
			return {
				filters: {
					"is_group": 1,
					"is_flexible_benefit": 1
				}
			};
		});
	}
});
