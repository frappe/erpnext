// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Email Digest", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("View Now"), function () {
				if (frm.is_dirty()) {
					frappe.show_alert({
						message: __("Save the Email Digest first.", "yellow"),
						indicator: "yellow",
					});
					return;
				}

				frm.call("get_digest_msg").then((r) => {
					let d = new frappe.ui.Dialog({
						title: __("Email Digest: {0}", [frm.doc.name]),
						width: 800,
					});
					$(d.body).html(r.message);
					d.show();
				});
			});

			frm.add_custom_button(__("Send Now"), function () {
				if (frm.is_dirty()) {
					frappe.show_alert({
						message: __("Save the Email Digest first.", "yellow"),
						indicator: "yellow",
					});
					return;
				}

				return frm.call("send", null, () => {
					frappe.show_alert({ message: __("Message Sent"), indicator: "green" });
				});
			});
		}
	},
});
