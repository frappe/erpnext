// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('COP', {
	setup: function(frm){
		frm.get_docfield("items").allow_bulk_edit = 1;		
        frm.get_field('items').grid.editable_fields = [
			{fieldname: 'account', columns: 2},
			{fieldname: 'mining_expenses', columns: 2},
			{fieldname: 'crushing_plant_expenses1', columns: 2},
			{fieldname: 'crushing_plant_expenses2', columns: 2},
			{fieldname: 'washed_expenses', columns: 2},
			{fieldname: 'transportation', columns: 1},
			{fieldname: 's_and_d', columns: 1}
		];
	},

	get_accounts: function(frm) {
		return frappe.call({
			method: "get_accounts",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("accounts");
				frm.refresh_fields();
			},
			freeze: true,
			freeze_message: "Loading Expense Accounts..... Please Wait"
		});
	}
});
