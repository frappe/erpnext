// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Land Unit', {
	onload: function(frm){
	},
	refresh: function(frm) {
		// frappe.msgprint('Refresh')
		if(!frm.doc.parent_land_unit){
			frm.set_read_only();
			frm.set_intro(__("This is a root territory and cannot be edited."));
		}
		else{
			frm.set_intro(null);
		}
	}
});
