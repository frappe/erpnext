// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee', 'company', 'company');

frappe.ui.form.on('Attendance Request', {
	setup: function (frm) {
		frm.set_query("status", function () {
			return {
				filters: {
					"is_leave": 0
				}
			};
		});

		frm.set_query("remaining_half_day_status", function () {
			return {
				filters: {
					is_half_day: 0,
					is_leave: 0,
				}
			};
		});
	},
});
