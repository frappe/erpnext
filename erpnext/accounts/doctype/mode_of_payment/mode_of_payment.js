// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.set_query("default_account", function(doc) {
	return{
		filters: [
			['Account', 'account_type', 'in', 'Bank, Cash'],
			['Account', 'group_or_ledger', '=', 'Ledger'],
			['Account', 'company', '=', doc.company]
		]
	}
});