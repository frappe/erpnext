// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Membership', {
	setup: function(frm) {
		frappe.db.get_single_value("Membership Settings", "enable_razorpay").then(val => {
			if (val) frm.set_df_property('razorpay_details_section', 'hidden', false);
		})
	},

	onload: function(frm) {
		frm.add_fetch('membership_type', 'amount', 'amount');
	}
});
