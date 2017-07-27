// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.set_root_readonly(doc);
}

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root customer group
	if(!doc.parent_customer_group) {
		cur_frm.set_read_only();
		cur_frm.set_intro(__("This is a root customer group and cannot be edited."));
	} else {
		cur_frm.set_intro(null);
	}
}

//get query select Customer Group
cur_frm.fields_dict['parent_customer_group'].get_query = function(doc,cdt,cdn) {
	return {
		filters: {
			'is_group': 1
		}
	}
}

cur_frm.fields_dict['accounts'].grid.get_field('account').get_query = function(doc, cdt, cdn) {
	var d  = locals[cdt][cdn];
	return {
		filters: {
			'account_type': 'Receivable',
			'company': d.company,
			"is_group": 0
		}
	}
}
