// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.set_query("default_account", "accounts", function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return{
		filters: [
			['Account', 'account_type', 'in', 'Bank, Cash'],
			['Account', 'is_group', '=', 0],
			['Account', 'company', '=', d.company]
		]
	}
});
