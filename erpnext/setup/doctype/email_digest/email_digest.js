// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Email Digest", {
	refresh: function(frm) {
		frm.add_custom_button(__('View Now'), function() {
			frappe.call({
				method: 'erpnext.setup.doctype.email_digest.email_digest.get_digest_msg',
				args: {
					name: frm.doc.name
				},
				callback: function(r) {
					var d = new frappe.ui.Dialog({
						title: __('Email Digest: ') + frm.doc.name,
						width: 800
					});
					$(d.body).html(r.message);
					d.show();
				}
			});
		});

		if (!frm.is_new()) {
			frm.add_custom_button(__('Send Now'), function() {
				return frm.call('send', null, (r) => {
					frappe.show_alert({message:__("Message Sent"), indicator:'green'});
				});
			});
		}
	}
});