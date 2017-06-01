// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Supplier Scorecard', {
	onload: function(frm) {
		frm.get_field("variables").grid.toggle_display("value", true);
		frm.get_field("criteria").grid.toggle_display("score", true);
		
		if (frm.doc.indicator_color != "")
		{

			frm.set_indicator_formatter('status', function(doc) { 

				return doc.indicator_color.toLowerCase();
			});
		}
		
	},
	refresh: function(frm) {
		//cur_frm.reload_doc();
	}
});
