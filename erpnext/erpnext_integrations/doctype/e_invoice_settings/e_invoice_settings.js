// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('E Invoice Settings', {
	refresh: function(frm) {
		frm.trigger("show_fetch_token_btn");
	},

	show_fetch_token_btn(frm) {
		frm.add_custom_button(__("Fetch Token"),
			() => {
				frm.call({
					doc: frm.doc,
					method: 'make_authentication_request',
					freeze: true
				});
			}
		);
	}
});
