// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.set_query("default_account", "accounts", function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	var company_currency = erpnext.get_currency(d.company);
	return{
		filters: [
			['Account', 'account_type', 'in', 'Bank, Cash, Receivable'],
			['Account', 'is_group', '=', 0],
			['Account', 'company', '=', d.company],
			['Account', 'account_currency', '=', company_currency]
		]
	}
});
