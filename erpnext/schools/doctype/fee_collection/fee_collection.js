// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("fee_structure", "total_amount", "total_amount");

frappe.ui.form.on('Fee Collection', {
	refresh: function(frm) {

	}
});
