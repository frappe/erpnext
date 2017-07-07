// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Supplier Scorecard Period", {
	onload: function(frm) {
		frm.get_field("variables").grid.toggle_display("value", true);
		frm.get_field("criteria").grid.toggle_display("score", true);
		
		
	},
	refresh: function(frm) {
		//cur_frm.reload_doc();
	}
});
