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

		frm.set_query('print_format', function(doc) {
			return {
				filters: {
					"doc_type": "Sales Invoice"
				}
			};
		});

		let docs_url = "https://docs.erpnext.com/docs/user/manual/en/non_profit/membership";

		frm.set_intro(__("You can learn more about memberships in the manual. ") + `<a href='${docs_url}'>${__('ERPNext Docs')}</a>`, true);

		frm.trigger("add_generate_button");
		frm.trigger("add_copy_buttonn");
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

	add_copy_buttonn: function(frm) {
		if (frm.doc.webhook_secret) {
			frm.add_custom_button(__("Copy Webhook URL"), () => {
				frappe.utils.copy_to_clipboard(`https://${frappe.boot.sitename}/api/method/erpnext.non_profit.doctype.membership.membership.trigger_razorpay_subscription`);
			});
		}
	}
});
