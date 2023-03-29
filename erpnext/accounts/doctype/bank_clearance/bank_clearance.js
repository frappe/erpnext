// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Bank Clearance", {
	setup: function(frm) {
		frm.add_fetch("account", "account_currency", "account_currency");

		frm.set_query("account", function() {
			return {
				"filters": {
					"account_type": ["in",["Bank","Cash"]],
					"is_group": 0,
				}
			};
		});

		frm.set_query("bank_account", function () {
			return {
				filters: {
					'is_company_account': 1
				},
			};
		});
	},

	onload: function(frm) {

		let default_bank_account =  frappe.defaults.get_user_default("Company")?
			locals[":Company"][frappe.defaults.get_user_default("Company")]["default_bank_account"]: "";
		frm.set_value("account", default_bank_account);



		frm.set_value("from_date", frappe.datetime.month_start());
		frm.set_value("to_date", frappe.datetime.month_end());
	},

	refresh: function(frm) {
		frm.disable_save();
		frm.add_custom_button(__('Get Payment Entries'), () =>
			frm.trigger("get_payment_entries")
		);

		frm.change_custom_button_type('Get Payment Entries', null, 'primary');
	},

	update_clearance_date: function(frm) {
		return frappe.call({
			method: "update_clearance_date",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("payment_entries");
				frm.refresh_fields();

				if (!frm.doc.payment_entries.length) {
					frm.change_custom_button_type('Get Payment Entries', null, 'primary');
					frm.change_custom_button_type('Update Clearance Date', null, 'default');
				}
			}
		});
	},

	get_payment_entries: function(frm) {
		return frappe.call({
			method: "get_payment_entries",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("payment_entries");

				if (frm.doc.payment_entries.length) {
					frm.add_custom_button(__('Update Clearance Date'), () =>
						frm.trigger("update_clearance_date")
					);

					frm.change_custom_button_type('Get Payment Entries', null, 'default');
					frm.change_custom_button_type('Update Clearance Date', null, 'primary');
				}
			}
		});
	}
});
