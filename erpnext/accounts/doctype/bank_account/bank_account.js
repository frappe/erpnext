// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('bank_account', 'parent_account', 'parent_account');

frappe.ui.form.on('Bank Account', {
	refresh: function(frm) {

	}
});

cur_frm.set_query("bank_account", function() {
				return {
					"filters": {
						"account_type": "Bank",
						"is_group": 0
					}				
				};
			});
