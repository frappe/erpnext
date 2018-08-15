// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Department', {
	refresh: function(frm) {
		// read-only for root department
		if(!frm.doc.parent_department) {
			frm.set_read_only();
			frm.set_intro(__("This is a root department and cannot be edited."));
		}
	},
	validate: function(frm) {
		if(frm.doc.name=="All Departments") {
			frappe.throw(__("You cannot edit root node."));
		}
	}
});
