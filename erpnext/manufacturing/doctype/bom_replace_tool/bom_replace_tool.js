// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.cscript.refresh = function(doc) {
	cur_frm.disable_save();
}

cur_frm.set_query("current_bom", function(doc) {
	return{
		query: "erpnext.controllers.queries.bom",
		filters: {name: "!" + doc.new_bom}
	}
});


cur_frm.set_query("new_bom", function(doc) {
	return{
		query: "erpnext.controllers.queries.bom",
		filters: {name: "!" + doc.current_bom}
	}
});