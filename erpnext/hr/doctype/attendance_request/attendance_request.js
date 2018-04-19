// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee', 'company', 'company');

frappe.ui.form.on('Attendance Request', {
	refresh: function(frm) {

	}
});
