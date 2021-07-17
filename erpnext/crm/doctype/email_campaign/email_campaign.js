// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Email Campaign', {
	email_campaign_for: function(frm) {
		frm.set_value('recipient', '');
	},

	start_date: function(frm){
		frappe.call({
			method:"erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.start_date
			},
			callback: function(resp){
				if(resp.message){
					cur_frm.set_value("start_date_nepali",resp.message)
				}
			}
		})
	},
});
