// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Checkin', {
	setup: (frm) => {
		if(!frm.doc.time) {
			frm.set_value("time", frappe.datetime.now_datetime());
		}
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.time
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("time_nepal", resp.message)
				}
			}
		})
	}
});
