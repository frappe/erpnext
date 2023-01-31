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

// get query select Customer Group
cur_frm.fields_dict['parent_supplier_group'].get_query = function() {
	return {
		filters: {
			'is_group': 1,
			'name': ['!=', cur_frm.doc.supplier_group_name]
		}
	};
};

cur_frm.fields_dict['accounts'].grid.get_field('account').get_query = function(doc, cdt, cdn) {
	var d  = locals[cdt][cdn];
	return {
		filters: {
			'account_type': 'Payable',
			'company': d.company,
			"is_group": 0
		}
	};
};
