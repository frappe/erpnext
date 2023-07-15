// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.set_root_readonly(doc);
}

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root customer group
	if(!doc.parent_customer_group && !doc.__islocal) {
		cur_frm.set_read_only();
		cur_frm.set_intro(__("This is a root customer group and cannot be edited."));
	} else {
		cur_frm.set_intro(null);
	}
}

frappe.ui.form.on("Customer Group", {
	setup: function(frm){
		frm.set_query('parent_customer_group', function (doc) {
			return {
				filters: {
					'is_group': 1,
					'name': ['!=', cur_frm.doc.customer_group_name]
				}
			}
		});

		frm.set_query('account', 'accounts', function (doc, cdt, cdn) {
			return {
				filters: {
					"account_type": 'Receivable',
					"company": locals[cdt][cdn].company,
					"is_group": 0
				}
			}
		});

		frm.set_query('advance_account', 'accounts', function (doc, cdt, cdn) {
			return {
				filters: {
					"root_type": 'Liability',
					"account_type": "Receivable",
					"company": locals[cdt][cdn].company,
					"is_group": 0
				}
			}
		});
	}
});
