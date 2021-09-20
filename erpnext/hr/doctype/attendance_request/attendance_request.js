// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee', 'company', 'company');

frappe.ui.form.on('Attendance Request', {
	half_day: function (frm) {
		if (frm.doc.half_day == 1) {
			frm.set_df_property('half_day_date', 'reqd', true);
		}
		else {
			frm.set_df_property('half_day_date', 'reqd', false);
		}
		
	},
	half_day_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.half_day_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("half_day_date_nepal", resp.message)
				}
			}
		})
	},

	from_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.from_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("from_date_nepal", resp.message)
				}
			}
		})
	},
	to_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.to_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("to_date_nepal", resp.message)
				}
			}
		})
	},
	
});
