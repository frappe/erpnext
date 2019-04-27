// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Action', {
	onload: function(frm) {
		frm.set_value("date", frappe.datetime.get_today());
		frm.refresh();
		if (frm.doc.review) {
			frm.doc.type = "Quality Review";
		}
		if (frm.doc.feedback) {
			frm.doc.type = "Quality Feedback";
		}
	},
	type: function(frm){
		if(frm.doc.description){
			frm.doc.review = '';
			frm.doc.feedback = '';
			frm.refresh();
		}
	}
});