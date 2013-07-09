// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.


cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.set_root_readonly(doc);
	cur_frm.add_custom_button("Item Group Tree", function() {
		wn.set_route("Sales Browser", "Item Group");
	})
}

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root item group
	if(!doc.parent_item_group) {
		cur_frm.perm = [[1,0,0], [1,0,0]];
		cur_frm.set_intro("This is a root item group and cannot be edited.");
	} else {
		cur_frm.set_intro(null);
	}
}

//get query select item group
cur_frm.fields_dict['parent_item_group'].get_query = function(doc,cdt,cdn) {
	return{
		filters:[
			['Item Group', 'is_group', '=', 'Yes'],
			['Item Group', 'naem', '!=', doc.item_group_name]
		]
	}
}