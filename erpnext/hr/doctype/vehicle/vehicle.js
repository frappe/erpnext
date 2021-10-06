// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vehicle', {
	refresh: function (frm) {

	},

	
	acquisition_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.acquisition_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("acquisition_date_nepal", resp.message)
				}
			}
		})
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
	},
	carbon_check_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.carbon_check_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("last_carbon_check_nepal", resp.message)
				}
			}
		})
	}
});
