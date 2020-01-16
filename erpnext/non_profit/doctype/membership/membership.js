// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Membership', {
	onload:function(frm) {
		frm.add_fetch('membership_type', 'amount', 'amount');
	}
});
