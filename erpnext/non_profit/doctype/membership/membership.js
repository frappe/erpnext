// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Membership', {
	setup: function(frm) {
		frappe.db.get_single_value("Membership Settings", "enable_razorpay").then(val => {
			if (val) frm.set_df_property("razorpay_details_section", "hidden", false);
		})
	},

	refresh: function(frm) {
		if (frm.doc.__islocal)
			return;

		!frm.doc.invoice && frm.add_custom_button("Generate Invoice", () => {
			frm.call({
				doc: frm.doc,
				method: "generate_invoice",
				args: {save: true},
				freeze: true,
				freeze_message: __("Creating Membership Invoice"),
				callback: function(r) {
					if (r.invoice)
						frm.reload_doc();
				}
			});
		});

		frappe.db.get_single_value("Membership Settings", "send_email").then(val => {
			if (val) frm.add_custom_button("Send Acknowledgement", () => {
				frm.call("send_acknowlement").then(() => {
					frm.reload_doc();
				});
			});
		})
	},

	onload: function(frm) {
		frm.add_fetch("membership_type", "amount", "amount");
	}
});
