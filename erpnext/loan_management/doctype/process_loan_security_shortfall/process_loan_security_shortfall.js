// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Process Loan Security Shortfall', {
	onload: function(frm) {
		frm.set_value('update_time', frappe.datetime.now_datetime());
	}
});
