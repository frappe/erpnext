// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc) {
	cur_frm.toggle_display('warehouse_name', doc.__islocal);
}

cur_frm.cscript.merge = function(doc, cdt, cdn) {
	if (!doc.merge_with) {
		msgprint(wn._("Please enter the warehouse to which you want to merge?"));
		return;
	}
	var check = confirm(wn._("Are you sure you want to merge this warehouse into " 
		+ doc.merge_with + "?"));
	if (check) {
		return $c_obj(make_doclist(cdt, cdn), 'merge_warehouses', '', '');
	}
}

cur_frm.set_query("create_account_under", function() {
	return {
		filters: {
			"company": cur_frm.doc.company,
			"debit_or_credit": "Debit",
			'group_or_ledger': "Group"
		}
	}
})
