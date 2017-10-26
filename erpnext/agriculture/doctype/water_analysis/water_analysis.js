// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Water Analysis', {
	refresh: function(frm) {
		console.log(frm.doc.laboratory_testing_datetime)
	},
	laboratory_testing_datetime: function(frm) {
		if (!frm.doc.result_datetime) 
			frm.doc.result_datetime = frm.doc.laboratory_testing_datetime;
		frm.refresh_fields();
	}
});
