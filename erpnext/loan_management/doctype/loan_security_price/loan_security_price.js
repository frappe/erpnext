// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Security Price', {
	// refresh: function(frm) {

	// }
	valid_upto: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.valid_upto
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("valid_upto_nepal", resp.message)
				}
			}
		})
	},
	valid_from: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.valid_from
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("valid_from_nepal", resp.message)
				}
			}
		})
	}
});
