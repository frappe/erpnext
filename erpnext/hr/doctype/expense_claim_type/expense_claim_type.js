// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.set_query("default_account", "accounts", function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return{
		filters: {
			"is_group": 0,
			"root_type": "Expense",
			'company': d.company
		}
	}
});