// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.cscript.refresh = function(doc) {
	cur_frm.set_intro(doc.__islocal ? "" : __("There is nothing to edit."));
	cur_frm.cscript.set_root_readonly(doc);
};

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root customer group
	if(!doc.parent_supplier_group && !doc.__islocal) {
		cur_frm.set_read_only();
		cur_frm.set_intro(__("This is a root supplier group and cannot be edited."));
	} else {
		cur_frm.set_intro(null);
	}
};

frappe.ui.form.on("Supplier Group", {
	setup: function(frm){
		frm.set_query('parent_supplier_group', function (doc) {
			return {
				filters: {
					'is_group': 1,
					'name': ['!=', cur_frm.doc.supplier_group_name]
				}
			}
		});

		frm.set_query('account', 'accounts', function (doc, cdt, cdn) {
			return {
				filters: {
					'root_type': 'Liability',
					'account_type': 'Payable',
					'company': locals[cdt][cdn].company,
					"is_group": 0
				}
			}
		});

		frm.set_query('advance_account', 'accounts', function (doc, cdt, cdn) {
			return {
				filters: {
					"root_type": 'Asset',
					"account_type": "Payable",
					"company": locals[cdt][cdn].company,
					"is_group": 0
				}
			}
		});
	}
});
