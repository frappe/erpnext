// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Movement', {
	select_serial_no: function(frm) {
		if (frm.doc.select_serial_no) {
			let serial_no = frm.doc.serial_no
				? frm.doc.serial_no + '\n' + frm.doc.select_serial_no : frm.doc.select_serial_no;
			frm.set_value("serial_no", serial_no);
			frm.set_value("quantity", serial_no.split('\n').length);
		}
	},

	serial_no: function(frm) {
		const qty = frm.doc.serial_no ? frm.doc.serial_no.split('\n').length : 0;
		frm.set_value("quantity", qty);
	},

	setup: function(frm) {
		frm.set_query("select_serial_no", function() {
			return {
				filters: {
					"asset": frm.doc.asset
				}
			};
		});
	}
});
