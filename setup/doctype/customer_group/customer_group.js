// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
 
cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.set_root_readonly(doc);
}

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root customer group
	if(!doc.parent_customer_group) {
		cur_frm.perm = [[1,0,0], [1,0,0]];
		cur_frm.set_intro(wn._("This is a root customer group and cannot be edited."));
	} else {
		cur_frm.set_intro(null);
	}
}

//get query select Customer Group
cur_frm.fields_dict['parent_customer_group'].get_query = function(doc,cdt,cdn) {
	return{
		searchfield:['name', 'parent_customer_group'],
		filters: {
			'is_group': "Yes"
		}
	} 
}