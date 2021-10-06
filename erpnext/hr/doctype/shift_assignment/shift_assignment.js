// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Assignment', {
	refresh: function(frm) {

	},
	start_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.start_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("start_date_nepal", resp.message)
				}
			}
		})
	},
	end_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.end_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("end_date_nepal", resp.message)
				}
			}
		})
	}
});
