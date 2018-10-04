// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Driver', {
	setup: function(frm) {
		frm.set_query('transporter', function(){
			return {
				filters: {
					'is_transporter': 1
				}
			};
		});
	}
});
