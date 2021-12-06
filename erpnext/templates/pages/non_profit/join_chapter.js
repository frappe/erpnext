// Copyright (c) 2017, EOSSF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Chapter Member', {
	onsubmit: function (frm) {
		console.log("here" + frappe.session.user)
		// body...
	}
	refresh: function(frm) {

	}
});
