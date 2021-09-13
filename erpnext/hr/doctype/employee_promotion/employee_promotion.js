// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/hr/employee_property_update.js' %}

frappe.ui.form.on('Employee Promotion', {
	refresh: function (frm) {

	},
	promotion_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.promotion_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("promotion_date_nepal", resp.message)
				}
			}
		})
	
	
	}
	

});
