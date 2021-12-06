// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Non Profit Settings", {
	refresh: function(frm) {
		frm.set_query("inv_print_format", function() {
			return {
				filters: {
					"doc_type": "Sales Invoice"
				}
			};
		});

		frm.set_query("membership_print_format", function() {
			return {
				filters: {
					"doc_type": "Membership"
				}
			};
		});

		frm.set_query("membership_debit_account", function() {
			return {
				filters: {
					"account_type": "Receivable",
					"is_group": 0,
					"company": frm.doc.company
				}
			};
		});

		frm.set_query("donation_debit_account", function() {
			return {
				filters: {
					"account_type": "Receivable",
					"is_group": 0,
					"company": frm.doc.donation_company
				}
			};
		});

		frm.set_query("membership_payment_account", function () {
			var account_types = ["Bank", "Cash"];
			return {
				filters: {
					"account_type": ["in", account_types],
					"is_group": 0,
					"company": frm.doc.company
				}
			};
		});

		frm.set_query("donation_payment_account", function () {
			var account_types = ["Bank", "Cash"];
			return {
				filters: {
					"account_type": ["in", account_types],
					"is_group": 0,
					"company": frm.doc.donation_company
				}
			};
		});

		let docs_url = "https://docs.erpnext.com/docs/user/manual/en/non_profit/membership";

		frm.set_intro(__("You can learn more about memberships in the manual. ") + `<a href='${docs_url}'>${__('ERPNext Docs')}</a>`, true);
		frm.trigger("setup_buttons_for_membership");
		frm.trigger("setup_buttons_for_donation");
	},

	setup_buttons_for_membership: function(frm) {
		let label;

		if (frm.doc.membership_webhook_secret) {

			frm.add_custom_button(__("Copy Webhook URL"), () => {
				frappe.utils.copy_to_clipboard(`https://${frappe.boot.sitename}/api/method/erpnext.non_profit.doctype.membership.membership.trigger_razorpay_subscription`);
			}, __("Memberships"));

			frm.add_custom_button(__("Revoke Key"), () => {
				frm.call("revoke_key",  {
					key: "membership_webhook_secret"
				}).then(() => {
					frm.refresh();
				});
			}, __("Memberships"));

			label = __("Regenerate Webhook Secret");

		} else {
			label = __("Generate Webhook Secret");
		}

		frm.add_custom_button(label, () => {
			frm.call("generate_webhook_secret", {
				field: "membership_webhook_secret"
			}).then(() => {
				frm.refresh();
			});
		}, __("Memberships"));
	},

	setup_buttons_for_donation: function(frm) {
		let label;

		if (frm.doc.donation_webhook_secret) {
			label = __("Regenerate Webhook Secret");

			frm.add_custom_button(__("Copy Webhook URL"), () => {
				frappe.utils.copy_to_clipboard(`https://${frappe.boot.sitename}/api/method/erpnext.non_profit.doctype.donation.donation.capture_razorpay_donations`);
			}, __("Donations"));

			frm.add_custom_button(__("Revoke Key"), () => {
				frm.call("revoke_key", {
					key: "donation_webhook_secret"
				}).then(() => {
					frm.refresh();
				});
			}, __("Donations"));

		} else {
			label = __("Generate Webhook Secret");
		}

		frm.add_custom_button(label, () => {
			frm.call("generate_webhook_secret", {
				field: "donation_webhook_secret"
			}).then(() => {
				frm.refresh();
			});
		}, __("Donations"));
	}
});
