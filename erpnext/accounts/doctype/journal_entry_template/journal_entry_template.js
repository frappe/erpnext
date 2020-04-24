// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Journal Entry Template", {
	// refresh: function(frm) {

	// }
	setup: function(frm) {
		frm.set_query("account" ,"accounts", () => {
				return {
					filters: {
						"company": frm.doc.company==undefined ? null: frm.doc.company,
					}
				}
		});
	},
	onload_post_render: function(frm){
		// frm.get_field("accounts").grid.set_multiple_add("account");
	},
	all_accounts: function(frm) {
		frm.trigger("clear_child");
	},
	voucher_type: function(frm) {
		var add_accounts = function(doc, r) {
			$.each(r, function(i, d) {
				var row = frappe.model.add_child(doc, "JE Template Account", "accounts");
				row.account = d.account;
			});
			refresh_field("accounts");
		}
		frm.trigger("clear_child");
		switch(frm.doc.voucher_type){
			case "Opening Entry":
				if(frm.doc.company == undefined){
					frappe.throw("Please select Company!");
				}
				frm.set_value("is_opening", "Yes");
				
				frappe.call({
					type:"GET",
					method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_opening_accounts",
					args: {
						"company": frm.doc.company
					},
					callback: function(r) {
						if(r.message) {
							add_accounts(frm.doc, r.message);
						}
					}
				})
				break;
			case "Bank Entry":
			case "Cash Entry":
				frappe.call({
					type: "GET",
					method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_default_bank_cash_account",
					args: {
						"account_type": (frm.doc.voucher_type=="Bank Entry" ?
							"Bank" : (frm.doc.voucher_type=="Cash Entry" ? "Cash" : null)),
						"company": frm.doc.company
					},
					callback: function(r) {
						if(r.message) {
							add_accounts(frm.doc, [r.message]);
						}
					}
				})
				break;
			default:
				frm.trigger("clear_child");
		}
	},
	clear_child: function(frm){
		frappe.model.clear_table(frm.doc, "accounts");
		refresh_field("accounts");
	}
});
