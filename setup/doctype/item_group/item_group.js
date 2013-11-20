// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.set_root_readonly(doc);
	cur_frm.appframe.add_button(wn._("Item Group Tree"), function() {
		wn.set_route("Sales Browser", "Item Group");
	}, "icon-sitemap")

	if(!doc.__islocal && doc.show_in_website) {
		cur_frm.appframe.add_button("View In Website", function() {
			window.open(doc.page_name);
		}, "icon-globe");
	}
}

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root item group
	if(!doc.parent_item_group) {
		cur_frm.perm = [[1,0,0], [1,0,0]];
		cur_frm.set_intro(wn._("This is a root item group and cannot be edited."));
	} else {
		cur_frm.set_intro(null);
	}
}

//get query select item group
cur_frm.fields_dict['parent_item_group'].get_query = function(doc,cdt,cdn) {
	return{
		filters:[
			['Item Group', 'is_group', '=', 'Yes'],
			['Item Group', 'name', '!=', doc.item_group_name]
		]
	}
}