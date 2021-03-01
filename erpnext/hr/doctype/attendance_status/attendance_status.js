// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Attendance Status', {
	is_half_day: function(frm) {
		frm.events.reset_values(["is_leave", "is_present"]);
	},
	is_leave: function(frm) {
		frm.events.reset_values(["is_half_day", "is_present"]);
	},
	is_present: function(frm) {
		frm.events.reset_values(["is_leave", "is_half_day"]);
	},

	reset_values: function(fields) {
		fields.forEach(field => {
			frm.set_value(field, 0);
		});

	}
});
