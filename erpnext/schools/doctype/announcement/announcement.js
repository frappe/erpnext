// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Announcement', {
	onload: function(frm) {
		frm.add_fetch('instructor', 'instructor_name' , 'posted_by');
	}
});

