// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Settings', {
	refresh: function(frm) {
		let filters = function() {
			return {
				filters : {
					is_group : 0
				}
			};
		};

		frm.set_query("default_warehouse", filters);
		frm.set_query("sample_retention_warehouse", filters);
	}
});
