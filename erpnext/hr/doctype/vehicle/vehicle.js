// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vehicle', {
	validate: function(frm) {
		if (frm.doc.__islocal){
			frm.doc.last_odometer_value = frm.doc.initial_odometer_value;
		}

	}
});
