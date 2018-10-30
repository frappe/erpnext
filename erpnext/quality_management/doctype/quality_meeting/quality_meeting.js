// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Meeting', {
	refresh: function(frm) {

	},
	onload: function(frm){
		if(frm.doc.date == null){
			frm.set_value("date", frappe.datetime.get_today());
		}
	}
});
