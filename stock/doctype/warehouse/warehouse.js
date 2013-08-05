// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc) {
	cur_frm.toggle_display('warehouse_name', doc.__islocal);
}

cur_frm.cscript.merge = function(doc, cdt, cdn) {
	if (!doc.merge_with) {
		msgprint("Please enter the warehouse to which you want to merge?");
		return;
	}
	var check = confirm("Are you sure you want to merge this warehouse into " 
		+ doc.merge_with + "?");
	if (check) {
		return $c_obj(make_doclist(cdt, cdn), 'merge_warehouses', '', '');
	}
}