// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Type', {
	refresh: function(frm) {
		frm.add_custom_button('Mark Auto Attendance', () => {
			frappe.confirm(__("Are you sure you want to Mark Auto Attendance"), () => {
				frm.call({
					doc: frm.doc,
					method: 'process_auto_attendance',
					freeze: true
				});
			});
		});
	}
});
