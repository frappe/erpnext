// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Bank Reconciliation", {
	setup: function(frm) {
		frm.add_fetch("bank_account", "account_currency", "account_currency");
	},

	onload: function(frm) {

		let default_bank_account =  frappe.defaults.get_user_default("Company")? 
			locals[":Company"][frappe.defaults.get_user_default("Company")]["default_bank_account"]: "";
		frm.set_value("bank_account", default_bank_account);

		frm.set_query("bank_account", function() {
			return {
				"filters": {
					"account_type": ["in",["Bank","Cash"]],
					"is_group": 0
				}
			};
		});

		frm.set_value("from_date", frappe.datetime.month_start());
		frm.set_value("to_date", frappe.datetime.month_end());
	},

	refresh: function(frm) {
		frm.disable_save();
	},

	update_clearance_date: function(frm) {
		return frappe.call({
			method: "update_clearance_date",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("payment_entries");
				frm.refresh_fields();
			}
		});
	},
	get_payment_entries: function(frm) {
		return frappe.call({
			method: "get_payment_entries",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("payment_entries");
				frm.refresh_fields();

				$(frm.fields_dict.payment_entries.wrapper).find("[data-fieldname=amount]").each(function(i,v){
					if (i !=0){
						$(v).addClass("text-right")
					}
				})
			}
		});
	}
});
