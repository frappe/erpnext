// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Healthcare Insurance Contract', {
	refresh: function(frm) {
		if(frm.doc.__islocal){
			frm.set_value('start_date', frappe.datetime.get_today())
		}
	},
	start_date: function(frm){
		if(frm.doc.start_date){
			var to_date=frappe.datetime.add_days(frm.doc.start_date, 365)
			frm.set_value('end_date', to_date);
		}
	},
});
