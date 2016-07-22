// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Student Batch', {
	refresh: function(frm) {

	}
});

cur_frm.add_fetch("student", "title", "student_name");
