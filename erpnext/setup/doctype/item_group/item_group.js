// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.list_route = "Sales Browser/Item Group";

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.set_root_readonly(doc);
	cur_frm.add_custom_button(__("Item Group Tree"), function() {
		frappe.set_route("Sales Browser", "Item Group");
	}, "icon-sitemap")
}

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root item group
	cur_frm.set_intro("");
	if(!doc.parent_item_group) {
		cur_frm.set_read_only();
		cur_frm.set_intro(__("This is a root item group and cannot be edited."), true);
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
