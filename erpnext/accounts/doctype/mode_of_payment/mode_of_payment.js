// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Mode of Payment', {
	setup: function(frm) {
		debugger;
		frm.set_query("default_account", "accounts", function(doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			let company_currency = erpnext.get_currency(d.company);
			return{
				filters: [
					['Account', 'account_type', 'in', 'Bank, Cash, Receivable'],
					['Account', 'is_group', '=', 0],
					['Account', 'company', '=', d.company],
					['Account', 'account_currency', '=', company_currency]
				]
			}
		});
	},
})