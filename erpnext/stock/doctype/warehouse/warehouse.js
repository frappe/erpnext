// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc) {
	cur_frm.toggle_display('warehouse_name', doc.__islocal);
}

cur_frm.set_query("create_account_under", function() {
	return {
		filters: {
			"organization": cur_frm.doc.organization,
			'is_group': 1
		}
	}
})
