// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.set_root_readonly(doc);
}

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root territory
	if(!doc.parent_territory) {
		cur_frm.perm = [[1,0,0], [1,0,0]];
		cur_frm.set_intro(wn._("This is a root territory and cannot be edited."));
	} else {
		cur_frm.set_intro(null);
	}
}

//get query select territory
cur_frm.fields_dict['parent_territory'].get_query = function(doc,cdt,cdn) {
	return{
		filters:[
			['Territory', 'is_group', '=', 'Yes'],
			['Territory', 'name', '!=', doc.territory_name]
		]
	}
}


// ******************** ITEM Group ******************************** 
cur_frm.fields_dict['target_details'].grid.get_field("item_group").get_query = function(doc, cdt, cdn) {
	return{
		filters:{ 'is_group': "No"}
	}
}
