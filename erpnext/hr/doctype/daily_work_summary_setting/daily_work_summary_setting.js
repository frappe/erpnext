// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Daily Work Summary Setting', {
	refresh: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('Daily Work Summary'), function () {
				frappe.set_route('List', 'Daily Work Summary');
			});
			frm.trigger('enabled');
		}
	},
	enabled: function(frm) {
		var doc = frm.doc;
		if(!frm.is_new() && has_common(frappe.user_roles, ["Administrator", "System Manager"])) {
			frm.set_df_property('enabled', 'read_only', 0);
		}
	},
});
