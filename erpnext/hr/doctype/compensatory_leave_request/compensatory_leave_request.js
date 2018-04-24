// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Compensatory Leave Request', {
	refresh: function(frm) {
		frm.set_query("leave_type", function() {
			return {
				filters: {
					"is_compensatory": true
				}
			};
		});
	}
});
