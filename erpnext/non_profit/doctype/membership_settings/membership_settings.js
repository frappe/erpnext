// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Membership Settings", {
	refresh: function(frm) {
		if (frm.doc.webhook_secret) {
			frm.add_custom_button(__("Revoke <Key></Key>"), () => {
				frm.call("revoke_key").then(() => {
					frm.refresh();
				})
			});
		}
		frm.trigger("add_generate_button");
	},

	add_generate_button: function(frm) {
		let label;

		if (frm.doc.webhook_secret) {
			label = __("Regenerate Webhook Secret");
		} else {
			label = __("Generate Webhook Secret");
		}
		frm.add_custom_button(label, () => {
			frm.call("generate_webhook_key").then(() => {
				frm.refresh();
			});
		});
	},
});
