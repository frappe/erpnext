// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('branch','cost_center','cost_center');
frappe.ui.form.on('Coal Raising Master', {
	onload: function(frm) {
		frm.set_value('from_date',frappe.datetime.month_start())
		frm.set_value('to_date',frappe.datetime.month_end())
	}
});
