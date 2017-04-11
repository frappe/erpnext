// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.set_root_readonly(doc);
}

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root territory
	if(!doc.parent_territory) {
		cur_frm.set_read_only();
		cur_frm.set_intro(__("This is a root territory and cannot be edited."));
	} else {
		cur_frm.set_intro(null);
	}
}

//get query select territory
cur_frm.fields_dict['parent_territory'].get_query = function(doc,cdt,cdn) {
	return{
		filters:[
			['Territory', 'is_group', '=', 1],
			['Territory', 'name', '!=', doc.territory_name]
		]
	}
}