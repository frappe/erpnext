// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.set_query("default_account", "accounts", function(doc, cdt, cdn) {
	return{
		filters: [
			['Account', 'account_type', 'in', 'Bank, Cash'],
			['Account', 'group_or_ledger', '=', 'Ledger'],
			['Account', 'company', '=', doc.company]
		]
	}
});
